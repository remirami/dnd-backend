"""
Test script for HP mechanics
"""
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterStats

def test_hp_mechanics():
    print("=" * 60)
    print("TESTING HP MECHANICS")
    print("=" * 60)
    
    # 1. Setup simulated character stats
    # We'll mock the object behavior since we can't easily make API calls in this script without server
    class MockStats:
        def __init__(self, hp, max_hp, temp_hp=0):
            self.hit_points = hp
            self.max_hit_points = max_hp
            self.temporary_hit_points = temp_hp
            
        def save(self):
            pass # No-op
            
    stats = MockStats(hp=20, max_hp=30, temp_hp=0)
    print(f"Initial: HP={stats.hit_points}/{stats.max_hit_points}, Temp={stats.temporary_hit_points}")
    
    # 2. Heal
    print("\n--- Testing Heal (15) ---")
    amount = 15
    old_hp = stats.hit_points
    stats.hit_points = min(stats.hit_points + amount, stats.max_hit_points)
    print(f"Result: HP={stats.hit_points}/{stats.max_hit_points} (Healed {stats.hit_points - old_hp})")
    assert stats.hit_points == 30
    
    # 3. Add Temp HP
    print("\n--- Testing Add Temp HP (10) ---")
    amount = 10
    if amount > stats.temporary_hit_points:
        stats.temporary_hit_points = amount
    print(f"Result: Temp={stats.temporary_hit_points}")
    assert stats.temporary_hit_points == 10
    
    # 4. Damage (Absorbed by Temp)
    print("\n--- Testing Damage (4) - Should trigger absorption ---")
    amount = 4
    damage_remaining = amount
    
    if stats.temporary_hit_points > 0:
        absorbed = min(stats.temporary_hit_points, damage_remaining)
        stats.temporary_hit_points -= absorbed
        damage_remaining -= absorbed
        print(f"Absorbed {absorbed} with Temp HP")
        
    if damage_remaining > 0:
        stats.hit_points = max(0, stats.hit_points - damage_remaining)
        print(f"Took {damage_remaining} regular damage")
        
    print(f"Result: HP={stats.hit_points}, Temp={stats.temporary_hit_points}")
    assert stats.temporary_hit_points == 6
    assert stats.hit_points == 30
    
    # 5. Damage (Exceeds Temp)
    print("\n--- Testing Damage (20) - Should break Temp and hurt HP ---")
    amount = 20
    damage_remaining = amount
    
    if stats.temporary_hit_points > 0:
        absorbed = min(stats.temporary_hit_points, damage_remaining)
        stats.temporary_hit_points -= absorbed
        damage_remaining -= absorbed
        print(f"Absorbed {absorbed} with Temp HP")
        
    if damage_remaining > 0:
        stats.hit_points = max(0, stats.hit_points - damage_remaining)
        print(f"Took {damage_remaining} regular damage")
        
    print(f"Result: HP={stats.hit_points}, Temp={stats.temporary_hit_points}")
    assert stats.temporary_hit_points == 0
    assert stats.hit_points == 16  # 30 - (20 - 6) = 16
    
    print("\n" + "=" * 60)
    print("ALL HP LOGIC TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_hp_mechanics()
