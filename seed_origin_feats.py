import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Feat

def seed_origin_feats():
    print("Seeding Origin Feats (SRD 5.2 Only)...")
    
    # EXACT SRD 5.2 TEXTS
    allowed_feats = [
        {
            "name": "Alert",
            "description": """Initiative Proficiency. When you roll Initiative, you can add your Proficiency Bonus to the roll.
Initiative Swap. Immediately after you roll Initiative, you can swap your Initiative with the Initiative of one willing ally in the same combat. You can't make this swap if you or the ally has the Incapacitated condition.""",
            "category": "origin",
            "source": "SRD 5.2"
        },
        {
            "name": "Magic Initiate",
            "description": """Two Cantrips. You learn two cantrips of your choice from the Cleric, Druid, or Wizard spell list. Intelligence, Wisdom, or Charisma is your spellcasting ability for this feat's spells (choose when you select this feat).
Level 1 Spell. Choose a level 1 spell from the same list you selected for this feat's cantrips. You always have that spell prepared. You can cast it once without a spell slot, and you regain the ability to cast it in that way when you finish a Long Rest. You can also cast the spell using any spell slots you have.
Spell Change. Whenever you gain a new level, you can replace one of the spells you chose for this feat with a different spell of the same level from the chosen spell list.
Repeatable. You can take this feat more than once, but you must choose a different spell list each time.""",
            "category": "origin",
            "source": "SRD 5.2"
        },
        {
            "name": "Savage Attacker",
            "description": """You've trained to deal particularly damaging strikes. Once per turn when you hit a target with a weapon, you can roll the weapon's damage dice twice and use either roll against the target.""",
            "category": "origin",
            "source": "SRD 5.2"
        },
        {
            "name": "Skilled",
            "description": """You gain proficiency in any combination of three skills or tools of your choice.
Repeatable. You can take this feat more than once.""",
            "category": "origin",
            "source": "SRD 5.2"
        }
    ]

    for feat_data in allowed_feats:
        Feat.objects.update_or_create(
            name=feat_data['name'],
            defaults={
                'description': feat_data['description'],
                'category': feat_data['category'],
                'source': feat_data['source'],
                'minimum_level': 1
            }
        )
        print(f"Ensured: {feat_data['name']}")

if __name__ == "__main__":
    seed_origin_feats()
