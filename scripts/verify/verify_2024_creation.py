import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterRace, CharacterClass, CharacterBackground
from characters.serializers import CharacterSerializer
from django.contrib.auth.models import User

def verify_2024_logic():
    print("Verifying 2024 Logic...")
    
    # Setup Data
    user, _ = User.objects.get_or_create(username='test_user')
    human_2024 = CharacterRace.objects.get(name='Human (2024)') # Use exact name from Seed
    farmer = CharacterBackground.objects.get(name='Farmer')
    
    human_2014, _ = CharacterRace.objects.get_or_create(
        name='human', 
        defaults={
            'ability_score_increases': 'STR+1,DEX+1,CON+1,INT+1,WIS+1,CHA+1',
            'source_ruleset': '2014'
        }
    )
    if not human_2014.ability_score_increases:
         human_2014.ability_score_increases = 'STR+1,DEX+1,CON+1,INT+1,WIS+1,CHA+1'
         human_2014.save()

    fighter, _ = CharacterClass.objects.get_or_create(name='fighter', defaults={'hit_dice': 'd10'})

    # 1. Test 2024 Character (Should have NO Racial ASI, but Auto-Grant Origin Feat)
    print("\nTest 1: Creating 2024 Character (Human 2024 + Farmer)...")
    data_2024 = {
        'name': 'Test 2024',
        'ruleset_version': '2024',
        'race_id': human_2024.id,
        'background_id': farmer.id, # Critical for Origin Feat
        'character_class_id': fighter.id,
        'strength': 10,
        'dexterity': 10,
        'constitution': 10,
        'intelligence': 10,
        'wisdom': 10,
        'charisma': 10,
        'user': user.id
    }
    
    serializer_2024 = CharacterSerializer(data=data_2024)
    if serializer_2024.is_valid():
        char_2024 = serializer_2024.save()
        stats = char_2024.stats
        print(f"Stats: Str={stats.strength} (Expected 10)")
        
        if stats.strength == 10:
            print("PASS: 2024 Character has correct stats (No Racial ASI applied).")
        else:
            print(f"FAIL: 2024 Character has wrong stats: {stats.strength}")
            
        # Verify Origin Feat
        feat_entry = char_2024.character_feats.first()
        if feat_entry and feat_entry.feat.name == 'Tough':
             print(f"PASS: Origin Feat 'Tough' auto-granted.")
        else:
             print(f"FAIL: Origin Feat 'Tough' NOT found. Found: {feat_entry}")

    else:
        print("FAIL: Serializer invalid", serializer_2024.errors)

    # 2. Test 2014 Character (Should HAVE Racial ASI)
    print("\nTest 2: Creating 2014 Character (Human 2014)...")
    data_2014 = {
        'name': 'Test 2014',
        'ruleset_version': '2014',
        'race_id': human_2014.id,
        'character_class_id': fighter.id,
        'strength': 10,
        'dexterity': 10,
        'constitution': 10,
        'intelligence': 10,
        'wisdom': 10,
        'charisma': 10,
        'user': user.id
    }
    
    serializer_2014 = CharacterSerializer(data=data_2014)
    if serializer_2014.is_valid():
        char_2014 = serializer_2014.save()
        stats = char_2014.stats
        print(f"Stats: Str={stats.strength} (Expected 11)")
        
        if stats.strength == 11:
            print("PASS: 2014 Character has correct stats (+1 Racial ASI applied).")
        else:
            print(f"FAIL: 2014 Character has wrong stats: {stats.strength}")
            
    else:
        print("FAIL: Serializer invalid", serializer_2014.errors)

if __name__ == '__main__':
    verify_2024_logic()
