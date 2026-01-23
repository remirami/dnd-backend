
import os
import django
import sys

# Setup Django environment
sys.path.append('c:/dnd-backend/dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from items.models import Weapon

print("Checking Weapons in Database...")
weapons = Weapon.objects.all()
print(f"Total Weapons: {weapons.count()}")

for w in weapons:
    print(f"WARNING: Weapon '{w.name}' has type '{w.weapon_type}'")

simple = Weapon.objects.filter(weapon_type__startswith='simple_')
print(f"Simple Weapons count: {simple.count()}")

martial = Weapon.objects.filter(weapon_type__startswith='martial_')
print(f"Martial Weapons count: {martial.count()}")
