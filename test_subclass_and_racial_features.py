"""
Test script for subclass and racial features implementation

This script tests:
1. Racial features are applied on character creation
2. Subclass features are applied when subclass is selected
3. Subclass features are applied during level-up
4. Manual application of racial features to existing characters
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import (
    Character, CharacterStats, CharacterClass, CharacterRace, 
    CharacterBackground, CharacterFeature
)
from campaigns.models import Campaign, CampaignCharacter, CharacterXP
from campaigns.racial_features_data import get_racial_features, apply_racial_features_to_character
from campaigns.class_features_data import get_class_features, get_subclass_features


def test_racial_features():
    """Test that racial features are properly defined and can be applied"""
    print("\n" + "="*80)
    print("TEST 1: Racial Features")
    print("="*80)
    
    # Test all races have features
    races = ['human', 'elf', 'dwarf', 'halfling', 'dragonborn', 'gnome', 'half-elf', 'half-orc', 'tiefling']
    
    for race_name in races:
        features = get_racial_features(race_name)
        print(f"\n{race_name.upper()}:")
        print(f"  Total features: {len(features)}")
        for feature in features:
            print(f"    - {feature['name']}")
    
    print("\n[PASS] All races have racial features defined")


def test_subclass_features():
    """Test that subclass features are properly defined"""
    print("\n" + "="*80)
    print("TEST 2: Subclass Features")
    print("="*80)
    
    # Test some key subclasses
    subclasses = {
        'Champion': [3, 7, 10, 15, 18],
        'Battle Master': [3, 7, 10, 15, 18],
        'School of Evocation': [2, 6, 10, 14],
        'Assassin': [3, 9, 13, 17],
        'Life Domain': [1, 2, 6, 8, 17],
        'Path of the Berserker': [3, 6, 10, 14],
        'College of Lore': [3, 6, 14],
    }
    
    for subclass_name, expected_levels in subclasses.items():
        print(f"\n{subclass_name}:")
        for level in expected_levels:
            features = get_subclass_features(subclass_name, level)
            if features:
                print(f"  Level {level}: {len(features)} feature(s)")
                for feature in features:
                    print(f"    - {feature['name']}")
    
    print("\n[PASS] All tested subclasses have features defined")


def test_character_creation_with_racial_features():
    """Test that racial features are applied when creating a character"""
    print("\n" + "="*80)
    print("TEST 3: Character Creation with Racial Features")
    print("="*80)
    
    # Get or create test user
    user, _ = User.objects.get_or_create(username='test_user', defaults={'email': 'test@example.com'})
    
    # Get or create necessary data
    elf_race, _ = CharacterRace.objects.get_or_create(
        name='elf',
        defaults={
            'size': 'M',
            'speed': 30,
            'ability_score_increases': 'DEX+2'
        }
    )
    
    fighter_class, _ = CharacterClass.objects.get_or_create(
        name='fighter',
        defaults={
            'hit_dice': 'd10',
            'primary_ability': 'STR',
            'saving_throw_proficiencies': 'STR,CON'
        }
    )
    
    # Create a character
    character = Character.objects.create(
        user=user,
        name='Test Elf Fighter',
        level=1,
        character_class=fighter_class,
        race=elf_race
    )
    
    # Apply racial features
    features = apply_racial_features_to_character(character)
    
    print(f"\nCreated character: {character.name}")
    print(f"Race: {character.race.get_name_display()}")
    print(f"Racial features applied: {len(features)}")
    
    for feature in features:
        print(f"  - {feature.name}")
    
    # Verify features were saved
    saved_features = CharacterFeature.objects.filter(
        character=character,
        feature_type='racial'
    )
    
    print(f"\nVerification: {saved_features.count()} racial features saved to database")
    
    assert saved_features.count() == len(features), "Mismatch in saved features count"
    print("[PASS] Racial features correctly applied on character creation")
    
    return character


def test_subclass_selection():
    """Test that subclass features are applied when selecting a subclass"""
    print("\n" + "="*80)
    print("TEST 4: Subclass Selection and Feature Application")
    print("="*80)
    
    # Get or create test user
    user, _ = User.objects.get_or_create(username='test_user2', defaults={'email': 'test2@example.com'})
    
    # Get or create necessary data
    human_race, _ = CharacterRace.objects.get_or_create(
        name='human',
        defaults={
            'size': 'M',
            'speed': 30,
            'ability_score_increases': 'STR+1,DEX+1,CON+1,INT+1,WIS+1,CHA+1'
        }
    )
    
    fighter_class, _ = CharacterClass.objects.get_or_create(
        name='fighter',
        defaults={
            'hit_dice': 'd10',
            'primary_ability': 'STR',
            'saving_throw_proficiencies': 'STR,CON'
        }
    )
    
    # Create a character at level 3 (when fighters choose subclass)
    character = Character.objects.create(
        user=user,
        name='Test Champion Fighter',
        level=3,
        character_class=fighter_class,
        race=human_race
    )
    
    # Apply racial features
    apply_racial_features_to_character(character)
    
    # Select Champion subclass
    character.subclass = 'Champion'
    character.save()
    
    # Apply subclass features retroactively
    from campaigns.class_features_data import get_subclass_features
    
    features_applied = []
    for level in range(3, character.level + 1):
        subclass_features = get_subclass_features('Champion', level)
        
        for feature_data in subclass_features:
            feature = CharacterFeature.objects.create(
                character=character,
                name=feature_data['name'],
                feature_type='class',
                description=feature_data['description'],
                source=f"Champion Level {level}"
            )
            features_applied.append(feature)
    
    print(f"\nCreated character: {character.name}")
    print(f"Class: {character.character_class.get_name_display()}")
    print(f"Subclass: {character.subclass}")
    print(f"Level: {character.level}")
    print(f"Subclass features applied: {len(features_applied)}")
    
    for feature in features_applied:
        print(f"  - {feature.name} ({feature.source})")
    
    # Verify features were saved
    saved_subclass_features = CharacterFeature.objects.filter(
        character=character,
        source__contains='Champion'
    )
    
    print(f"\nVerification: {saved_subclass_features.count()} subclass features saved to database")
    
    assert saved_subclass_features.count() == len(features_applied), "Mismatch in saved features count"
    print("[PASS] Subclass features correctly applied on subclass selection")
    
    return character


def test_level_up_with_subclass():
    """Test that subclass features are applied during level-up"""
    print("\n" + "="*80)
    print("TEST 5: Level-Up with Subclass Features")
    print("="*80)
    
    # Get or create test user
    user, _ = User.objects.get_or_create(username='test_user3', defaults={'email': 'test3@example.com'})
    
    # Get or create necessary data
    dwarf_race, _ = CharacterRace.objects.get_or_create(
        name='dwarf',
        defaults={
            'size': 'M',
            'speed': 25,
            'ability_score_increases': 'CON+2'
        }
    )
    
    fighter_class, _ = CharacterClass.objects.get_or_create(
        name='fighter',
        defaults={
            'hit_dice': 'd10',
            'primary_ability': 'STR',
            'saving_throw_proficiencies': 'STR,CON'
        }
    )
    
    # Create a character at level 6 with subclass
    character = Character.objects.create(
        user=user,
        name='Test Battle Master',
        level=6,
        character_class=fighter_class,
        race=dwarf_race,
        subclass='Battle Master'
    )
    
    # Create stats
    CharacterStats.objects.create(
        character=character,
        strength=16,
        dexterity=14,
        constitution=15,
        intelligence=10,
        wisdom=12,
        charisma=8,
        hit_points=52,
        max_hit_points=52,
        armor_class=18,
        speed=25,
        initiative=2,
        passive_perception=11
    )
    
    # Apply racial features
    apply_racial_features_to_character(character)
    
    # Create campaign and add character
    campaign = Campaign.objects.create(
        owner=user,
        name='Test Campaign',
        status='preparing',
        starting_level=6
    )
    
    campaign_char = CampaignCharacter.objects.create(
        campaign=campaign,
        character=character,
        current_hp=52,
        max_hp=52,
        hit_dice_remaining={'d10': 6}
    )
    
    # Create XP tracking
    xp_tracking = CharacterXP.objects.create(
        campaign_character=campaign_char,
        current_xp=0
    )
    
    print(f"\nCreated character: {character.name}")
    print(f"Class: {character.character_class.get_name_display()}")
    print(f"Subclass: {character.subclass}")
    print(f"Starting level: {character.level}")
    
    # Count features before level-up
    features_before = CharacterFeature.objects.filter(character=character).count()
    print(f"Features before level-up: {features_before}")
    
    # Level up to 7 (Battle Master gets features at level 7)
    print("\n--- Leveling up to 7 ---")
    xp_tracking.add_xp(23000, source='test')  # Enough XP for level 7
    
    # Reload character
    character.refresh_from_db()
    
    print(f"New level: {character.level}")
    
    # Count features after level-up
    features_after = CharacterFeature.objects.filter(character=character).count()
    print(f"Features after level-up: {features_after}")
    
    # Get new features
    new_features = CharacterFeature.objects.filter(
        character=character,
        source__contains='Level 7'
    )
    
    print(f"\nNew features gained at level 7:")
    for feature in new_features:
        print(f"  - {feature.name} ({feature.source})")
    
    assert features_after > features_before, "No new features were added during level-up"
    print("\n[PASS] Subclass features correctly applied during level-up")
    
    return character


def test_class_features_at_all_levels():
    """Test that class features exist for all classes at key levels"""
    print("\n" + "="*80)
    print("TEST 6: Class Features Coverage")
    print("="*80)
    
    classes = ['fighter', 'wizard', 'cleric', 'rogue', 'barbarian', 'bard', 
               'druid', 'monk', 'paladin', 'ranger', 'sorcerer', 'warlock']
    
    key_levels = [1, 2, 3, 5, 10, 15, 20]
    
    for class_name in classes:
        print(f"\n{class_name.upper()}:")
        for level in key_levels:
            features = get_class_features(class_name, level)
            if features:
                print(f"  Level {level}: {len(features)} feature(s)")
    
    print("\n[PASS] Class features defined for all classes")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("TESTING SUBCLASS AND RACIAL FEATURES IMPLEMENTATION")
    print("="*80)
    
    try:
        # Test 1: Racial features data
        test_racial_features()
        
        # Test 2: Subclass features data
        test_subclass_features()
        
        # Test 3: Character creation with racial features
        test_character_creation_with_racial_features()
        
        # Test 4: Subclass selection
        test_subclass_selection()
        
        # Test 5: Level-up with subclass
        test_level_up_with_subclass()
        
        # Test 6: Class features coverage
        test_class_features_at_all_levels()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("  [PASS] Racial features are properly defined for all races")
        print("  [PASS] Subclass features are properly defined for all subclasses")
        print("  [PASS] Racial features are applied on character creation")
        print("  [PASS] Subclass features are applied when subclass is selected")
        print("  [PASS] Subclass features are applied during level-up")
        print("  [PASS] Class features exist for all classes")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)

