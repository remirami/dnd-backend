
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature

SELECTOR_MAP = {
    'Fighter': 'Martial Archetype',
    'Barbarian': 'Primal Path',
    'Rogue': 'Roguish Archetype',
    'Sorcerer': 'Sorcerous Origin',
    'Warlock': 'Otherworldly Patron',
    'Cleric': 'Divine Domain',
    'Druid': 'Druid Circle',
    'Bard': 'Bard College',
    'Monk': 'Monastic Tradition',
    'Paladin': 'Sacred Oath',
    'Ranger': 'Ranger Archetype',
    'Wizard': 'Arcane Tradition',
}

def sync_subclass_selection():
    print("--- Syncing Subclass Selections ---")
    characters = Character.objects.exclude(subclass__isnull=True).exclude(subclass__exact='')
    count = 0
    
    for char in characters:
        # Normalize class name to Title Case for map lookup
        class_name = char.character_class.name.title()
        selector_name = SELECTOR_MAP.get(class_name)
        if not selector_name:
            print(f"Skipping {char.name}: Class '{class_name}' not in map")
            continue
            
        feature = CharacterFeature.objects.filter(character=char, name=selector_name).first()
        if feature:
            current_selection = feature.selection or []
            if char.subclass not in current_selection:
                print(f"Syncing {char.name} ({char.character_class.name}): {char.subclass}")
                feature.selection = [char.subclass]
                # Also ensure choice_limit is 1
                feature.choice_limit = 1
                feature.save()
                count += 1
    
    print(f"Synced {count} characters.")

if __name__ == '__main__':
    sync_subclass_selection()
