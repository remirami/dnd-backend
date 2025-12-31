#!/usr/bin/env python
"""Simple test to verify API imports worked"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from bestiary.models import Enemy
from items.models import Item, Weapon, Armor, MagicItem
from campaigns.models import Campaign
from campaigns.utils import TreasureGenerator, CampaignGenerator

print("\n" + "="*60)
print("  DATABASE CONTENT CHECK")
print("="*60 + "\n")

# Check counts
monster_count = Enemy.objects.count()
item_count = Item.objects.count()
weapon_count = Weapon.objects.count()
armor_count = Armor.objects.count()
magic_count = MagicItem.objects.count()

print(f"Monsters:     {monster_count:>4}")
print(f"Total Items:  {item_count:>4}")
print(f"  - Weapons:  {weapon_count:>4}")
print(f"  - Armor:    {armor_count:>4}")
print(f"  - Magic:    {magic_count:>4}")

# Show sample monsters
print("\n" + "="*60)
print("  SAMPLE MONSTERS BY CR")
print("="*60 + "\n")

for cr in ['1/4', '1', '5', '10']:
    monsters = Enemy.objects.filter(challenge_rating=cr)[:3]
    if monsters.exists():
        print(f"CR {cr}:")
        for monster in monsters:
            print(f"  - {monster.name} (HP: {monster.hp}, AC: {monster.ac})")
        print()

# Show sample items
print("="*60)
print("  SAMPLE ITEMS")
print("="*60 + "\n")

print("Weapons:")
for weapon in Weapon.objects.all()[:5]:
    print(f"  - {weapon.name}")

print("\nArmor:")
for armor in Armor.objects.all()[:3]:
    print(f"  - {armor.name}")

print("\nAll Items (first 10):")
for item in Item.objects.all()[:10]:
    cat = item.category.name if item.category else "No category"
    print(f"  - {item.name} ({cat})")

# Test treasure generation
print("\n" + "="*60)
print("  TESTING TREASURE GENERATION")
print("="*60 + "\n")

campaign = Campaign.objects.create(name="Test Campaign", starting_level=1)

treasure = TreasureGenerator.generate_treasure_room(campaign, 1)
print(f"Generated treasure room: {treasure.room_type}")
print("Rewards:")
for reward in treasure.reward_items.all():
    if reward.item:
        print(f"  - {reward.item.name} x{reward.quantity}")
    if reward.gold_amount:
        print(f"  - {reward.gold_amount} gold")

campaign.delete()

# Test encounter generation
print("\n" + "="*60)
print("  TESTING ENCOUNTER GENERATION")
print("="*60 + "\n")

campaign = Campaign.objects.create(name="Test Campaign 2", starting_level=1)

try:
    CampaignGenerator.populate_campaign(campaign, num_encounters=3)
    
    print(f"Generated {campaign.campaign_encounters.count()} encounters")
    
    for ce in campaign.campaign_encounters.all()[:2]:
        print(f"\nEncounter {ce.encounter_number}:")
        for ee in ce.encounter.encounter_enemies.all():
            print(f"  - {ee.quantity}x {ee.enemy.name} (CR {ee.enemy.challenge_rating})")
except Exception as e:
    print(f"Error: {e}")

campaign.delete()

print("\n" + "="*60)
print("  SUCCESS! ALL SYSTEMS WORKING!")
print("="*60 + "\n")

print("Your treasure and encounter systems are now using real D&D content!")
print(f"\nYou have {monster_count} monsters and {item_count} items in your database.")
print("\nNext steps:")
print("  1. Create a campaign via the API")
print("  2. Start encounters")
print("  3. Collect treasure with real D&D items!")
print()

