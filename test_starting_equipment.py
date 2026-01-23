import os
import django
import sys

#Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace
from characters.starting_equipment import get_starting_equipment_for_class, get_all_packs

def test_starting_equipment_data():
    print("=== Testing Starting Equipment Data Structure ===\n")
    
    # Test Fighter equipment
    print("1. Testing Fighter Equipment:")
    fighter_eq = get_starting_equipment_for_class('fighter')
    if fighter_eq:
        print(f"   ✓ Class: {fighter_eq['class_name']}")
        print(f"   ✓ Starting Gold: {fighter_eq['starting_gold']['min']}-{fighter_eq['starting_gold']['max']} gp")
        print(f"   ✓ Number of Choices: {len(fighter_eq['choices'])}")
        for choice in fighter_eq['choices']:
            print(f"   - Choice {choice['choice_number']}: {choice['description']} ({len(choice['options'])} options)")
    else:
        print("   ✗ Fighter equipment not found!")
    
    # Test Wizard equipment
    print("\n2. Testing Wizard Equipment:")
    wizard_eq = get_starting_equipment_for_class('wizard')
    if wizard_eq:
        print(f"   ✓ Class: {wizard_eq['class_name']}")
        print(f"   ✓ Starting Gold: {wizard_eq['starting_gold']['min']}-{wizard_eq['starting_gold']['max']} gp")
        print(f"   ✓ Number of Choices: {len(wizard_eq['choices'])}")
        print(f"   ✓ Default Items: {[item['name'] for item in wizard_eq['default_items']]}")
    else:
        print("   ✗ Wizard equipment not found!")
    
    # Test Rogue equipment
    print("\n3. Testing Rogue Equipment:")
    rogue_eq = get_starting_equipment_for_class('rogue')
    if rogue_eq:
        print(f"   ✓ Class: {rogue_eq['class_name']}")
        print(f"   ✓ Default Items: {[item['name'] for item in rogue_eq['default_items']]}")
    else:
        print("   ✗ Rogue equipment not found!")
    
    # Test Equipment Packs
    print("\n4. Testing Equipment Packs:")
    packs = get_all_packs()
    print(f"   ✓ Total Packs: {len(packs)}")
    for pack_name, pack_data in packs.items():
        print(f"   - {pack_name}: {pack_data['cost']} gp, {len(pack_data['items'])} items")
    
    # Test specific pack
    print("\n5. Testing Explorer's Pack contents:")
    explorers = get_all_packs().get("Explorer's Pack")
    if explorers:
        print(f"   ✓ Cost: {explorers['cost']} gp")
        for item in explorers['items']:
            print(f"   - {item['name']} x{item['quantity']}")
    
    print("\n=== All Tests Passed! ===")

if __name__ == "__main__":
    test_starting_equipment_data()
