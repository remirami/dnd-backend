from django.core.management.base import BaseCommand
from encounters.models import Encounter, EncounterEnemy
from bestiary.models import Enemy, EnemyStats


class Command(BaseCommand):
    help = 'Create test encounters with enemies for combat testing'

    def handle(self, *args, **options):
        # Create or get Goblin enemy
        goblin, created = Enemy.objects.get_or_create(
            name='Goblin',
            defaults={
                'challenge_rating': '1/4',
                'size': 'S',
                'creature_type': 'humanoid',
                'alignment': 'NE'
            }
        )
        
        if created:
            self.stdout.write(f'Created enemy: {goblin.name}')
        else:
            self.stdout.write(f'Enemy already exists: {goblin.name}')
        
        # Create stats for goblin
        goblin_stats, stats_created = EnemyStats.objects.get_or_create(
            enemy=goblin,
            defaults={
                'strength': 8,
                'dexterity': 14,
                'constitution': 10,
                'intelligence': 10,
                'wisdom': 8,
                'charisma': 8,
                'hit_points': 7,
                'armor_class': 15,
                'speed': '30 ft.',
                'passive_perception': 9
            }
        )
        
        if stats_created:
            self.stdout.write(f'  Created stats for {goblin.name}')
        else:
            self.stdout.write(f'  Stats already exist for {goblin.name}')
        
        # Create or get Orc enemy
        orc, created = Enemy.objects.get_or_create(
            name='Orc',
            defaults={
                'challenge_rating': '1/2',
                'size': 'M',
                'creature_type': 'humanoid',
                'alignment': 'CE'
            }
        )
        
        if created:
            self.stdout.write(f'Created enemy: {orc.name}')
        else:
            self.stdout.write(f'Enemy already exists: {orc.name}')
        
        # Create stats for orc
        orc_stats, stats_created = EnemyStats.objects.get_or_create(
            enemy=orc,
            defaults={
                'strength': 16,
                'dexterity': 12,
                'constitution': 16,
                'intelligence': 7,
                'wisdom': 11,
                'charisma': 10,
                'hit_points': 15,
                'armor_class': 13,
                'speed': '30 ft.',
                'passive_perception': 10
            }
        )
        
        if stats_created:
            self.stdout.write(f'  Created stats for {orc.name}')
        else:
            self.stdout.write(f'  Stats already exist for {orc.name}')
        
        # Create Test Encounter 1: Goblin Ambush
        encounter1, created = Encounter.objects.get_or_create(
            name='Goblin Ambush',
            defaults={
                'description': 'A group of goblins ambushes the party on the forest road',
                'location': 'Forest Road'
            }
        )
        
        if created:
            self.stdout.write(f'\nCreated encounter: {encounter1.name}')
        else:
            self.stdout.write(f'\nEncounter already exists: {encounter1.name}')
        
        # Add goblins to encounter
        for i in range(1, 4):  # 3 goblins
            goblin_enemy, created = EncounterEnemy.objects.get_or_create(
                encounter=encounter1,
                enemy=goblin,
                name=f'Goblin {i}',
                defaults={
                    'current_hp': goblin_stats.hit_points,
                    'initiative': 0,
                    'is_alive': True
                }
            )
            
            if created:
                self.stdout.write(f'  Added {goblin_enemy.name} to encounter')
            else:
                self.stdout.write(f'  {goblin_enemy.name} already in encounter')
        
        # Create Test Encounter 2: Orc Raid
        encounter2, created = Encounter.objects.get_or_create(
            name='Orc Raid',
            defaults={
                'description': 'A band of orcs attacks the village',
                'location': 'Village Outskirts'
            }
        )
        
        if created:
            self.stdout.write(f'\nCreated encounter: {encounter2.name}')
        else:
            self.stdout.write(f'\nEncounter already exists: {encounter2.name}')
        
        # Add orcs to encounter
        for i in range(1, 3):  # 2 orcs
            orc_enemy, created = EncounterEnemy.objects.get_or_create(
                encounter=encounter2,
                enemy=orc,
                name=f'Orc {i}',
                defaults={
                    'current_hp': orc_stats.hit_points,
                    'initiative': 0,
                    'is_alive': True
                }
            )
            
            if created:
                self.stdout.write(f'  Added {orc_enemy.name} to encounter')
            else:
                self.stdout.write(f'  {orc_enemy.name} already in encounter')
        
        # Create Test Encounter 3: Mixed Group
        encounter3, created = Encounter.objects.get_or_create(
            name='Mixed Threat',
            defaults={
                'description': 'A mixed group of goblins and orcs',
                'location': 'Abandoned Fort'
            }
        )
        
        if created:
            self.stdout.write(f'\nCreated encounter: {encounter3.name}')
        else:
            self.stdout.write(f'\nEncounter already exists: {encounter3.name}')
        
        # Add mixed enemies
        goblin_mixed, created = EncounterEnemy.objects.get_or_create(
            encounter=encounter3,
            enemy=goblin,
            name='Goblin Scout',
            defaults={
                'current_hp': goblin_stats.hit_points,
                'initiative': 0,
                'is_alive': True
            }
        )
        
        if created:
            self.stdout.write(f'  Added {goblin_mixed.name} to encounter')
        
        orc_mixed, created = EncounterEnemy.objects.get_or_create(
            encounter=encounter3,
            enemy=orc,
            name='Orc Warrior',
            defaults={
                'current_hp': orc_stats.hit_points,
                'initiative': 0,
                'is_alive': True
            }
        )
        
        if created:
            self.stdout.write(f'  Added {orc_mixed.name} to encounter')
        
        self.stdout.write(
            self.style.SUCCESS('\n[SUCCESS] Test encounters created successfully!')
        )
        self.stdout.write('\nEncounters created:')
        self.stdout.write(f'  - {encounter1.name}: {encounter1.enemies.count()} enemies')
        self.stdout.write(f'  - {encounter2.name}: {encounter2.enemies.count()} enemies')
        self.stdout.write(f'  - {encounter3.name}: {encounter3.enemies.count()} enemies')

