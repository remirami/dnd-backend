from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import logging

from .models import CombatSession, CombatParticipant, CombatAction, CombatLog, ConditionApplication, EnvironmentalEffect, ParticipantPosition
from .condition_effects import auto_apply_condition_from_spell, get_condition_for_spell
from .environmental_effects import (
    calculate_movement_cost, calculate_cover_ac_bonus, calculate_cover_save_bonus,
    has_full_cover, get_lighting_attack_modifier, get_weather_ranged_modifier,
    get_environmental_effects_summary
)
from .serializers import (
    CombatSessionSerializer, CombatParticipantSerializer, CombatActionSerializer,
    AttackRequestSerializer, SpellRequestSerializer, CombatLogSerializer,
    EnvironmentalEffectSerializer, ParticipantPositionSerializer
)
from .utils import (
    roll_d20, calculate_attack_roll, calculate_damage, check_hit,
    is_critical_hit, apply_resistance, calculate_saving_throw
)
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character
from bestiary.models import EnemyAttack, DamageType

# Combat logging
logger = logging.getLogger('combat')


class CombatSessionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing combat sessions"""
    queryset = CombatSession.objects.all().select_related(
        'encounter'
    ).prefetch_related(
        'participants',
        'participants__character',
        'participants__character__stats',
        'participants__encounter_enemy',
        'participants__encounter_enemy__enemy',
        'participants__encounter_enemy__enemy__stats'
    ).order_by('-started_at')
    serializer_class = CombatSessionSerializer
    
    def perform_create(self, serializer):
        """Handle creation with optional encounter"""
        encounter_id = self.request.data.get('encounter_id')
        is_practice = self.request.data.get('is_practice', False)
        
        if is_practice or not encounter_id:
            # Practice mode: no encounter needed
            serializer.save(encounter=None, is_practice=True)
        else:
            # Campaign mode: require encounter
            try:
                encounter = Encounter.objects.get(pk=encounter_id)
                serializer.save(encounter=encounter, is_practice=False)
            except Encounter.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"encounter_id": "Encounter not found"})
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a combat session"""
        session = self.get_object()
        logger.info(f"Combat start requested for session {pk} by user {request.user}")
        
        if session.status != 'preparing':
            logger.warning(f"Cannot start combat {pk}: status is '{session.status}', not 'preparing'")
            return Response(
                {"error": "Combat must be in 'preparing' status to start"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participants = session.participants.filter(is_active=True)
        if not participants.exists():
            logger.warning(f"Cannot start combat {pk}: no participants")
            return Response(
                {"error": "Cannot start combat without participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'active'
        session.current_round = 1
        session.current_turn_index = 0
        session.started_at = timezone.now()
        session.save()
        
        logger.info(f"Combat {pk} started with {participants.count()} participants")
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat started",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to combat"""
        session = self.get_object()
        participant_type = request.data.get('participant_type')
        
        if participant_type == 'character':
            character_id = request.data.get('character_id')
            if not character_id:
                return Response(
                    {"error": "Missing 'character_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                character = Character.objects.get(pk=character_id)
            except Character.DoesNotExist:
                return Response(
                    {"error": "Character not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not hasattr(character, 'stats'):
                return Response(
                    {"error": "Character must have stats"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            stats = character.stats
            participant = CombatParticipant.objects.create(
                combat_session=session,
                participant_type='character',
                character=character,
                initiative=0,
                current_hp=stats.hit_points,
                max_hp=stats.max_hit_points,
                armor_class=stats.armor_class
            )
            session.participants.add(participant)
            
            serializer = CombatParticipantSerializer(participant)
            return Response({
                "message": f"{character.name} added to combat",
                "participant": serializer.data
            })
        
        elif participant_type == 'enemy':
            encounter_enemy_id = request.data.get('encounter_enemy_id')
            enemy_id = request.data.get('enemy_id')  # Direct enemy ID for practice mode
            
            # Support both EncounterEnemy (for campaigns) and direct Enemy (for practice)
            if enemy_id:
                # Practice mode: add enemy directly
                from bestiary.models import Enemy
                try:
                    enemy = Enemy.objects.get(pk=enemy_id)
                except Enemy.DoesNotExist:
                    return Response(
                        {"error": "Enemy not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if not hasattr(enemy, 'stats'):
                    return Response(
                        {"error": "Enemy must have stats"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                enemy_name = request.data.get('enemy_name', enemy.name)
                enemy_hp = request.data.get('enemy_hp', enemy.stats.hit_points if hasattr(enemy, 'stats') else 10)
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=None,  # No EncounterEnemy for practice mode
                    initiative=0,
                    current_hp=enemy_hp,
                    max_hp=enemy.stats.hit_points if hasattr(enemy, 'stats') else enemy_hp,
                    armor_class=enemy.stats.armor_class if hasattr(enemy, 'stats') else 10
                )
                session.participants.add(participant)
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{enemy_name} added to combat",
                    "participant": serializer.data
                })
            
            elif encounter_enemy_id:
                # Campaign mode: use EncounterEnemy
                try:
                    encounter_enemy = EncounterEnemy.objects.get(pk=encounter_enemy_id)
                except EncounterEnemy.DoesNotExist:
                    return Response(
                        {"error": "Encounter enemy not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if session.encounter and encounter_enemy.encounter != session.encounter:
                    return Response(
                        {"error": "Enemy must be from the same encounter"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=encounter_enemy,
                    initiative=0,
                    current_hp=encounter_enemy.current_hp,
                    max_hp=encounter_enemy.enemy.stats.hit_points if hasattr(encounter_enemy.enemy, 'stats') else encounter_enemy.current_hp,
                    armor_class=encounter_enemy.enemy.stats.armor_class if hasattr(encounter_enemy.enemy, 'stats') else 10
                )
                session.participants.add(participant)
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{encounter_enemy.name} added to combat",
                    "participant": serializer.data
                })
            else:
                return Response(
                    {"error": "Missing 'encounter_enemy_id' or 'enemy_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        else:
            return Response(
                {"error": "Invalid participant_type. Must be 'character' or 'enemy'"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def roll_initiative(self, request, pk=None):
        """Roll initiative for all participants"""
        session = self.get_object()
        participants = session.participants.filter(is_active=True)
        
        if not participants.exists():
            return Response(
                {"error": "No participants in combat"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        for participant in participants:
            roll, _ = roll_d20()
            modifier = participant.get_ability_modifier('DEX')
            initiative = roll + modifier
            participant.initiative = initiative
            participant.save()
            results.append({
                'participant_id': participant.id,
                'name': participant.get_name(),
                'roll': roll,
                'modifier': modifier,
                'initiative': initiative
            })
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Initiative rolled",
            "results": results,
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def next_turn(self, request, pk=None):
        """Advance to the next turn"""
        session = self.get_object()
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        next_participant = session.next_turn()
        if not next_participant:
            return Response(
                {"error": "No active participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"Turn advanced to {next_participant.get_name()}",
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
        attack_name = data.get('attack_name', None)
        advantage = data.get('advantage', False)
        disadvantage = data.get('disadvantage', False)
        other_modifiers = data.get('other_modifiers', 0)
        weapon_slot = data.get('weapon_slot', 'main_hand')
        
        # Get equipped weapon for characters
        equipped_weapon = None
        damage_string = "1d4"  # Default unarmed
        use_ability = 'STR'  # Default to STR
        
        if attacker.character:
            # Try to get equipped weapon
            equipped_weapon = attacker.get_equipped_weapon(weapon_slot)
            if equipped_weapon:
                attack_name = attack_name or equipped_weapon.name
                damage_string = equipped_weapon.damage_dice
                
                # Use DEX for finesse weapons, otherwise STR
                if equipped_weapon.finesse:
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                else:
                    use_ability = 'STR'
            else:
                attack_name = attack_name or 'Unarmed Strike'
        elif attacker.encounter_enemy:
            # Try to find enemy attack
            enemy = attacker.encounter_enemy.enemy
            attacks = enemy.attacks.all()
            if attacks.exists():
                enemy_attack = attacks.first()
                attack_name = attack_name or enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        ability_mod = attacker.get_ability_modifier(use_ability)
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
            # Check weapon proficiency (simplified - check if character has weapon proficiency)
            proficiency = True  # TODO: Check actual weapon proficiency
        else:
            # For enemies, use a default proficiency bonus (simplified)
            proficiency_bonus = 2
            proficiency = True
        
        # Get magic item bonuses
        magic_bonuses = attacker.get_magic_item_bonuses()
        other_modifiers += magic_bonuses['to_hit']
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Get environmental effects for target
        cover_bonus = 0
        target_has_full_cover = False
        target_position = None
        target_cover_type = None
        
        try:
            target_position = target.position
            if target_position.current_cover:
                target_cover_type = target_position.current_cover
                cover_bonus = calculate_cover_ac_bonus(target_position.current_cover)
                target_has_full_cover = has_full_cover(target_position.current_cover)
        except ParticipantPosition.DoesNotExist:
            pass
        
        # Full cover prevents targeting
        if target_has_full_cover:
            return Response(
                {"error": f"{target.get_name()} has full cover and cannot be targeted"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get lighting effects for attacker
        lighting_modifier = None
        attacker_position = None
        attacker_lighting = None
        
        try:
            attacker_position = attacker.position
            if attacker_position.current_lighting:
                attacker_lighting = attacker_position.current_lighting
                has_darkvision = attacker.character.stats.darkvision > 0 if (attacker.character and hasattr(attacker.character, 'stats')) else False
                lighting_mod = get_lighting_attack_modifier(attacker_position.current_lighting, has_darkvision)
                lighting_modifier = lighting_mod
                if lighting_mod == 'disadvantage':
                    # Roll again and take lower
                    roll2, _ = roll_d20()
                    roll = min(roll, roll2)
                    advantage = False
                    disadvantage = True
                elif lighting_mod == 'advantage':
                    # Roll again and take higher
                    roll2, _ = roll_d20()
                    roll = max(roll, roll2)
                    advantage = True
                    disadvantage = False
        except ParticipantPosition.DoesNotExist:
            pass
        
        # Get weather effects for ranged attacks
        weather_modifier = None
        weather_effect = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='weather',
            is_active=True
        ).first()
        if weather_effect and weather_effect.weather_type:
            weather_mod = get_weather_ranged_modifier(weather_effect.weather_type)
            weather_modifier = weather_mod
            if weather_mod == 'disadvantage':
                # Check if ranged attack
                if equipped_weapon and equipped_weapon.range_normal > 0:
                    roll2, _ = roll_d20()
                    roll = min(roll, roll2)
                    advantage = False
                    disadvantage = True
            elif weather_mod == 'advantage':
                if equipped_weapon and equipped_weapon.range_normal > 0:
                    roll2, _ = roll_d20()
                    roll = max(roll, roll2)
                    advantage = True
                    disadvantage = False
        
        # Recalculate attack total with new roll
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Get target's effective AC (including armor, magic items, and cover)
        target_ac = target.calculate_effective_ac(cover_bonus=cover_bonus)
        
        # Check if hit
        hit = check_hit(attack_total, target_ac)
        critical = (roll == 20)  # Natural 20 is critical
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        if hit:
            # Add magic item damage bonus
            damage_modifier = ability_mod + magic_bonuses['to_damage']
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, damage_modifier, critical
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
            "target_ac": target_ac,
            "cover_bonus": cover_bonus,
            "weapon_used": attack_name if equipped_weapon else None,
            "ability_used": use_ability,
            "magic_bonuses": magic_bonuses,
            "hit": hit,
            "critical": critical,
            "damage": damage_amount if hit else 0,
            "target_hp": target.current_hp,
            "environmental_effects": {
                "cover": cover_bonus > 0,
                "cover_type": target_cover_type,
                "lighting": attacker_lighting,
                "lighting_modifier": lighting_modifier,
                "weather": weather_effect.weather_type if weather_effect else None,
                "weather_modifier": weather_modifier,
            },
            "breakdown": {
                "roll": roll_breakdown,
                "attack": attack_breakdown,
                "damage": damage_breakdown if hit else None
            },
            "concentration_broken": concentration_broken if hit else False,
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
        spell_level = data.get('spell_level')
        save_type = data.get('save_type', '')
        save_dc = data.get('save_dc')
        damage_string = data.get('damage_string', '')
        damage_type_id = data.get('damage_type')
        requires_concentration = request.data.get('requires_concentration', False)
        
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
        
        # Validate spell can be cast (if character is a spellcaster)
        if caster.character:
            from characters.spell_management import can_cast_spell
            is_ritual = request.data.get('is_ritual', False)
            
            if not can_cast_spell(caster.character, spell_name, allow_ritual=is_ritual):
                # Check if it's a ritual spell
                try:
                    from characters.models import CharacterSpell
                    spell = CharacterSpell.objects.get(character=caster.character, name=spell_name)
                    if spell.is_ritual and is_ritual:
                        # Allow ritual casting even if not prepared
                        pass
                    else:
                        return Response(
                            {"error": f"{caster.get_name()} cannot cast {spell_name}. Spell must be prepared (for prepared casters) or known (for known casters)."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except CharacterSpell.DoesNotExist:
                    return Response(
                        {"error": f"{caster.get_name()} does not know {spell_name}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        target = None
        if target_id:
            try:
                target = session.participants.get(pk=target_id)
            except CombatParticipant.DoesNotExist:
                return Response(
                    {"error": "Target not found in combat"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Handle concentration
        if requires_concentration:
            caster.is_concentrating = True
            caster.concentration_spell = spell_name
            caster.save()
        
        # Handle saving throw if applicable
        save_roll = None
        save_success = None
        damage_amount = 0
        if save_type and save_dc and target:
            save_roll, save_breakdown = roll_d20()
            ability_mod = target.get_ability_modifier(save_type)
            proficiency_bonus = target.character.proficiency_bonus if target.character else 2
            proficiency = False  # Simplified
            save_total, _ = calculate_saving_throw(save_roll, ability_mod, proficiency_bonus, proficiency)
            save_success = save_total >= save_dc
            
            # Calculate damage
            if damage_string:
                if save_success:
                    # Half damage on successful save
                    base_damage, _ = calculate_damage(damage_string, 0, False)
                    damage_amount = base_damage // 2
                else:
                    # Full damage on failed save
                    damage_amount, _ = calculate_damage(damage_string, 0, False)
                
                if damage_amount > 0:
                    new_hp, _ = target.take_damage(damage_amount)
        
        # Auto-apply conditions from spell (if save failed or no save)
        applied_condition = None
        if target and (not save_success or not save_type):
            applied_condition = auto_apply_condition_from_spell(target, spell_name)
            if applied_condition:
                # Create condition application record
                ConditionApplication.objects.create(
                    participant=target,
                    condition=applied_condition,
                    applied_round=session.current_round,
                    applied_turn=session.current_turn_index,
                    duration_type='spell' if requires_concentration else 'round',
                    duration_rounds=1 if not requires_concentration else 0,
                    expires_at_round=session.current_round + 1 if not requires_concentration else None,
                    source_type='spell',
                    source_name=spell_name
                )
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=caster,
            target=target,
            action_type='spell',
            attack_name=spell_name,
            damage_amount=damage_amount if damage_amount > 0 else None,
            save_type=save_type if save_type else None,
            save_dc=save_dc,
            save_roll=save_roll,
            save_success=save_success,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{caster.get_name()} casts {spell_name}"
        )
        
        # Mark action as used
        caster.action_used = True
        caster.save()
        
        return Response({
            "message": f"{caster.get_name()} casts {spell_name}",
            "spell_name": spell_name,
            "spell_level": spell_level,
            "target": target.get_name() if target else None,
            "target_hp": target.current_hp if target else None,
            "save_type": save_type if save_type else None,
            "save_dc": save_dc,
            "save_roll": save_roll,
            "save_success": save_success,
            "damage": damage_amount,
            "concentration_started": requires_concentration,
            "action": CombatActionSerializer(action).data
        })
    
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
        save_type = request.data.get('save_type')
        save_dc = request.data.get('save_dc')
        advantage = request.data.get('advantage', False)
        disadvantage = request.data.get('disadvantage', False)
        
        if not all([participant_id, save_type, save_dc]):
            return Response(
                {"error": "Missing required fields: participant_id, save_type, save_dc"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        ability_mod = participant.get_ability_modifier(save_type)
        proficiency_bonus = participant.character.proficiency_bonus if participant.character else 2
        proficiency = False  # Simplified
        save_total, save_breakdown = calculate_saving_throw(roll, ability_mod, proficiency_bonus, proficiency)
        save_success = save_total >= save_dc
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='other',
            save_type=save_type,
            save_dc=save_dc,
            save_roll=roll,
            save_success=save_success,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{participant.get_name()} makes a {save_type} saving throw"
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
        participant_id = request.data.get('participant_id')
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if participant.current_hp > 0:
            return Response(
                {"error": "Participant is not at 0 HP"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Roll death save manually
        from combat.utils import roll_d20
        roll, _ = roll_d20()
        
        # Natural 20: regain 1 HP and stabilize
        if roll == 20:
            participant.current_hp = 1
            participant.is_active = True
            participant.death_save_successes = 0
            participant.death_save_failures = 0
            participant.save()
            success, stabilized, died, message = True, True, False, "Natural 20! Regained 1 HP and stabilized."
        # Natural 1: two failures
        elif roll == 1:
            participant.death_save_failures += 2
            if participant.death_save_failures >= 3:
                participant.save()
                success, stabilized, died, message = False, False, True, "Natural 1! Two failures. Character dies."
            else:
                participant.save()
                success, stabilized, died, message = False, False, False, f"Natural 1! Two failures. {participant.death_save_failures}/3 failures."
        # Normal roll: 10+ = success, 9- = failure
        elif roll >= 10:
            participant.death_save_successes += 1
            if participant.death_save_successes >= 3:
                participant.death_save_successes = 0
                participant.death_save_failures = 0
                participant.save()
                success, stabilized, died, message = True, True, False, "Death save succeeded. Character stabilizes."
            else:
                participant.save()
                success, stabilized, died, message = True, False, False, f"Death save: {roll} (Success). {participant.death_save_successes}/3 successes."
        else:
            participant.death_save_failures += 1
            if participant.death_save_failures >= 3:
                participant.save()
                success, stabilized, died, message = False, False, True, "Death save failed. Character dies."
            else:
                participant.save()
                success, stabilized, died, message = False, False, False, f"Death save: {roll} (Failure). {participant.death_save_failures}/3 failures."
        
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
            "is_stable": stabilized,
            "is_dead": died,
            "death_save_successes": participant.death_save_successes,
            "death_save_failures": participant.death_save_failures,
            "current_hp": participant.current_hp,
            "action": CombatActionSerializer(action).data
        })
    
    @action(detail=True, methods=['post'])
    def check_concentration(self, request, pk=None):
        """Check concentration"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        damage_amount = request.data.get('damage_amount', 0)
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        broken, save_total, save_dc, message = participant.check_concentration(damage_amount)
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='concentration_check',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=message
        )
        
        return Response({
            "message": message,
            "concentration_broken": broken,
            "save_roll": save_total,
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
        
        attacker_id = request.data.get('attacker_id')
        target_id = request.data.get('target_id')
        
        if not attacker_id or not target_id:
            return Response(
                {"error": "Missing 'attacker_id' or 'target_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attacker = session.participants.get(pk=attacker_id)
            target = session.participants.get(pk=target_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Attacker or target not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if attacker.reaction_used:
            return Response(
                {"error": "Reaction already used this turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get attack details
        attack_name = request.data.get('attack_name', None)
        advantage = request.data.get('advantage', False)
        disadvantage = request.data.get('disadvantage', False)
        
        # Get equipped weapon for characters
        equipped_weapon = None
        damage_string = "1d4"  # Default unarmed
        use_ability = 'STR'  # Default to STR
        
        if attacker.character:
            # Try to get equipped weapon
            equipped_weapon = attacker.get_equipped_weapon('main_hand')
            if equipped_weapon:
                attack_name = attack_name or equipped_weapon.name
                damage_string = equipped_weapon.damage_dice
                
                # Use DEX for finesse weapons, otherwise STR
                if equipped_weapon.finesse:
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                else:
                    use_ability = 'STR'
            else:
                attack_name = attack_name or 'Opportunity Attack'
        elif attacker.encounter_enemy:
            # Try to find enemy attack
            enemy = attacker.encounter_enemy.enemy
            attacks = enemy.attacks.all()
            if attacks.exists():
                enemy_attack = attacks.first()
                attack_name = attack_name or enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        ability_mod = attacker.get_ability_modifier(use_ability)
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
            proficiency = True
        else:
            proficiency_bonus = 2
            proficiency = True
        
        # Get magic item bonuses
        magic_bonuses = attacker.get_magic_item_bonuses()
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, magic_bonuses['to_hit']
        )
        
        # Get target's effective AC
        target_ac = target.calculate_effective_ac()
        
        # Check if hit
        hit = check_hit(attack_total, target_ac)
        critical = (roll == 20)
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        if hit:
            # Add magic item damage bonus
            damage_modifier = ability_mod + magic_bonuses['to_damage']
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, damage_modifier, critical
            )
            new_hp, concentration_broken = target.take_damage(damage_amount)
        
        # Mark reaction as used
        attacker.reaction_used = True
        attacker.save()
        
        # Create combat action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            target=target,
            action_type='opportunity_attack',
            attack_name=attack_name,
            attack_roll=roll,
            attack_modifier=ability_mod + proficiency_bonus + magic_bonuses['to_hit'],
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage_amount if hit else None,
            critical=critical,
            is_opportunity_attack=True,
            is_reaction=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{attacker.get_name()} makes an opportunity attack"
        )
        
        return Response({
            "message": f"{attacker.get_name()} makes an opportunity attack on {target.get_name()}",
            "attack_roll": roll,
            "attack_total": attack_total,
            "target_ac": target_ac,
            "weapon_used": attack_name if equipped_weapon else None,
            "ability_used": use_ability,
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
    def use_reaction(self, request, pk=None):
        """
        Use a reaction (spell, ability, etc.)
        
        Request body:
        {
            "participant_id": 1,
            "reaction_type": "spell",  // or "ability"
            "spell_name": "Shield",  // if reaction_type is "spell"
            "ability_name": "Uncanny Dodge",  // if reaction_type is "ability"
            "target_id": 2,  // optional, for targeted reactions
            "description": "Uses Shield spell to block attack"  // optional
        }
        """
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        reaction_type = request.data.get('reaction_type')  # 'spell' or 'ability'
        
        if not participant_id or not reaction_type:
            return Response(
                {"error": "participant_id and reaction_type are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reaction_type not in ['spell', 'ability']:
            return Response(
                {"error": "reaction_type must be 'spell' or 'ability'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not participant.can_use_reaction():
            return Response(
                {"error": "Reaction already used this round"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target_id = request.data.get('target_id')
        target = None
        if target_id:
            try:
                target = session.participants.get(pk=target_id)
            except CombatParticipant.DoesNotExist:
                return Response(
                    {"error": "Target not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Mark reaction as used
        participant.use_reaction()
        
        # Get reaction details
        if reaction_type == 'spell':
            spell_name = request.data.get('spell_name', 'Unknown Spell')
            description = request.data.get('description', f"{participant.get_name()} casts {spell_name} as a reaction")
        else:
            ability_name = request.data.get('ability_name', 'Unknown Ability')
            description = request.data.get('description', f"{participant.get_name()} uses {ability_name} as a reaction")
        
        # Create reaction action
        action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=target,
            action_type='reaction',
            attack_name=spell_name if reaction_type == 'spell' else ability_name,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=description,
            is_reaction=True
        )
        
        return Response({
            "message": description,
            "reaction_type": reaction_type,
            "participant": participant.get_name(),
            "target": target.get_name() if target else None,
            "reaction_used": True,
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
        action_cost = request.data.get('action_cost', 1)
        action_name = request.data.get('action_name', 'Legendary Action')
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
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
            description=f"{participant.get_name()} uses {action_name}"
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
        
        # Generate combat log
        log = session.generate_log()
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat ended",
            "session": serializer.data,
            "log_id": log.id
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get combat statistics"""
        session = self.get_object()
        log = session.get_or_create_log()
        log.calculate_statistics()
        
        serializer = CombatLogSerializer(log)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Get comprehensive combat report"""
        session = self.get_object()
        report = session.get_combat_report()
        return Response(report)
    
    @action(detail=True, methods=['get', 'post'])
    def environmental_effects(self, request, pk=None):
        """
        Get or add environmental effects to combat session.
        
        GET: List all environmental effects
        POST: Add a new environmental effect
        """
        session = self.get_object()
        
        if request.method == 'GET':
            effects = EnvironmentalEffect.objects.filter(combat_session=session, is_active=True)
            serializer = EnvironmentalEffectSerializer(effects, many=True)
            
            # Get weather (applies to entire combat)
            weather_effect = effects.filter(effect_type='weather').first()
            weather = weather_effect.weather_type if weather_effect else None
            
            # Get summary
            summary = get_environmental_effects_summary(
                terrain=None,
                cover=None,
                lighting=None,
                weather=weather,
                hazards=None
            )
            
            return Response({
                'environmental_effects': serializer.data,
                'summary': summary
            })
        
        elif request.method == 'POST':
            # Create new environmental effect
            effect_type = request.data.get('effect_type')
            
            if not effect_type:
                return Response(
                    {"error": "effect_type is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            effect_data = {
                'combat_session': session.id,
                'effect_type': effect_type,
                'description': request.data.get('description', ''),
            }
            
            # Set type-specific fields
            if effect_type == 'terrain':
                effect_data['terrain_type'] = request.data.get('terrain_type')
            elif effect_type == 'cover':
                effect_data['cover_type'] = request.data.get('cover_type')
                effect_data['cover_area_x'] = request.data.get('cover_area_x')
                effect_data['cover_area_y'] = request.data.get('cover_area_y')
                effect_data['cover_area_radius'] = request.data.get('cover_area_radius')
            elif effect_type == 'lighting':
                effect_data['lighting_type'] = request.data.get('lighting_type')
                effect_data['lighting_area_x'] = request.data.get('lighting_area_x')
                effect_data['lighting_area_y'] = request.data.get('lighting_area_y')
                effect_data['lighting_area_radius'] = request.data.get('lighting_area_radius')
            elif effect_type == 'weather':
                effect_data['weather_type'] = request.data.get('weather_type')
            elif effect_type == 'hazard':
                effect_data['hazard_type'] = request.data.get('hazard_type')
                effect_data['hazard_area_x'] = request.data.get('hazard_area_x')
                effect_data['hazard_area_y'] = request.data.get('hazard_area_y')
                effect_data['hazard_area_radius'] = request.data.get('hazard_area_radius')
            
            serializer = EnvironmentalEffectSerializer(data=effect_data)
            if serializer.is_valid():
                effect = serializer.save()
                return Response({
                    "message": f"Environmental effect added: {effect.get_effect_type_display()}",
                    "effect": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def set_participant_position(self, request, pk=None):
        """Set or update participant position"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        x = request.data.get('x', 0)
        y = request.data.get('y', 0)
        z = request.data.get('z', 0)
        
        if not participant_id:
            return Response(
                {"error": "participant_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create position
        position, created = ParticipantPosition.objects.get_or_create(
            participant=participant,
            defaults={'x': x, 'y': y, 'z': z}
        )
        
        if not created:
            position.x = x
            position.y = y
            position.z = z
            position.save()
        
        # Update environmental effects at this position
        self._update_position_environmental_effects(position, session)
        
        serializer = ParticipantPositionSerializer(position)
        return Response({
            "message": f"Position updated for {participant.get_name()}",
            "position": serializer.data
        })
    
    def _update_position_environmental_effects(self, position, session):
        """Update environmental effects at participant's position"""
        # Check for terrain
        terrain_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='terrain',
            is_active=True
        )
        if terrain_effects.exists():
            position.current_terrain = terrain_effects.first().terrain_type
        
        # Check for cover
        cover_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='cover',
            is_active=True
        )
        for cover_effect in cover_effects:
            if cover_effect.cover_area_x and cover_effect.cover_area_y and cover_effect.cover_area_radius:
                if position.is_in_area(cover_effect.cover_area_x, cover_effect.cover_area_y, cover_effect.cover_area_radius):
                    position.current_cover = cover_effect.cover_type
                    break
        
        # Check for lighting
        lighting_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='lighting',
            is_active=True
        )
        for lighting_effect in lighting_effects:
            if lighting_effect.lighting_area_x and lighting_effect.lighting_area_y and lighting_effect.lighting_area_radius:
                if position.is_in_area(lighting_effect.lighting_area_x, lighting_effect.lighting_area_y, lighting_effect.lighting_area_radius):
                    position.current_lighting = lighting_effect.lighting_type
                    break
        
        # Check for hazards
        hazard_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='hazard',
            is_active=True
        )
        hazards = []
        for hazard_effect in hazard_effects:
            if hazard_effect.hazard_area_x and hazard_effect.hazard_area_y and hazard_effect.hazard_area_radius:
                if position.is_in_area(hazard_effect.hazard_area_x, hazard_effect.hazard_area_y, hazard_effect.hazard_area_radius):
                    hazards.append(hazard_effect.hazard_type)
        position.current_hazards = hazards
        
        position.save()
    
    @action(detail=False, methods=['post'])
    def practice_mode(self, request):
        """
        Create a practice combat session quickly.
        
        Request body:
        {
            "name": "Practice Combat",  // Optional name
            "character_ids": [1, 2, 3],  // List of character IDs
            "enemies": [  // List of enemies
                {"enemy_id": 1, "name": "Goblin 1", "hp": 7},
                {"enemy_id": 1, "name": "Goblin 2", "hp": 7}
            ]
        }
        """
        from bestiary.models import Enemy
        
        name = request.data.get('name', 'Practice Combat')
        character_ids = request.data.get('character_ids', [])
        enemies = request.data.get('enemies', [])
        
        # Create practice session
        session = CombatSession.objects.create(
            encounter=None,
            is_practice=True,
            status='preparing',
            notes=f"Practice session: {name}"
        )
        
        added_characters = []
        added_enemies = []
        
        # Add characters
        for char_id in character_ids:
            try:
                character = Character.objects.get(pk=char_id)
                if not hasattr(character, 'stats'):
                    continue
                
                stats = character.stats
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='character',
                    character=character,
                    initiative=0,
                    current_hp=stats.hit_points,
                    max_hp=stats.max_hit_points,
                    armor_class=stats.armor_class
                )
                session.participants.add(participant)
                added_characters.append({
                    'id': character.id,
                    'name': character.name,
                    'participant_id': participant.id
                })
            except Character.DoesNotExist:
                continue
        
        # Add enemies
        for enemy_data in enemies:
            enemy_id = enemy_data.get('enemy_id')
            enemy_name = enemy_data.get('name', 'Enemy')
            enemy_hp = enemy_data.get('hp')
            
            if not enemy_id:
                continue
            
            try:
                enemy = Enemy.objects.get(pk=enemy_id)
                if not hasattr(enemy, 'stats'):
                    continue
                
                hp = enemy_hp if enemy_hp is not None else enemy.stats.hit_points
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=None,
                    initiative=0,
                    current_hp=hp,
                    max_hp=enemy.stats.hit_points,
                    armor_class=enemy.stats.armor_class
                )
                session.participants.add(participant)
                added_enemies.append({
                    'id': enemy.id,
                    'name': enemy_name,
                    'participant_id': participant.id
                })
            except Enemy.DoesNotExist:
                continue
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"Practice combat session created: {name}",
            "session": serializer.data,
            "characters_added": added_characters,
            "enemies_added": added_enemies,
            "next_steps": [
                "1. Roll initiative: POST /api/combat/sessions/{id}/roll_initiative/",
                "2. Start combat: POST /api/combat/sessions/{id}/start/",
                "3. Make attacks: POST /api/combat/sessions/{id}/attack/"
            ]
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export combat log in various formats"""
        session = self.get_object()
        format_type = request.query_params.get('format', 'json').lower()
        
        if format_type == 'json':
            report = session.get_combat_report()
            return Response(report)
        
        elif format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            log = session.get_or_create_log()
            log.calculate_statistics()
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="combat_{session.id}.csv"'
            
            writer = csv.writer(response)
            # Write header
            writer.writerow(['Round', 'Turn', 'Timestamp', 'Actor', 'Action Type', 'Target', 'Hit', 'Damage', 'Critical'])
            
            # Write actions
            for action in session.actions.all().order_by('round_number', 'turn_number', 'created_at'):
                writer.writerow([
                    action.round_number,
                    action.turn_number,
                    action.created_at.isoformat(),
                    action.actor.get_name(),
                    action.get_action_type_display(),
                    action.target.get_name() if action.target else '',
                    'Yes' if action.hit else 'No' if action.hit is not None else '',
                    action.damage_amount or 0,
                    'Yes' if action.critical else 'No',
                ])
            
            return response
        
        else:
            return Response(
                {"error": f"Unsupported format: {format_type}. Supported: json, csv"},
                status=status.HTTP_400_BAD_REQUEST
            )


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
        response_data = {
            "message": f"{participant.get_name()} took {amount} damage",
            "current_hp": new_hp,
            "participant": serializer.data
        }
        if concentration_broken:
            response_data["concentration_broken"] = True
            response_data["concentration_message"] = f"Lost concentration on {participant.concentration_spell}"
        return Response(response_data)
    
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
    def move(self, request, pk=None):
        """
        Move a participant, considering difficult terrain.
        
        Request body:
        {
            "distance": 30,  // Distance to move in feet
            "x": 10,  // Optional: new X position
            "y": 10,  // Optional: new Y position
            "z": 0   // Optional: new Z position
        }
        """
        participant = self.get_object()
        session = participant.combat_session
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distance = request.data.get('distance', 0)
        x = request.data.get('x')
        y = request.data.get('y')
        z = request.data.get('z', 0)
        
        # Get participant's base speed
        base_speed = 30  # Default
        if participant.character and hasattr(participant.character, 'stats'):
            base_speed = participant.character.stats.speed or 30
        
        # Get current position
        try:
            position = participant.position
        except ParticipantPosition.DoesNotExist:
            position = ParticipantPosition.objects.create(
                participant=participant,
                x=x or 0,
                y=y or 0,
                z=z or 0
            )
        
        # Calculate movement cost considering terrain
        terrain_type = position.current_terrain
        weather_effect = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='weather',
            is_active=True
        ).first()
        weather = weather_effect.weather_type if weather_effect else None
        
        effective_movement, cost_multiplier = calculate_movement_cost(
            base_speed,
            terrain_type=terrain_type,
            weather=weather
        )
        
        # Calculate actual movement cost
        movement_cost = int(distance * cost_multiplier)
        
        # Check if participant has enough movement
        movement_remaining = effective_movement - participant.movement_used
        if movement_cost > movement_remaining:
            return Response(
                {"error": f"Not enough movement. Need {movement_cost} feet, have {movement_remaining} feet remaining"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update position if provided
        if x is not None and y is not None:
            position.x = x
            position.y = y
            position.z = z
            # Update environmental effects at new position
            session_viewset = CombatSessionViewSet()
            session_viewset._update_position_environmental_effects(position, session)
            position.save()
        
        # Update movement used
        participant.movement_used += movement_cost
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} moved {distance} feet (cost: {movement_cost} feet)",
            "movement_used": participant.movement_used,
            "movement_remaining": effective_movement - participant.movement_used,
            "terrain_multiplier": cost_multiplier,
            "position": ParticipantPositionSerializer(position).data if hasattr(position, 'id') else None,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def apply_hazard_damage(self, request, pk=None):
        """
        Apply damage from hazards at participant's position.
        Called automatically at start of turn if in hazard area.
        """
        participant = self.get_object()
        
        try:
            position = participant.position
        except ParticipantPosition.DoesNotExist:
            return Response(
                {"error": "Participant has no position"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not position.current_hazards:
            return Response(
                {"error": "Participant is not in any hazard area"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = participant.combat_session
        hazards_applied = []
        
        for hazard_type in position.current_hazards:
            from .environmental_effects import calculate_hazard_damage
            damage_dice, damage_type_name, save_type, save_dc, condition = calculate_hazard_damage(hazard_type)
            
            if not damage_dice:
                continue
            
            # Roll damage
            from .utils import calculate_damage, roll_d20, calculate_saving_throw
            damage_amount, damage_breakdown = calculate_damage(damage_dice, 0, False)
            
            # Make saving throw if applicable
            if save_type and save_dc:
                save_roll, _ = roll_d20()
                ability_mod = participant.get_ability_modifier(save_type)
                proficiency_bonus = participant.character.proficiency_bonus if participant.character else 2
                save_total, _ = calculate_saving_throw(save_roll, ability_mod, proficiency_bonus, False)
                
                if save_total >= save_dc:
                    damage_amount = damage_amount // 2  # Half damage on successful save
            
            # Apply damage
            new_hp, _ = participant.take_damage(damage_amount)
            
            # Apply condition if applicable
            if condition:
                from bestiary.models import Condition
                try:
                    cond = Condition.objects.get(name=condition)
                    participant.conditions.add(cond)
                except Condition.DoesNotExist:
                    pass
            
            hazards_applied.append({
                'hazard_type': hazard_type,
                'damage': damage_amount,
                'damage_type': damage_type_name,
                'save_success': save_total >= save_dc if save_type else None,
            })
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} took damage from hazards",
            "hazards_applied": hazards_applied,
            "current_hp": participant.current_hp,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def reset_turn(self, request, pk=None):
        """Reset turn resources for a participant"""
        participant = self.get_object()
        participant.reset_turn()
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()}'s turn reset",
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
        
        # Create condition application record
        session = participant.combat_session
        ConditionApplication.objects.create(
            participant=participant,
            condition=condition,
            applied_round=session.current_round,
            applied_turn=session.current_turn_index,
            duration_type=request.data.get('duration_type', 'instant'),
            duration_rounds=request.data.get('duration_rounds', 0),
            expires_at_round=request.data.get('expires_at_round'),
            source_type=request.data.get('source_type', 'manual'),
            source_name=request.data.get('source_name', ''),
        )
        
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


class CombatLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing combat logs"""
    queryset = CombatLog.objects.all()
    serializer_class = CombatLogSerializer
    
    def get_queryset(self):
        queryset = CombatLog.objects.all()
        session_id = self.request.query_params.get('session', None)
        is_public = self.request.query_params.get('public', None)
        
        if session_id:
            queryset = queryset.filter(combat_session_id=session_id)
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get detailed analytics for a combat log"""
        log = self.get_object()
        log.calculate_statistics()
        
        # Calculate additional metrics
        analytics = {
            'log_id': log.id,
            'session_id': log.combat_session.id,
            'encounter_name': log.combat_session.encounter.name,
            'duration': {
                'seconds': log.duration_seconds,
                'formatted': log.combat_session._format_duration(log.duration_seconds),
                'rounds': log.total_rounds,
                'turns': log.total_turns,
                'average_turns_per_round': round(log.total_turns / log.total_rounds, 2) if log.total_rounds > 0 else 0,
            },
            'damage_analysis': {
                'total_dealt': log.total_damage_dealt,
                'total_received': log.total_damage_received,
                'net_damage': log.total_damage_dealt - log.total_damage_received,
                'by_type': log.damage_by_type,
                'average_per_turn': round(log.total_damage_dealt / log.total_turns, 2) if log.total_turns > 0 else 0,
            },
            'action_analysis': {
                'total_actions': log.total_turns,
                'by_type': log.actions_by_type,
                'most_common_action': max(log.actions_by_type.items(), key=lambda x: x[1])[0] if log.actions_by_type else None,
            },
            'spell_analysis': {
                'total_spells_cast': sum(log.spells_cast.values()),
                'spells_by_name': log.spells_cast,
                'most_used_spell': max(log.spells_cast.items(), key=lambda x: x[1])[0] if log.spells_cast else None,
            },
            'participant_performance': {
                pid: {
                    'name': stats['name'],
                    'damage_dealt': stats['damage_dealt'],
                    'damage_received': stats['damage_received'],
                    'attacks_made': stats['attacks_made'],
                    'hit_rate': round((stats['attacks_hit'] / stats['attacks_made'] * 100), 2) if stats['attacks_made'] > 0 else 0,
                    'critical_hit_rate': round((stats['critical_hits'] / stats['attacks_made'] * 100), 2) if stats['attacks_made'] > 0 else 0,
                    'hp_change': stats['end_hp'] - stats['start_hp'],
                    'status': stats['status'],
                }
                for pid, stats in log.participant_stats.items()
            },
            'outcomes': {
                'victors': len(log.victors),
                'casualties': len(log.casualties),
                'victor_names': [log.participant_stats.get(pid, {}).get('name', 'Unknown') for pid in log.victors],
                'casualty_names': [log.participant_stats.get(pid, {}).get('name', 'Unknown') for pid in log.casualties],
            },
        }
        
        return Response(analytics)
