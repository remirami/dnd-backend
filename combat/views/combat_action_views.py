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

from bestiary.models import Condition
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
        target_id = data.get('target_id')
        target_ids = data.get('target_ids', [])
        if not target_id and target_ids:
            target_id = target_ids[0]

        try:
            attacker = session.participants.get(pk=attacker_id)
            target = session.participants.get(pk=target_id) if target_id else None
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Attacker or target not found in combat"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not target:
            return Response(
                {"error": "Target not found in combat"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target.is_dead():
            return Response(
                {"error": f"{target.get_name()} is dead and cannot be attacked."},
                status=status.HTTP_400_BAD_REQUEST
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
        
        # Get attack details
        is_dm_override = data.get('dm_override', False) or request.data.get('dm_override', False)

        # Check if it's attacker's turn
        current = session.get_current_participant()
        if not is_dm_override and current != attacker:
            return Response(
                {"error": f"It is not {attacker.get_name()}'s turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if attacker has attacks remaining this turn
        if not is_dm_override and attacker.attacks_remaining <= 0:
            return Response(
                {"error": f"{attacker.get_name()} has no attacks remaining this turn"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attack_name = data.get('attack_name', None)
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
            # 1. Check if explicitly an Unarmed Strike / Martial Arts Strike
            is_unarmed_attack = bool(attack_name and any(u in attack_name.lower() for u in ['unarmed', 'martial arts']))
            if is_unarmed_attack:
                equipped_weapon = None
            elif attack_name:
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

            # 2. Fall back to equipped weapon in slot if not an explicit unarmed attack
            if not is_unarmed_attack:
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
                str_mod = attacker.get_ability_modifier('STR')
                dex_mod = attacker.get_ability_modifier('DEX')
                if getattr(equipped_weapon, 'finesse', False):
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                elif attacker.is_monk():
                    # Monks can use DEX for monk weapons if DEX > STR
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                elif is_weapon_ranged:
                    use_ability = 'DEX'
                else:
                    use_ability = 'STR'
            else:
                attack_name = attack_name or 'Unarmed Strike'
                if attacker.is_monk():
                    damage_string = attacker.get_martial_arts_die()
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                else:
                    damage_string = "1"
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

            # Handle Saving Throw actions (e.g. Fire Breath, Acid Breath, Frightful Presence)
            if matched_action and matched_action.attack_type == 'saving_throw':
                if matched_action.has_recharge:
                    if attacker.recharge_state is None:
                        attacker.init_recharge_state()
                    is_ready = attacker.recharge_state.get(matched_action.name, True)
                    if not is_ready:
                        return Response(
                            {"error": f"{matched_action.name} is still recharging and cannot be used."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                save_ability = matched_action.saving_throw_ability or 'DEX'
                save_dc = matched_action.saving_throw_dc or 15

                # Support multi-target AoE if target_ids provided
                raw_target_ids = data.get('target_ids') or ([target.id] if target else [])
                aoe_targets = list(session.participants.filter(id__in=raw_target_ids, is_active=True))
                if not aoe_targets and target:
                    aoe_targets = [target]

                # Roll damage once for the saving throw action
                damage_amount = 0
                dmg_rolls = list(matched_action.damage_rolls.all())
                first_dr = dmg_rolls[0] if dmg_rolls else None
                dmg_type = first_dr.damage_type.name.lower() if (first_dr and first_dr.damage_type) else None
                if dmg_rolls:
                    for d in dmg_rolls:
                        roll_sum = sum(random.randint(1, d.dice_sides) for _ in range(d.dice_count)) + d.damage_bonus
                        damage_amount += max(0, roll_sum)
                else:
                    damage_amount, _ = calculate_damage(damage_string, 0, False)

                summary_messages = []
                last_saved = True
                last_damage = 0
                last_target_hp = target.current_hp if target else 0
                last_cond = None
                last_s_roll = 10
                last_s_total = 10

                from combat.condition_effects import is_auto_fail_save, is_condition_immune

                for cur_target in aoe_targets:
                    save_mod = cur_target.get_ability_modifier(save_ability)
                    if is_auto_fail_save(cur_target, save_ability):
                        saved = False
                        s_roll = 1
                        s_total = s_roll + save_mod
                        s_breakdown = f"Auto-fail ({cur_target.get_incapacitating_condition()})"
                    else:
                        s_roll, s_breakdown = roll_d20()
                        s_total = s_roll + save_mod
                        saved = (s_total >= save_dc)

                    lr_note = ""
                    if not saved and hasattr(cur_target, 'check_legendary_resistance'):
                        used_lr, saved, lr_msg = cur_target.check_legendary_resistance(save_ability, save_dc, s_total)
                        if used_lr:
                            lr_note = f" 🛡️ [Legendary Resistance Used!]"

                    target_damage = (damage_amount // 2) if (saved and matched_action.half_damage_on_save) else (0 if saved else damage_amount)
                    _new_hp, concentration_broken = cur_target.take_damage(target_damage, damage_type=dmg_type, is_critical=False)
                    fort_note = ""
                    if getattr(cur_target, 'last_undead_fortitude_triggered', False):
                        f_info = getattr(cur_target, 'undead_fortitude_details', {}) or {}
                        fort_note = f" 🧟 [Undead Fortitude: Remained at 1 HP (DC {f_info.get('dc', 0)})!]"

                    cond_applied = None
                    if not saved and matched_action.conditions_inflicted.exists():
                        for c in matched_action.conditions_inflicted.all():
                            if not is_condition_immune(cur_target, c.name):
                                cur_target.conditions.add(c)
                                cond_applied = c.name
                                if c.name.lower() == 'prone' and getattr(cur_target, 'is_flying', False):
                                    fall_dmg, fall_msg = cur_target.handle_flying_fall(session)
                                    if fall_msg:
                                        summary_messages.append(fall_msg)

                    if not saved:
                        last_saved = False
                    last_damage = target_damage
                    last_target_hp = cur_target.current_hp
                    last_cond = cond_applied
                    last_s_roll = s_roll
                    last_s_total = s_total

                    save_desc = f"{cur_target.get_name()} rolled {s_breakdown} + {save_mod} = {s_total} vs DC {save_dc} {save_ability} save ({'SUCCESS' if saved else 'FAILED'}). Took {target_damage} {dmg_type or 'damage'}.{lr_note}{fort_note}"
                    if cond_applied:
                        save_desc += f" Inflicted {cond_applied}!"
                    summary_messages.append(save_desc)

                    CombatAction.objects.create(
                        combat_session=session,
                        actor=attacker,
                        target=cur_target,
                        action_type='attack',
                        attack_name=matched_action.name,
                        attack_roll=s_roll,
                        attack_modifier=save_mod,
                        attack_total=s_total,
                        hit=not saved,
                        damage_amount=target_damage,
                        damage_type=first_dr.damage_type if first_dr else None,
                        round_number=session.current_round,
                        turn_number=session.current_turn_index,
                        description=save_desc,
                    )

                if matched_action.has_recharge:
                    if attacker.recharge_state is None:
                        attacker.recharge_state = {}
                    attacker.recharge_state[matched_action.name] = False

                attacker.attacks_remaining = 0
                attacker.action_used = True
                update_fields = ['attacks_remaining', 'action_used']
                if matched_action.has_recharge:
                    update_fields.append('recharge_state')
                attacker.save(update_fields=update_fields)

                overall_msg = f"{attacker.get_name()} uses {matched_action.name}! " + " ".join(summary_messages)

                return Response({
                    "message": overall_msg,
                    "saving_throw": {
                        "ability": save_ability,
                        "dc": save_dc,
                        "roll": last_s_roll,
                        "total": last_s_total,
                        "saved": last_saved,
                    },
                    "hit": not last_saved,
                    "damage": last_damage,
                    "target_hp": last_target_hp,
                    "attacks_remaining": 0,
                    "condition_applied": last_cond,
                    "breakdown": {"save": " ".join(summary_messages)},
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
        extra_info = []

        # Ranger Favored Enemy detection
        is_favored = False
        favored_enemy_type = None
        if hasattr(attacker, 'is_favored_enemy') and attacker.is_favored_enemy(target):
            is_favored = True
            favored_enemy_type = target.get_creature_type() if hasattr(target, 'get_creature_type') else 'humanoid'
        foe_slayer_used_on_attack = False
        
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
                    if hasattr(attacker, 'has_sharpshooter') and attacker.has_sharpshooter():
                        pass  # Sharpshooter: Attacking at long range does not impose disadvantage
                    else:
                        disadvantage = True
                        if f"Long Range ({dist} ft > {normal_range} ft)" not in disadv_reasons:
                            disadv_reasons.append(f"Long Range ({dist} ft > {normal_range} ft)")

        # Check cover before rolling
        cover_bonus = 0
        target_has_full_cover = False
        target_position = None
        target_cover_type = None
        target_cover_source = None

        # 1. Directional & line-of-sight cover calculation (5e rules)
        # - Melee attacks within reach suffer NO cover from terrain props
        # - Ranged attacks suffer Total Cover (cannot be targeted) if solid obstacles block line of sight
        # - Ranged attacks suffer Half Cover (+2 AC) if low obstacles (barricades, crates) intervene
        if has_coords:
            from combat.battlefield import get_attack_cover
            t_tiles = target.get_size_dimensions()['tiles'] if hasattr(target, 'get_size_dimensions') else 1
            attack_cover = get_attack_cover(
                session.id or 0,
                attacker.position_x,
                attacker.position_y,
                target.position_x,
                target.position_y,
                is_melee=is_melee,
                target_size_tiles=t_tiles,
            )
            if attack_cover.get('has_total_cover'):
                target_has_full_cover = True
                target_cover_source = attack_cover.get('source')
            else:
                cover_bonus = attack_cover.get('cover_bonus', 0)
                target_cover_type = attack_cover.get('cover_type')
                target_cover_source = attack_cover.get('source')

        # 2. Also check ParticipantPosition.current_cover if set by EnvironmentalEffect (e.g. trench on tile)
        if not target_has_full_cover:
            try:
                target_position = target.position
                if target_position.current_cover:
                    env_cover = target_position.current_cover
                    env_bonus = calculate_cover_ac_bonus(env_cover)
                    if env_bonus > cover_bonus:
                        cover_bonus = env_bonus
                        target_cover_type = env_cover
                        target_cover_source = "Environmental Cover"
            except ParticipantPosition.DoesNotExist:
                pass

        # 5e Sharpshooter: Ranged weapon attacks ignore half cover and three-quarters cover
        if not is_melee and hasattr(attacker, 'has_sharpshooter') and attacker.has_sharpshooter():
            cover_bonus = 0
            if target_cover_type in ['half', 'three_quarters']:
                target_cover_type = 'none'

        # Total cover prevents targeting directly
        if target_has_full_cover:
            return Response(
                {"error": f"{target.get_name()} has total cover behind {target_cover_source or 'an obstacle'} and cannot be targeted directly."},
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

        # Check 2024 Weapon Mastery: Vex (Advantage on next attack against target)
        if attacker.feature_uses and attacker.feature_uses.get('vex_target_id') == target.id:
            advantage = True
            if "Weapon Mastery: Vex (Advantage vs target)" not in adv_reasons:
                adv_reasons.append("Weapon Mastery: Vex (Advantage vs target)")
            attacker.feature_uses.pop('vex_target_id', None)
            attacker.save(update_fields=['feature_uses'])

        # Check 2024 Weapon Mastery: Sap (Disadvantage on next attack)
        if attacker.feature_uses and attacker.feature_uses.get('sapped'):
            disadvantage = True
            if "Weapon Mastery: Sap (Disadvantage on attack)" not in disadv_reasons:
                disadv_reasons.append("Weapon Mastery: Sap (Disadvantage on attack)")
            attacker.feature_uses.pop('sapped', None)
            attacker.save(update_fields=['feature_uses'])

        # Check Reckless Attack
        if attacker.feature_uses and attacker.feature_uses.get('reckless_attack_active') and is_melee and use_ability == 'STR':
            advantage = True
            adv_reasons.append("Reckless Attack")
        if target.feature_uses and target.feature_uses.get('reckless_attack_active'):
            advantage = True
            adv_reasons.append("Target is Reckless")

        # 5e Grappler Feat: Advantage on attack rolls against a creature you are grappling
        if attacker.has_grappler_feat() and target.grappled_by_id == attacker.id:
            advantage = True
            if "Grappler Feat (Attacking grappled target)" not in adv_reasons:
                adv_reasons.append("Grappler Feat (Attacking grappled target)")

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

        # Check Pack Tactics trait (5e rule: advantage if ally within 5 ft of target and not incapacitated)
        if hasattr(attacker, 'has_trait') and attacker.has_trait('pack_tactics'):
            allies = session.participants.filter(
                participant_type=attacker.participant_type,
                is_active=True,
                current_hp__gt=0
            ).exclude(id=attacker.id)
            for ally in allies:
                if ally.is_incapacitated():
                    continue
                if has_coords:
                    if ally.get_distance_to(target) <= 5:
                        advantage = True
                        if "Pack Tactics" not in adv_reasons:
                            adv_reasons.append("Pack Tactics")
                        break
                else:
                    advantage = True
                    if "Pack Tactics" not in adv_reasons:
                        adv_reasons.append("Pack Tactics")
                    break

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
                has_devils_sight = hasattr(attacker, 'has_devils_sight') and attacker.has_devils_sight()
                lighting_mod = get_lighting_attack_modifier(attacker_position.current_lighting, has_darkvision, has_devils_sight)
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

        # Roll attack with resolved advantage/disadvantage (with Halfling Lucky if applicable)
        attacker_lucky = getattr(attacker, 'has_lucky_trait', lambda: False)()
        roll, roll_breakdown = roll_d20(advantage=final_advantage, disadvantage=final_disadvantage, lucky=attacker_lucky)

        roll_annotation = roll_breakdown
        if final_advantage and adv_reasons:
            roll_annotation = f"{roll_breakdown} [{', '.join(adv_reasons)}]"
        elif final_disadvantage and disadv_reasons:
            roll_annotation = f"{roll_breakdown} [{', '.join(disadv_reasons)}]"
        elif advantage and disadvantage:
            roll_annotation = f"{roll_breakdown} [Adv & Dis Canceled]"
        if attacker_lucky and "Lucky" in roll_breakdown:
            roll_annotation += " 🍀 [Halfling Lucky]"
        
        # Get magic item bonuses
        magic_bonuses = attacker.get_magic_item_bonuses()
        other_modifiers += magic_bonuses['to_hit']

        # 5e Bless buff: add +1d4 to attack rolls
        if hasattr(attacker, 'has_buff') and attacker.has_buff('bless'):
            bless_val = random.randint(1, 4)
            other_modifiers += bless_val
            adv_reasons.append(f"Bless (+{bless_val})")

        # 5e Bane debuff: subtract 1d4 from attack rolls
        if hasattr(attacker, 'has_buff') and attacker.has_buff('bane'):
            bane_val = random.randint(1, 4)
            other_modifiers -= bane_val
            adv_reasons.append(f"Bane (-{bane_val})")

        # 5e Magic Weapon buff: +1 to attack rolls
        if hasattr(attacker, 'has_buff') and attacker.has_buff('magic weapon'):
            other_modifiers += 1
            adv_reasons.append("Magic Weapon (+1)")

        # Paladin Sacred Weapon: add Charisma modifier to attack rolls
        if attacker.feature_uses and attacker.feature_uses.get('sacred_weapon_active'):
            sw_bonus = attacker.feature_uses.get('sacred_weapon_bonus', 0)
            other_modifiers += sw_bonus
            adv_reasons.append(f"Sacred Weapon (+{sw_bonus})")

        # Bardic Inspiration on attack: if actor has bardic inspiration die and chooses to use it
        use_bi = request.data.get('use_bardic_inspiration')
        if attacker.feature_uses and attacker.feature_uses.get('has_bardic_inspiration'):
            die_str = attacker.feature_uses.get('has_bardic_inspiration', 'd6')
            die_sides = int(die_str.replace('d', '')) if 'd' in str(die_str) else 6
            if use_bi:
                bi_roll = random.randint(1, die_sides)
                other_modifiers += bi_roll
                adv_reasons.append(f"Bardic Inspiration (+{bi_roll})")
                attacker.feature_uses.pop('has_bardic_inspiration', None)
        # 5e Fighting Style: Archery (+2 to attack rolls with ranged weapons)
        is_ranged_weapon_attack = False
        if equipped_weapon:
            w_type = str(getattr(equipped_weapon, 'weapon_type', '')).lower()
            is_ranged_weapon_attack = ('ranged' in w_type) or (is_weapon_ranged and not is_weapon_thrown)
        elif not is_melee:
            is_ranged_weapon_attack = True

        if is_ranged_weapon_attack and hasattr(attacker, 'has_fighting_style') and attacker.has_fighting_style('archery'):
            other_modifiers += 2
            adv_reasons.append("Fighting Style: Archery (+2)")

        # 5e Feats: Sharpshooter & Great Weapon Master Power Attack (-5 to hit / +10 to damage)
        is_heavy_weapon = False
        if equipped_weapon:
            if getattr(equipped_weapon, 'heavy', False):
                is_heavy_weapon = True
            elif hasattr(equipped_weapon, 'properties'):
                try:
                    is_heavy_weapon = equipped_weapon.properties.filter(name__icontains='heavy').exists()
                except Exception:
                    pass
        elif any(w in (attack_name or '').lower() for w in ['greatsword', 'greataxe', 'maul', 'halberd', 'glaive', 'pike']):
            is_heavy_weapon = True

        power_attack_req = bool(
            request.data.get('power_attack') or
            request.data.get('sharpshooter') or
            request.data.get('great_weapon_master') or
            (attacker.feature_uses and (
                attacker.feature_uses.get('power_attack') or
                attacker.feature_uses.get('sharpshooter_active') or
                attacker.feature_uses.get('gwm_active')
            ))
        )
        from combat.feats_and_invocations import apply_power_attack_modifiers, trigger_gwm_bonus_attack
        pa_atk_mod, pa_dmg_mod, pa_note = apply_power_attack_modifiers(
            attacker,
            is_ranged=is_ranged_weapon_attack,
            is_heavy=is_heavy_weapon,
            power_attack_requested=power_attack_req
        )
        if pa_atk_mod != 0:
            other_modifiers += pa_atk_mod
            adv_reasons.append(pa_note)

        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, other_modifiers
        )
        
        # Get target's effective AC (including armor, magic items, and cover)
        target_ac = target.calculate_effective_ac(cover_bonus=cover_bonus)
        
        # Check if hit (incorporates expanded critical threshold, e.g. Champion Improved Critical 19-20 / 18-20)
        crit_threshold = attacker.get_critical_threshold() if hasattr(attacker, 'get_critical_threshold') else 20
        is_natural_crit = (roll >= crit_threshold)
        if is_natural_crit:
            hit = True
            critical = True
            if roll < 20:
                adv_reasons.append(f"Improved Critical ({roll} >= {crit_threshold})")
                attack_breakdown += f" | 🎯 Improved Critical ({roll} >= {crit_threshold})"
        else:
            hit = check_hit(attack_total, target_ac)
            critical = False

        # Ranger Level 20 Foe Slayer: can turn a miss into a hit against favored enemy
        if not hit and not is_natural_crit and is_favored and hasattr(attacker, 'has_foe_slayer') and attacker.has_foe_slayer():
            wis_mod = max(1, attacker.get_ability_modifier('WIS'))
            if attack_total + wis_mod >= target_ac:
                attack_total += wis_mod
                hit = True
                f_type_str = (favored_enemy_type or 'Enemy').title()
                attack_breakdown += f" | 🎯 Foe Slayer (+{wis_mod} WIS vs {f_type_str})"
                extra_info.append(f"Foe Slayer (+{wis_mod} to Hit)")
                foe_slayer_used_on_attack = True

        if hit and is_auto_critical(attacker, target, is_melee=is_melee):
            critical = True

        # 5e Sanctuary ward: attacker must make a Wisdom saving throw or attack is thwarted
        if hit and hasattr(target, 'has_buff') and target.has_buff('sanctuary') and not attacker.is_incapacitated():
            sanctuary_buff = target.get_buff('sanctuary')
            s_dc = 13
            if sanctuary_buff and sanctuary_buff.get('caster_id'):
                s_caster = session.participants.filter(id=sanctuary_buff['caster_id']).first()
                if s_caster and hasattr(s_caster, 'get_spell_save_dc'):
                    s_dc = s_caster.get_spell_save_dc() or 13
            w_roll, _ = roll_d20()
            w_mod = attacker.get_ability_modifier('WIS')
            w_total = w_roll + w_mod
            if w_total < s_dc:
                hit = False
                attack_breakdown += f" | 🛡️ Sanctuary: Failed WIS save ({w_total} vs DC {s_dc}) — attack thwarted!"

        # Bard (College of Lore): Cutting Words reaction reduces attack roll
        cutting_words_triggered = False
        cw_bard_id = request.data.get('cutting_words_bard_id')
        if (request.data.get('use_cutting_words') or cw_bard_id) and hit and not critical:
            from combat.subclasses import resolve_cutting_words
            cw_bard = None
            if cw_bard_id:
                cw_bard = session.participants.filter(id=cw_bard_id, is_active=True).first()
            if not cw_bard:
                for p in session.participants.filter(participant_type=target.participant_type, is_active=True):
                    if hasattr(p, 'is_lore_bard') and p.is_lore_bard() and not p.reaction_used and not p.is_incapacitated():
                        cw_bard = p
                        break
            if cw_bard:
                cw_res = resolve_cutting_words(session, cw_bard, attacker, roll_type='attack', roll_value=attack_total)
                if cw_res.get('success'):
                    attack_total = cw_res['modified_value']
                    hit = check_hit(attack_total, target_ac)
                    attack_breakdown += f" | {cw_res.get('annotation')}"
                    cutting_words_triggered = True


        # 5e Defensive Reaction: Shield spell (+5 AC turns hit into a miss)
        shield_reaction_triggered = False
        if hit and not critical and hasattr(target, 'can_use_reaction') and target.can_use_reaction() and not target.is_incapacitated():
            has_shield = False
            if target.participant_type == 'enemy':
                spell_uses = getattr(target, 'spell_uses_remaining', {}) or {}
                if spell_uses.get('Shield', 0) > 0 or spell_uses.get('shield', 0) > 0:
                    has_shield = True
                elif target.has_trait('shield_spell') or target.has_trait('shield'):
                    has_shield = True
                else:
                    enemy_res = target.resolve_enemy()
                    if enemy_res and (
                        enemy_res.actions.filter(name__iexact='shield').exists() or
                        enemy_res.abilities.filter(name__icontains='shield').exists()
                    ):
                        has_shield = True
            elif target.feature_uses and target.feature_uses.get('can_cast_shield'):
                has_shield = True

            if has_shield and attack_total < target_ac + 5:
                target.use_reaction()
                if not isinstance(target.feature_uses, dict):
                    target.feature_uses = {}
                target.feature_uses['shield_spell_active'] = True
                target.save(update_fields=['reaction_used', 'feature_uses'])
                target_ac += 5
                hit = False
                shield_reaction_triggered = True

                try:
                    CombatAction.objects.create(
                        combat_session=session,
                        actor=target,
                        action_type='reaction',
                        attack_name='Shield',
                        is_reaction=True,
                        round_number=session.current_round,
                        turn_number=session.current_turn_index,
                        description=f"⚡ {target.get_name()} casts Shield as a reaction! The shimmering magical barrier (+5 AC) deflects {attacker.get_name()}'s attack!"
                    )
                except Exception:
                    pass

        # Calculate damage if hit or graze
        damage_amount = 0
        damage_breakdown = ""
        concentration_broken = False
        attack_damage_type = None
        attack_resistance_info = None
        extra_info = []
        smite_total = 0
        sa_total = 0
        mastery_res = None

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
                # Add rage damage bonus if Barbarian is raging and makes a melee Strength attack
                rage_bonus = 0
                if attacker.is_raging() and is_melee and use_ability == 'STR':
                    rage_bonus = attacker.get_rage_damage_bonus()

                # 5e Fighting Style: Dueling (+2 damage when wielding a melee weapon in one hand and no other weapons)
                dueling_bonus = 0
                if is_melee and hasattr(attacker, 'has_fighting_style') and attacker.has_fighting_style('dueling'):
                    is_two_handed = False
                    if equipped_weapon:
                        is_two_handed = getattr(equipped_weapon, 'two_handed', False)
                        if not is_two_handed and hasattr(equipped_weapon, 'properties'):
                            try:
                                is_two_handed = equipped_weapon.properties.filter(name__icontains='two-handed').exists()
                            except Exception:
                                pass
                    elif any(w in (attack_name or '').lower() for w in ['greatsword', 'greataxe', 'halberd', 'maul', 'glaive', 'pike']):
                        is_two_handed = True

                    off_hand_weapon = attacker.get_equipped_weapon('off_hand') if hasattr(attacker, 'get_equipped_weapon') else None
                    if not is_two_handed and not off_hand_weapon:
                        dueling_bonus = 2

                # 5e Fighting Style: Great Weapon Fighting (reroll 1s and 2s on damage dice for two-handed / versatile melee weapons)
                reroll_gwf = False
                treat_gwf_3 = False
                if is_melee and hasattr(attacker, 'has_fighting_style') and (attacker.has_fighting_style('great_weapon_fighting') or attacker.has_fighting_style('great weapon')):
                    is_2h_or_versatile = False
                    if equipped_weapon:
                        is_2h_or_versatile = getattr(equipped_weapon, 'two_handed', False) or getattr(equipped_weapon, 'versatile', False)
                        if not is_2h_or_versatile and hasattr(equipped_weapon, 'properties'):
                            try:
                                is_2h_or_versatile = equipped_weapon.properties.filter(name__iregex=r'two-handed|versatile').exists()
                            except Exception:
                                pass
                    elif any(w in (attack_name or '').lower() for w in ['greatsword', 'greataxe', 'halberd', 'maul', 'glaive', 'pike', 'longsword', 'warhammer', 'battleaxe']):
                        is_2h_or_versatile = True

                    if is_2h_or_versatile:
                        is_2024 = False
                        if attacker.character and getattr(attacker.character, 'ruleset_version', '') == '2024':
                            is_2024 = True
                        if is_2024:
                            treat_gwf_3 = True
                        else:
                            reroll_gwf = True

                damage_modifier = damage_ability_mod + magic_bonuses['to_damage'] + rage_bonus + dueling_bonus + pa_dmg_mod
                damage_amount, damage_breakdown = calculate_damage(
                    damage_string, damage_modifier, critical,
                    reroll_ones_and_twos=reroll_gwf,
                    treat_ones_and_twos_as_three=treat_gwf_3
                )
                if dueling_bonus:
                    damage_breakdown += " | ⚔️ Dueling (+2)"
                if pa_dmg_mod > 0:
                    damage_breakdown += f" | {pa_note}"

            # Paladin: Divine Smite
            smite_slot = request.data.get('smite_slot_level') or (1 if request.data.get('use_divine_smite') else None)
            if smite_slot and is_melee and attacker.character and attacker.is_paladin():
                try:
                    smite_slot = int(smite_slot)
                    stats = getattr(attacker.character, 'stats', None)
                    if stats:
                        slots = stats.spell_slots or {}
                        expended = stats.expended_spell_slots or {}
                        s_key = str(smite_slot)
                        max_s = int(slots.get(s_key, 0))
                        used_s = int(expended.get(s_key, 0))
                        if max_s > used_s:
                            expended[s_key] = used_s + 1
                            stats.expended_spell_slots = expended
                            stats.save(update_fields=['expended_spell_slots'])
                            # 2d8 for 1st level, +1d8 per slot level above 1st (max 5d8), +1d8 vs undead/fiend (max 6d8)
                            dice_count = min(5, 1 + smite_slot)
                            if target.is_undead() or target.is_fiend():
                                dice_count = min(6, dice_count + 1)
                            if critical:
                                dice_count *= 2
                            smite_rolls = [random.randint(1, 8) for _ in range(dice_count)]
                            smite_total = sum(smite_rolls)
                            damage_amount += smite_total
                            damage_breakdown += f" | ⚡ Divine Smite ({dice_count}d8): +{smite_total} Radiant ({', '.join(map(str, smite_rolls))})"
                except Exception:
                    pass

            # Rogue: Sneak Attack
            wants_sa = request.data.get('use_sneak_attack', True)
            if wants_sa and attacker.is_rogue() and not attacker.feature_uses.get('sneak_attack_used_this_turn'):
                is_finesse = getattr(equipped_weapon, 'finesse', False)
                if not is_finesse and equipped_weapon and hasattr(equipped_weapon, 'properties'):
                    try:
                        is_finesse = equipped_weapon.properties.filter(name__icontains='finesse').exists()
                    except Exception:
                        pass
                is_finesse_or_ranged = (not is_melee) or is_finesse or (equipped_weapon and 'ranged' in str(getattr(equipped_weapon, 'weapon_type', '')).lower())
                if not is_finesse_or_ranged and not equipped_weapon:
                    is_finesse_or_ranged = True
                
                has_sneak_condition = False
                if final_advantage and not final_disadvantage:
                    has_sneak_condition = True
                elif not (disadvantage or final_disadvantage):
                    allies = session.participants.filter(
                        participant_type=attacker.participant_type,
                        is_active=True,
                        current_hp__gt=0
                    ).exclude(id=attacker.id)
                    for ally in allies:
                        if not ally.is_incapacitated() and target.get_distance_to(ally) <= 5:
                            has_sneak_condition = True
                            break
                
                if is_finesse_or_ranged and has_sneak_condition:
                    rogue_lvl = attacker.character.level or 1
                    sa_dice = max(1, (rogue_lvl + 1) // 2)
                    if critical:
                        sa_dice *= 2
                    sa_rolls = [random.randint(1, 6) for _ in range(sa_dice)]
                    sa_total = sum(sa_rolls)
                    damage_amount += sa_total
                    damage_breakdown += f" | 🗡️ Sneak Attack ({sa_dice}d6): +{sa_total} ({', '.join(map(str, sa_rolls))})"
                    if not isinstance(attacker.feature_uses, dict):
                        attacker.feature_uses = {}
                    attacker.feature_uses['sneak_attack_used_this_turn'] = True
                    attacker.save(update_fields=['feature_uses'])

            # Ranger (Hunter): Colossus Slayer
            wants_cs = request.data.get('use_colossus_slayer', True)
            if wants_cs and hit:
                from combat.subclasses import resolve_colossus_slayer
                cs_dmg, cs_annot = resolve_colossus_slayer(attacker, target, is_critical=critical)
                if cs_dmg > 0:
                    damage_amount += cs_dmg
                    damage_breakdown += f" | {cs_annot}"

            # 5e Spell Damage Riders: Hunter's Mark, Hex, Divine Favor, Crusader's Mantle, Enlarge/Reduce, Magic Weapon
            if hit and hasattr(attacker, 'has_buff'):
                if attacker.has_buff("hunter's mark"):
                    hm_dice = 2 if critical else 1
                    hm_rolls = [random.randint(1, 6) for _ in range(hm_dice)]
                    hm_dmg = sum(hm_rolls)
                    damage_amount += hm_dmg
                    damage_breakdown += f" | 🏹 Hunter's Mark (+{hm_dmg})"
                if attacker.has_buff('hex'):
                    hex_dice = 2 if critical else 1
                    hex_rolls = [random.randint(1, 6) for _ in range(hex_dice)]
                    hex_dmg = sum(hex_rolls)
                    damage_amount += hex_dmg
                    damage_breakdown += f" | 🔮 Hex (+{hex_dmg} necrotic)"
                if attacker.has_buff('divine favor'):
                    df_dice = 2 if critical else 1
                    df_rolls = [random.randint(1, 4) for _ in range(df_dice)]
                    df_dmg = sum(df_rolls)
                    damage_amount += df_dmg
                    damage_breakdown += f" | ⚔️ Divine Favor (+{df_dmg} radiant)"
                if attacker.has_buff("crusader's mantle"):
                    cm_dice = 2 if critical else 1
                    cm_rolls = [random.randint(1, 4) for _ in range(cm_dice)]
                    cm_dmg = sum(cm_rolls)
                    damage_amount += cm_dmg
                    damage_breakdown += f" | ☀️ Crusader's Mantle (+{cm_dmg} radiant)"
                if attacker.has_buff('enlarge/reduce'):
                    en_dice = 2 if critical else 1
                    en_rolls = [random.randint(1, 4) for _ in range(en_dice)]
                    en_dmg = sum(en_rolls)
                    damage_amount += en_dmg
                    damage_breakdown += f" | 🍄 Enlarge (+{en_dmg})"
                if attacker.has_buff('magic weapon'):
                    damage_amount += 1
                    damage_breakdown += " | ⚔️ Magic Weapon (+1)"

            # Ranger Favored Enemy & Foe Slayer damage rider
            if is_favored and hit:
                f_type_str = (favored_enemy_type or 'Enemy').title()
                if not foe_slayer_used_on_attack and hasattr(attacker, 'has_foe_slayer') and attacker.has_foe_slayer():
                    wis_mod = max(1, attacker.get_ability_modifier('WIS'))
                    damage_amount += wis_mod
                    damage_breakdown += f" | 🎯 Foe Slayer (+{wis_mod} WIS vs {f_type_str})"
                    extra_info.append(f"Foe Slayer (+{wis_mod})")
                else:
                    damage_breakdown += f" | 🎯 Favored Enemy ({f_type_str})"
                    extra_info.append(f"Favored Enemy ({f_type_str})")

            _new_hp, concentration_broken = target.take_damage(damage_amount, damage_type=attack_damage_type, is_critical=critical)
            attack_resistance_info = getattr(target, 'last_resistance_info', None)
            if getattr(target, 'last_relentless_endurance_triggered', False):
                damage_breakdown += " | 🛡️ Relentless Endurance: Kept at 1 HP!"
            if getattr(target, 'last_relentless_rage_triggered', False):
                rage_info = getattr(target, 'relentless_rage_details', {}) or {}
                damage_breakdown += f" | 🔥 Relentless Rage: Remained at 1 HP! (rolled {rage_info.get('total', 0)} vs DC {rage_info.get('dc', 10)})"
            if getattr(target, 'last_undead_fortitude_triggered', False):
                fort_info = getattr(target, 'undead_fortitude_details', {}) or {}
                damage_breakdown += f" | 🧟 Undead Fortitude: Remained at 1 HP! (rolled {fort_info.get('total', 0)} vs DC {fort_info.get('dc', 0)})"
            if getattr(target, 'last_death_ward_triggered', False):
                damage_breakdown += " | 🛡️ Death Ward: Ward broke and kept target at 1 HP!"

            # Warlock (Fiend Patron): Dark One's Blessing
            if _new_hp <= 0:
                from combat.subclasses import trigger_dark_ones_blessing
                thp_g = trigger_dark_ones_blessing(attacker, target)
                if thp_g > 0:
                    damage_breakdown += f" | 🔥 Dark One's Blessing: Gained {thp_g} Temp HP!"

            # Great Weapon Master: Bonus action attack on critical hit or reducing a target to 0 HP
            if is_melee and hasattr(attacker, 'has_great_weapon_master') and attacker.has_great_weapon_master():
                from combat.feats_and_invocations import trigger_gwm_bonus_attack
                gwm_granted = trigger_gwm_bonus_attack(attacker, is_critical=critical, target_dropped_to_zero=(_new_hp <= 0))
                if gwm_granted:
                    damage_breakdown += " | ⚔️ Great Weapon Master: Bonus Attack Unlocked!"
                    extra_info.append("Great Weapon Master: Bonus attack unlocked this turn!")

            # Check condition riders on hit (e.g. Wolf bite knock prone)
            if matched_action and matched_action.saving_throw_dc and matched_action.conditions_inflicted.exists():
                rider_ability = matched_action.saving_throw_ability or 'STR'
                rider_dc = matched_action.saving_throw_dc
                t_mod = target.get_ability_modifier(rider_ability)
                rider_adv = False
                for c in matched_action.conditions_inflicted.all():
                    c_low = c.name.lower()
                    if c_low == 'frightened' and getattr(target, 'has_brave_trait', lambda: False)():
                        rider_adv = True
                    elif c_low == 'charmed' and getattr(target, 'has_fey_ancestry', lambda: False)():
                        rider_adv = True
                    elif c_low == 'poisoned' and getattr(target, 'has_dwarven_resilience', lambda: False)():
                        rider_adv = True
                r_roll, r_breakdown = roll_d20(advantage=rider_adv, lucky=getattr(target, 'has_lucky_trait', lambda: False)())
                aura_bon = getattr(target, 'get_aura_of_protection_bonus', lambda: 0)()
                if (r_roll + t_mod + aura_bon) < rider_dc:
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

            # Monk (Warrior of the Open Hand): Open Hand Technique
            is_unarmed_or_monk = (is_melee and (not equipped_weapon or 'unarmed' in (attack_name or '').lower()))
            oht_technique = request.data.get('open_hand_technique')
            flurry_strikes_remaining = (attacker.feature_uses or {}).get('open_hand_flurry_attacks_remaining', 0) if attacker.feature_uses else 0
            if (oht_technique or flurry_strikes_remaining > 0) and hasattr(attacker, 'is_open_hand_monk') and attacker.is_open_hand_monk():
                chosen_tech = oht_technique or 'topple'
                from combat.subclasses import resolve_open_hand_technique
                oht_res = resolve_open_hand_technique(session, attacker, target, chosen_tech)
                if oht_res.get('annotation'):
                    damage_breakdown += f" | {oht_res['annotation']}"
                if flurry_strikes_remaining > 0:
                    attacker.feature_uses['open_hand_flurry_attacks_remaining'] = flurry_strikes_remaining - 1
                    attacker.save(update_fields=['feature_uses'])

            # 2024 Weapon Mastery on Hit (Vex, Topple, Push, Sap, Slow, Cleave)
            from combat.weapon_mastery import apply_mastery_on_hit
            cleave_tid = request.data.get('cleave_target_id')
            mastery_hit_res = apply_mastery_on_hit(
                session=session,
                attacker=attacker,
                target=target,
                weapon_name=attack_name,
                weapon_obj=equipped_weapon,
                damage_amount=damage_amount,
                damage_type=attack_damage_type,
                attack_total=attack_total,
                ability_mod=ability_mod,
                proficiency_bonus=proficiency_bonus,
                is_critical=critical,
                cleave_target_id=cleave_tid
            )
            if mastery_hit_res and mastery_hit_res.get('annotation'):
                damage_breakdown += f" | {mastery_hit_res['annotation']}"
                mastery_res = mastery_hit_res
        else:
            # 2024 Weapon Mastery: Graze (Deal ability modifier damage on miss)
            from combat.weapon_mastery import apply_mastery_on_miss
            graze_res = apply_mastery_on_miss(
                session=session,
                attacker=attacker,
                target=target,
                weapon_name=attack_name,
                weapon_obj=equipped_weapon,
                ability_mod=ability_mod,
                damage_type=attack_damage_type
            )
            if graze_res:
                damage_amount = graze_res['damage_amount']
                damage_breakdown = graze_res['annotation']
                concentration_broken = graze_res['concentration_broken']
                mastery_res = graze_res
        
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
            damage_amount=damage_amount if (hit or damage_amount > 0) else None,
            damage_type=damage_type_fk,
            critical=critical,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            is_advantage=final_advantage,
            is_disadvantage=final_disadvantage,
            description=f"{roll_annotation} | {attack_breakdown}" + (f" | {damage_breakdown}" if (not hit and damage_breakdown) else "")
        )
        
        # 2024 Weapon Mastery: Nick (Off-hand attack made as part of Attack action instead of Bonus Action)
        is_off_hand = request.data.get('is_off_hand') or (weapon_slot == 'off_hand')
        has_nick = attacker.has_weapon_mastery(weapon_name=attack_name, property_name='Nick')
        if is_off_hand:
            if not has_nick:
                attacker.bonus_action_used = True
            else:
                extra_info.append("Nick: No Bonus Action used")

        # Decrement attacks remaining
        attacker.attacks_remaining -= 1
        if attacker.attacks_remaining <= 0:
            attacker.action_used = True
        attacker.save()
        
        if hasattr(session, '_prefetched_objects_cache'):
            session._prefetched_objects_cache.clear()
        fresh_session = self.get_queryset().get(pk=session.pk)
        session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

        extra_info = extra_info or []
        if smite_total:
            extra_info.append(f"Divine Smite (+{smite_total} Radiant)")
        if sa_total:
            extra_info.append(f"Sneak Attack (+{sa_total})")
        msg_suffix = f" ({', '.join(extra_info)})" if extra_info else ""

        return Response({
            "message": f"{attacker.get_name()} attacks {target.get_name()}{msg_suffix}",
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
            "damage": damage_amount if (hit or damage_amount > 0) else 0,
            "resistance_info": attack_resistance_info if (hit or damage_amount > 0) else None,
            "target_hp": target.current_hp,
            "attacks_remaining": attacker.attacks_remaining,
            "is_favored_enemy": is_favored,
            "favored_enemy_type": favored_enemy_type,
            "weapon_mastery": mastery_res,
            "environmental_effects": {
                "cover": cover_bonus > 0,
                "cover_type": target_cover_type,
                "cover_source": target_cover_source,
                "cover_bonus": cover_bonus,
                "lighting": attacker_lighting,
                "lighting_modifier": lighting_modifier,
                "weather": weather_effect.weather_type if weather_effect else None,
                "weather_modifier": weather_modifier,
            },
            "breakdown": {
                "roll": roll_breakdown,
                "attack": attack_breakdown,
                "damage": damage_breakdown if (hit or damage_amount > 0) else None
            },
            "concentration_broken": concentration_broken if (hit or damage_amount > 0) else False,
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
        
        # Metamagic handling (D&D 5e Sorcerer feature)
        metamagic = (data.get('metamagic') or request.data.get('metamagic') or '').strip().lower()
        twinned_target_id = data.get('twinned_target_id') or request.data.get('twinned_target_id')
        careful_target_ids = data.get('careful_target_ids') or request.data.get('careful_target_ids') or []
        metamagic_cost = 0
        metamagic_applied = None
        metamagic_annotation = ""
        empowered_annotation = ""

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
        
        dm_override = data.get('dm_override', False) or request.data.get('dm_override', False)
        # Check if it's caster's turn
        current = session.get_current_participant()
        if not dm_override and current != caster:
            return Response(
                {"error": f"It is not {caster.get_name()}'s turn"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if metamagic:
            from combat.sorcery import can_use_metamagic, METAMAGIC_NAMES
            can_meta, m_cost, meta_reason = can_use_metamagic(caster, metamagic, spell_level=spell_level)
            if not can_meta:
                return Response({"error": meta_reason}, status=status.HTTP_400_BAD_REQUEST)
            metamagic_cost = m_cost
            metamagic_applied = METAMAGIC_NAMES.get(metamagic, metamagic.title())

            if metamagic == 'quickened':
                is_bonus_action = True
            elif metamagic == 'subtle':
                metamagic_annotation = "🔮 Subtle Spell (1 SP): Cast without verbal or somatic components"
        
        # 5e Action Economy: Determine if spell uses a Bonus Action or Main Action
        BONUS_ACTION_SPELLS = {
            'healing word', 'mass healing word', 'misty step', 'spiritual weapon',
            'hunter\'s mark', 'hex', 'sanctuary', 'shield of faith', 'divine favor',
            'expeditious retreat', 'magic weapon'
        }
        clean_spell_name = spell_name.strip().lower()
        if clean_spell_name == 'spare the dying':
            from combat.subclasses import _get_subclass_name, _has_feature_named
            if 'grave' in _get_subclass_name(caster) or _has_feature_named(caster, 'circle of mortality'):
                if request.data.get('as_bonus_action') or (caster.action_used and not caster.bonus_action_used):
                    is_bonus_action = True

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

            # Check remaining spell slots (accounting for created slots via Font of Magic)
            if spell_level and spell_level > 0 and not is_ritual and hasattr(caster.character, 'stats') and caster.character.stats:
                stats = caster.character.stats
                level_str = str(spell_level)
                created_count = int((stats.created_spell_slots or {}).get(level_str, 0))
                has_configured_slots = bool(stats.spell_slots and isinstance(stats.spell_slots, dict) and any(int(v) > 0 for v in stats.spell_slots.values()))
                if has_configured_slots or created_count > 0:
                    base_slots = int(stats.spell_slots.get(level_str, 0)) if (stats.spell_slots and isinstance(stats.spell_slots, dict)) else 0
                    max_slots = base_slots + created_count
                    expended = int((stats.expended_spell_slots or {}).get(level_str, 0))
                    if max_slots <= 0 or expended >= max_slots:
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
        
        # Auto-target self for Self-range spells or self-buffs if no target is specified
        # Metamagic: Twinned Spell adds second target
        if metamagic == 'twinned' and twinned_target_id:
            if not any(t.id == twinned_target_id for t in targets):
                t_twin = session.participants.filter(pk=twinned_target_id, is_active=True, current_hp__gt=0).first()
                if t_twin:
                    targets.append(t_twin)

        if not targets:
            self_buffs = {'shield', 'blur', 'mirror image', 'false life', 'expeditious retreat', 'fire shield', 'armor of agathys', 'blink', 'mage armor'}
            if clean_spell_name in self_buffs:
                targets = [caster]

        primary_target = targets[0] if targets else None

        # Deduct Metamagic sorcery points once casting is validated
        if metamagic and metamagic_cost > 0:
            from combat.sorcery import spend_sorcery_points
            spent = spend_sorcery_points(caster, metamagic_cost)
            if not spent:
                return Response(
                    {"error": f"Failed to spend {metamagic_cost} Sorcery Points for {metamagic_applied}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            metamagic_annotation = f"🔮 {metamagic_applied} ({metamagic_cost} SP)"

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
        SPELL_RANGE_DEFINITIONS = {
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
            'color spray': 'Self (15-foot cone)',
            'cone of cold': 'Self (60-foot cone)',
            'lightning bolt': 'Self (100-foot line)',
            'gust of wind': 'Self (60-foot line)',
            'fear': 'Self (30-foot cone)',
            'prismatic spray': 'Self (60-foot cone)',
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
            'shatter': '60 feet (10-foot radius)',
            'acid splash': '60 feet',
        }

        from combat.aoe_utils import AOE_SPELL_TEMPLATES
        from combat.spell_rules import SPELL_RULES

        rule_def = SPELL_RULES.get(clean_spell_name) or {}

        # Target validation for dead/dying creatures
        is_resurrection = clean_spell_name in {'revivify', 'raise dead', 'resurrection', 'true resurrection'}
        if not is_resurrection:
            for t in targets:
                if t.is_dead():
                    return Response(
                        {"error": f"{t.get_name()} is dead and cannot be targeted by {spell_name}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        if rule_def.get('requires_zero_hp'):
            for t in targets:
                if t.current_hp > 0 or t.is_dead():
                    return Response(
                        {"error": f"{spell_name} can only target a dying creature (at 0 HP and not dead). {t.get_name()} is not dying."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        if not requires_concentration:
            if rule_def.get('requires_concentration'):
                requires_concentration = True
            elif spell_obj:
                if hasattr(spell_obj, 'concentration'):
                    requires_concentration = bool(spell_obj.concentration)
                elif callable(getattr(spell_obj, 'requires_concentration', None)):
                    requires_concentration = bool(spell_obj.requires_concentration())
                else:
                    requires_concentration = bool(getattr(spell_obj, 'requires_concentration', False))

        if 'half_on_save' not in request.data and 'half_on_save' in rule_def:
            half_on_save = rule_def['half_on_save']

        raw_range = None
        if clean_spell_name in SPELL_RANGE_DEFINITIONS:
            raw_range = SPELL_RANGE_DEFINITIONS[clean_spell_name]
        elif clean_spell_name in SPELL_RULES and SPELL_RULES[clean_spell_name].get('range'):
            raw_range = SPELL_RULES[clean_spell_name]['range']
        elif spell_obj and spell_obj.range:
            raw_range = spell_obj.range.strip()

        # Check AoE template definitions (e.g. Thunderwave, Burning Hands) if range is just 'Self'
        aoe_template = AOE_SPELL_TEMPLATES.get(clean_spell_name) or AOE_SPELL_TEMPLATES.get(clean_spell_name.replace(' ', '_'))
        if aoe_template and (not raw_range or raw_range.lower() == 'self'):
            raw_range = f"Self ({aoe_template['size']}-foot {aoe_template['shape']})"

        lower_range = raw_range.lower() if raw_range else ''
        is_aoe_spell = any(s in lower_range for s in ['cone', 'cube', 'sphere', 'cylinder', 'line']) or bool(aoe_template)
        if lower_range:
            if lower_range == 'self' or (lower_range.startswith('self') and not is_aoe_spell):
                for t in targets:
                    if t != caster:
                        return Response(
                            {"error": f"{spell_name} has a range of Self and can only target yourself."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            elif is_aoe_spell and lower_range.startswith('self'):
                # For Self-area spells (e.g. Self (15-foot cube), Self (15-foot cone)),
                # the effect originates from caster; targets in the blast area can be up to area_size + 15 ft away.
                area_match = re.search(r'(\d+)', lower_range)
                max_reach = (int(area_match.group(1)) + 15) if area_match else 30
                for t in targets:
                    if t == caster:
                        continue
                    has_coords = (caster.position_x != 0 or caster.position_y != 0 or t.position_x != 0 or t.position_y != 0)
                    if not has_coords:
                        continue
                    dist = caster.get_distance_to(t)
                    if dist > max_reach:
                        return Response(
                            {"error": f"{spell_name} affects an area originating from you up to {max_reach} ft away, but {t.get_name()} is {dist} ft away."},
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
                        effective_reach = reach
                        if clean_spell_name == 'spare the dying':
                            from combat.subclasses import _get_subclass_name, _has_feature_named
                            if 'grave' in _get_subclass_name(caster) or _has_feature_named(caster, 'circle of mortality'):
                                effective_reach = 30
                        if dist > effective_reach:
                            if effective_reach > reach:
                                return Response(
                                    {"error": f"{spell_name} (Circle of Mortality 30 ft range): {t.get_name()} is {dist} ft away. Move closer first!"},
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            return Response(
                                {"error": f"{spell_name} is a Touch spell: {t.get_name()} is {dist} ft away (maximum reach is {reach} ft). Move closer first!"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    else:
                        range_match = re.search(r'(\d+)', lower_range)
                        if range_match:
                            max_range = int(range_match.group(1))
                            allowed_dist = (max_range + 20) if is_aoe_spell else max_range
                            if dist > allowed_dist:
                                return Response(
                                    {"error": f"{spell_name} has a range of {max_range} ft, but {t.get_name()} is {dist} ft away."},
                                    status=status.HTTP_400_BAD_REQUEST
                                )

        # 5e Line of Sight & Total Cover check for targeted spells
        # (Spells requiring a target cannot target a creature behind Total Cover)
        if not is_aoe_spell and not is_healing:
            from combat.battlefield import get_attack_cover
            for t in set(targets):
                if t.id == caster.id:
                    continue
                if caster.position_x is not None and t.position_x is not None:
                    is_touch_spell = 'touch' in lower_range
                    t_tiles = t.get_size_dimensions()['tiles'] if hasattr(t, 'get_size_dimensions') else 1
                    t_cover = get_attack_cover(
                        session.id or 0,
                        caster.position_x,
                        caster.position_y,
                        t.position_x,
                        t.position_y,
                        is_melee=is_touch_spell,
                        target_size_tiles=t_tiles,
                    )
                    if t_cover.get('has_total_cover'):
                        return Response(
                            {"error": f"{t.get_name()} has total cover behind {t_cover.get('source', 'an obstacle')} and cannot be targeted by {spell_name}."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

        # 5e Counterspell Reaction Interception
        counter_req = request.data.get('counterspell')
        if counter_req:
            counter_p_id = counter_req.get('participant_id')
            counter_slot = int(counter_req.get('slot_level', 3))
            try:
                counter_actor = session.participants.get(pk=counter_p_id)
                from combat.reaction_spells import resolve_counterspell
                is_countered, c_details = resolve_counterspell(
                    counter_actor, caster, clean_spell_name, spell_level or 1, counter_slot
                )
                if is_countered:
                    # Spell fails: consume caster's slot and action
                    if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
                        if spell_level and spell_level > 0 and not is_ritual:
                            stats = caster.character.stats
                            level_str = str(spell_level)
                            if not stats.expended_spell_slots:
                                stats.expended_spell_slots = {}
                            stats.expended_spell_slots[level_str] = stats.expended_spell_slots.get(level_str, 0) + 1
                            stats.save(update_fields=['expended_spell_slots'])
                    elif caster.encounter_enemy:
                        caster.use_enemy_spell(spell_name)
                    if is_bonus_action:
                        caster.bonus_action_used = True
                        caster.save(update_fields=['bonus_action_used'])
                    else:
                        caster.action_used = True
                        caster.save(update_fields=['action_used'])

                    CombatAction.objects.create(
                        combat_session=session,
                        actor=counter_actor,
                        target=caster,
                        action_type='reaction',
                        attack_name='Counterspell',
                        is_reaction=True,
                        round_number=session.current_round,
                        turn_number=session.current_turn_index,
                        description=c_details['message']
                    )
                    return Response({
                        "countered": True,
                        "message": c_details['message'],
                        "counterspell": c_details
                    }, status=status.HTTP_200_OK)
            except CombatParticipant.DoesNotExist:
                pass

        # 5e Dispel Magic resolution
        if clean_spell_name == 'dispel magic' and targets:
            target = targets[0]
            from combat.reaction_spells import resolve_dispel_magic
            dispelled, d_details = resolve_dispel_magic(caster, target, spell_level or 3)
            # Consume slot
            if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
                stats = caster.character.stats
                level_str = str(spell_level or 3)
                if not stats.expended_spell_slots:
                    stats.expended_spell_slots = {}
                stats.expended_spell_slots[level_str] = stats.expended_spell_slots.get(level_str, 0) + 1
                stats.save(update_fields=['expended_spell_slots'])
            caster.action_used = True
            caster.save(update_fields=['action_used'])

            act = CombatAction.objects.create(
                combat_session=session,
                actor=caster,
                target=target,
                action_type='spell',
                attack_name='Dispel Magic',
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=d_details['message']
            )
            return Response({
                "message": d_details['message'],
                "dispelled": dispelled,
                "details": d_details,
                "target_buffs": target.get_active_buffs(),
                "action": CombatActionSerializer(act).data
            }, status=status.HTTP_200_OK)

        # Handle concentration
        if requires_concentration:
            if caster.is_concentrating and caster.concentration_spell != spell_name:
                try:
                    from combat.spell_rules import remove_caster_concentration_buffs
                    remove_caster_concentration_buffs(caster)
                except Exception:
                    pass
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
                if hasattr(caster, 'has_buff') and caster.has_buff('haste') and caster.attacks_remaining > 1:
                    caster.attacks_remaining = 1
                else:
                    caster.attacks_remaining = 0
                caster.save(update_fields=['action_used', 'attacks_remaining'])

            # Description summary
            if len(target_darts) == 1:
                desc = combat_actions[0].description
            else:
                total_all_dmg = sum(tr["damage"] for tr in target_results)
                desc = f"{caster.get_name()} casts Magic Missile, firing {total_missile_darts} darts across {len(target_darts)} targets for {total_all_dmg} force damage total"

            # Decrement player character spell slots (prefer consuming created slots from Font of Magic)
            if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
                if spell_level and spell_level > 0 and not is_ritual:
                    stats = caster.character.stats
                    level_str = str(spell_level)
                    created = stats.created_spell_slots or {}
                    if int(created.get(level_str, 0)) > 0:
                        created[level_str] = int(created[level_str]) - 1
                        stats.created_spell_slots = created
                        stats.save(update_fields=['created_spell_slots'])
                    else:
                        if not stats.expended_spell_slots or not isinstance(stats.expended_spell_slots, dict):
                            stats.expended_spell_slots = {}
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

        # Dedicated resolution for Power Word Kill (5e 9th-level enchantment: target with <= 100 HP dies instantly)
        if clean_spell_name == 'power word kill' and targets:
            target = targets[0]
            target_hp = target.current_hp or 0
            killed = False
            if target_hp <= 100:
                killed = True
                _new_hp, conc_broken = target.take_damage(target_hp, damage_type='necrotic', is_critical=False)
                pwk_desc = f"💀 {caster.get_name()} utters Power Word Kill! {target.get_name()} ({target_hp} HP ≤ 100) dies instantly!"
            else:
                pwk_desc = f"{caster.get_name()} utters Power Word Kill on {target.get_name()}, but they have {target_hp} HP (>100 HP) and are unaffected!"

            if is_bonus_action:
                caster.bonus_action_used = True
                caster.save(update_fields=['bonus_action_used'])
            else:
                caster.action_used = True
                caster.save(update_fields=['action_used'])

            if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
                if spell_level and spell_level > 0 and not is_ritual:
                    stats = caster.character.stats
                    level_str = str(spell_level)
                    if not stats.expended_spell_slots:
                        stats.expended_spell_slots = {}
                    stats.expended_spell_slots[level_str] = stats.expended_spell_slots.get(level_str, 0) + 1
                    stats.save(update_fields=['expended_spell_slots'])
            elif caster.encounter_enemy:
                caster.use_enemy_spell(spell_name)

            act = CombatAction.objects.create(
                combat_session=session,
                actor=caster,
                target=target,
                action_type='spell',
                attack_name='Power Word Kill',
                damage_amount=target_hp if killed else 0,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=pwk_desc
            )

            if hasattr(session, '_prefetched_objects_cache'):
                session._prefetched_objects_cache.clear()
            fresh_session = self.get_queryset().get(pk=session.pk)
            session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

            return Response({
                "message": pwk_desc,
                "spell_name": spell_name,
                "spell_level": spell_level,
                "target": target.get_name(),
                "target_id": target.id,
                "target_hp": target.current_hp,
                "target_results": [{
                    "target_id": target.id,
                    "target_name": target.get_name(),
                    "target_hp": target.current_hp,
                    "killed": killed,
                    "damage": target_hp if killed else 0,
                }],
                "action": CombatActionSerializer(act).data,
                "session": session_data
            }, status=status.HTTP_200_OK)

        # Dedicated resolution for Power Word Stun (5e 8th-level enchantment: target with <= 150 HP is stunned)
        if clean_spell_name == 'power word stun' and targets:
            target = targets[0]
            target_hp = target.current_hp or 0
            stunned = False
            if target_hp <= 150:
                stunned = True
                try:
                    from bestiary.models import Condition
                    c_stun = Condition.objects.filter(name__iexact='stunned').first()
                    if c_stun:
                        target.conditions.add(c_stun)
                except Exception:
                    pass
                pws_desc = f"⚡ {caster.get_name()} speaks Power Word Stun! {target.get_name()} ({target_hp} HP ≤ 150) is stunned!"
            else:
                pws_desc = f"{caster.get_name()} speaks Power Word Stun on {target.get_name()}, but they have {target_hp} HP (>150 HP) and are unaffected!"

            if is_bonus_action:
                caster.bonus_action_used = True
                caster.save(update_fields=['bonus_action_used'])
            else:
                caster.action_used = True
                caster.save(update_fields=['action_used'])

            if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
                if spell_level and spell_level > 0 and not is_ritual:
                    stats = caster.character.stats
                    level_str = str(spell_level)
                    if not stats.expended_spell_slots:
                        stats.expended_spell_slots = {}
                    stats.expended_spell_slots[level_str] = stats.expended_spell_slots.get(level_str, 0) + 1
                    stats.save(update_fields=['expended_spell_slots'])
            elif caster.encounter_enemy:
                caster.use_enemy_spell(spell_name)

            act = CombatAction.objects.create(
                combat_session=session,
                actor=caster,
                target=target,
                action_type='spell',
                attack_name='Power Word Stun',
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=pws_desc
            )

            if hasattr(session, '_prefetched_objects_cache'):
                session._prefetched_objects_cache.clear()
            fresh_session = self.get_queryset().get(pk=session.pk)
            session_data = self.get_serializer(fresh_session).data if hasattr(self, 'get_serializer') else CombatSessionSerializer(fresh_session).data

            return Response({
                "message": pws_desc,
                "spell_name": spell_name,
                "spell_level": spell_level,
                "target": target.get_name(),
                "target_id": target.id,
                "target_hp": target.current_hp,
                "target_results": [{
                    "target_id": target.id,
                    "target_name": target.get_name(),
                    "target_hp": target.current_hp,
                    "stunned": stunned,
                    "condition_applied": "stunned" if stunned else None,
                }],
                "action": CombatActionSerializer(act).data,
                "session": session_data
            }, status=status.HTTP_200_OK)

        healing_spell_names = {'cure wounds', 'healing word', 'prayer of healing', 'mass cure wounds', 'heal', 'mass heal'}
        if is_healing or clean_spell_name in healing_spell_names:
            is_healing = True

        # For offensive AoE spells (e.g. Thunderwave, Burning Hands, Cone of Cold),
        # exclude caster from being targeted or damaged by their own blast
        if is_aoe_spell and not is_healing:
            targets = [t for t in targets if t.id != caster.id]

        # Resolve fallbacks for save_type, damage_string, and damage_type from spell rules if not provided
        rule_def = rule_def or SPELL_RULES.get(clean_spell_name) or {}

        # 5e Cantrip scaling based on character level / CR & Leveled Spell Upcasting
        from combat.spell_rules import is_cantrip, scale_cantrip_damage, scale_upcast_spell_damage, get_spell_base_level
        caster_lvl = 1
        if caster.character:
            caster_lvl = caster.character.level or 1
        elif caster.encounter_enemy:
            cr_val = getattr(caster.encounter_enemy.enemy, 'challenge_rating', None) or 1
            try:
                caster_lvl = int(float(cr_val))
            except (ValueError, TypeError):
                caster_lvl = 1
        elif hasattr(caster, 'character_level') and caster.character_level:
            caster_lvl = caster.character_level
        elif hasattr(caster, 'level') and caster.level:
            caster_lvl = caster.level

        is_a_cantrip = (spell_level == 0) or is_cantrip(clean_spell_name) or (spell_obj and spell_obj.level == 0)
        base_lvl = get_spell_base_level(clean_spell_name, spell_obj=spell_obj, aoe_template=aoe_template)

        if not damage_string:
            if aoe_template and aoe_template.get('base_damage'):
                base_formula = aoe_template['base_damage']
                if is_a_cantrip:
                    damage_string = scale_cantrip_damage(base_formula, caster_lvl)
                else:
                    damage_string = scale_upcast_spell_damage(clean_spell_name, base_formula, base_lvl, spell_level)
            elif rule_def.get('damage'):
                base_formula = rule_def['damage'].split()[0]
                if is_a_cantrip:
                    damage_string = scale_cantrip_damage(base_formula, caster_lvl)
                else:
                    damage_string = scale_upcast_spell_damage(clean_spell_name, base_formula, base_lvl, spell_level)
            elif rule_def.get('healing'):
                base_formula = rule_def['healing'].split()[0]
                damage_string = scale_upcast_spell_damage(clean_spell_name, base_formula, base_lvl, spell_level)
            elif spell_obj and spell_obj.damage_progression.first():
                base_formula = spell_obj.damage_progression.first().damage_dice
                if is_a_cantrip:
                    damage_string = scale_cantrip_damage(base_formula, caster_lvl)
                else:
                    damage_string = scale_upcast_spell_damage(clean_spell_name, base_formula, base_lvl, spell_level)
        elif is_a_cantrip and caster_lvl >= 5:
            # If an unscaled 1-die cantrip formula (e.g. "1d10") was passed, scale it to match character level
            damage_string = scale_cantrip_damage(damage_string, caster_lvl)
        elif not is_a_cantrip and spell_level:
            if int(spell_level) > base_lvl:
                damage_string = scale_upcast_spell_damage(clean_spell_name, damage_string, base_lvl, spell_level)
        if not save_type:
            if aoe_template and aoe_template.get('save_type'):
                save_type = aoe_template['save_type'].upper()
            elif rule_def.get('save_type'):
                save_type = rule_def['save_type'].upper()
        if not spell_damage_type:
            if aoe_template and aoe_template.get('damage_type'):
                spell_damage_type = aoe_template['damage_type']
            elif rule_def.get('damage_type'):
                spell_damage_type = rule_def['damage_type']
        if save_type and not save_dc:
            save_dc = caster.get_spell_save_dc() or 13

        # Roll base damage/healing once (5e rules: AoE rolls damage once and applies to all affected)
        base_damage = 0
        if damage_string:
            if metamagic == 'empowered':
                from combat.sorcery import apply_empowered_spell_reroll
                m_dice = re.match(r'(\d+)d(\d+)', damage_string.strip())
                if m_dice:
                    d_count, d_sides = int(m_dice.group(1)), int(m_dice.group(2))
                    initial_rolls = [random.randint(1, d_sides) for _ in range(d_count)]
                    cha_mod = caster.get_ability_modifier('CHA')
                    new_rolls, new_sum, emp_note = apply_empowered_spell_reroll(d_count, d_sides, cha_mod, initial_rolls)
                    base_damage = new_sum
                    empowered_annotation = emp_note
                else:
                    base_damage, _ = calculate_damage(damage_string, 0, False)
            else:
                base_damage, _ = calculate_damage(damage_string, 0, False)

        # Sorcerer (Draconic Sorcery): Elemental Affinity adds CHA mod to matching elemental spell damage
        if damage_string and not is_healing and base_damage > 0:
            from combat.subclasses import apply_elemental_affinity_damage
            ea_bonus, ea_annot = apply_elemental_affinity_damage(caster, spell_damage_type, base_damage)
            if ea_bonus > 0:
                base_damage += ea_bonus
                if 'damage_breakdown' in locals() and damage_breakdown:
                    damage_breakdown += f" | {ea_annot}"
                rider_str = f" [{ea_annot}]" if not 'rider_str' in locals() else f"{rider_str} [{ea_annot}]"

        # Warlock (Eldritch Invocation): Agonizing Blast adds CHA mod to Eldritch Blast
        if clean_spell_name == 'eldritch blast' and base_damage > 0:
            from combat.feats_and_invocations import apply_agonizing_blast_bonus
            m_eb = re.match(r'(\d+)d10', (damage_string or '').strip())
            eb_beams = int(m_eb.group(1)) if m_eb else 1
            ab_bonus, ab_annot = apply_agonizing_blast_bonus(caster, clean_spell_name, beam_count=eb_beams)
            if ab_bonus > 0:
                base_damage += ab_bonus
                rider_str = f" [{ab_annot}]" if not 'rider_str' in locals() else f"{rider_str} [{ab_annot}]"

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

            # Dedicated 5e Toll the Dead calculation (1d8 necrotic if uninjured, 1d12 necrotic if injured)
            if clean_spell_name == 'toll the dead':
                dice_die = '1d12' if (t.current_hp is not None and t.max_hp is not None and t.current_hp < t.max_hp) else '1d8'
                t_formula = scale_cantrip_damage(dice_die, caster_lvl)
                current_base_damage, _ = calculate_damage(t_formula, 0, False)
                if t == primary_target or not damage_string:
                    damage_string = t_formula
            else:
                current_base_damage = base_damage

            rider_str = ""
            if is_healing:
                from combat.spell_rules import can_heal_target
                if not can_heal_target(t, spell_name):
                    t_healing = 0
                    c_type = getattr(getattr(t.encounter_enemy, 'enemy', None), 'creature_type', 'undead') if t.encounter_enemy else 'undead'
                    rider_str += f" [No effect on {c_type}]"
                else:
                    has_circle_of_mortality = False
                    if caster:
                        from combat.subclasses import _get_subclass_name, _has_feature_named
                        has_circle_of_mortality = bool('grave' in _get_subclass_name(caster) or _has_feature_named(caster, 'circle of mortality'))

                    is_max_healing = (hasattr(t, 'has_buff') and t.has_buff('beacon of hope')) or (has_circle_of_mortality and t.current_hp == 0)
                    if is_max_healing and damage_string:
                        m_dice = re.match(r'(\d+)d(\d+)', damage_string.strip())
                        if m_dice:
                            max_val = int(m_dice.group(1)) * int(m_dice.group(2))
                            mod = caster.get_ability_modifier('WIS') if caster else 0
                            t_healing = max_val + mod
                            if has_circle_of_mortality and t.current_hp == 0:
                                rider_str += " [Circle of Mortality: Max Healing on 0 HP target!]"
                            else:
                                rider_str += " [Beacon of Hope: Max Healing!]"
                        else:
                            t_healing = max(1, current_base_damage)
                    else:
                        t_healing = max(1, current_base_damage)
                    t.heal(t_healing)
            elif (rule_def and rule_def.get('stabilizes_dying')) or clean_spell_name == 'spare the dying':
                if t.current_hp == 0 and not t.is_dead():
                    t.stabilize()
                    rider_str += " [Stabilized at 0 HP]"
                else:
                    rider_str += " [No effect: Target is not dying]"
            elif save_type and save_dc:
                # Metamagic: Careful Spell auto-succeeds for chosen/friendly targets
                is_careful_protected = bool(metamagic == 'careful' and (t.id in careful_target_ids or t.participant_type == caster.participant_type))
                if is_careful_protected:
                    t_save_roll = 20
                    t_save_total = save_dc + 5
                    t_save_success = True
                    rider_str += " [Careful Spell: Auto-Succeeded Save!]"
                elif is_auto_fail_save(t, save_type):
                    t_save_roll = 1
                    save_mod = t.get_ability_modifier(save_type)
                    t_save_total = t_save_roll + save_mod
                    t_save_success = False
                else:
                    target_save_adv = False
                    target_save_disadv = bool(metamagic == 'heightened')
                    if metamagic == 'heightened':
                        rider_str += " [Heightened Spell: Disadvantage on Save]"
                    if save_type.upper() in ['INT', 'WIS', 'CHA'] and getattr(t, 'has_gnome_cunning', lambda: False)():
                        target_save_adv = True
                    if ('charm' in clean_spell_name or 'hypnotic' in clean_spell_name) and getattr(t, 'has_fey_ancestry', lambda: False)():
                        target_save_adv = True
                    if ('fear' in clean_spell_name or 'fright' in clean_spell_name) and getattr(t, 'has_brave_trait', lambda: False)():
                        target_save_adv = True
                    if (spell_damage_type == 'poison' or 'poison' in clean_spell_name) and getattr(t, 'has_dwarven_resilience', lambda: False)():
                        target_save_adv = True
                    if save_type.upper() in ['WIS'] and hasattr(t, 'has_buff') and t.has_buff('beacon of hope'):
                        target_save_adv = True

                    t_save_roll, _ = roll_d20(advantage=target_save_adv, disadvantage=target_save_disadv, lucky=getattr(t, 'has_lucky_trait', lambda: False)())
                    save_mod = t.get_ability_modifier(save_type)
                    prof_bonus = t.character.proficiency_bonus if t.character else 2
                    prof = False
                    if t.character and hasattr(t.character, 'saving_throw_proficiencies') and t.character.saving_throw_proficiencies:
                        prof = save_type.lower() in [s.lower() for s in t.character.saving_throw_proficiencies]
                    aura_bonus = getattr(t, 'get_aura_of_protection_bonus', lambda: 0)()
                    magic_saves_bonus = t.get_magic_item_bonuses().get('to_saves', 0) if hasattr(t, 'get_magic_item_bonuses') else 0
                    save_other_mods = aura_bonus + magic_saves_bonus
                    if hasattr(t, 'has_buff') and t.has_buff('bless'):
                        b_val = random.randint(1, 4)
                        save_other_mods += b_val
                        rider_str += f" [Bless (+{b_val})]"
                    if hasattr(t, 'has_buff') and t.has_buff('bane'):
                        bane_val = random.randint(1, 4)
                        save_other_mods -= bane_val
                        rider_str += f" [Bane (-{bane_val})]"
                    t_save_total, _ = calculate_saving_throw(t_save_roll, save_mod, prof_bonus, prof, other_modifiers=save_other_mods)
                    t_save_success = (t_save_total >= save_dc)
                    if not t_save_success and hasattr(t, 'check_legendary_resistance'):
                        used_lr, t_save_success, lr_msg = t.check_legendary_resistance(save_type, save_dc, t_save_total)
                        if used_lr:
                            rider_str += " [Legendary Resistance Used!]"

                if current_base_damage > 0:
                    if t_save_success:
                        t_damage = (current_base_damage // 2) if half_on_save else 0
                    else:
                        t_damage = current_base_damage
                    if t_damage > 0:
                        _new_hp, concentration_broken = t.take_damage(t_damage, damage_type=spell_damage_type, is_critical=False)
                        if getattr(t, 'last_relentless_endurance_triggered', False):
                            rider_str += " [Relentless Endurance: Kept at 1 HP]"
                        if getattr(t, 'last_relentless_rage_triggered', False):
                            r_info = getattr(t, 'relentless_rage_details', {}) or {}
                            rider_str += f" [Relentless Rage: Remained at 1 HP (DC {r_info.get('dc', 10)})]"
                        if getattr(t, 'last_undead_fortitude_triggered', False):
                            f_info = getattr(t, 'undead_fortitude_details', {}) or {}
                            rider_str += f" [Undead Fortitude: Remained at 1 HP (DC {f_info.get('dc', 0)})]"
                        if _new_hp <= 0:
                            from combat.subclasses import trigger_dark_ones_blessing
                            thp_g = trigger_dark_ones_blessing(caster, t)
                            if thp_g > 0:
                                rider_str += f" [Dark One's Blessing: +{thp_g} Temp HP]"
            elif current_base_damage > 0:
                t_damage = current_base_damage
                _new_hp, concentration_broken = t.take_damage(t_damage, damage_type=spell_damage_type, is_critical=False)
                if getattr(t, 'last_relentless_endurance_triggered', False):
                    rider_str += " [Relentless Endurance: Kept at 1 HP]"
                if getattr(t, 'last_relentless_rage_triggered', False):
                    r_info = getattr(t, 'relentless_rage_details', {}) or {}
                    rider_str += f" [Relentless Rage: Remained at 1 HP (DC {r_info.get('dc', 10)})]"
                if getattr(t, 'last_undead_fortitude_triggered', False):
                    f_info = getattr(t, 'undead_fortitude_details', {}) or {}
                    rider_str += f" [Undead Fortitude: Remained at 1 HP (DC {f_info.get('dc', 0)})]"
                if _new_hp <= 0:
                    from combat.subclasses import trigger_dark_ones_blessing
                    thp_g = trigger_dark_ones_blessing(caster, t)
                    if thp_g > 0:
                        rider_str += f" [Dark One's Blessing: +{thp_g} Temp HP]"

            # 5E Thunderwave & Repelling Blast Forced Movement: Push 10 feet away from caster
            pushed_str = ""
            is_repelling = (clean_spell_name == 'eldritch blast' and t_damage > 0 and hasattr(caster, 'has_eldritch_invocation') and caster.has_eldritch_invocation('repelling_blast'))
            if ((clean_spell_name == 'thunderwave' and t_save_success is False) or is_repelling) and t.is_active and t.current_hp > 0:
                import math
                dx = (t.position_x or 0) - (caster.position_x or 0)
                dy = (t.position_y or 0) - (caster.position_y or 0)
                dist = math.hypot(dx, dy)
                if dist == 0:
                    dx, dy, dist = 1, 0, 1
                dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
                dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
                # D&D 5E: pushed 10 feet away (2 squares)
                if abs(dx) > abs(dy) * 1.5:
                    step_x = dir_x * 10
                    step_y = 0
                elif abs(dy) > abs(dx) * 1.5:
                    step_x = 0
                    step_y = dir_y * 10
                else:
                    step_x = dir_x * 10
                    step_y = dir_y * 10
                # Clamp strictly to battlefield grid boundaries [0, 45] ft cols, [0, 35] ft rows
                new_x = max(0, min(45, (t.position_x or 0) + step_x))
                new_y = max(0, min(35, (t.position_y or 0) + step_y))
                # Check if destination tile is already occupied by another active participant
                occ = session.participants.filter(
                    position_x=new_x, position_y=new_y, is_active=True, current_hp__gt=0
                ).exclude(id=t.id).first()
                if occ:
                    # If blocked at 10 ft, attempt 5 ft push
                    half_x = max(0, min(45, (t.position_x or 0) + (step_x // 2)))
                    half_y = max(0, min(35, (t.position_y or 0) + (step_y // 2)))
                    occ_half = session.participants.filter(
                        position_x=half_x, position_y=half_y, is_active=True, current_hp__gt=0
                    ).exclude(id=t.id).first()
                    if not occ_half:
                        new_x, new_y = half_x, half_y
                    else:
                        new_x, new_y = t.position_x, t.position_y

                if new_x != t.position_x or new_y != t.position_y:
                    t.position_x = new_x
                    t.position_y = new_y
                    t.save(update_fields=['position_x', 'position_y'])
                    try:
                        pos = t.position
                        pos.x = new_x
                        pos.y = new_y
                        pos.save()
                    except Exception:
                        pass
                    blast_source = "Repelling Blast" if is_repelling else "Thunderwave"
                    pushed_str = f" and was blasted 10 ft away by {blast_source} to ({new_x} ft, {new_y} ft)"

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

            # Auto-apply buffs from buff spells (Protection from Evil and Good, Shield of Faith, Bless, Mage Armor, Haste, etc.)
            from combat.spell_rules import is_buff_spell, apply_buff_to_target
            buff_applied = None
            if is_buff_spell(spell_name):
                buff_applied = apply_buff_to_target(caster, t, spell_name, spell_level=spell_level)

            t_resistance_info = getattr(t, 'last_resistance_info', None)
            t_cond_immune = getattr(t, 'last_condition_immune', None)

            target_results.append({
                "target_id": t.id,
                "target_name": t.get_name(),
                "target_hp": t.current_hp,
                "position_x": t.position_x,
                "position_y": t.position_y,
                "pushed": bool(pushed_str),
                "save_roll": t_save_roll,
                "save_total": t_save_total,
                "save_success": t_save_success,
                "damage": t_damage,
                "healing": t_healing,
                "concentration_broken": concentration_broken,
                "condition_applied": t_cond.name if t_cond else None,
                "buff_applied": buff_applied['name'] if buff_applied else None,
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

            buff_str = ""
            if buff_applied:
                buff_str = f" [Buff: {buff_applied['name']}]"

            if buff_applied:
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()}, granting {buff_applied['name']}!{buff_str}{rider_str}"
            elif is_healing:
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()}, restoring {t_healing} HP{cond_str}{rider_str}"
            elif t_damage > 0:
                save_str = f" (rolled {t_save_total} vs DC {save_dc} - {'SAVED' if t_save_success else 'FAILED'})" if save_type else ""
                dmg_type_str = f" {spell_damage_type}" if spell_damage_type else ""
                t_desc = f"{caster.get_name()} casts {spell_name} on {t.get_name()} for {t_damage}{dmg_type_str} damage{save_str}{pushed_str}{resist_str}{cond_str}{rider_str}"
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
                effect_type='hazard',
                hazard_type='spike_growth',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=20,
                description=f"Spike Growth: 20-ft radius spike and thorn field centered at ({effect_origin_x} ft, {effect_origin_y} ft) (Magical Difficult Terrain, 2d4 damage per 5 ft moved)."
            )
        elif clean_spell_name == 'wall of fire':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='hazard',
                hazard_type='wall_of_fire',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=15,
                description=f"Wall of Fire: Blazing wall of fire centered at ({effect_origin_x} ft, {effect_origin_y} ft) (5d8 fire damage on entry/end of turn)."
            )
        elif clean_spell_name == 'moonbeam':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='hazard',
                hazard_type='moonbeam',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=5,
                description=f"Moonbeam: 5-ft radius cylinder of silvery light centered at ({effect_origin_x} ft, {effect_origin_y} ft) (2d10 radiant damage on entry/start of turn)."
            )
        elif clean_spell_name == 'cloudkill':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='hazard',
                hazard_type='cloudkill',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=20,
                description=f"Cloudkill: 20-ft radius sphere of toxic gas centered at ({effect_origin_x} ft, {effect_origin_y} ft) (5d8 poison damage & heavily obscured)."
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
        elif clean_spell_name == 'stinking cloud':
            EnvironmentalEffect.objects.create(
                combat_session=session,
                effect_type='hazard',
                hazard_type='poison_gas',
                hazard_area_x=effect_origin_x,
                hazard_area_y=effect_origin_y,
                hazard_area_radius=20,
                description=f"A 20-ft radius sphere of noxious toxic gas lingers centered at ({effect_origin_x} ft, {effect_origin_y} ft) (Hazard & Heavily Obscured)."
            )

        # 5e Summoning & Persistent Minion / Token Spells
        from combat.summoning import is_summoning_spell, spawn_summon
        summoned_entity = None
        if is_summoning_spell(clean_spell_name):
            target_pos_x = request.data.get('target_x') if request.data.get('target_x') is not None else request.data.get('position_x')
            target_pos_y = request.data.get('target_y') if request.data.get('target_y') is not None else request.data.get('position_y')
            if target_pos_x is None and primary_target and primary_target.id != caster.id:
                target_pos_x = primary_target.position_x
                target_pos_y = primary_target.position_y
            creature_choice = request.data.get('creature_choice')
            summoned_entity = spawn_summon(
                session=session,
                caster=caster,
                spell_name=clean_spell_name,
                position_x=target_pos_x,
                position_y=target_pos_y,
                creature_choice=creature_choice,
                spell_level=spell_level
            )
            # Spiritual Weapon: In 5e, makes an attack on the turn it is cast!
            if clean_spell_name == 'spiritual weapon' and primary_target and primary_target.id != caster.id:
                from combat.summoning import command_summon_action
                command_summon_action(
                    session=session,
                    caster=caster,
                    summon=summoned_entity,
                    command_type='attack',
                    target=primary_target,
                    is_dm_override=True
                )

        # Mark action economy resource as consumed
        if is_bonus_action:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])
        else:
            caster.action_used = True
            if hasattr(caster, 'has_buff') and caster.has_buff('haste') and caster.attacks_remaining > 1:
                caster.attacks_remaining = 1
            else:
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

        # Decrement player character spell slots (prefer consuming created slots from Font of Magic)
        if caster.character and hasattr(caster.character, 'stats') and caster.character.stats:
            if spell_level and spell_level > 0 and not is_ritual:
                stats = caster.character.stats
                level_str = str(spell_level)
                created = stats.created_spell_slots or {}
                if int(created.get(level_str, 0)) > 0:
                    created[level_str] = int(created[level_str]) - 1
                    stats.created_spell_slots = created
                    stats.save(update_fields=['created_spell_slots'])
                else:
                    if not stats.expended_spell_slots or not isinstance(stats.expended_spell_slots, dict):
                        stats.expended_spell_slots = {}
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
            "damage_string": damage_string,
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
            "damage_type": spell_damage_type,
            "condition_applied": first_tr.get("condition_applied"),
            "buff_applied": first_tr.get("buff_applied"),
            "concentration_started": requires_concentration,
            "metamagic": metamagic_applied,
            "metamagic_annotation": metamagic_annotation,
            "empowered_annotation": empowered_annotation,
            "sorcery_points": caster.get_sorcery_points(),
            "action": CombatActionSerializer(combat_actions[0]).data if combat_actions else None,
            "summon": CombatParticipantSerializer(summoned_entity).data if summoned_entity else None,
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
        
        # Gnome Cunning: Advantage on mental saves vs magic
        save_adv = advantage
        if save_type.upper() in ['INT', 'WIS', 'CHA'] and getattr(participant, 'has_gnome_cunning', lambda: False)():
            save_adv = True
        
        # Haste: Advantage on DEX saves
        if save_type.upper() == 'DEX' and hasattr(participant, 'has_buff') and participant.has_buff('haste'):
            save_adv = True

        # Beacon of Hope: Advantage on WIS saves
        if save_type.upper() == 'WIS' and hasattr(participant, 'has_buff') and participant.has_buff('beacon of hope'):
            save_adv = True
        
        roll, roll_breakdown = roll_d20(advantage=save_adv, disadvantage=disadvantage, lucky=getattr(participant, 'has_lucky_trait', lambda: False)())
        ability_mod = participant.get_ability_modifier(save_type)
        proficiency = False
        if participant.character and hasattr(participant.character, 'saving_throw_proficiencies') and participant.character.saving_throw_proficiencies:
            proficiency = save_type.lower() in [s.lower() for s in participant.character.saving_throw_proficiencies]
        aura_bonus = getattr(participant, 'get_aura_of_protection_bonus', lambda: 0)()
        magic_saves_bonus = participant.get_magic_item_bonuses().get('to_saves', 0) if hasattr(participant, 'get_magic_item_bonuses') else 0
        proficiency_bonus = participant.character.proficiency_bonus if participant.character else 2
        save_total, save_breakdown = calculate_saving_throw(roll, ability_mod, proficiency_bonus, proficiency, other_modifiers=aura_bonus + magic_saves_bonus)

        # Bless buff: add +1d4 to saving throws
        bless_save_bonus = 0
        if hasattr(participant, 'has_buff') and participant.has_buff('bless'):
            bless_save_bonus = random.randint(1, 4)
            save_total += bless_save_bonus

        # Bane debuff: subtract 1d4 from saving throws
        bane_save_penalty = 0
        if hasattr(participant, 'has_buff') and participant.has_buff('bane'):
            bane_save_penalty = random.randint(1, 4)
            save_total -= bane_save_penalty

        # Resistance buff: add +1d4 to saving throws
        resistance_save_bonus = 0
        if hasattr(participant, 'has_buff') and participant.has_buff('resistance'):
            resistance_save_bonus = random.randint(1, 4)
            save_total += resistance_save_bonus

        save_success = save_total >= save_dc
        used_legendary_res = False
        lr_msg = ""
        if not save_success and hasattr(participant, 'check_legendary_resistance'):
            used_lr, save_success, lr_msg = participant.check_legendary_resistance(save_type, save_dc, save_total)
            if used_lr:
                used_legendary_res = True

        save_desc = f"{participant.get_name()} makes a {save_type} saving throw (rolled {save_total} vs DC {save_dc} - {'SUCCESS' if save_success else 'FAILED'})"
        if lr_msg:
            save_desc += f". {lr_msg}"
        
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
            description=save_desc
        )
        
        return Response({
            "message": save_desc,
            "save_type": save_type,
            "roll": roll,
            "save_total": save_total,
            "save_dc": save_dc,
            "save_success": save_success,
            "used_legendary_resistance": used_legendary_res,
            "breakdown": {
                "roll": roll_breakdown,
                "save": save_breakdown
            },
            "action": CombatActionSerializer(combat_action).data
        })

    @action(detail=True, methods=['post'])
    def font_of_magic(self, request, pk=None):
        """
        Font of Magic: Convert spell slot to sorcery points, or create a spell slot.
        Payload:
        - participant_id: ID of the participant (Sorcerer)
        - action_type: 'convert_slot' (slot -> points) or 'create_slot' (points -> slot)
        - slot_level: 1 to 5 (or 1 to 9 for convert)
        - dm_override: optional bool
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active"}, status=status.HTTP_400_BAD_REQUEST)

        participant_id = request.data.get('participant_id') or request.data.get('caster_id')
        action_type = request.data.get('action_type')
        slot_level = request.data.get('slot_level')
        dm_override = request.data.get('dm_override', False)

        if not participant_id or not action_type or slot_level is None:
            return Response(
                {"error": "Missing required fields: participant_id, action_type, slot_level"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            slot_level = int(slot_level)
        except (ValueError, TypeError):
            return Response({"error": "slot_level must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found"}, status=status.HTTP_404_NOT_FOUND)

        if not participant.is_active:
            return Response({"error": "Participant is not active"}, status=status.HTTP_400_BAD_REQUEST)

        current = session.get_current_participant()
        if not dm_override and current != participant:
            return Response({"error": f"It is not {participant.get_name()}'s turn"}, status=status.HTTP_400_BAD_REQUEST)

        # 5e: Font of Magic conversion requires a Bonus Action
        if not dm_override and participant.bonus_action_used:
            return Response({"error": f"{participant.get_name()} has already used their bonus action this turn"}, status=status.HTTP_400_BAD_REQUEST)

        from combat.sorcery import convert_slot_to_sorcery_points, create_slot_from_sorcery_points, get_sorcery_points_info

        if action_type == 'convert_slot':
            success, points_gained, msg = convert_slot_to_sorcery_points(participant, slot_level)
            if not success:
                return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        elif action_type == 'create_slot':
            success, cost, msg = create_slot_from_sorcery_points(participant, slot_level)
            if not success:
                return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": f"Invalid action_type: '{action_type}'. Use 'create_slot' or 'convert_slot'."}, status=status.HTTP_400_BAD_REQUEST)

        participant.bonus_action_used = True
        participant.save(update_fields=['bonus_action_used'])

        # Create CombatAction log
        act = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='special',
            attack_name='Font of Magic',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"✨ {participant.get_name()} used Font of Magic: {msg}"
        )

        sp_info = get_sorcery_points_info(participant)
        spell_slots = {}
        expended_spell_slots = {}
        created_spell_slots = {}
        if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
            spell_slots = participant.character.stats.spell_slots
            expended_spell_slots = participant.character.stats.expended_spell_slots
            created_spell_slots = participant.character.stats.created_spell_slots

        return Response({
            "message": msg,
            "action_type": action_type,
            "slot_level": slot_level,
            "sorcery_points": sp_info,
            "spell_slots": spell_slots,
            "expended_spell_slots": expended_spell_slots,
            "created_spell_slots": created_spell_slots,
            "bonus_action_used": participant.bonus_action_used,
            "action": CombatActionSerializer(act).data
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
        
        is_thief = hasattr(user_part, 'is_thief') and user_part.is_thief()
        use_fast_hands = bool(request.data.get('as_bonus_action') or (is_thief and (user_part.action_used or request.data.get('use_fast_hands'))))

        if use_fast_hands:
            if not is_thief and not (user_part.feature_uses and user_part.feature_uses.get('has_fast_hands')):
                return Response({"error": "Only Thief Rogues with Fast Hands can use items as a bonus action."}, status=status.HTTP_400_BAD_REQUEST)
            if user_part.bonus_action_used:
                return Response({"error": f"{user_part.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user_part.action_used or user_part.attacks_remaining <= 0:
                if is_thief and not user_part.bonus_action_used:
                    use_fast_hands = True
                else:
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
        
        # Consume Action or Bonus Action (Fast Hands)
        if use_fast_hands:
            user_part.bonus_action_used = True
            user_part.save(update_fields=['bonus_action_used'])
        else:
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
        action_prefix = "Fast Hands (Bonus Action): " if use_fast_hands else ""
        desc = (
            f"{action_prefix}{user_part.get_name()} drinks a {item_name}, restoring {heal_amount} HP."
            if user_part.id == target.id else
            f"{action_prefix}{user_part.get_name()} administers a {item_name} to {target.get_name()}, restoring {heal_amount} HP."
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
        
        participant_id = request.data.get('participant_id') or request.data.get('actor_id')
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
        
        clean_name = feature_name.strip().lower()
        
        if 'lay on hands' in clean_name:
            if target.participant_type == 'enemy':
                return Response({"error": "Cannot use beneficial features on a hostile enemy."}, status=status.HTTP_400_BAD_REQUEST)
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
            allowed_subactions = ['dash', 'disengage', 'hide']
            is_thief = hasattr(actor, 'is_thief') and actor.is_thief()
            if is_thief:
                allowed_subactions.extend(['use an object', 'fast hands', 'sleight of hand', 'thieves tools'])

            if subaction not in allowed_subactions:
                opts = "Dash, Disengage, or Hide" + (", Use an Object, or Sleight of Hand" if is_thief else "")
                return Response({"error": f"Invalid Cunning Action '{subaction}'. Must be {opts}."}, status=status.HTTP_400_BAD_REQUEST)
            
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
            elif subaction in ['use an object', 'fast hands']:
                extra_desc = f"{actor.get_name()} takes Cunning Action: Fast Hands to manipulate an object or item as a bonus action!"
            elif subaction in ['sleight of hand', 'thieves tools']:
                extra_desc = f"{actor.get_name()} takes Cunning Action: Fast Hands ({subaction.title()})!"
            
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

        elif 'turn undead' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if not actor.is_cleric() and not any('turn undead' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Turn Undead requires Cleric level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            if char_lvl < 2 and not any('turn undead' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Turn Undead requires Cleric level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            remaining_cd = actor.get_channel_divinity_uses_remaining()
            if remaining_cd <= 0:
                return Response({"error": "No Channel Divinity uses remaining (regains after short or long rest)."}, status=status.HTTP_400_BAD_REQUEST)
            
            spell_dc = actor.get_spell_save_dc('WIS')
            has_actor_pos = (actor.position_x is not None and actor.position_y is not None and (actor.position_x != 0 or actor.position_y != 0))
            
            enemies = session.participants.filter(
                participant_type='enemy',
                is_active=True,
                current_hp__gt=0
            )
            undead_in_range = []
            for e in enemies:
                if not e.is_undead():
                    continue
                if has_actor_pos and e.position_x is not None and e.position_y is not None:
                    dist = actor.get_distance_to(e)
                    if dist <= 30:
                        undead_in_range.append(e)
                else:
                    undead_in_range.append(e)
            
            destroy_threshold = None
            if char_lvl >= 17:
                destroy_threshold = 4.0
            elif char_lvl >= 14:
                destroy_threshold = 3.0
            elif char_lvl >= 11:
                destroy_threshold = 2.0
            elif char_lvl >= 8:
                destroy_threshold = 1.0
            elif char_lvl >= 5:
                destroy_threshold = 0.5
            
            results = []
            turned_count = 0
            destroyed_count = 0
            saved_count = 0
            frightened_cond, _ = Condition.objects.get_or_create(name='frightened')
            
            for u in undead_in_range:
                wis_mod = u.get_ability_modifier('WIS')
                r, _ = roll_d20()
                save_total = r + wis_mod
                cr_val = u.get_challenge_rating_value()
                
                if save_total < spell_dc:
                    if destroy_threshold is not None and cr_val <= destroy_threshold:
                        u.current_hp = 0
                        u.is_active = False
                        u.save(update_fields=['current_hp', 'is_active'])
                        destroyed_count += 1
                        results.append(f"💀 {u.get_name()} (CR {cr_val}) failed save ({r}+{wis_mod}={save_total} vs DC {spell_dc}) and is OBLITERATED by Destroy Undead!")
                    else:
                        u.conditions.add(frightened_cond)
                        if not isinstance(u.feature_uses, dict):
                            u.feature_uses = {}
                        u.feature_uses['is_turned'] = True
                        u.feature_uses['turned_by'] = actor.id
                        u.save(update_fields=['feature_uses'])
                        turned_count += 1
                        results.append(f"⚡ {u.get_name()} failed save ({r}+{wis_mod}={save_total} vs DC {spell_dc}) and is TURNED (Frightened for 1 min or until damaged)!")
                else:
                    saved_count += 1
                    results.append(f"🛡️ {u.get_name()} succeeded save ({r}+{wis_mod}={save_total} vs DC {spell_dc}) and resists.")
            
            actor.feature_uses['channel_divinity_uses_remaining'] = remaining_cd - 1
            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
            
            summary_header = f"✨ {actor.get_name()} presents their holy symbol and invokes Channel Divinity: Turn Undead (DC {spell_dc})! "
            if not undead_in_range:
                desc = summary_header + "No undead within 30 feet to censure."
            else:
                desc = summary_header + f"{destroyed_count} destroyed, {turned_count} turned, {saved_count} resisted.\n" + "\n".join(results)
            
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Channel Divinity: Turn Undead',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "destroyed_count": destroyed_count,
                "turned_count": turned_count,
                "saved_count": saved_count,
                "results": results,
                "remaining_uses": actor.feature_uses['channel_divinity_uses_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'preserve life' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            remaining_cd = actor.get_channel_divinity_uses_remaining()
            if remaining_cd <= 0:
                return Response({"error": "No Channel Divinity uses remaining."}, status=status.HTTP_400_BAD_REQUEST)
            
            pool = 5 * char_lvl
            target_id = request.data.get('target_id') or actor.id
            amount = int(request.data.get('amount') or pool)
            amount = max(1, min(amount, pool))
            
            target_participant = session.participants.filter(id=target_id).first() or actor
            if target_participant.participant_type == 'enemy':
                return Response({"error": "Cannot heal a hostile enemy."}, status=status.HTTP_400_BAD_REQUEST)
            
            half_max = target_participant.max_hp // 2
            if target_participant.current_hp >= half_max:
                return Response({"error": f"Preserve Life cannot heal a creature above half their maximum HP ({half_max} HP)."}, status=status.HTTP_400_BAD_REQUEST)
            
            healable = half_max - target_participant.current_hp
            actual_heal = min(amount, healable)
            target_participant.heal(actual_heal)
            
            actor.feature_uses['channel_divinity_uses_remaining'] = remaining_cd - 1
            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
            
            desc = f"✨ {actor.get_name()} invokes Channel Divinity: Preserve Life upon {target_participant.get_name()}, restoring {actual_heal} HP (now {target_participant.current_hp}/{target_participant.max_hp} HP)."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=target_participant,
                action_type='feature',
                attack_name='Channel Divinity: Preserve Life',
                damage_amount=actual_heal,
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "healed_amount": actual_heal,
                "target_hp": target_participant.current_hp,
                "remaining_uses": actor.feature_uses['channel_divinity_uses_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'sacred weapon' in clean_name:
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            remaining_cd = actor.get_channel_divinity_uses_remaining()
            if remaining_cd <= 0:
                return Response({"error": "No Channel Divinity uses remaining."}, status=status.HTTP_400_BAD_REQUEST)
            
            cha_mod = max(1, actor.get_ability_modifier('CHA'))
            actor.feature_uses['sacred_weapon_active'] = True
            actor.feature_uses['sacred_weapon_bonus'] = cha_mod
            actor.feature_uses['channel_divinity_uses_remaining'] = remaining_cd - 1
            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
            
            desc = f"⚔️ {actor.get_name()} imbues their weapon with holy light using Sacred Weapon! Gained +{cha_mod} to attack rolls for 1 minute."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Channel Divinity: Sacred Weapon',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "sacred_weapon_active": True,
                "attack_bonus": cha_mod,
                "remaining_uses": actor.feature_uses['channel_divinity_uses_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'turn the unholy' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            remaining_cd = actor.get_channel_divinity_uses_remaining()
            if remaining_cd <= 0:
                return Response({"error": "No Channel Divinity uses remaining."}, status=status.HTTP_400_BAD_REQUEST)
            
            spell_dc = actor.get_spell_save_dc('CHA')
            has_actor_pos = (actor.position_x is not None and actor.position_y is not None and (actor.position_x != 0 or actor.position_y != 0))
            
            enemies = session.participants.filter(
                participant_type='enemy',
                is_active=True,
                current_hp__gt=0
            )
            targets_in_range = []
            for e in enemies:
                if not (e.is_undead() or e.is_fiend()):
                    continue
                if has_actor_pos and e.position_x is not None and e.position_y is not None:
                    dist = actor.get_distance_to(e)
                    if dist <= 30:
                        targets_in_range.append(e)
                else:
                    targets_in_range.append(e)
            
            results = []
            turned_count = 0
            saved_count = 0
            frightened_cond, _ = Condition.objects.get_or_create(name='frightened')
            
            for t in targets_in_range:
                wis_mod = t.get_ability_modifier('WIS')
                r, _ = roll_d20()
                save_total = r + wis_mod
                
                if save_total < spell_dc:
                    t.conditions.add(frightened_cond)
                    if not isinstance(t.feature_uses, dict):
                        t.feature_uses = {}
                    t.feature_uses['is_turned'] = True
                    t.feature_uses['turned_by'] = actor.id
                    t.save(update_fields=['feature_uses'])
                    turned_count += 1
                    results.append(f"⚡ {t.get_name()} failed save ({r}+{wis_mod}={save_total} vs DC {spell_dc}) and is TURNED!")
                else:
                    saved_count += 1
                    results.append(f"🛡️ {t.get_name()} succeeded save ({r}+{wis_mod}={save_total} vs DC {spell_dc}) and resists.")
            
            actor.feature_uses['channel_divinity_uses_remaining'] = remaining_cd - 1
            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])
            
            desc = f"✨ {actor.get_name()} invokes Turn the Unholy (DC {spell_dc})! {turned_count} turned, {saved_count} resisted.\n" + "\n".join(results)
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Channel Divinity: Turn the Unholy',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "turned_count": turned_count,
                "saved_count": saved_count,
                "remaining_uses": actor.feature_uses['channel_divinity_uses_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'bardic inspiration' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            
            remaining_bi = actor.get_bardic_inspiration_uses_remaining()
            if remaining_bi <= 0:
                return Response({"error": "No Bardic Inspiration uses remaining (regains after long rest, or short rest at level 5+)."}, status=status.HTTP_400_BAD_REQUEST)
            
            if not target_id or int(target_id) == actor.id:
                return Response({"error": "Bardic Inspiration must target an ally other than yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                target_ally = session.participants.get(id=target_id)
            except CombatParticipant.DoesNotExist:
                return Response({"error": "Target ally not found."}, status=status.HTTP_404_NOT_FOUND)
            
            if target_ally.participant_type == 'enemy':
                return Response({"error": "Cannot inspire a hostile enemy."}, status=status.HTTP_400_BAD_REQUEST)
            
            die_size = actor.get_bardic_inspiration_die_size()
            if not isinstance(target_ally.feature_uses, dict):
                target_ally.feature_uses = {}
            target_ally.feature_uses['has_bardic_inspiration'] = die_size
            target_ally.save(update_fields=['feature_uses'])
            
            actor.feature_uses['bardic_inspiration_uses_remaining'] = remaining_bi - 1
            actor.bonus_action_used = True
            actor.save(update_fields=['feature_uses', 'bonus_action_used'])
            
            desc = f"🎵 {actor.get_name()} inspires {target_ally.get_name()} with words of encouragement! {target_ally.get_name()} gains a {die_size} Bardic Inspiration die."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=target_ally,
                action_type='feature',
                attack_name='Bardic Inspiration',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "die_size": die_size,
                "target_id": target_ally.id,
                "remaining_uses": actor.feature_uses['bardic_inspiration_uses_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'flurry of blows' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            ki = actor.get_ki_pool_remaining()
            if ki < 1:
                return Response({"error": "Not enough Ki points (requires 1 Ki)."}, status=status.HTTP_400_BAD_REQUEST)
            
            actor.feature_uses['ki_pool_remaining'] = ki - 1
            actor.bonus_action_used = True
            actor.attacks_remaining += 2
            if hasattr(actor, 'is_open_hand_monk') and actor.is_open_hand_monk():
                actor.feature_uses['open_hand_flurry_attacks_remaining'] = 2
            actor.save(update_fields=['feature_uses', 'bonus_action_used', 'attacks_remaining'])
            
            desc = f"🥋 {actor.get_name()} spends 1 Ki point to unleash a Flurry of Blows! Gained 2 bonus unarmed strikes this turn."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Ki: Flurry of Blows',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "attacks_remaining": actor.attacks_remaining,
                "remaining_ki": actor.feature_uses['ki_pool_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'martial arts' in clean_name or 'bonus unarmed strike' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            actor.bonus_action_used = True
            actor.attacks_remaining += 1
            actor.save(update_fields=['bonus_action_used', 'attacks_remaining'])
            
            desc = f"🥋 {actor.get_name()} uses Martial Arts to make a bonus unarmed strike this turn!"
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Martial Arts: Bonus Strike',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "attacks_remaining": actor.attacks_remaining,
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'patient defense' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            ki = actor.get_ki_pool_remaining()
            if ki < 1:
                return Response({"error": "Not enough Ki points (requires 1 Ki)."}, status=status.HTTP_400_BAD_REQUEST)
            
            actor.feature_uses['ki_pool_remaining'] = ki - 1
            actor.feature_uses['dodge_active'] = True
            actor.bonus_action_used = True
            actor.save(update_fields=['feature_uses', 'bonus_action_used'])
            
            desc = f"🥋 {actor.get_name()} spends 1 Ki point for Patient Defense, taking the Dodge action as a bonus action! Attacks against them have disadvantage."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Ki: Patient Defense',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "dodge_active": True,
                "remaining_ki": actor.feature_uses['ki_pool_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'step of the wind' in clean_name:
            if actor.bonus_action_used:
                return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            ki = actor.get_ki_pool_remaining()
            if ki < 1:
                return Response({"error": "Not enough Ki points (requires 1 Ki)."}, status=status.HTTP_400_BAD_REQUEST)
            
            subaction = request.data.get('subaction', 'disengage').lower()
            actor.feature_uses['ki_pool_remaining'] = ki - 1
            actor.bonus_action_used = True
            if subaction == 'dash':
                actor.movement_used = max(0, actor.movement_used - actor.speed)
                desc = f"🥋 {actor.get_name()} spends 1 Ki point for Step of the Wind: Dash! Movement increased and jump distance doubled."
            else:
                actor.feature_uses['disengaged'] = True
                desc = f"🥋 {actor.get_name()} spends 1 Ki point for Step of the Wind: Disengage! Movement will not provoke opportunity attacks."
            
            actor.save(update_fields=['feature_uses', 'bonus_action_used', 'movement_used'])
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name=f'Ki: Step of the Wind ({subaction.capitalize()})',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "subaction": subaction,
                "remaining_ki": actor.feature_uses['ki_pool_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'stunning strike' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if char_lvl < 5 and not any('stunning strike' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Stunning Strike requires Monk level 5+."}, status=status.HTTP_400_BAD_REQUEST)
            ki = actor.get_ki_pool_remaining()
            if ki < 1:
                return Response({"error": "Not enough Ki points (requires 1 Ki)."}, status=status.HTTP_400_BAD_REQUEST)
            
            if not target_id or int(target_id) == actor.id:
                return Response({"error": "Stunning Strike requires a target creature."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target_creature = session.participants.get(id=target_id)
            except CombatParticipant.DoesNotExist:
                return Response({"error": "Target creature not found."}, status=status.HTTP_404_NOT_FOUND)
            
            ki_dc = actor.get_spell_save_dc('WIS')
            con_mod = target_creature.get_ability_modifier('CON')
            r, _ = roll_d20()
            total_save = r + con_mod
            
            actor.feature_uses['ki_pool_remaining'] = ki - 1
            actor.save(update_fields=['feature_uses'])
            
            stunned_cond, _ = Condition.objects.get_or_create(name='stunned')
            if total_save < ki_dc:
                target_creature.conditions.add(stunned_cond)
                desc = f"⚡ {actor.get_name()} channels Ki into a Stunning Strike! {target_creature.get_name()} failed CON save ({r}+{con_mod}={total_save} vs DC {ki_dc}) and is STUNNED until end of next turn!"
                stun_success = True
            else:
                desc = f"🛡️ {actor.get_name()} attempts Stunning Strike, but {target_creature.get_name()} resisted with CON save ({r}+{con_mod}={total_save} vs DC {ki_dc})."
                stun_success = False
            
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=target_creature,
                action_type='feature',
                attack_name='Stunning Strike',
                hit=stun_success,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "stun_success": stun_success,
                "roll": r,
                "save_total": total_save,
                "dc": ki_dc,
                "remaining_ki": actor.feature_uses['ki_pool_remaining'],
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'wholeness of body' in clean_name:
            if not getattr(actor, 'is_open_hand_monk', lambda: False)():
                return Response({"error": "Wholeness of Body requires Warrior of the Open Hand subclass."}, status=status.HTTP_400_BAD_REQUEST)
            is_2024 = bool(actor.character and getattr(actor.character, 'ruleset_version', '') == '2024')
            if is_2024:
                if actor.bonus_action_used:
                    return Response({"error": f"{actor.get_name()} has already used their bonus action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if actor.action_used or actor.attacks_remaining <= 0:
                    return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)

            max_uses = max(1, actor.get_ability_modifier('WIS')) if is_2024 else 1
            cur_uses = actor.feature_uses.get('wholeness_of_body_uses', 0) if actor.feature_uses else 0
            if cur_uses >= max_uses:
                return Response({"error": f"No uses of Wholeness of Body remaining ({cur_uses}/{max_uses} used)."}, status=status.HTTP_400_BAD_REQUEST)

            from combat.subclasses import resolve_wholeness_of_body
            healed, desc = resolve_wholeness_of_body(actor)
            if not isinstance(actor.feature_uses, dict):
                actor.feature_uses = {}
            actor.feature_uses['wholeness_of_body_uses'] = cur_uses + 1

            if is_2024:
                actor.bonus_action_used = True
                actor.save(update_fields=['bonus_action_used', 'feature_uses'])
            else:
                actor.action_used = True
                actor.attacks_remaining = 0
                actor.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])

            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Wholeness of Body',
                damage_amount=healed,
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "healed": healed,
                "current_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "remaining_uses": max_uses - (cur_uses + 1),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'wild shape' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if char_lvl < 2 and not any('wild shape' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Wild Shape requires Druid level 2+."}, status=status.HTTP_400_BAD_REQUEST)
            
            is_end = ('end' in clean_name) or bool(request.data.get('end_wild_shape', False))
            is_active = bool(actor.feature_uses.get('wild_shaped', False))
            
            if is_end:
                if not is_active:
                    return Response({"error": f"{actor.get_name()} is not currently Wild Shaped."}, status=status.HTTP_400_BAD_REQUEST)
                orig_hp = actor.feature_uses.get('pre_wild_shape_hp', actor.max_hp)
                orig_max_hp = actor.feature_uses.get('pre_wild_shape_max_hp', actor.max_hp)
                orig_ac = actor.feature_uses.get('pre_wild_shape_ac', actor.armor_class)
                beast_name = actor.feature_uses.get('wild_shape_beast', 'Beast')
                
                actor.current_hp = orig_hp
                actor.max_hp = orig_max_hp
                actor.armor_class = orig_ac
                actor.feature_uses['wild_shaped'] = False
                actor.feature_uses['wild_shape_beast'] = None
                actor.save(update_fields=['current_hp', 'max_hp', 'armor_class', 'feature_uses'])
                
                desc = f"🌿 {actor.get_name()} sheds their {beast_name} form and reverts to normal humanoid shape ({orig_hp}/{orig_max_hp} HP, AC {orig_ac})."
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=actor,
                    action_type='feature',
                    attack_name='End Wild Shape',
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "wild_shaped": False,
                    "remaining_uses": actor.get_wild_shape_uses_remaining(),
                    "action": CombatActionSerializer(combat_action).data
                })
            else:
                if is_active:
                    return Response({"error": f"{actor.get_name()} is already Wild Shaped as a {actor.feature_uses.get('wild_shape_beast')}."}, status=status.HTTP_400_BAD_REQUEST)
                rem_uses = actor.get_wild_shape_uses_remaining()
                if rem_uses <= 0:
                    return Response({"error": "No Wild Shape uses remaining (regains after short or long rest)."}, status=status.HTTP_400_BAD_REQUEST)
                
                beast_choice = request.data.get('beast_name', 'Wolf').strip()
                beast_stats = {
                    'wolf': {'name': 'Wolf', 'hp': 11, 'ac': 13, 'speed': 40},
                    'brown bear': {'name': 'Brown Bear', 'hp': 34, 'ac': 11, 'speed': 40},
                    'dire wolf': {'name': 'Dire Wolf', 'hp': 37, 'ac': 14, 'speed': 50},
                    'panther': {'name': 'Panther', 'hp': 13, 'ac': 12, 'speed': 50},
                }
                b = beast_stats.get(beast_choice.lower(), beast_stats['wolf'])
                
                actor.feature_uses['pre_wild_shape_hp'] = actor.current_hp
                actor.feature_uses['pre_wild_shape_max_hp'] = actor.max_hp
                actor.feature_uses['pre_wild_shape_ac'] = actor.armor_class
                actor.feature_uses['wild_shaped'] = True
                actor.feature_uses['wild_shape_beast'] = b['name']
                actor.feature_uses['wild_shape_uses_remaining'] = rem_uses - 1
                
                actor.current_hp = b['hp']
                actor.max_hp = b['hp']
                actor.armor_class = b['ac']
                actor.action_used = True
                actor.attacks_remaining = 0
                actor.save(update_fields=['current_hp', 'max_hp', 'armor_class', 'feature_uses', 'action_used', 'attacks_remaining'])
                
                desc = f"🐾 {actor.get_name()} magically transforms into a {b['name']}! (Gained {b['hp']} Beast HP, AC {b['ac']})"
                combat_action = CombatAction.objects.create(
                    combat_session=session,
                    actor=actor,
                    target=actor,
                    action_type='feature',
                    attack_name=f"Wild Shape: {b['name']}",
                    hit=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
                return Response({
                    "message": desc,
                    "wild_shaped": True,
                    "beast": b,
                    "remaining_uses": actor.feature_uses['wild_shape_uses_remaining'],
                    "action": CombatActionSerializer(combat_action).data
                })

        elif 'indomitable' in clean_name:
            char_lvl = (actor.character.level or 1) if actor.character else 1
            if char_lvl < 9 and not any('indomitable' in f.name.lower() for f in (actor.character.features.all() if actor.character else [])):
                return Response({"error": "Indomitable requires Fighter level 9+."}, status=status.HTTP_400_BAD_REQUEST)
            max_uses = 1 if char_lvl < 13 else (2 if char_lvl < 17 else 3)
            used_count = actor.feature_uses.get('indomitable_used_count', 0)
            if used_count >= max_uses:
                return Response({"error": f"No Indomitable uses remaining ({used_count}/{max_uses} used, regains on long rest)."}, status=status.HTTP_400_BAD_REQUEST)
            
            save_type = request.data.get('save_type', 'CON').upper()
            r, _ = roll_d20()
            save_mod = actor.get_ability_modifier(save_type)
            prof_bonus = actor.character.proficiency_bonus if actor.character else 2
            prof = False
            if actor.character and hasattr(actor.character, 'saving_throw_proficiencies') and actor.character.saving_throw_proficiencies:
                prof = save_type.lower() in [s.lower() for s in actor.character.saving_throw_proficiencies]
            is_2024 = bool(actor.character and getattr(actor.character, 'ruleset_version', '') == '2024')
            fighter_bonus = char_lvl if is_2024 else 0
            aura_bonus = getattr(actor, 'get_aura_of_protection_bonus', lambda: 0)()
            magic_saves_bonus = actor.get_magic_item_bonuses().get('to_saves', 0) if hasattr(actor, 'get_magic_item_bonuses') else 0
            new_total, breakdown = calculate_saving_throw(r, save_mod, prof_bonus, prof, other_modifiers=fighter_bonus + aura_bonus + magic_saves_bonus)
            
            actor.feature_uses['indomitable_used_count'] = used_count + 1
            actor.save(update_fields=['feature_uses'])
            
            bonus_str = f" (including +{fighter_bonus} Fighter level bonus)" if fighter_bonus > 0 else ""
            desc = f"🛡️ {actor.get_name()} draws upon Indomitable to reroll their {save_type} save! New result: {new_total}{bonus_str} ({max_uses - (used_count + 1)} uses left)."
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Indomitable (Save Reroll)',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "new_roll": r,
                "save_total": new_total,
                "remaining_uses": max_uses - (used_count + 1),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'arcane recovery' in clean_name:
            if not actor.has_arcane_recovery():
                return Response({"error": "Arcane Recovery is a Wizard class feature."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.action_used or actor.attacks_remaining <= 0:
                return Response({"error": f"{actor.get_name()} has already used their action this turn."}, status=status.HTTP_400_BAD_REQUEST)
            if actor.is_arcane_recovery_used():
                return Response({"error": "Arcane Recovery can only be used once per day (already expended)."}, status=status.HTTP_400_BAD_REQUEST)

            stats = getattr(actor.character, 'stats', None)
            if not stats or not stats.spell_slots:
                return Response({"error": f"{actor.get_name()} has no spell slots to recover."}, status=status.HTTP_400_BAD_REQUEST)

            expended = dict(stats.expended_spell_slots or {})
            max_recoverable_levels = actor.get_arcane_recovery_max_levels()
            recovered_slots = request.data.get('recovered_slots')
            recovered_details = []

            if recovered_slots and isinstance(recovered_slots, dict):
                # User specified exact slots to recover (e.g. {"1": 2} or {"2": 1})
                total_levels = 0
                for lvl_str, count in recovered_slots.items():
                    try:
                        lvl = int(lvl_str)
                        cnt = int(count)
                    except (ValueError, TypeError):
                        continue
                    if cnt <= 0:
                        continue
                    if lvl >= 6:
                        return Response({"error": "Arcane Recovery cannot recover spell slots of 6th level or higher."}, status=status.HTTP_400_BAD_REQUEST)
                    if lvl < 1:
                        return Response({"error": "Invalid spell slot level."}, status=status.HTTP_400_BAD_REQUEST)
                    exp_count = int(expended.get(str(lvl), 0))
                    if cnt > exp_count:
                        return Response({"error": f"Cannot recover {cnt} level {lvl} slots (only {exp_count} currently expended)."}, status=status.HTTP_400_BAD_REQUEST)
                    total_levels += lvl * cnt

                if total_levels == 0:
                    return Response({"error": "No spell slots chosen for recovery."}, status=status.HTTP_400_BAD_REQUEST)
                if total_levels > max_recoverable_levels:
                    return Response({"error": f"Combined spell slot levels ({total_levels}) exceed Arcane Recovery limit ({max_recoverable_levels} levels)."}, status=status.HTTP_400_BAD_REQUEST)

                for lvl_str, count in recovered_slots.items():
                    cnt = int(count)
                    if cnt > 0:
                        lvl = int(lvl_str)
                        expended[str(lvl)] = max(0, int(expended.get(str(lvl), 0)) - cnt)
                        recovered_details.append(f"{cnt}x Level {lvl}")
            else:
                # Auto-recovery: prioritize highest eligible slots (1..5)
                remaining_levels = max_recoverable_levels
                max_slot_key = max([int(k) for k in stats.spell_slots.keys()] or [1])
                for lvl in range(min(5, max_slot_key), 0, -1):
                    lvl_str = str(lvl)
                    exp_count = int(expended.get(lvl_str, 0))
                    recovered_for_lvl = 0
                    while exp_count > 0 and remaining_levels >= lvl:
                        exp_count -= 1
                        remaining_levels -= lvl
                        recovered_for_lvl += 1
                    if recovered_for_lvl > 0:
                        expended[lvl_str] = exp_count
                        recovered_details.append(f"{recovered_for_lvl}x Level {lvl}")

                if not recovered_details:
                    return Response({"error": "All spell slots (levels 1-5) are already at full capacity."}, status=status.HTTP_400_BAD_REQUEST)

            stats.expended_spell_slots = expended
            stats.save(update_fields=['expended_spell_slots'])

            if not isinstance(actor.feature_uses, dict):
                actor.feature_uses = {}
            actor.feature_uses['arcane_recovery_used'] = True
            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])

            details_str = ", ".join(recovered_details)
            desc = f"🔮 {actor.get_name()} channels Arcane Recovery, drawing upon magical study to restore {details_str} spell slot(s)! (Expended for today)"
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Arcane Recovery',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "recovered": details_str,
                "expended_spell_slots": stats.expended_spell_slots,
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'natural recovery' in clean_name:
            if not actor.is_land_druid():
                return Response({"error": f"{actor.get_name()} is not a Circle of the Land Druid."}, status=status.HTTP_400_BAD_REQUEST)

            from combat.subclasses import resolve_natural_recovery
            slots_to_rec = request.data.get('recovered_slots')
            res = resolve_natural_recovery(actor, slots_to_recover=slots_to_rec)
            if not res.get('success'):
                return Response({"error": res.get('message')}, status=status.HTTP_400_BAD_REQUEST)

            actor.action_used = True
            actor.attacks_remaining = 0
            actor.save(update_fields=['action_used', 'attacks_remaining'])

            desc = res.get('annotation')
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Natural Recovery',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "recovered": res.get('recovered'),
                "action": CombatActionSerializer(combat_action).data
            })

        elif "land's aid" in clean_name or "lands aid" in clean_name:
            if not actor.is_land_druid():
                return Response({"error": f"{actor.get_name()} is not a Circle of the Land Druid."}, status=status.HTTP_400_BAD_REQUEST)

            tx = request.data.get('target_x', actor.position_x or 0)
            ty = request.data.get('target_y', actor.position_y or 0)
            heal_target_id = request.data.get('heal_target_id')
            heal_p = session.participants.filter(id=heal_target_id).first() if heal_target_id else None

            from combat.subclasses import resolve_lands_aid
            res = resolve_lands_aid(session, actor, int(tx), int(ty), heal_target=heal_p)
            if not res.get('success'):
                return Response({"error": res.get('message')}, status=status.HTTP_400_BAD_REQUEST)

            desc = res.get('annotation')
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name="Land's Aid",
                hit=True,
                damage_amount=res.get('damage_base', 0),
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "targets_hit": res.get('targets_hit', []),
                "healed_amount": res.get('healed_amount', 0),
                "healed_target": res.get('healed_target'),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'elemental affinity' in clean_name:
            if not actor.is_draconic_sorcerer():
                return Response({"error": f"{actor.get_name()} is not a Draconic Sorcerer."}, status=status.HTTP_400_BAD_REQUEST)

            from combat.subclasses import activate_elemental_affinity_resistance
            res = activate_elemental_affinity_resistance(actor)
            if not res.get('success'):
                return Response({"error": res.get('message')}, status=status.HTTP_400_BAD_REQUEST)

            desc = res.get('annotation')
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Elemental Affinity Resistance',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "damage_type": res.get('damage_type'),
                "remaining_sorcery_points": res.get('remaining_sorcery_points'),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'dragon wings' in clean_name:
            if not actor.is_draconic_sorcerer():
                return Response({"error": f"{actor.get_name()} is not a Draconic Sorcerer."}, status=status.HTTP_400_BAD_REQUEST)

            manifest = bool(request.data.get('manifest', True))
            from combat.subclasses import toggle_dragon_wings
            res = toggle_dragon_wings(actor, manifest=manifest)
            if not res.get('success'):
                return Response({"error": res.get('message')}, status=status.HTTP_400_BAD_REQUEST)

            actor.bonus_action_used = True
            actor.save(update_fields=['bonus_action_used'])

            desc = res.get('annotation')
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Dragon Wings',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "manifested": res.get('manifested'),
                "fly_speed": res.get('fly_speed', 0),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'cutting words' in clean_name:
            if not actor.is_lore_bard():
                return Response({"error": f"{actor.get_name()} is not a College of Lore Bard."}, status=status.HTTP_400_BAD_REQUEST)

            roll_type = request.data.get('roll_type', 'attack')
            roll_val = int(request.data.get('roll_value', 15))
            from combat.subclasses import resolve_cutting_words
            res = resolve_cutting_words(session, actor, target, roll_type=roll_type, roll_value=roll_val)
            if not res.get('success'):
                return Response({"error": res.get('message')}, status=status.HTTP_400_BAD_REQUEST)

            desc = res.get('annotation')
            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=target,
                action_type='reaction',
                attack_name='Cutting Words',
                is_reaction=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            return Response({
                "message": desc,
                "reduction": res.get('reduction'),
                "modified_value": res.get('modified_value'),
                "remaining_uses": res.get('remaining_uses'),
                "action": CombatActionSerializer(combat_action).data
            })

        elif 'peerless skill' in clean_name:
            if not actor.is_lore_bard():
                return Response({"error": f"{actor.get_name()} is not a College of Lore Bard."}, status=status.HTTP_400_BAD_REQUEST)

            check_tot = int(request.data.get('check_total', 10))
            from combat.subclasses import resolve_peerless_skill
            new_tot, annot = resolve_peerless_skill(actor, check_tot)

            combat_action = CombatAction.objects.create(
                combat_session=session,
                actor=actor,
                target=actor,
                action_type='feature',
                attack_name='Peerless Skill',
                hit=True,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=annot
            )
            return Response({
                "message": annot,
                "original_total": check_tot,
                "new_total": new_tot,
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

        if participant.grappled_by_id:
            grappler_name = participant.grappled_by.get_name() if participant.grappled_by else "another creature"
            return Response({"error": f"{participant.get_name()} is grappled by {grappler_name} and cannot move (speed 0)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_x = int(target_x)
            target_y = int(target_y)
        except (ValueError, TypeError):
            return Response({"error": "target_x and target_y must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        # Snap to 5-ft grid
        target_x = round(target_x / 5.0) * 5
        target_y = round(target_y / 5.0) * 5

        from combat.battlefield import is_tile_solid
        mover_tiles = participant.get_size_dimensions()['tiles'] if hasattr(participant, 'get_size_dimensions') else 1

        # Check full footprint of mover (arena bounds, solid obstacles, and other combatant occupancy)
        for ox in range(mover_tiles):
            for oy in range(mover_tiles):
                cx = target_x + ox * 5
                cy = target_y + oy * 5
                if cx < 0 or cx > 45 or cy < 0 or cy > 35:
                    return Response({
                        "error": f"Creature footprint extends out of arena bounds at ({cx} ft, {cy} ft)."
                    }, status=status.HTTP_400_BAD_REQUEST)
                if is_tile_solid(session.id or 0, cx // 5, cy // 5):
                    return Response({
                        "error": f"Creature footprint overlaps an impassable solid obstacle at ({cx} ft, {cy} ft)."
                    }, status=status.HTTP_400_BAD_REQUEST)
                if session.participants.filter(position_x=cx, position_y=cy, is_active=True, current_hp__gt=0).exclude(id=participant.id).exists():
                    return Response({
                        "error": f"Destination square at ({cx} ft, {cy} ft) is already occupied."
                    }, status=status.HTTP_400_BAD_REQUEST)


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
        mover_halted_by_sentinel = False
        halt_tile = None

        enemies = session.participants.filter(
            is_active=True,
            current_hp__gt=0
        ).exclude(participant_type=participant.participant_type)

        for enemy in enemies:
            if not enemy.can_use_reaction() or enemy.is_incapacitated():
                continue

            # 5e Rules: A creature grappled by the mover is being dragged along and does not get an Opportunity Attack against the grappler
            if participant.is_grappling and (enemy.grappled_by_id == participant.id or enemy in participant.grappling_targets.all()):
                continue

            # Sentinel: Disengage does NOT prevent opportunity attacks from a Sentinel
            if is_disengaged and not (hasattr(enemy, 'has_sentinel') and enemy.has_sentinel()):
                continue

            enemy_x = enemy.position_x
            enemy_y = enemy.position_y
            provoked = False
            provoke_step = -1
            from combat.feats_and_invocations import check_polearm_entry_provocation, apply_sentinel_opportunity_hit
            for step_idx in range(len(move_path) - 1):
                step_from = move_path[step_idx]
                step_to = move_path[step_idx + 1]
                d_from = max(abs(step_from[0] - enemy_x), abs(step_from[1] - enemy_y))
                d_to = max(abs(step_to[0] - enemy_x), abs(step_to[1] - enemy_y))
                if d_from <= 5 and d_to > 5:
                    provoked = True
                    provoke_step = step_idx
                    break
                # Polearm Master: Enter weapon reach provokes opportunity attack
                if check_polearm_entry_provocation(participant, enemy, step_from, step_to):
                    provoked = True
                    provoke_step = step_idx
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
                desc_extra = ""
                if hit:
                    dmg_amount, _ = calculate_damage(dmg_str, critical=(raw_d20 == 20))
                    damage_dealt = max(1, dmg_amount)
                    participant.take_damage(damage_dealt)
                    if participant.current_hp <= 0:
                        mover_fell_unconscious = True
                    # Sentinel: Speed becomes 0 on hit
                    if hasattr(enemy, 'has_sentinel') and enemy.has_sentinel():
                        sentinel_applied, sentinel_msg = apply_sentinel_opportunity_hit(participant, enemy)
                        if sentinel_applied:
                            desc_extra = f" {sentinel_msg}"
                            mover_halted_by_sentinel = True
                            if 0 <= provoke_step < len(move_path):
                                halt_tile = move_path[provoke_step]
                
                desc = f"⚠️ Opportunity Attack! {enemy.get_name()} strikes at {participant.get_name()}: rolled {total_atk} vs AC {target_ac} ({'HIT for ' + str(damage_dealt) + ' dmg' if hit else 'MISSED'}).{desc_extra}"
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
                if mover_fell_unconscious or mover_halted_by_sentinel:
                    break

        # If mover was dropped to 0 HP by an opportunity attack, they collapse at their original tile
        # If halted by Sentinel, they stop at the tile where they were intercepted
        if mover_halted_by_sentinel and not mover_fell_unconscious:
            halt_x, halt_y = halt_tile if halt_tile else (participant.position_x, participant.position_y)
            participant.position_x = halt_x
            participant.position_y = halt_y
            participant.save(update_fields=['position_x', 'position_y'])
            desc = f"{participant.get_name()}'s speed was reduced to 0 by Sentinel! Movement halted at ({halt_x} ft, {halt_y} ft)."
        elif not mover_fell_unconscious:
            participant.position_x = target_x
            participant.position_y = target_y
            participant.movement_used += dist_moved
            participant.save(update_fields=['position_x', 'position_y', 'movement_used'])
            desc = f"{participant.get_name()} moved {dist_moved} ft to ({target_x} ft, {target_y} ft)."

            # 5e Grapple: Drag the grappled victim along with the grappler
            if participant.is_grappling:
                for victim in participant.grappling_targets.filter(is_active=True):
                    candidate_tiles = []
                    if len(move_path) >= 2:
                        candidate_tiles.append(move_path[-2])
                    for dx in [0, -5, 5]:
                        for dy in [0, -5, 5]:
                            if dx == 0 and dy == 0:
                                continue
                            candidate_tiles.append((target_x + dx, target_y + dy))

                    dragged_pos = None
                    for cx, cy in candidate_tiles:
                        if 0 <= cx <= 45 and 0 <= cy <= 35:
                            if not is_tile_solid(session.id or 0, cx // 5, cy // 5):
                                occ = session.participants.filter(
                                    position_x=cx, position_y=cy, is_active=True, current_hp__gt=0
                                ).exclude(id__in=[participant.id, victim.id]).exists()
                                if not occ:
                                    dragged_pos = (cx, cy)
                                    break

                    if dragged_pos:
                        victim.position_x = dragged_pos[0]
                        victim.position_y = dragged_pos[1]
                        victim.save(update_fields=['position_x', 'position_y'])
                        desc += f" Dragging {victim.get_name()} to ({dragged_pos[0]} ft, {dragged_pos[1]} ft)."
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
        
        if hasattr(participant, 'has_buff') and participant.has_buff('haste') and participant.attacks_remaining > 1:
            participant.attacks_remaining -= 1
        else:
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
        
        if hasattr(participant, 'has_buff') and participant.has_buff('haste') and participant.attacks_remaining > 1:
            participant.attacks_remaining -= 1
        else:
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

    @action(detail=True, methods=['post'])
    def set_altitude(self, request, pk=None):
        """
        Change flying altitude or take off / land.
        POST /api/combat/sessions/{id}/set_altitude/
        Payload: { "participant_id": 1, "altitude": 30 }
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active."}, status=status.HTTP_400_BAD_REQUEST)

        participant_id = request.data.get('participant_id')
        target_altitude = request.data.get('altitude')

        if target_altitude is None:
            return Response({"error": "altitude is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_altitude = max(0, int(target_altitude))
        except (ValueError, TypeError):
            return Response({"error": "altitude must be a non-negative integer."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            participant = session.participants.get(id=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Participant not found."}, status=status.HTTP_404_NOT_FOUND)

        if not participant.is_active or participant.current_hp <= 0:
            return Response({"error": f"{participant.get_name()} is defeated and cannot fly."}, status=status.HTTP_400_BAD_REQUEST)

        if participant.is_incapacitated():
            return Response({"error": f"{participant.get_name()} is {participant.get_incapacitating_condition()} and cannot fly."}, status=status.HTTP_400_BAD_REQUEST)

        if participant.grappled_by:
            return Response({"error": f"{participant.get_name()} is grappled and cannot fly (speed 0)."}, status=status.HTTP_400_BAD_REQUEST)

        # Check fly speed
        fly_speed = participant.get_fly_speed()
        if target_altitude > 0 and fly_speed <= 0 and not participant.can_fly():
            return Response({"error": f"{participant.get_name()} does not have a flying speed or spell."}, status=status.HTTP_400_BAD_REQUEST)

        current_alt = participant.altitude or 0
        alt_change = abs(target_altitude - current_alt)

        if alt_change > 0:
            if alt_change > participant.movement_remaining:
                return Response(
                    {"error": f"Changing altitude by {alt_change} ft exceeds remaining movement ({participant.movement_remaining} ft)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            participant.movement_used += alt_change

        old_alt = participant.altitude or 0
        participant.altitude = target_altitude
        participant.is_flying = (target_altitude > 0)
        participant.save(update_fields=['altitude', 'is_flying', 'movement_used'])

        if target_altitude == 0:
            desc = f"{participant.get_name()} descends and touches down on the ground."
        elif old_alt == 0:
            desc = f"🛫 {participant.get_name()} takes flight and ascends to {target_altitude} ft!"
        else:
            direction = "ascends" if target_altitude > old_alt else "descends"
            desc = f"🛫 {participant.get_name()} {direction} to an altitude of {target_altitude} ft."

        CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='move',
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
    def stabilize(self, request, pk=None):
        """Administer first aid to stabilize an unconscious, dying participant (DC 10 Medicine check)."""
        session = self.get_object()
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data
        healer_id = data.get('healer_id') or data.get('actor_id')
        target_id = data.get('target_id')

        if not healer_id or not target_id:
            return Response(
                {"error": "Both healer_id and target_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            healer = session.participants.get(pk=healer_id)
            target = session.participants.get(pk=target_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Healer or target participant not found in combat."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not healer.is_active or healer.current_hp <= 0:
            return Response(
                {"error": f"{healer.get_name()} is defeated and cannot stabilize others."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if healer.is_incapacitated():
            return Response(
                {"error": f"{healer.get_name()} is {healer.get_incapacitating_condition()} and cannot take actions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_dm_override = data.get('dm_override', False)
        current = session.get_current_participant()
        if not is_dm_override and current != healer:
            return Response(
                {"error": f"It is not {healer.get_name()}'s turn."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not is_dm_override and healer.action_used:
            return Response(
                {"error": f"{healer.get_name()} has already used their action this turn."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target.is_dead():
            return Response(
                {"error": f"{target.get_name()} is dead and cannot be stabilized."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target.current_hp > 0:
            return Response(
                {"error": f"{target.get_name()} has {target.current_hp} HP and does not need stabilization."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target.is_stable():
            return Response(
                {"error": f"{target.get_name()} is already stable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reach check: Touch/adjacent (5 ft or healer reach)
        has_coords = (healer.position_x is not None and healer.position_y is not None and
                      target.position_x is not None and target.position_y is not None and
                      (healer.position_x != 0 or healer.position_y != 0 or target.position_x != 0 or target.position_y != 0))
        if has_coords:
            dist = healer.get_distance_to(target)
            reach = healer.get_reach() if hasattr(healer, 'get_reach') else 5
            if dist > reach:
                return Response(
                    {"error": f"{target.get_name()} is {dist} ft away. You must be within reach ({reach} ft) to administer first aid."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check for Healer's Kit
        # In 5e SRD, using a Healer's Kit automatically succeeds at stabilizing without rolling a Medicine check.
        use_healers_kit = data.get('use_healers_kit', False)
        if use_healers_kit:
            kit_ci = None
            if healer.character:
                kit_ci = healer.character.character_items.filter(item__name__icontains="healer's kit").first()
                if not kit_ci:
                    kit_ci = healer.character.character_items.filter(item__name__icontains="healers kit").first()
            if not kit_ci:
                return Response(
                    {"error": f"{healer.get_name()} does not have a Healer's Kit."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if kit_ci.quantity > 1:
                kit_ci.quantity -= 1
                kit_ci.save(update_fields=['quantity'])
            else:
                kit_ci.delete()

            if not is_dm_override:
                healer.action_used = True
                healer.save(update_fields=['action_used'])

            target.stabilize()
            desc = (
                f"🩺 {healer.get_name()} uses a Healer's Kit on {target.get_name()}! "
                f"Automatic success! {target.get_name()} is stabilized at 0 HP."
            )
            CombatAction.objects.create(
                combat_session=session,
                actor=healer,
                target=target,
                action_type='item',
                attack_name="Healer's Kit",
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc
            )
            fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
            return Response({
                "success": True,
                "used_healers_kit": True,
                "message": desc,
                "healer": CombatParticipantSerializer(healer).data,
                "target": CombatParticipantSerializer(target).data,
                "session": CombatSessionSerializer(fresh_session).data
            }, status=status.HTTP_200_OK)

        # Wisdom (Medicine) check vs DC 10
        wis_mod = healer.get_ability_modifier('WIS')
        prof_bonus = 0
        if healer.character:
            cp = healer.character.proficiencies.filter(proficiency_type='skill', skill_name__iexact='medicine').first()
            if cp:
                base_prof = healer.character.proficiency_bonus or 2
                prof_mult = 2 if getattr(cp, 'proficiency_level', 'proficient') == 'expertise' else 1
                prof_bonus = base_prof * prof_mult

        other_mod = 0
        guidance_str = ""
        if hasattr(healer, 'has_buff') and healer.has_buff('guidance'):
            g_val = random.randint(1, 4)
            other_mod += g_val
            guidance_str = f" [Guidance (+{g_val})]"

        manual_roll = data.get('manual_roll') or data.get('roll')
        if manual_roll is not None:
            try:
                roll = int(manual_roll)
            except (ValueError, TypeError):
                roll, _ = roll_d20()
        else:
            roll, _ = roll_d20()

        total = roll + wis_mod + prof_bonus + other_mod
        dc = 10
        success = (total >= dc)

        if not is_dm_override:
            healer.action_used = True
            healer.save(update_fields=['action_used'])

        mod_sign = f"+{wis_mod + prof_bonus + other_mod}" if (wis_mod + prof_bonus + other_mod) >= 0 else f"{wis_mod + prof_bonus + other_mod}"
        if success:
            target.stabilize()
            desc = (
                f"🩺 {healer.get_name()} administers first aid to {target.get_name()} "
                f"(Medicine DC {dc}: rolled {roll} {mod_sign} = {total}{guidance_str}) - Success! "
                f"{target.get_name()} is stabilized at 0 HP."
            )
        else:
            desc = (
                f"🩺 {healer.get_name()} attempts first aid on {target.get_name()} "
                f"(Medicine DC {dc}: rolled {roll} {mod_sign} = {total}{guidance_str}) - Failed."
            )

        CombatAction.objects.create(
            combat_session=session,
            actor=healer,
            target=target,
            action_type='skill_check',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc
        )

        fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
        return Response({
            "success": success,
            "roll": roll,
            "total": total,
            "dc": dc,
            "message": desc,
            "healer": CombatParticipantSerializer(healer).data,
            "target": CombatParticipantSerializer(target).data,
            "session": CombatSessionSerializer(fresh_session).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def command_summon(self, request, pk=None):
        """Command a summoned minion or persistent spell object (e.g. Spiritual Weapon, Flaming Sphere, Animate Dead, Familiar)."""
        session = self.get_object()
        if session.status != 'active':
            return Response({"error": "Combat is not active"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        caster_id = data.get('caster_id') or data.get('actor_id')
        summon_id = data.get('summon_id')
        command_type = data.get('command_type') or data.get('action_type') or 'attack'
        target_id = data.get('target_id')
        dest_x = data.get('destination_x') if data.get('destination_x') is not None else data.get('x')
        dest_y = data.get('destination_y') if data.get('destination_y') is not None else data.get('y')
        attack_index = data.get('attack_index', 0)
        manual_roll = data.get('manual_roll') or data.get('roll')
        is_dm_override = data.get('dm_override', False)

        if not caster_id or not summon_id:
            return Response({"error": "Both caster_id and summon_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            caster = session.participants.get(pk=caster_id)
            summon = session.participants.get(pk=summon_id)
        except CombatParticipant.DoesNotExist:
            return Response({"error": "Caster or summon participant not found in combat."}, status=status.HTTP_404_NOT_FOUND)

        target = None
        if target_id:
            try:
                target = session.participants.get(pk=target_id)
            except CombatParticipant.DoesNotExist:
                return Response({"error": "Target participant not found in combat."}, status=status.HTTP_404_NOT_FOUND)

        from combat.summoning import command_summon_action
        result = command_summon_action(
            session=session,
            caster=caster,
            summon=summon,
            command_type=command_type,
            target=target,
            dest_x=dest_x,
            dest_y=dest_y,
            attack_index=attack_index,
            manual_roll=manual_roll,
            is_dm_override=is_dm_override
        )

        if not result.get('success'):
            return Response({"error": result.get('error', 'Command failed.')}, status=status.HTTP_400_BAD_REQUEST)

        fresh_session = CombatSession.objects.prefetch_related('participants', 'participants__conditions', 'actions').get(id=session.id)
        return Response({
            "success": True,
            "message": result.get('message', ''),
            "command_result": result,
            "caster": CombatParticipantSerializer(caster).data,
            "summon": CombatParticipantSerializer(summon).data,
            "target": CombatParticipantSerializer(target).data if target else None,
            "session": CombatSessionSerializer(fresh_session).data
        }, status=status.HTTP_200_OK)


