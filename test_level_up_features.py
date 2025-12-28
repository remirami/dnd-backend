#!/usr/bin/env python
"""Test script for level-up system with class features and hit dice"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterFeature
from campaigns.models import Campaign, CampaignCharacter, CharacterXP

print("\n" + "="*70)
print("  LEVEL-UP SYSTEM TEST - Class Features & Hit Dice")
print("="*70 + "\n")

# Get or create test user
user, _ = User.objects.get_or_create(username='testuser', defaults={'email': 'test@test.com'})

# Get Fighter class
try:
    fighter_class = CharacterClass.objects.get(name='fighter')
except CharacterClass.DoesNotExist:
    print("ERROR: Fighter class not found. Run: python manage.py populate_character_data")
    exit(1)

# Get a race
try:
    human_race = CharacterRace.objects.get(name='human')
except CharacterRace.DoesNotExist:
    print("ERROR: Human race not found. Run: python manage.py populate_character_data")
    exit(1)

# Create test character
print("Creating test character...")
character = Character.objects.create(
    user=user,
    name="Test Fighter",
    level=1,
    character_class=fighter_class,
    race=human_race
)

# Create stats
stats = CharacterStats.objects.create(
    character=character,
    strength=16,
    dexterity=14,
    constitution=15,
    intelligence=10,
    wisdom=12,
    charisma=8,
    hit_points=12,
    max_hit_points=12,
    armor_class=16
)

print(f"Created: {character.name} - Level {character.level} {character.character_class.name}")
print(f"HP: {stats.hit_points}/{stats.max_hit_points}")
print(f"STR: {stats.strength}, DEX: {stats.dexterity}, CON: {stats.constitution}")

# Create campaign
campaign = Campaign.objects.create(
    owner=user,
    name="Feature Test Campaign",
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

print(f"\nAdded to campaign: {campaign.name}")
print(f"Starting hit dice: {campaign_char.hit_dice_remaining}")

# Check initial features
initial_features = CharacterFeature.objects.filter(character=character)
print(f"\nInitial features: {initial_features.count()}")
for feature in initial_features:
    print(f"  - {feature.name} ({feature.source})")

# Get XP tracking (created by initialize_from_character)
xp_tracking = CharacterXP.objects.get(campaign_character=campaign_char)

print("\n" + "-"*70)
print("  LEVEL UP TO 2")
print("-"*70 + "\n")

# Grant XP to level up to 2
result = xp_tracking.add_xp(300, source="test")
character.refresh_from_db()  # Refresh to get updated level
print(f"Granted 300 XP")
print(f"Current XP: {xp_tracking.current_xp}")
print(f"New Level: {character.level}")
print(f"Level gained: {result['level_gained']}")

# Refresh from database
campaign_char.refresh_from_db()
character.refresh_from_db()

print(f"\nNew HP: {campaign_char.current_hp}/{campaign_char.max_hp}")
print(f"New hit dice: {campaign_char.hit_dice_remaining}")

# Check features gained
level_2_features = CharacterFeature.objects.filter(character=character, source__contains="Level 2")
print(f"\nFeatures gained at level 2: {level_2_features.count()}")
for feature in level_2_features:
    print(f"  - {feature.name}")
    print(f"    {feature.description[:100]}...")

print("\n" + "-"*70)
print("  LEVEL UP TO 3")
print("-"*70 + "\n")

# Level up to 3
result = xp_tracking.add_xp(600, source="test")  # 300 + 600 = 900 (level 3)
character.refresh_from_db()  # Refresh to get updated level
print(f"Granted 600 XP (total: {xp_tracking.current_xp})")
print(f"New Level: {character.level}")

campaign_char.refresh_from_db()
print(f"New HP: {campaign_char.current_hp}/{campaign_char.max_hp}")
print(f"New hit dice: {campaign_char.hit_dice_remaining}")

# Check features gained
level_3_features = CharacterFeature.objects.filter(character=character, source__contains="Level 3")
print(f"\nFeatures gained at level 3: {level_3_features.count()}")
for feature in level_3_features:
    print(f"  - {feature.name}")
    print(f"    {feature.description[:100]}...")

print("\n" + "-"*70)
print("  LEVEL UP TO 5 (Extra Attack)")
print("-"*70 + "\n")

# Level up to 5
result = xp_tracking.add_xp(5600, source="test")  # Total 6500 (level 5)
character.refresh_from_db()  # Refresh to get updated level
print(f"Granted 5600 XP (total: {xp_tracking.current_xp})")
print(f"New Level: {character.level}")

campaign_char.refresh_from_db()
print(f"New HP: {campaign_char.current_hp}/{campaign_char.max_hp}")
print(f"New hit dice: {campaign_char.hit_dice_remaining}")

# Check features gained at level 5
level_5_features = CharacterFeature.objects.filter(character=character, source__contains="Level 5")
print(f"\nFeatures gained at level 5: {level_5_features.count()}")
for feature in level_5_features:
    print(f"  - {feature.name}")
    print(f"    {feature.description[:100]}...")

print("\n" + "-"*70)
print("  ALL CHARACTER FEATURES")
print("-"*70 + "\n")

all_features = CharacterFeature.objects.filter(character=character).order_by('source')
print(f"Total features: {all_features.count()}\n")
for feature in all_features:
    print(f"[{feature.source}] {feature.name}")

print("\n" + "-"*70)
print("  HIT DICE TRACKING")
print("-"*70 + "\n")

print(f"Character Level: {character.level}")
print(f"Hit Dice Pool: {campaign_char.hit_dice_remaining}")
print(f"Expected: {{'d10': {character.level}}} (Fighter uses d10)")

# Verify hit dice count
expected_dice = character.level
actual_dice = campaign_char.hit_dice_remaining.get('d10', 0)
if actual_dice == expected_dice:
    print(f"\n[PASS] Hit dice count is correct!")
else:
    print(f"\n[FAIL] Hit dice count is wrong! Expected {expected_dice}, got {actual_dice}")

print("\n" + "="*70)
print("  TEST COMPLETE")
print("="*70 + "\n")

# Cleanup
print("Cleaning up test data...")
campaign.delete()
character.delete()
print("Done!")

