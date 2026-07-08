"""
Combat Action Views - Core combat action endpoints.

Contains the CombatActionMixin with attack, cast_spell, and saving_throw actions.
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging

from combat.models import CombatParticipant, CombatAction, ConditionApplication, EnvironmentalEffect, ParticipantPosition
from combat.condition_effects import auto_apply_condition_from_spell
from combat.environmental_effects import (
    calculate_cover_ac_bonus, has_full_cover,
    get_lighting_attack_modifier, get_weather_ranged_modifier,
)
from combat.serializers import (
    CombatActionSerializer, AttackRequestSerializer, SpellRequestSerializer,
)
from combat.utils import (
    roll_d20, calculate_attack_roll, calculate_damage, check_hit,
    calculate_saving_throw
)

logger = logging.getLogger('combat')


class CombatActionMixin:
    """Mixin providing core combat actions: attack, cast_spell, saving_throw."""

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
        
        # Check if attacker has attacks remaining this turn
        if attacker.attacks_remaining <= 0:
            return Response(
                {"error": f"{attacker.get_name()} has no attacks remaining this turn"},
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
        
        # Resolve enemy model (either from encounter or by name for practice mode)
        resolved_enemy = None
        if attacker.encounter_enemy:
            resolved_enemy = attacker.encounter_enemy.enemy
        elif attacker.participant_type == 'enemy' and attacker.name:
            from bestiary.models import Enemy as EnemyModel
            resolved_enemy = EnemyModel.objects.filter(name=attacker.name).first()
        
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
        elif resolved_enemy:
            # Try to find enemy attack — match by name if provided, else use best
            attacks = resolved_enemy.attacks.all()
            if attacks.exists():
                if attack_name:
                    enemy_attack = attacks.filter(name__iexact=attack_name).first() or attacks.first()
                else:
                    enemy_attack = attacks.first()
                attack_name = attack_name or enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        ability_mod = attacker.get_ability_modifier(use_ability)
        damage_ability_mod = ability_mod  # Separate tracker for damage (may differ from attack bonus for enemies)
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
            # Check weapon proficiency (simplified - check if character has weapon proficiency)
            proficiency = True  # TODO: Check actual weapon proficiency
        elif resolved_enemy:
            # Use enemy's actual attack bonus directly (includes prof + ability mod)
            enemy_atk = resolved_enemy.attacks.filter(name__iexact=attack_name).first() if attack_name else resolved_enemy.attacks.first()
            if enemy_atk:
                # EnemyAttack.bonus already includes proficiency + ability modifier
                # Keep damage_ability_mod as the raw ability modifier for damage calculation
                damage_ability_mod = ability_mod
                ability_mod = enemy_atk.bonus
                proficiency_bonus = 0
                proficiency = False
            else:
                try:
                    proficiency_bonus = resolved_enemy.stats.proficiency_bonus or 2
                except Exception:
                    proficiency_bonus = 2
                proficiency = True
        else:
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
            damage_modifier = damage_ability_mod + magic_bonuses['to_damage']
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, damage_modifier, critical
            )
            new_hp, concentration_broken = target.take_damage(damage_amount)
        
        # Create combat action
        combat_action = CombatAction.objects.create(
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
        
        # Decrement attacks remaining
        attacker.attacks_remaining -= 1
        if attacker.attacks_remaining <= 0:
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
            "attacks_remaining": attacker.attacks_remaining,
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
            "action": CombatActionSerializer(combat_action).data
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
        data.get('damage_type')
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
        
        # Validate spell slots for player characters
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
        
        # Validate spell slots for enemies
        if caster.encounter_enemy:
            if not caster.can_cast_enemy_spell(spell_name):
                return Response(
                    {"error": f"{caster.get_name()} has no spell slots remaining for {spell_name}"},
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
        combat_action = CombatAction.objects.create(
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
        
        # Decrement enemy spell slots
        if caster.encounter_enemy:
            caster.use_enemy_spell(spell_name)
        
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
            "action": CombatActionSerializer(combat_action).data
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
        
        save_dc = int(save_dc)
        
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
        combat_action = CombatAction.objects.create(
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
            "action": CombatActionSerializer(combat_action).data
        })
