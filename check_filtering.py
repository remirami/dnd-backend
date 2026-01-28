import requests
import sys

BASE_URL = "http://localhost:8000"

def check_filtering():
    # Login (if needed, but assuming ReadOnly is public or I have a token? CharacterRace is usually public-ish or requires auth)
    # The snippet showed IsAuthenticated check for some viewsets, but ReadOnlyModelViewSet?
    # ViewSets inherited generic ReadOnlyModelViewSet but usually permissions are set globally.
    # checking views.py again... 
    # CharacterRaceViewSet doesn't specify permission_classes, so it uses default (IsAuthenticated probably).
    # I need a token.
    
    # Get token via verify_2024_creation logic styling (or just assume I can use model access)
    # Actually, let's use django test client or just python request with assumed running server?
    # Running server is on 8000.
    # User credential? 'test_user'
    
    # Simpler: Use Django Test Client inside script to avoid auth hassle if possible, 
    # OR just log in as 'test_user'.
    
    import os
    import django
    sys.path.append(os.getcwd())
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
    django.setup()
    
    from rest_framework.test import APIClient
    from django.contrib.auth.models import User
    
    user, _ = User.objects.get_or_create(username='test_user')
    client = APIClient()
    client.force_authenticate(user=user)
    
    print("Checking 2024 Ruleset Filtering...")
    response = client.get('/api/races/?ruleset=2024')
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
        
    data = response.json()
    # Should only contain 2024 items
    results = data.get('results', data)
    print(f"Found {len(results)} races for 2024:")
    names = [r['name'] for r in results]
    print(names)
    
    if any(n in names for n in ['Human', 'Elf', 'Dwarf']): # 2014 names
         print("FAIL: 2014 races found in 2024 list!")
    else:
         print("PASS: Only 2024 races found (or empty if none seeded).")

    print("\nChecking 2014 Ruleset Filtering...")
    response = client.get('/api/races/?ruleset=2014')
    results = data.get('results', response.json())
    print(f"Found {len(results)} races for 2014:")
    names = [r['name'] for r in results]
    print(names[:5], "...")
    
    if 'Human' in names:
        print("PASS: 2014 Human found.")
    else:
        print("FAIL: 2014 Human NOT found.")

if __name__ == '__main__':
    check_filtering()
