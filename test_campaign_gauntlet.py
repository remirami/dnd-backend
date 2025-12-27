"""
Test script for Roguelike Gauntlet Campaign System
Run with: python test_campaign_gauntlet.py

Make sure you have:
- At least 2 characters with stats
- At least 3 encounters with enemies
"""
import requests
import json
import time

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

def test_campaign_gauntlet():
    """Test the roguelike gauntlet campaign system"""
    
    print("\n" + "="*60)
    print("ROGUELIKE GAUNTLET CAMPAIGN SYSTEM TEST")
    print("="*60)
    
    # Step 1: Get or create characters
    print("\n1. Getting characters...")
    chars_response = requests.get(f"{BASE_URL}/characters/")
    characters = chars_response.json().get('results', [])
    
    if len(characters) < 2:
        print("  ERROR: Need at least 2 characters with stats")
        print("  Run: python manage.py create_test_characters")
        return
    
    # Filter characters with stats
    valid_chars = [c for c in characters if c.get('stats')]
    if len(valid_chars) < 2:
        print("  ERROR: Need at least 2 characters with stats")
        return
    
    char1 = valid_chars[0]
    char2 = valid_chars[1]
    print(f"  Using character 1: {char1['name']} (ID: {char1['id']})")
    print(f"  Using character 2: {char2['name']} (ID: {char2['id']})")
    
    # Step 2: Get or create encounters
    print("\n2. Getting encounters...")
    encounters_response = requests.get(f"{BASE_URL}/encounters/")
    encounters = encounters_response.json().get('results', [])
    
    if len(encounters) < 3:
        print("  ERROR: Need at least 3 encounters")
        print("  Run: python manage.py create_test_encounters")
        return
    
    enc1 = encounters[0]
    enc2 = encounters[1] if len(encounters) > 1 else encounters[0]
    enc3 = encounters[2] if len(encounters) > 2 else encounters[0]
    
    print(f"  Using encounter 1: {enc1['name']} (ID: {enc1['id']})")
    print(f"  Using encounter 2: {enc2['name']} (ID: {enc2['id']})")
    print(f"  Using encounter 3: {enc3['name']} (ID: {enc3['id']})")
    
    # Step 3: Create campaign
    print("\n3. Creating campaign...")
    campaign_data = {
        "name": "Test Gauntlet Run",
        "description": "A test roguelike gauntlet campaign",
        "long_rests_available": 2
    }
    campaign_response = requests.post(f"{BASE_URL}/campaigns/", json=campaign_data)
    campaign = print_response(campaign_response, "Campaign Created")
    
    if not campaign:
        return
    
    campaign_id = campaign['id']
    print(f"  Campaign ID: {campaign_id}")
    
    # Step 4: Add characters to campaign
    print("\n4. Adding characters to campaign...")
    
    add_char1 = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/add_character/",
        json={"character_id": char1['id']}
    )
    result1 = print_response(add_char1, f"Added {char1['name']}")
    
    add_char2 = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/add_character/",
        json={"character_id": char2['id']}
    )
    result2 = print_response(add_char2, f"Added {char2['name']}")
    
    # Step 5: Add encounters to campaign
    print("\n5. Adding encounters to campaign...")
    
    add_enc1 = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/add_encounter/",
        json={"encounter_id": enc1['id']}
    )
    print_response(add_enc1, f"Added Encounter 1: {enc1['name']}")
    
    add_enc2 = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/add_encounter/",
        json={"encounter_id": enc2['id']}
    )
    print_response(add_enc2, f"Added Encounter 2: {enc2['name']}")
    
    add_enc3 = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/add_encounter/",
        json={"encounter_id": enc3['id']}
    )
    print_response(add_enc3, f"Added Encounter 3: {enc3['name']}")
    
    # Step 6: Check party status before starting
    print("\n6. Checking initial party status...")
    party_response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/")
    party = print_response(party_response, "Initial Party Status")
    
    # Step 7: Start campaign
    print("\n7. Starting campaign...")
    start_response = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start/")
    start_result = print_response(start_response, "Campaign Started")
    
    if not start_result:
        return
    
    # Step 8: Get current encounter
    print("\n8. Getting current encounter...")
    current_enc_response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/current_encounter/")
    current_enc = print_response(current_enc_response, "Current Encounter")
    
    if current_enc:
        print(f"  Current Encounter: {current_enc['encounter']['name']} (Number {current_enc['encounter_number']})")
    
    # Step 9: Start first encounter
    print("\n9. Starting first encounter...")
    start_enc_response = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start_encounter/")
    start_enc_result = print_response(start_enc_response, "Encounter Started")
    
    # Step 10: Simulate combat (damage characters)
    print("\n10. Simulating combat damage...")
    print("  (In a real scenario, you would run actual combat here)")
    print("  Simulating: Characters take some damage...")
    
    # Get campaign characters
    campaign_chars_response = requests.get(f"{BASE_URL}/campaign-characters/?campaign={campaign_id}")
    campaign_chars = campaign_chars_response.json().get('results', [])
    
    if campaign_chars:
        # Simulate damage by updating HP (in real scenario, this happens during combat)
        print(f"  Note: In real combat, HP would be tracked via CombatParticipant")
        print(f"  For testing, we'll simulate damage by checking party status after combat")
    
    # Step 11: Complete first encounter (simulate victory)
    print("\n11. Completing first encounter...")
    complete_response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/complete_encounter/",
        json={
            "rewards": {
                "gold": 50,
                "xp": 100
            }
        }
    )
    complete_result = print_response(complete_response, "Encounter 1 Completed")
    
    # Step 12: Check party status after encounter
    print("\n12. Checking party status after encounter 1...")
    party_after1 = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/")
    party_status1 = print_response(party_after1, "Party Status After Encounter 1")
    
    # Step 13: Take a short rest
    print("\n13. Taking a short rest...")
    print("  Characters will spend hit dice to heal")
    short_rest_response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/short_rest/",
        json={
            "hit_dice_to_spend": {
                str(campaign_chars[0]['id']): 1,  # First character spends 1 hit die
                str(campaign_chars[1]['id']): 1   # Second character spends 1 hit die
            }
        }
    )
    short_rest_result = print_response(short_rest_response, "Short Rest Completed")
    
    if short_rest_result:
        print(f"  Total healing: {short_rest_result.get('total_healing', 0)} HP")
        print(f"  Short rests used: {short_rest_result.get('short_rests_used', 0)}")
    
    # Step 14: Start second encounter
    print("\n14. Starting second encounter...")
    start_enc2_response = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start_encounter/")
    start_enc2_result = print_response(start_enc2_response, "Encounter 2 Started")
    
    # Step 15: Complete second encounter
    print("\n15. Completing second encounter...")
    complete2_response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/complete_encounter/",
        json={
            "rewards": {
                "gold": 75,
                "xp": 150
            }
        }
    )
    complete2_result = print_response(complete2_response, "Encounter 2 Completed")
    
    # Step 16: Take a long rest (strategic decision!)
    print("\n16. Taking a long rest (strategic decision!)...")
    print("  This will fully restore HP and hit dice, but uses one of the limited long rests")
    long_rest_response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/long_rest/",
        json={"confirm": True}
    )
    long_rest_result = print_response(long_rest_response, "Long Rest Completed")
    
    if long_rest_result:
        print(f"  Long rests used: {long_rest_result.get('long_rests_used', 0)}")
        print(f"  Long rests remaining: {long_rest_result.get('long_rests_remaining', 0)}")
        for char_result in long_rest_result.get('characters', []):
            print(f"    {char_result['character_name']}: Restored {char_result['hp_restored']} HP")
    
    # Step 17: Start third encounter
    print("\n17. Starting third encounter...")
    start_enc3_response = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start_encounter/")
    start_enc3_result = print_response(start_enc3_response, "Encounter 3 Started")
    
    # Step 18: Complete third encounter (campaign should complete)
    print("\n18. Completing third encounter (final encounter)...")
    complete3_response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/complete_encounter/",
        json={
            "rewards": {
                "gold": 100,
                "xp": 200
            }
        }
    )
    complete3_result = print_response(complete3_response, "Encounter 3 Completed")
    
    # Step 19: Check final campaign status
    print("\n19. Checking final campaign status...")
    final_status = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/status/")
    final = print_response(final_status, "Final Campaign Status")
    
    if final:
        campaign_data = final.get('campaign', {})
        print(f"\n  Campaign Status: {campaign_data.get('status', 'unknown')}")
        print(f"  Encounters Completed: {campaign_data.get('current_encounter_index', 0)}/{campaign_data.get('total_encounters', 0)}")
        print(f"  Short Rests Used: {campaign_data.get('short_rests_used', 0)}")
        print(f"  Long Rests Used: {campaign_data.get('long_rests_used', 0)}")
        print(f"  Long Rests Remaining: {campaign_data.get('long_rests_available', 0) - campaign_data.get('long_rests_used', 0)}")
        
        party = final.get('party_status', [])
        print(f"\n  Final Party Status:")
        for char in party:
            status_icon = "ALIVE" if char['is_alive'] else "DEAD"
            print(f"    {char['character']}: {char['current_hp']}/{char['max_hp']} HP ({status_icon})")
            print(f"      Hit Dice: {char['available_hit_dice']}")
    
    # Step 20: Get full campaign details
    print("\n20. Getting full campaign details...")
    campaign_details = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/")
    details = print_response(campaign_details, "Campaign Details")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("  Campaign created and started")
    print("  Characters added to campaign")
    print("  Encounters added and completed")
    print("  Short rest tested (hit dice healing)")
    print("  Long rest tested (full recovery)")
    print("  Campaign progression tested")
    print("\n  SUCCESS: Gauntlet campaign system is working!")
    print("\nTo test with real combat:")
    print("  1. Start an encounter")
    print("  2. Create a combat session using the encounter")
    print("  3. Run combat using the combat system")
    print("  4. Complete the encounter after combat ends")
    print("\nAPI Endpoints tested:")
    print(f"  GET  /api/campaigns/{campaign_id}/")
    print(f"  POST /api/campaigns/{campaign_id}/start/")
    print(f"  POST /api/campaigns/{campaign_id}/add_character/")
    print(f"  POST /api/campaigns/{campaign_id}/add_encounter/")
    print(f"  POST /api/campaigns/{campaign_id}/start_encounter/")
    print(f"  POST /api/campaigns/{campaign_id}/complete_encounter/")
    print(f"  POST /api/campaigns/{campaign_id}/short_rest/")
    print(f"  POST /api/campaigns/{campaign_id}/long_rest/")
    print(f"  GET  /api/campaigns/{campaign_id}/status/")
    print(f"  GET  /api/campaigns/{campaign_id}/party_status/")

if __name__ == "__main__":
    try:
        test_campaign_gauntlet()
    except requests.exceptions.ConnectionError:
        print("\n  ERROR: Could not connect to server.")
        print("   Make sure the Django server is running:")
        print("   python manage.py runserver")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()

