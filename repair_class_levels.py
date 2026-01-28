
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClassLevel

def repair_class_levels():
    print("--- Repairing Character Class Levels ---")
    characters = Character.objects.exclude(subclass__isnull=True).exclude(subclass__exact='')
    count = 0

    for char in characters:
        if not char.character_class:
            continue
            
        # Find the class level for the primary class
        cl = CharacterClassLevel.objects.filter(
            character=char, 
            character_class=char.character_class
        ).first()
        
        if cl:
            if cl.subclass != char.subclass:
                print(f"Fixing {char.name}: {cl.subclass} -> {char.subclass}")
                cl.subclass = char.subclass
                cl.save()
                count += 1
            else:
                # print(f"Skipping {char.name}: Already synced")
                pass
        else:
            print(f"Warning: {char.name} has subclass '{char.subclass}' but no class level entry for {char.character_class.name}")
            # Optional: Create it?
            # CharacterClassLevel.objects.create(character=char, character_class=char.character_class, level=char.level, subclass=char.subclass)

    print(f"Repaired {count} characters.")

if __name__ == '__main__':
    repair_class_levels()
