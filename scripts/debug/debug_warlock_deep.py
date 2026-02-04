import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass
from campaigns.utils import calculate_spell_slots, SPELL_SLOT_TABLES
import pprint

def debug_deep():
    print("=== Deep Debugging Warlocks ===")
    
    # 1. Inspect Table directly
    print("\n[1] SPELL_SLOT_TABLES['warlock']:")
    w_table = SPELL_SLOT_TABLES.get('warlock', {})
    pprint.pprint(w_table)
    
    # Check key types
    sample_keys = list(w_table.keys())[:5]
    print(f"Key Types: {[type(k) for k in sample_keys]}")

    # 2. Find High Level Warlocks
    warlocks = Character.objects.filter(character_class__name__icontains='warlock', level__gt=5)
    print(f"\n[2] Found {warlocks.count()} High Level Warlocks:")
    
    for char in warlocks:
        print(f"\n--- {char.name} (Lvl {char.level}) ---")
        print(f"Class: '{char.character_class.name}' (ID: {char.character_class.id})")
        
        # Current DB Slots
        db_slots = char.stats.spell_slots
        print(f"Current DB Slots: {db_slots}")
        
        # Calculated Slots
        calc_slots = calculate_spell_slots(char.character_class.name, char.level)
        print(f"Calculated Slots: {calc_slots}")
        
        # Comparison
        if db_slots != calc_slots:
            print("MISMATCH DETECTED!")
            # Attempt repair?
        else:
            print("Matches calculation.")
            
        # Check Pending Trigger
        # If slots are Level 3 (e.g. {'3': 2}) but level is 17...
        # Check what MAX level is derived
        max_level = 0
        if db_slots:
            for lvl, count in db_slots.items():
                if count > 0:
                    max_level = max(max_level, int(lvl))
        print(f"Max Level from DB Slots: {max_level}")
        
        pending = char.pending_spell_choices
        print(f"Pending Choices: {pending}")

if __name__ == '__main__':
    debug_deep()
