
import os
import django
import sys
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterClassLevel, CharacterRace, CharacterStats
from characters.views import CharacterViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User

def test_subclass_access():
    print("--- Starting Subclass API Debug ---")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='debug_user')
    fighter_class, _ = CharacterClass.objects.get_or_create(name="fighter", defaults={'hit_dice': '1d10'})
    
    human_race, _ = CharacterRace.objects.get_or_create(name="Human", defaults={'speed': 30, 'size': 'M'})
    
    # Create Character (Fighter 3)
    char_name = "SubclassTester"
    Character.objects.filter(name=char_name).delete()
    character = Character.objects.create(
        user=user,
        name=char_name,
        level=3,
        character_class=fighter_class,
        race=human_race,
        pending_subclass_selection=True  # Important!
    )
    
    # Create Class Level
    CharacterClassLevel.objects.create(
        character=character,
        character_class=fighter_class,
        level=3
    )
    
    print(f"Created {character.name}: Level {character.level} {fighter_class.name}")
    print(f"Pending Subclass: {character.pending_subclass_selection}")
    
    # 2. Call API
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'get': 'eligible_subclasses'})
    
    request = factory.get(f'/characters/{character.id}/eligible_subclasses/')
    force_authenticate(request, user=user)
    
    # 3. Execute
    try:
        response = view(request, pk=character.id)
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Payload: {json.dumps(response.data, indent=2)}")
            subs = response.data.get('available_subclasses', [])
            if len(subs) > 0:
                print(f"SUCCESS: Found {len(subs)} subclasses: {[s['name'] for s in subs]}")
            else:
                print("FAILURE: Subclass list is empty!")
        else:
            print(f"FAILURE: Error response: {response.data}")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_subclass_access()
