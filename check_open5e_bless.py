import requests
import json

try:
    print("Fetching 'Bless' from Open5e...")
    response = requests.get('https://api.open5e.com/spells/?search=Bless')
    response.raise_for_status()
    data = response.json()
    
    print(f"Found {data['count']} results.")
    
    for result in data['results']:
        print(f"\nName: {result['name']}")
        print(f"Slug: {result['slug']}")
        print(f"Document: {result.get('document__slug', 'N/A')}")
        print(f"Level: {result['level']}")

except Exception as e:
    print(f"Error: {e}")
