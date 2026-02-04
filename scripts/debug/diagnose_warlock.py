import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character, CharacterClass
from campaigns.utils import calculate_spell_slots, SPELL_SLOT_TABLES

def diagnose():
    print("--- Diagnosing Warlock Slot Calculation ---")
    
    # Check Class Name in DB
    try:
        w_class = CharacterClass.objects.filter(name__icontains='warlock').first()
        print(f"DB Class: '{w_class.name}' (ID: {w_class.id})")
    except Exception as e:
        print(f"Error finding Warlock class: {e}")
        return

    # Check Table Key
    print(f"Table Keys: {list(SPELL_SLOT_TABLES.keys())}")
    print(f"Has 'warlock'? {'warlock' in SPELL_SLOT_TABLES}")
    print(f"Has 'Warlock'? {'Warlock' in SPELL_SLOT_TABLES}")
    
    # Test Calculation
    levels = [1, 2, 3, 4, 5, 6, 7, 8]
    for lvl in levels:
        slots_lower = calculate_spell_slots('warlock', lvl)
        slots_cap = calculate_spell_slots('Warlock', lvl)
        slots_db = calculate_spell_slots(w_class.name, lvl)
        print(f"Lvl {lvl}: lower={slots_lower}, cap={slots_cap}, db='{w_class.name}'->{slots_db}")

    # Inspect "sdfsdfsdf"
    char = Character.objects.filter(name__icontains='sdfsdfsdf').last()
    if char:
        print(f"\nCharacter '{char.name}' (Lvl {char.level} {char.character_class.name})")
        print(f"  Current Slots: {char.stats.spell_slots}")
        
        # Try to fix
        new_slots = calculate_spell_slots(char.character_class.name, char.level)
        print(f"  Re-calculated: {new_slots}")
        
        if new_slots and new_slots != char.stats.spell_slots:
            print("  Applying fix...")
            char.stats.spell_slots = new_slots
            char.stats.save()
            
            # Fix pending
            max_level = 0
            for lvl_key, count in new_slots.items():
                if count > 0:
                     max_level = max(max_level, int(lvl_key))
            
            pending = char.pending_spell_choices
            if pending:
                pending['max_level'] = max_level
                char.pending_spell_choices = pending
                char.save()
                print(f"  Fixed Pending Max Level to {max_level}")
    else:
        print("\nCharacter 'sdfsdfsdf' not found.")

if __name__ == '__main__':
    diagnose()
