"""
Management command to seed encounter themes, associations, and biome weights

Usage: python manage.py seed_encounter_themes
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from encounters.models import (
    EncounterTheme, EnemyThemeAssociation, ThemeIncompatibility,
    BiomeEncounterWeight
)
from bestiary.models import Enemy


class Command(BaseCommand):
    help = 'Seed encounter themes with D&D 5e themed data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding encounter themes...')
        
        with transaction.atomic():
            # Clear existing data
            self.stdout.write('Clearing existing theme data...')
            EnemyThemeAssociation.objects.all().delete()
            BiomeEncounterWeight.objects.all().delete()
            ThemeIncompatibility.objects.all().delete()
            EncounterTheme.objects.all().delete()
            
            # Create themes
            themes = self.create_themes()
            self.stdout.write(f'Created {len(themes)} themes')
            
            # Associate enemies
            associations = self.create_enemy_associations(themes)
            self.stdout.write(f'Created {associations} enemy associations')
            
            # Define incompatibilities
            incompatibilities = self.create_incompatibilities(themes)
            self.stdout.write(f'Created {incompatibilities} incompatibilities')
            
            # Define biome weights
            weights = self.create_biome_weights(themes)
            self.stdout.write(f'Created {weights} biome weights')
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded encounter themes!'))
    
    def create_themes(self):
        """Create core encounter themes"""
        themes = {}
        
        # Humanoid Threats
        themes['bandit'] = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws and highway robbers",
            min_cr=1,
            max_cr=8,
            weight=120,
            flavor_text="A band of outlaws has made this area their hunting ground, preying on travelers and merchants."
        )
        
        themes['cultist'] = EncounterTheme.objects.create(
            name="Cultist Gathering",
            category="humanoid",
            description="Dark cult members conducting rituals",
            min_cr=2,
            max_cr=10,
            weight=80,
            flavor_text="Hooded figures chant in an ancient tongue, their ritual threatening to summon dark powers."
        )
        
        themes['tribal'] = EncounterTheme.objects.create(
            name="Goblinoid Raiders",
            category="humanoid",
            description="Goblins, hobgoblins, and bugbears",
            min_cr=1,
            max_cr=12,
            weight=100,
            flavor_text="A raiding party of goblinoids scouts the area, looking for weakness to exploit."
        )
        
        # Undead
        themes['undead'] = EncounterTheme.objects.create(
            name="Undead Horde",
            category="undead",
            description="Zombies, skeletons, and other unliving",
            min_cr=1,
            max_cr=15,
            weight=90,
            flavor_text="The dead walk these cursed lands, animated by dark necromancy."
        )
        
        # Beasts
        themes['predators'] = EncounterTheme.objects.create(
            name="Natural Predators",
            category="beast",
            description="Wolves, bears, and hunting beasts",
            min_cr=1,
            max_cr=6,
            weight=100,
            flavor_text="Wild predators stalk these lands, hungry and territorial."
        )
        
        themes['giant_beasts'] = EncounterTheme.objects.create(
            name="Giant Creatures",
            category="beast",
            description="Giant spiders, scorpions, and other enlarged beasts",
            min_cr=2,
            max_cr=8,
            weight=70,
            flavor_text="Unnatural magical energies have caused these creatures to grow to enormous size."
        )
        
        # Dragons
        themes['dragon'] = EncounterTheme.objects.create(
            name="Dragon's Domain",
            category="dragon",
            description="Dragons and their servants",
            min_cr=5,
            max_cr=20,
            weight=50,
            flavor_text="A dragon has claimed this territory, commanding kobolds and cultists to do its bidding."
        )
        
        # Aberrations
        themes['aberration'] = EncounterTheme.objects.create(
            name="Eldritch Horrors",
            category="aberration",
            description="Mind flayers, beholders, and aberrations",
            min_cr=8,
            max_cr=20,
            weight=40,
            flavor_text="Reality warps in the presence of these alien beings from beyond the stars."
        )
        
        # Elementals
        themes['elemental'] = EncounterTheme.objects.create(
            name="Elemental Forces",
            category="elemental",
            description="Elementals and elemental creatures",
            min_cr=3,
            max_cr=15,
            weight=60,
            flavor_text="The very elements have been roused to fury, manifesting as dangerous creatures."
        )
        
        # Fiends
        themes['devils'] = EncounterTheme.objects.create(
            name="Infernal Contract",
            category="fiend",
            description="Devils and their servants",
            min_cr=5,
            max_cr=20,
            weight=50,
            flavor_text="Devils from the Nine Hells enforce dark contracts and spread corruption."
        )
        
        # Fey
        themes['fey'] = EncounterTheme.objects.create(
            name="Fey Tricksters",
            category="fey",
            description="Sprites, pixies, and mischievous fey",
            min_cr=2,
            max_cr=10,
            weight=60,
            flavor_text="The veil between worlds grows thin, allowing capricious fey to cross over."
        )
        
        # Giants
        themes['giant'] = EncounterTheme.objects.create(
            name="Giant's Territory",
            category="giant",
            description="Giants and their pets",
            min_cr=5,
            max_cr=18,
            weight=50,
            flavor_text="Giants roam this land, claiming it as their ancient birthright."
        )
        
        # Dungeon
        themes['dungeon'] = EncounterTheme.objects.create(
            name="Dungeon Denizens",
            category="dungeon",
            description="Mixed creatures found in dungeons",
            min_cr=1,
            max_cr=15,
            weight=80,
            flavor_text="These ruins are home to various creatures seeking shelter and treasure."
        )
        
        return themes
    
    def create_enemy_associations(self, themes):
        """Associate enemies with themes"""
        count = 0
        
        # Helper function
        def associate(theme_key, enemy_name, role, weight=100, min_count=1, max_count=4):
            nonlocal count
            try:
                theme = themes[theme_key]
                enemy = Enemy.objects.filter(name__icontains=enemy_name).first()
                if enemy:
                    EnemyThemeAssociation.objects.create(
                        theme=theme,
                        enemy=enemy,
                        role=role,
                        weight=weight,
                        min_count=min_count,
                        max_count=max_count
                    )
                    count += 1
            except Exception as e:
                self.stdout.write(f"Could not associate {enemy_name}: {e}")
        
        # Bandit associations
        associate('bandit', 'Bandit', 'support', 100, 2, 6)
        associate('bandit', 'Bandit Captain', 'leader', 80, 1, 1)
        associate('bandit', 'Thug', 'elite', 60, 1, 3)
        
        # Cultist associations  
        associate('cultist', 'Cultist', 'support', 100, 3, 8)
        associate('cultist', 'Cult Fanatic', 'leader', 70, 1, 2)
        
        # Goblinoid associations
        associate('tribal', 'Goblin', 'support', 100, 4, 10)
        associate('tribal', 'Hobgoblin', 'elite', 70, 1, 4)
        associate('tribal', 'Bugbear', 'primary', 60, 1, 2)
        
        # Undead associations
        associate('undead', 'Zombie', 'support', 100, 3, 8)
        associate('undead', 'Skeleton', 'support', 100, 3, 8)
        associate('undead', 'Wight', 'elite', 60, 1, 2)
        
        # Predator associations
        associate('predators', 'Wolf', 'support', 100, 2, 6)
        associate('predators', 'Dire Wolf', 'elite', 70, 1, 3)
        associate('predators', 'Bear', 'primary', 80, 1, 2)
        
        # Giant creatures
        associate('giant_beasts', 'Giant Spider', 'primary', 100, 1, 4)
        associate('giant_beasts', 'Giant Scorpion', 'primary', 80, 1, 3)
        
        return count
    
    def create_incompatibilities(self, themes):
        """Define theme incompatibilities"""
        count = 0
        
        incompatible_pairs = [
            ('bandit', 'aberration', "Bandits flee from aberrations"),
            ('predators', 'undead', "Beasts avoid undead"),
            ('fey', 'devils', "Fey despise lawful evil"),
            ('tribal', 'aberration', "Goblinoids fear mind control"),
            ('dragon', 'aberration', "Dragons are territorial"),
            ('undead', 'elemental', "Undead and elementals don't mix"),
        ]
        
        for theme1_key, theme2_key, reason in incompatible_pairs:
            if theme1_key in themes and theme2_key in themes:
                ThemeIncompatibility.objects.create(
                    theme1=themes[theme1_key],
                    theme2=themes[theme2_key],
                    reason=reason,
                    allow_chaotic=True
                )
                count += 1
        
        return count
    
    def create_biome_weights(self, themes):
        """Define biome distribution weights"""
        count = 0
        
        biome_data = [
            # Forest
            ('forest', 'predators', 'endemic', 120),
            ('forest', 'tribal', 'endemic', 100),
            ('forest', 'bandit', 'adapted', 80),
            ('forest', 'fey', 'adapted', 60),
            ('forest', 'undead', 'anomaly', 20, "Cursed grove"),
            
            # Desert
            ('desert', 'giant_beasts', 'endemic', 100),
            ('desert', 'elemental', 'endemic', 80),
            ('desert', 'bandit', 'adapted', 70),
            ('desert', 'undead', 'adapted', 50),
            ('desert', 'aberration', 'anomaly', 15, "Ancient buried temple"),
            
            # Mountain
            ('mountain', 'giant', 'endemic', 100),
            ('mountain', 'dragon', 'endemic', 80),
            ('mountain', 'tribal', 'adapted', 70),
            ('mountain', 'elemental', 'adapted', 60),
            
            # Swamp
            ('swamp', 'undead', 'endemic', 100),
            ('swamp', 'predators', 'endemic', 80),
            ('swamp', 'tribal', 'adapted', 60),
            ('swamp', 'fey', 'adapted', 50),
            
            # Plains
            ('plains', 'bandit', 'endemic', 100),
            ('plains', 'tribal', 'endemic', 90),
            ('plains', 'predators', 'adapted', 70),
            ('plains', 'giant', 'traveler', 40),
            
            # Underdark
            ('underdark', 'aberration', 'endemic', 120),
            ('underdark', 'dungeon', 'endemic', 100),
            ('underdark', 'tribal', 'endemic', 80),
            ('underdark', 'giant_beasts', 'adapted', 60),
            
            # Urban
            ('urban', 'bandit', 'endemic', 120),
            ('urban', 'cultist', 'endemic', 100),
            ('urban', 'devils', 'adapted', 60),
            ('urban', 'aberration', 'anomaly', 10, "Secret cult beneath city"),
            
            # Dungeon (generic)
            ('dungeon', 'dungeon', 'endemic', 120),
            ('dungeon', 'undead', 'endemic', 100),
            ('dungeon', 'tribal', 'endemic', 90),
            ('dungeon', 'aberration', 'adapted', 60),
        ]
        
        for data in biome_data:
            biome, theme_key, category, weight = data[:4]
            narrative = data[4] if len(data) > 4 else ""
            
            if theme_key in themes:
                BiomeEncounterWeight.objects.create(
                    biome=biome,
                    theme=themes[theme_key],
                    category=category,
                    weight=weight,
                    narrative_reason=narrative
                )
                count += 1
        
        return count
