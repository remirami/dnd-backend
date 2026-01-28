import os
import django
import sys
from django.contrib.auth import get_user_model

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterFeature, CharacterRace
from characters.serializers import CharacterSerializer

def verify_features():
    User = get_user_model()
    # Create dummy user if needed
    user, _ = User.objects.get_or_create(username='test_verifier', email='test@example.com')
    
    # Get Fighter class
    try:
        fighter = CharacterClass.objects.get(name='fighter')
    except CharacterClass.DoesNotExist:
        # Fallback for dev environment inconsistency
        fighter = CharacterClass.objects.filter(name__iexact='fighter').first()
        if not fighter:
            print("Error: Fighter class not found")
            return

    # Get Race (Any)
    human = CharacterRace.objects.first()
    
    if not human:
        print("Error: No races found in DB")
        return
        
    # 1. Test 2014 Fighter
    print(f"\n--- Testing 2014 Fighter (Race: {human.name}) ---")
    data_14 = {
        'name': 'Fighter 2014',
        'character_class_id': fighter.id,
        'ruleset_version': '2014',
        'race_id': human.id
    }
    # Mock request for serializer context
    from unittest.mock import Mock
    request = Mock(user=user)
    
    # Serializer 'create' needs context? No, perform_create usually handles user. 
    # But serializer.save(user=user) works.
    serializer_14 = CharacterSerializer(data=data_14)
    if serializer_14.is_valid():
        char_14 = serializer_14.save(user=user)
        # Check features
        features = CharacterFeature.objects.filter(character=char_14, feature_type='class')
        print(f"Features count: {features.count()}")
        for f in features:
            print(f"- {f.name}: {f.description[:50]}...")
            
        # Assertion
        has_weapon_mastery = features.filter(name='Weapon Mastery').exists()
        if has_weapon_mastery:
            print("FAILURE: 2014 Fighter has Weapon Mastery!")
        else:
            print("SUCCESS: 2014 Fighter has NO Weapon Mastery.")
    else:
        print(f"Validation Error 14: {serializer_14.errors}")

    # 2. Test 2024 Fighter
    print("\n--- Testing 2024 Fighter ---")
    data_24 = {
        'name': 'Fighter 2024',
        'character_class_id': fighter.id,
        'ruleset_version': '2024',
        'race_id': human.id
    }
    serializer_24 = CharacterSerializer(data=data_24)
    if serializer_24.is_valid():
        char_24 = serializer_24.save(user=user)
        # Check features
        features = CharacterFeature.objects.filter(character=char_24, feature_type='class')
        print(f"Features count: {features.count()}")
        for f in features:
            print(f"- {f.name}: {f.description[:50]}...")
            
        # Assertion
        has_weapon_mastery = features.filter(name='Weapon Mastery').exists()
        if has_weapon_mastery:
            print("SUCCESS: 2024 Fighter HAS Weapon Mastery.")
        else:
            print("FAILURE: 2024 Fighter MISSING Weapon Mastery.")
            
        # Check Second Wind description
        sw = features.filter(name='Second Wind').first()
        if sw:
            if "2 times" in sw.description:
                print("SUCCESS: Second Wind is 2024 version.")
            else:
                print("FAILURE: Second Wind is 2014 version?")
    else:
        print(f"Validation Error 24: {serializer_24.errors}")

    # Cleanup
    char_14.delete()
    char_24.delete()

if __name__ == '__main__':
    verify_features()
