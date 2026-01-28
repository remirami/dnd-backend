import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterRace

def seed_species():
    print("Seeding 2024 Core Species...")
    
    # 2024 Species List (Standard PHB 2024 line-up)
    # Note: No ASIs (handled by Backgrounds).
    species_list = [
        {
            "name": "Elf (2024)",
            "description": "Magical people of otherworldly grace, living in the world but not entirely part of it.",
            "speed": 30
        },
        {
            "name": "Dwarf (2024)",
            "description": "Solid and enduring like the mountains they love, weathering the passage of centuries.",
            "speed": 30
        },
        {
            "name": "Halfling (2024)",
            "description": "The isolated comforts of home are the goals of most halflings' lives.",
            "speed": 30
        },
        {
            "name": "Gnome (2024)",
            "description": "A constant hum of busy activity requires gnomes to have an unquenchable zest for life.",
            "speed": 30
        },
        {
            "name": "Dragonborn (2024)",
            "description": "Born of dragons, as their name proclaims, these folk walk proudly through a world that greets them with fearful incomprehension.",
            "speed": 30
        },
        {
            "name": "Tiefling (2024)",
            "description": "To be greeted with stares and whispers, to suffer violence and insult on the street, to see mistrust and fear in every eye: this is the lot of the tiefling.",
            "speed": 30
        },
        {
            "name": "Orc (2024)",
            "description": "Orcs live a life of wandering, often in groups called tribes.",
            "speed": 30
        },
        {
            "name": "Goliath (2024)",
            "description": "Strong and reclusive, every day brings a new challenge to a goliath.",
            "speed": 30
        },
        {
            "name": "Aasimar (2024)",
            "description": "Aasimar are placed in the world to serve as guardians of law and good.",
            "speed": 30
        }
    ]

    count = 0
    for s in species_list:
        race, created = CharacterRace.objects.get_or_create(
            name=s['name'],
            defaults={
                'description': s['description'],
                'speed': s['speed'],
                'ability_score_increases': '', # Explicitly empty for 2024
                'source_ruleset': '2024'
            }
        )
        if created:
            print(f"Created {s['name']}")
            count += 1
        else:
            # Update to ensure correctness
            race.source_ruleset = '2024'
            race.ability_score_increases = ''
            race.speed = s['speed']
            race.save()
            print(f"Updated {s['name']}")
            
    print(f"Seeding Complete. {count} new species created.")

if __name__ == '__main__':
    seed_species()
