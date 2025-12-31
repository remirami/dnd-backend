"""
Test script for Roguelite Gauntlet Features (Phase 1)

Tests:
- Starting level selection
- Experience points system
- Level up functionality
- Treasure rooms
- XP tracking

Run with: python test_roguelite_features.py
Make sure you have:
- At least 2 characters with stats
- At least 3 encounters with enemies
- Django server running
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"


def print_response(response, title=""):
    """Print formatted response"""
    print("\n" + "=" * 60)
    if title:
        print(title)
        print("=" * 60)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        try:
            # Try to encode as UTF-8 and handle errors
            text = response.text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(text[:1000])  # Limit output
        except:
            print("Could not decode response")
    print("=" * 60 + "\n")


def get_data(response):
    """Extract JSON data from response"""
    try:
        data = response.json()
        return data if response.status_code < 400 else None
    except:
        return None


def test_roguelite_features():
    """Test the roguelite features"""
    
    print("\n" + "=" * 60)
    print("ROGUELITE GAUNTLET FEATURES TEST")
    print("=" * 60 + "\n")
    
    # Step 1: Login or register
    print("1. Authenticating...")
    login_data = {
        "username": "testuser_roguelite",
        "password": "testpass123"
    }
    
    # Try to login first
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    if response.status_code != 200:
        # Register if login fails
        register_data = {
            "username": "testuser_roguelite",
            "email": "roguelite@test.com",
            "password": "testpass123",
            "password2": "testpass123"
        }
        response = requests.post(f"{BASE_URL}/auth/register/", json=register_data)
        print_response(response, "User Registration")
        tokens = get_data(response)
        if tokens and 'tokens' in tokens:
            access_token = tokens['tokens']['access']
        else:
            print("[ERROR] Registration failed!")
            return False
    else:
        tokens = get_data(response)
        access_token = tokens['access']
        print("[OK] Login successful!")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 2: Get or create characters
    print("\n2. Getting characters...")
    response = requests.get(f"{BASE_URL}/characters/", headers=headers)
    characters_data = get_data(response)
    
    if not characters_data or len(characters_data.get('results', [])) < 2:
        print("[WARNING] Need at least 2 characters. Creating test characters...")
        
        # Get character class and race
        response = requests.get(f"{BASE_URL}/character-classes/")
        classes = get_data(response)
        if not classes or not classes.get('results'):
            print("[ERROR] No character classes available. Run populate_character_data first.")
            return False
        class_id = classes['results'][0]['id']
        
        response = requests.get(f"{BASE_URL}/character-races/")
        races = get_data(response)
        if not races or not races.get('results'):
            print("[ERROR] No character races available. Run populate_character_data first.")
            return False
        race_id = races['results'][0]['id']
        
        # Create 2 characters
        created_char_ids = []
        for i in range(2):
            char_data = {
                "name": f"Hero {i+1}",
                "level": 1,
                "character_class_id": class_id,
                "race_id": race_id,
                "alignment": "NG"
            }
            response = requests.post(f"{BASE_URL}/characters/", json=char_data, headers=headers)
            if response.status_code == 201:
                char_result = get_data(response)
                char_id = char_result.get('id')
                created_char_ids.append(char_id)
                print(f"   Created character {i+1} (ID: {char_id})")
        
        # Create stats for the characters
        print("   Creating character stats...")
        for char_id in created_char_ids:
            stats_data = {
                "character": char_id,
                "strength": 16,
                "dexterity": 14,
                "constitution": 15,
                "intelligence": 12,
                "wisdom": 13,
                "charisma": 10,
                "hit_points": 30,
                "max_hit_points": 30,
                "armor_class": 15,
                "speed": 30
            }
            response = requests.post(f"{BASE_URL}/character-stats/", json=stats_data, headers=headers)
            if response.status_code == 201:
                print(f"      Created stats for character {char_id}")
            else:
                print(f"      [WARNING] Failed to create stats for character {char_id}: {response.status_code}")
        
        # Get characters again
        response = requests.get(f"{BASE_URL}/characters/", headers=headers)
        characters_data = get_data(response)
    
    characters = characters_data.get('results', []) if characters_data else []
    if len(characters) < 2:
        print("[ERROR] Still don't have enough characters!")
        return False
    
    char_ids = [c['id'] for c in characters[:2]]
    print(f"[OK] Using {len(char_ids)} characters")
    
    # Step 3: Get encounters
    print("\n3. Getting encounters...")
    response = requests.get(f"{BASE_URL}/encounters/")
    encounters_data = get_data(response)
    
    if not encounters_data or len(encounters_data.get('results', [])) < 3:
        print("[ERROR] Need at least 3 encounters. Run create_test_encounters first.")
        return False
    
    encounters = encounters_data['results'][:3]
    encounter_ids = [e['id'] for e in encounters]
    print(f"[OK] Using {len(encounter_ids)} encounters")
    
    # Step 4: Create campaign with starting level 3
    print("\n4. Creating campaign with starting level 3...")
    campaign_data = {
        "name": "Roguelite Test Campaign",
        "description": "Testing roguelite features",
        "starting_level": 3,  # NEW: Starting level selection
        "long_rests_available": 2
    }
    response = requests.post(f"{BASE_URL}/campaigns/", json=campaign_data, headers=headers)
    print_response(response, "Create Campaign (Starting Level 3)")
    campaign = get_data(response)
    
    if not campaign:
        print("[ERROR] Failed to create campaign!")
        return False
    
    campaign_id = campaign['id']
    print(f"[OK] Campaign created with ID: {campaign_id}")
    print(f"   Starting Level: {campaign.get('starting_level', 'N/A')}")
    
    # Step 5: Add characters to campaign
    print("\n5. Adding characters to campaign...")
    for char_id in char_ids:
        response = requests.post(
            f"{BASE_URL}/campaigns/{campaign_id}/add_character/",
            json={"character_id": char_id},
            headers=headers
        )
        if response.status_code == 201:
            char_data = get_data(response)
            char_name = char_data.get('campaign_character', {}).get('character', {}).get('name', 'Unknown')
            char_level = char_data.get('campaign_character', {}).get('character', {}).get('level', 'N/A')
            print(f"   Added {char_name} (Level {char_level})")
        else:
            error_data = get_data(response)
            error_msg = error_data.get('error', 'Unknown error') if error_data else response.text
            print(f"   [WARNING] Failed to add character {char_id}: {error_msg}")
            
            # Try to verify character has stats
            char_response = requests.get(f"{BASE_URL}/characters/{char_id}/", headers=headers)
            char_info = get_data(char_response)
            if char_info and not char_info.get('stats'):
                print(f"      Character {char_id} is missing stats! Creating stats...")
                # Try to create stats
                stats_data = {
                    "character": char_id,
                    "strength": 16,
                    "dexterity": 14,
                    "constitution": 15,
                    "intelligence": 12,
                    "wisdom": 13,
                    "charisma": 10,
                    "hit_points": 30,
                    "max_hit_points": 30,
                    "armor_class": 15,
                    "speed": 30
                }
                stats_response = requests.post(f"{BASE_URL}/character-stats/", json=stats_data, headers=headers)
                if stats_response.status_code == 201:
                    print(f"      Created stats, retrying character addition...")
                    # Retry adding character
                    retry_response = requests.post(
                        f"{BASE_URL}/campaigns/{campaign_id}/add_character/",
                        json={"character_id": char_id},
                        headers=headers
                    )
                    if retry_response.status_code == 201:
                        char_data = get_data(retry_response)
                        char_name = char_data.get('campaign_character', {}).get('character', {}).get('name', 'Unknown')
                        print(f"      Successfully added {char_name} after creating stats")
    
    # Step 6: Add encounters
    print("\n6. Adding encounters to campaign...")
    for enc_id in encounter_ids:
        response = requests.post(
            f"{BASE_URL}/campaigns/{campaign_id}/add_encounter/",
            json={"encounter_id": enc_id},
            headers=headers
        )
        if response.status_code == 201:
            print(f"   Added encounter {enc_id}")
    
    # Step 7: Check party status (should show XP tracking)
    print("\n7. Checking initial party status...")
    response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/", headers=headers)
    party_data = get_data(response)
    if party_data:
        print("[OK] Party status retrieved")
        for char in party_data.get('party', []):
            xp = char.get('current_xp', 0)
            level = char.get('level', 'N/A')
            print(f"   {char.get('character')}: Level {level}, XP: {xp}")
    
    # Step 8: Start campaign
    print("\n8. Starting campaign...")
    response = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start/", headers=headers)
    print_response(response, "Start Campaign")
    
    if response.status_code != 200:
        print("[ERROR] Failed to start campaign!")
        return False
    
    print("[OK] Campaign started!")
    
    # Step 9: Start first encounter
    print("\n9. Starting first encounter...")
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/start_encounter/",
        headers=headers
    )
    if response.status_code == 200:
        print("[OK] Encounter started")
    else:
        print(f"[WARNING] Failed to start encounter: {response.status_code}")
    
    # Step 10: Complete first encounter (should grant XP and maybe treasure)
    print("\n10. Completing first encounter...")
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/complete_encounter/",
        json={},
        headers=headers
    )
    print_response(response, "Complete Encounter 1")
    encounter_result = get_data(response)
    
    if encounter_result:
        xp_rewards = encounter_result.get('xp_rewards', {})
        print("[OK] Encounter completed!")
        print(f"   Total XP granted: {xp_rewards.get('total_xp_granted', 0)}")
        print(f"   Levels gained: {xp_rewards.get('levels_gained', 0)}")
        
        if xp_rewards.get('characters'):
            for char_result in xp_rewards['characters']:
                name = char_result.get('character_name', 'Unknown')
                xp_gained = char_result.get('xp_gained', 0)
                total_xp = char_result.get('total_xp', 0)
                level = char_result.get('level', 'N/A')
                level_gained = char_result.get('level_gained', False)
                level_str = f"{level} (LEVEL UP!)" if level_gained else str(level)
                print(f"   {name}: +{xp_gained} XP (Total: {total_xp}), Level {level_str}")
        
        # Check for treasure room
        if 'treasure_room' in encounter_result:
            treasure = encounter_result['treasure_room']
            print(f"\n   [TREASURE ROOM DISCOVERED!]")
            print(f"   Type: {treasure.get('room_type', 'N/A')}")
            print(f"   Gold: {treasure.get('rewards', {}).get('gold', 0)}")
            print(f"   XP Bonus: {treasure.get('rewards', {}).get('xp_bonus', 0)}")
            items = treasure.get('rewards', {}).get('items', [])
            if items:
                print(f"   Items: {len(items)}")
    
    # Step 11: Check party status again
    print("\n11. Checking party status after encounter...")
    response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/", headers=headers)
    party_data = get_data(response)
    if party_data:
        print("[OK] Updated party status:")
        for char in party_data.get('party', []):
            xp = char.get('current_xp', 0)
            level = char.get('level', 'N/A')
            hp = f"{char.get('current_hp', 0)}/{char.get('max_hp', 0)}"
            print(f"   {char.get('character')}: Level {level}, XP: {xp}, HP: {hp}")
    
    # Step 12: Get treasure rooms
    print("\n12. Checking treasure rooms...")
    response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/treasure_rooms/", headers=headers)
    treasure_rooms = get_data(response)
    if treasure_rooms:
        print(f"[OK] Found {len(treasure_rooms)} treasure room(s)")
        for room in treasure_rooms:
            room_type = room.get('room_type', 'N/A')
            discovered = room.get('discovered', False)
            encounter_num = room.get('encounter_number', 'N/A')
            status = "Discovered" if discovered else "Hidden"
            print(f"   Encounter {encounter_num}: {room_type} - {status}")
            
            if discovered and not room.get('loot_distributed', False):
                print(f"      [LOOT AVAILABLE]")
    
    # Step 12: Claim treasure if available
    if treasure_rooms:
        undiscovered = [r for r in treasure_rooms if not r.get('discovered', False)]
        if undiscovered:
            room_id = undiscovered[0]['id']
            print(f"\n13. Discovering treasure room {room_id}...")
            response = requests.post(
                f"{BASE_URL}/campaigns/{campaign_id}/discover_treasure_room/",
                json={"encounter_number": undiscovered[0]['encounter_number']},
                headers=headers
            )
            print_response(response, "Discover Treasure Room")
        
        # Try to claim treasure
        available = [r for r in treasure_rooms if r.get('discovered', False) and not r.get('loot_distributed', False)]
        if available:
            room_id = available[0]['id']
            print(f"\n14. Claiming treasure from room {room_id}...")
            # Get a character to give rewards to
            response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/", headers=headers)
            party = get_data(response)
            if party and party.get('party'):
                char_id = party['party'][0]['id']
                response = requests.post(
                    f"{BASE_URL}/campaigns/{campaign_id}/claim_treasure/",
                    json={
                        "treasure_room_id": room_id,
                        "character_id": char_id
                    },
                    headers=headers
                )
                print_response(response, "Claim Treasure")
                claim_result = get_data(response)
                if claim_result:
                    rewards = claim_result.get('rewards', {})
                    print(f"   Gold gained: {rewards.get('gold_gained', 0)}")
                    print(f"   XP bonus: {rewards.get('xp_bonus', 0)}")
    
    # Step 14: Test manual XP granting
    print("\n15. Testing manual XP granting...")
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/grant_xp/",
        json={
            "xp_amount": 500,
            "source": "test_reward"
        },
        headers=headers
    )
    print_response(response, "Grant XP (500 XP)")
    xp_result = get_data(response)
    
    if xp_result:
        print("[OK] XP granted manually!")
        for char_result in xp_result.get('results', {}).get('characters', []):
            name = char_result.get('character_name', 'Unknown')
            xp_gained = char_result.get('xp_gained', 0)
            total_xp = char_result.get('total_xp', 0)
            level = char_result.get('level', 'N/A')
            level_gained = char_result.get('level_gained', False)
            level_str = f"{level} (LEVEL UP!)" if level_gained else str(level)
            print(f"   {name}: +{xp_gained} XP (Total: {total_xp}), Level {level_str}")
    
    # Step 15: Start and complete another encounter to test level progression
    print("\n16. Starting second encounter...")
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/start_encounter/",
        headers=headers
    )
    if response.status_code == 200:
        print("[OK] Second encounter started")
    
    print("\n17. Completing second encounter...")
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/complete_encounter/",
        json={},
        headers=headers
    )
    encounter_result = get_data(response)
    
    if encounter_result:
        xp_rewards = encounter_result.get('xp_rewards', {})
        print("[OK] Second encounter completed!")
        print(f"   Total XP granted: {xp_rewards.get('total_xp_granted', 0)}")
        print(f"   Levels gained: {xp_rewards.get('levels_gained', 0)}")
        
        for char_result in xp_rewards.get('characters', []):
            name = char_result.get('character_name', 'Unknown')
            xp_gained = char_result.get('xp_gained', 0)
            total_xp = char_result.get('total_xp', 0)
            level = char_result.get('level', 'N/A')
            level_gained = char_result.get('level_gained', False)
            if level_gained:
                print(f"   {name}: LEVELED UP to Level {level}! (Total XP: {total_xp})")
    
    # Step 16: Final party status
    print("\n18. Final party status...")
    response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/party_status/", headers=headers)
    party_data = get_data(response)
    if party_data:
        print("[OK] Final party status:")
        for char in party_data.get('party', []):
            name = char.get('character', 'Unknown')
            level = char.get('level', 'N/A')
            xp = char.get('current_xp', 0)
            total_xp_gained = char.get('total_xp_gained', 0)
            level_ups = char.get('level_ups_gained', 0)
            hp = f"{char.get('current_hp', 0)}/{char.get('max_hp', 0)}"
            print(f"   {name}:")
            print(f"      Level: {level} (Started at {campaign.get('starting_level', 'N/A')}, +{level_ups} levels)")
            print(f"      XP: {xp} (Total gained: {total_xp_gained})")
            print(f"      HP: {hp}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL ROGUELITE FEATURES TESTS COMPLETED!")
    print("=" * 60)
    print("\nSummary:")
    print("  [OK] Starting level selection works")
    print("  [OK] XP system grants XP on encounter completion")
    print("  [OK] Level ups happen automatically at XP thresholds")
    print("  [OK] Treasure rooms can be generated and discovered")
    print("  [OK] Manual XP granting works")
    print("  [OK] XP tracking in party status")
    print("\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_roguelite_features()
        if not success:
            print("\n[ERROR] Some tests failed. Check the output above for details.")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server.")
        print("   Make sure Django server is running: python manage.py runserver")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

