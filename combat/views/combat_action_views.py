"""
Combat Action Views - Core combat action endpoints.

Contains the CombatActionMixin with attack, cast_spell, and saving_throw actions.
"""
import logging
import random

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from combat.condition_effects import auto_apply_condition_from_spell
from combat.environmental_effects import (
    calculate_cover_ac_bonus,
    get_lighting_attack_modifier,
    get_weather_ranged_modifier,
    has_full_cover,
)
from combat.models import (
    CombatAction,
    CombatParticipant,
    ConditionApplication,
    EnvironmentalEffect,
    ParticipantPosition,
)
from combat.serializers import (
    AttackRequestSerializer,
    CombatActionSerializer,
    SpellRequestSerializer,
)
from combat.utils import calculate_attack_roll, calculate_damage, calculate_saving_throw, check_hit, roll_d20

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

        if attacker.is_incapacitated():
            return Response(
                {"error": f"{attacker.get_name()} is {attacker.get_incapacitating_condition()} and cannot take actions."},
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
        
        # Sane defaults in case modifiers are not set
        ability_mod = attacker.get_ability_modifier('STR')
        damage_ability_mod = ability_mod
        proficiency_bonus = 2
        proficiency = True

        # Resolve enemy model (either from encounter or by name for practice mode)
        resolved_enemy = None
        if attacker.encounter_enemy:
            resolved_enemy = attacker.encounter_enemy.enemy
        elif attacker.participant_type == 'enemy' and attacker.name:
            from bestiary.models import Enemy as EnemyModel
            resolved_enemy = EnemyModel.objects.filter(name=attacker.name).first()
        
        matched_action = None
        if attacker.character:
            # Try to get equipped weapon
            equipped_weapon = attacker.get_equipped_weapon(weapon_slot)
            if equipped_weapon:
                attack_name = attack_name or equipped_weapon.name
                damage_string = equipped_weapon.damage_dice
                
                # Check weapon type: ranged weapons use DEX, finesse can use DEX or STR
                if getattr(equipped_weapon, 'weapon_type', None) in ['simple_ranged', 'martial_ranged']:
                    use_ability = 'DEX'
                elif getattr(equipped_weapon, 'finesse', False):
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                else:
                    use_ability = 'STR'
            else:
                attack_name = attack_name or 'Unarmed Strike'
                damage_string = "1d4"
                use_ability = 'STR'

            ability_mod = attacker.get_ability_modifier(use_ability)
            damage_ability_mod = ability_mod
            proficiency_bonus = attacker.character.proficiency_bonus or 2
            proficiency = True
        elif resolved_enemy:
            # Check for EnemyAction
            if attack_name:
                matched_action = resolved_enemy.actions.filter(name__iexact=attack_name).first()
                if not matched_action:
                    matched_action = resolved_enemy.actions.filter(name__icontains=attack_name.split()[0]).first()

            # Check Pack Tactics
            if attacker.has_trait('pack_tactics'):
                ally_count = session.participants.filter(
                    participant_type='enemy',
                    is_active=True,
                    current_hp__gt=0,
                ).exclude(id=attacker.id).count()
                if ally_count > 0:
                    advantage = True

            # Handle Saving Throw actions (e.g. Fire Breath)
            if matched_action and matched_action.attack_type == 'saving_throw':
                if matched_action.has_recharge:
                    is_ready = attacker.recharge_state.get(matched_action.name, True)
                    if not is_ready:
                        return Response(
                            {"error": f"{matched_action.name} is still recharging and cannot be used."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                save_ability = matched_action.saving_throw_ability or 'DEX'
                save_dc = matched_action.saving_throw_dc or 15
                save_mod = target.get_ability_modifier(save_ability)

                from combat.condition_effects import is_auto_fail_save
                if is_auto_fail_save(target, save_ability):
                    saved = False
                    s_roll = 1
                    s_total = s_roll + save_mod
                    s_breakdown = f"Auto-fail ({target.get_incapacitating_condition()})"
                else:
                    s_roll, s_breakdown = roll_d20()
                    s_total = s_roll + save_mod
                    saved = (s_total >= save_dc)

                # Roll damage
                damage_amount = 0
                dmg_rolls = list(matched_action.damage_rolls.all())
                if dmg_rolls:
                    for d in dmg_rolls:
                        roll_sum = sum(random.randint(1, d.dice_sides) for _ in range(d.dice_count)) + d.damage_bonus
                        damage_amount += max(0, roll_sum)
                else:
                    damage_amount, _ = calculate_damage(damage_string, 0, False)

                if saved and matched_action.half_damage_on_save:
                    damage_amount = damage_amount // 2
                elif saved:
                    damage_amount = 0

                _new_hp, concentration_broken = target.take_damage(damage_amount)

                cond_applied = None
                if not saved and matched_action.conditions_inflicted.exists():
                    for c in matched_action.conditions_inflicted.all():
                        target.conditions.add(c)
                        cond_applied = c.name

                if matched_action.has_recharge:
                    attacker.recharge_state[matched_action.name] = False
                    attacker.save(update_fields=['recharge_state'])

                attacker.attacks_remaining -= 1
                if attacker.attacks_remaining <= 0:
                    attacker.action_used = True
                attacker.save()

                save_desc = f"{target.get_name()} rolled {s_breakdown} + {save_mod} = {s_total} vs DC {save_dc} {save_ability} save ({'SUCCESS' if saved else 'FAILED'}). Took {damage_amount} damage."
                if cond_applied:
                    save_desc += f" Inflicted {cond_applied}!"

                CombatAction.objects.create(
                    combat_session=session,
                    actor=attacker,
                    target=target,
                    action_type='attack',
                    attack_name=matched_action.name,
                    attack_roll=s_roll,
                    attack_modifier=save_mod,
                    attack_total=s_total,
                    hit=not saved,
                    damage_amount=damage_amount,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=save_desc,
                )

                return Response({
                    "message": f"{attacker.get_name()} uses {matched_action.name} against {target.get_name()}",
                    "saving_throw": {
                        "ability": save_ability,
                        "dc": save_dc,
                        "roll": s_roll,
                        "total": s_total,
                        "saved": saved,
                    },
                    "hit": not saved,
                    "damage": damage_amount,
                    "target_hp": target.current_hp,
                    "attacks_remaining": attacker.attacks_remaining,
                    "concentration_broken": concentration_broken,
                    "condition_applied": cond_applied,
                    "breakdown": {"save": save_desc},
                })

            # Try to find enemy action or attack
            if matched_action:
                attack_name = matched_action.name
                if matched_action.attack_bonus is not None:
                    ability_mod = matched_action.attack_bonus
                    proficiency_bonus = 0
                    proficiency = False
                else:
                    ability_mod = attacker.get_ability_modifier('STR')
                    proficiency_bonus = 2
                    proficiency = True
                damage_ability_mod = 0
            else:
                valid_attacks = resolved_enemy.attacks.exclude(name__icontains='multiattack')
                if valid_attacks.exists():
                    enemy_atk = valid_attacks.filter(name__iexact=attack_name).first() if attack_name else valid_attacks.first()
                    if not enemy_atk:
                        enemy_atk = valid_attacks.first()
                    attack_name = enemy_atk.name
                    damage_string = enemy_atk.damage
                    ability_mod = enemy_atk.bonus
                    proficiency_bonus = 0
                    proficiency = False
                    has_mod = bool(re.search(r'[+-]\s*\d+', damage_string))
                    damage_ability_mod = 0 if has_mod else attacker.get_ability_modifier('STR')
                else:
                    attack_name = attack_name or "Slam"
                    ability_mod = attacker.get_ability_modifier('STR')
                    proficiency_bonus = 2
                    proficiency = True
                    damage_ability_mod = ability_mod
                    damage_string = "1d6"
        
        # Determine melee vs ranged
        is_melee = True
        if equipped_weapon and getattr(equipped_weapon, 'range_normal', 0) > 5:
            is_melee = False
        elif matched_action and getattr(matched_action, 'attack_type', '') == 'ranged_weapon':
            is_melee = False

        # Check cover before rolling
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

        from combat.condition_effects import evaluate_attack_roll_conditions, is_auto_critical
        cond_adv, cond_disadv, _ = evaluate_attack_roll_conditions(attacker, target, is_melee=is_melee)
        if cond_adv:
            advantage = True
        if cond_disadv:
            disadvantage = True

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
                    disadvantage = True
                elif lighting_mod == 'advantage':
                    advantage = True
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
            if not is_melee:
                if weather_mod == 'disadvantage':
                    disadvantage = True
                elif weather_mod == 'advantage':
                    advantage = True

        # 5e Advantage / Disadvantage resolution: if both are present, they cancel out
        final_advantage = bool(advantage and not disadvantage)
        final_disadvantage = bool(disadvantage and not advantage)

        # Roll attack with resolved advantage/disadvantage
        roll, roll_breakdown = roll_d20(advantage=final_advantage, disadvantage=final_disadvantage)
        
        # Get magic item bonuses
        magic_bonuses = attacker.get_magic_item_bonuses()
        other_modifiers += magic_bonuses['to_hit']
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Get target's effective AC (including armor, magic items, and cover)
        target_ac = target.calculate_effective_ac(cover_bonus=cover_bonus)
        
        # Check if hit
        hit = check_hit(attack_total, target_ac)
        critical = (roll == 20)  # Natural 20 is critical
        if hit and is_auto_critical(attacker, target, is_melee=is_melee):
            critical = True
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        if hit:
            if matched_action and matched_action.damage_rolls.exists():
                total_dmg = 0
                dmg_parts = []
                for d in matched_action.damage_rolls.all():
                    n_dice = d.dice_count * (2 if critical else 1)
                    rolls = [random.randint(1, d.dice_sides) for _ in range(n_dice)]
                    subtotal = sum(rolls) + d.damage_bonus
                    total_dmg += max(0, subtotal)
                    dt_name = f" {d.damage_type.name}" if d.damage_type else ""
                    rolls_str = ', '.join(map(str, rolls))
                    dmg_parts.append(f"{rolls_str} + {d.damage_bonus} = {subtotal}{dt_name}")
                damage_amount = max(1, total_dmg)
                damage_breakdown = " | ".join(dmg_parts)
            else:
                damage_modifier = damage_ability_mod + magic_bonuses['to_damage']
                damage_amount, damage_breakdown = calculate_damage(
                    damage_string, damage_modifier, critical
                )

            _new_hp, concentration_broken = target.take_damage(damage_amount)

            # Check condition riders on hit (e.g. Wolf bite knock prone)
            if matched_action and matched_action.saving_throw_dc and matched_action.conditions_inflicted.exists():
                rider_ability = matched_action.saving_throw_ability or 'STR'
                rider_dc = matched_action.saving_throw_dc
                t_mod = target.get_ability_modifier(rider_ability)
                r_roll, r_breakdown = roll_d20()
                if (r_roll + t_mod) < rider_dc:
                    cond_names = []
                    for c in matched_action.conditions_inflicted.all():
                        target.conditions.add(c)
                        cond_names.append(c.name)
                    if cond_names:
                        damage_breakdown += f" | Inflicted {', '.join(cond_names)} (failed DC {rider_dc} {rider_ability} save: {r_breakdown}+{t_mod})"

            # Lock recharge if applicable
            if matched_action and matched_action.has_recharge:
                attacker.recharge_state[matched_action.name] = False
                attacker.save(update_fields=['recharge_state'])
        
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
            is_advantage=final_advantage,
            is_disadvantage=final_disadvantage,
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
            "is_advantage": final_advantage,
            "is_disadvantage": final_disadvantage,
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
        is_healing = data.get('is_healing', False)
        is_ritual = data.get('is_ritual', False) or request.data.get('is_ritual', False)
        requires_concentration = data.get('requires_concentration', False) or request.data.get('requires_concentration', False)
        
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

        if caster.is_incapacitated():
            return Response(
                {"error": f"{caster.get_name()} is {caster.get_incapacitating_condition()} and cannot take actions."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if it's caster's turn
        current = session.get_current_participant()
        if current != caster:
            return Response(
                {"error": f"It is not {caster.get_name()}'s turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if caster has action remaining this turn
        if caster.action_used or caster.attacks_remaining <= 0:
            return Response(
                {"error": f"{caster.get_name()} has already used their action this turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate spell slots for player characters
        if caster.character:
            from characters.spell_management import can_cast_spell
            
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

            # Check remaining spell slots
            if spell_level and spell_level > 0 and not is_ritual and hasattr(caster.character, 'stats') and caster.character.stats:
                stats = caster.character.stats
                level_str = str(spell_level)
                if stats.spell_slots and isinstance(stats.spell_slots, dict):
                    max_slots = int(stats.spell_slots.get(level_str, 0))
                    if max_slots > 0:
                        expended = int((stats.expended_spell_slots or {}).get(level_str, 0))
                        if expended >= max_slots:
                            return Response(
                                {"error": f"{caster.get_name()} has no level {spell_level} spell slots remaining."},
                                status=status.HTTP_400_BAD_REQUEST
                            )
        
        # Validate spell slots for enemies
        if caster.encounter_enemy and not caster.can_cast_enemy_spell(spell_name):
            return Response(
                {"error": f"{caster.get_name()} has no spell slots remaining for {spell_name}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target = None
        if target_id:
            if target_id == caster.id:
                target = caster
            else:
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
            caster.save(update_fields=['is_concentrating', 'concentration_spell'])
        
        # Handle saving throw and spell effects
        save_roll = None
        save_total = None
        save_success = None
        damage_amount = 0
        healing_amount = 0
        
        # Determine if this is a healing spell
        healing_spell_names = {'cure wounds', 'healing word', 'prayer of healing', 'mass cure wounds', 'heal', 'mass heal'}
        if is_healing or spell_name.strip().lower() in healing_spell_names:
            is_healing = True
            if damage_string and target:
                base_heal, _ = calculate_damage(damage_string, 0, False)
                healing_amount = max(1, base_heal)
                target.heal(healing_amount)
        elif save_type and save_dc and target:
            save_roll, _save_breakdown = roll_d20()
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
                    _new_hp, _ = target.take_damage(damage_amount)
        elif damage_string and target:
            base_damage, _ = calculate_damage(damage_string, 0, False)
            damage_amount = base_damage
            if damage_amount > 0:
                _new_hp, _ = target.take_damage(damage_amount)
        
        # Auto-apply conditions from spell (if not healing, and save failed or no save)
        applied_condition = None
        if not is_healing and target and (save_success is False or not save_type):
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
        
        # Action description
        if is_healing and target:
            desc = f"{caster.get_name()} casts {spell_name} on {target.get_name()}, restoring {healing_amount} HP"
        elif damage_amount > 0 and target:
            desc = f"{caster.get_name()} casts {spell_name} on {target.get_name()} for {damage_amount} damage"
        elif target:
            desc = f"{caster.get_name()} casts {spell_name} on {target.get_name()}"
        else:
            desc = f"{caster.get_name()} casts {spell_name}"

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
            description=desc
        )
        
        # Mark action as used and consume turn action
        caster.action_used = True
        caster.attacks_remaining = 0
        caster.save(update_fields=['action_used', 'attacks_remaining'])

        
        # Decrement player character spell slots
        if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
            if spell_level and spell_level > 0 and not is_ritual:
                stats = caster.character.stats
                if not stats.expended_spell_slots or not isinstance(stats.expended_spell_slots, dict):
                    stats.expended_spell_slots = {}
                level_str = str(spell_level)
                current_used = stats.expended_spell_slots.get(level_str, 0)
                stats.expended_spell_slots[level_str] = current_used + 1
                stats.save(update_fields=['expended_spell_slots'])

        # Decrement enemy spell slots
        if caster.encounter_enemy:
            caster.use_enemy_spell(spell_name)
        
        return Response({
            "message": desc,
            "spell_name": spell_name,
            "spell_level": spell_level,
            "target": target.get_name() if target else None,
            "target_id": target.id if target else None,
            "target_hp": target.current_hp if target else None,
            "is_healing": is_healing,
            "healing_amount": healing_amount,
            "save_type": save_type if save_type else None,
            "save_dc": save_dc,
            "save_roll": save_roll,
            "save_total": save_total,
            "save_success": save_success,
            "damage": damage_amount,
            "condition_applied": applied_condition.name if applied_condition else None,
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

    @action(detail=True, methods=['post'])
    def use_item(self, request, pk=None):
        """
        Use an item/consumable in combat (e.g. Potion of Healing).
        Standard 5e: Consumes Action, heals drinker or target ally.
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active"}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        target_id = request.data.get('target_id')
        item_name = request.data.get('item_name', 'Potion of Healing')
        
        try:
            user_part = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if user_part.action_used or user_part.attacks_remaining <= 0:
            return Response({"error": f"{user_part.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Target defaults to self
        if not target_id or int(target_id) == user_part.id:
            target = user_part
        else:
            try:
                target = session.participants.get(id=target_id)
            except CombatParticipant.DoesNotExist:
                target = user_part
        
        # Validate target
        if target.participant_type == 'enemy':
            return Response({"error": "Cannot use beneficial supplies on a hostile enemy."}, status=status.HTTP_400_BAD_REQUEST)
        if target.current_hp <= 0 and target.death_save_failures >= 3:
            return Response({"error": "Target is deceased. Simple potions cannot revive the dead."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Roll healing based on potion type (Standard 5e formulas)
        lower_name = item_name.lower()
        if 'supreme' in lower_name:
            heal_amount = sum(random.randint(1, 4) for _ in range(10)) + 20
        elif 'superior' in lower_name:
            heal_amount = sum(random.randint(1, 4) for _ in range(8)) + 8
        elif 'greater' in lower_name:
            heal_amount = sum(random.randint(1, 4) for _ in range(4)) + 4
        else:
            # Standard Potion of Healing: 2d4 + 2
            heal_amount = random.randint(1, 4) + random.randint(1, 4) + 2
            
        old_hp = target.current_hp
        target.heal(heal_amount)
        actual_healed = target.current_hp - old_hp
        
        # Consume Action
        user_part.action_used = True
        user_part.attacks_remaining = 0
        user_part.save(update_fields=['action_used', 'attacks_remaining'])
        
        # Consume from inventory if character owns this item
        if user_part.character:
            ci = user_part.character.character_items.filter(item__name__icontains='potion').first()
            if ci:
                if ci.quantity > 1:
                    ci.quantity -= 1
                    ci.save(update_fields=['quantity'])
                else:
                    ci.delete()
        
        # Log action
        desc = (
            f"{user_part.get_name()} drinks a {item_name}, restoring {heal_amount} HP."
            if user_part.id == target.id else
            f"{user_part.get_name()} administers a {item_name} to {target.get_name()}, restoring {heal_amount} HP."
        )
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=user_part,
            target=target,
            action_type='item',
            attack_name=item_name,
            damage_amount=heal_amount,
            hit=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )
        
        return Response({
            "message": desc,
            "heal_amount": heal_amount,
            "actual_healed": actual_healed,
            "target_hp": target.current_hp,
            "action": CombatActionSerializer(combat_action).data
        })

    @action(detail=True, methods=['post'])
    def use_feature(self, request, pk=None):
        """
        Use a class feature or racial trait in combat (e.g. Lay on Hands, Second Wind).
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active"}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        target_id = request.data.get('target_id')
        feature_name = request.data.get('feature_name', '')
        
        try:
            actor = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not actor.character:
            return Response({"error": "Only player characters can use class features."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Target defaults to actor
        if not target_id or int(target_id) == actor.id:
            target = actor
        else:
            try:
                target = session.participants.get(id=target_id)
            except CombatParticipant.DoesNotExist:
                target = actor
        
        if target.participant_type == 'enemy':
            return Response({"error": "Cannot use beneficial features on a hostile enemy."}, status=status.HTTP_400_BAD_REQUEST)
        
        clean_name = feature_name.strip().lower()
        
        if 'lay on hands' in clean_name:
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            pool = actor.get_lay_on_hands_pool()
            if pool <= 0:
                return Response({"error": "Lay on Hands pool is completely depleted."}, status=status.HTTP_400_BAD_REQUEST)
            
            cure_poison = request.data.get('cure_poison', False)
            if cure_poison:
                if pool < 5:
                    return Response({"error": "Neutralizing poison requires 5 points from Lay on Hands pool."}, status=status.HTTP_400_BAD_REQUEST)
                # Remove Poisoned condition if present
                poison_cond = target.conditions.filter(name__iexact='Poisoned').first()
                if poison_cond:
                    target.conditions.remove(poison_cond)
                
                actor.feature_uses['lay_on_hands_pool'] = pool - 5
                actor.action_used = True
                actor.attacks_remaining = 0
                actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
                
                desc = f"{actor.get_name()} channels Lay on Hands upon {target.get_name()}, cleansing poisons and toxins. ({actor.feature_uses['lay_on_hands_pool']} HP left in pool)"
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=target,
                    action_type='feature',
                    attack_name='Lay on Hands (Cure Poison)',
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "remaining_pool": actor.feature_uses['lay_on_hands_pool'],
                    "action": CombatActionSerializer(combat_action).data
                })
            else:
                amount = int(request.data.get('amount', 1))
                if amount <= 0 or amount > pool:
                    return Response({"error": f"Invalid amount. Available pool: {pool} HP"}, status=status.HTTP_400_BAD_REQUEST)
                
                if target.current_hp <= 0 and target.death_save_failures >= 3:
                    return Response({"error": "Target is deceased. Lay on Hands cannot revive the dead."}, status=status.HTTP_400_BAD_REQUEST)
                
                old_hp = target.current_hp
                target.heal(amount)
                actual_healed = target.current_hp - old_hp
                
                new_pool = pool - amount
                actor.feature_uses['lay_on_hands_pool'] = new_pool
                actor.action_used = True
                actor.attacks_remaining = 0
                actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
                
                desc = (
                    f"{actor.get_name()} uses Lay on Hands on themselves, restoring {amount} HP ({new_pool} HP left in pool)."
                    if actor.id == target.id else
                    f"{actor.get_name()} lays hands upon {target.get_name()}, restoring {amount} HP ({new_pool} HP left in pool)."
                )
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=target,
                    action_type='feature',
                    attack_name='Lay on Hands',
                    damage_amount=amount,
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "healed_amount": amount,
                    "actual_healed": actual_healed,
                    "target_hp": target.current_hp,
                    "remaining_pool": new_pool,
                    "action": CombatActionSerializer(combat_action).data
                })
                
        elif 'second wind' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.feature_uses.get('second_wind_used', False):
                return Response({"error": "Second Wind has already been used (regains after short/long rest)."}, status=status.HTTP_400_BAD_REQUEST)
            
            fighter_level = actor.character.level or 1
            heal_amount = random.randint(1, 10) + fighter_level
            old_hp = actor.current_hp
            actor.heal(heal_amount)
            actual_healed = actor.current_hp - old_hp
            
            actor.bonus_action_used = True
            actor.feature_uses['second_wind_used'] = True
            actor.save(update_fields=['bonus_action_used', 'feature_uses'])
            
            desc = f"{actor.get_name()} draws upon Second Wind, recovering {heal_amount} HP."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Second Wind',
                damage_amount=heal_amount,
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "healed_amount": heal_amount,
                "target_hp": actor.current_hp,
                "action": CombatActionSerializer(combat_action).data
            })
            
        else:
            return Response({"error": f"Feature '{feature_name}' not yet supported for active combat trigger."}, status=status.HTTP_400_BAD_REQUEST)
