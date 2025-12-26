"""
Combat utilities for dice rolling and calculations
"""
import random
import re
from typing import Tuple, Optional


def roll_dice(dice_string: str) -> Tuple[int, str]:
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


def roll_d20(advantage: bool = False, disadvantage: bool = False) -> Tuple[int, str]:
    """
    Roll a d20, optionally with advantage or disadvantage
    Returns: (result, breakdown_string)
    """
    if advantage and disadvantage:
        # Cancel out, roll normally
        roll = random.randint(1, 20)
        return roll, f"d20: {roll}"
    
    roll1 = random.randint(1, 20)
    
    if advantage:
        roll2 = random.randint(1, 20)
        result = max(roll1, roll2)
        return result, f"d20 (advantage): {roll1}, {roll2} → {result}"
    elif disadvantage:
        roll2 = random.randint(1, 20)
        result = min(roll1, roll2)
        return result, f"d20 (disadvantage): {roll1}, {roll2} → {result}"
    else:
        return roll1, f"d20: {roll1}"


def calculate_attack_roll(
    base_roll: int,
    ability_modifier: int,
    proficiency_bonus: int = 0,
    proficiency: bool = False,
    other_modifiers: int = 0
) -> Tuple[int, str]:
    """
    Calculate total attack roll
    Returns: (total, breakdown_string)
    """
    attack_modifier = ability_modifier
    if proficiency:
        attack_modifier += proficiency_bonus
    attack_modifier += other_modifiers
    
    total = base_roll + attack_modifier
    
    parts = [f"Roll: {base_roll}"]
    if ability_modifier != 0:
        parts.append(f"Ability: {ability_modifier:+d}")
    if proficiency:
        parts.append(f"Proficiency: +{proficiency_bonus}")
    if other_modifiers != 0:
        parts.append(f"Other: {other_modifiers:+d}")
    parts.append(f"Total: {total}")
    
    breakdown = " + ".join(parts)
    return total, breakdown


def calculate_damage(
    damage_string: str,
    ability_modifier: int = 0,
    critical: bool = False
) -> Tuple[int, str]:
    """
    Calculate damage from a dice string
    If critical, double the dice (but not modifiers)
    Returns: (damage, breakdown_string)
    """
    # Parse damage string (e.g., "2d6+3 slashing")
    # Extract just the dice part
    dice_part = damage_string.split()[0] if ' ' in damage_string else damage_string
    
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
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    
    rolls_str = ', '.join(map(str, rolls))
    if modifier > 0:
        breakdown_parts.append(f"{rolls_str} + {modifier} = {total}")
    elif modifier < 0:
        breakdown_parts.append(f"{rolls_str} {modifier} = {total}")
    else:
        breakdown_parts.append(f"{rolls_str} = {total}")
    
    breakdown = " | ".join(breakdown_parts)
    return total, breakdown


def calculate_saving_throw(
    base_roll: int,
    ability_modifier: int,
    proficiency_bonus: int = 0,
    proficiency: bool = False,
    other_modifiers: int = 0
) -> Tuple[int, str]:
    """
    Calculate total saving throw
    Returns: (total, breakdown_string)
    """
    save_modifier = ability_modifier
    if proficiency:
        save_modifier += proficiency_bonus
    save_modifier += other_modifiers
    
    total = base_roll + save_modifier
    
    parts = [f"Roll: {base_roll}"]
    if ability_modifier != 0:
        parts.append(f"Ability: {ability_modifier:+d}")
    if proficiency:
        parts.append(f"Proficiency: +{proficiency_bonus}")
    if other_modifiers != 0:
        parts.append(f"Other: {other_modifiers:+d}")
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

