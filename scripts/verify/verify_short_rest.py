
import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from characters.models import Character, CharacterClass, CharacterStats, CharacterRace, CharacterBackground
from rest_framework.test import APIRequestFactory, force_authenticate
from characters.views import CharacterViewSet

User = get_user_model()

def run_verification():
    print("--- Starting Short Rest Verification ---")
    
    # 1. Setup User
    user, created = User.objects.get_or_create(username='test_verifier', email='test@example.com')
    if created:
        user.set_password('testpass')
        user.save()
    print(f"User: {user.username}")

    # Get Race and Background
    race = CharacterRace.objects.first()
    background = CharacterBackground.objects.first()
    
    if not race or not background:
        print("Error: Database must be populated with at least one Race and Background.")
        return

    # 2. Setup Warlock (Pact Magic Test)
    warlock_class, _ = CharacterClass.objects.get_or_create(name='warlock', defaults={'hit_dice': 'd8'})
    warlock, _ = Character.objects.get_or_create(
        name='Test Warlock',
        user=user,
        defaults={
            'character_class': warlock_class,
            'level': 5,
            'race': race,
            'background': background,
        }
    )
    if not hasattr(warlock, 'stats'):
        CharacterStats.objects.create(character=warlock, max_hit_points=40, hit_points=20, constitution=14, armor_class=12)
    
    stats = warlock.stats
    stats.spell_slots = {'3': 2} # Warlock lvl 5 has 2 level 3 slots
    stats.expended_spell_slots = {'3': 2} # All used
    stats.hit_dice_used = 0
    stats.save()
    
    print(f"\n[Test 1] Warlock Short Rest (Slot Reset)")
    print(f"Initial Slots Used: {stats.expended_spell_slots}")
    
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'post': 'short_rest'})
    
    # Request: Short rest, 0 HD
    request = factory.post(f'/characters/{warlock.id}/short_rest/', {'hit_dice_to_spend': 0}, format='json')
    force_authenticate(request, user=user)
    response = view(request, pk=warlock.id)
    
    warlock.stats.refresh_from_db()
    print(f"Response: {response.status_code}")
    print(f"Final Slots Used: {warlock.stats.expended_spell_slots}")
    
    if warlock.stats.expended_spell_slots == {}:
        print("SUCCESS: Warlock slots reset.")
    else:
        print("FAILURE: Warlock slots did not reset.")

    # 3. Setup Wizard (No Slot Reset Test)
    wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard', defaults={'hit_dice': 'd6'})
    wizard, _ = Character.objects.get_or_create(
        name='Test Wizard',
        user=user,
        defaults={
            'character_class': wizard_class,
            'level': 5,
            'race': race,
            'background': background,
        }
    )
    if not hasattr(wizard, 'stats'):
        CharacterStats.objects.create(character=wizard, max_hit_points=30, hit_points=15, constitution=12, armor_class=10)
        
    w_stats = wizard.stats
    w_stats.spell_slots = {'1': 4, '2': 3, '3': 2}
    w_stats.expended_spell_slots = {'1': 1, '3': 1}
    w_stats.hit_dice_used = 0
    w_stats.save()
    
    print(f"\n[Test 2] Wizard Short Rest (No Slot Reset, spending HD)")
    print(f"Initial HP: {w_stats.hit_points}/{w_stats.max_hit_points}")
    print(f"Initial Slots Used: {w_stats.expended_spell_slots}")
    
    # Request: Short rest, 1 HD
    request = factory.post(f'/characters/{wizard.id}/short_rest/', {'hit_dice_to_spend': 1}, format='json')
    force_authenticate(request, user=user)
    response = view(request, pk=wizard.id)
    
    wizard.stats.refresh_from_db()
    print(f"Response: {response.status_code}")
    print(f"Final HP: {wizard.stats.hit_points}")
    print(f"Final Slots Used: {wizard.stats.expended_spell_slots}")
    print(f"Final Hit Dice Used: {wizard.stats.hit_dice_used}")
    
    if wizard.stats.expended_spell_slots == {'1': 1, '3': 1}:
        print("SUCCESS: Wizard slots NOT reset.")
    else:
        print("FAILURE: Wizard slots were reset (or changed) incorrectly.")
        
    if wizard.stats.hit_points > 15:
        print(f"SUCCESS: HP increased by {wizard.stats.hit_points - 15}.")
    else:
        print("FAILURE: HP did not increase.")
        
    if wizard.stats.hit_dice_used == 1:
        print("SUCCESS: Hit Dice decremented correctly.")
    else:
        print(f"FAILURE: Hit Dice used is {wizard.stats.hit_dice_used}, expected 1.")

    # 4. Setup Multiclass Warlock/Sorcerer (Partial Reset Test)
    print("\n[Test 3] Multiclass Warlock/Sorcerer Short Rest")
    mc_char, _ = Character.objects.get_or_create(
        name='Test Multiclass',
        user=user,
        defaults={
            'character_class': warlock_class, # Primary Warlock
            'level': 5, # Total (but we will set class levels manually if needed, or just mock stats)
            'race': race,
            'background': background,
        }
    )
    # Mocking stats as if calculated correctly:
    # Warlock 5 (2 @ L3) + Sorcerer 1 (2 @ L1)
    # Total Slots: L1: 2, L3: 2
    if not hasattr(mc_char, 'stats'):
        CharacterStats.objects.create(character=mc_char, max_hit_points=50, hit_points=50, constitution=14, armor_class=12)
    
    mc_stats = mc_char.stats
    mc_stats.spell_slots = {'1': 2, '3': 2} 
    mc_stats.expended_spell_slots = {'1': 2, '3': 2} # All used
    mc_stats.save()
    
    print(f"Initial Slots Used: {mc_stats.expended_spell_slots}")
    
    # Request: Short Rest
    request = factory.post(f'/characters/{mc_char.id}/short_rest/', {'hit_dice_to_spend': 0}, format='json')
    force_authenticate(request, user=user)
    response = view(request, pk=mc_char.id)
    
    mc_char.stats.refresh_from_db()
    print(f"Final Slots Used: {mc_char.stats.expended_spell_slots}")
    
    # Expectation: Level 3 (Warlock) reset, Level 1 (Sorcerer) NOT reset.
    # Current BUG: All reset (because primary is Warlock) OR None reset (if primary wasn't Warlock).
    # Since primary is Warlock, current code does `expended_spell_slots = {}`.
    
    if '1' in mc_char.stats.expended_spell_slots and mc_char.stats.expended_spell_slots['1'] > 0:
         print("SUCCESS: Sorcerer slots persisted.")
    else:
         print("FAILURE: Sorcerer slots were reset (Expected persistence).")
         
    if '3' not in mc_char.stats.expended_spell_slots or mc_char.stats.expended_spell_slots['3'] == 0:
         print("SUCCESS: Warlock slots reset.")
    else:
         print("FAILURE: Warlock slots NOT reset.")

    # 5. Monk Ki Point Test
    print("\n[Test 4] Monk Ki Point Reset")
    monk_class, _ = CharacterClass.objects.get_or_create(name='monk', defaults={'hit_dice': 'd8'})
    monk, _ = Character.objects.get_or_create(
        name='Test Monk',
        user=user,
        defaults={
            'character_class': monk_class,
            'level': 5,
            'race': race,
            'background': background,
        }
    )
    if not hasattr(monk, 'stats'):
        CharacterStats.objects.create(character=monk, max_hit_points=35, hit_points=35, constitution=14, armor_class=15)
        
    m_stats = monk.stats
    m_stats.ki_points_used = 3
    m_stats.save()
    
    print(f"Initial Ki Used: {m_stats.ki_points_used}")
    
    # Request: Short Rest
    request = factory.post(f'/characters/{monk.id}/short_rest/', {'hit_dice_to_spend': 0}, format='json')
    force_authenticate(request, user=user)
    response = view(request, pk=monk.id)
    
    monk.stats.refresh_from_db()
    print(f"Final Ki Used: {monk.stats.ki_points_used}")
    
    if monk.stats.ki_points_used == 0:
        print("SUCCESS: Ki points reset.")
    else:
        print(f"FAILURE: Ki points not reset. Value: {monk.stats.ki_points_used}")

    print("\n--- Verification Complete ---")

if __name__ == '__main__':
    run_verification()
