import os
import sys

import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterRace


def seed_species():
    print("Seeding 2024 Core Species with complete traits...")
    
    species_list = [
        {
            "name": "Human (2024)",
            "description": "Versatile and ambitious, humans are innovators and explorers who adapt swiftly to any challenge.",
            "speed": 30,
            "size": "M",
            "traits": [
                {"name": "Resourceful", "description": "You gain Heroic Inspiration whenever you finish a Long Rest."},
                {"name": "Skillful", "description": "You gain proficiency in one skill of your choice."},
                {"name": "Versatile", "description": "You gain the Origin Feat of your choice at character creation."}
            ]
        },
        {
            "name": "Elf (2024)",
            "description": "Magical people of otherworldly grace, living in the world but not entirely part of it.",
            "speed": 30,
            "size": "M",
            "skill_proficiencies": "Perception",
            "traits": [
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions (60 ft.)."},
                {"name": "Elven Lineage", "description": "You inherit arcane heritage (Drow, High Elf, or Wood Elf) with supernatural spells or enhanced speed."},
                {"name": "Fey Ancestry", "description": "You have advantage on saving throws against being charmed, and magic can't put you to sleep."},
                {"name": "Keen Senses", "description": "You have proficiency in the Perception skill."},
                {"name": "Trance", "description": "You don't need sleep; meditatively resting for 4 hours grants the full benefits of a Long Rest."}
            ]
        },
        {
            "name": "Dwarf (2024)",
            "description": "Solid and enduring like the mountains they love, weathering the passage of centuries.",
            "speed": 30,
            "size": "M",
            "traits": [
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions with extended range (120 ft.)."},
                {"name": "Dwarven Resilience", "description": "You have resistance to poison damage and advantage on saving throws against being poisoned."},
                {"name": "Dwarven Toughness", "description": "Your hit point maximum increases by 1, and increases by 1 every time you gain a level."},
                {"name": "Stonecunning", "description": "As a bonus action, you gain tremorsense out to 60 feet for 10 minutes while on stone surfaces."}
            ]
        },
        {
            "name": "Halfling (2024)",
            "description": "The isolated comforts of home are the goals of most halflings' lives.",
            "speed": 30,
            "size": "S",
            "traits": [
                {"name": "Brave", "description": "You have advantage on saving throws against being frightened."},
                {"name": "Halfling Nimbleness", "description": "You can move through the space of any creature that is of a size larger than yours."},
                {"name": "Luck", "description": "When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and must use the new roll."},
                {"name": "Naturally Stealthy", "description": "You can attempt to hide even when obscured only by a creature at least one size larger than you."}
            ]
        },
        {
            "name": "Gnome (2024)",
            "description": "A constant hum of busy activity requires gnomes to have an unquenchable zest for life.",
            "speed": 30,
            "size": "S",
            "traits": [
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions (60 ft.)."},
                {"name": "Gnomish Cunning", "description": "You have advantage on all Intelligence, Wisdom, and Charisma saving throws against magic."},
                {"name": "Gnomish Lineage", "description": "You inherit curious lineage (Forest Gnome with illusion magic and beast speech, or Rock Gnome with clockwork tinkering)."}
            ]
        },
        {
            "name": "Dragonborn (2024)",
            "description": "Born of dragons, as their name proclaims, these folk walk proudly through a world that greets them with fearful incomprehension.",
            "speed": 30,
            "size": "M",
            "traits": [
                {"name": "Breath Weapon", "description": "Replace one attack with an exhalation of destructive energy (1d10 damage, scaling with level)."},
                {"name": "Damage Resistance", "description": "You have resistance to the damage type associated with your Draconic Ancestry."},
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions (60 ft.)."},
                {"name": "Draconic Flight", "description": "At 5th level, you can sprout spectral wings as a bonus action, gaining a fly speed equal to your speed for 10 minutes."}
            ]
        },
        {
            "name": "Tiefling (2024)",
            "description": "To be greeted with stares and whispers, to suffer violence and insult on the street, to see mistrust and fear in every eye: this is the lot of the tiefling.",
            "speed": 30,
            "size": "M",
            "traits": [
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions (60 ft.)."},
                {"name": "Fiendish Legacy", "description": "Choose Abyssal (Poison resistance), Chthonic (Necrotic resistance), or Infernal (Fire resistance) with thematic spells."},
                {"name": "Otherworldly Presence", "description": "You know the Thaumaturgy cantrip to create supernatural omens."}
            ]
        },
        {
            "name": "Orc (2024)",
            "description": "Orcs live a life of wandering, proud of their stamina, community, and ferocious willpower.",
            "speed": 30,
            "size": "M",
            "traits": [
                {"name": "Adrenaline Rush", "description": "You can take the Dash action as a bonus action, gaining temporary hit points equal to your proficiency bonus."},
                {"name": "Darkvision", "description": "You have superior vision in dark and dim conditions with extended range (120 ft.)."},
                {"name": "Relentless Endurance", "description": "When reduced to 0 hit points but not killed outright, you can drop to 1 hit point instead (once per long rest)."}
            ]
        },
        {
            "name": "Goliath (2024)",
            "description": "Strong and reclusive giants' kin, every day brings a new physical and heroic challenge to a goliath.",
            "speed": 35,
            "size": "M",
            "traits": [
                {"name": "Giant Ancestry", "description": "Supernatural lineage of giants granting supernatural boons (Cloud teleport, Fire strike, Frost chill, Hill tumble, or Stone endurance)."},
                {"name": "Large Form", "description": "Starting at level 5, you can grow to Large size for 10 minutes, gaining advantage on Strength checks and +10 ft speed."},
                {"name": "Powerful Build", "description": "You count as one size larger when determining carrying capacity and the weight you can push, drag, or lift."}
            ]
        }
    ]

    count = 0
    for s in species_list:
        race, created = CharacterRace.objects.get_or_create(
            name=s['name'],
            defaults={
                'description': s['description'],
                'speed': s['speed'],
                'size': s.get('size', 'M'),
                'traits': s.get('traits', []),
                'skill_proficiencies': s.get('skill_proficiencies', ''),
                'ability_score_increases': '', # Explicitly empty for 2024
                'source_ruleset': '2024'
            }
        )
        if created:
            print(f"Created {s['name']}")
            count += 1
        else:
            # Update to ensure correctness
            race.description = s['description']
            race.source_ruleset = '2024'
            race.ability_score_increases = ''
            race.speed = s['speed']
            race.size = s.get('size', 'M')
            race.traits = s.get('traits', [])
            race.skill_proficiencies = s.get('skill_proficiencies', '')
            race.save()
            print(f"Updated {s['name']}")
            
    print(f"Seeding Complete. {count} new species created.")

if __name__ == '__main__':
    seed_species()
