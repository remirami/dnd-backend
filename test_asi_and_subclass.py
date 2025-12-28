#!/usr/bin/env python
"""Test ASI player choice and subclass selection"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from campaigns.models import Campaign, CampaignCharacter, CharacterXP

print("\n" + "="*70)
print("  ASI PLAYER CHOICE & SUBCLASS SELECTION TEST")
print("="*70 + "\n")

# Get or create test user
user, _ = User.objects.get_or_create(username='testuser2', defaults={'email': 'test2@test.com'})

# Get Fighter class
fighter_class = CharacterClass.objects.get(name='fighter')
human_race = CharacterRace.objects.get(name='human')

# Create test character
print("Creating test character...")
character = Character.objects.create(
    user=user,
    name="Test Fighter ASI",
    level=1,
    character_class=fighter_class,
    race=human_race
)

# Create stats
stats = CharacterStats.objects.create(
    character=character,
    strength=15,
    dexterity=14,
    constitution=13,
    intelligence=10,
    wisdom=12,
    charisma=8,
    hit_points=12,
    max_hit_points=12,
    armor_class=16
)

print(f"Created: {character.name} - Level {character.level}")
print(f"Initial Stats: STR {stats.strength}, DEX {stats.dexterity}, CON {stats.constitution}")
print(f"Subclass: {character.subclass or 'None'}")

# Create campaign
campaign = Campaign.objects.create(
    owner=user,
    name="ASI Test Campaign",
    starting_level=1
)

# Add character to campaign
campaign_char = CampaignCharacter.objects.create(
    campaign=campaign,
    character=character,
    current_hp=12,
    max_hp=12
)
campaign_char.initialize_from_character()

# Get XP tracking
xp_tracking = CharacterXP.objects.get(campaign_character=campaign_char)

print(f"\nPending ASI levels: {xp_tracking.pending_asi_levels}")
print(f"Pending subclass: {xp_tracking.pending_subclass_selection}")

print("\n" + "-"*70)
print("  LEVEL UP TO 3 (Subclass Selection)")
print("-"*70 + "\n")

# Level up to 3
xp_tracking.add_xp(900, source="test")
character.refresh_from_db()
xp_tracking.refresh_from_db()

print(f"New Level: {character.level}")
print(f"Pending ASI levels: {xp_tracking.pending_asi_levels}")
print(f"Pending subclass: {xp_tracking.pending_subclass_selection}")

if xp_tracking.pending_subclass_selection:
    print("\n[PASS] Subclass selection is pending!")
    
    # Simulate selecting subclass
    print("\nSelecting subclass: Champion...")
    character.subclass = "Champion"
    character.save()
    xp_tracking.pending_subclass_selection = False
    xp_tracking.save()
    
    print(f"[PASS] Subclass selected: {character.subclass}")
else:
    print("\n[FAIL] Subclass selection should be pending at level 3!")

print("\n" + "-"*70)
print("  LEVEL UP TO 4 (ASI)")
print("-"*70 + "\n")

# Level up to 4
xp_tracking.add_xp(1800, source="test")  # 900 + 1800 = 2700 (level 4)
character.refresh_from_db()
xp_tracking.refresh_from_db()

print(f"New Level: {character.level}")
print(f"Pending ASI levels: {xp_tracking.pending_asi_levels}")

if 4 in xp_tracking.pending_asi_levels:
    print("\n[PASS] ASI is pending for level 4!")
    
    # Show current stats
    stats.refresh_from_db()
    print(f"\nCurrent Stats:")
    print(f"  STR: {stats.strength}")
    print(f"  DEX: {stats.dexterity}")
    print(f"  CON: {stats.constitution}")
    
    # Simulate applying ASI: +2 to Strength
    print("\nApplying ASI: +2 to Strength...")
    stats.strength = min(20, stats.strength + 2)
    stats.save()
    xp_tracking.pending_asi_levels.remove(4)
    xp_tracking.save()
    
    stats.refresh_from_db()
    print(f"\nNew Stats:")
    print(f"  STR: {stats.strength} (+2)")
    print(f"  DEX: {stats.dexterity}")
    print(f"  CON: {stats.constitution}")
    
    print(f"\n[PASS] ASI applied successfully!")
    print(f"Remaining pending ASI: {xp_tracking.pending_asi_levels}")
else:
    print("\n[FAIL] ASI should be pending for level 4!")

print("\n" + "-"*70)
print("  LEVEL UP TO 8 (Another ASI)")
print("-"*70 + "\n")

# Level up to 8
xp_tracking.add_xp(31300, source="test")  # Total 34000 (level 8)
character.refresh_from_db()
xp_tracking.refresh_from_db()

print(f"New Level: {character.level}")
print(f"Pending ASI levels: {xp_tracking.pending_asi_levels}")

if 8 in xp_tracking.pending_asi_levels:
    print("\n[PASS] ASI is pending for level 8!")
    
    # Show current stats
    stats.refresh_from_db()
    print(f"\nCurrent Stats:")
    print(f"  STR: {stats.strength}")
    print(f"  DEX: {stats.dexterity}")
    print(f"  CON: {stats.constitution}")
    
    # Simulate applying ASI: +1 to DEX, +1 to CON
    print("\nApplying ASI: +1 to DEX, +1 to CON...")
    stats.dexterity = min(20, stats.dexterity + 1)
    stats.constitution = min(20, stats.constitution + 1)
    stats.save()
    xp_tracking.pending_asi_levels.remove(8)
    xp_tracking.save()
    
    stats.refresh_from_db()
    print(f"\nNew Stats:")
    print(f"  STR: {stats.strength}")
    print(f"  DEX: {stats.dexterity} (+1)")
    print(f"  CON: {stats.constitution} (+1)")
    
    print(f"\n[PASS] ASI applied successfully!")
    print(f"Remaining pending ASI: {xp_tracking.pending_asi_levels}")
else:
    print("\n[FAIL] ASI should be pending for level 8!")

print("\n" + "="*70)
print("  SUMMARY")
print("="*70 + "\n")

character.refresh_from_db()
stats.refresh_from_db()
xp_tracking.refresh_from_db()

print(f"Character: {character.name}")
print(f"Level: {character.level}")
print(f"Class: {character.character_class.name}")
print(f"Subclass: {character.subclass}")
print(f"\nFinal Stats:")
print(f"  STR: {stats.strength} (started at 15)")
print(f"  DEX: {stats.dexterity} (started at 14)")
print(f"  CON: {stats.constitution} (started at 13)")
print(f"  INT: {stats.intelligence}")
print(f"  WIS: {stats.wisdom}")
print(f"  CHA: {stats.charisma}")
print(f"\nPending ASI levels: {xp_tracking.pending_asi_levels}")
print(f"Pending subclass: {xp_tracking.pending_subclass_selection}")

# Verify results
print("\n" + "="*70)
print("  TEST RESULTS")
print("="*70 + "\n")

tests_passed = 0
tests_total = 5

if character.subclass == "Champion":
    print("[PASS] Subclass selection works")
    tests_passed += 1
else:
    print("[FAIL] Subclass selection failed")

if stats.strength == 17:  # 15 + 2
    print("[PASS] First ASI applied correctly (+2 STR)")
    tests_passed += 1
else:
    print(f"[FAIL] First ASI incorrect (STR should be 17, is {stats.strength})")

if stats.dexterity == 15:  # 14 + 1
    print("[PASS] Second ASI applied correctly (+1 DEX)")
    tests_passed += 1
else:
    print(f"[FAIL] Second ASI incorrect (DEX should be 15, is {stats.dexterity})")

if stats.constitution == 14:  # 13 + 1
    print("[PASS] Second ASI applied correctly (+1 CON)")
    tests_passed += 1
else:
    print(f"[FAIL] Second ASI incorrect (CON should be 14, is {stats.constitution})")

if len(xp_tracking.pending_asi_levels) == 0:
    print("[PASS] No pending ASI remaining")
    tests_passed += 1
else:
    print(f"[FAIL] Pending ASI should be empty, has: {xp_tracking.pending_asi_levels}")

print(f"\nTests Passed: {tests_passed}/{tests_total}")

if tests_passed == tests_total:
    print("\n[SUCCESS] ALL TESTS PASSED!")
else:
    print(f"\n[WARNING] {tests_total - tests_passed} test(s) failed")

# Cleanup
print("\nCleaning up...")
campaign.delete()
character.delete()
print("Done!")

