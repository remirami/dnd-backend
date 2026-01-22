
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterClassLevel
from characters.views import CharacterViewSet
from rest_framework.test import APIRequestFactory

def test_level_up():
    print("--- Starting Level Up Debug ---")
    
    # 1. Setup Data
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='debug_user')

    # Ensure Barbarian class exists
    barb_class, _ = CharacterClass.objects.get_or_create(
        name="barbarian", # using lowercase as user reported
        defaults={'hit_dice': '1d12'}
    )
    
    from characters.models import CharacterRace
    human_race, _ = CharacterRace.objects.get_or_create(name="Human", defaults={'speed': 30, 'size': 'M'})
    
    # Create Character
    char_name = "DebugBarb"
    Character.objects.filter(name=char_name).delete()
    character = Character.objects.create(
        user=user, # Assign owner
        name=char_name,
        level=7,
        character_class=barb_class,
        race=human_race,
        alignment="N",
        background=None
    )
    
    # Create Stats
    from characters.models import CharacterStats
    CharacterStats.objects.create(
        character=character,
        strength=10, dexterity=10, constitution=10,
        intelligence=10, wisdom=10, charisma=10,
        hit_points=50, max_hit_points=50,
        armor_class=10,
        initiative=0,
        speed=30,
        passive_perception=10
    )
    
    # Create Class Level
    CharacterClassLevel.objects.create(
        character=character,
        character_class=barb_class,
        level=7
    )
    
    print(f"Created {character.name}: Level {character.level} {barb_class.name}")
    print(f"Pending ASI before: {character.pending_asi_levels}")
    
    # 2. Simulate Level Up Request
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'post': 'level_up'})
    
    # Request payload
    data = {'class_id': barb_class.id}
    request = factory.post(f'/characters/{character.id}/level_up/', data, format='json')
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=user)
    
    # 3. Execute
    print("\n--- Executing Level Up View ---")
    try:
        response = view(request, pk=character.id)
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.data}")
        if response.status_code != 200:
            print(f"Error: {response.data}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        
    # 4. Verification
    character.refresh_from_db()
    print("\n--- After Level Up ---")
    print(f"Total Level: {character.level}")
    
    class_level = CharacterClassLevel.objects.get(character=character, character_class=barb_class)
    print(f"Class Level: {class_level.level}")
    
    print(f"Pending ASI: {character.pending_asi_levels}")
    
    # Check Features
    features = character.features.all()
    print(f"Features Gained ({len(features)}):")
    for f in features:
        print(f"- {f.name} ({f.source})")
        
    # Check if ASI should have triggered
    if 8 in character.pending_asi_levels:
        print("\nSUCCESS: ASI Triggered for Level 8")
    else:
        print("\nFAILURE: ASI DID NOT Trigger for Level 8")

if __name__ == "__main__":
    test_level_up()
