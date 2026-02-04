import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass, CharacterClassLevel, CharacterFeature
from characters.views import CharacterViewSet
from rest_framework.test import APIRequestFactory

def verify_fix():
    print("--- Verifying Dashboard Subclass Fix ---")
    
    # Debug Classes
    print(f"Total Classes: {CharacterClass.objects.count()}")
    for c in CharacterClass.objects.all():
        print(f" - {c.name} (ID: {c.id})")

    # 1. Create a 2024 Monk (Level 3)
    try:
        monk_class = CharacterClass.objects.filter(name__iexact='monk').first()
        if not monk_class:
            raise CharacterClass.DoesNotExist
    except CharacterClass.DoesNotExist:
        print("Monk not found. Using first available class.")
        monk_class = CharacterClass.objects.first()
        if not monk_class:
            print("CRITICAL: No classes in DB.")
            return
    
    # Get a Race
    from characters.models import CharacterRace
    race = CharacterRace.objects.first()
    if not race:
        print("CRITICAL: No races in DB.")
        return

    # Check if we have a test character or create one
    char_name = "Test Monk 2024"
    character = Character.objects.filter(name=char_name).first()
    if not character:
        character = Character.objects.create(
            name=char_name, 
            ruleset_version='2024',
            character_class=monk_class, # Primary class logic
            race=race,
            level=3
        )
    else:
        character.ruleset_version = '2024'
        character.level = 3
        character.character_class = monk_class
        character.subclass = None # Reset
        character.pending_subclass_selection = True
        character.save()
        
    # Ensure ClassLevel exists
    ccl, created = CharacterClassLevel.objects.get_or_create(
        character=character,
        character_class=monk_class,
        defaults={'level': 3}
    )
    if not created:
        ccl.level = 3
        ccl.subclass = None
        ccl.save()
        
    print(f"Created/Updated Character: {character.name} (Lvl 3 Monk, 2024)")
    
    # 2. Call eligible_subclasses
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'get': 'eligible_subclasses'})
    
    request = factory.get(f'/api/characters/{character.id}/eligible_subclasses/')
    request.user = None # Mock if needed, but view might not require it strictly for unit test if permissions bypassed or we just call view method directly? 
    # ViewSet calls self.get_object(), which uses queryset. User filter might apply.
    # CharacterViewSet filters by request.user.
    # We need to bypass this or mock user.
    
    # Hack: Inspect logic directly via method inspection or assume standard retrieval
    # or better: Just instantiate logic manually or override get_object.
    
    # Actually, let's just create a dummy user and assign character to it
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username="testuser")
    character.user = user
    character.save()
    
    from rest_framework.test import force_authenticate
    view = CharacterViewSet.as_view({'get': 'eligible_subclasses'})
    request = factory.get(f'/api/characters/{character.id}/eligible_subclasses/')
    force_authenticate(request, user=user)
    
    response = view(request, pk=character.id)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    available = response.data.get('available_subclasses', [])
    names = [sub['name'] for sub in available]
    
    print(f"Available Subclasses: {names}")
    
    # 3. Assertions
    if "Warrior of the Open Hand" in names:
        print("SUCCESS: Found 'Warrior of the Open Hand' (2024 Name)")
    elif "Way of the Open Hand" in names:
        print("FAILURE: Found 'Way of the Open Hand' (2014 Name) - Fix not working")
    else:
        print("FAILURE: Open Hand subclass not found at all")
        
    # 4. Verify Choose Subclass
    print("\n--- Verifying Selection ---")
    view_choose = CharacterViewSet.as_view({'post': 'choose_subclass'})
    req_choose = factory.post(f'/api/characters/{character.id}/choose_subclass/', {'subclass': 'Warrior of the Open Hand'})
    force_authenticate(req_choose, user=user)
    
    resp_choose = view_choose(req_choose, pk=character.id)
    print(f"Choose Status: {resp_choose.status_code}")
    if resp_choose.status_code == 200:
        character.refresh_from_db()
        print(f"Character Subclass: {character.subclass}")
        if character.subclass == "Warrior of the Open Hand":
             print("SUCCESS: Subclass applied")
             
        # Check Features
        feats = CharacterFeature.objects.filter(character=character, feature_type='subclass')
        print(f"Subclass Features: {[f.name for f in feats]}")
    else:
        print(f"Choose Error: {resp_choose.data}")

if __name__ == '__main__':
    verify_fix()
