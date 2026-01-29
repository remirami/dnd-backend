
import os
import django

# Setup Django environment
import sys
# Add project root to path
sys.path.append('c:/dnd-backend/dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterFeature, CharacterFeat, Feat
from campaigns.feat_data import get_feat_config

def fix_skilled_feat():
    config = get_feat_config('Skilled')
    if not config:
        print("Error: Skilled feat config not found.")
        return

    # 1. Fix CharacterFeatures (What shows on the sheet)
    features = CharacterFeature.objects.filter(name__iexact='Skilled')
    print(f"Found {features.count()} CharacterFeature entries for 'Skilled'.")
    
    for f in features:
        updated = False
        if not f.options:
            f.options = config['options']
            updated = True
        if f.choice_limit != 3:
            f.choice_limit = 3
            updated = True
            
        if updated:
            f.save()
            print(f"Updated CharacterFeature {f.id} for {f.character.name}")
            
    # 2. Fix CharacterFeats (Backend record)
    feats = CharacterFeat.objects.filter(feat__name__iexact='Skilled')
    print(f"Found {feats.count()} CharacterFeat entries for 'Skilled'.")
    
    for f in feats:
        updated = False
        if not f.options:
            f.options = config['options']
            updated = True
        if f.choice_limit != 3:
            f.choice_limit = 3
            updated = True
            
        if updated:
            f.save()
            print(f"Updated CharacterFeat {f.id} for {f.character.name}")

if __name__ == "__main__":
    fix_skilled_feat()
