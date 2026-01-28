
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature
from campaigns.class_features_data import CLASS_FEATURES_2024, SUBCLASS_FEATURES_2024

def repair_features():
    print("--- Repairing Character Features ---")
    characters = Character.objects.all()
    count = 0
    
    for char in characters:
        # Check standard class features
        if char.character_class:
            # We specifically want to fix Fighting Style for Fighter
            if char.character_class.name == 'Fighter':
                fs = CharacterFeature.objects.filter(character=char, name="Fighting Style").first()
                if fs:
                    # Find data source
                    # Fighting style is generic to class level 1 usually
                    fs_data = next((f for f in CLASS_FEATURES_2024['Fighter'][1] if f['name'] == 'Fighting Style'), None)
                    if fs_data and fs_data.get('options'):
                        print(f"Updating Fighting Style for {char.name}...")
                        fs.options = fs_data['options']
                        fs.choice_limit = fs_data.get('choice_limit', 1)
                        fs.save()
                        count += 1

        # Check subclass features
        if char.subclass:
            # Battle Master Combat Superiority
            if char.subclass == 'Battle Master':
                cs = CharacterFeature.objects.filter(character=char, name="Combat Superiority").first()
                if cs:
                    # Find data source
                    # Battle Master Level 3
                    cs_data = next((f for f in SUBCLASS_FEATURES_2024['Battle Master'][3] if f['name'] == 'Combat Superiority'), None)
                    if cs_data and cs_data.get('options'):
                        print(f"Updating Combat Superiority for {char.name}...")
                        cs.options = cs_data['options']
                        cs.choice_limit = cs_data.get('choice_limit', 1)
                        cs.save()
                        count += 1
                        
    print(f"Repaired {count} features.")

if __name__ == '__main__':
    repair_features()
