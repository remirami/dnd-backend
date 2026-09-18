"""
Multiclassing System for D&D 5e Characters

Handles multiclass prerequisites, spell slot calculation, and feature progression.
"""



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
    
    # Normalize class name to title case for lookup (models store lowercase, dict uses Title Case)
    normalized_class_name = target_class_name.title()
    
    # Get prerequisites
    prerequisites = MULTICLASS_PREREQUISITES.get(normalized_class_name, {})
    
    if not prerequisites:
        return False, f"No prerequisites defined for {normalized_class_name}"
    
    # Check ability score requirements
    stats = character.stats
    missing_requirements = []
    
    # Fighter can use STR or DEX
    if normalized_class_name == 'Fighter':
        if stats.strength < 13 and stats.dexterity < 13:
            missing_requirements.append("STR 13 or DEX 13")
    # Monk needs DEX and WIS
    elif normalized_class_name == 'Monk':
        if stats.dexterity < 13:
            missing_requirements.append("DEX 13")
        if stats.wisdom < 13:
            missing_requirements.append("WIS 13")
    # Paladin needs STR and CHA
    elif normalized_class_name == 'Paladin':
        if stats.strength < 13:
            missing_requirements.append("STR 13")
        if stats.charisma < 13:
            missing_requirements.append("CHA 13")
    # Ranger needs DEX and WIS
    elif normalized_class_name == 'Ranger':
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


def _get_class_levels(character):
    """Get class levels for character, utilizing in-memory prefetch cache if available"""
    if hasattr(character, '_prefetched_objects_cache') and 'class_levels' in character._prefetched_objects_cache:
        return list(character.class_levels.all())
    from .models import CharacterClassLevel
    return list(CharacterClassLevel.objects.filter(character=character).select_related('character_class'))


def calculate_multiclass_spell_slots(character):
    """
    Calculate spell slots for a multiclass character based on 5e rules.
    Returns: dict mapping spell level to number of slots
    """
    class_levels = _get_class_levels(character)
    
    if not class_levels:
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
    if not character.stats:
        return None
    
    class_levels = _get_class_levels(character)
    stats = character.stats
    
    spellcasting_abilities = []
    
    for class_level in class_levels:
        class_name = class_level.character_class.name
        # Try both lowercase and capitalized
        ability = SPELLCASTING_CLASSES.get(class_name) or SPELLCASTING_CLASSES.get(class_name.capitalize())
        
        if ability:
            ability_value = getattr(stats, ability, 10)
            from core.dnd_utils import calculate_ability_modifier
            ability_modifier = calculate_ability_modifier(ability_value)
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
    class_levels = _get_class_levels(character)
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
    class_levels = _get_class_levels(character)
    if class_levels:
        return sum(class_level.level for class_level in class_levels)
    return getattr(character, 'level', 1)


def get_class_level(character, class_name):
    """Get level in a specific class"""
    class_name_lower = class_name.lower()
    for cl in _get_class_levels(character):
        if cl.character_class.name.lower() == class_name_lower:
            return cl.level
    return 0


def get_primary_class(character):
    """Get the primary class (highest level, or first if tied)"""
    class_levels = _get_class_levels(character)
    if class_levels:
        sorted_levels = sorted(class_levels, key=lambda cl: (-cl.level, cl.id))
        return sorted_levels[0].character_class
    
    return character.character_class

