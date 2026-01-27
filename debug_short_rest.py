import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character
from rest_framework.test import APIRequestFactory, force_authenticate
from characters.views import CharacterViewSet

def debug_short_rest():
    # Get a character
    char = Character.objects.first()
    if not char:
        print("No characters found")
        return

    print(f"Testing Short Rest for: {char.name} (Lvl {char.level} {char.character_class.name})")
    print(f"Initial HP: {char.stats.hit_points}/{char.stats.max_hit_points}")
    print(f"Hit Dice Used: {char.stats.hit_dice_used}")
    
    # Simulate damage
    char.stats.hit_points = 1
    char.stats.save()
    print(f"Reduced HP to 1 for testing.")

    # Request
    factory = APIRequestFactory()
    view = CharacterViewSet.as_view({'post': 'short_rest'})
    
    # Simulate authentication
    request = factory.post(f'/api/characters/{char.id}/short_rest/', {'hit_dice_to_spend': 1}, format='json')
    from django.contrib.auth.models import User
    
    user = char.user
    if not user:
        print("Character has no user. Assigning to 'debug' user.")
        user = User.objects.first() or User.objects.create(username='debug')
        char.user = user
        char.save()
        
    force_authenticate(request, user=user)
    
    response = view(request, pk=char.id)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    # Reload
    char.stats.refresh_from_db()
    print(f"New HP: {char.stats.hit_points}")
    print(f"New Hit Dice Used: {char.stats.hit_dice_used}")

if __name__ == '__main__':
    debug_short_rest()
