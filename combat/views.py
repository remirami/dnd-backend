from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import CombatSession, CombatParticipant, CombatAction
from .serializers import (
    CombatSessionSerializer, CombatParticipantSerializer, CombatActionSerializer,
    AttackRequestSerializer, SpellRequestSerializer
)
from .utils import (
    roll_d20, calculate_attack_roll, calculate_damage, check_hit,
    is_critical_hit, apply_resistance, calculate_saving_throw
)
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character
from bestiary.models import EnemyAttack, DamageType


class CombatSessionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing combat sessions"""
    queryset = CombatSession.objects.all().order_by('-started_at')
    serializer_class = CombatSessionSerializer
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a combat session"""
        session = self.get_object()
        if session.status != 'preparing':
            return Response(
                {"error": "Combat session is not in preparing status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there are participants
        if not session.participants.exists():
            return Response(
                {"error": "Cannot start combat without participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'active'
        session.current_round = 1
        session.current_turn_index = 0
        session.save()
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat started!",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def roll_initiative(self, request, pk=None):
        """Roll initiative for all participants"""
        session = self.get_object()
        
        if session.status == 'active':
            return Response(
                {"error": "Cannot roll initiative after combat has started"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participants = session.participants.all()
        if not participants.exists():
            return Response(
                {"error": "No participants in combat session"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .utils import roll_d20
        
        results = []
        for participant in participants:
            # Roll d20 + DEX modifier
            roll, _ = roll_d20()
            dex_mod = participant.get_ability_modifier('DEX')
            initiative = roll + dex_mod
            
            participant.initiative = initiative
            participant.save()
            
            results.append({
                "participant": participant.get_name(),
                "roll": roll,
                "dex_modifier": dex_mod,
                "initiative": initiative
            })
        
        # Sort participants by initiative
        serializer = self.get_serializer(session)
        return Response({
            "message": "Initiative rolled for all participants",
            "results": results,
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a character or enemy to the combat"""
        session = self.get_object()
        
        if session.status == 'active':
            return Response(
                {"error": "Cannot add participants after combat has started"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_type = request.data.get('participant_type')
        character_id = request.data.get('character_id')
        encounter_enemy_id = request.data.get('encounter_enemy_id')
        
        if participant_type == 'character':
            if not character_id:
                return Response(
                    {"error": "character_id required for character participant"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                character = Character.objects.get(pk=character_id)
                if not hasattr(character, 'stats'):
                    return Response(
                        {"error": "Character must have stats"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                participant, created = CombatParticipant.objects.get_or_create(
                    combat_session=session,
                    participant_type='character',
                    character=character,
                    defaults={
                        'current_hp': character.stats.hit_points,
                        'max_hp': character.stats.max_hit_points,
                        'armor_class': character.stats.armor_class,
                    }
                )
                
                if not created:
                    return Response(
                        {"error": "Character already in combat"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{character.name} added to combat",
                    "participant": serializer.data
                })
            except Character.DoesNotExist:
                return Response(
                    {"error": "Character not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif participant_type == 'enemy':
            if not encounter_enemy_id:
                return Response(
                    {"error": "encounter_enemy_id required for enemy participant"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                encounter_enemy = EncounterEnemy.objects.get(pk=encounter_enemy_id)
                if encounter_enemy.encounter != session.encounter:
                    return Response(
                        {"error": "Enemy must be from the same encounter"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                participant, created = CombatParticipant.objects.get_or_create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=encounter_enemy,
                    defaults={
                        'current_hp': encounter_enemy.current_hp,
                        'max_hp': encounter_enemy.current_hp,  # Use current as max
                        'armor_class': encounter_enemy.enemy.stats.armor_class if hasattr(encounter_enemy.enemy, 'stats') else encounter_enemy.enemy.ac or 10,
                    }
                )
                
                if not created:
                    return Response(
                        {"error": "Enemy already in combat"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{encounter_enemy.name} added to combat",
                    "participant": serializer.data
                })
            except EncounterEnemy.DoesNotExist:
                return Response(
                    {"error": "Encounter enemy not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(
            {"error": "Invalid participant_type. Use 'character' or 'enemy'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def next_turn(self, request, pk=None):
        """Advance to the next turn"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset previous participant's turn
        current = session.get_current_participant()
        if current:
            current.reset_turn()
        
        # Advance to next turn
        next_participant = session.next_turn()
        
        if not next_participant:
            return Response(
                {"error": "No active participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"Round {session.current_round}, {next_participant.get_name()}'s turn",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def attack(self, request, pk=None):
        """Make an attack"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AttackRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        attacker_id = data['attacker_id']
        target_id = data['target_id']
        
        try:
            attacker = session.participants.get(pk=attacker_id)
            target = session.participants.get(pk=target_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Attacker or target not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not attacker.is_active:
            return Response(
                {"error": "Attacker is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if it's attacker's turn
        current = session.get_current_participant()
        if current != attacker:
            return Response(
                {"error": f"It is not {attacker.get_name()}'s turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get attack details
        attack_name = data.get('attack_name', 'Unarmed Strike')
        advantage = data.get('advantage', False)
        disadvantage = data.get('disadvantage', False)
        other_modifiers = data.get('other_modifiers', 0)
        
        # Find attack if it's an enemy attack
        damage_string = "1d4"  # Default unarmed
        if attacker.encounter_enemy:
            # Try to find enemy attack
            enemy = attacker.encounter_enemy.enemy
            attacks = enemy.attacks.all()
            if attacks.exists():
                enemy_attack = attacks.first()
                attack_name = enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        # For now, use STR modifier (could be improved to use weapon-specific ability)
        ability_mod = attacker.get_ability_modifier('STR')
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
        else:
            # For enemies, use a default proficiency bonus (simplified)
            proficiency_bonus = 2
        proficiency = True  # Simplified - should check weapon proficiency
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Check if hit
        hit = check_hit(attack_total, target.armor_class)
        critical = (roll == 20)  # Natural 20 is critical
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        if hit:
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, ability_mod, critical
            )
            new_hp, concentration_broken = target.take_damage(damage_amount)
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            target=target,
            action_type='attack',
            attack_name=attack_name,
            attack_roll=roll,
            attack_modifier=ability_mod + (proficiency_bonus if proficiency else 0) + other_modifiers,
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage_amount if hit else None,
            critical=critical,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{roll_breakdown} | {attack_breakdown}"
        )
        
        # Mark action as used
        attacker.action_used = True
        attacker.save()
        
        return Response({
            "message": f"{attacker.get_name()} attacks {target.get_name()}",
            "attack_roll": roll,
            "attack_total": attack_total,
            "target_ac": target.armor_class,
            "hit": hit,
            "critical": critical,
            "damage": damage_amount if hit else 0,
            "target_hp": target.current_hp,
            "breakdown": {
                "roll": roll_breakdown,
                "attack": attack_breakdown,
                "damage": damage_breakdown if hit else None
            },
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def cast_spell(self, request, pk=None):
        """Cast a spell"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SpellRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        caster_id = data['caster_id']
        target_id = data.get('target_id')
        spell_name = data['spell_name']
        
        try:
            caster = session.participants.get(pk=caster_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Caster not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not caster.is_active:
            return Response(
                {"error": "Caster is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if it's caster's turn
        current = session.get_current_participant()
        if current != caster:
            return Response(
                {"error": f"It is not {caster.get_name()}'s turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get spell details
        spell_level = data.get('spell_level', 0)
        save_type = data.get('save_type', '')
        save_dc = data.get('save_dc')
        damage_string = data.get('damage_string', '')
        damage_type_id = data.get('damage_type')
        
        # If there's a target and a saving throw, roll it
        target = None
        save_roll = None
        save_success = None
        if target_id:
            try:
                target = session.participants.get(pk=target_id)
            except CombatParticipant.DoesNotExist:
                return Response(
                    {"error": "Target not found in combat"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if save_type and save_dc:
                # Roll saving throw
                save_roll_base, _ = roll_d20()
                save_ability_mod = target.get_ability_modifier(save_type)
                save_total, save_breakdown = calculate_saving_throw(
                    save_roll_base, save_ability_mod
                )
                save_success = save_total >= save_dc
                save_roll = save_total
        
        # Calculate damage if applicable
        damage_amount = 0
        damage_breakdown = ""
        if damage_string:
            damage_amount, damage_breakdown = calculate_damage(damage_string)
            
            # Apply damage based on save (if applicable)
            if target and save_success is not None:
                if save_success:
                    damage_amount = damage_amount // 2  # Half damage on successful save
                    damage_breakdown += f" | Save succeeded: half damage = {damage_amount}"
                else:
                    damage_breakdown += f" | Save failed: full damage = {damage_amount}"
            
            if target:
                new_hp, concentration_broken = target.take_damage(damage_amount)
        
        # Get damage type
        damage_type = None
        if damage_type_id:
            from bestiary.models import DamageType
            try:
                damage_type = DamageType.objects.get(pk=damage_type_id)
            except DamageType.DoesNotExist:
                pass
        
        # Check if spell requires concentration
        requires_concentration = request.data.get('requires_concentration', False)
        if requires_concentration:
            caster.is_concentrating = True
            caster.concentration_spell = spell_name
            caster.save()
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=caster,
            target=target,
            action_type='spell',
            attack_name=spell_name,
            damage_amount=damage_amount if damage_string else None,
            damage_type=damage_type,
            save_type=save_type,
            save_dc=save_dc,
            save_roll=save_roll,
            save_success=save_success,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"Cast {spell_name} (Level {spell_level})" + (" [Concentration]" if requires_concentration else "")
        )
        
        # Mark action as used
        caster.action_used = True
        caster.save()
        
        result = {
            "message": f"{caster.get_name()} casts {spell_name}",
            "spell_name": spell_name,
            "spell_level": spell_level,
            "action": CombatActionSerializer(action).data
        }
        
        if target:
            result["target"] = target.get_name()
            result["target_hp"] = target.current_hp
        
        if save_type and save_dc:
            result["save_type"] = save_type
            result["save_dc"] = save_dc
            result["save_roll"] = save_roll
            result["save_success"] = save_success
        
        if damage_amount > 0:
            result["damage"] = damage_amount
            result["damage_breakdown"] = damage_breakdown
        
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def saving_throw(self, request, pk=None):
        """Make a saving throw"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        save_type = request.data.get('save_type')  # STR, DEX, CON, etc.
        save_dc = request.data.get('save_dc')
        advantage = request.data.get('advantage', False)
        disadvantage = request.data.get('disadvantage', False)
        
        if not participant_id or not save_type:
            return Response(
                {"error": "Missing 'participant_id' or 'save_type'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Roll saving throw
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        ability_mod = participant.get_ability_modifier(save_type)
        
        # Check for proficiency (simplified - should check actual proficiencies)
        proficiency_bonus = participant.character.proficiency_bonus if participant.character else 2
        proficiency = False  # Simplified - should check actual saving throw proficiencies
        
        save_total, save_breakdown = calculate_saving_throw(
            roll, ability_mod, proficiency_bonus, proficiency
        )
        
        save_success = None
        if save_dc:
            save_success = save_total >= save_dc
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='other',
            save_type=save_type,
            save_dc=save_dc,
            save_roll=save_total,
            save_success=save_success,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"Saving throw: {save_type} | {roll_breakdown} | {save_breakdown}"
        )
        
        return Response({
            "message": f"{participant.get_name()} makes a {save_type} saving throw",
            "save_type": save_type,
            "roll": roll,
            "save_total": save_total,
            "save_dc": save_dc,
            "save_success": save_success,
            "breakdown": {
                "roll": roll_breakdown,
                "save": save_breakdown
            },
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def death_save(self, request, pk=None):
        """Make a death saving throw"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        roll = request.data.get('roll')  # Optional: can provide roll or auto-roll
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if participant.current_hp > 0:
            return Response(
                {"error": "Participant is not unconscious"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Make death save
        success, is_stable, is_dead, message = participant.make_death_save(roll)
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='death_save',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=message
        )
        
        return Response({
            "message": message,
            "success": success,
            "is_stable": is_stable,
            "is_dead": is_dead,
            "death_save_successes": participant.death_save_successes,
            "death_save_failures": participant.death_save_failures,
            "current_hp": participant.current_hp,
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def check_concentration(self, request, pk=None):
        """Check concentration after taking damage"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        damage_amount = int(request.data.get('damage_amount', 0))
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check concentration
        concentration_broken, save_roll, save_dc, message = participant.check_concentration(damage_amount)
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='concentration_check',
            save_type='CON',
            save_dc=save_dc,
            save_roll=save_roll,
            save_success=not concentration_broken,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=message
        )
        
        return Response({
            "message": message,
            "concentration_broken": concentration_broken,
            "save_roll": save_roll,
            "save_dc": save_dc,
            "is_concentrating": participant.is_concentrating,
            "concentration_spell": participant.concentration_spell,
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def opportunity_attack(self, request, pk=None):
        """Make an opportunity attack"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AttackRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        attacker_id = data['attacker_id']
        target_id = data['target_id']
        
        try:
            attacker = session.participants.get(pk=attacker_id)
            target = session.participants.get(pk=target_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Attacker or target not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if attacker.reaction_used:
            return Response(
                {"error": "Attacker has already used their reaction this turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not attacker.is_active:
            return Response(
                {"error": "Attacker is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get attack details
        attack_name = data.get('attack_name', 'Opportunity Attack')
        advantage = data.get('advantage', False)
        disadvantage = data.get('disadvantage', False)
        other_modifiers = data.get('other_modifiers', 0)
        
        # Find attack if it's an enemy attack
        damage_string = "1d4"  # Default unarmed
        if attacker.encounter_enemy:
            enemy = attacker.encounter_enemy.enemy
            attacks = enemy.attacks.all()
            if attacks.exists():
                enemy_attack = attacks.first()
                attack_name = enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        ability_mod = attacker.get_ability_modifier('STR')
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
        else:
            proficiency_bonus = 2
        proficiency = True
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Check if hit
        hit = check_hit(attack_total, target.armor_class)
        critical = (roll == 20)
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        if hit:
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, ability_mod, critical
            )
            new_hp, concentration_broken = target.take_damage(damage_amount)
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            target=target,
            action_type='opportunity_attack',
            attack_name=attack_name,
            attack_roll=roll,
            attack_modifier=ability_mod + proficiency_bonus + other_modifiers,
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage_amount if hit else None,
            critical=critical,
            is_opportunity_attack=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"Opportunity Attack: {roll_breakdown} | {attack_breakdown}"
        )
        
        # Mark reaction as used
        attacker.reaction_used = True
        attacker.save()
        
        return Response({
            "message": f"{attacker.get_name()} makes an opportunity attack on {target.get_name()}",
            "attack_roll": roll,
            "attack_total": attack_total,
            "target_ac": target.armor_class,
            "hit": hit,
            "critical": critical,
            "damage": damage_amount if hit else 0,
            "target_hp": target.current_hp,
            "breakdown": {
                "roll": roll_breakdown,
                "attack": attack_breakdown,
                "damage": damage_breakdown if hit else None
            },
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def legendary_action(self, request, pk=None):
        """Use a legendary action"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        action_cost = int(request.data.get('action_cost', 1))
        action_name = request.data.get('action_name', 'Legendary Action')
        action_description = request.data.get('action_description', '')
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if participant.legendary_actions_max == 0:
            return Response(
                {"error": "Participant does not have legendary actions"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use legendary action
        success, message = participant.use_legendary_action(action_cost)
        
        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='legendary_action',
            attack_name=action_name,
            is_legendary_action=True,
            legendary_action_cost=action_cost,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=action_description or f"Used {action_name} (Cost: {action_cost})"
        )
        
        return Response({
            "message": message,
            "action_name": action_name,
            "action_cost": action_cost,
            "legendary_actions_remaining": participant.legendary_actions_remaining,
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End the combat session"""
        session = self.get_object()
        
        if session.status == 'ended':
            return Response(
                {"error": "Combat is already ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save()
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat ended",
            "session": serializer.data
        })


class CombatParticipantViewSet(viewsets.ModelViewSet):
    """API endpoint for managing combat participants"""
    queryset = CombatParticipant.objects.all()
    serializer_class = CombatParticipantSerializer
    
    @action(detail=True, methods=['post'])
    def damage(self, request, pk=None):
        """Apply damage to a participant"""
        participant = self.get_object()
        amount = int(request.data.get('amount', 0))
        
        if amount <= 0:
            return Response(
                {"error": "Damage amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_hp, concentration_broken = participant.take_damage(amount)
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} took {amount} damage",
            "current_hp": new_hp,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def heal(self, request, pk=None):
        """Heal a participant"""
        participant = self.get_object()
        amount = int(request.data.get('amount', 0))
        
        if amount <= 0:
            return Response(
                {"error": "Heal amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_hp = participant.heal(amount)
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} healed {amount} HP",
            "current_hp": new_hp,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_condition(self, request, pk=None):
        """Add a condition to a participant"""
        participant = self.get_object()
        condition_id = request.data.get('condition_id')
        
        if not condition_id:
            return Response(
                {"error": "Missing 'condition_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from bestiary.models import Condition
        try:
            condition = Condition.objects.get(pk=condition_id)
        except Condition.DoesNotExist:
            return Response(
                {"error": "Condition not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant.conditions.add(condition)
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{condition.get_name_display()} added to {participant.get_name()}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def remove_condition(self, request, pk=None):
        """Remove a condition from a participant"""
        participant = self.get_object()
        condition_id = request.data.get('condition_id')
        
        if not condition_id:
            return Response(
                {"error": "Missing 'condition_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from bestiary.models import Condition
        try:
            condition = Condition.objects.get(pk=condition_id)
        except Condition.DoesNotExist:
            return Response(
                {"error": "Condition not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant.conditions.remove(condition)
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{condition.get_name_display()} removed from {participant.get_name()}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def start_concentration(self, request, pk=None):
        """Start concentrating on a spell"""
        participant = self.get_object()
        spell_name = request.data.get('spell_name', '')
        
        if not spell_name:
            return Response(
                {"error": "Missing 'spell_name'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if participant.is_concentrating:
            return Response(
                {"error": f"Already concentrating on {participant.concentration_spell}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.is_concentrating = True
        participant.concentration_spell = spell_name
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} starts concentrating on {spell_name}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def end_concentration(self, request, pk=None):
        """End concentration"""
        participant = self.get_object()
        
        if not participant.is_concentrating:
            return Response(
                {"error": "Not concentrating on any spell"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_name = participant.concentration_spell
        participant.is_concentrating = False
        participant.concentration_spell = ""
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} loses concentration on {spell_name}",
            "participant": serializer.data
        })


class CombatActionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing combat actions (read-only)"""
    queryset = CombatAction.objects.all()
    serializer_class = CombatActionSerializer
