import requests
import os
import json

# Try to get existing auth token? 
# Or just login?
# Assuming I can use Basic Auth or need to login first.
# For simplicity, I will assume the server is running locally and try a direct POST if I can get a token, but likely need login.
# Actually, I can use the existing DB to get an auth token if DRF Token Auth is enabled.

# Alternative: use manage.py shell to verify the CODE first again? No, I did that.
# I need to hit the HTTP port.

SERVER_URL = "http://127.0.0.1:8000"

def test_api():
    print(f"Testing API at {SERVER_URL}...")
    
    # login
    try:
        resp = requests.post(f"{SERVER_URL}/api/token/", data={'username': 'test_creator', 'password': 'password123'})
        # Wait, I need a valid user.
    except Exception:
        print("Authenticating...")

    # I'll assume I can't easily auth via script without knowing a real password.
    # BUT, I can check if the server is responsive.
    try:
        response = requests.get(f"{SERVER_URL}/api/characters/")
        print(f"Server Status Code: {response.status_code}")
        # 401 Unauthorized is GOOD (Server is up).
        # Connection Refused means server is down/wrong port.
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    print("To truly test the running code, I need to know if the python process has reloaded.")
    print("If I cannot authenticated via script, I cannot CREATE a character via API.")
    
    # ... I can use `requests` inside `manage.py shell`? No.
    # I will just rely on the user to restart if I suspect stale code.
    
    # Wait! I can create a user with known password in a setup script, THEN run this.
    pass

if __name__ == '__main__':
    # Creating a temp user to test API
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
    django.setup()
    from django.contrib.auth.models import User
    
    u, created = User.objects.get_or_create(username='api_tester')
    u.set_password('testpass123')
    u.save()
    
    # Now run requests
    import requests
    
    # 1. Login (Basic Auth)
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth('api_tester', 'testpass123')
    headers = {}
        
    # 2. Get Warlock Class ID
    # Rely on existing DB access for setup only
    from characters.models import CharacterClass, CharacterRace
    warlock = CharacterClass.objects.get(name__icontains='warlock')
    race = CharacterRace.objects.first()
    
    # 3. Create Character
    payload = {
        "name": "API Warlock",
        "character_class_id": warlock.id,
        "race_id": race.id,
        "level": 1,
        "ability_scores": {
            "strength": 10, "dexterity": 10, "constitution": 10, 
            "intelligence": 10, "wisdom": 10, "charisma": 10
        }
    }
    
    print(f"Sending POST to {SERVER_URL}/api/characters/ ...")
    r = requests.post(f"{SERVER_URL}/api/characters/", json=payload, auth=auth)
    
    if r.status_code == 201:
        data = r.json()
        char_id = data['id']
        print(f"Created Character ID: {char_id}")
        
        # 4. Check Slots in Response
        # The serializer should include 'stats'
        stats = data.get('stats', {})
        slots = stats.get('spell_slots', {})
        print(f"Response Slots: {slots}")
        
        if slots == {'1': 1}:
            print("SUCCESS: Server returned correct slots.")
        else:
            print(f"FAIL: Server returned {slots}. Expected {{'1': 1}}.")
            print("CONCLUSION: Server code is STALE. Restart required.")
            
    else:
        print(f"Creation Failed: {r.status_code} {r.text}")



