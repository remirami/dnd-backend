
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature

def debug_sync():
    try:
        char = Character.objects.get(id=151)
        print(f"Character: {char.name} (ID: {char.id})")
        print(f"Class: '{char.character_class.name}'")
        print(f"Subclass: '{char.subclass}'")
        
        feature = CharacterFeature.objects.filter(character=char, name="Martial Archetype").first()
        if feature:
            print(f"Feature Found: {feature.name}")
            print(f"Selection Type: {type(feature.selection)}")
            print(f"Selection: {feature.selection}")
            print(f"Options: {feature.options}")
        else:
            print("Feature 'Martial Archetype' NOT FOUND")
            
    except Character.DoesNotExist:
        print("Character 151 not found")

if __name__ == '__main__':
    debug_sync()
