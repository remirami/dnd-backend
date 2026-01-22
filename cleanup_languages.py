
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from bestiary.models import Language

standard_languages = [
    'Common', 'Dwarvish', 'Elvish', 'Giant', 'Gnomish', 'Goblin', 'Halfling', 'Orc', 
    'Abyssal', 'Celestial', 'Draconic', 'Deep Speech', 'Infernal', 'Primordial', 'Sylvan', 'Undercommon',
    'Druidic', "Thieves' Cant"
]

print("Starting cleanup...")

# Ensure standard languages exist
for lang in standard_languages:
    Language.objects.get_or_create(name=lang)

# Identify non-standard languages
qs = Language.objects.exclude(name__in=standard_languages)
count = qs.count()
print(f"Found {count} non-standard languages to delete.")

# Delete them
if count > 0:
    print("Deleting...")
    qs.delete()
    print("Delete complete.")

# Verify
remaining = list(Language.objects.values_list('name', flat=True))
print(f"Remaining languages ({len(remaining)}): {remaining}")
