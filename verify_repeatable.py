
import os
import django
import sys

# Setup Django environment
sys.path.append('c:/dnd-backend/dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, Feat, CharacterFeat
from campaigns.feat_data import get_feat_config

def verify_repeatable_feat():
    # 1. Get a test character
    char = Character.objects.first() # Using first available char
    if not char:
        print("No character found to test.")
        return

    print(f"Testing with character: {char.name}")
    
    # 2. Get "Skilled" feat
    skilled = Feat.objects.filter(name__iexact="Skilled").first()
    if not skilled:
        print("Skilled feat not found.")
        return

    # 3. Ensure they have it once (or add it)
    if not CharacterFeat.objects.filter(character=char, feat=skilled).exists():
        print("Adding first instance of Skilled...")
        CharacterFeat.objects.create(character=char, feat=skilled, level_taken=4)
    else:
        print("Character already has Skilled (1st instance).")

    # 4. Try adding it again (Simulate what views.py does)
    print("Attempting to add second instance of Skilled...")
    feat_config = get_feat_config(skilled.name)
    
    # Check if we naturally allow it
    try:
        # Create features to simulate what views.py does now
        from characters.models import CharacterFeature

        # Ensure first feature exists
        if not CharacterFeature.objects.filter(character=char, name="Skilled").exists():
            print("Creating initial Skilled feature (simulating pre-existing state)...")
            CharacterFeature.objects.create(
                character=char,
                name="Skilled",
                feature_type='feat',
                description="Initial skilled",
                options=feat_config.get('options', []),
                choice_limit=feat_config.get('choice_limit', 1)
            )
        
        # Manually create the feature as views.py would
        feature_name = skilled.name
        if feat_config.get('repeatable'):
            count = CharacterFeature.objects.filter(character=char, name__startswith=feature_name).count()
            if count > 0:
                 feature_name = f"{feature_name} ({count + 1})"
        
        CharacterFeature.objects.create(
            character=char,
            name=feature_name,
            feature_type='feat',
            description=skilled.description,
            options=feat_config.get('options', []),
            choice_limit=feat_config.get('choice_limit', 1)
        )
        print(f"Created feature: {feature_name}")
        
        # Verify count
        feat_count = CharacterFeat.objects.filter(character=char, feat=skilled).count()
        feature_count = CharacterFeature.objects.filter(character=char, name__startswith="Skilled").count()
        
        print(f"Total 'Skilled' feats: {feat_count}")
        print(f"Total 'Skilled' features: {feature_count}")
        
        # Verify names
        features = CharacterFeature.objects.filter(character=char, name__startswith="Skilled")
        for f in features:
            print(f"- Feature: {f.name} (Selection: {f.selection})")

    except Exception as e:
        print(f"FAILED to add second instance: {e}")

if __name__ == "__main__":
    verify_repeatable_feat()
