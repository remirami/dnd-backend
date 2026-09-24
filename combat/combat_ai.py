"""
Tactical Combat AI for enemy turns with Pillar 4 Monster Actions integration.

Resolves an enemy's turn by:
1. Evaluating charged breath weapons and special recharge abilities
2. Checking traits like Pack Tactics (granting Advantage if allies are active)
3. Executing multiattack sequences (Bite, Claw, etc.)
4. Handling saving throw condition riders (knock prone, poison, grapple)
"""
import random
import re

from combat.utils import roll_d20


def resolve_enemy_turn(session, participant):
    """
    Resolve an enemy participant's turn using enhanced AI.
    """
    actions = []

    # Check if participant is defeated or inactive
    if participant.current_hp <= 0 or not participant.is_active:
        return [{
            'type': 'skip',
            'message': f"{participant.get_name()} is defeated and cannot act.",
        }]

    # Check if participant is incapacitated
    if participant.is_incapacitated():
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} is {participant.get_incapacitating_condition()} and cannot take actions.",
        })
        participant.action_used = True
        participant.attacks_remaining = 0
        participant.save(update_fields=['action_used', 'attacks_remaining'])
        return actions
    
    # Get all living player targets
    targets = list(
        session.participants.filter(
            participant_type='character',
            is_active=True,
            current_hp__gt=0,
        ).order_by('current_hp')  # Lowest HP first
    )
    
    # If no player character targets exist (e.g. practice mode / enemy vs enemy), target opposing participants
    if not targets:
        targets = list(
            session.participants.filter(
                is_active=True,
                current_hp__gt=0,
            ).exclude(id=participant.id).order_by('current_hp')
        )
    
    if not targets:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no valid targets to attack.",
        })
        return actions

    enemy = _resolve_enemy(participant)

    # 1. Check for charged special action (e.g. Breath Weapon)
    special_action = _get_ready_special_action(participant, enemy)
    if special_action:
        # Move closer if targets are far
        if targets:
            move_res = _execute_ai_movement(session, participant, targets[0], {'name': special_action.name})
            if move_res:
                actions.append(move_res)
        result = _execute_special_action(session, participant, targets, special_action)
        actions.append(result)
        return actions

    # 2. Check for Pack Tactics
    has_pack_tactics = False
    if participant.has_trait('pack_tactics'):
        # Check if another living ally is active in the session
        ally_count = session.participants.filter(
            participant_type='enemy',
            is_active=True,
            current_hp__gt=0,
        ).exclude(id=participant.id).count()
        has_pack_tactics = (ally_count > 0)

    # 3. Get enemy attacks / actions
    enemy_attacks = _get_enemy_attacks(participant, enemy)
    if not enemy_attacks:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no available attacks.",
        })
        return actions

    # 4. Multiattack evaluation
    attack_count, attack_sequence = _check_multiattack(participant, enemy)

    # Tactical movement phase before attacking: close into reach or position
    initial_target = _select_target(targets, attacker=participant, enemy=enemy)
    first_attack = _select_attack(enemy_attacks, attacker=participant, enemy=enemy)

    if initial_target and first_attack:
        move_action = _execute_ai_movement(session, participant, initial_target, first_attack)
        if move_action:
            actions.append(move_action)

    # If we have an explicit sequence (e.g. [{'action_name': 'Bite', 'count': 1}, {'action_name': 'Claw', 'count': 2}])
    if attack_sequence:
        for seq_item in attack_sequence:
            atk_name = seq_item['action_name']
            count = seq_item.get('count', 1)
            # Find matching attack
            matched_atk = next((a for a in enemy_attacks if a['name'].lower() == atk_name.lower()), None)
            if not matched_atk:
                matched_atk = _select_attack(enemy_attacks)

            for _ in range(count):
                target = _select_target(targets, attacker=participant, enemy=enemy)
                if not target:
                    break
                if target.id != initial_target.id:
                    follow_move = _execute_ai_movement(session, participant, target, matched_atk)
                    if follow_move:
                        actions.append(follow_move)
                res = _execute_attack(session, participant, target, matched_atk, advantage=has_pack_tactics)
                actions.append(res)
                targets = [t for t in targets if t.current_hp > 0 and t.is_active]
    else:
        # Standard multiattack loop
        for _ in range(attack_count):
            target = _select_target(targets, attacker=participant, enemy=enemy)
            if not target:
                break
            if target.id != initial_target.id:
                follow_move = _execute_ai_movement(session, participant, target, first_attack)
                if follow_move:
                    actions.append(follow_move)
            attack = _select_attack(enemy_attacks, attacker=participant, enemy=enemy)
            res = _execute_attack(session, participant, target, attack, advantage=has_pack_tactics)
            actions.append(res)
            targets = [t for t in targets if t.current_hp > 0 and t.is_active]

    return actions


def _resolve_enemy(participant):
    """Resolve the Enemy model for a participant (encounter or practice mode)."""
    return participant.resolve_enemy()


def _get_ready_special_action(participant, enemy):
    """Return a charged high-impact special action (breath weapon or AoE saving throw)."""
    if not enemy:
        return None

    # Check EnemyAction records
    for act in enemy.actions.filter(has_recharge=True):
        is_ready = participant.recharge_state.get(act.name, True)
        if is_ready:
            return act

    # Check for saving_throw actions without recharge that deal heavy damage
    st_action = enemy.actions.filter(attack_type='saving_throw', has_recharge=False).first()
    if st_action and st_action.damage_rolls.exists():
        return st_action

    return None


def _get_enemy_attacks(participant, enemy):
    """Get available attacks for an enemy participant."""
    attacks = []
    
    if enemy:
        # Prefer structured EnemyAction records (excluding Multiattack utility entries)
        melee_or_ranged = enemy.actions.filter(
            attack_type__in=['melee_weapon', 'ranged_weapon', 'melee_spell', 'ranged_spell']
        ).exclude(name__icontains='multiattack')
        if melee_or_ranged.exists():
            for act in melee_or_ranged:
                dmg_rolls = list(act.damage_rolls.all())
                dmg_str = " + ".join([d.formula for d in dmg_rolls]) if dmg_rolls else "1d6 bludgeoning"
                attacks.append({
                    'name': act.name,
                    'bonus': act.attack_bonus or 3,
                    'damage': dmg_str,
                    'action_obj': act,
                })
        else:
            # Fallback to legacy EnemyAttack (excluding any named Multiattack)
            for atk in enemy.attacks.exclude(name__icontains='multiattack'):
                attacks.append({
                    'name': atk.name,
                    'bonus': atk.bonus,
                    'damage': atk.damage,
                    'action_obj': None,
                })

    if not attacks:
        # Check enemy stats for bonus
        str_mod = participant.get_ability_modifier('STR')
        attacks.append({
            'name': 'Slam',
            'bonus': max(1, str_mod + 2),
            'damage': f'1d6+{max(0, str_mod)} bludgeoning' if str_mod > 0 else '1d6 bludgeoning',
            'action_obj': None,
        })
    
    return attacks


def _check_multiattack(participant, enemy):
    """Check if enemy has multiattack and return count & sequence."""
    if not enemy:
        return 1, []

    if hasattr(enemy, 'multiattack') and enemy.multiattack:
        seq = [
            item for item in (enemy.multiattack.sequence or [])
            if 'multiattack' not in item.get('action_name', '').lower()
        ]
        return max(1, enemy.multiattack.action_count), seq

    # Fallback parsing
    for ability in enemy.abilities.all():
        name_lower = ability.name.lower()
        if 'multiattack' in name_lower:
            desc = ability.description.lower()
            number_words = {
                'two': 2, 'three': 3, 'four': 4, 'five': 5,
                '2': 2, '3': 3, '4': 4, '5': 5,
            }
            for word, count in number_words.items():
                if word in desc:
                    return count, []
            return 2, []

    return 1, []


def _determine_archetype(participant, enemy):
    """Determine the tactical archetype of the combatant."""
    if participant and participant.has_trait('pack_tactics'):
        return 'pack_hunter'

    if enemy:
        # Check for spellcasting
        if enemy.actions.filter(attack_type__in=['melee_spell', 'ranged_spell']).exists():
            return 'caster'
        # Check for ranged attacks
        if enemy.actions.filter(attack_type='ranged_weapon').exists():
            return 'sniper'
        # Check high STR or giant/brute
        if enemy.creature_type in ['giant', 'monstrosity'] or (hasattr(enemy, 'stats') and enemy.stats and enemy.stats.strength >= 16):
            return 'brute'

    return 'skirmisher'


def _select_target(targets, attacker=None, enemy=None):
    """
    Tactical Target Evaluation (Pillar 5):
    Evaluates:
    - Auto-crit vulnerability: Incapacitated (paralyzed/unconscious) targets receive massive priority (+50).
    - Concentration threat: Casters & snipers target concentrating heroes to disrupt big spells (+35).
    - Wounded/Kill shot: Targets with <=25% HP receive high focus (+30) to eliminate actions from the party.
    - Low AC vulnerability: Brutes favor easier targets to guarantee high damage hits (+15).
    """
    if not targets:
        return None

    archetype = _determine_archetype(attacker, enemy) if attacker else 'skirmisher'

    best_target = None
    best_score = -999999.0

    for target in targets:
        score = 0.0

        # 1. Incapacitated target execution (+50)
        if target.is_incapacitated():
            score += 50.0

        # 2. Concentration disruption
        if getattr(target, 'is_concentrating', False):
            score += 35.0 if archetype in ['caster', 'sniper'] else 15.0

        # 3. Wounded / Low HP priority (up to +30)
        if target.max_hp > 0:
            hp_percent = target.current_hp / target.max_hp
            if hp_percent <= 0.25:
                score += 30.0
            elif hp_percent <= 0.50:
                score += 15.0
            score += (1.0 - hp_percent) * 10.0

        # 4. Low AC priority for Brutes
        if archetype == 'brute':
            target_ac = target.armor_class or 10
            score += max(0, 18 - target_ac) * 1.5

        # 5. Pack Hunter ally focus
        if archetype == 'pack_hunter':
            score += 15.0

        # Small random jitter
        score += random.uniform(0, 3)

        if score > best_score:
            best_score = score
            best_target = target

    return best_target or random.choice(targets)


def _select_attack(attacks, attacker=None, enemy=None):
    """Select the best attack considering archetype and bonus."""
    if not attacks:
        return None

    archetype = _determine_archetype(attacker, enemy) if attacker else 'skirmisher'

    if archetype == 'sniper':
        ranged = [
            a for a in attacks
            if a.get('action_obj') and 'ranged' in getattr(a.get('action_obj'), 'attack_type', '')
        ]
        if ranged:
            return max(ranged, key=lambda a: a['bonus'])

    if archetype == 'caster':
        spells = [a for a in attacks if a.get('action_obj') and 'spell' in getattr(a.get('action_obj'), 'attack_type', '')]
        if spells:
            return max(spells, key=lambda a: a['bonus'])

    return max(attacks, key=lambda a: a['bonus'])



def _execute_special_action(session, attacker, targets, action_obj):
    """Execute an AoE or breath weapon saving throw action."""
    from combat.models import CombatAction

    action_name = action_obj.name
    dc = action_obj.saving_throw_dc or 15
    ability = action_obj.saving_throw_ability or 'DEX'
    half_on_save = action_obj.half_damage_on_save

    # Roll base damage for the ability
    total_damage = 0
    dmg_rolls = list(action_obj.damage_rolls.all())
    if dmg_rolls:
        for d in dmg_rolls:
            roll_sum = sum(random.randint(1, d.dice_sides) for _ in range(d.dice_count)) + d.damage_bonus
            total_damage += max(0, roll_sum)
    else:
        total_damage = random.randint(10, 25)

    affected_summaries = []

    for target in targets:
        # Check auto-fail on STR/DEX saves
        from combat.condition_effects import is_auto_fail_save
        if is_auto_fail_save(target, ability):
            saved = False
        else:
            save_mod = target.get_ability_modifier(ability)
            roll, _ = roll_d20()
            save_total = roll + save_mod
            saved = (save_total >= dc)

        # Apply damage
        damage_taken = (total_damage // 2) if (saved and half_on_save) else (0 if saved else total_damage)
        first_dr = action_obj.damage_rolls.first() if action_obj.damage_rolls.exists() else None
        special_dtype = first_dr.damage_type.name if (first_dr and first_dr.damage_type) else None
        if damage_taken > 0:
            target.take_damage(damage_taken, damage_type=special_dtype)

        # Apply conditions on failed save
        if not saved and action_obj.conditions_inflicted.exists():
            for c in action_obj.conditions_inflicted.all():
                target.conditions.add(c)
        status_txt = f"{target.get_name()}: {'Saved' if saved else 'Failed'} (took {damage_taken} dmg)"
        affected_summaries.append(status_txt)

    # Set ability to uncharged
    if action_obj.has_recharge:
        attacker.recharge_state[action_name] = False
        attacker.save(update_fields=['recharge_state'])

    summary_desc = f"{attacker.get_name()} unleashes {action_name}! " + ", ".join(affected_summaries)

    try:
        CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            action_type='attack',
            attack_name=action_name,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            hit=True,
            damage_amount=total_damage,
            description=summary_desc,
        )
    except Exception:
        pass

    return {
        'type': 'special_action',
        'attacker': attacker.get_name(),
        'action_name': action_name,
        'message': summary_desc,
    }


def _execute_attack(session, attacker, target, attack, advantage=False):
    """Execute a single melee or ranged attack."""
    from combat.models import CombatAction
    from combat.condition_effects import evaluate_attack_roll_conditions, is_auto_critical

    attack_name = attack['name']
    attack_bonus = attack['bonus']
    damage_str = attack['damage']
    action_obj = attack.get('action_obj')

    # Condition-based advantage and disadvantage
    cond_adv, cond_disadv, _ = evaluate_attack_roll_conditions(attacker, target, is_melee=True)
    eff_adv = (advantage or cond_adv) and not cond_disadv
    eff_disadv = cond_disadv and not (advantage or cond_adv)

    roll, _roll_breakdown = roll_d20(advantage=eff_adv, disadvantage=eff_disadv)
    attack_total = roll + attack_bonus

    is_critical = (roll == 20)
    is_fumble = (roll == 1)
    target_ac = target.armor_class
    hit = is_critical or (not is_fumble and attack_total >= target_ac)
    if hit and is_auto_critical(attacker, target, is_melee=True):
        is_critical = True

    result = {
        'type': 'attack',
        'attacker': attacker.get_name(),
        'attacker_id': attacker.id,
        'target': target.get_name(),
        'target_id': target.id,
        'attack_name': attack_name,
        'roll': roll,
        'attack_bonus': attack_bonus,
        'attack_total': attack_total,
        'target_ac': target_ac,
        'hit': hit,
        'critical': is_critical,
        'fumble': is_fumble,
        'damage': 0,
        'damage_type': '',
        'target_hp_before': target.current_hp,
        'target_hp_after': target.current_hp,
        'target_killed': False,
        'condition_applied': None,
        'pack_tactics': advantage,
        'is_advantage': eff_adv,
        'is_disadvantage': eff_disadv,
        'roll_breakdown': _roll_breakdown,
    }

    if hit:
        damage_amount, damage_type = _parse_and_roll_damage(damage_str, is_critical)
        new_hp, conc_broken = target.take_damage(damage_amount, damage_type=damage_type)
        target_killed = (new_hp <= 0)

        # Condition rider (e.g. Wolf bite knock prone)
        if action_obj and action_obj.saving_throw_dc and action_obj.conditions_inflicted.exists():
            save_mod = target.get_ability_modifier(action_obj.saving_throw_ability or 'STR')
            s_roll, _ = roll_d20()
            if (s_roll + save_mod) < action_obj.saving_throw_dc:
                for c in action_obj.conditions_inflicted.all():
                    target.conditions.add(c)
                    result['condition_applied'] = c.name

        result['damage'] = damage_amount
        result['damage_type'] = damage_type
        result['target_hp_after'] = target.current_hp
        result['target_killed'] = target_killed
        result['target_killed'] = target_killed

    try:
        CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            target=target,
            action_type='attack',
            attack_name=attack_name,
            attack_roll=roll,
            attack_modifier=attack_bonus,
            attack_total=attack_total,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            hit=hit,
            critical=is_critical,
            damage_amount=result['damage'] if hit else 0,
            is_advantage=eff_adv,
            is_disadvantage=eff_disadv,
            description=_format_attack_description(result),
        )
    except Exception:
        pass

    return result


def _parse_and_roll_damage(damage_str, is_critical=False):
    """Parse dice formula like '2d10+8 piercing' and roll."""
    # Split multi-damage expressions like '2d10+8 piercing + 2d6 fire'
    parts = damage_str.split('+')
    total = 0
    primary_dtype = 'slashing'

    # Match each NdM(+B)?
    dice_matches = re.finditer(r'(\d+)d(\d+)(?:([+\-])(\d+))?\s*([a-zA-Z]*)', damage_str)
    found_any = False
    for m in dice_matches:
        found_any = True
        num_dice = int(m.group(1))
        die_size = int(m.group(2))
        sign = m.group(3)
        bonus = int(m.group(4)) if m.group(4) else 0
        if sign == '-':
            bonus = -bonus
        dtype = m.group(5).strip() or primary_dtype
        primary_dtype = dtype

        if is_critical:
            num_dice *= 2

        subtotal = sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus
        total += max(0, subtotal)

    if not found_any:
        try:
            return int(damage_str.strip()), 'untyped'
        except ValueError:
            return random.randint(1, 6), 'untyped'

    return max(1, total), primary_dtype


def _format_attack_description(result):
    """Format human-readable attack description."""
    attacker = result['attacker']
    target = result['target']
    attack_name = result['attack_name']
    pt = ""
    if result.get('pack_tactics'):
        pt = " [Pack Tactics (Advantage)]"
    elif result.get('is_advantage'):
        pt = " [Advantage]"
    elif result.get('is_disadvantage'):
        pt = " [Disadvantage]"

    roll_bd = result.get('roll_breakdown', '')
    roll_prefix = f"{roll_bd} | " if roll_bd else ""

    if result['fumble']:
        return f"{roll_prefix}{attacker} attacks {target} with {attack_name}{pt} but fumbles! (rolled 1)"

    if result['critical'] and result['hit']:
        cond_str = f" Target is {result['condition_applied']}!" if result.get('condition_applied') else ""
        return (
            f"{roll_prefix}{attacker} CRITICALLY HITS {target} with {attack_name}!{pt} "
            f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
            f"dealing {result['damage']} {result['damage_type']} damage.{cond_str}"
        )

    if result['hit']:
        cond_str = f" Target is {result['condition_applied']}!" if result.get('condition_applied') else ""
        msg = (
            f"{roll_prefix}{attacker} hits {target} with {attack_name}{pt} "
            f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
            f"dealing {result['damage']} {result['damage_type']} damage.{cond_str}"
        )
        if result['target_killed']:
            msg += f" {target} falls!"
        return msg

    return (
        f"{roll_prefix}{attacker} attacks {target} with {attack_name}{pt} but misses "
        f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']})."
    )


LAYOUT_OBSTACLES = {
    0: [(20, 10), (20, 25), (25, 10), (25, 25)],  # Ancient Pillars
    1: [(15, 25)],                                  # Watchtower Pylon
    2: [(25, 15)],                                  # Great Stalagmite
    3: [(20, 0), (20, 5), (25, 0), (20, 30), (20, 35), (25, 35)],  # Cliffs
    4: [(20, 5), (25, 30)],                         # Ancient Oaks
}


def _execute_ai_movement(session, participant, target, attack=None):
    """
    Tactical movement phase for enemy AI.
    Calculates whether the enemy needs to close distance (for melee)
    or reposition (for ranged) and updates participant coordinates on the 10x8 grid.
    """
    speed = participant.speed or 30
    movement_used = participant.movement_used or 0
    movement_remaining = max(0, speed - movement_used)

    if movement_remaining < 5 or participant.is_incapacitated():
        return None

    cur_x = participant.position_x or 0
    cur_y = participant.position_y or 0
    tgt_x = target.position_x or 0
    tgt_y = target.position_y or 0

    # Current Chebyshev distance (in feet)
    cur_dist = max(abs(cur_x - tgt_x), abs(cur_y - tgt_y))

    # Determine melee vs ranged
    is_melee = True
    action_obj = attack.get('action_obj') if attack else None
    if action_obj and getattr(action_obj, 'attack_type', '') in ['ranged_weapon', 'ranged_spell']:
        is_melee = False
    elif attack and any(term in attack.get('name', '').lower() for term in ['bow', 'crossbow', 'dart', 'sling', 'blowgun', 'ranged', 'ray', 'blast', 'javelin']):
        is_melee = False

    reach = participant.get_reach() if hasattr(participant, 'get_reach') else 5

    # If already in melee reach, no need to move
    if is_melee and cur_dist <= reach:
        return None

    # If ranged and already in comfortable distance (15..50 ft), no need to move
    if not is_melee and 15 <= cur_dist <= 50:
        return None

    # Get occupied positions of other living combatants and blocking obstacles
    occupied = set(
        session.participants.filter(is_active=True, current_hp__gt=0)
        .exclude(id=participant.id)
        .values_list('position_x', 'position_y')
    )
    layout_idx = (session.id or 0) % 5
    occupied.update(LAYOUT_OBSTACLES.get(layout_idx, []))

    best_tile = None
    best_dist_to_target = cur_dist
    best_step_cost = 999

    max_steps = min(8, movement_remaining // 5)
    for dx in range(-max_steps, max_steps + 1):
        for dy in range(-max_steps, max_steps + 1):
            cand_x = cur_x + dx * 5
            cand_y = cur_y + dy * 5

            # Must be within 10x8 grid (X: 0..45, Y: 0..35)
            if cand_x < 0 or cand_x > 45 or cand_y < 0 or cand_y > 35:
                continue

            dist_from_cur = max(abs(cand_x - cur_x), abs(cand_y - cur_y))
            if dist_from_cur <= 0 or dist_from_cur > movement_remaining:
                continue

            if (cand_x, cand_y) in occupied:
                continue

            dist_to_target = max(abs(cand_x - tgt_x), abs(cand_y - tgt_y))

            if is_melee:
                # Primary goal: get as close to target as possible (ideally <= reach)
                if dist_to_target < best_dist_to_target or (dist_to_target == best_dist_to_target and dist_from_cur < best_step_cost):
                    best_dist_to_target = dist_to_target
                    best_step_cost = dist_from_cur
                    best_tile = (cand_x, cand_y)
            else:
                # Ranged: Seek ~25-35 ft distance, avoid adjacent (<=5 ft)
                diff_from_ideal = abs(dist_to_target - 30) + (100 if dist_to_target <= 5 else 0)
                curr_diff = abs(best_dist_to_target - 30) + (100 if best_dist_to_target <= 5 else 0)
                if diff_from_ideal < curr_diff or (diff_from_ideal == curr_diff and dist_from_cur < best_step_cost):
                    best_dist_to_target = dist_to_target
                    best_step_cost = dist_from_cur
                    best_tile = (cand_x, cand_y)

    if best_tile and best_tile != (cur_x, cur_y) and best_step_cost > 0:
        old_x, old_y = cur_x, cur_y
        participant.position_x = best_tile[0]
        participant.position_y = best_tile[1]
        participant.movement_used = (participant.movement_used or 0) + best_step_cost
        participant.save(update_fields=['position_x', 'position_y', 'movement_used'])

        from combat.models import CombatAction
        try:
            CombatAction.objects.create(
                combat_session=session,
                actor=participant,
                action_type='move',
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=f"{participant.get_name()} moved {best_step_cost} ft towards {target.get_name()}.",
            )
        except Exception:
            pass

        return {
            'type': 'move',
            'attacker': participant.get_name(),
            'target': target.get_name(),
            'distance': best_step_cost,
            'from_x': old_x,
            'from_y': old_y,
            'to_x': best_tile[0],
            'to_y': best_tile[1],
            'message': f"🐾 {participant.get_name()} moved {best_step_cost} ft towards {target.get_name()}.",
        }

    return None
