import os
import django
import time
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Character

def monitor_creations():
    print("=== Monitoring for New Characters ===")
    print("Keep this script running and go create a character in the browser.")
    
    last_count = Character.objects.count()
    print(f"Current Character Count: {last_count}")
    
    try:
        while True:
            current_count = Character.objects.count()
            if current_count > last_count:
                # New character found!
                new_char = Character.objects.last()
                print(f"\n[NEW DETECTED] {datetime.now()}")
                print(f"Name: {new_char.name}")
                print(f"Class: {new_char.character_class.name if new_char.character_class else 'None'}")
                print(f"Level: {new_char.level}")
                
                # Check Slots
                slots = new_char.stats.spell_slots
                print(f"Initial Spell Slots: {slots}")
                
                if slots == {}:
                    print(">>> CRITICAL FAILURE: Spell Slots are EMPTY.")
                    print(">>> This means the server created the character using OLD CODE.")
                    print(">>> Resolution: You MUST restart the server process that is handling API requests.")
                else:
                    print(">>> SUCCESS: Spell Slots are populated correctly.")
                    print(">>> If the frontend still shows defaults, try Hard Refresh (Ctrl+F5).")
                
                last_count = current_count
                
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping monitor.")

if __name__ == '__main__':
    monitor_creations()
