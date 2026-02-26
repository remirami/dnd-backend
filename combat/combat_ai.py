"""
Simple Combat AI for enemy turns.

Resolves an enemy's turn by selecting targets and executing attacks
based on the enemy's available actions and basic tactical rules.
"""
import re
import random
from combat.utils import roll_d20


def resolve_enemy_turn(session, participant):
    """
    Resolve an enemy participant's turn using simple AI.
    
    Strategy:
    1. Select target: Prefer lowest-HP living player character
    2. Select attack: Use best available attack (highest bonus)
    3. Execute attack: Roll to hit, roll damage if hit
    4. If multiattack, execute additional attacks
    
    Args:
        session: CombatSession instance
        participant: CombatParticipant (enemy) whose turn it is
        
    Returns:
        list[dict]: List of action results
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
    
    if not targets:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no valid targets.",
        })
        return actions
    
    # Get enemy attacks
    enemy_attacks = _get_enemy_attacks(participant)
    
    if not enemy_attacks:
        actions.append({
            'type': 'skip',
            'message': f"{participant.get_name()} has no available attacks.",
        })
        return actions
    
    # Check for multiattack
    has_multiattack, attack_count = _check_multiattack(participant)
    
    # Execute attacks
    for i in range(attack_count):
        # Pick target (lowest HP that's still alive)
        target = _select_target(targets)
        if not target:
            break
        
        # Pick attack (best available)
        attack = _select_attack(enemy_attacks)
        
        # Execute the attack
        result = _execute_attack(session, participant, target, attack)
        actions.append(result)
        
        # Refresh target list (they might have died)
        targets = [t for t in targets if t.current_hp > 0 and t.is_active]
    
    return actions


def _get_enemy_attacks(participant):
    """Get available attacks for an enemy participant."""
    attacks = []
    
    # If linked to an encounter enemy with a bestiary entry
    if participant.encounter_enemy:
        enemy = participant.encounter_enemy.enemy
        for atk in enemy.attacks.all():
            attacks.append({
                'name': atk.name,
                'bonus': atk.bonus,
                'damage': atk.damage,
            })
    
    # If no attacks found, generate a default melee attack
    if not attacks:
        attacks.append({
            'name': 'Slam',
            'bonus': 3,
            'damage': '1d6+1 bludgeoning',
        })
    
    return attacks


def _check_multiattack(participant):
    """Check if enemy has multiattack ability."""
    if not participant.encounter_enemy:
        return False, 1
    
    enemy = participant.encounter_enemy.enemy
    
    # Check abilities for Multiattack
    for ability in enemy.abilities.all():
        name_lower = ability.name.lower()
        if 'multiattack' in name_lower:
            # Try to parse number of attacks from description
            desc = ability.description.lower()
            
            # Common patterns: "makes two attacks", "makes three attacks"
            number_words = {
                'two': 2, 'three': 3, 'four': 4, 'five': 5,
                '2': 2, '3': 3, '4': 4, '5': 5,
            }
            
            for word, count in number_words.items():
                if word in desc:
                    return True, count
            
            # Default to 2 attacks if multiattack found but count unclear
            return True, 2
    
    return False, 1


def _select_target(targets):
    """Select the best target (lowest HP surviving player)."""
    if not targets:
        return None
    
    # Primary: lowest current HP
    # Tiebreaker: randomize to avoid predictability
    min_hp = targets[0].current_hp  # Already sorted by current_hp
    lowest_hp_targets = [t for t in targets if t.current_hp == min_hp]
    
    return random.choice(lowest_hp_targets)


def _select_attack(attacks):
    """Select the best attack (highest bonus)."""
    if not attacks:
        return None
    return max(attacks, key=lambda a: a['bonus'])


def _execute_attack(session, attacker, target, attack):
    """
    Execute a single attack and apply damage.
    
    Returns:
        dict with attack results
    """
    from combat.models import CombatAction
    
    attack_name = attack['name']
    attack_bonus = attack['bonus']
    damage_str = attack['damage']
    
    # Roll attack
    roll, roll_breakdown = roll_d20()
    attack_total = roll + attack_bonus
    
    # Determine hit
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
    }
    
    if hit:
        # Parse and roll damage
        damage_amount, damage_type = _parse_and_roll_damage(damage_str, is_critical)
        
        # Apply damage
        target.current_hp = max(0, target.current_hp - damage_amount)
        target_killed = target.current_hp <= 0
        if target_killed:
            target.is_active = False
        target.save()
        
        result['damage'] = damage_amount
        result['damage_type'] = damage_type
        result['target_hp_after'] = target.current_hp
        result['target_killed'] = target_killed
    
    # Log the action
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
        pass  # Don't fail the AI turn if logging fails
    
    return result


def _parse_and_roll_damage(damage_str, is_critical=False):
    """
    Parse a damage string like '2d6+3 slashing' and roll it.
    
    Returns:
        (damage_amount, damage_type)
    """
    # Try to extract dice expression and damage type
    # Patterns: "2d6+3 slashing", "1d8 piercing", "2d6+3"
    match = re.match(r'(\d+d\d+(?:[+\-]\d+)?)\s*(.*)', damage_str.strip())
    
    if not match:
        # Fallback: try just a number
        try:
            return int(damage_str.strip()), 'untyped'
        except ValueError:
            return random.randint(1, 6), 'untyped'
    
    dice_expr = match.group(1)
    damage_type = match.group(2).strip() or 'untyped'
    
    # Parse dice: NdM+B
    dice_match = re.match(r'(\d+)d(\d+)([+\-]\d+)?', dice_expr)
    if not dice_match:
        return random.randint(1, 6), damage_type
    
    num_dice = int(dice_match.group(1))
    die_size = int(dice_match.group(2))
    bonus = int(dice_match.group(3)) if dice_match.group(3) else 0
    
    # Critical = double dice
    if is_critical:
        num_dice *= 2
    
    # Roll
    total = sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus
    return max(1, total), damage_type  # Minimum 1 damage on hit


def _format_attack_description(result):
    """Format a human-readable attack description."""
    attacker = result['attacker']
    target = result['target']
    attack_name = result['attack_name']
    
    if result['fumble']:
        return f"{attacker} attacks {target} with {attack_name} but fumbles! (rolled 1)"
    
    if result['critical']:
        if result['hit']:
            return (
                f"{attacker} CRITICALLY HITS {target} with {attack_name}! "
                f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
                f"dealing {result['damage']} {result['damage_type']} damage."
            )
    
    if result['hit']:
        msg = (
            f"{attacker} hits {target} with {attack_name} "
            f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']}) "
            f"dealing {result['damage']} {result['damage_type']} damage."
        )
        if result['target_killed']:
            msg += f" {target} falls!"
        return msg
    
    return (
        f"{attacker} attacks {target} with {attack_name} but misses "
        f"(rolled {result['roll']}+{result['attack_bonus']}={result['attack_total']} vs AC {result['target_ac']})."
    )
