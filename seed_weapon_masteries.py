import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from items.models import Weapon

def seed_weapon_masteries():
    print("Seeding Weapon Mastery Properties (2024 Rules)...")
    
    mastery_map = {
        'Cleave': ['Greataxe', 'Halberd'],
        'Graze': ['Glaive', 'Greatsword'],
        'Nick': ['Dagger', 'Light Hammer', 'Scimitar', 'Sickle'],
        'Push': ['Greatclub', 'Heavy Crossbow', 'Pike', 'Warhammer'],
        'Sap': ['Flail', 'Mace', 'Morningstar', 'War Pick'],
        'Slow': ['Club', 'Javelin', 'Light Crossbow', 'Longbow', 'Musket', 'Sling', 'Whip'],
        'Topple': ['Battleaxe', 'Lance', 'Maul', 'Quarterstaff', 'Trident'],
        'Vex': ['Blowgun', 'Dart', 'Hand Crossbow', 'Handaxe', 'Pistol', 'Rapier', 'Shortbow', 'Shortsword']
    }
    
    updated_count = 0
    not_found = []

    for property_name, weapon_names in mastery_map.items():
        for weapon_name in weapon_names:
            # Case insensitive search
            weapons = Weapon.objects.filter(name__iexact=weapon_name)
            if weapons.exists():
                for weapon in weapons:
                    weapon.mastery_property = property_name
                    weapon.save()
                    updated_count += 1
                    print(f"Updated {weapon.name}: {property_name}")
            else:
                not_found.append(weapon_name)
                
    print(f"\nSeeding Complete. Updated {updated_count} weapons.")
    if not_found:
        print(f"Warning: The following weapons were not found in the database: {', '.join(not_found)}")

if __name__ == "__main__":
    seed_weapon_masteries()
