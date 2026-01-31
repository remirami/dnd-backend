import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace
from characters.serializers import CharacterSerializer

def test_creation():
    print("Testing New Warlock Creation...")
    user, _ = User.objects.get_or_create(username='test_creator')
    warlock_class = CharacterClass.objects.get(name='warlock')
    # Use first available race
    race = CharacterRace.objects.first()

    data = {
        'name': "Fresh Warlock",
        'character_class_id': warlock_class.id,
        'race_id': race.id,
        'level': 1,
        'ability_scores': {
            'strength': 10, 'dexterity': 10, 'constitution': 10,
            'intelligence': 10, 'wisdom': 10, 'charisma': 16
        }
    }
    
    # Simulate API creation flow
    context = {'request': type('obj', (object,), {'user': user})}
    serializer = CharacterSerializer(data=data, context=context)
    
    if serializer.is_valid():
        char = serializer.save(user=user)
        print(f"Created Character: {char.name}")
        print(f"Spell Slots: {char.stats.spell_slots}")
        
        expected_slots = {'1': 1}
        if char.stats.spell_slots == expected_slots:
            print("SUCCESS: Spell slots initialized correctly.")
        else:
            print(f"FAIL: Expected {expected_slots}, got {char.stats.spell_slots}")
            
        # Cleanup
        char.delete()
    else:
        print(f"Validation Failed: {serializer.errors}")

if __name__ == '__main__':
    test_creation()
