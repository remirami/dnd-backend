import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Feat

def seed_feat_categories():
    print("Seeding Feat Categories (2024 Rules)...")
    
    # 1. Epic Boons
    epic_boon_count = Feat.objects.filter(name__startswith='Boon of').update(category='epic_boon')
    print(f"Updated {epic_boon_count} Epic Boons.")
    
    # 2. Origin Feats
    origin_feats = [
        'Alert', 'Crafter', 'Healer', 'Lucky', 'Magic Initiate', 
        'Musician', 'Savage Attacker', 'Skilled', 'Tavern Brawler', 'Tough'
    ]
    # Note: Using iexact for robust matching
    origin_count = 0
    for name in origin_feats:
         updated = Feat.objects.filter(name__iexact=name).update(category='origin')
         if updated:
             origin_count += updated
             print(f"Set {name} to Origin")
    
    # 3. Fighting Styles (SRD 5.2 Only)
    # Removed: Dueling, Protection, Blind Fighting, Interception, Thrown Weapon Fighting, Unarmed Fighting
    fighting_styles = [
        'Archery', 'Defense', 'Great Weapon Fighting', 'Two-Weapon Fighting'
    ]
    fs_count = 0
    for name in fighting_styles:
         updated = Feat.objects.filter(name__iexact=name).update(category='fighting_style')
         if updated:
             fs_count += updated
             print(f"Set {name} to Fighting Style")
             
    # 4. General Feats (Default 'general' for everything else if Level > 1?)
    # For now, let's just mark specific known General feats if we have them.
    # We default others to 'other' or 'general' depending on policy.
    # The Model default is 'other'. 
    
    print("\nCategorization Complete.")

if __name__ == "__main__":
    seed_feat_categories()
