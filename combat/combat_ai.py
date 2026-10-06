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

    # Flying AI: If capable of flight and not airborne, take flight to rain breath/ranged attacks from above
    if participant.can_fly() and not participant.is_flying and not participant.is_incapacitated() and not participant.grappled_by:
        takeoff_alt = min(30, participant.get_fly_speed())
        if takeoff_alt <= participant.movement_remaining:
            participant.altitude = takeoff_alt
            participant.is_flying = True
            participant.movement_used += takeoff_alt
            participant.save(update_fields=['altitude', 'is_flying', 'movement_used'])
            desc = f"🛫 {participant.get_name()} takes flight, ascending to {takeoff_alt} ft altitude!"
            actions.append({'type': 'move', 'message': desc})
            try:
                from combat.models import CombatAction
                CombatAction.objects.create(
                    combat_session=session,
                    actor=participant,
                    action_type='move',
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=desc
                )
            except Exception:
                pass

    if special_action:
        # Move closer if targets are far
        if targets:
            move_res = _execute_ai_movement(session, participant, targets[0], {'name': special_action.name})
            if move_res:
                actions.append(move_res)
        result = _execute_special_action(session, participant, targets, special_action)
        actions.append(result)
        return actions

    # 2. Determine tactical archetype & preferred combat mode
    archetype = _determine_archetype(participant, enemy)

    # 3. Get enemy attacks / actions
    enemy_attacks = _get_enemy_attacks(participant, enemy)
    if not enemy_attacks:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no available attacks.",
        })
        return actions

    has_melee_atk = any(_is_attack_melee(a) for a in enemy_attacks)
    has_ranged_atk = any(_is_attack_ranged(a) for a in enemy_attacks)

    if archetype in ['sniper', 'caster'] and has_ranged_atk:
        preferred_mode = 'ranged'
    elif has_melee_atk:
        preferred_mode = 'melee'
    else:
        preferred_mode = 'ranged'

    # 4. Multiattack evaluation
    attack_count, attack_sequence = _check_multiattack(participant, enemy)

    # 5. Grid-aware target selection
    target = _select_target(targets, attacker=participant, enemy=enemy, preferred_mode=preferred_mode)
    if not target:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no valid targets to attack.",
        })
        return actions

    # Flying AI Swoop: If airborne with only melee attacks, swoop down to reach target
    if participant.is_flying and not has_ranged_atk and target:
        reach = participant.get_reach() if hasattr(participant, 'get_reach') else 5
        target_alt = getattr(target, 'altitude', 0) or 0
        desired_alt = target_alt + reach
        if (participant.altitude or 0) > desired_alt:
            participant.altitude = desired_alt
            participant.save(update_fields=['altitude'])
            desc = f"🦅 {participant.get_name()} swoops down to {desired_alt} ft altitude to strike {target.get_name()} in melee!"
            actions.append({'type': 'move', 'message': desc})

    intended_attack = _select_intended_attack(enemy_attacks, preferred_mode=preferred_mode)

    # 6. 🐾 TACTICAL MOVEMENT PHASE (FIRST)
    # Melee combatants close distance into reach before attacking.
    # Ranged/Caster combatants back up if adjacent (to avoid disadvantage) or maintain distance.
    move_action = _execute_ai_movement(
        session, participant, target,
        attack=intended_attack,
        preferred_mode=preferred_mode
    )
    if move_action:
        actions.append(move_action)

    # 7. ⚔️ ATTACK RESOLUTION PHASE (SECOND)
    reach = participant.get_reach() if hasattr(participant, 'get_reach') else 5

    if attack_sequence:
        current_target = target
        for seq_item in attack_sequence:
            atk_name = seq_item['action_name']
            count = seq_item.get('count', 1)
            matched_atk = next((a for a in enemy_attacks if a['name'].lower() == atk_name.lower()), None)
            if not matched_atk:
                matched_atk = intended_attack

            for _ in range(count):
                # If current target died, pick next living target and move if movement remains
                if current_target.current_hp <= 0 or not current_target.is_active:
                    targets = [t for t in targets if t.current_hp > 0 and t.is_active]
                    if not targets:
                        break
                    current_target = _select_target(targets, attacker=participant, enemy=enemy, preferred_mode=preferred_mode)
                    follow_move = _execute_ai_movement(session, participant, current_target, attack=matched_atk, preferred_mode=preferred_mode)
                    if follow_move:
                        actions.append(follow_move)

                in_range, _, _, _ = _check_action_range(participant, current_target, matched_atk.get('action_obj'), default_reach=reach)
                pack_adv = _check_pack_tactics(session, participant, current_target)
                if in_range:
                    res = _execute_attack(session, participant, current_target, matched_atk, advantage=pack_adv)
                    actions.append(res)
                else:
                    ranged_fallback = _find_ranged_fallback(enemy_attacks, participant, current_target, default_reach=reach)
                    if ranged_fallback:
                        res = _execute_attack(session, participant, current_target, ranged_fallback, advantage=pack_adv)
                        actions.append(res)
                targets = [t for t in targets if t.current_hp > 0 and t.is_active]
    else:
        current_target = target
        for _ in range(attack_count):
            if current_target.current_hp <= 0 or not current_target.is_active:
                targets = [t for t in targets if t.current_hp > 0 and t.is_active]
                if not targets:
                    break
                current_target = _select_target(targets, attacker=participant, enemy=enemy, preferred_mode=preferred_mode)
                follow_move = _execute_ai_movement(session, participant, current_target, attack=intended_attack, preferred_mode=preferred_mode)
                if follow_move:
                    actions.append(follow_move)

            attack_to_use = _select_attack_for_distance(enemy_attacks, participant, current_target, preferred_mode=preferred_mode, default_reach=reach)
            if attack_to_use:
                pack_adv = _check_pack_tactics(session, participant, current_target)
                res = _execute_attack(session, participant, current_target, attack_to_use, advantage=pack_adv)
                actions.append(res)
            targets = [t for t in targets if t.current_hp > 0 and t.is_active]

    # 8. 💨 BONUS ACTION: NIMBLE ESCAPE (Goblin / Skirmisher)
    # The creature takes Disengage as a bonus action and retreats away from melee threats.
    if participant.is_active and participant.current_hp > 0:
        has_nimble = participant.has_trait('nimble_escape') or ('goblin' in (participant.get_name() or '').lower())
        if has_nimble and not participant.bonus_action_used:
            hostiles = [t for t in targets if t.is_active and t.current_hp > 0]
            is_threatened = any(
                participant.get_distance_to(h) <= 5
                for h in hostiles
            ) if (participant.position_x != 0 or participant.position_y != 0) else False

            speed = participant.speed or 30
            mov_used = participant.movement_used or 0
            remaining_movement = max(0, speed - mov_used)

            if is_threatened or (preferred_mode == 'ranged' and remaining_movement >= 5):
                participant.bonus_action_used = True
                if not isinstance(participant.feature_uses, dict):
                    participant.feature_uses = {}
                participant.feature_uses['disengaged'] = True
                participant.save(update_fields=['bonus_action_used', 'feature_uses'])

                nimble_desc = f"{participant.get_name()} used Nimble Escape to Disengage as a bonus action and slipped away!"
                from combat.models import CombatAction
                try:
                    CombatAction.objects.create(
                        combat_session=session,
                        actor=participant,
                        action_type='other',
                        round_number=session.current_round,
                        turn_number=session.current_turn_index,
                        description=f"💨 {nimble_desc}"
                    )
                except Exception:
                    pass

                retreat_target = min(hostiles, key=lambda h: participant.get_distance_to(h)) if hostiles else target
                retreat_move = _execute_ai_movement(session, participant, retreat_target, preferred_mode='ranged')
                actions.append({
                    'type': 'nimble_escape',
                    'message': f"💨 {nimble_desc}",
                    'disengaged': True,
                    'movement': retreat_move
                })

    if not actions:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} took a defensive stance and held their ground.",
        })

    return actions


def _check_pack_tactics(session, attacker, target):
    """
    Check 5e Pack Tactics trait:
    Advantage on attack rolls against target if at least one ally is within 5 feet of target and isn't incapacitated.
    """
    if not (attacker.has_trait('pack_tactics') or _determine_archetype(attacker) == 'pack_hunter'):
        return False

    allies = session.participants.filter(
        participant_type=attacker.participant_type,
        is_active=True,
        current_hp__gt=0
    ).exclude(id=attacker.id)

    has_coords = (attacker.position_x != 0 or attacker.position_y != 0 or target.position_x != 0 or target.position_y != 0)

    for ally in allies:
        if ally.is_incapacitated():
            continue
        if has_coords:
            dist = ally.get_distance_to(target) if hasattr(ally, 'get_distance_to') else max(
                abs((ally.position_x or 0) - (target.position_x or 0)),
                abs((ally.position_y or 0) - (target.position_y or 0))
            )
            if dist <= 5:
                return True
        else:
            return True

    return False


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


def _determine_archetype(participant, enemy=None):
    """Determine the tactical archetype of the combatant."""
    if participant and participant.has_trait('pack_tactics'):
        return 'pack_hunter'

    if not enemy and participant:
        enemy = _resolve_enemy(participant)

    if not enemy:
        return 'skirmisher'

    # Check for spellcasting actions or features
    if enemy.actions.filter(attack_type__in=['melee_spell', 'ranged_spell']).exists():
        return 'caster'

    ranged_actions = enemy.actions.filter(attack_type='ranged_weapon')
    melee_actions = enemy.actions.filter(attack_type='melee_weapon')
    has_ranged = ranged_actions.exists()
    has_melee = melee_actions.exists()

    name_lower = (enemy.name or '').lower()
    is_explicit_archer = any(term in name_lower for term in [
        'archer', 'scout', 'sniper', 'marksman', 'sharpshooter', 'crossbowman', 'bowman'
    ])

    # If only ranged attacks, or name explicitly indicates archer/sniper
    if has_ranged and (not has_melee or is_explicit_archer):
        return 'sniper'

    str_val = getattr(getattr(enemy, 'stats', None), 'strength', 10) or 10
    dex_val = getattr(getattr(enemy, 'stats', None), 'dexterity', 10) or 10

    # If creature has ranged weapons and DEX > STR, classify as sniper unless giant/monstrosity/beast
    if has_ranged and dex_val > str_val and enemy.creature_type not in ['giant', 'monstrosity', 'beast']:
        return 'sniper'

    # Check high STR or giant/monstrosity/brute
    if enemy.creature_type in ['giant', 'monstrosity'] or str_val >= 15:
        return 'brute'

    return 'skirmisher'


def _select_target(targets, attacker=None, enemy=None, preferred_mode='melee'):
    """
    Tactical Target Evaluation (Pillar 5 & Pillar 6):
    Grid-aware target selection that balances:
    - Distance & Reachability: Can the attacker reach this target this turn?
    - Auto-crit vulnerability: Incapacitated (paralyzed/unconscious) targets receive massive priority (+45).
    - Concentration threat: Casters & snipers target concentrating heroes to disrupt big spells (+35).
    - Wounded/Kill shot: Targets with <=25% HP receive high focus (+25) to eliminate party action economy.
    - Low AC vulnerability: Brutes favor easier targets to guarantee hits (+15).
    - Pack Hunter ally focus: (+20) when allies are engaging the target.
    """
    if not targets:
        return None

    archetype = _determine_archetype(attacker, enemy) if attacker else 'skirmisher'

    best_target = None
    best_score = -999999.0

    cur_x = (attacker.position_x or 0) if attacker else 0
    cur_y = (attacker.position_y or 0) if attacker else 0
    speed = (attacker.speed or 30) if attacker else 30
    movement_remaining = max(0, speed - ((attacker.movement_used or 0) if attacker else 0))
    reach = (attacker.get_reach() if hasattr(attacker, 'get_reach') else 5) if attacker else 5
    has_coords = attacker and (attacker.position_x != 0 or attacker.position_y != 0)

    for target in targets:
        score = 0.0
        tgt_x = target.position_x or 0
        tgt_y = target.position_y or 0
        dist = max(abs(cur_x - tgt_x), abs(cur_y - tgt_y)) if has_coords else 5

        # ── Distance & Reachability Scoring ──
        if has_coords:
            if preferred_mode == 'melee':
                if dist <= reach:
                    # Target is ALREADY in melee reach: huge priority!
                    # Saves movement, avoids opportunity attacks, enables full multiattack
                    score += 60.0
                elif dist <= movement_remaining + reach:
                    # Reachable with movement this turn: high priority, closer is better
                    score += 35.0 - (dist / 5.0) * 2.0
                else:
                    # Unreachable this turn: heavy penalty so reachable targets are always chosen first.
                    # If all targets are unreachable, closest will still have the highest score
                    score -= 80.0 + (dist / 5.0) * 3.0
            else:
                # Ranged / Caster
                if dist <= 5:
                    # In melee: disadvantage on ranged attacks!
                    score -= 15.0
                elif 15 <= dist <= 60:
                    # Optimal firing range
                    score += 30.0
                elif dist > 60:
                    # Long range or far away
                    score -= (dist - 60) * 0.5

        # ── Tactical 5e Priorities ──
        # 1. Incapacitated target execution (+45)
        if target.is_incapacitated():
            score += 45.0

        # 2. Concentration disruption
        if getattr(target, 'is_concentrating', False):
            score += 35.0 if archetype in ['caster', 'sniper'] else 15.0

        # 3. Wounded / Low HP priority (up to +25)
        if target.max_hp > 0:
            hp_percent = target.current_hp / target.max_hp
            if hp_percent <= 0.25:
                score += 25.0
            elif hp_percent <= 0.50:
                score += 15.0
            score += (1.0 - hp_percent) * 10.0

        # 4. Low AC priority for Brutes
        if archetype == 'brute':
            target_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else (target.armor_class or 10)
            score += max(0, 18 - target_ac) * 1.5

        # 5. Pack Hunter / Pack Tactics ally focus
        if archetype == 'pack_hunter' or (attacker and attacker.has_trait('pack_tactics')):
            session_ref = getattr(attacker, 'combat_session', None) or getattr(attacker, 'session', None)
            if has_coords and session_ref:
                allies_near = any(
                    a.get_distance_to(target) <= 5
                    for a in session_ref.participants.filter(
                        participant_type=attacker.participant_type,
                        is_active=True,
                        current_hp__gt=0
                    ).exclude(id=attacker.id)
                    if not a.is_incapacitated()
                )
                if allies_near:
                    score += 25.0
                else:
                    score += 5.0
            else:
                score += 15.0

        # Small random jitter (0..1.5) to avoid robotic determinism on ties
        score += random.uniform(0, 1.5)

        if score > best_score:
            best_score = score
            best_target = target

    return best_target or targets[0]


def _parse_action_range(action_obj, default_reach=5):
    """
    Parse (normal_range, max_range, is_melee) from EnemyAction.reach_or_range.
    Examples:
      - '5 ft.' -> (5, 5, True)
      - '10 ft.' -> (10, 10, True)
      - '60/120 ft.' -> (60, 120, False)
      - '30 ft.' -> (30, 30, False/True depending on attack_type)
    """
    if not action_obj:
        return default_reach, default_reach, True
    
    reach_str = getattr(action_obj, 'reach_or_range', '') or ''
    attack_type = getattr(action_obj, 'attack_type', '') or ''
    is_melee = 'melee' in attack_type or ('ranged' not in attack_type and 'spell' not in attack_type)
    
    numbers = [int(n) for n in re.findall(r'\d+', reach_str)]
    if len(numbers) >= 2:
        return numbers[0], numbers[1], False
    elif len(numbers) == 1:
        val = numbers[0]
        return val, val, is_melee
    
    return default_reach, default_reach, is_melee


def _check_action_range(attacker, target, action_obj, default_reach=5):
    """
    Check if target is within reach/range of the action.
    Returns (in_range, is_long_range, dist, max_range).
    """
    if not attacker or not target:
        return True, False, 5, 5
    has_coords = (attacker.position_x != 0 or attacker.position_y != 0 or target.position_x != 0 or target.position_y != 0)
    if not has_coords:
        return True, False, 5, 5
    
    dist = attacker.get_distance_to(target)
    normal_r, max_r, is_melee = _parse_action_range(action_obj, default_reach=default_reach)
    
    if dist > max_r:
        return False, False, dist, max_r
    if not is_melee and dist > normal_r:
        return True, True, dist, max_r
    return True, False, dist, max_r


def _is_attack_melee(attack, default_reach=5):
    """Check if an attack is a melee attack."""
    if not attack:
        return True
    act = attack.get('action_obj')
    if act:
        _, _, is_melee = _parse_action_range(act, default_reach=default_reach)
        return is_melee
    name = (attack.get('name') or '').lower()
    ranged_terms = ['bow', 'crossbow', 'dart', 'sling', 'blowgun', 'ranged', 'ray', 'blast', 'javelin', 'rock']
    return not any(term in name for term in ranged_terms)


def _is_attack_ranged(attack, default_reach=5):
    """Check if an attack is a ranged attack."""
    return not _is_attack_melee(attack, default_reach=default_reach)


def _select_intended_attack(attacks, preferred_mode='melee'):
    """Select the intended attack for closing distance."""
    if not attacks:
        return None
    if preferred_mode == 'melee':
        melee_atks = [a for a in attacks if _is_attack_melee(a)]
        if melee_atks:
            return max(melee_atks, key=lambda a: a.get('bonus', 0))
    else:
        ranged_atks = [a for a in attacks if _is_attack_ranged(a)]
        if ranged_atks:
            return max(ranged_atks, key=lambda a: a.get('bonus', 0))
    return max(attacks, key=lambda a: a.get('bonus', 0))


def _select_attack_for_distance(attacks, attacker, target, preferred_mode='melee', default_reach=5):
    """Select the best attack considering actual post-movement distance to target."""
    if not attacks or not attacker or not target:
        return attacks[0] if attacks else None

    dist = attacker.get_distance_to(target) if hasattr(attacker, 'get_distance_to') else max(
        abs((attacker.position_x or 0) - (target.position_x or 0)),
        abs((attacker.position_y or 0) - (target.position_y or 0))
    )

    # In melee reach
    if dist <= default_reach:
        if preferred_mode == 'melee':
            melee_atks = [a for a in attacks if _is_attack_melee(a, default_reach=default_reach)]
            if melee_atks:
                return max(melee_atks, key=lambda a: a.get('bonus', 0))
        return max(attacks, key=lambda a: a.get('bonus', 0))

    # Outside melee reach: look for attacks that can reach dist
    in_range_attacks = []
    for a in attacks:
        act = a.get('action_obj')
        in_range, _, _, _ = _check_action_range(attacker, target, act, default_reach=default_reach)
        if in_range:
            in_range_attacks.append(a)

    if in_range_attacks:
        return max(in_range_attacks, key=lambda a: a.get('bonus', 0))

    return None


def _find_ranged_fallback(attacks, attacker, target, default_reach=5):
    """Find a ranged attack that can reach the target if melee attack is out of reach."""
    for a in attacks:
        if _is_attack_ranged(a, default_reach=default_reach):
            act = a.get('action_obj')
            in_range, _, _, _ = _check_action_range(attacker, target, act, default_reach=default_reach)
            if in_range:
                return a
    return None


def _select_attack(attacks, attacker=None, enemy=None, target=None):
    """Select the best attack considering archetype, bonus, and target range."""
    if not attacks:
        return None

    # If target is provided and coordinates exist, prioritize attacks in range
    if attacker and target:
        has_coords = (attacker.position_x != 0 or attacker.position_y != 0 or target.position_x != 0 or target.position_y != 0)
        if has_coords:
            in_range_attacks = []
            for a in attacks:
                act = a.get('action_obj')
                in_range, _, _, _ = _check_action_range(
                    attacker, target, act,
                    default_reach=attacker.get_reach() if hasattr(attacker, 'get_reach') else 5
                )
                if in_range:
                    in_range_attacks.append(a)
            if in_range_attacks:
                attacks = in_range_attacks

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

    # Filter targets within reach_or_range if coordinates exist
    if action_obj and getattr(action_obj, 'reach_or_range', None):
        range_match = re.search(r'(\d+)', action_obj.reach_or_range)
        if range_match:
            max_r = int(range_match.group(1))
            valid_targets = []
            for t in targets:
                has_coords = (attacker.position_x != 0 or attacker.position_y != 0 or t.position_x != 0 or t.position_y != 0)
                if not has_coords or attacker.get_distance_to(t) <= max_r:
                    valid_targets.append(t)
            targets = valid_targets

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
            if not saved and hasattr(target, 'check_legendary_resistance'):
                used_lr, saved, lr_msg = target.check_legendary_resistance(ability, dc, save_total)
                if used_lr:
                    affected_summaries.append(f"{target.get_name()}: Used Legendary Resistance! (SUCCESS)")

        # Apply damage
        damage_taken = (total_damage // 2) if (saved and half_on_save) else (0 if saved else total_damage)
        first_dr = action_obj.damage_rolls.first() if action_obj.damage_rolls.exists() else None
        special_dtype = first_dr.damage_type.name if (first_dr and first_dr.damage_type) else None
        if damage_taken > 0:
            target.take_damage(damage_taken, damage_type=special_dtype, is_critical=False)
            if getattr(target, 'last_undead_fortitude_triggered', False):
                affected_summaries.append(f"{target.get_name()}: Undead Fortitude kept them at 1 HP!")

        # Apply conditions on failed save
        if not saved and action_obj.conditions_inflicted.exists():
            from combat.condition_effects import is_condition_immune
            for c in action_obj.conditions_inflicted.all():
                if not is_condition_immune(target, c.name):
                    target.conditions.add(c)
                    if c.name.lower() == 'prone' and getattr(target, 'is_flying', False):
                        fall_dmg, fall_msg = target.handle_flying_fall(session)
                        if fall_msg:
                            affected_summaries.append(fall_msg)
        status_txt = f"{target.get_name()}: {'Saved' if saved else 'Failed'} (took {damage_taken} dmg)"
        affected_summaries.append(status_txt)

    # Set ability to uncharged and mark action economy as used
    attacker.action_used = True
    attacker.attacks_remaining = 0
    fields_to_update = ['action_used', 'attacks_remaining']
    if action_obj.has_recharge:
        if attacker.recharge_state is None:
            attacker.recharge_state = {}
        attacker.recharge_state[action_name] = False
        fields_to_update.append('recharge_state')
    attacker.save(update_fields=fields_to_update)

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

    in_range, is_long_range, dist, max_r = _check_action_range(
        attacker, target, action_obj,
        default_reach=attacker.get_reach() if hasattr(attacker, 'get_reach') else 5
    )
    if not in_range:
        result = {
            'type': 'attack',
            'attacker': attacker.get_name(),
            'attacker_id': attacker.id,
            'target': target.get_name(),
            'target_id': target.id,
            'attack_name': attack_name,
            'roll': 0,
            'attack_bonus': attack_bonus,
            'attack_total': 0,
            'target_ac': target.armor_class,
            'hit': False,
            'critical': False,
            'fumble': False,
            'out_of_range': True,
            'damage': 0,
            'damage_type': '',
            'target_hp_before': target.current_hp,
            'target_hp_after': target.current_hp,
            'target_killed': False,
            'condition_applied': None,
            'pack_tactics': False,
            'is_advantage': False,
            'is_disadvantage': False,
            'roll_breakdown': f"Out of range ({dist} ft > {max_r} ft)",
        }
        try:
            CombatAction.objects.create(
                combat_session=session,
                actor=attacker,
                target=target,
                action_type='attack',
                attack_name=attack_name,
                attack_roll=None,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                hit=False,
                damage_amount=0,
                description=f"{attacker.get_name()} cannot reach {target.get_name()} with {attack_name} ({dist} ft away, max range {max_r} ft)."
            )
        except Exception:
            pass
        return result

    # Determine if melee or ranged
    _, _, is_melee = _parse_action_range(action_obj, default_reach=attacker.get_reach() if hasattr(attacker, 'get_reach') else 5)

    # Condition-based advantage and disadvantage
    cond_adv, cond_disadv, _ = evaluate_attack_roll_conditions(attacker, target, is_melee=is_melee)
    if is_long_range:
        cond_disadv = True

    eff_adv = (advantage or cond_adv) and not cond_disadv
    eff_disadv = cond_disadv and not (advantage or cond_adv)

    roll, _roll_breakdown = roll_d20(advantage=eff_adv, disadvantage=eff_disadv)
    attack_total = roll + attack_bonus
    if hasattr(attacker, 'has_buff') and attacker.has_buff('bless'):
        import random
        attack_total += random.randint(1, 4)

    is_critical = (roll == 20)
    is_fumble = (roll == 1)
    target_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else (target.armor_class or 10)
    hit = is_critical or (not is_fumble and attack_total >= target_ac)
    if hit and is_auto_critical(attacker, target, is_melee=is_melee):
        is_critical = True

    # 5e Defensive Reaction: Shield spell (+5 AC turns hit into a miss)
    if hit and not is_critical and hasattr(target, 'can_use_reaction') and target.can_use_reaction() and not target.is_incapacitated():
        has_shield = False
        if target.participant_type == 'enemy':
            spell_uses = getattr(target, 'spell_uses_remaining', {}) or {}
            if spell_uses.get('Shield', 0) > 0 or spell_uses.get('shield', 0) > 0:
                has_shield = True
            elif target.has_trait('shield_spell') or target.has_trait('shield'):
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
            from combat.models import CombatAction
            try:
                CombatAction.objects.create(
                    combat_session=session,
                    actor=target,
                    action_type='reaction',
                    attack_name='Shield',
                    is_reaction=True,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=f"⚡ {target.get_name()} casts Shield as a reaction! +5 AC turns {attacker.get_name()}'s hit into a MISS!"
                )
            except Exception:
                pass

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
        new_hp, conc_broken = target.take_damage(damage_amount, damage_type=damage_type, is_critical=is_critical)
        target_killed = (new_hp <= 0)
        if getattr(target, 'last_undead_fortitude_triggered', False):
            result['undead_fortitude_triggered'] = True
            target_killed = False

        # Condition rider (e.g. Wolf bite knock prone)
        if action_obj and action_obj.saving_throw_dc and action_obj.conditions_inflicted.exists():
            save_mod = target.get_ability_modifier(action_obj.saving_throw_ability or 'STR')
            s_roll, _ = roll_d20()
            if (s_roll + save_mod) < action_obj.saving_throw_dc:
                # Check Legendary Resistance on condition rider
                saved_rider = False
                if hasattr(target, 'check_legendary_resistance'):
                    used_lr, saved_rider, _ = target.check_legendary_resistance(
                        action_obj.saving_throw_ability or 'STR',
                        action_obj.saving_throw_dc,
                        s_roll + save_mod
                    )
                if not saved_rider:
                    from combat.condition_effects import is_condition_immune
                    for c in action_obj.conditions_inflicted.all():
                        if not is_condition_immune(target, c.name):
                            target.conditions.add(c)
                            result['condition_applied'] = c.name

        result['damage'] = damage_amount
        result['damage_type'] = damage_type
        result['target_hp_after'] = target.current_hp
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

    attacker.action_used = True
    attacker.attacks_remaining = max(0, (attacker.attacks_remaining or 1) - 1)
    attacker.save(update_fields=['action_used', 'attacks_remaining'])

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

    if result.get('out_of_range'):
        return f"{roll_prefix}{attacker} tries to attack {target} with {attack_name}, but target is out of range!"

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
        if result.get('undead_fortitude_triggered'):
            msg += f" | 🧟 Undead Fortitude: Remained at 1 HP!"
        elif result['target_killed']:
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


def _execute_ai_movement(session, participant, target, attack=None, preferred_mode=None):
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

    # Determine melee vs ranged and reach
    action_obj = attack.get('action_obj') if attack else None
    normal_r, max_r, parsed_is_melee = _parse_action_range(
        action_obj,
        default_reach=participant.get_reach() if hasattr(participant, 'get_reach') else 5
    )
    if not action_obj and attack and any(term in attack.get('name', '').lower() for term in ['bow', 'crossbow', 'dart', 'sling', 'blowgun', 'ranged', 'ray', 'blast', 'javelin', 'rock']):
        parsed_is_melee = False
        normal_r, max_r = 60, 120

    if preferred_mode == 'melee':
        is_melee = True
    elif preferred_mode == 'ranged':
        is_melee = False
    else:
        is_melee = parsed_is_melee

    reach = normal_r if (is_melee and action_obj) else (participant.get_reach() if hasattr(participant, 'get_reach') else 5)

    # If already in melee reach, no need to move
    if is_melee and cur_dist <= reach:
        return None

    # If ranged and already in comfortable distance (15..normal_r ft), no need to move
    if not is_melee and 15 <= cur_dist <= min(max(15, normal_r), 50):
        return None

    # Get occupied positions of other living combatants and blocking obstacles
    from combat.battlefield import is_tile_solid
    mover_tiles = participant.get_size_dimensions()['tiles'] if hasattr(participant, 'get_size_dimensions') else 1

    occupied = set()
    for other in session.participants.filter(is_active=True, current_hp__gt=0).exclude(id=participant.id):
        o_tiles = other.get_size_dimensions()['tiles'] if hasattr(other, 'get_size_dimensions') else 1
        for ox in range(o_tiles):
            for oy in range(o_tiles):
                occupied.add((other.position_x + ox * 5, other.position_y + oy * 5))

    best_tile = None
    best_dist_to_target = cur_dist
    best_step_cost = 999

    max_steps = min(8, movement_remaining // 5)
    for dx in range(-max_steps, max_steps + 1):
        for dy in range(-max_steps, max_steps + 1):
            cand_x = cur_x + dx * 5
            cand_y = cur_y + dy * 5

            dist_from_cur = max(abs(cand_x - cur_x), abs(cand_y - cur_y))
            if dist_from_cur <= 0 or dist_from_cur > movement_remaining:
                continue

            # Verify entire multi-tile footprint fits within bounds, avoids solid obstacles & other combatants
            footprint_valid = True
            for ox in range(mover_tiles):
                for oy in range(mover_tiles):
                    fx = cand_x + ox * 5
                    fy = cand_y + oy * 5
                    if fx < 0 or fx > 45 or fy < 0 or fy > 35:
                        footprint_valid = False
                        break
                    if is_tile_solid(session.id or 0, fx // 5, fy // 5):
                        footprint_valid = False
                        break
                    if (fx, fy) in occupied:
                        footprint_valid = False
                        break
                if not footprint_valid:
                    break

            if not footprint_valid:
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

        move_desc = (
            f"{participant.get_name()} moved {best_step_cost} ft towards {target.get_name()}."
            if is_melee or cur_dist > 30
            else f"{participant.get_name()} repositioned {best_step_cost} ft to maintain distance from {target.get_name()}."
        )

        from combat.models import CombatAction
        try:
            CombatAction.objects.create(
                combat_session=session,
                actor=participant,
                action_type='move',
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=move_desc,
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
            'message': f"🐾 {move_desc}",
        }

    return None


def execute_ai_legendary_action(session, boss, trigger_participant=None):
    """
    Evaluate and execute a legendary action for an enemy boss at the end of another creature's turn.
    5e rule: Max 3 points per round, used 1 at a time at the end of another creature's turn.
    """
    if not boss or not boss.is_active or boss.current_hp <= 0 or boss.is_incapacitated():
        return None

    enemy = boss.resolve_enemy()

    # Auto-initialize legendary actions max if not set
    if boss.legendary_actions_max == 0:
        if enemy and (enemy.legendary_actions.exists() or enemy.actions.filter(action_type='legendary_action').exists()):
            boss.legendary_actions_max = 3
            boss.legendary_actions_remaining = 3
            boss.save(update_fields=['legendary_actions_max', 'legendary_actions_remaining'])

    if boss.legendary_actions_remaining <= 0:
        return None

    # Target living player characters
    targets = list(session.participants.filter(
        participant_type='character',
        is_active=True,
        current_hp__gt=0
    ))
    if not targets:
        # Fallback to opposing participants if no player characters
        targets = list(session.participants.filter(
            is_active=True,
            current_hp__gt=0
        ).exclude(id=boss.id))
    if not targets:
        return None

    # Find available legendary action options
    leg_actions = list(enemy.actions.filter(action_type='legendary_action')) if enemy else []
    leg_models = list(enemy.legendary_actions.all()) if enemy else []

    chosen_name = None
    chosen_cost = 1
    action_obj = None

    # Check Wing Attack option (Cost 2): prioritize if heroes are within 10-15 ft
    wing_act = next((a for a in leg_actions if 'wing' in a.name.lower()), None)
    wing_model = next((m for m in leg_models if 'wing' in m.name.lower()), None)
    if (wing_act or wing_model) and boss.legendary_actions_remaining >= 2:
        close_targets = [
            t for t in targets
            if (boss.position_x == 0 and boss.position_y == 0) or boss.get_distance_to(t) <= 15
        ]
        if close_targets:
            chosen_name = wing_act.name if wing_act else wing_model.name
            chosen_cost = 2
            action_obj = wing_act

    # Fallback to attack option (Cost 1) (Tail Attack, Bite, or first available)
    if not chosen_name:
        for a in leg_actions:
            if 'wing' not in a.name.lower():
                chosen_name = a.name
                chosen_cost = 1
                action_obj = a
                break

    if not chosen_name and leg_models:
        for m in leg_models:
            if 'wing' not in m.name.lower():
                chosen_name = m.name
                chosen_cost = m.cost or 1
                break

    # If no structured legendary actions, fallback to standard melee attack as cost 1
    if not chosen_name and enemy:
        atk = enemy.actions.filter(attack_type='melee_weapon').first()
        if atk:
            chosen_name = f"Legendary {atk.name}"
            chosen_cost = 1
            action_obj = atk

    # Generic fallback if participant has legendary actions enabled
    if not chosen_name:
        chosen_name = "Tail Attack"
        chosen_cost = 1

    if not chosen_name or chosen_cost > boss.legendary_actions_remaining:
        return None

    # Deduct legendary action points
    boss.legendary_actions_remaining -= chosen_cost
    boss.save(update_fields=['legendary_actions_remaining'])

    from bestiary.models import Condition
    from combat.models import CombatAction

    # Execute Wing Attack (Saving throw + Knock Prone + Reposition)
    if 'wing' in chosen_name.lower():
        dc = (action_obj and action_obj.saving_throw_dc) or 19
        ability = (action_obj and action_obj.saving_throw_ability) or 'DEX'
        close_targets = [
            t for t in targets
            if (boss.position_x == 0 and boss.position_y == 0) or boss.get_distance_to(t) <= 15
        ]
        prone_cond, _ = Condition.objects.get_or_create(name='prone')
        affected_summaries = []
        for t in close_targets:
            s_roll, _ = roll_d20()
            s_mod = t.get_ability_modifier(ability)
            saved = (s_roll + s_mod >= dc)
            dmg = random.randint(10, 18)
            t_dmg = dmg // 2 if saved else dmg
            t.take_damage(t_dmg, damage_type='bludgeoning')
            if not saved:
                t.conditions.add(prone_cond)
                if getattr(t, 'is_flying', False):
                    fall_dmg, fall_msg = t.handle_flying_fall(session)
                    if fall_msg:
                        affected_summaries.append(fall_msg)
                affected_summaries.append(f"{t.get_name()} took {t_dmg} bludgeoning and was knocked prone")
            else:
                affected_summaries.append(f"{t.get_name()} saved (took {t_dmg} dmg)")

        # Reposition boss
        old_x, old_y = boss.position_x, boss.position_y
        if boss.position_x != 0 or boss.position_y != 0:
            boss.position_x = min(40, max(5, boss.position_x + random.choice([-10, 10])))
            boss.position_y = min(30, max(5, boss.position_y + random.choice([-10, 10])))
            boss.save(update_fields=['position_x', 'position_y'])

        desc = (
            f"⚡ [LEGENDARY ACTION] {boss.get_name()} uses {chosen_name}! "
            f"({boss.legendary_actions_remaining} legendary actions left). "
            + (", ".join(affected_summaries) if affected_summaries else "Beats wings violently!")
        )
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=boss,
            action_type='legendary_action',
            attack_name=chosen_name,
            is_legendary_action=True,
            legendary_action_cost=chosen_cost,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {
            'type': 'legendary_action',
            'actor': boss.get_name(),
            'action_name': chosen_name,
            'cost': chosen_cost,
            'remaining': boss.legendary_actions_remaining,
            'message': desc,
        }

    # Execute Single Target Attack (e.g. Tail Attack)
    target = min(targets, key=lambda t: boss.get_distance_to(t)) if (boss.position_x != 0 or boss.position_y != 0) else targets[0]
    attack_bonus = (action_obj and action_obj.attack_bonus) or 11
    roll, _ = roll_d20()
    atk_total = roll + attack_bonus
    target_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else (target.armor_class or 10)
    hit = (roll == 20) or (roll != 1 and atk_total >= target_ac)
    dmg_dealt = 0

    if hit:
        dmg_rolls = list(action_obj.damage_rolls.all()) if action_obj else []
        if dmg_rolls:
            for d in dmg_rolls:
                dmg_dealt += sum(random.randint(1, d.dice_sides) for _ in range(d.dice_count)) + d.damage_bonus
        else:
            dmg_dealt = random.randint(12, 22)
        target.take_damage(dmg_dealt, damage_type='bludgeoning')

    desc = (
        f"⚡ [LEGENDARY ACTION] {boss.get_name()} strikes {target.get_name()} with {chosen_name}! "
        f"({'HIT for ' + str(dmg_dealt) + ' damage' if hit else 'MISSED'}) "
        f"({boss.legendary_actions_remaining} legendary actions left)"
    )
    combat_action = CombatAction.objects.create(
        combat_session=session,
        actor=boss,
        target=target,
        action_type='legendary_action',
        attack_name=chosen_name,
        attack_roll=roll,
        attack_modifier=attack_bonus,
        attack_total=atk_total,
        hit=hit,
        damage_amount=dmg_dealt if hit else 0,
        is_legendary_action=True,
        legendary_action_cost=chosen_cost,
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=desc,
    )
    return {
        'type': 'legendary_action',
        'actor': boss.get_name(),
        'target': target.get_name(),
        'action_name': chosen_name,
        'cost': chosen_cost,
        'hit': hit,
        'damage': dmg_dealt,
        'remaining': boss.legendary_actions_remaining,
        'message': desc,
    }
