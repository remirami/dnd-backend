
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature

def check_duplicates():
    try:
        char = Character.objects.get(id=151)
        print(f"--- Checking Duplicates for {char.name} (ID: 151) ---")
        
        # Check Combat Superiority
        features = CharacterFeature.objects.filter(character=char, name="Combat Superiority")
        print(f"\nFound {features.count()} instances of 'Combat Superiority':")
        for f in features:
            print(f"  ID: {f.id} | Options: {len(f.options or [])} | Selection: {f.selection}")

        # Check Martial Archetype
        ma_features = CharacterFeature.objects.filter(character=char, name="Martial Archetype")
        print(f"\nFound {ma_features.count()} instances of 'Martial Archetype':")
        for f in ma_features:
            print(f"  ID: {f.id} | Options: {len(f.options or [])} | Selection: {f.selection}")

    except Character.DoesNotExist:
        print("Character 151 not found")

if __name__ == '__main__':
    check_duplicates()
