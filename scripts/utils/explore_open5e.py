"""
Explore Open5e API to find available subclass/archetype data
"""

import requests
import json

BASE_URL = "https://api.open5e.com"

# Test different endpoint variations
endpoints_to_test = [
    "/classes/",
    "/races/",
    "/subraces/",
    "/archetypes/",
    "/subclasses/",
    "/v1/classes/",
    "/v1/archetypes/",
    "/v1/subclasses/",
]

print("Testing Open5e API endpoints...\n")

for endpoint in endpoints_to_test:
    try:
        url = BASE_URL + endpoint
        response = requests.get(url, timeout=10)
        print(f"{endpoint}: Status {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'count' in data:
                    print(f"  -> Found {data['count']} items")
                    if data.get('results'):
                        first_item = data['results'][0]
                        print(f"  -> First item: {first_item.get('name', 'N/A')}")
                        if 'class' in first_item or 'archetype' in first_item:
                            print(f"  -> This looks like subclass data!")
                            print(f"  -> Sample keys: {list(first_item.keys())[:10]}")
            except:
                print(f"  -> Response is not JSON")
        print()
    except Exception as e:
        print(f"{endpoint}: Error - {str(e)}\n")

# Try to get detailed class info
print("\n" + "="*80)
print("Fetching detailed Fighter class info...")
print("="*80)

try:
    response = requests.get(f"{BASE_URL}/classes/fighter/", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"\nFighter class keys: {list(data.keys())}")
        if 'archetypes' in data:
            print(f"\nArchetypes found: {data['archetypes']}")
        if 'subtypes_name' in data:
            print(f"\nSubtypes name: {data['subtypes_name']}")
except Exception as e:
    print(f"Error: {e}")

# Check if there's a features endpoint
print("\n" + "="*80)
print("Checking for features endpoint...")
print("="*80)

features_endpoints = [
    "/features/",
    "/v1/features/",
    "/classfeatures/",
    "/v1/classfeatures/",
]

for endpoint in features_endpoints:
    try:
        url = BASE_URL + endpoint
        response = requests.get(url, timeout=10)
        print(f"{endpoint}: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'count' in data:
                print(f"  -> Found {data['count']} features")
                if data.get('results'):
                    print(f"  -> Sample: {data['results'][0].get('name', 'N/A')}")
    except Exception as e:
        print(f"{endpoint}: Error - {str(e)}")

