"""
Combat Action Views - Core combat action endpoints.

Contains the CombatActionMixin with attack, cast_spell, and saving_throw actions.
"""
import logging
import random
import re

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from combat.condition_effects import auto_apply_condition_from_spell, is_condition_immune
from combat.environmental_effects import (
    calculate_cover_ac_bonus,
    get_lighting_attack_modifier,
    get_weather_ranged_modifier,
    has_full_cover,
)
from combat.models import (
    CombatAction,
    CombatParticipant,
    CombatSession,
    ConditionApplication,
    EnvironmentalEffect,
    ParticipantPosition,
)
from combat.serializers import (
    AttackRequestSerializer,
    CombatActionSerializer,
    CombatParticipantSerializer,
    CombatSessionSerializer,
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
        is_dm_override = data.get('dm_override', False)
        has_inspiration = data.get('inspiration', False)
        other_modifiers = data.get('other_modifiers', 0)
        weapon_slot = data.get('weapon_slot', 'main_hand')
        
        # In 5e rules, advantage/disadvantage are governed by conditions, features, and environment.
        # Manual client overrides are only honored in test mode with dm_override or via inspiration.
        # Restrict dm_override in gauntlet runs to staff/superusers
        has_gauntlet = hasattr(session, 'gauntlet_runs') and session.gauntlet_runs.exists()
        if is_dm_override and has_gauntlet and not (request.user and (request.user.is_staff or request.user.is_superuser)):
            is_dm_override = False

        advantage = bool(data.get('advantage', False)) if is_dm_override else False
        disadvantage = bool(data.get('disadvantage', False)) if is_dm_override else False
        
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
            # 1. Match weapon by attack_name first if provided
            if attack_name:
                matched_ci = attacker.character.character_items.filter(
                    item__name__iexact=attack_name,
                    item__weapon__isnull=False
                ).select_related('item__weapon').first()
                if not matched_ci:
                    matched_ci = attacker.character.character_items.filter(
                        item__name__icontains=attack_name,
                        item__weapon__isnull=False
                    ).select_related('item__weapon').first()
                if matched_ci:
                    equipped_weapon = matched_ci.item.weapon
                else:
                    from items.models import Weapon
                    equipped_weapon = Weapon.objects.filter(name__iexact=attack_name).first()
                    if not equipped_weapon:
                        equipped_weapon = Weapon.objects.filter(name__icontains=attack_name).first()

            # 2. Fall back to equipped weapon in slot
            if not equipped_weapon:
                equipped_weapon = attacker.get_equipped_weapon(weapon_slot)
            if not equipped_weapon and weapon_slot == 'main_hand':
                equipped_weapon = attacker.get_equipped_weapon('two_handed') or attacker.get_equipped_weapon('off_hand')

            if equipped_weapon:
                attack_name = attack_name or equipped_weapon.name
                damage_string = equipped_weapon.damage_dice
                
                # Check weapon type: ranged weapons use DEX, finesse can use DEX or STR, thrown melee weapons use STR
                is_weapon_ranged = (
                    getattr(equipped_weapon, 'weapon_type', None) in ['simple_ranged', 'martial_ranged'] or
                    'ranged' in str(getattr(equipped_weapon, 'weapon_type', '')).lower() or
                    ((getattr(equipped_weapon, 'range_normal', 0) or 0) > 5 and not getattr(equipped_weapon, 'thrown', False))
                )
                if getattr(equipped_weapon, 'finesse', False):
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                elif is_weapon_ranged:
                    use_ability = 'DEX'
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

        adv_reasons = []
        disadv_reasons = []
        
        # Determine melee vs ranged
        is_melee = True
        is_ranged_param = data.get('is_ranged')
        is_weapon_ranged = equipped_weapon and (
            getattr(equipped_weapon, 'weapon_type', None) in ['simple_ranged', 'martial_ranged'] or
            'ranged' in str(getattr(equipped_weapon, 'weapon_type', '')).lower() or
            ((getattr(equipped_weapon, 'range_normal', 0) or 0) > 5 and not getattr(equipped_weapon, 'thrown', False))
        )
        is_weapon_thrown = equipped_weapon and getattr(equipped_weapon, 'thrown', False)

        has_coords = (attacker.position_x != 0 or attacker.position_y != 0 or target.position_x != 0 or target.position_y != 0)
        dist = attacker.get_distance_to(target) if has_coords else 5
        reach = attacker.get_reach() if hasattr(attacker, 'get_reach') else 5

        if is_ranged_param is True:
            is_melee = False
        elif is_ranged_param is False:
            is_melee = True
        elif is_weapon_ranged:
            is_melee = False
        elif is_weapon_thrown and has_coords and dist > reach:
            # Target is beyond melee reach, but weapon is thrown -> make a ranged thrown attack!
            is_melee = False
        elif matched_action and getattr(matched_action, 'attack_type', '') == 'ranged_weapon':
            is_melee = False
        elif attack_name:
            lower_name = attack_name.lower()
            if any(term in lower_name for term in ['bow', 'crossbow', 'dart', 'sling', 'blowgun', 'ranged', 'ray', 'blast']):
                is_melee = False

        # Check grid reach for melee vs ranged
        if has_coords:
            if is_melee:
                if dist > reach:
                    return Response(
                        {"error": f"{target.get_name()} is out of melee reach ({dist} ft away, maximum reach is {reach} ft). Move closer first!"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # 5e Ranged attack distance validation
                normal_range = (equipped_weapon and getattr(equipped_weapon, 'range_normal', 0)) or 0
                long_range = (equipped_weapon and getattr(equipped_weapon, 'range_long', 0)) or 0

                # 5e Fallback defaults for standard weapons if not populated in DB
                if normal_range <= 5:
                    lower_name = (attack_name or '').lower()
                    if 'javelin' in lower_name:
                        normal_range, long_range = 30, 120
                    elif 'shortbow' in lower_name:
                        normal_range, long_range = 80, 320
                    elif 'longbow' in lower_name:
                        normal_range, long_range = 150, 600
                    elif any(t in lower_name for t in ['dart', 'dagger', 'spear', 'handaxe', 'trident', 'hammer']):
                        normal_range, long_range = 20, 60
                    elif 'crossbow' in lower_name and 'heavy' in lower_name:
                        normal_range, long_range = 100, 400
                    elif 'crossbow' in lower_name:
                        normal_range, long_range = 80, 320
                    elif 'sling' in lower_name:
                        normal_range, long_range = 30, 120
                    elif not is_melee:
                        normal_range, long_range = 60, 180

                if long_range <= 0:
                    long_range = max(normal_range, normal_range * 3)

                if dist > long_range:
                    return Response(
                        {"error": f"{target.get_name()} is beyond weapon range ({dist} ft away, maximum range is {long_range} ft)."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if dist > normal_range:
                    disadvantage = True
                    if f"Long Range ({dist} ft > {normal_range} ft)" not in disadv_reasons:
                        disadv_reasons.append(f"Long Range ({dist} ft > {normal_range} ft)")

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

        # 5e Close Quarters: Ranged attack while a hostile is within 5 ft incurs disadvantage
        if has_coords and not is_melee:
            hostile_adjacent = [
                opp for opp in session.participants.filter(is_active=True, current_hp__gt=0).exclude(participant_type=attacker.participant_type)
                if attacker.is_adjacent_to(opp) and not opp.is_incapacitated()
            ]
            if hostile_adjacent:
                disadvantage = True
                if "Close Quarters (Hostile within 5 ft)" not in disadv_reasons:
                    disadv_reasons.append("Close Quarters (Hostile within 5 ft)")

        # 5e Dodge Action: Attacks against a dodging target have disadvantage
        if target.feature_uses and target.feature_uses.get('dodge_active') and not target.is_incapacitated():
            disadvantage = True
            if "Target is Dodging" not in disadv_reasons:
                disadv_reasons.append("Target is Dodging")


        from combat.condition_effects import evaluate_attack_roll_conditions, is_auto_critical
        cond_adv, cond_disadv, cond_reasons = evaluate_attack_roll_conditions(attacker, target, is_melee=is_melee)
        if cond_adv:
            advantage = True
        if cond_disadv:
            disadvantage = True
        for cr in cond_reasons:
            if 'advantage' in cr.lower() or 'prone (melee' in cr.lower() or ('invisible' in cr.lower() and 'target is' not in cr.lower()):
                adv_reasons.append(cr)
            else:
                disadv_reasons.append(cr)

        # Check Reckless Attack
        if attacker.feature_uses and attacker.feature_uses.get('reckless_attack_active') and is_melee and use_ability == 'STR':
            advantage = True
            adv_reasons.append("Reckless Attack")
        if target.feature_uses and target.feature_uses.get('reckless_attack_active'):
            advantage = True
            adv_reasons.append("Target is Reckless")

        # Check Pack Tactics
        if attacker.has_trait('pack_tactics') or (resolved_enemy and hasattr(resolved_enemy, 'traits') and resolved_enemy.traits.filter(name__icontains='pack tactics').exists()):
            allies = session.participants.filter(
                participant_type=attacker.participant_type,
                is_active=True,
                current_hp__gt=0
            ).exclude(id=attacker.id)
            active_allies = [a for a in allies if not a.is_incapacitated()]
            if active_allies:
                advantage = True
                if "Pack Tactics" not in adv_reasons:
                    adv_reasons.append("Pack Tactics")

        # Flanking check for melee attacks (5e optional tactical rule)
        if is_melee:
            allies = session.participants.filter(
                participant_type=attacker.participant_type,
                is_active=True,
                current_hp__gt=0
            ).exclude(id=attacker.id)
            active_allies = [a for a in allies if not a.is_incapacitated()]
            if active_allies:
                if has_coords:
                    reach = attacker.get_reach() if hasattr(attacker, 'get_reach') else 5
                    attacker_dist = attacker.get_distance_to(target)
                    # Attacker must be in melee reach of target to flank
                    if attacker_dist <= reach:
                        # At least one ally must also be within 5 ft of target
                        flanking_ally = next((
                            a for a in active_allies
                            if a.get_distance_to(target) <= 5
                        ), None)
                        if flanking_ally:
                            advantage = True
                            if "Flanking" not in adv_reasons:
                                adv_reasons.append("Flanking")
                else:
                    advantage = True
                    if "Flanking" not in adv_reasons:
                        adv_reasons.append("Flanking")

        # Check manual inspiration or DM override if provided
        if has_inspiration:
            advantage = True
            if "Heroic Inspiration" not in adv_reasons:
                adv_reasons.append("Heroic Inspiration")
        if is_dm_override:
            if data.get('advantage') and "DM Override" not in adv_reasons:
                advantage = True
                adv_reasons.append("DM Override")
            if data.get('disadvantage') and "DM Override" not in disadv_reasons:
                disadvantage = True
                disadv_reasons.append("DM Override")

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
                    disadv_reasons.append("Darkness")
                elif lighting_mod == 'advantage':
                    advantage = True
                    adv_reasons.append("Illuminated")
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
                    disadv_reasons.append("Harsh Weather")
                elif weather_mod == 'advantage':
                    advantage = True
                    adv_reasons.append("Favorable Wind")

        # 5e Advantage / Disadvantage resolution: if both are present, they cancel out
        final_advantage = bool(advantage and not disadvantage)
        final_disadvantage = bool(disadvantage and not advantage)

        # Roll attack with resolved advantage/disadvantage
        roll, roll_breakdown = roll_d20(advantage=final_advantage, disadvantage=final_disadvantage)

        roll_annotation = roll_breakdown
        if final_advantage and adv_reasons:
            roll_annotation = f"{roll_breakdown} [{', '.join(adv_reasons)}]"
        elif final_disadvantage and disadv_reasons:
            roll_annotation = f"{roll_breakdown} [{', '.join(disadv_reasons)}]"
        elif advantage and disadvantage:
            roll_annotation = f"{roll_breakdown} [Adv & Dis Canceled]"
        
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
        attack_damage_type = None

        if hit:
            # Determine damage type
            if attacker.character:
                if equipped_weapon and getattr(equipped_weapon, 'damage_type', None):
                    attack_damage_type = equipped_weapon.damage_type
                elif not equipped_weapon:
                    attack_damage_type = 'bludgeoning'
            elif matched_action and matched_action.damage_rolls.exists():
                first_dr = matched_action.damage_rolls.first()
                if first_dr and first_dr.damage_type:
                    attack_damage_type = first_dr.damage_type

            if not attack_damage_type and damage_string:
                ds_lower = str(damage_string).lower()
                if 'slashing' in ds_lower:
                    attack_damage_type = 'slashing'
                elif 'piercing' in ds_lower:
                    attack_damage_type = 'piercing'
                elif 'bludgeoning' in ds_lower:
                    attack_damage_type = 'bludgeoning'

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
                # Add rage damage bonus if Barbarian is raging and makes a melee Strength attack
                rage_bonus = 0
                if attacker.is_raging() and is_melee and use_ability == 'STR':
                    rage_bonus = attacker.get_rage_damage_bonus()

                damage_modifier = damage_ability_mod + magic_bonuses['to_damage'] + rage_bonus
                damage_amount, damage_breakdown = calculate_damage(
                    damage_string, damage_modifier, critical
                )
                if rage_bonus > 0:
                    damage_breakdown += f" (+{rage_bonus} Rage)"

            _new_hp, concentration_broken = target.take_damage(damage_amount, damage_type=attack_damage_type)
            attack_resistance_info = getattr(target, 'last_resistance_info', None)

            # Check condition riders on hit (e.g. Wolf bite knock prone)
            if matched_action and matched_action.saving_throw_dc and matched_action.conditions_inflicted.exists():
                rider_ability = matched_action.saving_throw_ability or 'STR'
                rider_dc = matched_action.saving_throw_dc
                t_mod = target.get_ability_modifier(rider_ability)
                r_roll, r_breakdown = roll_d20()
                if (r_roll + t_mod) < rider_dc:
                    cond_names = []
                    for c in matched_action.conditions_inflicted.all():
                        if is_condition_immune(target, c.name):
                            damage_breakdown += f" | Target is IMMUNE to {c.name}!"
                            continue
                        target.conditions.add(c)
                        cond_names.append(c.name)
                    if cond_names:
                        damage_breakdown += f" | Inflicted {', '.join(cond_names)} (failed DC {rider_dc} {rider_ability} save: {r_breakdown}+{t_mod})"

            # Lock recharge if applicable
            if matched_action and matched_action.has_recharge:
                attacker.recharge_state[matched_action.name] = False
                attacker.save(update_fields=['recharge_state'])
        
        # Resolve DamageType foreign key for combat action
        from items.models import DamageType as DamageTypeModel
        damage_type_fk = attack_damage_type if isinstance(attack_damage_type, DamageTypeModel) else None
        if not damage_type_fk and isinstance(attack_damage_type, str):
            damage_type_fk = DamageTypeModel.objects.filter(name__iexact=attack_damage_type).first()

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
            damage_type=damage_type_fk,
            critical=critical,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            is_advantage=final_advantage,
            is_disadvantage=final_disadvantage,
            description=f"{roll_annotation} | {attack_breakdown}"
        )
        
        # Decrement attacks remaining
        attacker.attacks_remaining -= 1
        if attacker.attacks_remaining <= 0:
            attacker.action_used = True
        attacker.save()
        
        if hasattr(session, '_prefetched_objects_cache'):
            session._prefetched_objects_cache.clear()
        fresh_session = self.get_queryset().get(pk=session.pk)
        session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

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
            "advantage": final_advantage,
            "disadvantage": final_disadvantage,
            "advantage_reasons": adv_reasons,
            "disadvantage_reasons": disadv_reasons,
            "damage": damage_amount if hit else 0,
            "resistance_info": attack_resistance_info if hit else None,
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
            "action": CombatActionSerializer(combat_action).data,
            "session": session_data
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
        target_ids = data.get('target_ids') or []
        if not target_ids and target_id:
            target_ids = [target_id]
        spell_name = data['spell_name']
        spell_level = data.get('spell_level')
        save_type = data.get('save_type', '')
        save_dc = data.get('save_dc')
        damage_string = data.get('damage_string', '')
        data.get('damage_type')
        is_healing = data.get('is_healing', False)
        is_ritual = data.get('is_ritual', False) or request.data.get('is_ritual', False)
        requires_concentration = data.get('requires_concentration', False) or request.data.get('requires_concentration', False)
        is_bonus_action = data.get('is_bonus_action', False) or request.data.get('is_bonus_action', False)
        casting_time = data.get('casting_time', '') or request.data.get('casting_time', '')
        half_on_save = data.get('half_on_save', True)
        
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
        
        # 5e Action Economy: Determine if spell uses a Bonus Action or Main Action
        BONUS_ACTION_SPELLS = {
            'healing word', 'mass healing word', 'misty step', 'spiritual weapon',
            'hunter\'s mark', 'hex', 'sanctuary', 'shield of faith', 'divine favor',
            'expeditious retreat'
        }
        clean_spell_name = spell_name.strip().lower()
        if is_bonus_action or 'bonus' in str(casting_time).lower() or clean_spell_name in BONUS_ACTION_SPELLS:
            is_bonus_action = True

        if is_bonus_action:
            if caster.bonus_action_used:
                return Response(
                    {"error": f"{caster.get_name()} has already used their bonus action this turn"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
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
        
        targets = []
        if target_ids:
            for tid in target_ids:
                if tid == caster.id:
                    targets.append(caster)
                else:
                    t_obj = session.participants.filter(pk=tid).first()
                    if t_obj:
                        targets.append(t_obj)
        elif target_id:
            if target_id == caster.id:
                targets = [caster]
            else:
                try:
                    targets = [session.participants.get(pk=target_id)]
                except CombatParticipant.DoesNotExist:
                    return Response(
                        {"error": "Target not found in combat"},
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        primary_target = targets[0] if targets else None

        # Resolve spell metadata from central spell library
        spell_damage_type = None
        spell_obj = None
        try:
            from spells.models import Spell
            spell_obj = Spell.objects.filter(name__iexact=spell_name).first()
            if spell_obj:
                spell_dmg = spell_obj.damage_progression.first()
                if spell_dmg and spell_dmg.damage_type:
                    spell_damage_type = spell_dmg.damage_type
        except Exception:
            pass  # Graceful fallback if spell library unavailable

        # Magic Missile 5e target normalization: 3 darts at level 1 (+1 per upcast level)
        total_missile_darts = 3 + max(0, (int(spell_level) if spell_level is not None else 1) - 1)
        if clean_spell_name == 'magic missile':
            if not targets:
                return Response(
                    {"error": "Magic Missile requires at least one target."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if len(targets) == 1:
                targets = [targets[0]] * total_missile_darts
            elif len(targets) < total_missile_darts:
                while len(targets) < total_missile_darts:
                    targets.append(primary_target)
            elif len(targets) > total_missile_darts:
                targets = targets[:total_missile_darts]

        # Validate spell range (Self, Touch, X feet)
        SPELL_RANGE_FALLBACKS = {
            'cure wounds': 'Touch',
            'inflict wounds': 'Touch',
            'shocking grasp': 'Touch',
            'spare the dying': 'Touch',
            'guidance': 'Touch',
            'resistance': 'Touch',
            'identify': 'Touch',
            'mage armor': 'Touch',
            'protection from evil and good': 'Touch',
            'shield': 'Self',
            'shield of faith': '60 feet',
            'misty step': 'Self',
            'thunderwave': 'Self (15-foot cube)',
            'burning hands': 'Self (15-foot cone)',
            'blur': 'Self',
            'mirror image': 'Self',
            'expeditious retreat': 'Self',
            'false life': 'Self',
            'fire bolt': '120 feet',
            'eldritch blast': '120 feet',
            'sacred flame': '60 feet',
            'guiding bolt': '120 feet',
            'magic missile': '120 feet',
            'healing word': '60 feet',
            'fireball': '150 feet',
            'hold person': '60 feet',
            'witch bolt': '30 feet',
            'ray of frost': '60 feet',
            'toll the dead': '60 feet',
            'vicious mockery': '60 feet',
            'scorching ray': '120 feet',
            'grease': '60 feet',
            'fog cloud': '120 feet',
        }

        raw_range = None
        if spell_obj and spell_obj.range:
            raw_range = spell_obj.range.strip()
        elif clean_spell_name in SPELL_RANGE_FALLBACKS:
            raw_range = SPELL_RANGE_FALLBACKS[clean_spell_name]

        if raw_range:
            lower_range = raw_range.lower()
            if lower_range == 'self' or (lower_range.startswith('self') and '(' not in lower_range):
                for t in targets:
                    if t != caster:
                        return Response(
                            {"error": f"{spell_name} has a range of Self and can only target yourself."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                reach = caster.get_reach() if hasattr(caster, 'get_reach') else 5
                for t in targets:
                    if t == caster:
                        continue
                    has_coords = (caster.position_x != 0 or caster.position_y != 0 or t.position_x != 0 or t.position_y != 0)
                    if not has_coords:
                        continue
                    dist = caster.get_distance_to(t)
                    if lower_range == 'touch':
                        if dist > reach:
                            return Response(
                                {"error": f"{spell_name} is a Touch spell: {t.get_name()} is {dist} ft away (maximum reach is {reach} ft). Move closer first!"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    else:
                        range_match = re.search(r'(\d+)', lower_range)
                        if range_match:
                            max_range = int(range_match.group(1))
                            if dist > max_range:
                                return Response(
                                    {"error": f"{spell_name} has a range of {max_range} ft, but {t.get_name()} is {dist} ft away."},
                                    status=status.HTTP_400_BAD_REQUEST
                                )

        # Handle concentration
        if requires_concentration:
            caster.is_concentrating = True
            caster.concentration_spell = spell_name
            caster.save(update_fields=['is_concentrating', 'concentration_spell'])

        # Dedicated resolution for Magic Missile (5e: 3+ auto-hitting force darts, Shield spell negation)
        if clean_spell_name == 'magic missile':
            from combat.spell_rules import has_active_shield
            spell_damage_type = 'force'

            # Group darts by unique target maintaining order
            target_darts = {}
            for t in targets:
                if t.id not in target_darts:
                    target_darts[t.id] = {"target": t, "dart_rolls": []}
                # 5e: Each dart deals 1d4 + 1 force damage
                roll_dmg, _ = calculate_damage("1d4+1", 0, False)
                target_darts[t.id]["dart_rolls"].append(roll_dmg)

            target_results = []
            combat_actions = []

            for tid, tdata in target_darts.items():
                t = tdata["target"]
                dart_rolls = tdata["dart_rolls"]
                darts_count = len(dart_rolls)
                is_shielded = has_active_shield(t)

                if is_shielded:
                    t_damage = 0
                    concentration_broken = False
                    dart_word = "dart" if darts_count == 1 else "darts"
                    t_desc = f"{caster.get_name()} casts Magic Missile at {t.get_name()}, but a Shield spell absorbs all {darts_count} {dart_word}! (0 damage)"
                else:
                    t_damage = sum(dart_rolls)
                    _new_hp, concentration_broken = t.take_damage(t_damage, damage_type='force')
                    rolls_breakdown = " + ".join(str(r) for r in dart_rolls)
                    dart_word = "dart" if darts_count == 1 else "darts"
                    t_desc = f"{caster.get_name()} casts Magic Missile, striking {t.get_name()} with {darts_count} {dart_word} for {t_damage} force damage! ({rolls_breakdown})"

                t_resistance_info = getattr(t, 'last_resistance_info', None)
                if t_resistance_info:
                    rtype = t_resistance_info.get('type', '')
                    if rtype == 'immunity':
                        t_desc += f" [IMMUNE to {t_resistance_info.get('damage_type', '')}!]"
                    elif rtype == 'resistance':
                        t_desc += f" [RESISTED {t_resistance_info.get('damage_type', '')} — half damage]"
                    elif rtype == 'vulnerability':
                        t_desc += f" [VULNERABLE to {t_resistance_info.get('damage_type', '')} — double damage!]"

                target_results.append({
                    "target_id": t.id,
                    "target_name": t.get_name(),
                    "target_hp": t.current_hp,
                    "darts_count": darts_count,
                    "dart_rolls": dart_rolls,
                    "save_roll": None,
                    "save_total": None,
                    "save_success": None,
                    "damage": t_damage,
                    "healing": 0,
                    "shield_negated": is_shielded,
                    "concentration_broken": concentration_broken,
                    "condition_applied": None,
                    "condition_immune": None,
                    "post_effects": [],
                    "resistance_info": t_resistance_info,
                })

                act = CombatAction.objects.create(
                    combat_session=session,
                    actor=caster,
                    target=t,
                    action_type='spell',
                    attack_name='Magic Missile',
                    damage_amount=t_damage if t_damage > 0 else None,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=t_desc
                )
                combat_actions.append(act)

            # Mark action economy resource as consumed
            if is_bonus_action:
                caster.bonus_action_used = True
                caster.save(update_fields=['bonus_action_used'])
            else:
                caster.action_used = True
                caster.attacks_remaining = 0
                caster.save(update_fields=['action_used', 'attacks_remaining'])

            # Description summary
            if len(target_darts) == 1:
                desc = combat_actions[0].description
            else:
                total_all_dmg = sum(tr["damage"] for tr in target_results)
                desc = f"{caster.get_name()} casts Magic Missile, firing {total_missile_darts} darts across {len(target_darts)} targets for {total_all_dmg} force damage total"

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

            if hasattr(session, '_prefetched_objects_cache'):
                session._prefetched_objects_cache.clear()
            fresh_session = self.get_queryset().get(pk=session.pk)
            session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

            first_tr = target_results[0] if target_results else {}
            return Response({
                "message": desc,
                "spell_name": spell_name,
                "spell_level": spell_level,
                "is_bonus_action": is_bonus_action,
                "target": primary_target.get_name() if primary_target else None,
                "target_id": primary_target.id if primary_target else None,
                "target_hp": primary_target.current_hp if primary_target else None,
                "target_results": target_results,
                "is_healing": False,
                "healing_amount": 0,
                "save_type": None,
                "save_dc": None,
                "save_roll": None,
                "save_total": None,
                "save_success": None,
                "damage": first_tr.get("damage", 0),
                "condition_applied": None,
                "concentration_started": False,
                "action": CombatActionSerializer(combat_actions[0]).data if combat_actions else None,
                "session": session_data
            })
        
        healing_spell_names = {'cure wounds', 'healing word', 'prayer of healing', 'mass cure wounds', 'heal', 'mass heal'}
        if is_healing or clean_spell_name in healing_spell_names:
            is_healing = True

        # Roll base damage/healing once (5e rules: AoE rolls damage once and applies to all affected)
        base_damage = 0
        if damage_string:
            base_damage, _ = calculate_damage(damage_string, 0, False)

        target_results = []
        combat_actions = []
        from combat.condition_effects import is_auto_fail_save

        for t in targets:
            t_save_roll = None
            t_save_total = None
            t_save_success = None
            t_damage = 0
            t_healing = 0
            t_cond = None
            concentration_broken = False

            rider_str = ""
            if is_healing:
                from combat.spell_rules import can_heal_target
                if not can_heal_target(t, spell_name):
                    t_healing = 0
                    c_type = getattr(getattr(t.encounter_enemy, 'enemy', None), 'creature_type', 'undead') if t.encounter_enemy else 'undead'
                    rider_str += f" [No effect on {c_type}]"
                else:
                    t_healing = max(1, base_damage)
                    t.heal(t_healing)
            elif save_type and save_dc:
                if is_auto_fail_save(t, save_type):
                    t_save_roll = 1
                    save_mod = t.get_ability_modifier(save_type)
                    t_save_total = t_save_roll + save_mod
                    t_save_success = False
                else:
                    t_save_roll, _ = roll_d20()
                    save_mod = t.get_ability_modifier(save_type)
                    prof_bonus = t.character.proficiency_bonus if t.character else 2
                    prof = False
                    if t.character and hasattr(t.character, 'saving_throw_proficiencies') and t.character.saving_throw_proficiencies:
                        prof = save_type.lower() in [s.lower() for s in t.character.saving_throw_proficiencies]
                    t_save_total, _ = calculate_saving_throw(t_save_roll, save_mod, prof_bonus, prof)
                    t_save_success = (t_save_total >= save_dc)

                if base_damage > 0:
                    if t_save_success:
                        t_damage = (base_damage // 2) if half_on_save else 0
                    else:
                        t_damage = base_damage
                    if t_damage > 0:
                        _new_hp, concentration_broken = t.take_damage(t_damage, damage_type=spell_damage_type)
            elif base_damage > 0:
                t_damage = base_damage
                _new_hp, concentration_broken = t.take_damage(t_damage, damage_type=spell_damage_type)

            # 5E Thunderwave Forced Movement: Push 10 feet away from caster on failed save
            pushed_str = ""
            if clean_spell_name == 'thunderwave' and t_save_success is False and t.is_active and t.current_hp > 0:
                import math
                dx = (t.position_x or 0) - (caster.position_x or 0)
                dy = (t.position_y or 0) - (caster.position_y or 0)
                dist = math.hypot(dx, dy)
                if dist == 0:
                    dx, dy, dist = 1, 0, 1
                # 10 feet push (2 grid cells)
                step_x = round((dx / dist) * 10 / 5) * 5
                step_y = round((dy / dist) * 10 / 5) * 5
                # Clamp strictly to battlefield grid boundaries [0, 45] feet (10x10 grid: 0 to 45 ft)
                # Never wrap around or push off the edge!
                new_x = max(0, min(45, (t.position_x or 0) + step_x))
                new_y = max(0, min(45, (t.position_y or 0) + step_y))
                if new_x != t.position_x or new_y != t.position_y:
                    t.position_x = new_x
                    t.position_y = new_y
                    t.save(update_fields=['position_x', 'position_y'])
                    pushed_str = f" and was blasted 10 ft away to ({new_x} ft, {new_y} ft)"

            # Apply spell post-effects (e.g. Shocking Grasp reaction prevention, Ray of Frost speed reduction)
            from combat.spell_rules import apply_spell_post_effects
            post_effects = apply_spell_post_effects(caster, t, spell_name, hit_or_save_failed=(t_save_success is False or not save_type))
            if post_effects:
                rider_str += f" [{' '.join(post_effects)}]"

            # Auto-apply conditions from spell (if not healing, and save failed or no save)
            t_cond = None
            if not is_healing and (t_save_success is False or not save_type):
                t_cond = auto_apply_condition_from_spell(t, spell_name)
                if t_cond:
                    ConditionApplication.objects.create(
                        participant=t,
                        condition=t_cond,
                        applied_round=session.current_round,
                        applied_turn=session.current_turn_index,
                        duration_type='spell' if requires_concentration else 'round',
                        duration_rounds=1 if not requires_concentration else 0,
                        expires_at_round=session.current_round + 1 if not requires_concentration else None,
                        source_type='spell',
                        source_name=spell_name
                    )

            t_resistance_info = getattr(t, 'last_resistance_info', None)
            t_cond_immune = getattr(t, 'last_condition_immune', None)

            target_results.append({
                "target_id": t.id,
                "target_name": t.get_name(),
                "target_hp": t.current_hp,
                "save_roll": t_save_roll,
                "save_total": t_save_total,
                "save_success": t_save_success,
                "damage": t_damage,
                "healing": t_healing,
                "concentration_broken": concentration_broken,
                "condition_applied": t_cond.name if t_cond else None,
                "condition_immune": t_cond_immune,
                "post_effects": post_effects,
                "resistance_info": t_resistance_info,
            })

            # Create individual action log
            # Build resistance annotation for combat log
            resist_str = ""
            if t_resistance_info:
                rtype = t_resistance_info.get('type', '')
                if rtype == 'immunity':
                    resist_str = f" [IMMUNE to {t_resistance_info.get('damage_type', '')}!]"
                elif rtype == 'resistance':
                    resist_str = f" [RESISTED {t_resistance_info.get('damage_type', '')} — half damage]"
                elif rtype == 'vulnerability':
                    resist_str = f" [VULNERABLE to {t_resistance_info.get('damage_type', '')} — double damage!]"

            cond_str = ""
            if t_cond:
                cond_str = f" [{t_cond.name.capitalize()} applied]"
            elif t_cond_immune:
                cond_str = f" [IMMUNE to {t_cond_immune}!]"

            if is_healing:
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()}, restoring {t_healing} HP{cond_str}{rider_str}"
            elif t_damage > 0:
                save_str = f" (rolled {t_save_total} vs DC {save_dc} - {'SAVED' if t_save_success else 'FAILED'})" if save_type else ""
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()} for {t_damage} damage{save_str}{pushed_str}{resist_str}{cond_str}{rider_str}"
            else:
                save_str = f" (rolled {t_save_total} vs DC {save_dc} - SAVED, 0 damage)" if save_type else ""
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()}{save_str}{pushed_str}{cond_str}{rider_str}"

            act = CombatAction.objects.create(
                combat_session=session,
                actor=caster,
                target=t,
                action_type='spell',
                attack_name=spell_name,
                damage_amount=t_damage if t_damage > 0 else None,
                save_type=save_type if save_type else None,
                save_dc=save_dc,
                save_roll=t_save_roll,
                save_success=t_save_success,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=t_desc
            )
            combat_actions.append(act)

        if not targets:
            act = CombatAction.objects.create(
                combat_session=session,
                actor=caster,
                target=None,
                action_type='spell',
                attack_name=spell_name,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=f"{caster.get_name()} casts {spell_name}"
            )
            combat_actions.append(act)

        # 5E Persistent Ground & Environmental Spell Effects
        effect_origin_x = primary_target.position_x if (primary_target and primary_target.position_x is not None) else (caster.position_x if caster.position_x is not None else 20)
        effect_origin_y = primary_target.position_y if (primary_target and primary_target.position_y is not None) else (caster.position_y if caster.position_y is not None else 15)

        if clean_spell_name == 'grease':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='terrain',
                terrain_type='mud',
                cover_area_x=effect_origin_x,
                cover_area_y=effect_origin_y,
                cover_area_radius=5,
                description=f"Slick Grease covers the ground in a 10-ft square around ({effect_origin_x} ft, {effect_origin_y} ft) (Difficult Terrain)."
            )
        elif clean_spell_name == 'fog cloud':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='weather',
                weather_type='heavy_fog',
                lighting_area_x=effect_origin_x,
                lighting_area_y=effect_origin_y,
                lighting_area_radius=20,
                description=f"Fog Cloud creates a 20-ft radius sphere of dense fog centered at ({effect_origin_x} ft, {effect_origin_y} ft) (Heavily Obscured)."
            )
        elif clean_spell_name == 'darkness':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='lighting',
                lighting_type='magical_darkness',
                lighting_area_x=effect_origin_x,
                lighting_area_y=effect_origin_y,
                lighting_area_radius=15,
                description=f"Magical Darkness shrouds a 15-ft radius sphere around ({effect_origin_x} ft, {effect_origin_y} ft)."
            )
        elif clean_spell_name == 'web':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='terrain',
                terrain_type='thick_vegetation',
                cover_area_x=effect_origin_x,
                cover_area_y=effect_origin_y,
                cover_area_radius=10,
                description=f"Sticky Webbing fills a 20-ft cube centered at ({effect_origin_x} ft, {effect_origin_y} ft) (Difficult Terrain)."
            )
        elif clean_spell_name == 'spike growth':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='terrain',
                terrain_type='rubble',
                cover_area_x=effect_origin_x,
                cover_area_y=effect_origin_y,
                cover_area_radius=20,
                description=f"Hard Spikes and thorns sprout in a 20-ft radius around ({effect_origin_x} ft, {effect_origin_y} ft) (Difficult Terrain)."
            )
        elif clean_spell_name == 'entangle':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='terrain',
                terrain_type='thick_vegetation',
                cover_area_x=effect_origin_x,
                cover_area_y=effect_origin_y,
                cover_area_radius=10,
                description=f"Grasping weeds and vines sprout in a 20-ft square around ({effect_origin_x} ft, {effect_origin_y} ft) (Difficult Terrain)."
            )
        elif clean_spell_name == 'sleet storm':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='terrain',
                terrain_type='ice',
                cover_area_x=effect_origin_x,
                cover_area_y=effect_origin_y,
                cover_area_radius=40,
                description=f"Freezing sleet covers a 40-ft radius around ({effect_origin_x} ft, {effect_origin_y} ft) (Difficult Terrain & Heavily Obscured)."
            )
        elif clean_spell_name in ['cloudkill', 'stinking cloud']:
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='hazard',
                hazard_type='poison_gas',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=20,
                description=f"A 20-ft radius sphere of noxious toxic gas lingers centered at ({effect_origin_x} ft, {effect_origin_y} ft) (Hazard & Heavily Obscured)."
            )

        # Mark action economy resource as consumed
        if is_bonus_action:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])
        else:
            caster.action_used = True
            caster.attacks_remaining = 0
            caster.save(update_fields=['action_used', 'attacks_remaining'])

        # Action description summary
        if len(targets) > 1:
            total_dmg = sum(tr["damage"] for tr in target_results)
            total_heal = sum(tr["healing"] for tr in target_results)
            if is_healing:
                desc = f"{caster.get_name()} casts {spell_name} healing {len(targets)} targets for {total_heal} HP total"
            else:
                desc = f"{caster.get_name()} casts {spell_name} hitting {len(targets)} targets for {total_dmg} damage total"
        elif len(targets) == 1 and combat_actions:
            desc = combat_actions[0].description
        else:
            desc = f"{caster.get_name()} casts {spell_name}"

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
        
        if hasattr(session, '_prefetched_objects_cache'):
            session._prefetched_objects_cache.clear()
        fresh_session = self.get_queryset().get(pk=session.pk)
        session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

        first_tr = target_results[0] if target_results else {}
        return Response({
            "message": desc,
            "spell_name": spell_name,
            "spell_level": spell_level,
            "is_bonus_action": is_bonus_action,
            "target": primary_target.get_name() if primary_target else None,
            "target_id": primary_target.id if primary_target else None,
            "target_hp": primary_target.current_hp if primary_target else None,
            "target_results": target_results,
            "is_healing": is_healing,
            "healing_amount": first_tr.get("healing", 0),
            "save_type": save_type if save_type else None,
            "save_dc": save_dc,
            "save_roll": first_tr.get("save_roll"),
            "save_total": first_tr.get("save_total"),
            "save_success": first_tr.get("save_success"),
            "damage": first_tr.get("damage", 0),
            "condition_applied": first_tr.get("condition_applied"),
            "concentration_started": requires_concentration,
            "action": CombatActionSerializer(combat_actions[0]).data if combat_actions else None,
            "session": session_data
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

        elif 'rage' in clean_name:
            is_end = ('end' in clean_name) or bool(request.data.get('end_rage', False))
            if is_end:
                if not actor.is_raging():
                    return Response({"error": f"{actor.get_name()} is not currently raging."}, status=status.HTTP_400_BAD_REQUEST)
                actor.feature_uses['is_raging'] = False
                actor.save(update_fields=['feature_uses'])
                desc = f"{actor.get_name()} calms their battle fury and ceases raging."
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=actor,
                    action_type='feature',
                    attack_name='End Rage',
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "is_raging": False,
                    "remaining_uses": actor.get_rage_uses_remaining(),
                    "action": CombatActionSerializer(combat_action).data
                })
            else:
                if actor.is_raging():
                    return Response({"error": f"{actor.get_name()} is already raging!"}, status=status.HTTP_400_BAD_REQUEST)
                remaining = actor.get_rage_uses_remaining()
                if remaining <= 0:
                    return Response({"error": f"No Rage uses remaining (0/{actor.get_max_rage_uses()}). Regained after a long rest."}, status=status.HTTP_400_BAD_REQUEST)
                if actor.bonus_action_used:
                    return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
                
                equipped_armor = actor.get_equipped_armor()
                if equipped_armor and equipped_armor.armor_type == 'heavy':
                    return Response({"error": "Cannot enter Rage while wearing Heavy Armor."}, status=status.HTTP_400_BAD_REQUEST)
                
                actor.feature_uses['is_raging'] = True
                if actor.get_max_rage_uses() < 900:  # Not unlimited
                    actor.feature_uses['rage_uses_remaining'] = remaining - 1
                actor.bonus_action_used = True
                update_fields = ['feature_uses', 'bonus_action_used']
                if actor.is_concentrating:
                    actor.is_concentrating = False
                    actor.concentration_spell = ""
                    update_fields.extend(['is_concentrating', 'concentration_spell'])
                actor.save(update_fields=update_fields)
                
                rage_bonus = actor.get_rage_damage_bonus()
                rem = actor.get_rage_uses_remaining()
                rem_str = "Unlimited" if rem >= 900 else f"{rem} left"
                desc = f"🔥 {actor.get_name()} roars and enters a primal Rage! Resistance to Bludgeoning, Piercing, and Slashing damage; +{rage_bonus} melee damage with Strength. ({rem_str})"
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=actor,
                    action_type='feature',
                    attack_name='Rage',
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "is_raging": True,
                    "remaining_uses": actor.get_rage_uses_remaining(),
                    "action": CombatActionSerializer(combat_action).data
                })

        elif 'reckless attack' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if not actor.has_reckless_attack() and not (actor.is_barbarian() and char_lvl >= 2):
                return Response({"error": "Reckless Attack requires Barbarian level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.feature_uses.get('reckless_attack_active', False):
                return Response({"error": "Reckless Attack is already active for this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            actor.feature_uses['reckless_attack_active'] = True
            actor.save(update_fields=['feature_uses'])
            desc = f"⚡ {actor.get_name()} attacks Recklessly! Gained advantage on Strength melee attacks this turn, but incoming attacks have advantage until next turn."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Reckless Attack',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "reckless_attack_active": True,
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'action surge' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if not actor.is_fighter() and not any('action surge' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Action Surge requires Fighter level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if char_lvl < 2 and not any('action surge' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Action Surge requires Fighter level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.feature_uses.get('action_surge_used', False):
                return Response({"error": "Action Surge has already been used (regains after short/long rest)."}, status=status.HTTP_400_BAD_REQUEST)
            
            actor.action_used = False
            actor.attacks_remaining = actor._calculate_attacks_per_action()
            actor.feature_uses['action_surge_used'] = True
            actor.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])
            
            desc = f"⚡ {actor.get_name()} pushes beyond their limits with Action Surge! Gained an additional Action this turn."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Action Surge',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "action_used": False,
                "attacks_remaining": actor.attacks_remaining,
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'cunning action' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if not actor.is_rogue() and not any('cunning action' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Cunning Action requires Rogue level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if char_lvl < 2 and not any('cunning action' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Cunning Action requires Rogue level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            subaction = request.data.get('subaction', 'dash').lower().strip()
            if subaction not in ['dash', 'disengage', 'hide']:
                return Response({"error": f"Invalid Cunning Action '{subaction}'. Must be Dash, Disengage, or Hide."}, status=status.HTTP_400_BAD_REQUEST)
            
            actor.bonus_action_used = True
            extra_desc = ""
            if subaction == 'dash':
                actor.movement_used = max(0, actor.movement_used - actor.speed)
                extra_desc = f"{actor.get_name()} takes Cunning Action: Dash, gaining additional movement for this turn!"
            elif subaction == 'disengage':
                actor.feature_uses['disengaged'] = True
                extra_desc = f"{actor.get_name()} takes Cunning Action: Disengage. Movement will not provoke opportunity attacks this turn!"
            elif subaction == 'hide':
                stealth_mod = actor.get_ability_modifier('DEX')
                h_roll, h_breakdown = roll_d20()
                h_total = h_roll + stealth_mod
                actor.feature_uses['hidden'] = True
                extra_desc = f"{actor.get_name()} takes Cunning Action: Hide! Stealth roll: {h_breakdown} + {stealth_mod} = {h_total}."
            
            actor.save(update_fields=['bonus_action_used', 'movement_used', 'feature_uses'])
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name=f"Cunning Action: {subaction.capitalize()}",
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=extra_desc
            )
            return Response({
                "message": extra_desc,
                "bonus_action_used": True,
                "action": CombatActionSerializer(combat_action).data
            })

        else:
            return Response({"error": f"Feature '{feature_name}' not yet supported for active combat trigger."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Move a combat participant on the tactical battle grid.
        POST /api/combat/sessions/{id}/move/
        Request body: { "participant_id": 1, "target_x": 15, "target_y": 10 }
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        target_x = request.data.get('target_x')
        target_y = request.data.get('target_y')
        
        if participant_id is None or target_x is None or target_y is None:
            return Response({"error": "participant_id, target_x, and target_y are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            participant = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not participant.is_active or participant.current_hp <= 0:
            return Response({"error": f"{participant.get_name()} is defeated and cannot move."}, status=status.HTTP_400_BAD_REQUEST)
        
        if participant.is_incapacitated():
            return Response({"error": f"{participant.get_name()} is {participant.get_incapacitating_condition()} and cannot move."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_x = int(target_x)
            target_y = int(target_y)
        except (ValueError, TypeError):
            return Response({"error": "target_x and target_y must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        # Snap to 5-ft grid
        target_x = round(target_x / 5.0) * 5
        target_y = round(target_y / 5.0) * 5

        # Arena bounds (10x8 grid: 0..45 ft in X, 0..35 ft in Y)
        if target_x < 0 or target_x > 45 or target_y < 0 or target_y > 35:
            return Response({
                "error": f"Target coordinates ({target_x}, {target_y}) are out of arena bounds (0-45ft X, 0-35ft Y)."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check occupancy by another living combatant
        occupied = session.participants.filter(
            position_x=target_x,
            position_y=target_y,
            is_active=True,
            current_hp__gt=0
        ).exclude(id=participant.id).exists()
        if occupied:
            return Response({"error": "Destination square is already occupied."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate tile-by-tile path cost on the 5e grid (accounting for difficult terrain & obstacles)
        from combat.battlefield import calculate_tile_path
        path_cost, move_path = calculate_tile_path(
            session, participant, participant.position_x, participant.position_y, target_x, target_y
        )

        if path_cost == float('inf'):
            return Response({
                "error": "Destination is blocked by an obstacle or impassable terrain."
            }, status=status.HTTP_400_BAD_REQUEST)

        if path_cost == 0:
            return Response({
                "message": f"{participant.get_name()} is already at ({target_x}, {target_y})",
                "participant": CombatParticipantSerializer(participant).data,
                "distance_moved": 0
            })

        rem_movement = participant.movement_remaining
        if path_cost > rem_movement:
            return Response({
                "error": f"Not enough movement. Path requires {path_cost} ft (due to difficult terrain or obstacles), but {participant.get_name()} only has {rem_movement} ft remaining."
            }, status=status.HTTP_400_BAD_REQUEST)

        dist_moved = path_cost

        # Check Opportunity Attacks along the actual path traveled
        is_disengaged = bool(participant.feature_uses and participant.feature_uses.get('disengaged'))
        oa_results = []
        mover_fell_unconscious = False

        if not is_disengaged:
            enemies = session.participants.filter(
                is_active=True,
                current_hp__gt=0
            ).exclude(participant_type=participant.participant_type)

            for enemy in enemies:
                if not enemy.can_use_reaction() or enemy.is_incapacitated():
                    continue
                enemy_x = enemy.position_x
                enemy_y = enemy.position_y
                provoked = False
                for step_idx in range(len(move_path) - 1):
                    step_from = move_path[step_idx]
                    step_to = move_path[step_idx + 1]
                    d_from = max(abs(step_from[0] - enemy_x), abs(step_from[1] - enemy_y))
                    d_to = max(abs(step_to[0] - enemy_x), abs(step_to[1] - enemy_y))
                    if d_from <= 5 and d_to > 5:
                        provoked = True
                        break

                if provoked:
                    enemy.use_reaction()
                    # Execute Opportunity Attack
                    raw_d20, _ = roll_d20()
                    atk_bonus = 2
                    dmg_str = "1d6+2"
                    resolved_enemy = enemy.resolve_enemy()
                    if resolved_enemy:
                        melee_act = resolved_enemy.actions.filter(attack_type='melee_weapon').first()
                        if melee_act:
                            atk_bonus = melee_act.attack_bonus or 2
                            dmg_rolls = list(melee_act.damage_rolls.all())
                            if dmg_rolls:
                                dmg_str = " + ".join([d.formula for d in dmg_rolls])
                    elif enemy.character and enemy.character.stats:
                        atk_bonus = enemy.character.stats.strength_modifier + 2
                    
                    total_atk = raw_d20 + atk_bonus
                    target_ac = participant.calculate_effective_ac() if hasattr(participant, 'calculate_effective_ac') else participant.armor_class
                    hit = (total_atk >= target_ac or raw_d20 == 20) and raw_d20 != 1
                    
                    damage_dealt = 0
                    if hit:
                        dmg_amount, _ = calculate_damage(dmg_str, critical=(raw_d20 == 20))
                        damage_dealt = max(1, dmg_amount)
                        participant.take_damage(damage_dealt)
                        if participant.current_hp <= 0:
                            mover_fell_unconscious = True
                    
                    desc = f"⚠️ Opportunity Attack! {enemy.get_name()} strikes at {participant.get_name()}: rolled {total_atk} vs AC {target_ac} ({'HIT for ' + str(damage_dealt) + ' dmg' if hit else 'MISSED'})."
                    CombatAction.objects.create(
                        combat_session=session,
                        actor=enemy,
                        target=participant,
                        action_type='opportunity_attack',
                        hit=hit,
                        damage_amount=damage_dealt,
                        round_number=session.current_round,
                        turn_number=session.current_turn_index,
                        description=desc
                    )
                    oa_results.append({
                        "attacker": enemy.get_name(),
                        "hit": hit,
                        "attack_roll": total_atk,
                        "damage": damage_dealt,
                        "target_hp_remaining": participant.current_hp,
                        "description": desc
                    })
                    if mover_fell_unconscious:
                        break

        # If mover was dropped to 0 HP by an opportunity attack, they collapse at their original tile
        if not mover_fell_unconscious:
            participant.position_x = target_x
            participant.position_y = target_y
            participant.movement_used += dist_moved
            participant.save(update_fields=['position_x', 'position_y', 'movement_used'])
            desc = f"{participant.get_name()} moved {dist_moved} ft to ({target_x} ft, {target_y} ft)."
        else:
            participant.movement_used += 5
            participant.save(update_fields=['movement_used', 'current_hp', 'is_active'])
            desc = f"{participant.get_name()} attempted to move {dist_moved} ft but was struck down by an opportunity attack at ({participant.position_x} ft, {participant.position_y} ft)!"

        CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=participant,
            action_type='move',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )

        # Refetch fresh session from DB so serialized participants contain updated coordinates
        fresh_session = CombatSession.objects.prefetch_related(
            'participants',
            'participants__conditions',
            'actions',
        ).get(id=session.id)

        return Response({
            "message": desc,
            "participant": CombatParticipantSerializer(participant).data,
            "opportunity_attacks": oa_results,
            "session": CombatSessionSerializer(fresh_session).data
        })

    @action(detail=True, methods=['post'])
    def dash(self, request, pk=None):
        """
        Take the Dash action.
        POST /api/combat/sessions/{id}/dash/
        Payload: { "participant_id": 1 }
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        try:
            participant = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if participant.action_used or participant.attacks_remaining <= 0:
            return Response({"error": f"{participant.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant.action_used = True
        participant.attacks_remaining = 0
        if not participant.feature_uses:
            participant.feature_uses = {}
        participant.feature_uses['dash_active'] = True
        participant.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])

        desc = f"{participant.get_name()} takes the Dash action, doubling their movement speed for this turn (+{participant.speed} ft)!"
        CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=participant,
            action_type='dash',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )

        fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
        return Response({
            "message": desc,
            "participant": CombatParticipantSerializer(participant).data,
            "session": CombatSessionSerializer(fresh_session).data
        })

    @action(detail=True, methods=['post'])
    def disengage(self, request, pk=None):
        """
        Take the Disengage action.
        POST /api/combat/sessions/{id}/disengage/
        Payload: { "participant_id": 1 }
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        try:
            participant = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if participant.action_used or participant.attacks_remaining <= 0:
            return Response({"error": f"{participant.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant.action_used = True
        participant.attacks_remaining = 0
        if not participant.feature_uses:
            participant.feature_uses = {}
        participant.feature_uses['disengaged'] = True
        participant.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])

        desc = f"{participant.get_name()} takes the Disengage action! Their movement will not provoke opportunity attacks for the rest of this turn."
        CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=participant,
            action_type='disengage',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )

        fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
        return Response({
            "message": desc,
            "participant": CombatParticipantSerializer(participant).data,
            "session": CombatSessionSerializer(fresh_session).data
        })

    @action(detail=True, methods=['post'])
    def dodge(self, request, pk=None):
        """
        Take the Dodge action.
        POST /api/combat/sessions/{id}/dodge/
        Payload: { "participant_id": 1 }
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = request.data.get('participant_id')
        try:
            participant = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if participant.action_used or participant.attacks_remaining <= 0:
            return Response({"error": f"{participant.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant.action_used = True
        participant.attacks_remaining = 0
        if not participant.feature_uses:
            participant.feature_uses = {}
        participant.feature_uses['dodge_active'] = True
        participant.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])

        desc = f"{participant.get_name()} takes the Dodge action! Attacks against them have disadvantage until the start of their next turn."
        CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=participant,
            action_type='dodge',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )

        fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
        return Response({
            "message": desc,
            "participant": CombatParticipantSerializer(participant).data,
            "session": CombatSessionSerializer(fresh_session).data
        })

