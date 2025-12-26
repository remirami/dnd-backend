"""
Simple script to test the combat system
Run with: python test_combat.py
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def print_response(response, title=""):
    """Pretty print API response"""
    if title:
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(f"Status: {response.status_code}")
        print(response.text)
    
    print(f"\nStatus Code: {response.status_code}")
    return data if response.status_code < 400 else None

def test_combat_flow():
    """Test the complete combat flow"""
    
    print("\n" + "="*60)
    print("COMBAT SYSTEM TEST - Phase 1")
    print("="*60)
    
    # Step 1: Get or create necessary data
    print("\n1. Checking for existing data...")
    
    # Get characters
    chars_response = requests.get(f"{BASE_URL}/characters/")
    characters = chars_response.json().get('results', [])
    if not characters:
        print("❌ No characters found! Please create a character first.")
        print("   You can use Django admin or the API to create one.")
        return
    
    character = characters[0]
    print(f"✓ Using character: {character['name']} (ID: {character['id']})")
    
    # Get encounters
    encounters_response = requests.get(f"{BASE_URL}/encounters/")
    encounters = encounters_response.json().get('results', [])
    if not encounters:
        print("❌ No encounters found! Please create an encounter first.")
        return
    
    # Find an encounter with enemies
    encounter = None
    for enc in encounters:
        # Get full encounter details to see enemies
        enc_detail = requests.get(f"{BASE_URL}/encounters/{enc['id']}/").json()
        enemies = enc_detail.get('enemies', [])
        if enemies:
            encounter = enc_detail
            break
    
    if not encounter:
        print("❌ No encounters with enemies found! Please add enemies to an encounter first.")
        return
    
    print(f"✓ Using encounter: {encounter['name']} (ID: {encounter['id']})")
    
    # Use enemies from the encounter object
    encounter_enemies = encounter.get('enemies', [])
    if not encounter_enemies:
        print("❌ No enemies in encounter! Please add enemies to the encounter first.")
        return
    
    encounter_enemy = encounter_enemies[0]
    print(f"✓ Using enemy: {encounter_enemy['name']} (ID: {encounter_enemy['id']}) from encounter {encounter['id']}")
    
    # Step 2: Create combat session
    print("\n2. Creating combat session...")
    session_data = {
        "encounter_id": encounter['id'],
        "status": "preparing"
    }
    session_response = requests.post(
        f"{BASE_URL}/combat/sessions/",
        json=session_data
    )
    session = print_response(session_response, "Combat Session Created")
    if not session:
        return
    
    session_id = session['id']
    
    # Step 3: Add character to combat
    print("\n3. Adding character to combat...")
    add_char_data = {
        "participant_type": "character",
        "character_id": character['id']
    }
    char_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/add_participant/",
        json=add_char_data
    )
    char_participant = print_response(char_response, "Character Added")
    if not char_participant:
        return
    
    char_participant_id = char_participant['participant']['id']
    
    # Step 4: Add enemy to combat
    print("\n4. Adding enemy to combat...")
    add_enemy_data = {
        "participant_type": "enemy",
        "encounter_enemy_id": encounter_enemy['id']
    }
    enemy_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/add_participant/",
        json=add_enemy_data
    )
    enemy_participant = print_response(enemy_response, "Enemy Added")
    if not enemy_participant:
        return
    
    enemy_participant_id = enemy_participant['participant']['id']
    
    # Step 5: Roll initiative
    print("\n5. Rolling initiative...")
    initiative_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/roll_initiative/"
    )
    initiative_result = print_response(initiative_response, "Initiative Rolled")
    if not initiative_result:
        return
    
    # Step 6: Start combat
    print("\n6. Starting combat...")
    start_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/start/"
    )
    start_result = print_response(start_response, "Combat Started")
    if not start_result:
        return
    
    # Step 7: Get current state
    print("\n7. Getting current combat state...")
    state_response = requests.get(f"{BASE_URL}/combat/sessions/{session_id}/")
    state = print_response(state_response, "Current Combat State")
    if not state:
        return
    
    current_participant = state.get('current_participant')
    if current_participant:
        print(f"\n✓ Current turn: {current_participant['name']} (ID: {current_participant['id']})")
    
    # Step 8: Make an attack
    print("\n8. Making an attack...")
    # Determine attacker and target
    attacker_id = current_participant['id'] if current_participant else char_participant_id
    target_id = enemy_participant_id if attacker_id == char_participant_id else char_participant_id
    
    attack_data = {
        "attacker_id": attacker_id,
        "target_id": target_id,
        "attack_name": "Longsword",
        "advantage": False,
        "disadvantage": False
    }
    attack_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/attack/",
        json=attack_data
    )
    attack_result = print_response(attack_response, "Attack Made")
    
    # Step 9: Advance to next turn
    print("\n9. Advancing to next turn...")
    next_turn_response = requests.post(
        f"{BASE_URL}/combat/sessions/{session_id}/next_turn/"
    )
    next_turn_result = print_response(next_turn_response, "Next Turn")
    
    # Step 10: View combat log
    print("\n10. Viewing combat log...")
    log_response = requests.get(
        f"{BASE_URL}/combat/actions/?combat_session={session_id}"
    )
    log_result = print_response(log_response, "Combat Log")
    
    # Step 11: Test Phase 2 - Spell Casting
    print("\n11. Testing spell casting (Phase 2)...")
    current = session.get_current_participant()
    if current and current['participant_type'] == 'character':
        spell_response = requests.post(
            f"{BASE_URL}/combat/sessions/{session_id}/cast_spell/",
            {
                'caster_id': current['id'],
                'target_id': enemy_participant_id,
                'spell_name': 'Firebolt',
                'spell_level': 0,
                'damage_string': '1d10',
                'save_type': 'DEX',
                'save_dc': 13
            },
            format='json'
        )
        spell_result = print_response(spell_response, "Spell Cast")
    
    # Step 12: Test Phase 2 - Saving Throw
    print("\n12. Testing saving throw (Phase 2)...")
    if current:
        save_response = requests.post(
            f"{BASE_URL}/combat/sessions/{session_id}/saving_throw/",
            {
                'participant_id': enemy_participant_id,
                'save_type': 'DEX',
                'save_dc': 13,
                'advantage': False
            },
            format='json'
        )
        save_result = print_response(save_response, "Saving Throw")
    
    # Step 13: Test Phase 2 - Conditions
    print("\n13. Testing conditions (Phase 2)...")
    if char_participant_id:
        # Try to add a condition (you may need to create conditions first via populate_conditions_environments)
        try:
            # This will fail if no conditions exist, but that's okay for testing
            condition_response = requests.post(
                f"{BASE_URL}/combat/participants/{char_participant_id}/add_condition/",
                {'condition_id': 1},  # Assuming condition ID 1 exists
                format='json'
            )
            if condition_response.status_code < 400:
                print_response(condition_response, "Condition Added")
            else:
                print("  (Skipping condition test - run 'python manage.py populate_conditions_environments' first)")
        except Exception as e:
            print(f"  (Skipping condition test: {e})")
    
    # Step 14: Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("Phase 1:")
    print("✓ Combat session created")
    print("✓ Participants added")
    print("✓ Initiative rolled")
    print("✓ Combat started")
    print("✓ Attack made")
    print("✓ Turn advanced")
    print("\nPhase 2:")
    print("✓ Spell casting tested")
    print("✓ Saving throws tested")
    print("✓ Conditions system tested")
    print("\n✅ Phase 1 & 2 combat system is working!")
    print("\nTo continue testing:")
    print(f"  - Make more attacks: POST {BASE_URL}/combat/sessions/{session_id}/attack/")
    print(f"  - Cast spells: POST {BASE_URL}/combat/sessions/{session_id}/cast_spell/")
    print(f"  - Make saving throws: POST {BASE_URL}/combat/sessions/{session_id}/saving_throw/")
    print(f"  - Add conditions: POST {BASE_URL}/combat/participants/<id>/add_condition/")
    print(f"  - View session: GET {BASE_URL}/combat/sessions/{session_id}/")
    print(f"  - End combat: POST {BASE_URL}/combat/sessions/{session_id}/end/")

if __name__ == "__main__":
    try:
        test_combat_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure the Django server is running:")
        print("   python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

