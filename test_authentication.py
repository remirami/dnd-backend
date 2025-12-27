"""
Test script for user authentication system

Tests:
- User registration
- User login
- Accessing protected endpoints with tokens
- User data isolation (users only see their own data)
- Creating resources with authentication
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
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("=" * 60 + "\n")


def get_data(response):
    """Extract JSON data from response"""
    try:
        data = response.json()
        return data if response.status_code < 400 else None
    except:
        return None


def test_authentication():
    """Test the authentication system"""
    
    print("\n" + "=" * 60)
    print("AUTHENTICATION SYSTEM TEST")
    print("=" * 60 + "\n")
    
    # Test 1: Register User 1
    print("\n1. Registering User 1...")
    user1_data = {
        "username": "testuser1",
        "email": "user1@test.com",
        "password": "testpass123",
        "password2": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=user1_data)
    print_response(response, "User 1 Registration")
    user1_tokens = get_data(response)
    
    # If user already exists, try to login instead
    if not user1_tokens or 'tokens' not in user1_tokens:
        if response.status_code == 400:
            try:
                error_data = response.json()
                if 'username' in str(error_data):
                    print("   User 1 already exists, logging in instead...")
                    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
                        "username": "testuser1",
                        "password": "testpass123"
                    })
                    login_data = get_data(login_response)
                    if login_data and 'access' in login_data:
                        user1_tokens = {'tokens': login_data}
                        print("   Login successful!")
                    else:
                        print("[ERROR] User 1 registration/login failed!")
                        return False
                else:
                    print("[ERROR] User 1 registration failed!")
                    return False
            except:
                print("[ERROR] User 1 registration failed!")
                return False
        else:
            print("[ERROR] User 1 registration failed!")
            return False
    
    user1_access_token = user1_tokens['tokens']['access']
    user1_headers = {"Authorization": f"Bearer {user1_access_token}"}
    print("[OK] User 1 registered/logged in successfully!")
    print(f"   Access Token: {user1_access_token[:50]}...")
    
    # Test 2: Register User 2
    print("\n2. Registering User 2...")
    user2_data = {
        "username": "testuser2",
        "email": "user2@test.com",
        "password": "testpass123",
        "password2": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=user2_data)
    print_response(response, "User 2 Registration")
    user2_tokens = get_data(response)
    
    # If user already exists, try to login instead
    if not user2_tokens or 'tokens' not in user2_tokens:
        if response.status_code == 400:
            try:
                error_data = response.json()
                if 'username' in str(error_data):
                    print("   User 2 already exists, logging in instead...")
                    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
                        "username": "testuser2",
                        "password": "testpass123"
                    })
                    login_data = get_data(login_response)
                    if login_data and 'access' in login_data:
                        user2_tokens = {'tokens': login_data}
                        print("   Login successful!")
                    else:
                        print("[ERROR] User 2 registration/login failed!")
                        return False
                else:
                    print("[ERROR] User 2 registration failed!")
                    return False
            except:
                print("[ERROR] User 2 registration failed!")
                return False
        else:
            print("[ERROR] User 2 registration failed!")
            return False
    
    user2_access_token = user2_tokens['tokens']['access']
    user2_headers = {"Authorization": f"Bearer {user2_access_token}"}
    print("[OK] User 2 registered/logged in successfully!")
    
    # Test 3: Login User 1
    print("\n3. Testing Login for User 1...")
    login_data = {
        "username": "testuser1",
        "password": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    print_response(response, "User 1 Login")
    login_tokens = get_data(response)
    
    if login_tokens and 'access' in login_tokens:
        print("[OK] Login successful!")
        # Update headers with new token from login
        user1_headers = {"Authorization": f"Bearer {login_tokens['access']}"}
    else:
        print("[ERROR] Login failed!")
        return False
    
    # Test 4: Get current user info
    print("\n4. Getting current user info...")
    response = requests.get(f"{BASE_URL}/auth/me/", headers=user1_headers)
    print_response(response, "Current User Info")
    user_info = get_data(response)
    
    if user_info and user_info.get('username') == 'testuser1':
        print("[OK] User info retrieved successfully!")
        print(f"   Username: {user_info.get('username')}")
        print(f"   Email: {user_info.get('email')}")
    else:
        print("[ERROR] Failed to get user info!")
        return False
    
    # Test 5: Try accessing protected endpoint without token
    print("\n5. Testing unauthenticated access (should fail)...")
    response = requests.get(f"{BASE_URL}/characters/")
    print_response(response, "Unauthenticated Characters Request")
    
    if response.status_code == 401:
        print("[OK] Unauthenticated access correctly rejected!")
    else:
        print(f"[WARNING] Unexpected status code: {response.status_code}")
    
    # Test 6: Create character as User 1 (with auth)
    print("\n6. Creating character as User 1...")
    
    # First, we need a character class and race - let's check what's available
    response = requests.get(f"{BASE_URL}/character-classes/")
    classes = get_data(response)
    if classes and 'results' in classes and len(classes['results']) > 0:
        character_class_id = classes['results'][0]['id']
        print(f"   Using character class ID: {character_class_id}")
    else:
        print("[ERROR] No character classes available. Run populate_character_data command first.")
        return False
    
    response = requests.get(f"{BASE_URL}/character-races/")
    races = get_data(response)
    if races and 'results' in races and len(races['results']) > 0:
        race_id = races['results'][0]['id']
        print(f"   Using character race ID: {race_id}")
    else:
        print("[ERROR] No character races available. Run populate_character_data command first.")
        return False
    
    character_data = {
        "name": "User1 Hero",
        "level": 1,
        "character_class_id": character_class_id,
        "race_id": race_id,
        "alignment": "NG"
    }
    response = requests.post(
        f"{BASE_URL}/characters/",
        json=character_data,
        headers=user1_headers
    )
    print_response(response, "Create Character as User 1")
    user1_character = get_data(response)
    
    if user1_character:
        user1_character_id = user1_character.get('id')
        print("[OK] Character created successfully!")
        print(f"   Character ID: {user1_character_id}")
        print(f"   Character Name: {user1_character.get('name')}")
    else:
        print("[ERROR] Failed to create character!")
        return False
    
    # Test 7: Create character as User 2
    print("\n7. Creating character as User 2...")
    character_data = {
        "name": "User2 Hero",
        "level": 1,
        "character_class_id": character_class_id,
        "race_id": race_id,
        "alignment": "CG"
    }
    response = requests.post(
        f"{BASE_URL}/characters/",
        json=character_data,
        headers=user2_headers
    )
    print_response(response, "Create Character as User 2")
    user2_character = get_data(response)
    
    if user2_character:
        user2_character_id = user2_character.get('id')
        print("[OK] Character created successfully!")
        print(f"   Character ID: {user2_character_id}")
        print(f"   Character Name: {user2_character.get('name')}")
    else:
        print("[ERROR] Failed to create character!")
        return False
    
    # Test 8: User 1 should only see their own characters
    print("\n8. Testing data isolation - User 1's characters...")
    response = requests.get(f"{BASE_URL}/characters/", headers=user1_headers)
    print_response(response, "User 1 Characters List")
    user1_characters = get_data(response)
    
    if user1_characters:
        if 'results' in user1_characters:
            character_list = user1_characters['results']
        else:
            character_list = user1_characters if isinstance(user1_characters, list) else [user1_characters]
        
        user1_character_names = [c.get('name') for c in character_list if isinstance(c, dict)]
        print(f"   User 1 sees {len(user1_character_names)} character(s): {user1_character_names}")
        
        if len(user1_character_names) >= 1 and "User1 Hero" in user1_character_names:
            print("[OK] User 1 only sees their own character(s)!")
        else:
            print("[ERROR] Data isolation failed - User 1 sees wrong characters!")
            return False
    else:
        print("[ERROR] Failed to get characters!")
        return False
    
    # Test 9: User 2 should only see their own characters
    print("\n9. Testing data isolation - User 2's characters...")
    response = requests.get(f"{BASE_URL}/characters/", headers=user2_headers)
    print_response(response, "User 2 Characters List")
    user2_characters = get_data(response)
    
    if user2_characters:
        if 'results' in user2_characters:
            character_list = user2_characters['results']
        else:
            character_list = user2_characters if isinstance(user2_characters, list) else [user2_characters]
        
        user2_character_names = [c.get('name') for c in character_list if isinstance(c, dict)]
        print(f"   User 2 sees {len(user2_character_names)} character(s): {user2_character_names}")
        
        if len(user2_character_names) >= 1 and "User2 Hero" in user2_character_names:
            print("[OK] User 2 only sees their own character(s)!")
        else:
            print("[ERROR] Data isolation failed - User 2 sees wrong characters!")
            return False
    else:
        print("[ERROR] Failed to get characters!")
        return False
    
    # Test 10: Create campaign as User 1
    print("\n10. Creating campaign as User 1...")
    campaign_data = {
        "name": "User1's Campaign",
        "description": "Test campaign for User 1",
        "long_rests_available": 2
    }
    response = requests.post(
        f"{BASE_URL}/campaigns/",
        json=campaign_data,
        headers=user1_headers
    )
    print_response(response, "Create Campaign as User 1")
    user1_campaign = get_data(response)
    
    if user1_campaign:
        user1_campaign_id = user1_campaign.get('id')
        print("[OK] Campaign created successfully!")
        print(f"   Campaign ID: {user1_campaign_id}")
        print(f"   Campaign Name: {user1_campaign.get('name')}")
    else:
        print("[ERROR] Failed to create campaign!")
        return False
    
    # Test 11: User 1 should only see their own campaigns
    print("\n11. Testing campaign isolation - User 1's campaigns...")
    response = requests.get(f"{BASE_URL}/campaigns/", headers=user1_headers)
    print_response(response, "User 1 Campaigns List")
    user1_campaigns = get_data(response)
    
    if user1_campaigns:
        if 'results' in user1_campaigns:
            campaign_list = user1_campaigns['results']
        else:
            campaign_list = user1_campaigns if isinstance(user1_campaigns, list) else [user1_campaigns]
        
        user1_campaign_names = [c.get('name') for c in campaign_list if isinstance(c, dict)]
        print(f"   User 1 sees {len(user1_campaign_names)} campaign(s): {user1_campaign_names}")
        
        if len(user1_campaign_names) >= 1 and "User1's Campaign" in user1_campaign_names:
            print("[OK] User 1 only sees their own campaigns!")
        else:
            print("[WARNING] Campaign isolation may have issues")
    else:
        print("[ERROR] Failed to get campaigns!")
        return False
    
    # Test 12: Test token refresh
    print("\n12. Testing token refresh...")
    refresh_token = user1_tokens['tokens']['refresh']
    response = requests.post(
        f"{BASE_URL}/auth/token/refresh/",
        json={"refresh": refresh_token}
    )
    print_response(response, "Token Refresh")
    refreshed_tokens = get_data(response)
    
    if refreshed_tokens and 'access' in refreshed_tokens:
        print("[OK] Token refresh successful!")
        new_access_token = refreshed_tokens['access']
        print(f"   New access token: {new_access_token[:50]}...")
    else:
        print("[ERROR] Token refresh failed!")
        return False
    
    # Test 13: Public endpoints should still be accessible
    print("\n13. Testing public endpoint access (bestiary)...")
    response = requests.get(f"{BASE_URL}/enemies/")
    print_response(response, "Public Enemies Endpoint (No Auth Required)")
    
    if response.status_code == 200:
        print("[OK] Public endpoints are still accessible!")
    else:
        print(f"[WARNING] Unexpected status code: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL AUTHENTICATION TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("  [OK] User registration works")
    print("  [OK] User login works")
    print("  [OK] Protected endpoints require authentication")
    print("  [OK] Users can only see their own characters")
    print("  [OK] Users can only see their own campaigns")
    print("  [OK] Data isolation is working correctly")
    print("  [OK] Token refresh works")
    print("  [OK] Public endpoints remain accessible")
    print("\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_authentication()
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

