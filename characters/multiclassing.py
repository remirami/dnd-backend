"""
Multiclassing System for D&D 5e Characters

Handles multiclass prerequisites, spell slot calculation, and feature progression.
"""

from .models import Character, CharacterClass


# Multiclass prerequisites (ability score requirements)
MULTICLASS_PREREQUISITES = {
    'Barbarian': {'strength': 13},
    'Bard': {'charisma': 13},
    'Cleric': {'wisdom': 13},
    'Druid': {'wisdom': 13},
    'Fighter': {'strength': 13, 'dexterity': 13},  # STR or DEX
    'Monk': {'dexterity': 13, 'wisdom': 13},
    'Paladin': {'strength': 13, 'charisma': 13},
    'Ranger': {'dexterity': 13, 'wisdom': 13},
    'Rogue': {'dexterity': 13},
    'Sorcerer': {'charisma': 13},
    'Warlock': {'charisma': 13},
    'Wizard': {'intelligence': 13},
}


# Spellcasting classes and their spellcasting ability
SPELLCASTING_CLASSES = {
    'Bard': 'charisma',
    'Cleric': 'wisdom',
    'Druid': 'wisdom',
    'Paladin': 'charisma',
    'Ranger': 'wisdom',
    'Sorcerer': 'charisma',
    'Warlock': 'charisma',
    'Wizard': 'intelligence',
    'Eldritch Knight': 'intelligence',  # Fighter subclass
    'Arcane Trickster': 'intelligence',  # Rogue subclass
}


# Full caster classes (for multiclass spell slot calculation)
FULL_CASTERS = ['Bard', 'Cleric', 'Druid', 'Sorcerer', 'Wizard']

# Half caster classes
HALF_CASTERS = ['Paladin', 'Ranger']

# Third caster classes (subclasses)
THIRD_CASTERS = ['Eldritch Knight', 'Arcane Trickster']

# Pact magic (Warlock - separate from spell slots)
PACT_MAGIC = ['Warlock']


def can_multiclass_into(character, target_class_name):
    """
    Check if character meets prerequisites to multiclass into target class.
    Returns: (can_multiclass, reason)
    """
    if not character.stats:
        return False, "Character has no stats"
    
    # Check if already has this class
    from .models import CharacterClassLevel
    if CharacterClassLevel.objects.filter(character=character, character_class__name=target_class_name).exists():
        return False, f"Already has levels in {target_class_name}"
    
    # Get prerequisites
    prerequisites = MULTICLASS_PREREQUISITES.get(target_class_name, {})
    
    if not prerequisites:
        return False, f"No prerequisites defined for {target_class_name}"
    
    # Check ability score requirements
    stats = character.stats
    missing_requirements = []
    
    # Fighter can use STR or DEX
    if target_class_name == 'Fighter':
        if stats.strength < 13 and stats.dexterity < 13:
            missing_requirements.append("STR 13 or DEX 13")
    # Monk needs DEX and WIS
    elif target_class_name == 'Monk':
        if stats.dexterity < 13:
            missing_requirements.append("DEX 13")
        if stats.wisdom < 13:
            missing_requirements.append("WIS 13")
    # Paladin needs STR and CHA
    elif target_class_name == 'Paladin':
        if stats.strength < 13:
            missing_requirements.append("STR 13")
        if stats.charisma < 13:
            missing_requirements.append("CHA 13")
    # Ranger needs DEX and WIS
    elif target_class_name == 'Ranger':
        if stats.dexterity < 13:
            missing_requirements.append("DEX 13")
        if stats.wisdom < 13:
            missing_requirements.append("WIS 13")
    # All others need single ability score
    else:
        for ability, minimum in prerequisites.items():
            ability_value = getattr(stats, ability, 0)
            if ability_value < minimum:
                missing_requirements.append(f"{ability.upper()} {minimum}")
    
    if missing_requirements:
        return False, f"Missing prerequisites: {', '.join(missing_requirements)}"
    
    return True, "Prerequisites met"


def calculate_multiclass_spell_slots(character):
    """
    Calculate spell slots for multiclass spellcasters.
    Uses the multiclass spellcaster table from D&D 5e.
    
    Returns: dict mapping spell level to number of slots
    """
    from .models import CharacterClassLevel
    
    # Get all class levels
    class_levels = CharacterClassLevel.objects.filter(character=character)
    
    if not class_levels.exists():
        return {}
    
    # Calculate caster level
    caster_level = 0
    
    for class_level in class_levels:
        class_name = class_level.character_class.name
        # Normalize to capitalized for comparison
        class_name_capitalized = class_name.capitalize()
        level = class_level.level
        
        if class_name_capitalized in FULL_CASTERS or class_name in FULL_CASTERS:
            caster_level += level
        elif class_name_capitalized in HALF_CASTERS or class_name in HALF_CASTERS:
            caster_level += level // 2
        elif class_name_capitalized in THIRD_CASTERS or class_name in THIRD_CASTERS:
            caster_level += level // 3
        # Warlock doesn't contribute to spell slot calculation
    
    # Multiclass spell slot table
    MULTICLASS_SPELL_SLOTS = {
        1: {1: 2},
        2: {1: 3},
        3: {1: 4, 2: 2},
        4: {1: 4, 2: 3},
        5: {1: 4, 2: 3, 3: 2},
        6: {1: 4, 2: 3, 3: 3},
        7: {1: 4, 2: 3, 3: 3, 4: 1},
        8: {1: 4, 2: 3, 3: 3, 4: 2},
        9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
        10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
        11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
        12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
        13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
        14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
        15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
        16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
        17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
        18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
        19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
        20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    }
    
    return MULTICLASS_SPELL_SLOTS.get(caster_level, {})


def get_multiclass_spellcasting_ability(character):
    """
    Get spellcasting ability for multiclass character.
    Uses the highest ability modifier from all spellcasting classes.
    """
    from .models import CharacterClassLevel
    
    if not character.stats:
        return None
    
    class_levels = CharacterClassLevel.objects.filter(character=character)
    stats = character.stats
    
    spellcasting_abilities = []
    
    for class_level in class_levels:
        class_name = class_level.character_class.name
        # Try both lowercase and capitalized
        ability = SPELLCASTING_CLASSES.get(class_name) or SPELLCASTING_CLASSES.get(class_name.capitalize())
        
        if ability:
            ability_value = getattr(stats, ability, 10)
            ability_modifier = (ability_value - 10) // 2
            spellcasting_abilities.append((ability, ability_modifier))
    
    if not spellcasting_abilities:
        return None
    
    # Return ability with highest modifier
    best_ability = max(spellcasting_abilities, key=lambda x: x[1])
    return best_ability[0]


def get_multiclass_hit_dice(character):
    """
    Get hit dice for multiclass character.
    Returns dict mapping die type to count.
    """
    from .models import CharacterClassLevel
    
    class_levels = CharacterClassLevel.objects.filter(character=character)
    hit_dice = {}
    
    for class_level in class_levels:
        hit_dice_type = class_level.character_class.hit_dice
        level = class_level.level
        
        if hit_dice_type in hit_dice:
            hit_dice[hit_dice_type] += level
        else:
            hit_dice[hit_dice_type] = level
    
    return hit_dice


def get_total_level(character):
    """Get total character level (sum of all class levels)"""
    from .models import CharacterClassLevel
    
    class_levels = CharacterClassLevel.objects.filter(character=character)
    return sum(class_level.level for class_level in class_levels)


def get_class_level(character, class_name):
    """Get level in a specific class"""
    from .models import CharacterClassLevel
    
    # Normalize class name to lowercase
    class_name_lower = class_name.lower()
    
    try:
        class_level = CharacterClassLevel.objects.get(
            character=character,
            character_class__name=class_name_lower
        )
        return class_level.level
    except CharacterClassLevel.DoesNotExist:
        return 0


def get_primary_class(character):
    """Get the primary class (highest level, or first if tied)"""
    from .models import CharacterClassLevel
    
    class_levels = CharacterClassLevel.objects.filter(character=character).order_by('-level', 'id')
    
    if class_levels.exists():
        return class_levels.first().character_class
    
    # Fallback to character_class field
    return character.character_class

