import os
import django
import sys
import json

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from items.models import Weapon
from items.serializers import WeaponSerializer
from campaigns.class_features_data import get_class_features

def verify_weapon_mastery():
    print("Verifying Weapon Mastery System...")

    # 1. Verify Model Data
    print("\n1. Verifying Weapon Data...")
    greatsword = Weapon.objects.filter(name__iexact='Greatsword').first()
    if greatsword:
        print(f"Greatsword Mastery: {greatsword.mastery_property}")
        if greatsword.mastery_property == 'Graze':
            print("SUCCESS: Greatsword has correct mastery (Graze)")
        else:
            print(f"FAILURE: Greatsword has wrong mastery: {greatsword.mastery_property}")
    else:
        print("FAILURE: Greatsword not found")

    # 2. Verify Serializer
    print("\n2. Verifying Serializer...")
    if greatsword:
        serializer = WeaponSerializer(greatsword)
        data = serializer.data
        if 'mastery_property' in data:
            print(f"Serializer Output: mastery_property='{data['mastery_property']}'")
            print("SUCCESS: Serializer includes mastery_property")
        else:
            print("FAILURE: Serializer missing mastery_property")

    # 3. Verify Class Features Logic
    print("\n3. Verifying Class Features (Fighter Level 1)...")
    features = get_class_features('Fighter', 1, ruleset='2024')
    wm_feature = next((f for f in features if f['name'] == 'Weapon Mastery'), None)
    
    if wm_feature:
        print("Found Weapon Mastery Feature")
        print(f"Choice Limit: {wm_feature.get('choice_limit')}")
        options = wm_feature.get('options', [])
        print(f"Option Count: {len(options)}")
        if 'Greatsword' in options and 'Dagger' in options:
             print("SUCCESS: Options include expected weapons")
        else:
             print("FAILURE: Options missing expected weapons")
    else:
        print("FAILURE: Weapon Mastery feature not found for Fighter Level 1")

if __name__ == "__main__":
    verify_weapon_mastery()
