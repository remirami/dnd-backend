import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character
from campaigns.utils import calculate_spell_slots

def repair_all():
    print("Final Repair Sweep...")
    characters = Character.objects.all()
    
    for char in characters:
        if not char.character_class:
            continue

        try:
             # Just access stats to check existence
             _ = char.stats
        except:
             print(f"Skipping {char.name} (No stats)")
             continue
        
        # Calculate correct slots
        new_slots = calculate_spell_slots(char.character_class.name, char.level)
        current_slots = char.stats.spell_slots or {}
        
        if current_slots != new_slots:
            print(f"Fixing {char.name} (Lvl {char.level} {char.character_class.name}): {current_slots} -> {new_slots}")
            char.stats.spell_slots = new_slots
            char.stats.save()
            
            # Reset pending choices if seemingly broken
            pending = char.pending_spell_choices
            if pending:
                max_level = 0
                for lvl, count in new_slots.items():
                    if count > 0:
                        max_level = max(max_level, int(lvl))
                
                if pending.get('max_level', 0) < max_level:
                    print(f"  Fixing pending max_level to {max_level}")
                    pending['max_level'] = max_level
                    char.pending_spell_choices = pending
                    char.save()

if __name__ == '__main__':
    repair_all()
