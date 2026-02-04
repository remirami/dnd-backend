
import os
import django
import sys

# Setup Django environment
sys.path.append('c:/dnd-backend/dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterClass, Character, CharacterFeature, CharacterRace, CharacterBackground
from django.contrib.auth.models import User
from characters.serializers import CharacterSerializer

def verify_monk_skills():
    print("Verifying Monk Skills...")
    
    # 1. Verify Class Data
    monk = CharacterClass.objects.get(name='monk')
    print(f"Monk Options: {monk.skill_proficiency_choices}")
    print(f"Monk Limit: {monk.num_skill_choices}")
    
    if not monk.skill_proficiency_choices:
        print("FAIL: Monk has no skill choices in DB.")
        return

    # 2. Create Monk Character via Serializer
    user, _ = User.objects.get_or_create(username='test_user')
    
    # Get IDs
    monk_cls = CharacterClass.objects.get(name='monk')
    human_race = CharacterRace.objects.get(name='human')
    acolyte_bg = CharacterBackground.objects.get(name='acolyte')
    
    data = {
        'name': 'Test Monk',
        'sex': 'Male',
        'character_class': monk_cls.id,
        'race': human_race.id,
        'background': acolyte_bg.id,
        'alignment': 'Neutral', # "True Neutral" maps to "Neutral" usually or strictly enforced
        'ability_scores': {'strength': 10, 'dexterity': 16, 'constitution': 14, 'intelligence': 10, 'wisdom': 14, 'charisma': 10}
    }
    
    # We need a request context usually, but checking if we can mock it or valid without
    # Actually simpler to just call .create() directly if validation isn't needed or duplicate the logic?
    # No, better to use serializer to test the actual logic path.
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory
    factory = APIRequestFactory()
    request = factory.post('/characters/')
    request.user = user

    serializer = CharacterSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        char = serializer.save()
        print(f"Created Monk: {char.name}")
        
        # 3. Verify Class Skills Feature
        features = CharacterFeature.objects.filter(character=char, name="Class Skills")
        if features.exists():
            f = features.first()
            print(f"SUCCESS: Found 'Class Skills' feature.")
            print(f"Options: {f.options}")
            print(f"Limit: {f.choice_limit}")
            
            # Sub-verification
            expected = set(monk.skill_proficiency_choices.split(','))
            actual = set(f.options)
            if expected == actual and f.choice_limit == 2:
                print("Options and Limit match expected SRD values.")
            else:
                 print(f"Mismatch! Expected {len(expected)} options, got {len(actual)}.")
        else:
            print("FAIL: 'Class Skills' feature not created.")
    else:
        print(f"Serializer errors: {serializer.errors}")

if __name__ == "__main__":
    verify_monk_skills()
