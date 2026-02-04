import os
import django
from django.test import RequestFactory

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterRace
from characters.views import CharacterViewSet
from rest_framework.test import force_authenticate
from django.contrib.auth.models import User

def reproduce_levelup():
    print("Simulating Warlock Level Up...")
    
    # Setup
    user, _ = User.objects.get_or_create(username='test_user')
    warlock_class = CharacterClass.objects.get(name='warlock')
    
    # Create Level 1 Warlock
    human = CharacterRace.objects.first()
    char = Character.objects.create(
        user=user,
        name="Test Warlock",
        level=1,
        character_class=warlock_class,
        race=human
    )
    from characters.models import CharacterStats
    stats = CharacterStats.objects.create(
        character=char,
        hit_points=8,
        max_hit_points=8,
        temp_hp=0,
        passive_perception=10,
        armor_class=10,
        initiative_bonus=0
    )
    char.stats = stats
    char.save()
    
    # Initial slots (Level 1)
    char.stats.spell_slots = {'1': 1}
    char.stats.save()
    
    print(f"Created Lvl 1: {char.stats.spell_slots}")
    
    # Level Up to 3 (Should get Lvl 2 slots)
    # We do 2 then 3
    
    view = CharacterViewSet.as_view({'post': 'level_up'})
    factory = RequestFactory()
    
    # Level 2
    print("\nLeveling to 2...")
    req = factory.post(f'/characters/{char.id}/level_up/')
    force_authenticate(req, user=user)
    view(req, pk=char.id)
    char.refresh_from_db()
    print(f"Lvl 2 Slots: {char.stats.spell_slots}")
    
    # Level 3
    print("\nLeveling to 3...")
    req = factory.post(f'/characters/{char.id}/level_up/')
    force_authenticate(req, user=user)
    view(req, pk=char.id)
    
    char.refresh_from_db()
    print(f"Lvl 3 Slots: {char.stats.spell_slots}")
    print(f"Pending Choices: {char.pending_spell_choices}")
    
    expected_max = 2
    actual_max = char.pending_spell_choices.get('max_level', 0)
    
    if actual_max == expected_max:
        print("SUCCESS: Max level is correct.")
    else:
        print(f"FAIL: Expected max level {expected_max}, got {actual_max}")

if __name__ == '__main__':
    reproduce_levelup()
