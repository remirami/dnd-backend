import os
import django
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterRace
from characters.views import CharacterViewSet
# We need to simulate the viewset logic or call the method directly?
# The level_up logic is in the ViewSet action 'level_up'.

def test_levelup_flow():
    print("Testing Warlock Level Up Flow (Lvl 1 -> 3)...")
    
    # Setup
    user, _ = User.objects.get_or_create(username='level_tester')
    warlock = CharacterClass.objects.get(name__icontains='warlock')
    race = CharacterRace.objects.first()
    
    # 1. Create Character (using model directly as we know serializer is fixed for creation)
    # Actually, let's use serializer to be safe
    from characters.serializers import CharacterSerializer
    
    data = {
        'name': "LevelUp Tester",
        'character_class_id': warlock.id,
        'race_id': race.id,
        'level': 1,
        'ability_scores': {'strength':10, 'dexterity':10, 'constitution':10, 'intelligence':10, 'wisdom':10, 'charisma':16}
    }
    context = {'request': type('obj', (object,), {'user': user})}
    serializer = CharacterSerializer(data=data, context=context)
    if not serializer.is_valid():
        print(f"Creation Errors: {serializer.errors}")
        return
    char = serializer.save(user=user)
    print(f"Created {char.name} (Lvl {char.level}). Slots: {char.stats.spell_slots}")
    
    # 2. Level Up to 2
    print("Leveling to 2...")
    view = CharacterViewSet()
    view.request = type('obj', (object,), {'user': user, 'method': 'POST'})
    view.kwargs = {'pk': char.id}
    # Mocking get_object
    view.get_object = lambda: char
    
    # Call level_up logic? 
    # The viewset 'level_up' endpoint calls 'perform_level_up' logic essentially.
    # Let's hit the logic used by the endpoint.
    # Reviewing views.py... it handles 'level_up' action.
    
    # Since I can't easily call the action without a full request object, 
    # I will simulate what the action does:
    # 1. Update level and class_levels
    # 2. Recalculate stats
    # 3. Generate pending choices
    
    # ACTUALLY, I should manually manipulate the DB to simulate level up and see if SIGNALS or Save overrides handle it?
    # No, 'level_up' is an explicit action.
    # I will inspect 'characters/views.py' to see exactly what 'level_up' does and call THAT function if detached, 
    # or replicate the calls.
    
    pass 

if __name__ == '__main__':
    # Re-reading views.py quickly to find the logic function
    # It likely calls something in 'level_up_utils.py' or similar?
    # Or it's inline.
    pass
