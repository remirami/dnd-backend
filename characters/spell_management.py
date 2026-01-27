"""
Spell Management Utilities for D&D 5e Characters

Handles spell preparation, learning, and spellbook management.
"""

from .models import Character, CharacterSpell


# Spellcasting types
PREPARED_CASTERS = ['cleric', 'druid', 'paladin', 'wizard']
KNOWN_CASTERS = ['bard', 'ranger', 'sorcerer', 'warlock']
RITUAL_CASTERS = ['cleric', 'druid', 'wizard']  # Can cast ritual spells without preparing


def _normalize_class_name(character):
    """Normalize character class name to lowercase for case-insensitive comparison."""
    if not character or not character.character_class:
        return ''
    return character.character_class.name.lower()


def is_prepared_caster(character):
    """Check if character is a prepared caster (case-insensitive)"""
    return _normalize_class_name(character) in PREPARED_CASTERS


def is_known_caster(character):
    """Check if character is a known caster (case-insensitive)"""
    class_name = _normalize_class_name(character)
    if class_name in KNOWN_CASTERS:
        return True
    
    # Check subclasses
    subclass = (character.subclass or '').lower()
    if class_name == 'rogue' and 'arcane trickster' in subclass:
        return True
    if class_name == 'fighter' and 'eldritch knight' in subclass:
        return True
        
    return False


def can_cast_rituals(character):
    """Check if character can cast ritual spells (case-insensitive)"""
    return _normalize_class_name(character) in RITUAL_CASTERS


def get_spellcasting_ability(character):
    """Get the spellcasting ability modifier for a character"""
    if not character.stats:
        return 0
    
    class_name = _normalize_class_name(character)
    subclass = (character.subclass or '').lower()
    
    if class_name == 'wizard' or \
       (class_name == 'fighter' and 'eldritch knight' in subclass) or \
       (class_name == 'rogue' and 'arcane trickster' in subclass):
        return character.stats.intelligence_modifier
    elif class_name in ['cleric', 'druid', 'ranger']:
        return character.stats.wisdom_modifier
    elif class_name in ['bard', 'paladin', 'sorcerer', 'warlock']:
        return character.stats.charisma_modifier
    
    return 0


def calculate_spells_prepared(character):
    """
    Calculate how many spells a prepared caster can prepare.
    
    Formula: Level + Spellcasting Ability Modifier
    Paladin: Floor(Level / 2) + Charisma Modifier
    Minimum: 1 spell
    """
    if not is_prepared_caster(character):
        return 0
    
    class_name = _normalize_class_name(character)
    spellcasting_mod = get_spellcasting_ability(character)
    
    if class_name == 'paladin':
        if character.level < 2:
            return 0
        spells_prepared = (character.level // 2) + spellcasting_mod
    else:
        spells_prepared = character.level + spellcasting_mod
    
    return max(1, spells_prepared)


def calculate_spells_known(character):
    """
    Calculate how many spells a known caster knows.
    
    Returns a dict mapping level to number of spells known.
    """
    if not is_known_caster(character):
        return 0
    
    class_name = _normalize_class_name(character)
    subclass = (character.subclass or '').lower()
    level = character.level
    
    # Check subclasses logic first if needed, otherwise utilize class map
    if class_name == 'rogue' and 'arcane trickster' in subclass:
        # Arcane Trickster Spells Known
        # Lvl 3: 3, 4: 4, ...
        at_known = {
            1: 0, 2: 0, 3: 3, 4: 4, 5: 4, 6: 4, 7: 5, 8: 6, 9: 6,
            10: 7, 11: 8, 12: 8, 13: 9, 14: 10, 15: 10, 16: 11,
            17: 11, 18: 11, 19: 12, 20: 13
        }
        return at_known.get(level, 0)

    if class_name == 'fighter' and 'eldritch knight' in subclass:
        # Eldritch Knight Spells Known
        ek_known = {
            1: 0, 2: 0, 3: 3, 4: 4, 5: 4, 6: 4, 7: 5, 8: 6, 9: 6,
            10: 7, 11: 8, 12: 8, 13: 9, 14: 10, 15: 10, 16: 11,
            17: 11, 18: 11, 19: 12, 20: 13
        }
        # Note: Same as AT
        return ek_known.get(level, 0)
    
    # Spells known by class and level
    spells_known = {
        'bard': {
            1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12,
            10: 14, 11: 15, 12: 15, 13: 16, 14: 18, 15: 19, 16: 19,
            17: 20, 18: 22, 19: 22, 20: 22
        },
        'ranger': {
            1: 0, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 5, 8: 5, 9: 6,
            10: 6, 11: 7, 12: 7, 13: 8, 14: 8, 15: 9, 16: 9,
            17: 10, 18: 10, 19: 11, 20: 11
        },
        'sorcerer': {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10,
            10: 11, 11: 12, 12: 12, 13: 13, 14: 13, 15: 14, 16: 14,
            17: 15, 18: 15, 19: 15, 20: 15
        },
        'warlock': {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10,
            10: 10, 11: 11, 12: 11, 13: 12, 14: 12, 15: 13, 16: 13,
            17: 14, 18: 14, 19: 15, 20: 15
        }
    }
    
    return spells_known.get(class_name, {}).get(level, 0)


def calculate_cantrips_known(character):
    """
    Calculate how many cantrips a character knows.
    """
    if not character.character_class:
        return 0
        
    class_name = _normalize_class_name(character)
    subclass = (character.subclass or '').lower()
    level = character.level
    
    # Subclasses
    if class_name == 'rogue' and 'arcane trickster' in subclass:
        # Mage Hand + 2 others at lvl 3. Increases at 10.
        # Impl: 3 at 3. 4 at 10.
        at_cantrips = {
             1: 0, 2: 0, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3,
             10: 4, 11: 4, 12: 4, 13: 4, 14: 4, 15: 4, 16: 4, 
             17: 4, 18: 4, 19: 4, 20: 4
        }
        return at_cantrips.get(level, 0)

    if class_name == 'fighter' and 'eldritch knight' in subclass:
        # 2 at 3. Increases at 10 to 3.
        ek_cantrips = {
             1: 0, 2: 0, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 2,
             10: 3, 11: 3, 12: 3, 13: 3, 14: 3, 15: 3, 16: 3, 
             17: 3, 18: 3, 19: 3, 20: 3
        }
        return ek_cantrips.get(level, 0)

    # Cantrips known by class and level
    # Based on SRD
    cantrips_known = {
        'bard': {
            1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3,
            10: 4, 11: 4, 12: 4, 13: 4, 14: 4, 15: 4, 16: 4,
            17: 4, 18: 4, 19: 4, 20: 4
        },
        'cleric': {
            1: 3, 2: 3, 3: 3, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4,
            10: 5, 11: 5, 12: 5, 13: 5, 14: 5, 15: 5, 16: 5,
            17: 5, 18: 5, 19: 5, 20: 5
        },
        'druid': {
            1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3,
            10: 4, 11: 4, 12: 4, 13: 4, 14: 4, 15: 4, 16: 4,
            17: 4, 18: 4, 19: 4, 20: 4
        },
        'sorcerer': {
            1: 4, 2: 4, 3: 4, 4: 5, 5: 5, 6: 5, 7: 5, 8: 5, 9: 5,
            10: 6, 11: 6, 12: 6, 13: 6, 14: 6, 15: 6, 16: 6,
            17: 6, 18: 6, 19: 6, 20: 6
        },
        'warlock': {
            1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3,
            10: 4, 11: 4, 12: 4, 13: 4, 14: 4, 15: 4, 16: 4,
            17: 4, 18: 4, 19: 4, 20: 4
        },
        'wizard': {
            1: 3, 2: 3, 3: 3, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4,
            10: 5, 11: 5, 12: 5, 13: 5, 14: 5, 15: 5, 16: 5,
            17: 5, 18: 5, 19: 5, 20: 5
        },
        # Artificer (Tasha's) starts with 2, increases at 10 to 3, 14 to 4?
        # Keeping it simple with SRD classes for now.
    }
    
    return cantrips_known.get(class_name, {}).get(level, 0)


def get_wizard_spellbook_size(character):
    """
    Calculate Wizard spellbook size.
    Wizards start with 6 spells at level 1, and gain 2 per level.
    """
    if _normalize_class_name(character) != 'wizard':
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
    if _normalize_class_name(character) != 'wizard':
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
    if _normalize_class_name(character) != 'wizard':
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

