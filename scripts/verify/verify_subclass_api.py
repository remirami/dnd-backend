import os
import django
import sys
# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from characters.models import CharacterClass
from characters.views import CharacterClassViewSet

def verify_api():
    print("--- Verifying Subclass API ---")
    
    # Get a class (e.g. Fighter)
    fighter = CharacterClass.objects.filter(name='Fighter').first()
    if not fighter:
        print("CRITICAL: Fighter class not found")
        return

    view = CharacterClassViewSet.as_view({'get': 'subclasses'})
    factory = APIRequestFactory()

    # Test 2014
    print("\n1. Testing 2014 Ruleset...")
    req_2014 = factory.get(f'/api/character-classes/{fighter.id}/subclasses/?ruleset=2014')
    res_2014 = view(req_2014, pk=fighter.id)
    print(f"   Status: {res_2014.status_code}")
    print(f"   Data: {res_2014.data}")
    
    # Expected: Champion, Battle Master
    names_2014 = [x['name'] for x in res_2014.data]
    if 'Champion' in names_2014:
        print("   SUCCESS: Found Champion")
    else:
        print("   FAILURE: Missing Champion")

    # Test 2024
    print("\n2. Testing 2024 Ruleset...")
    req_2024 = factory.get(f'/api/character-classes/{fighter.id}/subclasses/?ruleset=2024')
    res_2024 = view(req_2024, pk=fighter.id)
    print(f"   Status: {res_2024.status_code}")
    print(f"   Data: {res_2024.data}")
    
    # Expected: Champion, Battle Master (same for Fighter, maybe check Monk?)
    
    # Check Monk for renaming
    monk = CharacterClass.objects.filter(name='Monk').first()
    if monk:
        print("\n3. Testing Monk Rename (2024)...")
        req_monk = factory.get(f'/api/character-classes/{monk.id}/subclasses/?ruleset=2024')
        res_monk = view(req_monk, pk=monk.id)
        monk_subs = [x['name'] for x in res_monk.data]
        print(f"   Monk Subclasses: {monk_subs}")
        if 'Warrior of the Open Hand' in monk_subs:
             print("   SUCCESS: Found Warrior of the Open Hand")
        else:
             print("   FAILURE: Expected Warrior of the Open Hand")

if __name__ == '__main__':
    verify_api()
