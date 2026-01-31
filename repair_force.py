import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character
from campaigns.utils import calculate_spell_slots

def repair_force():
    print("=== FORCE REPAIR ===")
    
    # 1. Fix "sdfsdfsdf" specifically (and Aasd)
    targets = Character.objects.filter(character_class__name__icontains='warlock')
    
    for char in targets:
        print(f"Checking {char.name} (Lvl {char.level})...")
        proper_slots = calculate_spell_slots(char.character_class.name, char.level)
        try:
            current_slots = char.stats.spell_slots
        except Exception:
            print(f"  Skipping (No Stats)")
            continue
        
        if current_slots != proper_slots:
            print(f"  MISMATCH! DB: {current_slots} vs CALC: {proper_slots}")
            print(f"  FIXING...")
            char.stats.spell_slots = proper_slots
            char.stats.save()
            
            # Recalculate pending max level
            max_level = 0
            for lvl, count in proper_slots.items():
                if count > 0:
                    max_level = max(max_level, int(lvl))
            
            pending = char.pending_spell_choices
            if pending:
                print(f"  Fixing Pending: {pending.get('max_level')} -> {max_level}")
                pending['max_level'] = max_level
                char.pending_spell_choices = pending
                char.save()
        else:
            print("  OK.")

if __name__ == '__main__':
    repair_force()
