"""
Script to remove duplicate character features and proficiencies.
Run with: python manage.py shell < remove_duplicate_features.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterFeature, CharacterProficiency
from django.db.models import Count

def remove_duplicate_features():
    """Remove duplicate character features while keeping one copy."""
    print("Checking for duplicate features...")
    
    duplicates_removed = 0
    
    for character in Character.objects.all():
        # Get all features for this character grouped by name and type
        features = CharacterFeature.objects.filter(character=character)
        
        # Find duplicates: same name, type, and source
        seen = set()
        for feature in features:
            key = (feature.name, feature.feature_type, feature.source)
            if key in seen:
                print(f"  Removing duplicate: {feature.name} ({feature.feature_type}) from {character.name}")
                feature.delete()
                duplicates_removed += 1
            else:
                seen.add(key)
    
    print(f"\nRemoved {duplicates_removed} duplicate features.")

def remove_duplicate_proficiencies():
    """Remove duplicate character proficiencies while keeping one copy."""
    print("\nChecking for duplicate proficiencies...")
    
    duplicates_removed = 0
    
    for character in Character.objects.all():
        # Get all proficiencies for this character
        proficiencies = CharacterProficiency.objects.filter(character=character)
        
        # Find duplicates: same type, skill_name, and source
        seen = set()
        for prof in proficiencies:
            key = (prof.proficiency_type, prof.skill_name, prof.source)
            if key in seen:
                print(f"  Removing duplicate: {prof.skill_name or prof.item_name} from {character.name}")
                prof.delete()
                duplicates_removed += 1
            else:
                seen.add(key)
    
    print(f"\nRemoved {duplicates_removed} duplicate proficiencies.")

if __name__ == '__main__':
    print("=" * 60)
    print("Removing Duplicate Features and Proficiencies")
    print("=" * 60)
    remove_duplicate_features()
    remove_duplicate_proficiencies()
    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("=" * 60)
