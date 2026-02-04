
import os
import django
import sys
import json

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature
from characters.serializers import CharacterSerializer
from campaigns.class_features_data import CLASS_FEATURES_2024, CLASS_FEATURES_2014

def repair_and_verify():
    print("--- Repairing Subclass Feature Options ---")
    
    # 1. Update options for Subclass features
    characters = Character.objects.all()
    
    MANEUVER_OPTIONS = [
        "Commander's Strike", "Disarming Attack", "Distracting Strike", "Evasive Footwork",
        "Feinting Attack", "Goading Attack", "Lunging Attack", "Maneuvering Attack",
        "Menacing Attack", "Parry", "Precision Attack", "Pushing Attack", "Rally",
        "Riposte", "Sweeping Attack", "Trip Attack", "Ambush", "Bait and Switch",
        "Brace", "Commanding Presence", "Grappling Strike", "Quick Toss", "Tactical Assessment"
    ]
    
    for char in characters:
        # Fix Fighter Martial Archetype
        ma = CharacterFeature.objects.filter(character=char, name="Martial Archetype").first()
        if ma:
            if not ma.options:
                print(f"Updating Martial Archetype options for {char.name}")
                ma.options = FIGHTER_OPTIONS
                ma.choice_limit = 1
                ma.save()
                updates += 1

        # Fix Combat Superiority
        cs = CharacterFeature.objects.filter(character=char, name="Combat Superiority").first()
        if cs:
            if not cs.options:
                print(f"Updating Combat Superiority options for {char.name}")
                cs.options = MANEUVER_OPTIONS
                cs.choice_limit = 3
                cs.save()
                updates += 1
                
    print(f"Updated {updates} features.")
    
    # 2. Verify Serializer Output for Char 151
    print("\n--- Verifying Serializer Output (Character 151) ---")
    try:
        char = Character.objects.get(id=151)
        serializer = CharacterSerializer(char)
        data = serializer.data
        
        # Find the features in the serialized data
        features = data.get('features', [])
        
        for f in features:
            if f['name'] in ['Martial Archetype', 'Combat Superiority']:
                print(f"\nFeature: {f['name']}")
                print(f"  Options type: {type(f.get('options'))}")
                print(f"  Options len: {len(f.get('options') or [])}")
                print(f"  Selection: {f.get('selection')}")
                
    except Character.DoesNotExist:
        print("Character 151 not found")

if __name__ == '__main__':
    repair_and_verify()
