
import os
import django
import sys

sys.path.append('c:/dnd-backend/dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from items.models import Item

print("Checking Packs in Database...")
packs = Item.objects.filter(name__icontains='Pack')
for p in packs:
    print(f"Found: {p.name} ({p.category}) - {p.description[:50]}...")
