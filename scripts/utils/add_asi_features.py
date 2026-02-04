"""
Script to add Ability Score Increase features to existing characters.
Run with: python add_asi_features.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature
import re

def add_asi_features():
    """Add Ability Score Increase features to existing characters."""
    print("Adding ASI features to existing characters...")
    
    ability_map = {
        'str': 'Strength',
        'dex': 'Dexterity', 
        'con': 'Constitution',
        'int': 'Intelligence',
        'wis': 'Wisdom',
        'cha': 'Charisma'
    }
    
    added = 0
    
    for character in Character.objects.all():
        race = character.race
        if not race or not race.ability_score_increases:
            continue
        
        # Check if this character already has an ASI feature
        if CharacterFeature.objects.filter(
            character=character,
            name='Ability Score Increase',
            feature_type='racial'
        ).exists():
            print(f"  {character.name} already has ASI feature, skipping...")
            continue
        
        # Parse the increases
        increases_str = race.ability_score_increases
        parts = []
        
        for part in increases_str.split(','):
            part = part.strip()
            if part:
                for abbr, full_name in ability_map.items():
                    if abbr in part.lower():
                        match = re.search(r'[+-]?\d+', part)
                        if match:
                            bonus = match.group()
                            parts.append(f"{bonus} {full_name}")
                        break
        
        if parts:
            description = "Your ability scores increase by: " + ", ".join(parts) + "."
            CharacterFeature.objects.create(
                character=character,
                name='Ability Score Increase',
                feature_type='racial',
                description=description,
                source='Race'
            )
            print(f"  ✓ Added ASI feature to {character.name} ({race.name}): {', '.join(parts)}")
            added += 1
    
    print(f"\nAdded {added} ASI features to existing characters.")

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Ability Score Increase Features")
    print("=" * 60)
    add_asi_features()
    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
