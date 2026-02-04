
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature

def debug_features():
    try:
        char = Character.objects.get(id=151)
        print(f"--- Debugging {char.name} (ID: {char.id}) ---")
        
        features_to_check = ["Martial Archetype", "Combat Superiority"]
        
        for fname in features_to_check:
            f = CharacterFeature.objects.filter(character=char, name=fname).first()
            if f:
                print(f"\nFeature: {f.name}")
                print(f"  ID: {f.id}")
                print(f"  Options ({len(f.options or [])}): {f.options}")
                print(f"  Selection: {f.selection}")
                print(f"  Choice Limit: {f.choice_limit}")
            else:
                print(f"\nFeature '{fname}' NOT FOUND")

    except Character.DoesNotExist:
        print("Character 151 not found")

if __name__ == '__main__':
    debug_features()
