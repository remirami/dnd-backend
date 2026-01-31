import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character
from campaigns.utils import calculate_spell_slots

def repair_spell_slots():
    print("Repairing spell slots for all characters...")
    characters = Character.objects.all()
    
    for char in characters:
        if not char.character_class:
            continue
            
        print(f"Processing {char.name} ({char.character_class.name} {char.level})...")
        
        # 1. Update Slots
        current_slots = char.stats.spell_slots or {}
        new_slots = calculate_spell_slots(char.character_class.name, char.level)
        
        if current_slots != new_slots:
            print(f"  Updating slots: {current_slots} -> {new_slots}")
            char.stats.spell_slots = new_slots
            char.stats.save()
            
            # 2. Fix Pending Choices
            # Trigger recalculation of pending choices if slots changed
            # This mimics the fix: using fresh slots to determine max level
            max_level = 0
            if new_slots:
                 # Calculate max level from slots
                 for lvl, count in new_slots.items():
                     if count > 0:
                         max_level = max(max_level, int(lvl))
            
            pending = char.pending_spell_choices
            if pending and pending.get('max_level', 0) < max_level:
                print(f"  Updating pending max_level: {pending.get('max_level')} -> {max_level}")
                pending['max_level'] = max_level
                char.pending_spell_choices = pending
                char.save()
        else:
            print("  Slots already correct.")

if __name__ == '__main__':
    repair_spell_slots()
