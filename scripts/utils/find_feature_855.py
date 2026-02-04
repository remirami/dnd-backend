
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterFeature

def find_feature_owner():
    try:
        f = CharacterFeature.objects.get(id=855)
        print(f"Feature 855 found!")
        print(f"Name: {f.name}")
        print(f"Character: {f.character.name} (ID: {f.character.id})")
        print(f"Options: {len(f.options or [])}")
        
    except CharacterFeature.DoesNotExist:
        print("Feature 855 does not exist in the database.")

if __name__ == '__main__':
    find_feature_owner()
