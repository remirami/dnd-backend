"""
Test script for Multiclassing System

Tests:
1. Multiclass prerequisites checking
2. Adding new class levels
3. Spell slot calculation for multiclass casters
4. Hit dice calculation
5. Feature application
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterClassLevel
from characters.multiclassing import (
    can_multiclass_into, calculate_multiclass_spell_slots, get_multiclass_spellcasting_ability,
    get_multiclass_hit_dice, get_total_level, get_class_level
)

# Configure stdout for Unicode
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def print_test(name):
    """Print test header"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def test_multiclass_prerequisites():
    """Test multiclass prerequisites checking"""
    print_test("Multiclass Prerequisites")
    
    user, _ = User.objects.get_or_create(username='test_user')
    fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard')
    paladin_class, _ = CharacterClass.objects.get_or_create(name='paladin')
    race, _ = CharacterRace.objects.get_or_create(name='human')
    
    # Create character with low stats
    character = Character.objects.create(
        user=user,
        name="Low Stats Fighter",
        character_class=fighter_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'strength': 16,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 10,  # Too low for Wizard
            'wisdom': 10,
            'charisma': 10,
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 16,
        }
    )
    
    # Test: Cannot multiclass into Wizard (needs INT 13)
    can_multiclass, reason = can_multiclass_into(character, 'Wizard')
    print(f"  Wizard multiclass (INT 10): {can_multiclass} - {reason}")
    assert not can_multiclass, "Should not be able to multiclass into Wizard with INT 10"
    
    # Test: Can multiclass into Paladin (needs STR 13 and CHA 13)
    can_multiclass, reason = can_multiclass_into(character, 'Paladin')
    print(f"  Paladin multiclass (STR 16, CHA 10): {can_multiclass} - {reason}")
    assert not can_multiclass, "Should not be able to multiclass into Paladin with CHA 10"
    
    # Update stats to meet requirements
    stats.intelligence = 13
    stats.charisma = 13
    stats.save()
    
    # Test: Now can multiclass into Wizard
    can_multiclass, reason = can_multiclass_into(character, 'Wizard')
    print(f"  Wizard multiclass (INT 13): {can_multiclass} - {reason}")
    assert can_multiclass, "Should be able to multiclass into Wizard with INT 13"
    
    # Test: Now can multiclass into Paladin
    can_multiclass, reason = can_multiclass_into(character, 'Paladin')
    print(f"  Paladin multiclass (STR 16, CHA 13): {can_multiclass} - {reason}")
    assert can_multiclass, "Should be able to multiclass into Paladin with STR 16 and CHA 13"
    
    character.delete()
    print("  ✅ All prerequisite tests passed!")


def test_multiclass_levels():
    """Test adding class levels"""
    print_test("Multiclass Level Tracking")
    
    user, _ = User.objects.get_or_create(username='test_user')
    fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard')
    race, _ = CharacterRace.objects.get_or_create(name='human')
    
    character = Character.objects.create(
        user=user,
        name="Fighter/Wizard",
        character_class=fighter_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'strength': 16,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 14,
            'wisdom': 10,
            'charisma': 10,
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 16,
        }
    )
    
    # Create Fighter level 5
    fighter_level = CharacterClassLevel.objects.create(
        character=character,
        character_class=fighter_class,
        level=5
    )
    print(f"  Created Fighter Level {fighter_level.level}")
    
    # Add Wizard level
    wizard_level = CharacterClassLevel.objects.create(
        character=character,
        character_class=wizard_class,
        level=1
    )
    print(f"  Created Wizard Level {wizard_level.level}")
    
    # Test total level
    total_level = get_total_level(character)
    print(f"  Total level: {total_level}")
    assert total_level == 6, f"Expected total level 6, got {total_level}"
    
    # Test class levels
    fighter_lvl = get_class_level(character, 'Fighter')
    wizard_lvl = get_class_level(character, 'Wizard')
    print(f"  Fighter level: {fighter_lvl}, Wizard level: {wizard_lvl}")
    assert fighter_lvl == 5, f"Expected Fighter level 5, got {fighter_lvl}"
    assert wizard_lvl == 1, f"Expected Wizard level 1, got {wizard_lvl}"
    
    # Level up Wizard
    wizard_level.level += 1
    wizard_level.save()
    total_level = get_total_level(character)
    print(f"  After Wizard level-up: Total level {total_level}")
    assert total_level == 7, f"Expected total level 7, got {total_level}"
    
    character.delete()
    print("  ✅ All level tracking tests passed!")


def test_multiclass_spell_slots():
    """Test multiclass spell slot calculation"""
    print_test("Multiclass Spell Slots")
    
    user, _ = User.objects.get_or_create(username='test_user')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard')
    cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric')
    paladin_class, _ = CharacterClass.objects.get_or_create(name='paladin')
    race, _ = CharacterRace.objects.get_or_create(name='human')
    
    # Test 1: Wizard 5 / Cleric 3 (Full + Full = 8 caster levels)
    character = Character.objects.create(
        user=user,
        name="Wizard/Cleric",
        character_class=wizard_class,
        race=race,
        level=8
    )
    
    wizard_level = CharacterClassLevel.objects.create(
        character=character,
        character_class=wizard_class,
        level=5
    )
    cleric_level = CharacterClassLevel.objects.create(
        character=character,
        character_class=cleric_class,
        level=3
    )
    
    # Debug: Check class names
    print(f"  Wizard class name: {wizard_class.name}, Cleric class name: {cleric_class.name}")
    print(f"  Wizard level: {wizard_level.level}, Cleric level: {cleric_level.level}")
    
    spell_slots = calculate_multiclass_spell_slots(character)
    print(f"  Wizard 5 / Cleric 3 (8 caster levels): {spell_slots}")
    print(f"  Caster level calculation debug:")
    class_levels = CharacterClassLevel.objects.filter(character=character)
    for cl in class_levels:
        print(f"    {cl.character_class.name}: {cl.level}")
    
    assert spell_slots.get(4, 0) >= 1, f"Should have 4th level slots at caster level 8, got {spell_slots}"
    
    character.delete()
    
    # Test 2: Paladin 5 / Wizard 3 (Half + Full = 5.5 → 5 caster levels)
    character = Character.objects.create(
        user=user,
        name="Paladin/Wizard",
        character_class=paladin_class,
        race=race,
        level=8
    )
    
    CharacterClassLevel.objects.create(
        character=character,
        character_class=paladin_class,
        level=5
    )
    CharacterClassLevel.objects.create(
        character=character,
        character_class=wizard_class,
        level=3
    )
    
    spell_slots = calculate_multiclass_spell_slots(character)
    print(f"  Paladin 5 / Wizard 3 (5 caster levels): {spell_slots}")
    assert spell_slots.get(3, 0) >= 1, "Should have 3rd level slots at caster level 5"
    
    character.delete()
    print("  ✅ All spell slot tests passed!")


def test_multiclass_hit_dice():
    """Test multiclass hit dice calculation"""
    print_test("Multiclass Hit Dice")
    
    user, _ = User.objects.get_or_create(username='test_user')
    fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter', defaults={'hit_dice': 'd10'})
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard', defaults={'hit_dice': 'd6'})
    race, _ = CharacterRace.objects.get_or_create(name='human')
    
    character = Character.objects.create(
        user=user,
        name="Fighter/Wizard",
        character_class=fighter_class,
        race=race,
        level=8
    )
    
    CharacterClassLevel.objects.create(
        character=character,
        character_class=fighter_class,
        level=5
    )
    CharacterClassLevel.objects.create(
        character=character,
        character_class=wizard_class,
        level=3
    )
    
    hit_dice = get_multiclass_hit_dice(character)
    print(f"  Fighter 5 / Wizard 3 hit dice: {hit_dice}")
    assert hit_dice.get('d10', 0) == 5, f"Expected 5d10, got {hit_dice.get('d10', 0)}d10"
    assert hit_dice.get('d6', 0) == 3, f"Expected 3d6, got {hit_dice.get('d6', 0)}d6"
    
    character.delete()
    print("  ✅ All hit dice tests passed!")


def test_spellcasting_ability():
    """Test multiclass spellcasting ability"""
    print_test("Multiclass Spellcasting Ability")
    
    user, _ = User.objects.get_or_create(username='test_user')
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard')
    cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric')
    race, _ = CharacterRace.objects.get_or_create(name='human')
    
    character = Character.objects.create(
        user=user,
        name="Wizard/Cleric",
        character_class=wizard_class,
        race=race,
        level=6
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'strength': 10,
            'dexterity': 10,
            'constitution': 14,
            'intelligence': 16,  # Higher INT
            'wisdom': 14,  # Lower WIS
            'charisma': 10,
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
        }
    )
    
    CharacterClassLevel.objects.create(
        character=character,
        character_class=wizard_class,
        level=3
    )
    CharacterClassLevel.objects.create(
        character=character,
        character_class=cleric_class,
        level=3
    )
    
    spellcasting_ability = get_multiclass_spellcasting_ability(character)
    print(f"  Spellcasting ability: {spellcasting_ability}")
    # Should use INT (16) over WIS (14)
    assert spellcasting_ability == 'intelligence', f"Expected intelligence, got {spellcasting_ability}"
    
    character.delete()
    print("  ✅ All spellcasting ability tests passed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MULTICLASSING SYSTEM TESTS")
    print("="*60)
    
    try:
        test_multiclass_prerequisites()
        test_multiclass_levels()
        test_multiclass_spell_slots()
        test_multiclass_hit_dice()
        test_spellcasting_ability()
        
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

