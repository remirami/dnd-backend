import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterBackground

def seed_backgrounds():
    print("Seeding 2024 Backgrounds...")
    
    # 1. Cleanup bad data
    bad_bg = CharacterBackground.objects.filter(name='farmer_2024')
    if bad_bg.exists():
        print(f"Deleting {bad_bg.count()} 'farmer_2024' entries...")
        bad_bg.delete()

    # 2. Define 2024 Backgrounds
    # Source: SRD 5.2 / 2024 PHB Rules
    # Note: ASIs are just stats array. "Feat" is the Origin Feat name.
    
    backgrounds = [
        {
            "name": "Acolyte",
            "description": "You devoted yourself to service in a temple to a god or a pantheon of gods.",
            "asi_stats": ["Intelligence", "Wisdom", "Charisma"],
            "feat": "Magic Initiate (Cleric)",
            "skill_proficiencies": "Insight, Religion"
        },
        {
            "name": "Artisan",
            "description": "You began your adult life as an apprentice to a shopkeeper or artisan.",
            "asi_stats": ["Strength", "Dexterity", "Intelligence"],
            "feat": "Crafter",
            "skill_proficiencies": "Investigation, Persuasion"
        },
        {
            "name": "Charlatan",
            "description": "You know how to get people to believe what isn't true.",
            "asi_stats": ["Dexterity", "Constitution", "Charisma"],
            "feat": "Skilled",
            "skill_proficiencies": "Deception, Sleight of Hand"
        },
        {
            "name": "Criminal",
            "description": "You broke the law and survived by your wits.",
            "asi_stats": ["Dexterity", "Constitution", "Intelligence"],
            "feat": "Alert",
            "skill_proficiencies": "Sleight of Hand, Stealth"
        },
        {
            "name": "Entertainer",
            "description": "You thrived in front of an audience.",
            "asi_stats": ["Strength", "Dexterity", "Charisma"],
            "feat": "Musician",
            "skill_proficiencies": "Acrobatics, Performance"
        },
        {
            "name": "Farmer",
            "description": "You grew up close to the land.",
            "asi_stats": ["Strength", "Constitution", "Wisdom"],
            "feat": "Tough",
            "skill_proficiencies": "Animal Handling, Nature"
        },
        {
            "name": "Guard",
            "description": "You earned your living by protecting the community.",
            "asi_stats": ["Strength", "Intelligence", "Wisdom"],
            "feat": "Alert",
            "skill_proficiencies": "Athletics, Perception"
        },
        {
            "name": "Guide",
            "description": "You spent your youth in the outdoors, leading others through the wilderness.",
            "asi_stats": ["Dexterity", "Constitution", "Wisdom"],
            "feat": "Magic Initiate (Druid)",
            "skill_proficiencies": "Stealth, Survival"
        },
        {
            "name": "Hermit",
            "description": "You spent your early years in seclusion.",
            "asi_stats": ["Constitution", "Wisdom", "Charisma"],
            "feat": "Healer",
            "skill_proficiencies": "Medicine, Religion"
        },
        {
            "name": "Merchant",
            "description": "You apprenticed with a guild or a business.",
            "asi_stats": ["Constitution", "Intelligence", "Charisma"],
            "feat": "Lucky",
            "skill_proficiencies": "Animal Handling, Persuasion"
        },
        {
            "name": "Noble",
            "description": "You were raised in a family of wealth, power, and privilege.",
            "asi_stats": ["Strength", "Intelligence", "Charisma"],
            "feat": "Skilled",
            "skill_proficiencies": "History, Persuasion"
        },
        {
            "name": "Sage",
            "description": "You spent your years learning the lore of the multiverse.",
            "asi_stats": ["Constitution", "Intelligence", "Wisdom"],
            "feat": "Magic Initiate (Wizard)",
            "skill_proficiencies": "Arcana, History"
        },
        {
            "name": "Sailor",
            "description": "You sailed on a seagoing vessel for years.",
            "asi_stats": ["Strength", "Dexterity", "Wisdom"],
            "feat": "Tavern Brawler",
            "skill_proficiencies": "Acrobatics, Perception"
        },
        {
            "name": "Scribe",
            "description": "You were a writer, a copyist, or a record keeper.",
            "asi_stats": ["Dexterity", "Intelligence", "Wisdom"],
            "feat": "Skilled",
            "skill_proficiencies": "Investigation, Perception"
        },
        {
            "name": "Soldier",
            "description": "You began your career as a warrior.",
            "asi_stats": ["Strength", "Dexterity", "Constitution"],
            "feat": "Savage Attacker",
            "skill_proficiencies": "Athletics, Intimidation"
        },
        {
            "name": "Wayfarer",
            "description": "You grew up wandering the roads.",
            "asi_stats": ["Dexterity", "Wisdom", "Charisma"],
            "feat": "Lucky",
            "skill_proficiencies": "Insight, Stealth"
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
