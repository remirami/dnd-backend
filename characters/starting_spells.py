"""
Starting Spell Selection Rules for D&D 5e Classes

Defines how many cantrips and spells each class gets at level 1,
and the rules for spell selection (prepared vs. known casters).
"""

# Spell selection rules for each class at level 1
STARTING_SPELL_RULES = {
    'Wizard': {
        'cantrips': 3,
        'spells': {
            'type': 'prepared',  # Prepared caster with spellbook
            'spellbook_size': 6,  # Add 6 spells to spellbook at creation
            'can_prepare_formula': 'level + intelligence_modifier',
            'min_prepared': 1,
        },
        'description': 'Choose 3 cantrips and 6 1st-level spells for your spellbook. You can prepare a number of spells equal to your level + Intelligence modifier (minimum 1).'
    },
    'Cleric': {
        'cantrips': 3,
        'spells': {
            'type': 'prepared',  # Prepared caster with access to all class spells
            'can_prepare_formula': 'level + wisdom_modifier',
            'min_prepared': 1,
        },
        'description': 'Choose 3 cantrips. You have access to all Cleric spells and can prepare a number equal to your level + Wisdom modifier (minimum 1).'
    },
    'Druid': {
        'cantrips': 2,
        'spells': {
            'type': 'prepared',  # Prepared caster with access to all class spells
            'can_prepare_formula': 'level + wisdom_modifier',
            'min_prepared': 1,
        },
        'description': 'Choose 2 cantrips. You have access to all Druid spells and can prepare a number equal to your level + Wisdom modifier (minimum 1).'
    },
    'Sorcerer': {
        'cantrips': 4,
        'spells': {
            'type': 'known',  # Known caster - spells are permanent
            'spells_known': 2,
        },
        'description': 'Choose 4 cantrips and 2 1st-level spells. These spells are permanently known and can only be changed when you level up.'
    },
    'Bard': {
        'cantrips': 2,
        'spells': {
            'type': 'known',  # Known caster - spells are permanent
            'spells_known': 4,
        },
        'description': 'Choose 2 cantrips and 4 1st-level spells. These spells are permanently known and can only be changed when you level up.'
    },
    'Warlock': {
        'cantrips': 2,
        'spells': {
            'type': 'known',  # Known caster - spells are permanent
            'spells_known': 2,
        },
        'description': 'Choose 2 cantrips and 2 1st-level spells. These spells are permanently known and can only be changed when you level up.'
    },
    'Paladin': {
        'cantrips': 0,
        'spells': {
            'type': 'prepared',
            'can_prepare_formula': 'level + charisma_modifier',
            'min_prepared': 0,  # Paladins don't get spells at level 1
            'starting_level': 2,  # They get spells at level 2
        },
        'description': 'Paladins do not gain spellcasting until level 2.'
    },
    'Ranger': {
        'cantrips': 0,
        'spells': {
            'type': 'known',
            'spells_known': 0,  # Rangers don't get spells at level 1
            'starting_level': 2,  # They get spells at level 2
        },
        'description': 'Rangers do not gain spellcasting until level 2.'
    },
}

# Non-spellcasting classes
NON_CASTERS = ['Fighter', 'Barbarian', 'Rogue', 'Monk']


def get_starting_spell_rules(class_name):
    """
    Get the starting spell selection rules for a class.
    
    Args:
        class_name: Name of the character class (case-insensitive)
        
    Returns:
        Dictionary with spell selection rules, or None if not a caster
    """
    # Normalize class name
    class_name = class_name.strip().lower().capitalize()
    
    # Check if non-caster
    if class_name in NON_CASTERS:
        return None
    
    return STARTING_SPELL_RULES.get(class_name)


def is_caster_at_level_1(class_name):
    """
    Check if a class can cast spells at level 1.
    
    Args:
        class_name: Name of the character class (case-insensitive)
        
    Returns:
        True if the class can select spells at level 1, False otherwise
    """
    rules = get_starting_spell_rules(class_name)
    if not rules:
        return False
    
    # Check if they have cantrips or spells at level 1
    has_cantrips = rules.get('cantrips', 0) > 0
    spells_info = rules.get('spells', {})
    
    # Check if they start spellcasting at a later level
    if spells_info.get('starting_level', 1) > 1:
        return False
    
    # Known casters with known spells > 0
    if spells_info.get('type') == 'known' and spells_info.get('spells_known', 0) > 0:
        return True
    
    # Prepared casters with spellbook or prepared spells
    if spells_info.get('type') == 'prepared':
        if spells_info.get('spellbook_size', 0) > 0:  # Wizard
            return True
        if spells_info.get('min_prepared', 0) >= 0:  # Cleric/Druid (they can prepare)
            return True
    
    # If they have cantrips but no leveled spells, still show spell selection
    return has_cantrips


def calculate_starting_cantrips(class_name):
    """
    Calculate how many cantrips a class gets at level 1.
    
    Args:
        class_name: Name of the character class (case-insensitive)
        
    Returns:
        Number of cantrips (0 if not a caster)
    """
    rules = get_starting_spell_rules(class_name)
    if not rules:
        return 0
    
    return rules.get('cantrips', 0)


def calculate_starting_spells(class_name, character_stats=None):
    """
    Calculate how many leveled spells a class can select at level 1.
    
    Args:
        class_name: Name of the character class (case-insensitive)
        character_stats: CharacterStats object (needed for prepared casters)
        
    Returns:
        Dictionary with spell selection info, or None if not a caster
    """
    rules = get_starting_spell_rules(class_name)
    if not rules:
        return None
    
    spells_info = rules.get('spells', {})
    result = {
        'type': spells_info.get('type'),
        'count': 0,
        'description': rules.get('description', ''),
    }
    
    # Check if they start spellcasting at a later level
    if spells_info.get('starting_level', 1) > 1:
        result['count'] = 0
        return result
    
    # Known casters: fixed number
    if spells_info.get('type') == 'known':
        result['count'] = spells_info.get('spells_known', 0)
        return result
    
    # Prepared casters
    if spells_info.get('type') == 'prepared':
        # Wizards: add to spellbook
        if spells_info.get('spellbook_size'):
            result['count'] = spells_info.get('spellbook_size')
            result['is_spellbook'] = True
            return result
        
        # Other prepared casters: they don't "select" spells at creation
        # They have access to all class spells and just prepare from that list
        # For character creation, we won't have them select specific spells
        result['count'] = 0
        result['can_prepare_all'] = True
        
        # Calculate how many they can prepare (if stats provided)
        if character_stats:
            class_name_lower = class_name.lower()
            if class_name_lower == 'cleric':
                modifier = character_stats.wisdom_modifier
            elif class_name_lower == 'druid':
                modifier = character_stats.wisdom_modifier
            elif class_name_lower == 'paladin':
                modifier = character_stats.charisma_modifier
            else:
                modifier = 0
            
            # Level 1 + modifier, minimum from rules
            can_prepare = max(1 + modifier, spells_info.get('min_prepared', 1))
            result['can_prepare_count'] = can_prepare
        
        return result
    
    return result


def get_spell_selection_requirements(class_name, character_stats=None):
    """
    Get complete spell selection requirements for character creation.
    
    Args:
        class_name: Name of the character class (case-insensitive)
        character_stats: CharacterStats object (optional)
        
    Returns:
        Dictionary with all requirements, or None if not a level 1 caster
    """
    if not is_caster_at_level_1(class_name):
        return None
    
    rules = get_starting_spell_rules(class_name)
    spells_data = calculate_starting_spells(class_name, character_stats)
    
    return {
        'class_name': class_name,
        'cantrips_count': calculate_starting_cantrips(class_name),
        'spells_info': spells_data,
        'description': rules.get('description', ''),
    }
