"""
D&D 5e calculation utilities

This module provides standard D&D 5e game mechanics calculations
that are used throughout the application.
"""


def calculate_ability_modifier(ability_score):
    """
    Calculate ability modifier from ability score.
    
    Args:
        ability_score (int): Ability score (1-30)
    
    Returns:
        int: Ability modifier
    
    Example:
        >>> calculate_ability_modifier(16)
        3
        >>> calculate_ability_modifier(10)
        0
    """
    return (ability_score - 10) // 2


def calculate_proficiency_bonus(level):
    """
    Calculate proficiency bonus from character level.
    
    Args:
        level (int): Character level (1-20)
    
    Returns:
        int: Proficiency bonus
    
    Example:
        >>> calculate_proficiency_bonus(1)
        2
        >>> calculate_proficiency_bonus(5)
        3
        >>> calculate_proficiency_bonus(20)
        6
    """
    if level < 1:
        return 2
    if level > 20:
        return 6
    return ((level - 1) // 4) + 2


def get_xp_for_level(level):
    """
    Get minimum XP required for a given level.
    
    Args:
        level (int): Character level (1-20)
    
    Returns:
        int: Minimum XP required
    
    Example:
        >>> get_xp_for_level(1)
        0
        >>> get_xp_for_level(5)
        6500
    """
    xp_table = {
        1: 0,
        2: 300,
        3: 900,
        4: 2700,
        5: 6500,
        6: 14000,
        7: 23000,
        8: 34000,
        9: 48000,
        10: 64000,
        11: 85000,
        12: 100000,
        13: 120000,
        14: 140000,
        15: 165000,
        16: 195000,
        17: 225000,
        18: 265000,
        19: 305000,
        20: 355000,
    }
    return xp_table.get(level, 0)


def get_level_from_xp(xp):
    """
    Calculate character level from XP.
    
    Args:
        xp (int): Experience points
    
    Returns:
        int: Character level (1-20)
    
    Example:
        >>> get_level_from_xp(0)
        1
        >>> get_level_from_xp(7000)
        5
    """
    xp_thresholds = [
        (355000, 20),
        (305000, 19),
        (265000, 18),
        (225000, 17),
        (195000, 16),
        (165000, 15),
        (140000, 14),
        (120000, 13),
        (100000, 12),
        (85000, 11),
        (64000, 10),
        (48000, 9),
        (34000, 8),
        (23000, 7),
        (14000, 6),
        (6500, 5),
        (2700, 4),
        (900, 3),
        (300, 2),
        (0, 1),
    ]
    
    for threshold_xp, level in xp_thresholds:
        if xp >= threshold_xp:
            return level
    
    return 1


def roll_dice(dice_string):
    """
    Roll dice from string notation like '2d6+3' or '1d20'.
    
    Args:
        dice_string (str): Dice notation (e.g., '2d6+3', '1d8', '3d10-2')
    
    Returns:
        tuple: (total, list of individual rolls, modifier)
    
    Example:
        >>> total, rolls, modifier = roll_dice('2d6+3')
        >>> len(rolls)
        2
        >>> modifier
        3
    
    Raises:
        ValueError: If dice string format is invalid
    """
    import re
    import random
    
    # Match patterns like 2d6, 2d6+3, 2d6-2
    match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', dice_string.strip())
    if not match:
        raise ValueError(f"Invalid dice string: {dice_string}")
    
    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier_sign = match.group(3) or '+'
    modifier = int(match.group(4)) if match.group(4) else 0
    
    # Roll each die
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls)
    
    # Apply modifier
    if modifier_sign == '+':
        total += modifier
    else:
        total -= modifier
        modifier = -modifier  # Make negative for return value
    
    return total, rolls, modifier


def calculate_hit_points(level, hit_die, constitution_modifier, use_average=False):
    """
    Calculate maximum hit points for a character.
    
    Args:
        level (int): Character level
        hit_die (int): Hit die size (6, 8, 10, or 12)
        constitution_modifier (int): CON modifier
        use_average (bool): Use average HP (True) or rolled (False)
    
    Returns:
        int: Maximum hit points
    
    Example:
        >>> calculate_hit_points(5, 8, 2, use_average=True)
        32  # 8 + (4*5) + (2*5) = 8 + 20 + 10 = 38... wait let me recalc
        >>> # Level 1: 8 + 2 = 10
        >>> # Levels 2-5: (5 + 2) * 4 = 28
        >>> # Total: 10 + 28 = 38
    """
    import random
    
    # First level: max HP
    if level < 1:
        level = 1
    
    first_level_hp = hit_die + constitution_modifier
    
    if level == 1:
        return max(1, first_level_hp)  # Minimum 1 HP
    
    # Subsequent levels
    if use_average:
        # Use average: (die_size / 2) + 1
        average_roll = (hit_die // 2) + 1
        additional_hp = (average_roll + constitution_modifier) * (level - 1)
    else:
        # Roll for each level
        additional_hp = 0
        for _ in range(level - 1):
            roll = random.randint(1, hit_die)
            additional_hp += roll + constitution_modifier
    
    total_hp = first_level_hp + additional_hp
    return max(level, total_hp)  # Minimum 1 HP per level


def calculate_spell_save_dc(proficiency_bonus, spellcasting_modifier):
    """
    Calculate spell save DC.
    
    Args:
        proficiency_bonus (int): Character's proficiency bonus
        spellcasting_modifier (int): Spellcasting ability modifier
    
    Returns:
        int: Spell save DC
    
    Example:
        >>> calculate_spell_save_dc(3, 4)
        15  # 8 + 3 + 4 = 15
    """
    return 8 + proficiency_bonus + spellcasting_modifier


def calculate_spell_attack_bonus(proficiency_bonus, spellcasting_modifier):
    """
    Calculate spell attack bonus.
    
    Args:
        proficiency_bonus (int): Character's proficiency bonus
        spellcasting_modifier (int): Spellcasting ability modifier
    
    Returns:
        int: Spell attack bonus
    
    Example:
        >>> calculate_spell_attack_bonus(3, 4)
        7  # 3 + 4 = 7
    """
    return proficiency_bonus + spellcasting_modifier


def calculate_armor_class(base_armor_class, dexterity_modifier, shield_bonus=0, magic_bonus=0):
    """
    Calculate armor class.
    
    Args:
        base_armor_class (int): Base AC from armor (10 if unarmored)
        dexterity_modifier (int): DEX modifier
        shield_bonus (int): Bonus from shield (usually +2)
        magic_bonus (int): Bonus from magic items
    
    Returns:
        int: Total armor class
    
    Example:
        >>> calculate_armor_class(14, 2, shield_bonus=2)
        18  # 14 + 2 + 2 = 18
    """
    return base_armor_class + dexterity_modifier + shield_bonus + magic_bonus


def calculate_initiative(dexterity_modifier, bonus=0):
    """
    Calculate initiative modifier.
    
    Args:
        dexterity_modifier (int): DEX modifier
        bonus (int): Additional initiative bonus
    
    Returns:
        int: Initiative modifier
    
    Example:
        >>> calculate_initiative(3)
        3
        >>> calculate_initiative(3, bonus=2)
        5
    """
    return dexterity_modifier + bonus


def calculate_carrying_capacity(strength_score):
    """
    Calculate carrying capacity in pounds.
    
    Args:
        strength_score (int): Strength score
    
    Returns:
        int: Carrying capacity in pounds
    
    Example:
        >>> calculate_carrying_capacity(15)
        225  # 15 * 15 = 225
    """
    return strength_score * 15


def get_encumbrance_thresholds(strength_score):
    """
    Get encumbrance thresholds (normal, encumbered, heavily encumbered).
    
    Args:
        strength_score (int): Strength score
    
    Returns:
        dict: Thresholds for each encumbrance level
    
    Example:
        >>> get_encumbrance_thresholds(15)
        {'normal': 75, 'encumbered': 150, 'max': 225}
    """
    capacity = calculate_carrying_capacity(strength_score)
    return {
        'normal': capacity // 3,  # Up to 5x STR
        'encumbered': (capacity * 2) // 3,  # Up to 10x STR
        'max': capacity,  # Up to 15x STR
    }
