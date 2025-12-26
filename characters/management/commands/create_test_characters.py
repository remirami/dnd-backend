from django.core.management.base import BaseCommand
from characters.models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground
)


class Command(BaseCommand):
    help = 'Create test characters with stats for combat testing'

    def handle(self, *args, **options):
        # Ensure base data exists
        fighter_class, _ = CharacterClass.objects.get_or_create(
            name='fighter',
            defaults={
                'hit_dice': 'd10',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'STR,CON',
                'description': 'A master of martial combat'
            }
        )
        
        wizard_class, _ = CharacterClass.objects.get_or_create(
            name='wizard',
            defaults={
                'hit_dice': 'd6',
                'primary_ability': 'INT',
                'saving_throw_proficiencies': 'INT,WIS',
                'description': 'A scholarly magic-user'
            }
        )
        
        human_race, _ = CharacterRace.objects.get_or_create(
            name='human',
            defaults={
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+1,DEX+1,CON+1,INT+1,WIS+1,CHA+1'
            }
        )
        
        elf_race, _ = CharacterRace.objects.get_or_create(
            name='elf',
            defaults={
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'DEX+2'
            }
        )
        
        soldier_bg, _ = CharacterBackground.objects.get_or_create(
            name='soldier',
            defaults={
                'skill_proficiencies': 'Athletics,Intimidation',
                'languages': 0
            }
        )
        
        sage_bg, _ = CharacterBackground.objects.get_or_create(
            name='sage',
            defaults={
                'skill_proficiencies': 'Arcana,History',
                'languages': 2
            }
        )
        
        # Create Fighter character
        fighter, created = Character.objects.get_or_create(
            name='Test Fighter',
            defaults={
                'level': 5,
                'character_class': fighter_class,
                'race': human_race,
                'background': soldier_bg,
                'alignment': 'LG',
                'experience_points': 6500,
                'player_name': 'Test Player 1'
            }
        )
        
        if created:
            self.stdout.write(f'Created character: {fighter.name}')
        else:
            self.stdout.write(f'Character already exists: {fighter.name}')
        
        # Create stats for fighter
        fighter_stats, stats_created = CharacterStats.objects.get_or_create(
            character=fighter,
            defaults={
                'strength': 18,
                'dexterity': 14,
                'constitution': 16,
                'intelligence': 10,
                'wisdom': 12,
                'charisma': 10,
                'hit_points': 45,
                'max_hit_points': 45,
                'armor_class': 18,
                'speed': 30,
                'initiative': 2,
                'passive_perception': 11
            }
        )
        
        if stats_created:
            self.stdout.write(f'  Created stats for {fighter.name}')
        else:
            self.stdout.write(f'  Stats already exist for {fighter.name}')
        
        # Create Wizard character
        wizard, created = Character.objects.get_or_create(
            name='Test Wizard',
            defaults={
                'level': 5,
                'character_class': wizard_class,
                'race': elf_race,
                'background': sage_bg,
                'alignment': 'NG',
                'experience_points': 6500,
                'player_name': 'Test Player 2'
            }
        )
        
        if created:
            self.stdout.write(f'Created character: {wizard.name}')
        else:
            self.stdout.write(f'Character already exists: {wizard.name}')
        
        # Create stats for wizard
        wizard_stats, stats_created = CharacterStats.objects.get_or_create(
            character=wizard,
            defaults={
                'strength': 8,
                'dexterity': 14,
                'constitution': 14,
                'intelligence': 18,
                'wisdom': 12,
                'charisma': 10,
                'hit_points': 32,
                'max_hit_points': 32,
                'armor_class': 12,
                'speed': 30,
                'initiative': 2,
                'passive_perception': 11,
                'spell_save_dc': 15,
                'spell_attack_bonus': 7
            }
        )
        
        if stats_created:
            self.stdout.write(f'  Created stats for {wizard.name}')
        else:
            self.stdout.write(f'  Stats already exist for {wizard.name}')
        
        # Create Rogue character
        rogue_class, _ = CharacterClass.objects.get_or_create(
            name='rogue',
            defaults={
                'hit_dice': 'd8',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'DEX,INT',
                'description': 'A scoundrel who uses stealth and trickery'
            }
        )
        
        rogue, created = Character.objects.get_or_create(
            name='Test Rogue',
            defaults={
                'level': 3,
                'character_class': rogue_class,
                'race': elf_race,
                'background': soldier_bg,
                'alignment': 'CN',
                'experience_points': 2700,
                'player_name': 'Test Player 3'
            }
        )
        
        if created:
            self.stdout.write(f'Created character: {rogue.name}')
        else:
            self.stdout.write(f'Character already exists: {rogue.name}')
        
        # Create stats for rogue
        rogue_stats, stats_created = CharacterStats.objects.get_or_create(
            character=rogue,
            defaults={
                'strength': 10,
                'dexterity': 16,
                'constitution': 14,
                'intelligence': 12,
                'wisdom': 13,
                'charisma': 14,
                'hit_points': 24,
                'max_hit_points': 24,
                'armor_class': 15,
                'speed': 30,
                'initiative': 3,
                'passive_perception': 14
            }
        )
        
        if stats_created:
            self.stdout.write(f'  Created stats for {rogue.name}')
        else:
            self.stdout.write(f'  Stats already exist for {rogue.name}')
        
        self.stdout.write(
            self.style.SUCCESS('\n[SUCCESS] Test characters created successfully!')
        )
        self.stdout.write('\nCharacters created:')
        self.stdout.write(f'  - {fighter.name} (Level {fighter.level} Fighter) - HP: {fighter_stats.hit_points}, AC: {fighter_stats.armor_class}')
        self.stdout.write(f'  - {wizard.name} (Level {wizard.level} Wizard) - HP: {wizard_stats.hit_points}, AC: {wizard_stats.armor_class}')
        self.stdout.write(f'  - {rogue.name} (Level {rogue.level} Rogue) - HP: {rogue_stats.hit_points}, AC: {rogue_stats.armor_class}')

