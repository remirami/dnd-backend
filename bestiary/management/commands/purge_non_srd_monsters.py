"""
Purge non-SRD monsters from the database.

Uses a hardcoded list of SRD 5.1 monster names (from 5thsrd.org) as the
authoritative reference, then deletes any monsters not on that list.
"""
from django.core.management.base import BaseCommand
from bestiary.models import Enemy


# Complete SRD 5.1 monster list from https://5thsrd.org/gamemaster_rules/monster_indexes/monsters_by_name/
SRD_MONSTER_NAMES = {
    # A
    "Aboleth", "Acolyte", "Adult Black Dragon", "Adult Blue Dragon",
    "Adult Brass Dragon", "Adult Bronze Dragon", "Adult Copper Dragon",
    "Adult Gold Dragon", "Adult Green Dragon", "Adult Red Dragon",
    "Adult Silver Dragon", "Adult White Dragon", "Air Elemental",
    "Ancient Black Dragon", "Ancient Blue Dragon", "Ancient Brass Dragon",
    "Ancient Bronze Dragon", "Ancient Copper Dragon", "Ancient Gold Dragon",
    "Ancient Green Dragon", "Ancient Red Dragon", "Ancient Silver Dragon",
    "Ancient White Dragon", "Androsphinx", "Animated Armor", "Ankheg",
    "Ape", "Archmage", "Assassin", "Awakened Shrub", "Awakened Tree",
    "Axe Beak", "Azer",
    # B
    "Baboon", "Badger", "Balor", "Bandit", "Bandit Captain", "Barbed Devil",
    "Basilisk", "Bat", "Bearded Devil", "Behir", "Berserker",
    "Black Dragon Wyrmling", "Black Pudding", "Black Bear", "Blink Dog",
    "Blood Hawk", "Blue Dragon Wyrmling", "Boar", "Bone Devil",
    "Brass Dragon Wyrmling", "Bronze Dragon Wyrmling", "Brown Bear",
    "Bugbear", "Bulette",
    # C
    "Camel", "Cat", "Centaur", "Chain Devil", "Chimera", "Chuul",
    "Clay Golem", "Cloaker", "Cloud Giant", "Cockatrice", "Commoner",
    "Constrictor Snake", "Copper Dragon Wyrmling", "Couatl", "Crab",
    "Crocodile", "Cult Fanatic", "Cultist",
    # D
    "Darkmantle", "Death Dog", "Deer", "Deva", "Dire Wolf", "Djinni",
    "Doppelganger", "Draft Horse", "Dragon Turtle", "Dretch", "Drider",
    "Druid", "Dryad", "Duergar", "Dust Mephit",
    # E
    "Eagle", "Earth Elemental", "Efreeti", "Elephant", "Elf, Drow", "Elk",
    "Erinyes", "Ettercap", "Ettin",
    # F
    "Fire Elemental", "Fire Giant", "Flesh Golem", "Flying Snake",
    "Flying Sword", "Frog", "Frost Giant",
    # G
    "Gargoyle", "Gelatinous Cube", "Ghast", "Ghost", "Ghoul", "Giant Ape",
    "Giant Badger", "Giant Bat", "Giant Boar", "Giant Centipede",
    "Giant Constrictor Snake", "Giant Crab", "Giant Crocodile", "Giant Eagle",
    "Giant Elk", "Giant Fire Beetle", "Giant Frog", "Giant Goat",
    "Giant Hyena", "Giant Lizard", "Giant Octopus", "Giant Owl",
    "Giant Poisonous Snake", "Giant Rat", "Giant Scorpion", "Giant Sea Horse",
    "Giant Shark", "Giant Spider", "Giant Toad", "Giant Vulture",
    "Giant Wasp", "Giant Weasel", "Giant Wolf Spider", "Gibbering Mouther",
    "Glabrezu", "Gladiator", "Gnoll", "Gnome, Deep (Svirfneblin)", "Goat",
    "Goblin", "Gold Dragon Wyrmling", "Gorgon", "Gray Ooze",
    "Green Dragon Wyrmling", "Green Hag", "Grick", "Griffon", "Grimlock",
    "Guard", "Guardian Naga", "Gynosphinx",
    # H
    "Half-Red Dragon Veteran", "Harpy", "Hawk", "Hell Hound", "Hezrou",
    "Hill Giant", "Hippogriff", "Hobgoblin", "Homunculus", "Horned Devil",
    "Hunter Shark", "Hydra", "Hyena",
    # I
    "Ice Devil", "Ice Mephit", "Imp", "Invisible Stalker", "Iron Golem",
    # J
    "Jackal",
    # K
    "Killer Whale", "Knight", "Kobold", "Kraken",
    # L
    "Lamia", "Lemure", "Lich", "Lion", "Lizard", "Lizardfolk",
    # M
    "Mage", "Magma Mephit", "Magmin", "Mammoth", "Manticore", "Marilith",
    "Mastiff", "Medusa", "Merfolk", "Merrow", "Mimic", "Minotaur",
    "Minotaur Skeleton", "Mule", "Mummy", "Mummy Lord",
    # N
    "Nalfeshnee", "Night Hag", "Nightmare", "Noble",
    # O
    "Ochre Jelly", "Octopus", "Ogre", "Ogre Zombie", "Oni", "Orc",
    "Otyugh", "Owl", "Owlbear",
    # P
    "Panther", "Pegasus", "Phase Spider", "Pit Fiend", "Planetar",
    "Plesiosaurus", "Poisonous Snake", "Polar Bear", "Pony", "Priest",
    "Pseudodragon", "Purple Worm",
    # Q
    "Quasit", "Quipper",
    # R
    "Rakshasa", "Rat", "Raven", "Red Dragon Wyrmling", "Reef Shark",
    "Remorhaz", "Rhinoceros", "Riding Horse", "Roc", "Roper",
    "Rug of Smothering", "Rust Monster",
    # S
    "Saber-Toothed Tiger", "Sahuagin", "Salamander", "Satyr", "Scorpion",
    "Scout", "Sea Hag", "Sea Horse", "Shadow", "Shambling Mound",
    "Shield Guardian", "Shrieker", "Silver Dragon Wyrmling", "Skeleton",
    "Solar", "Specter", "Spider", "Spirit Naga", "Sprite", "Spy",
    "Steam Mephit", "Stirge", "Stone Giant", "Stone Golem", "Storm Giant",
    "Succubus/Incubus", "Swarm of Bats", "Swarm of Insects",
    "Swarm of Poisonous Snakes", "Swarm of Quippers", "Swarm of Rats",
    "Swarm of Ravens",
    # T
    "Tarrasque", "Thug", "Tiger", "Treant", "Tribal Warrior", "Triceratops",
    "Troll", "Tyrannosaurus Rex",
    # U
    "Unicorn",
    # V
    "Vampire", "Vampire Spawn", "Veteran", "Violet Fungus", "Vrock", "Vulture",
    # W
    "Warhorse", "Warhorse Skeleton", "Water Elemental", "Weasel", "Werebear",
    "Wereboar", "Wererat", "Weretiger", "Werewolf", "White Dragon Wyrmling",
    "Wight", "Will-o'-Wisp", "Winter Wolf", "Wolf", "Worg", "Wraith", "Wyvern",
    # X
    "Xorn",
    # Y
    "Young Black Dragon", "Young Blue Dragon", "Young Brass Dragon",
    "Young Bronze Dragon", "Young Copper Dragon", "Young Gold Dragon",
    "Young Green Dragon", "Young Red Dragon", "Young Silver Dragon",
    "Young White Dragon",
    # Z
    "Zombie",
}


class Command(BaseCommand):
    help = 'Remove non-SRD monsters from the database (keeps only SRD 5.1 monsters)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_confirm = options['yes']

        # Normalize SRD names for case-insensitive comparison
        srd_names_lower = {name.lower() for name in SRD_MONSTER_NAMES}

        # Get all monsters in the database
        all_monsters = Enemy.objects.all().order_by('name')
        total_count = all_monsters.count()

        # Separate SRD vs non-SRD
        to_keep = []
        to_delete = []

        for monster in all_monsters:
            if monster.name.lower() in srd_names_lower:
                to_keep.append(monster)
            else:
                to_delete.append(monster)

        self.stdout.write(f'\nDatabase has {total_count} total monsters')
        self.stdout.write(f'SRD reference list has {len(SRD_MONSTER_NAMES)} monsters')
        self.stdout.write(self.style.SUCCESS(f'  ✅ SRD (keeping): {len(to_keep)}'))
        self.stdout.write(self.style.WARNING(f'  ❌ Non-SRD (deleting): {len(to_delete)}'))

        if to_delete:
            self.stdout.write('\nMonsters to be deleted:')
            for m in to_delete:
                self.stdout.write(f'  - {m.name} (CR {m.challenge_rating})')

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n[DRY RUN] No changes made.'))
            return

        if not to_delete:
            self.stdout.write(self.style.SUCCESS('\nAll monsters are SRD-compliant! Nothing to delete.'))
            return

        if not skip_confirm:
            self.stdout.write(f'\nThis will permanently delete {len(to_delete)} monsters and all related data.')
            confirm = input('Are you sure? (yes/no): ')
            if confirm.lower() not in ('yes', 'y'):
                self.stdout.write('Aborted.')
                return

        # Delete non-SRD monsters (cascade deletes stats, attacks, etc.)
        deleted_count = 0
        for monster in to_delete:
            monster_name = monster.name
            monster.delete()
            deleted_count += 1
            self.stdout.write(f'  Deleted: {monster_name}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Purge complete! Deleted {deleted_count} non-SRD monsters. '
            f'{len(to_keep)} SRD monsters remain.'
        ))
