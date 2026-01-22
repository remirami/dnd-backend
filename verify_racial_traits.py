from django.contrib.auth.models import User
from characters.models import Character, CharacterRace, CharacterClass, CharacterBackground
from characters.services.character_builder import CharacterBuilderService
from characters.builder_models import CharacterBuilderSession

def verify():
    print("Starting verification...")
    # Setup
    user = User.objects.first()
    race = CharacterRace.objects.get(name='elf')
    char_class = CharacterClass.objects.get(name='ranger')
    bg = CharacterBackground.objects.first()
    
    print(f"Testing with Race: {race.name}")
    print(f"Race Skills: {race.skill_proficiencies}")
    print(f"Race Traits: {len(race.traits)} found")

    # Create session
    session = CharacterBuilderSession.objects.create(user=user)
    session.data = {
        'method': 'standard_array',
        'base_scores': {'strength': 10, 'dexterity': 14, 'constitution': 10, 'intelligence': 10, 'wisdom': 14, 'charisma': 10}
    }
    session.save()
    
    # Step 3: Choose Race (Applies Bonuses)
    print("Applying Race selection...")
    success, msg, data = CharacterBuilderService.choose_race(session, race.id)
    if not success:
        print(f"FAILED to choose race: {msg}")
        return
        
    session.refresh_from_db()
    
    # Step 4: Choose Class
    print("Applying Class selection...")
    success, msg, data = CharacterBuilderService.choose_class(session, char_class.id)
    
    # Step 5: Choose Background
    success, msg, data = CharacterBuilderService.choose_background(session, bg.id)
    
    # Finalize
    print("Finalizing character...")
    success, msg, char = CharacterBuilderService.finalize_character(session, "TraitTestElf", "N")
    
    if not success:
        print(f"FAILED: {msg}")
        return
        
    print(f"Character created: {char.name}")
    
    # Verify Skills
    skills = char.proficiencies.filter(proficiency_type='skill')
    skill_names = [s.skill_name for s in skills]
    print(f"Character Skills: {skill_names}")
    
    if "Perception" in skill_names:
        print("SUCCESS: Perception skill found.")
    else:
        print("FAILURE: Perception skill MISSING.")
        
    # Verify Traits
    traits = char.features.filter(source='race')
    trait_names = [t.name for t in traits]
    print(f"Character Racial Traits: {trait_names}")
    
    if "Darkvision" in trait_names:
        print("SUCCESS: Darkvision trait found.")
    else:
        print("FAILURE: Darkvision trait MISSING.")
    
    # Clean up
    char.delete()
    # Verify Racial Bonuses (Elf gets +2 DEX)
    # Base DEX 14 + 2 = 16
    dex_score = char.stats.dexterity
    print(f"Dexterity Score: {dex_score}")
    if dex_score == 16:
        print("SUCCESS: Dex bonus applied (+2).")
    else:
        print(f"FAILED: Dex bonus not applied. Expected 16, got {dex_score}")

    print("Verification complete.")

if __name__ == '__main__':
    verify()
