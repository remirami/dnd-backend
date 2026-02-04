
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterClassLevel, CharacterRace, CharacterStats
from characters.views import CharacterViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User

def test_fighter_levelup():
    print("--- Starting Fighter Level Up Debug ---")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='debug_user')
    fighter_class, _ = CharacterClass.objects.get_or_create(
        name="fighter", 
        defaults={'hit_dice': '1d10', 'primary_ability': 'STR', 'saving_throw_proficiencies': 'STR,CON'}
    )
    human_race, _ = CharacterRace.objects.get_or_create(name="Human", defaults={'speed': 30, 'size': 'M'})
    
    # Create Character (Fighter 1) with LOW STATS (to fail multiclass prereq if checked)
    char_name = "WeakFighter"
    Character.objects.filter(name=char_name).delete()
    character = Character.objects.create(
        user=user,
        name=char_name,
        level=1,
        character_class=fighter_class,
        race=human_race,
        alignment="N"
    )
    
    # Intentionally NOT creating CharacterClassLevel to simulate potential legacy state?
    # Or creating it to see if it works when present?
    # User said "Fighter 1 to Fighter 2".
    # Let's try WITHOUT the class level first (Simulation of bug).
    # CharacterClassLevel.objects.create(character=character, character_class=fighter_class, level=1)
    
    # Create Stats (Low stats)
    CharacterStats.objects.create(
        character=character,
        strength=10, dexterity=10, constitution=10,  # Fails Fighter Prereq (Str 13 or Dex 13)
        intelligence=10, wisdom=10, charisma=10,
        hit_points=10, max_hit_points=10,
        armor_class=10,
        initiative=0,
        speed=30,
        passive_perception=10
    )
    
    print(f"Created {character.name}: Level {character.level} {fighter_class.name}")
    print("Note: CharacterClassLevel object is MISSING to simulate potential issue.")
    
    # 2. Simulate Level Up Request
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'post': 'level_up'})
    
    data = {'class_id': fighter_class.id}
    request = factory.post(f'/characters/{character.id}/level_up/', data, format='json')
    force_authenticate(request, user=user)
    
    # 3. Execute
    print("\n--- Executing Level Up View ---")
    try:
        response = view(request, pk=character.id)
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.data}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fighter_levelup()
