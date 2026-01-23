import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterItem
from items.models import Item
from characters.views import CharacterViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User
import json

def test_unequip_item():
    print("--- Testing Unequip Item Endpoint ---")
    
    # 1. Get or create test user
    user, _ = User.objects.get_or_create(username='debug_user')
    
    # 2. Get a character with equipped items
    try:
        character = Character.objects.filter(user=user).first()
        if not character:
            print("ERROR: No characters found for user")
            return
        
        print(f"Testing with character: {character.name} (ID: {character.id})")
        
        # Find an equipped item
        equipped_item = CharacterItem.objects.filter(
            character=character,
            is_equipped=True
        ).first()
        
        if not equipped_item:
            print("No equipped items found. Creating test item...")
            # Create test item
            test_item, _ = Item.objects.get_or_create(
                name="Test Sword",
                defaults={'description': 'A test weapon', 'weight': 3}
            )
            equipped_item = CharacterItem.objects.create(
                character=character,
                item=test_item,
                is_equipped=True,
                equipment_slot='main_hand'
            )
            print(f"Created and equipped: {test_item.name}")
        
        print(f"\nAttempting to unequip: {equipped_item.item.name}")
        print(f"  - CharacterItem ID: {equipped_item.id}")
        print(f"  - Is Equipped: {equipped_item.is_equipped}")
        print(f"  - Equipment Slot: {equipped_item.equipment_slot}")
        
        # 3. Call the unequip API
        factory = APIRequestFactory()
        view = CharacterViewSet.as_view({'post': 'unequip_item'})
        
        request = factory.post(
            f'/characters/{character.id}/unequip_item/',
            {'character_item_id': equipped_item.id},
            format='json'
        )
        force_authenticate(request, user=user)
        
        # 4. Execute
        response = view(request, pk=character.id)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Data: {json.dumps(response.data, indent=2)}")
        
        # 5. Verify state
        equipped_item.refresh_from_db()
        print(f"\nAfter unequip:")
        print(f"  - Is Equipped: {equipped_item.is_equipped}")
        print(f"  - Equipment Slot: {equipped_item.equipment_slot}")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_unequip_item()
