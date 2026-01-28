import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterRace

def cleanup_races():
    print("Inspecting Races...")
    races = CharacterRace.objects.all()
    for r in races:
        print(f"ID: {r.id} | Name: {r.name} | Ruleset: {r.source_ruleset}")
        
    # Delete 'human_2024' if it exists (the one with snake_case)
    # The screenshot showed 'human_2024'.
    bad_races = CharacterRace.objects.filter(name='human_2024')
    if bad_races.exists():
        print(f"Found {bad_races.count()} bad 'human_2024' entries.")
        target_race = CharacterRace.objects.filter(name='Human (2024)').first()
        
        if target_race:
             for bad in bad_races:
                 # Reassign characters
                 from characters.models import Character
                 chars = Character.objects.filter(race=bad)
                 print(f"Reassigning {chars.count()} characters from {bad.name} to {target_race.name}...")
                 chars.update(race=target_race)
                 
                 # Now delete
                 print(f"Deleting {bad.name}...")
                 bad.delete()
        else:
             print("Cannot delete human_2024 because Human (2024) is missing!")
    else:
        print("No 'human_2024' found.")

    # Also check if we have multiple 'Human (2024)'
    humans_24 = CharacterRace.objects.filter(name='Human (2024)')
    if humans_24.count() > 1:
        print(f"Found {humans_24.count()} 'Human (2024)' entries. Keeping only one.")
        # Keep the first one, delete others
        first = humans_24.first()
        humans_24.exclude(id=first.id).delete()
        print("Duplicates deleted.")
        
    print("Cleanup Complete.")

if __name__ == '__main__':
    cleanup_races()
