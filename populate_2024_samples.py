import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterRace, CharacterBackground

def populate_2024_data():
    print("Populating 2024 Sample Data...")
    
    # 1. Human (2024 Species)
    # Note: 2024 Humans get NO ability score increases from Species.
    # They get "Resourceful" (Heroic Inspiration) and "Skillful" (Skill + Origin Feat)
    human_2024, created = CharacterRace.objects.get_or_create(
        name='human_2024',
        defaults={
            'source_ruleset': '2024',
            'size': 'M',
            'speed': 30,
            'ability_score_increases': '', # NO ASI
            'traits': [
                {"name": "Resourceful", "description": "You gain Heroic Inspiration whenever you finish a Long Rest."},
                {"name": "Skillful", "description": "You gain proficiency in one Skill of your choice and one Origin Feat of your choice."}
            ],
            'description': "Humans (2024 Rules) are versatile and adaptable."
        }
    )
    if created:
        print("Created Species: Human (2024)")
    else:
        print("Species Human (2024) already exists.")

    # 2. Farmer (2024 Background)
    # Grants: Str/Con/Wis ASI, Tough Feat, Animal Handling, Nature
    farmer_2024, created = CharacterBackground.objects.get_or_create(
        name='farmer_2024',
        defaults={
            'source_ruleset': '2024',
            'skill_proficiencies': 'Animal Handling,Nature',
            'tool_proficiencies': 'Carpenter\'s Tools,Woodcarver\'s Tools', # Example
            'ability_score_options': {
                'options': ['+2/+1', '+1/+1/+1'],
                'stats': ['STR', 'CON', 'WIS']
            },
            'feature_name': 'Origin Feat: Tough',
            'feature_description': 'You gain the Tough feat.',
            'description': 'You grew up close to the land...'
        }
    )
    if created:
        print("Created Background: Farmer (2024)")
    else:
        print("Background Farmer (2024) already exists.")

if __name__ == '__main__':
    populate_2024_data()
