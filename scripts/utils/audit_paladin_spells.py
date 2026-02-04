import os
import django
import sys

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnd_backend.settings")
django.setup()

from spells.models import Spell
from characters.models import CharacterClass

try:
    classes = CharacterClass.objects.all()
    print(f"Found {classes.count()} classes:")
    for c in classes:
        print(f"- '{c.name}' (ID: {c.id})")

    paladin = CharacterClass.objects.filter(name__iexact='Paladin').first()
    if not paladin:
        print("Paladin class not found in database (checked case-insensitive)!")
    else:
        print(f"Found Paladin: '{paladin.name}' (ID: {paladin.id})")
        spells = Spell.objects.filter(classes=paladin)
        count = spells.count()
        print(f"Paladin Spells Count: {count}")
        
        # Check sources
        from django.db.models import Count
        sources = spells.values('source').annotate(count=Count('source'))
        print("\nSpell Sources:")
        for s in sources:
            print(f"- {s['source']}: {s['count']} spells")
            
        print("\nSample Non-SRD Spells (if any):")
        non_srd = spells.exclude(source__iexact='PHB').exclude(source__iexact='SRD')[:10]
        for s in non_srd:
            print(f"- {s.name} ({s.source})")

except Exception as e:
    print(f"Error: {e}")
