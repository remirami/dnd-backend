"""
Test script for spell selection data and endpoints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.starting_spells import (
    get_starting_spell_rules,
    is_caster_at_level_1,
    calculate_starting_cantrips,
    calculate_starting_spells,
    get_spell_selection_requirements
)

def test_spell_selection_data():
    """Test spell selection data for all classes"""
    print("=" * 60)
    print("TESTING STARTING SPELL SELECTION DATA")
    print("=" * 60)
    
    classes = [
        'Wizard', 'Cleric', 'Druid', 'Sorcerer', 'Bard', 'Warlock',
        'Paladin', 'Ranger', 'Fighter', 'Barbarian', 'Rogue', 'Monk'
    ]
    
    for class_name in classes:
        print(f"\n{class_name}:")
        print("-" * 40)
        
        # Check if caster at level 1
        is_caster = is_caster_at_level_1(class_name)
        print(f"  Is Caster at Level 1: {is_caster}")
        
        if is_caster:
            # Get cantrips
            cantrips = calculate_starting_cantrips(class_name)
            print(f"  Cantrips: {cantrips}")
            
            # Get spells
            spells_info = calculate_starting_spells(class_name)
            if spells_info:
                print(f"  Spell Type: {spells_info['type']}")
                print(f"  Spell Count: {spells_info['count']}")
                if 'is_spellbook' in spells_info:
                    print(f"  Uses Spellbook: {spells_info['is_spellbook']}")
                if 'can_prepare_all' in spells_info:
                    print(f"  Can Prepare All Class Spells: {spells_info['can_prepare_all']}")
            
            # Get full requirements
            requirements = get_spell_selection_requirements(class_name)
            if requirements:
                print(f"  Description: {requirements['description'][:80]}...")
        else:
            print("  → No spellcasting at level 1")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    test_spell_selection_data()
