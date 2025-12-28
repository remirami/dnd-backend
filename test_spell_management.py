"""
Test script for Spell Management System

Tests:
1. Spell preparation for prepared casters (Cleric, Druid, Paladin, Wizard)
2. Spell learning for known casters (Bard, Ranger, Sorcerer, Warlock)
3. Spellbook management for Wizards
4. Ritual casting
5. Combat spell validation
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterBackground, CharacterStats, CharacterSpell
from characters.spell_management import (
    is_prepared_caster, is_known_caster, can_cast_rituals,
    calculate_spells_prepared, calculate_spells_known,
    get_wizard_spellbook_size, can_learn_spell, can_add_to_spellbook,
    can_cast_spell
)

# Configure stdout for Unicode
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def print_test(name):
    """Print test header"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def test_spellcasting_types():
    """Test spellcasting type detection"""
    print_test("Spellcasting Type Detection")
    
    # Create test characters
    user, _ = User.objects.get_or_create(username='test_user')
    
    classes_to_test = [
        ('Cleric', True, False),  # (class_name, is_prepared, is_known)
        ('Druid', True, False),
        ('Paladin', True, False),
        ('Wizard', True, False),
        ('Bard', False, True),
        ('Ranger', False, True),
        ('Sorcerer', False, True),
        ('Warlock', False, True),
        ('Fighter', False, False),  # Non-caster
    ]
    
    for class_name, expected_prepared, expected_known in classes_to_test:
        char_class, _ = CharacterClass.objects.get_or_create(name=class_name)
        race, _ = CharacterRace.objects.get_or_create(name='Human')
        
        character = Character.objects.create(
            user=user,
            name=f"Test {class_name}",
            character_class=char_class,
            race=race,
            level=5
        )
        
        # Create stats
        stats, _ = CharacterStats.objects.get_or_create(
            character=character,
            defaults={
                'hit_points': 50,
                'max_hit_points': 50,
                'armor_class': 15,
                'intelligence': 16,
                'wisdom': 16,
                'charisma': 16
            }
        )
        
        is_prep = is_prepared_caster(character)
        is_known = is_known_caster(character)
        can_ritual = can_cast_rituals(character)
        
        print(f"  {class_name:12} | Prepared: {str(is_prep):5} | Known: {str(is_known):5} | Ritual: {str(can_ritual):5}")
        
        assert is_prep == expected_prepared, f"{class_name} prepared caster check failed"
        assert is_known == expected_known, f"{class_name} known caster check failed"
        
        # Cleanup
        character.delete()
    
    print("  ✅ All spellcasting type tests passed!")


def test_spells_prepared():
    """Test spells prepared calculation"""
    print_test("Spells Prepared Calculation")
    
    user, _ = User.objects.get_or_create(username='test_user')
    char_class, _ = CharacterClass.objects.get_or_create(name='Cleric')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    # Test different levels and ability scores
    test_cases = [
        (1, 16, 1 + 3),  # Level 1, WIS 16 (+3) = 4 spells
        (5, 18, 5 + 4),  # Level 5, WIS 18 (+4) = 9 spells
        (10, 20, 10 + 5),  # Level 10, WIS 20 (+5) = 15 spells
    ]
    
    for level, wisdom, expected in test_cases:
        character = Character.objects.create(
            user=user,
            name=f"Test Cleric L{level}",
            character_class=char_class,
            race=race,
            level=level
        )
        
        stats, _ = CharacterStats.objects.get_or_create(
            character=character,
            defaults={
                'hit_points': 50,
                'max_hit_points': 50,
                'armor_class': 15,
                'wisdom': wisdom
            }
        )
        stats.wisdom = wisdom
        stats.save()
        
        spells_prepared = calculate_spells_prepared(character)
        print(f"  Level {level}, WIS {wisdom} (+{(wisdom-10)//2}) → {spells_prepared} spells prepared")
        
        assert spells_prepared == expected, f"Expected {expected}, got {spells_prepared}"
        
        character.delete()
    
    print("  ✅ All spells prepared tests passed!")


def test_spells_known():
    """Test spells known calculation"""
    print_test("Spells Known Calculation")
    
    user, _ = User.objects.get_or_create(username='test_user')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    # Test Bard spells known
    bard_class, _ = CharacterClass.objects.get_or_create(name='Bard')
    
    test_cases = [
        (1, 4),
        (5, 8),
        (10, 14),
        (20, 22),
    ]
    
    for level, expected in test_cases:
        character = Character.objects.create(
            user=user,
            name=f"Test Bard L{level}",
            character_class=bard_class,
            race=race,
            level=level
        )
        
        stats, _ = CharacterStats.objects.get_or_create(
            character=character,
            defaults={
                'hit_points': 50,
                'max_hit_points': 50,
                'armor_class': 15,
                'charisma': 16
            }
        )
        
        spells_known = calculate_spells_known(character)
        print(f"  Bard Level {level} → {spells_known} spells known")
        
        assert spells_known == expected, f"Expected {expected}, got {spells_known}"
        
        character.delete()
    
    print("  ✅ All spells known tests passed!")


def test_wizard_spellbook():
    """Test Wizard spellbook size"""
    print_test("Wizard Spellbook Size")
    
    user, _ = User.objects.get_or_create(username='test_user')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='Wizard')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    test_cases = [
        (1, 6),   # Level 1: 6 spells
        (5, 14),  # Level 5: 6 + (5-1)*2 = 14 spells
        (10, 24), # Level 10: 6 + (10-1)*2 = 24 spells
    ]
    
    for level, expected in test_cases:
        character = Character.objects.create(
            user=user,
            name=f"Test Wizard L{level}",
            character_class=wizard_class,
            race=race,
            level=level
        )
        
        stats, _ = CharacterStats.objects.get_or_create(
            character=character,
            defaults={
                'hit_points': 50,
                'max_hit_points': 50,
                'armor_class': 15,
                'intelligence': 16
            }
        )
        
        spellbook_size = get_wizard_spellbook_size(character)
        print(f"  Wizard Level {level} → Spellbook size: {spellbook_size}")
        
        assert spellbook_size == expected, f"Expected {expected}, got {spellbook_size}"
        
        character.delete()
    
    print("  ✅ All wizard spellbook tests passed!")


def test_prepare_spells():
    """Test spell preparation"""
    print_test("Spell Preparation")
    
    user, _ = User.objects.get_or_create(username='test_user')
    cleric_class, _ = CharacterClass.objects.get_or_create(name='Cleric')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    character = Character.objects.create(
        user=user,
        name="Test Cleric",
        character_class=cleric_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
            'wisdom': 18  # +4 modifier
        }
    )
    
    spells_prepared_limit = calculate_spells_prepared(character)
    print(f"  Cleric Level 5, WIS 18 → Can prepare {spells_prepared_limit} spells")
    
    # Create enough spells to fill the limit
    spells = []
    spell_names = ['Cure Wounds', 'Bless', 'Guiding Bolt', 'Healing Word', 'Shield of Faith', 
                   'Command', 'Detect Magic', 'Purify Food and Drink', 'Thaumaturgy']
    
    for i, spell_name in enumerate(spell_names[:spells_prepared_limit]):
        spell = CharacterSpell.objects.create(
            character=character,
            name=spell_name,
            level=1,
            school='Evocation' if i % 2 == 0 else 'Abjuration',
            description=f"Test spell {spell_name}"
        )
        spells.append(spell)
    
    # Test preparing spells
    spells_to_prepare = spells[:spells_prepared_limit]
    for spell in spells_to_prepare:
        spell.is_prepared = True
        spell.save()
    
    prepared_count = CharacterSpell.objects.filter(character=character, is_prepared=True).count()
    print(f"  Prepared {prepared_count} spells")
    
    assert prepared_count == spells_prepared_limit, f"Expected {spells_prepared_limit}, got {prepared_count}"
    
    # Test can_cast_spell
    can_cast = can_cast_spell(character, 'Cure Wounds')
    print(f"  Can cast 'Cure Wounds': {can_cast}")
    assert can_cast == True
    
    cannot_cast = can_cast_spell(character, 'Fireball')
    print(f"  Can cast 'Fireball': {cannot_cast}")
    assert cannot_cast == False
    
    character.delete()
    print("  ✅ All spell preparation tests passed!")


def test_learn_spells():
    """Test spell learning for known casters"""
    print_test("Spell Learning (Known Casters)")
    
    user, _ = User.objects.get_or_create(username='test_user')
    bard_class, _ = CharacterClass.objects.get_or_create(name='Bard')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    character = Character.objects.create(
        user=user,
        name="Test Bard",
        character_class=bard_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
            'charisma': 16
        }
    )
    
    spells_known_limit = calculate_spells_known(character)
    print(f"  Bard Level 5 → Can know {spells_known_limit} spells")
    
    # Learn spells up to limit
    spell_names = ['Vicious Mockery', 'Healing Word', 'Charm Person', 'Sleep', 'Thunderwave', 'Detect Magic', 'Faerie Fire', 'Tasha\'s Hideous Laughter']
    
    for i, spell_name in enumerate(spell_names[:spells_known_limit]):
        spell = CharacterSpell.objects.create(
            character=character,
            name=spell_name,
            level=1 if i < 4 else 2,
            school='Enchantment' if i % 2 == 0 else 'Evocation',
            description=f"Test spell {spell_name}"
        )
        print(f"  Learned: {spell_name}")
    
    learned_count = CharacterSpell.objects.filter(character=character, level__gt=0).count()
    print(f"  Total spells learned: {learned_count}")
    
    assert learned_count == spells_known_limit, f"Expected {spells_known_limit}, got {learned_count}"
    
    # Test can_cast_spell
    can_cast = can_cast_spell(character, 'Vicious Mockery')
    print(f"  Can cast 'Vicious Mockery': {can_cast}")
    assert can_cast == True
    
    character.delete()
    print("  ✅ All spell learning tests passed!")


def test_wizard_spellbook_management():
    """Test Wizard spellbook management"""
    print_test("Wizard Spellbook Management")
    
    user, _ = User.objects.get_or_create(username='test_user')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='Wizard')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    character = Character.objects.create(
        user=user,
        name="Test Wizard",
        character_class=wizard_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
            'intelligence': 16
        }
    )
    
    spellbook_size = get_wizard_spellbook_size(character)
    print(f"  Wizard Level 5 → Spellbook size: {spellbook_size}")
    
    # Add spells to spellbook (create enough to fill spellbook)
    spell_names = ['Magic Missile', 'Shield', 'Mage Armor', 'Detect Magic', 'Identify', 'Burning Hands', 
                   'Charm Person', 'Sleep', 'Mage Hand', 'Prestidigitation', 'Ray of Frost', 'Fire Bolt',
                   'Comprehend Languages', 'Find Familiar']
    
    for i, spell_name in enumerate(spell_names[:spellbook_size]):
        spell = CharacterSpell.objects.create(
            character=character,
            name=spell_name,
            level=1,
            school='Evocation' if i % 2 == 0 else 'Abjuration',
            description=f"Test spell {spell_name}",
            in_spellbook=True
        )
        print(f"  Added to spellbook: {spell_name}")
    
    spellbook_count = CharacterSpell.objects.filter(character=character, in_spellbook=True).count()
    print(f"  Total spells in spellbook: {spellbook_count}")
    
    assert spellbook_count == spellbook_size, f"Expected {spellbook_size}, got {spellbook_count}"
    
    # Test preparing spells from spellbook
    spells_to_prepare = CharacterSpell.objects.filter(character=character, in_spellbook=True)[:calculate_spells_prepared(character)]
    for spell in spells_to_prepare:
        spell.is_prepared = True
        spell.save()
    
    prepared_count = CharacterSpell.objects.filter(character=character, is_prepared=True).count()
    print(f"  Prepared {prepared_count} spells from spellbook")
    
    # Test can_cast_spell
    can_cast = can_cast_spell(character, 'Magic Missile')
    print(f"  Can cast 'Magic Missile': {can_cast}")
    assert can_cast == True
    
    character.delete()
    print("  ✅ All wizard spellbook tests passed!")


def test_ritual_casting():
    """Test ritual casting"""
    print_test("Ritual Casting")
    
    user, _ = User.objects.get_or_create(username='test_user')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='Wizard')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    character = Character.objects.create(
        user=user,
        name="Test Wizard",
        character_class=wizard_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
            'intelligence': 16
        }
    )
    
    # Add ritual spell to spellbook but don't prepare it
    ritual_spell = CharacterSpell.objects.create(
        character=character,
        name='Detect Magic',
        level=1,
        school='Divination',
        description='Ritual spell',
        is_ritual=True,
        in_spellbook=True,
        is_prepared=False  # Not prepared
    )
    
    print(f"  Created ritual spell 'Detect Magic' (not prepared)")
    
    # Test ritual casting
    can_cast_ritual = can_cast_spell(character, 'Detect Magic', allow_ritual=True)
    print(f"  Can cast 'Detect Magic' as ritual: {can_cast_ritual}")
    assert can_cast_ritual == True
    
    # Test non-ritual casting (should fail)
    cannot_cast_normal = can_cast_spell(character, 'Detect Magic', allow_ritual=False)
    print(f"  Can cast 'Detect Magic' normally (not ritual): {cannot_cast_normal}")
    assert cannot_cast_normal == False
    
    # Test non-ritual caster
    fighter_class, _ = CharacterClass.objects.get_or_create(name='Fighter')
    fighter = Character.objects.create(
        user=user,
        name="Test Fighter",
        character_class=fighter_class,
        race=race,
        level=5
    )
    
    can_ritual = can_cast_rituals(fighter)
    print(f"  Fighter can cast rituals: {can_ritual}")
    assert can_ritual == False
    
    character.delete()
    fighter.delete()
    print("  ✅ All ritual casting tests passed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SPELL MANAGEMENT SYSTEM TESTS")
    print("="*60)
    
    try:
        test_spellcasting_types()
        test_spells_prepared()
        test_spells_known()
        test_wizard_spellbook()
        test_prepare_spells()
        test_learn_spells()
        test_wizard_spellbook_management()
        test_ritual_casting()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

