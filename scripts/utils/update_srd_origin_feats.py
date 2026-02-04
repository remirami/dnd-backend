import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import Feat

def update_origin_feats():
    print("Enforcing Strict SRD 5.2 Origin Feats...")

    # 1. The Allowed List with Exact Descriptions
    allowed_feats = {
        "Alert": """Initiative Proficiency. When you roll Initiative, you can add your Proficiency Bonus to the roll.
Initiative Swap. Immediately after you roll Initiative, you can swap your Initiative with the Initiative of one willing ally in the same combat. You can't make this swap if you or the ally has the Incapacitated condition.""",

        "Magic Initiate": """Two Cantrips. You learn two cantrips of your choice from the Cleric, Druid, or Wizard spell list. Intelligence, Wisdom, or Charisma is your spellcasting ability for this feat's spells (choose when you select this feat).
Level 1 Spell. Choose a level 1 spell from the same list you selected for this feat's cantrips. You always have that spell prepared. You can cast it once without a spell slot, and you regain the ability to cast it in that way when you finish a Long Rest. You can also cast the spell using any spell slots you have.
Spell Change. Whenever you gain a new level, you can replace one of the spells you chose for this feat with a different spell of the same level from the chosen spell list.
Repeatable. You can take this feat more than once, but you must choose a different spell list each time.""",

        "Savage Attacker": """You've trained to deal particularly damaging strikes. Once per turn when you hit a target with a weapon, you can roll the weapon's damage dice twice and use either roll against the target.""",

        "Skilled": """You gain proficiency in any combination of three skills or tools of your choice.
Repeatable. You can take this feat more than once."""
    }

    # 2. Update/Create the Allowed Feats
    for name, description in allowed_feats.items():
        feat, created = Feat.objects.update_or_create(
            name=name,
            defaults={
                'description': description,
                'category': 'origin',
                'source': 'SRD 5.2',
                'minimum_level': 1
            }
        )
        action = "Created" if created else "Updated"
        print(f"{action} Allowed Feat: {name}")

    # 3. Delete disallowed Origin Feats
    # We delete anything with category='origin' that is NOT in the allowed list
    disallowed = Feat.objects.filter(category='origin').exclude(name__in=allowed_feats.keys())
    
    if disallowed.exists():
        count = disallowed.count()
        names = list(disallowed.values_list('name', flat=True))
        disallowed.delete()
        print(f"Deleted {count} disallowed Origin features: {names}")
    else:
        print("No disallowed Origin features found.")

    # 4. Handle 'Tough' specifically if it wasn't categorized as Origin but exists
    # If the user wants it removed from "Feats" entirely if not in list:
    # "Remove those that are not in this list from the database from feats"
    # So we check ANY feat that isn't in our allowed list (excluding Epic Boons maybe?)
    # Evaluating user intent: "These are the Origin Feats... Remove those that are not in this list"
    # Likely meaning remove other Origin Feat candidates.
    # I will stick to deleting category='origin' to be safe, but also check for the specific ones I added earlier like 'Tough' even if categorised differently.
    
    specific_removals = ['Crafter', 'Healer', 'Lucky', 'Musician', 'Tavern Brawler', 'Tough']
    for name in specific_removals:
        if name not in allowed_feats: # Just to be safe
             Feat.objects.filter(name=name).delete()
             # print(f"Ensured deletion of: {name}")

if __name__ == "__main__":
    update_origin_feats()
