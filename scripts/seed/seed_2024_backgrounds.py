import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterBackground

def seed_backgrounds():
    print("Seeding 2024 Backgrounds (SRD 5.2 Strict)...")
    
    # 2024 Backgrounds (SRD 5.2 Only)
    # Acolyte, Criminal, Sage, Soldier
    
    backgrounds = [
        {
            "name": "Acolyte",
            "description": "You devoted yourself to service in a temple to a god or a pantheon of gods.",
            "asi_stats": ["Intelligence", "Wisdom", "Charisma"],
            "feat": "Magic Initiate", 
            "skill_proficiencies": "Insight, Religion"
        },
        {
            "name": "Criminal",
            "description": "You broke the law and survived by your wits.",
            "asi_stats": ["Dexterity", "Constitution", "Intelligence"],
            "feat": "Alert",
            "skill_proficiencies": "Sleight of Hand, Stealth"
        },
        {
            "name": "Sage",
            "description": "You spent your years learning the lore of the multiverse.",
            "asi_stats": ["Constitution", "Intelligence", "Wisdom"],
            "feat": "Magic Initiate",
            "skill_proficiencies": "Arcana, History"
        },
        {
            "name": "Soldier",
            "description": "You began your career as a warrior.",
            "asi_stats": ["Strength", "Dexterity", "Constitution"],
            "feat": "Savage Attacker",
            "skill_proficiencies": "Athletics, Intimidation"
        }
    ]

    count = 0
    for bg in backgrounds:
        json_config = {
            "stats": bg['asi_stats'],
            "options": ["+2/+1", "+1/+1/+1"],
            "feat": bg['feat']
        }
        
        obj, created = CharacterBackground.objects.update_or_create(
            name=bg['name'],
            defaults={
                'description': bg['description'],
                'skill_proficiencies': bg['skill_proficiencies'],
                'source_ruleset': '2024',
                'ability_score_options': json_config
            }
        )
        if created:
            count += 1
            print(f"Created {bg['name']}")
        else:
            print(f"Updated {bg['name']}")
            
    print(f"Seeding Complete. {count} new backgrounds created.")

if __name__ == '__main__':
    seed_backgrounds()
