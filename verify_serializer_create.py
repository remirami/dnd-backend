from django.contrib.auth.models import User
from characters.models import Character, CharacterRace, CharacterClass, CharacterBackground
from characters.serializers import CharacterSerializer

def verify_serializer():
    print("Starting Serializer Verification...")
    
    # Setup
    user = User.objects.first()
    race = CharacterRace.objects.get(name='human') 
    char_class = CharacterClass.objects.get(name='fighter')
    # Use Charlatan for background testing
    bg = CharacterBackground.objects.get(name='charlatan') 
    
    # Simulate Frontend Payload (Base Scores)
    data = {
        'name': 'SerializerTestBiostory',
        'race_id': race.id,
        'character_class_id': char_class.id,
        'background_id': bg.id,
        'alignment': 'CN',
        'strength': 10,
        'dexterity': 14, 
        'constitution': 10,
        'intelligence': 10,
        'wisdom': 14,
        'charisma': 14 # Boost CHA for Deception?
    }
    
    print(f"Creating character with Background: {bg.name}")
    
    # Create via Serializer
    serializer = CharacterSerializer(data=data)
    if serializer.is_valid():
        char = serializer.save(user=user)
        print(f"Character created: {char.name}")
        
        # Verify Background Skills (Deception)
        skills = char.proficiencies.filter(proficiency_type='skill')
        skill_names = [s.skill_name for s in skills]
        print(f"Skills: {skill_names}")
        
        if 'Deception' in skill_names:
            print("SUCCESS: Deception skill found (Background).")
        else:
            print("FAILED: Deception skill missing.")

        # Verify Background Feature
        features = char.features.filter(feature_type='background')
        feature_names = [f.name for f in features]
        print(f"Background Features: {feature_names}")
        
        if 'False Identity' in feature_names:
             print("SUCCESS: False Identity feature found.")
        else:
             print("FAILED: False Identity feature missing.")
             
        # Cleanup
        char.delete()
    else:
        print(f"Validation Failed: {serializer.errors}")

if __name__ == '__main__':
    verify_serializer()
