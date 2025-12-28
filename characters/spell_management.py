"""
Spell Management Utilities for D&D 5e Characters

Handles spell preparation, learning, and spellbook management.
"""

from .models import Character, CharacterSpell


# Spellcasting types
PREPARED_CASTERS = ['Cleric', 'Druid', 'Paladin', 'Wizard']
KNOWN_CASTERS = ['Bard', 'Ranger', 'Sorcerer', 'Warlock']
RITUAL_CASTERS = ['Cleric', 'Druid', 'Wizard']  # Can cast ritual spells without preparing


def is_prepared_caster(character):
    """Check if character is a prepared caster"""
    return character.character_class.name in PREPARED_CASTERS


def is_known_caster(character):
    """Check if character is a known caster"""
    return character.character_class.name in KNOWN_CASTERS


def can_cast_rituals(character):
    """Check if character can cast ritual spells"""
    return character.character_class.name in RITUAL_CASTERS


def get_spellcasting_ability(character):
    """Get the spellcasting ability modifier for a character"""
    if not character.stats:
        return 0
    
    class_name = character.character_class.name
    
    if class_name in ['Wizard', 'Eldritch Knight', 'Arcane Trickster']:
        return character.stats.intelligence_modifier
    elif class_name in ['Cleric', 'Druid', 'Ranger']:
        return character.stats.wisdom_modifier
    elif class_name in ['Bard', 'Paladin', 'Sorcerer', 'Warlock']:
        return character.stats.charisma_modifier
    
    return 0


def calculate_spells_prepared(character):
    """
    Calculate how many spells a prepared caster can prepare.
    
    Formula: Level + Spellcasting Ability Modifier
    Minimum: 1 spell
    """
    if not is_prepared_caster(character):
        return 0
    
    spellcasting_mod = get_spellcasting_ability(character)
    spells_prepared = character.level + spellcasting_mod
    
    return max(1, spells_prepared)


def calculate_spells_known(character):
    """
    Calculate how many spells a known caster knows.
    
    Returns a dict mapping level to number of spells known.
    """
    if not is_known_caster(character):
        return {}
    
    class_name = character.character_class.name
    level = character.level
    
    # Spells known by class and level
    spells_known = {
        'Bard': {
            1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12,
            10: 14, 11: 15, 12: 15, 13: 16, 14: 18, 15: 19, 16: 19,
            17: 20, 18: 22, 19: 22, 20: 22
        },
        'Ranger': {
            1: 0, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 5, 8: 5, 9: 6,
            10: 6, 11: 7, 12: 7, 13: 8, 14: 8, 15: 9, 16: 9,
            17: 10, 18: 10, 19: 11, 20: 11
        },
        'Sorcerer': {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10,
            10: 11, 11: 12, 12: 12, 13: 13, 14: 13, 15: 14, 16: 14,
            17: 15, 18: 15, 19: 15, 20: 15
        },
        'Warlock': {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10,
            10: 10, 11: 11, 12: 11, 13: 12, 14: 12, 15: 13, 16: 13,
            17: 14, 18: 14, 19: 15, 20: 15
        }
    }
    
    return spells_known.get(class_name, {}).get(level, 0)


def get_wizard_spellbook_size(character):
    """
    Calculate Wizard spellbook size.
    Wizards start with 6 spells at level 1, and gain 2 per level.
    """
    if character.character_class.name != 'Wizard':
        return 0
    
    # Level 1: 6 spells, then +2 per level
    return 6 + (character.level - 1) * 2


def can_prepare_spell(character, spell):
    """
    Check if a character can prepare a spell.
    For prepared casters, checks if spell is in their available spells.
    """
    if not is_prepared_caster(character):
        return False
    
    # For now, assume all spells are available if they're in the character's spell list
    # In a full implementation, you'd check against class spell lists
    return True


def can_learn_spell(character, spell_level):
    """
    Check if a known caster can learn a spell of the given level.
    """
    if not is_known_caster(character):
        return False
    
    spells_known_limit = calculate_spells_known(character)
    current_spells_known = CharacterSpell.objects.filter(
        character=character,
        level__gt=0  # Exclude cantrips
    ).count()
    
    return current_spells_known < spells_known_limit


def can_add_to_spellbook(character, spell_level):
    """
    Check if a Wizard can add a spell to their spellbook.
    """
    if character.character_class.name != 'Wizard':
        return False
    
    spellbook_size = get_wizard_spellbook_size(character)
    current_spellbook_size = CharacterSpell.objects.filter(
        character=character,
        in_spellbook=True
    ).count()
    
    return current_spellbook_size < spellbook_size


def get_prepared_spells(character):
    """Get all prepared spells for a character"""
    return CharacterSpell.objects.filter(
        character=character,
        is_prepared=True
    )


def get_known_spells(character):
    """Get all known spells for a known caster"""
    if not is_known_caster(character):
        return CharacterSpell.objects.none()
    
    return CharacterSpell.objects.filter(
        character=character,
        level__gt=0  # Exclude cantrips from known count
    )


def get_spellbook_spells(character):
    """Get all spells in a Wizard's spellbook"""
    if character.character_class.name != 'Wizard':
        return CharacterSpell.objects.none()
    
    return CharacterSpell.objects.filter(
        character=character,
        in_spellbook=True
    )


def can_cast_spell(character, spell_name, allow_ritual=True):
    """
    Check if a character can cast a spell.
    
    For prepared casters: spell must be prepared (or ritual if allow_ritual=True)
    For known casters: spell must be known
    """
    try:
        spell = CharacterSpell.objects.get(character=character, name=spell_name)
    except CharacterSpell.DoesNotExist:
        return False
    
    if is_prepared_caster(character):
        # Prepared casters can cast if spell is prepared
        if spell.is_prepared:
            return True
        
        # Or if it's a ritual and they can cast rituals
        if allow_ritual and spell.is_ritual and can_cast_rituals(character):
            return True
        
        return False
    
    elif is_known_caster(character):
        # Known casters can cast if they know the spell
        return True
    
    return False

