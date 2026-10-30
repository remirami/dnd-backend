"""
Multiclassing System for SRD 5.2 5e Characters

Handles multiclass prerequisites, spell slot calculation, and feature progression.
"""



# Multiclass prerequisites (ability score requirements)
# 2014 Rules
MULTICLASS_PREREQUISITES_2014 = {
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

# 2024 Rules (SRD 5.2): Paladin & Ranger can qualify via STR or DEX
MULTICLASS_PREREQUISITES_2024 = {
    'Barbarian': {'strength': 13},
    'Bard': {'charisma': 13},
    'Cleric': {'wisdom': 13},
    'Druid': {'wisdom': 13},
    'Fighter': {'strength': 13, 'dexterity': 13},  # STR or DEX
    'Monk': {'dexterity': 13, 'wisdom': 13},
    'Paladin': {'strength': 13, 'dexterity': 13, 'charisma': 13},  # (STR or DEX) and CHA
    'Ranger': {'strength': 13, 'dexterity': 13, 'wisdom': 13},     # (STR or DEX) and WIS
    'Rogue': {'dexterity': 13},
    'Sorcerer': {'charisma': 13},
    'Warlock': {'charisma': 13},
    'Wizard': {'intelligence': 13},
}

MULTICLASS_PREREQUISITES = MULTICLASS_PREREQUISITES_2014


def get_multiclass_prerequisites(class_name, ruleset='2014'):
    """Get prerequisites dictionary for a class by name and ruleset"""
    norm = class_name.title() if class_name else ''
    prereqs_dict = MULTICLASS_PREREQUISITES_2024 if ruleset == '2024' else MULTICLASS_PREREQUISITES_2014
    return prereqs_dict.get(norm, {})


def check_class_prerequisites(stats, class_name, ruleset='2014'):
    """
    Check if a set of stats meets the multiclass prerequisites for a specific class.
    Returns: (meets_prereqs, missing_requirements_list)
    """
    if not stats or not class_name:
        return False, ["Missing stats or class"]

    norm = class_name.title()
    missing = []

    if norm == 'Fighter':
        if stats.strength < 13 and stats.dexterity < 13:
            missing.append("STR 13 or DEX 13")
    elif norm == 'Monk':
        if stats.dexterity < 13:
            missing.append("DEX 13")
        if stats.wisdom < 13:
            missing.append("WIS 13")
    elif norm == 'Paladin':
        if ruleset == '2024':
            if stats.strength < 13 and stats.dexterity < 13:
                missing.append("STR 13 or DEX 13")
        else:
            if stats.strength < 13:
                missing.append("STR 13")
        if stats.charisma < 13:
            missing.append("CHA 13")
    elif norm == 'Ranger':
        if ruleset == '2024':
            if stats.strength < 13 and stats.dexterity < 13:
                missing.append("STR 13 or DEX 13")
        else:
            if stats.dexterity < 13:
                missing.append("DEX 13")
        if stats.wisdom < 13:
            missing.append("WIS 13")
    else:
        prereqs = get_multiclass_prerequisites(norm, ruleset)
        if not prereqs:
            return False, [f"No prerequisites defined for {norm}"]
        for ability, minimum in prereqs.items():
            val = getattr(stats, ability, 0)
            if val < minimum:
                missing.append(f"{ability.upper()} {minimum}")

    return (len(missing) == 0), missing


# Multiclass proficiencies granted upon taking 1st level in a multiclass
MULTICLASS_PROFICIENCIES = {
    'barbarian': {
        'armor': ['Shields'],
        'weapon': ['Simple Weapons', 'Martial Weapons']
    },
    'bard': {
        'armor': ['Light Armor'],
        'tool': ['Musical Instrument']
    },
    'cleric': {
        'armor': ['Light Armor', 'Medium Armor', 'Shields']
    },
    'druid': {
        'armor': ['Light Armor', 'Medium Armor', 'Shields']
    },
    'fighter': {
        'armor': ['Light Armor', 'Medium Armor', 'Shields'],
        'weapon': ['Simple Weapons', 'Martial Weapons']
    },
    'monk': {
        'weapon': ['Simple Weapons', 'Shortswords']
    },
    'paladin': {
        'armor': ['Light Armor', 'Medium Armor', 'Shields'],
        'weapon': ['Simple Weapons', 'Martial Weapons']
    },
    'ranger': {
        'armor': ['Light Armor', 'Medium Armor', 'Shields'],
        'weapon': ['Simple Weapons', 'Martial Weapons']
    },
    'rogue': {
        'armor': ['Light Armor'],
        'tool': ["Thieves' Tools"]
    },
    'sorcerer': {},
    'warlock': {
        'armor': ['Light Armor'],
        'weapon': ['Simple Weapons']
    },
    'wizard': {},
}


def apply_multiclass_proficiencies(character, new_class_name):
    """
    Grant multiclass proficiencies when gaining the first level in a new class.
    Returns list of granted CharacterProficiency instances.
    """
    from .models import CharacterProficiency

    key = new_class_name.lower()
    profs_data = MULTICLASS_PROFICIENCIES.get(key, {})
    granted = []

    for category, items in profs_data.items():
        for item in items:
            prof, created = CharacterProficiency.objects.get_or_create(
                character=character,
                proficiency_type=category,
                item_name=item,
                defaults={
                    'source': f"Multiclass ({new_class_name.title()})"
                }
            )
            if created:
                granted.append(prof)

    return granted


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
    Under 5e rules, a character must meet the ability score prerequisites
    for BOTH their current class(es) AND the new target class.
    Returns: (can_multiclass, reason)
    """
    if not character.stats:
        return False, "Character has no stats"
    
    # Check if already has this class
    from .models import CharacterClassLevel
    if CharacterClassLevel.objects.filter(character=character, character_class__name__iexact=target_class_name).exists():
        return False, f"Already has levels in {target_class_name}"
    
    ruleset = getattr(character, 'ruleset_version', '2014')
    stats = character.stats
    
    # 1. Verify current class(es) prerequisites
    current_classes = list(character.class_levels.all())
    if not current_classes and character.character_class:
        # Fallback to primary class if class_levels not yet populated
        current_classes = [type('DummyClassLevel', (), {'character_class': character.character_class})()]
        
    for cl in current_classes:
        cur_name = cl.character_class.name
        meets, missing = check_class_prerequisites(stats, cur_name, ruleset)
        if not meets:
            return False, f"Missing prerequisites for current class {cur_name.title()}: {', '.join(missing)}"
            
    # 2. Verify target class prerequisites
    meets, missing = check_class_prerequisites(stats, target_class_name, ruleset)
    if not meets:
        return False, f"Missing prerequisites for {target_class_name.title()}: {', '.join(missing)}"
    
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
    Under 2024 rules (SRD 5.2), half-caster levels round up.
    Returns: dict mapping spell level to number of slots
    """
    class_levels = _get_class_levels(character)
    
    if not class_levels:
        return {}
    
    # Calculate caster level
    caster_level = 0
    is_2024 = getattr(character, 'ruleset_version', '2014') == '2024'
    
    for class_level in class_levels:
        class_name = class_level.character_class.name
        # Normalize to capitalized for comparison
        class_name_capitalized = class_name.capitalize()
        level = class_level.level
        
        if class_name_capitalized in FULL_CASTERS or class_name in FULL_CASTERS:
            caster_level += level
        elif class_name_capitalized in HALF_CASTERS or class_name in HALF_CASTERS:
            if is_2024:
                # 2024 SRD 5.2: half-caster levels round up
                caster_level += (level + 1) // 2
            else:
                # 2014 rules: half-caster levels round down
                caster_level += level // 2
        elif class_name_capitalized in THIRD_CASTERS or class_name in THIRD_CASTERS:
            caster_level += level // 3
        # Warlock doesn't contribute to standard multiclass spell slots (Pact Magic)
    
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
    from django.db.models import Sum
    from .models import CharacterClassLevel
    total = CharacterClassLevel.objects.filter(character=character).aggregate(Sum('level'))['level__sum']
    if total is not None and total > 0:
        return total
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

