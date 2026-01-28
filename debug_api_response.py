
import requests
import json
import os

# Assuming server is running on 8000
URL = "http://localhost:8000/api/characters/151/"

# We need a token. Let's try to grab one or just check if the endpoint is public (it's not).
# Alternatively, we can use the python shell to simulate a request through Django Test Client which is easier authentication-wise.

def check_via_client():
    import django
    sys.path.append(os.getcwd())
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
    django.setup()
    
    from rest_framework.test import APIClient
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    client = APIClient()
    # Assume admin user exists from earlier interactions or use the owner of char 151
    # debug_ui_issues said char 151 is "öpö". Let's find its owner.
    from characters.models import Character
    try:
        char = Character.objects.get(id=151)
        user = char.user
        if not user:
             print("Character has no owner.")
             return
        
        print(f"Authenticating as {user.username}")
        client.force_authenticate(user=user)
        
        response = client.get(f'/api/characters/{char.id}/')
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            print(f"--- API Response Features ({len(features)}) ---")
            for f in features:
                if f['name'] == 'Combat Superiority':
                    print(f"\nFeature: {f['name']}")
                    print(f"  ID: {f['id']}")
                    print(f"  Options Key Exists: {'options' in f}")
                    print(f"  Options Value: {f.get('options')}")
                    print(f"  Selection Value: {f.get('selection')}")
        else:
            print(f"Error: {response.status_code} - {response.content}")
            
    except Character.DoesNotExist:
        print("Character 151 not found")

import sys
if __name__ == "__main__":
    check_via_client()
