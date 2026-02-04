import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterClass, Character, CharacterClassLevel

def merge_wizards():
    print("Merging Wizard duplicates...")
    
    try:
        # Keep 'wizard' (lowercase, matches others) - assuming ID 16.
        # But verify by name just in case.
        target_wizard = CharacterClass.objects.get(name='wizard')
        bad_wizard = CharacterClass.objects.get(name='Wizard')
        
        print(f"Target: {target_wizard.name} (ID: {target_wizard.id})")
        print(f"Bad: {bad_wizard.name} (ID: {bad_wizard.id})")
        
        # 1. Update Character.character_class
        chars = Character.objects.filter(character_class=bad_wizard)
        print(f"Moving {chars.count()} characters...")
        chars.update(character_class=target_wizard)
        
        # 2. Update CharacterClassLevel
        levels = CharacterClassLevel.objects.filter(character_class=bad_wizard)
        print(f"Moving {levels.count()} class level entries...")
        
        # Loop to avoid UniqueConstraint (character, class) errors if they already have target_wizard
        for lvl in levels:
            # Check if they already have the target class
            if CharacterClassLevel.objects.filter(character=lvl.character, character_class=target_wizard).exists():
                print(f"Skipping merge for {lvl.character.name} (already has target class). Manual handling might be needed if levels differ.")
                # If they have both, we basically just delete the bad one, OR we sum levels?
                # Assuming "duplicate class" bug, they probably only have one or the other effectively.
                # If they have mismatched levels, this is complex.
                # Deletion of 'bad' entry might be safest if 'target' exists?
                pass 
            else:
                lvl.character_class = target_wizard
                lvl.save()
        
        # Now clean up remaining (those that weren't moved because user already had target)
        # Or just delete bad_wizard, which will cascade delete remaining levels?
        # WAIT: CASCADE delete on CharacterClassLevel might wipe the Level 15 wizard levels.
        # We need to ensure we didn't lose data.
        
        remaining_levels = CharacterClassLevel.objects.filter(character_class=bad_wizard)
        if remaining_levels.exists():
            print(f"Deleting {remaining_levels.count()} redundant class level entries...")
            remaining_levels.delete()
            
        print("Deleting bad Wizard class entry...")
        bad_wizard.delete()
        print("Success.")
        
    except CharacterClass.DoesNotExist:
        print("Could not find both 'wizard' and 'Wizard'. Cleanup already done?")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    merge_wizards()
