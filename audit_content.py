
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from bestiary.models import Enemy
from spells.models import Spell
from characters.models import CharacterRace, CharacterClass, Character

# SRD Violations Blacklist (Non-SRD / Product Identity)
BLACKLIST_MONSTERS = [
    "Beholder", "Mind Flayer", "Illithid", "Carrion Crawler", 
    "Displacer Beast", "Githyanki", "Githzerai", "Kuo-toa", 
    "Slaad", "Umber Hulk", "Yuan-ti", "Yuan-ti Abomination", "Yuan-ti Malison"
]

BLACKLIST_RACES = [
    "Tortle", "Tabaxi", "Gith", "Aarakocra", "Genasi", "Goliath", "Aasimar", "Firbolg", "Kenku"
    # Note: Some of these are in SRD 5.1 (e.g. Deep Gnome is Svirfneblin, but name is protected?)
    # Actually most non-PHB races are not in SRD.
]

BLACKLIST_SPELL_TERMS = [
    "Mordenkainen", "Tasha", "Xanathar", "Bigby", "Evard", "Hadar", "Hunger of Hadar", "Arms of Hadar",
    "Agannazar", "Aganazzar", "Melf", "Rary", "Snilloc", "Tenser", "Jim's", "Acquisitions Incorporated"
]

def audit():
    print("------- SRD COMPLIANCE AUDIT -------")
    
    # Check Monsters
    print("\n[Scanning Monsters...]")
    violations = 0
    for name in BLACKLIST_MONSTERS:
        count = Enemy.objects.filter(name__icontains=name).count()
        if count > 0:
            print(f"!! VIOLATION: Found {count} instances of '{name}'")
            violations += count
            
    # Check Races
    print("\n[Scanning Races...]")
    for name in BLACKLIST_RACES:
        count = CharacterRace.objects.filter(name__icontains=name).count()
        if count > 0:
            print(f"!! VIOLATION: Found {count} instances of '{name}'")
            violations += 1

    # Check Spells
    print("\n[Scanning Spells...]")
    for term in BLACKLIST_SPELL_TERMS:
        # Spells like "Bigby's Hand" are usually "Arcane Hand" in SRD.
        # Open5e usually scrubs them, but let's check.
        found_spells = Spell.objects.filter(name__icontains=term)
        for spell in found_spells:
            print(f"!! VIOLATION: Spell '{spell.name}' contains '{term}'")
            violations += 1
            
    if violations == 0:
        print("\n✅ CLEAN SCAN: No obvious violations found based on blacklist.")
    else:
        print(f"\n❌ FAILED: Found {violations} potential violations.")

if __name__ == "__main__":
    audit()
