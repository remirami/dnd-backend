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
                target = _select_target(targets)
                if not target:
                    break
                res = _execute_attack(session, participant, target, matched_atk, advantage=has_pack_tactics)
                actions.append(res)
                targets = [t for t in targets if t.current_hp > 0 and t.is_active]
    else:
        # Standard multiattack loop
        for _ in range(attack_count):
            target = _select_target(targets)
            if not target:
                break
            attack = _select_attack(enemy_attacks)
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


def _select_target(targets):
    """Select the lowest HP target with random tiebreaker."""
    if not targets:
        return None
    min_hp = targets[0].current_hp
    lowest_hp_targets = [t for t in targets if t.current_hp == min_hp]
    return random.choice(lowest_hp_targets)


def _select_attack(attacks):
    """Select the attack with highest bonus."""
    if not attacks:
        return None
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
        # Roll saving throw
        save_mod = target.get_ability_modifier(ability)
        roll, _ = roll_d20()
        save_total = roll + save_mod
        saved = (save_total >= dc)

        # Apply damage
        damage_taken = (total_damage // 2) if (saved and half_on_save) else (0 if saved else total_damage)
        target.current_hp = max(0, target.current_hp - damage_taken)
        if target.current_hp <= 0:
            target.is_active = False

        # Apply conditions on failed save
        if not saved and action_obj.conditions_inflicted.exists():
            for c in action_obj.conditions_inflicted.all():
                target.conditions.add(c)

        target.save()
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

    attack_name = attack['name']
    attack_bonus = attack['bonus']
    damage_str = attack['damage']
    action_obj = attack.get('action_obj')

    roll, _roll_breakdown = roll_d20(advantage=advantage)
    attack_total = roll + attack_bonus

    is_critical = (roll == 20)
    is_fumble = (roll == 1)
    target_ac = target.armor_class
    hit = is_critical or (not is_fumble and attack_total >= target_ac)

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
    }

    if hit:
        damage_amount, damage_type = _parse_and_roll_damage(damage_str, is_critical)
        target.current_hp = max(0, target.current_hp - damage_amount)
        target_killed = target.current_hp <= 0
        if target_killed:
            target.is_active = False

        # Condition rider (e.g. Wolf bite knock prone)
        if action_obj and action_obj.saving_throw_dc and action_obj.conditions_inflicted.exists():
            save_mod = target.get_ability_modifier(action_obj.saving_throw_ability or 'STR')
            s_roll, _ = roll_d20()
            if (s_roll + save_mod) < action_obj.saving_throw_dc:
                for c in action_obj.conditions_inflicted.all():
                    target.conditions.add(c)
                    result['condition_applied'] = c.name

        target.save()

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
    pt = " [Pack Tactics]" if result.get('pack_tactics') else ""

    if result['fumble']:
        return f"{attacker} attacks {target} with {attack_name}{pt} but fumbles! (rolled 1)"

    if result['critical'] and result['hit']:
        cond_str = f" Target is {result['condition_applied']}!" if result.get('condition_applied') else ""
        return (
            f"{attacker} CRITICALLY HITS {target} with {attack_name}!{pt} "
            f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
            f"dealing {result['damage']} {result['damage_type']} damage.{cond_str}"
        )

    if result['hit']:
        cond_str = f" Target is {result['condition_applied']}!" if result.get('condition_applied') else ""
        msg = (
            f"{attacker} hits {target} with {attack_name}{pt} "
            f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
            f"dealing {result['damage']} {result['damage_type']} damage.{cond_str}"
        )
        if result['target_killed']:
            msg += f" {target} falls!"
        return msg

    return (
        f"{attacker} attacks {target} with {attack_name}{pt} but misses "
        f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']})."
    )
