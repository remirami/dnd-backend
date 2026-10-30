"""
Combat utilities for dice rolling and calculations
"""
import random
import re


def roll_dice(dice_string: str) -> tuple[int, str]:
    """
    Roll dice based on a string like "2d6+3" or "1d20"
    Returns: (result, breakdown_string)
    """
    # Parse dice string (e.g., "2d6+3", "1d20", "1d8-1")
    pattern = r'(\d+)d(\d+)([+-]\d+)?'
    match = re.match(pattern, dice_string.lower().replace(' ', ''))
    
    if not match:
        raise ValueError(f"Invalid dice string: {dice_string}")
    
    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    
    # Roll the dice
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    
    # Create breakdown string
    rolls_str = ', '.join(map(str, rolls))
    if modifier > 0:
        breakdown = f"{rolls_str} + {modifier} = {total}"
    elif modifier < 0:
        breakdown = f"{rolls_str} {modifier} = {total}"
    else:
        breakdown = f"{rolls_str} = {total}"
    
    return total, breakdown


def roll_d20(advantage: bool = False, disadvantage: bool = False, lucky: bool = False) -> tuple[int, str]:
    """
    Roll a d20, optionally with advantage or disadvantage.
    If lucky is True (e.g. Halfling Lucky), any natural 1 rolled is rerolled once.
    Returns: (result, breakdown_string)
    """
    def _roll_single() -> tuple[int, str]:
        r = random.randint(1, 20)
        if r == 1 and lucky:
            reroll = random.randint(1, 20)
            return reroll, f"1➔{reroll} (Lucky)"
        return r, str(r)

    if advantage and disadvantage:
        # Cancel out, roll normally
        roll, text = _roll_single()
        return roll, f"d20: {text}"
    
    if advantage:
        roll1, text1 = _roll_single()
        roll2, text2 = _roll_single()
        result = max(roll1, roll2)
        return result, f"d20 (advantage): [{text1}, {text2}] → {result}"
    elif disadvantage:
        roll1, text1 = _roll_single()
        roll2, text2 = _roll_single()
        result = min(roll1, roll2)
        return result, f"d20 (disadvantage): [{text1}, {text2}] → {result}"
    else:
        roll, text = _roll_single()
        return roll, f"d20: {text}"


def calculate_attack_roll(
    base_roll: int,
    ability_modifier: int,
    proficiency_bonus: int = 0,
    proficiency: bool = False,
    other_modifiers: int = 0,
    exhaustion_level: int = 0
) -> tuple[int, str]:
    """
    Calculate total attack roll (supports 2024 cumulative exhaustion)
    Returns: (total, breakdown_string)
    """
    attack_modifier = ability_modifier
    if proficiency:
        attack_modifier += proficiency_bonus
    attack_modifier += other_modifiers
    if exhaustion_level > 0:
        attack_modifier -= exhaustion_level
    
    total = base_roll + attack_modifier
    
    parts = [f"Roll: {base_roll}"]
    if ability_modifier != 0:
        parts.append(f"Ability: {ability_modifier:+d}")
    if proficiency:
        parts.append(f"Proficiency: +{proficiency_bonus}")
    if other_modifiers != 0:
        parts.append(f"Other: {other_modifiers:+d}")
    if exhaustion_level > 0:
        parts.append(f"Exhaustion: -{exhaustion_level}")
    parts.append(f"Total: {total}")
    
    breakdown = " + ".join(parts)
    return total, breakdown


def calculate_damage(
    damage_string: str,
    ability_modifier: int = 0,
    critical: bool = False,
    reroll_ones_and_twos: bool = False,
    treat_ones_and_twos_as_three: bool = False
) -> tuple[int, str]:
    """
    Calculate damage from a dice string
    If critical, double the dice (but not modifiers)
    If reroll_ones_and_twos (5e 2014 Great Weapon Fighting), reroll any 1s or 2s once.
    If treat_ones_and_twos_as_three (5e 2024 Great Weapon Fighting), treat 1s and 2s as 3.
    Returns: (damage, breakdown_string)
    """
    # Parse damage string (e.g., "2d6+3 slashing")
    # Extract just the dice part
    dice_part = damage_string.split()[0] if ' ' in damage_string else damage_string
    
    # Check if damage_string is a flat number (e.g. "1" for standard SRD 5.2 5e Unarmed Strike)
    if dice_part.strip().isdigit():
        base_val = int(dice_part.strip())
        total = max(1, base_val + ability_modifier)
        mod_str = f" {'+' if ability_modifier >= 0 else '-'} {abs(ability_modifier)}" if ability_modifier else ""
        breakdown_str = f"Flat damage {base_val}{mod_str} = {total}"
        return total, breakdown_str

    pattern = r'(\d+)d(\d+)([+-]\d+)?'
    match = re.match(pattern, dice_part.lower().replace(' ', ''))
    
    if not match:
        raise ValueError(f"Invalid damage string: {damage_string}")
    
    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    
    # Double dice on critical, but not modifier
    if critical:
        num_dice *= 2
        breakdown_parts = [f"Critical hit! Rolling {num_dice}d{die_size}"]
    else:
        breakdown_parts = [f"Rolling {num_dice}d{die_size}"]
    
    # Roll the dice
    rolls = []
    gwf_notes = []
    for _ in range(num_dice):
        r = random.randint(1, die_size)
        if treat_ones_and_twos_as_three and r in (1, 2):
            gwf_notes.append(f"{r}→3")
            r = 3
        elif reroll_ones_and_twos and r in (1, 2):
            new_r = random.randint(1, die_size)
            gwf_notes.append(f"{r}↺{new_r}")
            r = new_r
        rolls.append(r)

    total_modifier = modifier + ability_modifier
    total = sum(rolls) + total_modifier
    
    rolls_str = ', '.join(map(str, rolls))
    gwf_str = f" [GWF: {', '.join(gwf_notes)}]" if gwf_notes else ""
    if total_modifier > 0:
        breakdown_parts.append(f"{rolls_str}{gwf_str} + {total_modifier} = {total}")
    elif total_modifier < 0:
        breakdown_parts.append(f"{rolls_str}{gwf_str} {total_modifier} = {total}")
    else:
        breakdown_parts.append(f"{rolls_str}{gwf_str} = {total}")
    
    breakdown = " | ".join(breakdown_parts)
    return total, breakdown



def calculate_saving_throw(
    base_roll: int,
    ability_modifier: int,
    proficiency_bonus: int = 0,
    proficiency: bool = False,
    other_modifiers: int = 0,
    exhaustion_level: int = 0
) -> tuple[int, str]:
    """
    Calculate total saving throw (supports 2024 cumulative exhaustion)
    Returns: (total, breakdown_string)
    """
    save_modifier = ability_modifier
    if proficiency:
        save_modifier += proficiency_bonus
    save_modifier += other_modifiers
    if exhaustion_level > 0:
        save_modifier -= exhaustion_level
    
    total = base_roll + save_modifier
    
    parts = [f"Roll: {base_roll}"]
    if ability_modifier != 0:
        parts.append(f"Ability: {ability_modifier:+d}")
    if proficiency:
        parts.append(f"Proficiency: +{proficiency_bonus}")
    if other_modifiers != 0:
        parts.append(f"Other: {other_modifiers:+d}")
    if exhaustion_level > 0:
        parts.append(f"Exhaustion: -{exhaustion_level}")
    parts.append(f"Total: {total}")
    
    breakdown = " + ".join(parts)
    return total, breakdown


def calculate_ability_check(
    base_roll: int,
    ability_modifier: int,
    proficiency_bonus: int = 0,
    proficiency: bool = False,
    half_proficiency: bool = False,
    other_modifiers: int = 0,
    reliable_talent: bool = False,
    indomitable_might_score: int = 0,
    exhaustion_level: int = 0
) -> tuple[int, str]:
    """
    Calculate total ability check roll (supports Remarkable Athlete, Rogue Reliable Talent, Barbarian Indomitable Might, and 2024 exhaustion).
    Returns: (total, breakdown_string)
    """
    import math
    effective_roll = base_roll
    rt_note = ""
    if reliable_talent and proficiency:
        if base_roll < 10:
            effective_roll = 10
            rt_note = f" (Reliable Talent from {base_roll})"

    check_modifier = ability_modifier
    if proficiency:
        check_modifier += proficiency_bonus
    elif half_proficiency:
        check_modifier += math.ceil(proficiency_bonus / 2)
    check_modifier += other_modifiers
    if exhaustion_level > 0:
        check_modifier -= exhaustion_level

    total = effective_roll + check_modifier
    parts = [f"Roll: {effective_roll}{rt_note}"]
    if ability_modifier != 0:
        parts.append(f"Ability: {ability_modifier:+d}")
    if proficiency:
        parts.append(f"Proficiency: +{proficiency_bonus}")
    elif half_proficiency:
        parts.append(f"Remarkable Athlete: +{math.ceil(proficiency_bonus / 2)}")
    if other_modifiers != 0:
        parts.append(f"Other: {other_modifiers:+d}")
    if exhaustion_level > 0:
        parts.append(f"Exhaustion: -{exhaustion_level}")

    if indomitable_might_score > 0 and total < indomitable_might_score:
        parts.append(f"Indomitable Might: adjusted {total} -> {indomitable_might_score}")
        total = indomitable_might_score

    parts.append(f"Total: {total}")

    breakdown = " + ".join(parts)
    return total, breakdown


def check_hit(attack_roll: int, target_ac: int) -> bool:
    """Check if an attack roll hits the target's AC"""
    return attack_roll >= target_ac


def is_critical_hit(attack_roll: int, advantage: bool = False) -> bool:
    """
    Check if an attack is a critical hit (natural 20)
    Note: This checks the base d20 roll, not the total
    For simplicity, we'll check if roll is 20 (or both dice are 20 with advantage)
    """
    # This is simplified - in a real implementation, you'd track the base d20 roll
    # For now, we'll check if the roll is 20 (which would be the base roll if total is high enough)
    return attack_roll >= 20  # Simplified check



def apply_resistance(damage: int, resistance_type: str) -> int:
    """
    Apply damage resistance/immunity/vulnerability
    resistance_type: 'resistance', 'immunity', 'vulnerability'
    """
    if resistance_type == 'immunity':
        return 0
    elif resistance_type == 'resistance':
        return damage // 2  # Half damage
    elif resistance_type == 'vulnerability':
        return damage * 2  # Double damage
    return damage


MAX_TOTAL_COMBATS_PER_USER = 10
MAX_ACTIVE_COMBATS_PER_USER = 2


def enforce_user_combat_limits(user, auto_delete_oldest: bool = False):
    """
    Enforces maximum combat session limits per user:
      - MAX_ACTIVE_COMBATS_PER_USER = 2
      - MAX_TOTAL_COMBATS_PER_USER = 10
    
    If auto_delete_oldest is True:
      - If active battles >= 2, deletes the oldest active session(s) until active < 2.
      - If total battles >= 10, deletes oldest sessions (preferring ended ones first) until total < 10.
    If auto_delete_oldest is False:
      - Raises rest_framework.exceptions.ValidationError with specific error codes.
    """
    if not user or not user.is_authenticated:
        return

    from rest_framework.exceptions import ValidationError
    from combat.models import CombatSession
    from gauntlet.models import GauntletRun

    # Purge any abandoned empty preparing sessions first
    CombatSession.objects.filter(
        created_by=user,
        status='preparing',
        participants__isnull=True
    ).delete()

    user_sessions = CombatSession.objects.filter(created_by=user)

    # 1. Check Active battles limit (max 2)
    active_sessions_qs = user_sessions.filter(
        status__in=['preparing', 'active']
    ).exclude(
        status='preparing',
        participants__isnull=True
    ).order_by('started_at', 'id')

    active_count = active_sessions_qs.count()
    if active_count >= MAX_ACTIVE_COMBATS_PER_USER:
        if auto_delete_oldest:
            excess_active = active_count - MAX_ACTIVE_COMBATS_PER_USER + 1
            oldest_active_ids = list(active_sessions_qs.values_list('id', flat=True)[:excess_active])
            GauntletRun.objects.filter(
                current_combat_session_id__in=oldest_active_ids,
                status__in=['preparing', 'active', 'respite']
            ).update(status='failed')
            CombatSession.objects.filter(id__in=oldest_active_ids).delete()
        else:
            raise ValidationError({
                "error": f"Active combat limit reached. You can have a maximum of {MAX_ACTIVE_COMBATS_PER_USER} active combat sessions. Please finish or delete an active combat session before starting a new one.",
                "code": "ACTIVE_LIMIT_REACHED",
                "limit_type": "active",
                "active_count": active_count,
                "max_active": MAX_ACTIVE_COMBATS_PER_USER
            })

    # 2. Check Total battles limit (max 10)
    user_sessions = CombatSession.objects.filter(created_by=user)
    total_count = user_sessions.count()

    if total_count >= MAX_TOTAL_COMBATS_PER_USER:
        if auto_delete_oldest:
            needed_deletions = total_count - MAX_TOTAL_COMBATS_PER_USER + 1
            ended_sessions = list(user_sessions.filter(status='ended').order_by('started_at', 'id').values_list('id', flat=True))
            to_delete_ids = ended_sessions[:needed_deletions]

            if len(to_delete_ids) < needed_deletions:
                remaining_needed = needed_deletions - len(to_delete_ids)
                remaining_sessions = list(
                    user_sessions.exclude(id__in=to_delete_ids).order_by('started_at', 'id').values_list('id', flat=True)[:remaining_needed]
                )
                to_delete_ids.extend(remaining_sessions)

            GauntletRun.objects.filter(
                current_combat_session_id__in=to_delete_ids,
                status__in=['preparing', 'active', 'respite']
            ).update(status='failed')
            CombatSession.objects.filter(id__in=to_delete_ids).delete()
        else:
            raise ValidationError({
                "error": f"Combat archive limit reached. You can have a maximum of {MAX_TOTAL_COMBATS_PER_USER} saved combat sessions. Please delete an older session to create a new one.",
                "code": "TOTAL_LIMIT_REACHED",
                "limit_type": "total",
                "total_count": total_count,
                "max_total": MAX_TOTAL_COMBATS_PER_USER
            })


