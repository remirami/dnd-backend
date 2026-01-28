import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterBackground

def inspect_backgrounds():
    print("Inspecting Character Backgrounds...")
    bgs = CharacterBackground.objects.all().order_by('name')
    
    for b in bgs:
        print(f"ID: {b.id} | Name: '{b.name}' | Ruleset: {b.source_ruleset}")
        # Print a bit of the ASI/Feat config if exists
        print(f"    - ASIs: {b.ability_score_options}")
        print(f"    - Feat: {getattr(b, 'starting_feat', 'None')}")

if __name__ == '__main__':
    inspect_backgrounds()
