import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterBackground

def update_srd_backgrounds():
    print("Enforcing Strict SRD 5.2 Backgrounds...")

    # Allowed List
    allowed_backgrounds = [
        {
            "name": "Acolyte",
            "description": "You devoted yourself to service in a temple to a god or a pantheon of gods.",
            "asi_stats": ["Intelligence", "Wisdom", "Charisma"],
            "feat": "Magic Initiate", # Generic Magic Initiate
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
            "feat": "Magic Initiate", # Generic Magic Initiate
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

    allowed_names = [bg['name'] for bg in allowed_backgrounds]

    # 1. Update/Create Allowed
    for bg in allowed_backgrounds:
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
        action = "Created" if created else "Updated"
        print(f"{action} Allowed Background: {obj.name}")

    # 2. Delete Disallowed
    # Delete all 2024 backgrounds NOT in the allowed list
    print("Finding disallowed backgrounds...")
    disallowed_bgs = CharacterBackground.objects.filter(source_ruleset='2024').exclude(name__in=allowed_names)
    
    if disallowed_bgs.exists():
        from characters.models import Character
        # Fix ProtectedError by setting character backgrounds to NULL first
        # (or we could reassign them, but NULL is safer for now)
        print("Detaching disallowed backgrounds from characters...")
        
        # We process manually to be safe or use update()
        characters_to_fix = Character.objects.filter(background__in=disallowed_bgs)
        updated_chars = characters_to_fix.update(background=None)
        print(f"Updated {updated_chars} characters to have no background.")

        deleted_count, _ = disallowed_bgs.delete()
        print(f"Deleted {deleted_count} disallowed 2024 backgrounds.")
    else:
        print("No disallowed backgrounds found.")

if __name__ == "__main__":
    update_srd_backgrounds()
