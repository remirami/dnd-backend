import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterRace, CharacterClass, CharacterBackground, Feat

def seed_2024_data():
    print("Seeding 2024 Data...")

    # 1. Species (Human 2024)
    human_24, created = CharacterRace.objects.get_or_create(
        name='Human (2024)',
        defaults={
            'description': 'Versatile and ambitious (2024 Rules).',
            'ability_score_increases': '', # NO ASI from Species
            'speed': 30,
            'source_ruleset': '2024'
        }
    )
    if created:
        print("Created Human (2024)")
    else:
        # Update just in case
        human_24.source_ruleset = '2024'
        human_24.ability_score_increases = ''
        human_24.save()
        print("Updated Human (2024)")

    # 2. Feat (Tough - for Origin Feat)
    tough, _ = Feat.objects.get_or_create(
        name='Tough',
        defaults={
            'description': 'Your hit point maximum increases.',
            'source': 'Player\'s Handbook (2024)' 
        }
    )

    # 3. Background (Farmer)
    # Options: +2/+1 or +1/+1/+1 to [Str, Con, Wis]
    farmer, created = CharacterBackground.objects.get_or_create(
        name='Farmer',
        defaults={
            'description': 'You grew up close to the land.',
            'skill_proficiencies': 'Animal Handling, Nature',
            'source_ruleset': '2024',
            'ability_score_options': {
                'stats': ['Strength', 'Constitution', 'Wisdom'],
                'options': ['+2/+1', '+1/+1/+1'],
                'feat': 'Tough'
            }
        }
    )
    if created:
        print("Created Farmer Background")
    else:
        farmer.source_ruleset = '2024'
        farmer.ability_score_options = {
            'stats': ['Strength', 'Constitution', 'Wisdom'],
            'options': ['+2/+1', '+1/+1/+1'],
            'feat': 'Tough'
        }
        farmer.save()
        print("Updated Farmer Background")

    print("Seeding Complete.")

if __name__ == '__main__':
    seed_2024_data()
