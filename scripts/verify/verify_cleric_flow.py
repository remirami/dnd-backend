import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterClassLevel, CharacterFeature, CharacterRace, CharacterBackground
from spells.models import Spell
from rest_framework.test import APIRequestFactory, force_authenticate
from characters.views import CharacterViewSet
from django.contrib.auth.models import User

def verify_cleric():
    print("--- Verifying Cleric (2024) Flow ---")
    
    # 1. Setup
    user, _ = User.objects.get_or_create(username='test_cleric_verifier')
    cleric_class = CharacterClass.objects.get(name__iexact='Cleric')
    race = CharacterRace.objects.first()
    background = CharacterBackground.objects.first()
    
    # 2. Creation (Level 1)
    print("\n1. Creating Level 1 Cleric...")
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'post': 'create'})
    
    data = {
        'name': 'Test Cleric',
        'race_id': race.id,
        'background_id': background.id,
        'character_class_id': cleric_class.id,
        'ruleset_version': '2024',
        'ability_scores': {'str': 10, 'dex': 10, 'con': 14, 'int': 10, 'wis': 16, 'cha': 12}
    }
    
    request = factory.post('/api/characters/', data, format='json')
    force_authenticate(request, user=user)
    response = view(request)
    
    if response.status_code != 201:
        print(f"FAILED: Creation failed with {response.status_code}")
        print(response.data)
        return
        
    char_id = response.data['id']
    character = Character.objects.get(id=char_id)
    print(f"SUCCESS: Created character {character.name} (ID: {char_id})")
    
    # Check Features
    features = CharacterFeature.objects.filter(character=character)
    feature_names = [f.name for f in features]
    print(f"Level 1 Features: {feature_names}")
    
    expected_l1 = ['Spellcasting', 'Divine Order']
    missing = [f for f in expected_l1 if f not in feature_names]
    if missing:
        print(f"WARNING: Missing Level 1 Features: {missing}")
    else:
        print("PASS: Level 1 features present.")

    # 3. Level Up to 3
    print("\n2. Leveling Up to 3...")
    levelup_view = CharacterViewSet.as_view({'post': 'level_up'})
    
    # Lvl 2
    req_l2 = factory.post(f'/api/characters/{char_id}/level_up/', {'class_id': cleric_class.id}, format='json')
    force_authenticate(req_l2, user=user)
    levelup_view(req_l2, pk=char_id)
    
    # Lvl 3
    req_l3 = factory.post(f'/api/characters/{char_id}/level_up/', {'class_id': cleric_class.id}, format='json')
    force_authenticate(req_l3, user=user)
    levelup_view(req_l3, pk=char_id)
    
    character.refresh_from_db()
    print(f"Current Level: {character.level}")
    
    # 4. Subclass Selection
    print("\n3. Selecting Subclass: Life Domain...")
    subclass_view = CharacterViewSet.as_view({'post': 'choose_subclass'})
    subclass_data = {'subclass': 'Life Domain', 'class_id': cleric_class.id}
    
    req_sub = factory.post(f'/api/characters/{char_id}/choose_subclass/', subclass_data, format='json')
    force_authenticate(req_sub, user=user)
    resp_sub = subclass_view(req_sub, pk=char_id)
    
    if resp_sub.status_code != 200:
        print(f"FAILED: Subclass selection failed with {resp_sub.status_code}")
        print(resp_sub.data)
    else:
        print("SUCCESS: Subclass selected.")
        
    # Verify Features again
    features = CharacterFeature.objects.filter(character=character)
    feature_names = [f.name for f in features]
    print(f"Level 3 Features: {feature_names}")
    
    if 'Life Domain' in feature_names or 'Disciple of Life' in feature_names: # Check specific subclass features
         print("PASS: Subclass features present.")
    else:
         print("WARNING: Subclass features missing.")

    # 5. Spell Slots
    stats = character.stats
    print(f"\n4. Spell Slots: {stats.spell_slots}")
    # Cleric Lvl 3: 4 Lv1, 2 Lv2
    if stats.spell_slots.get('1') == 4 and stats.spell_slots.get('2') == 2:
        print("PASS: Spell slots correct.")
    else:
        print("FAIL: Spell slots incorrect (Expected 4 Lv1, 2 Lv2).")

    # Cleanup
    character.delete()
    print("\nTest character deleted.")

if __name__ == '__main__':
    verify_cleric()
