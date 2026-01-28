
import os
import django
import sys
import json

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature

def inspect_features():
    print("--- Inspecting Character Features ---")
    # Get the most recently accessed character or just the first few
    chars = Character.objects.all().order_by('-updated_at')[:5]
    
    for char in chars:
        print(f"\nCharacter: {char.name} (ID: {char.id}) - Level {char.level} {char.character_class.name}")
        features = CharacterFeature.objects.filter(character=char, name="Combat Superiority")
        
        if not features.exists():
            print("  - No 'Combat Superiority' feature found.")
            # Check for generic Battle Master features
            bm_features = CharacterFeature.objects.filter(character=char, source__icontains="Battle Master")
            for f in bm_features:
                print(f"  - Found other BM feature: {f.name}")
            continue
            
        for f in features:
            print(f"  Feature: {f.name} (ID: {f.id})")
            print(f"    Options type: {type(f.options)}")
            print(f"    Options: {f.options}")
            print(f"    Choice Limit: {f.choice_limit}")

if __name__ == '__main__':
    inspect_features()
