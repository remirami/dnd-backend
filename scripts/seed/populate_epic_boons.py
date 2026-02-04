import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Feat

def populate_epic_boons():
    epic_boons = [
        {
            "name": "Boon of Combat Prowess",
            "description": "When you miss with a melee weapon attack, you can choose to hit instead. Once you use this boon, you can't use it again until you finish a short rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Dimensional Travel",
            "description": "As an action, you can cast the Misty Step spell, without using a spell slot or any components. You can use this boon once per short rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Energy Resistance",
            "description": "You gain resistance to one type of damage of your choice: acid, cold, fire, lightning, necrotic, poison, psychic, radiant, or thunder. You can change this choice whenever you finish a short rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Fate",
            "description": "When another creature that you can see within 60 feet of you makes an ability check, an attack roll, or a saving throw, you can roll a d10 and apply the result as a bonus or penalty to the roll. Once you use this boon, you can't use it again until you finish a short rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Fortitude",
            "description": "Your hit point maximum increases by 40.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Irresistible Offense",
            "description": "You can bypass the damage resistances of any creature.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Recovery",
            "description": "You can use a bonus action to regain a number of hit points equal to half your hit point maximum. Once you use this boon, you can't use it again until you finish a long rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Speed",
            "description": "Your walking speed increases by 30 feet. In addition, you can use a bonus action to take the Dash or Disengage action.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Spell Recall",
            "description": "You can cast any spell you know or have prepared without expending a spell slot. Once you use this boon, you can't use it again until you finish a long rest.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of the Night Spirit",
            "description": "While you are in dim light or darkness, you can become invisible as an action. You remain invisible until you make an attack, cast a spell, or are in bright light.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Truesight",
            "description": "You have truesight out to a range of 60 feet.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Undetectability",
            "description": "You gain a +10 bonus to Dexterity (Stealth) checks, and you can't be detected by magical sensors.",
            "minimum_level": 19,
            "source": "SRD 5.2"
        }
    ]

    created_count = 0
    updated_count = 0

    print("Populating Epic Boons...")
    
    for boon_data in epic_boons:
        feat, created = Feat.objects.update_or_create(
            name=boon_data['name'],
            defaults={
                'description': boon_data['description'],
                'minimum_level': boon_data['minimum_level'],
                'source': boon_data['source'],
                'strength_requirement': 0,
                'dexterity_requirement': 0,
                'constitution_requirement': 0,
                'intelligence_requirement': 0,
                'wisdom_requirement': 0,
                'charisma_requirement': 0,
            }
        )
        
        if created:
            created_count += 1
            print(f"Created: {feat.name}")
        else:
            updated_count += 1
            print(f"Updated: {feat.name}")

    print(f"\nDone! Created {created_count} new boons, updated {updated_count} existing boons.")

if __name__ == "__main__":
    populate_epic_boons()
