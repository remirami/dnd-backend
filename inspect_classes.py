import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterClass

def inspect_classes():
    print("Inspecting Character Classes...")
    classes = CharacterClass.objects.all().order_by('name')
    
    seen = {}
    for c in classes:
        print(f"ID: {c.id} | Name: '{c.name}' | Hit Dice: {c.hit_dice}")
        key = c.name.lower()
        if key in seen:
            print(f"!! DUPLICATE DETECTED: {c.name} (IDs: {seen[key]} and {c.id})")
        seen[key] = c.id

if __name__ == '__main__':
    inspect_classes()
