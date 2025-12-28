#!/usr/bin/env python
"""
Test script to demonstrate API import integration with treasure and encounter systems.

Usage:
    python test_api_integration.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from bestiary.models import Enemy
from items.models import Item, Weapon, Armor, MagicItem
from campaigns.models import Campaign
from campaigns.utils import TreasureGenerator, CampaignGenerator


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_database_content():
    """Check what content is in the database"""
    print_section("📊 Database Content Check")
    
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
    
    if monster_count == 0:
        print("\n⚠️  No monsters found!")
        print("Run: python manage.py import_monsters_from_api --source open5e")
        return False
    
    if item_count == 0:
        print("\n⚠️  No items found!")
        print("Run: python manage.py import_items_from_api --source open5e")
        return False
    
    print("\n✅ Database has content!")
    return True


def show_sample_monsters():
    """Show sample monsters by CR"""
    print_section("🐉 Sample Monsters by CR")
    
    for cr in ['1/4', '1', '5', '10', '15', '20']:
        monsters = Enemy.objects.filter(challenge_rating=cr)[:3]
        if monsters.exists():
            print(f"\nCR {cr}:")
            for monster in monsters:
                print(f"  - {monster.name} (HP: {monster.hp}, AC: {monster.ac})")


def show_sample_items():
    """Show sample items by category"""
    print_section("⚔️  Sample Items by Category")
    
    # Weapons
    weapons = Weapon.objects.all()[:5]
    if weapons.exists():
        print("\nWeapons:")
        for weapon in weapons:
            print(f"  - {weapon.name} ({weapon.damage_dice} {weapon.damage_type}, {weapon.value} gp)")
    
    # Armor
    armor = Armor.objects.all()[:5]
    if armor.exists():
        print("\nArmor:")
        for piece in armor:
            print(f"  - {piece.name} (AC: {piece.armor_class}, {piece.value} gp)")
    
    # Magic Items
    magic = MagicItem.objects.all()[:5]
    if magic.exists():
        print("\nMagic Items:")
        for item in magic:
            print(f"  - {item.name} ({item.rarity}, {item.value} gp)")


def test_treasure_generation():
    """Test treasure generation with imported items"""
    print_section("🏆 Testing Treasure Generation")
    
    # Create test campaign
    campaign = Campaign.objects.create(
        name="API Integration Test",
        starting_level=1
    )
    
    print("Creating treasure rooms...\n")
    
    # Generate different types of treasure rooms
    for i in range(1, 4):
        treasure = TreasureGenerator.generate_treasure_room(campaign, i)
        print(f"Treasure Room {i} ({treasure.room_type}):")
        
        # Show rewards
        rewards = treasure.treasureroomreward_set.all()
        if rewards.exists():
            for reward in rewards:
                if reward.item:
                    print(f"  ✨ {reward.item.name} x{reward.quantity} ({reward.item.rarity})")
                if reward.gold_amount:
                    print(f"  💰 {reward.gold_amount} gold")
                if reward.xp_bonus:
                    print(f"  ⭐ {reward.xp_bonus} XP bonus")
        else:
            print(f"  Rewards: {treasure.rewards}")
        print()
    
    # Cleanup
    campaign.delete()
    print("✅ Treasure generation working!")


def test_encounter_generation():
    """Test encounter generation with imported monsters"""
    print_section("⚔️  Testing Encounter Generation")
    
    # Create test campaign
    campaign = Campaign.objects.create(
        name="Encounter Test",
        starting_level=1
    )
    
    print("Generating encounters...\n")
    
    # Populate campaign with encounters
    try:
        CampaignGenerator.populate_campaign(campaign, num_encounters=5)
        
        # Show generated encounters
        for ce in campaign.campaign_encounters.all():
            print(f"Encounter {ce.encounter_number}:")
            for ee in ce.encounter.encounter_enemies.all():
                enemy = ee.enemy
                print(f"  🐲 {ee.quantity}x {enemy.name} (CR {enemy.challenge_rating}, HP: {enemy.hp}, AC: {enemy.ac})")
            print()
        
        print("✅ Encounter generation working!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        campaign.delete()


def test_integration():
    """Test full integration"""
    print_section("🎮 Testing Full Integration")
    
    # Create test campaign
    campaign = Campaign.objects.create(
        name="Full Integration Test",
        starting_level=3
    )
    
    print("Populating campaign with encounters and treasures...\n")
    
    try:
        # Populate campaign
        CampaignGenerator.populate_campaign(campaign, num_encounters=3)
        
        # Show results
        print(f"Campaign: {campaign.name}")
        print(f"Total Encounters: {campaign.campaign_encounters.count()}")
        print(f"Total Treasure Rooms: {campaign.treasure_rooms.count()}")
        print()
        
        # Show first encounter
        first_encounter = campaign.campaign_encounters.first()
        if first_encounter:
            print(f"First Encounter:")
            for ee in first_encounter.encounter.encounter_enemies.all():
                print(f"  - {ee.quantity}x {ee.enemy.name}")
        
        # Show first treasure
        first_treasure = campaign.treasure_rooms.first()
        if first_treasure:
            print(f"\nFirst Treasure Room ({first_treasure.room_type}):")
            for reward in first_treasure.treasureroomreward_set.all()[:3]:
                if reward.item:
                    print(f"  - {reward.item.name}")
        
        print("\n✅ Full integration working!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        campaign.delete()


def main():
    """Main test function"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║     🎲 D&D API Integration Test                           ║
    ║                                                            ║
    ║     This script tests the integration between:            ║
    ║     - Open5e API imports                                  ║
    ║     - Treasure generation system                          ║
    ║     - Encounter generation system                         ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Check database content
    if not check_database_content():
        print("\n❌ Database is empty. Please import content first:")
        print("   python manage.py import_monsters_from_api --source open5e")
        print("   python manage.py import_items_from_api --source open5e")
        return
    
    # Show samples
    show_sample_monsters()
    show_sample_items()
    
    # Test systems
    test_treasure_generation()
    test_encounter_generation()
    test_integration()
    
    print_section("✅ All Tests Complete!")
    print("Your treasure and encounter systems are now using real D&D content!")
    print("\nNext steps:")
    print("  1. Create a campaign via the API")
    print("  2. Start encounters")
    print("  3. Collect treasure with real D&D items!")
    print()


if __name__ == '__main__':
    main()

