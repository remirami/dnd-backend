import json
import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
from bestiary.models import (
    Enemy, EnemyStats, EnemyAttack, EnemyAbility, EnemySpell, EnemySpellSlot,
    DamageType, EnemyResistance, Language, EnemyLanguage
)


class Command(BaseCommand):
    help = 'Import monsters from various sources (JSON, CSV, D&D Beyond API)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['json', 'csv', 'dndbeyond', 'srd', 'open5e'],
            required=True,
            help='Source type for import'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to import file (for JSON/CSV)'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='URL for D&D Beyond API or other web sources'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving to database'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing monsters instead of skipping'
        )

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        try:
            if source == 'json':
                self.import_from_json(options['file'], dry_run, update_existing)
            elif source == 'csv':
                self.import_from_csv(options['file'], dry_run, update_existing)
            elif source == 'dndbeyond':
                self.import_from_dndbeyond(options['url'], dry_run, update_existing)
            elif source == 'srd':
                self.import_srd_monsters(dry_run, update_existing)
            elif source == 'open5e':
                self.import_from_open5e(dry_run, update_existing)
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def import_from_json(self, file_path, dry_run, update_existing):
        """Import monsters from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON: {str(e)}')

        if isinstance(data, list):
            monsters = data
        elif isinstance(data, dict) and 'monsters' in data:
            monsters = data['monsters']
        else:
            monsters = [data]

        self.process_monsters(monsters, dry_run, update_existing)

    def import_from_csv(self, file_path, dry_run, update_existing):
        """Import monsters from CSV file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                monsters = list(reader)
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')

        self.process_monsters(monsters, dry_run, update_existing)

    def import_from_dndbeyond(self, url, dry_run, update_existing):
        """Import monsters from D&D Beyond API (if available)"""
        if not REQUESTS_AVAILABLE:
            raise CommandError('Requests library not available. Install with: pip install requests')
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise CommandError(f'Failed to fetch from D&D Beyond: {str(e)}')

        # Parse D&D Beyond format
        monsters = self.parse_dndbeyond_format(data)
        self.process_monsters(monsters, dry_run, update_existing)

    def import_srd_monsters(self, dry_run, update_existing):
        """Import monsters from D&D 5e SRD (System Reference Document)"""
        from bestiary.importers import SRDMonsterData
        srd_monsters = SRDMonsterData.get_srd_monsters()
        self.process_monsters(srd_monsters, dry_run, update_existing)

    def import_from_open5e(self, dry_run, update_existing):
        """Import monsters from Open5e API"""
        from bestiary.importers import Open5eAPI
        
        self.stdout.write('Fetching monsters from Open5e API...')
        api = Open5eAPI()
        
        # Fetch data
        raw_monsters = api.get_all_monsters()
        self.stdout.write(f'Fetched {len(raw_monsters)} monsters. Processing...')
        
        # Parse and process
        monsters = []
        for raw_monster in raw_monsters:
            monsters.append(api.parse_monster_data(raw_monster))
            
        self.process_monsters(monsters, dry_run, update_existing)

    def process_monsters(self, monsters, dry_run, update_existing):
        """Process and import monster data"""
        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for monster_data in monsters:
            try:
                if dry_run:
                    self.stdout.write(f'[DRY RUN] Would import: {monster_data.get("name", "Unknown")}')
                    continue

                with transaction.atomic():
                    monster, created = self.create_or_update_monster(monster_data, update_existing)
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'Imported: {monster.name}')
                    elif update_existing:
                        updated_count += 1
                        self.stdout.write(f'Updated: {monster.name}')
                    else:
                        skipped_count += 1
                        self.stdout.write(f'Skipped (exists): {monster_data.get("name", "Unknown")}')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to import {monster_data.get("name", "Unknown")}: {str(e)}')
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import complete: {imported_count} imported, {updated_count} updated, {skipped_count} skipped'
                )
            )

    def create_or_update_monster(self, data, update_existing):
        """Create or update a monster from data"""
        name = data.get('name', 'Unknown Monster')
        
        # Check if monster exists
        try:
            monster = Enemy.objects.get(name=name)
            if not update_existing:
                return monster, False
        except Enemy.DoesNotExist:
            monster = None

        # Create or update basic enemy data
        enemy_data = {
            'name': name,
            'hp': data.get('hit_points', data.get('hp', 1)),
            'ac': data.get('armor_class', data.get('ac', 10)),
            'challenge_rating': data.get('challenge_rating', data.get('cr', ''))
        }

        if monster:
            for key, value in enemy_data.items():
                setattr(monster, key, value)
            monster.save()
        else:
            monster = Enemy.objects.create(**enemy_data)

        # Create or update stats
        self.create_or_update_stats(monster, data)
        
        # Create attacks
        self.create_attacks(monster, data)
        
        # Create abilities
        self.create_abilities(monster, data)
        
        # Create spells
        self.create_spells(monster, data)
        
        # Create resistances
        self.create_resistances(monster, data)
        
        # Create languages
        self.create_languages(monster, data)

        return monster, not monster

    def create_or_update_stats(self, monster, data):
        """Create or update enemy stats"""
        stats_data = {
            'enemy': monster,
            'strength': data.get('strength', 10),
            'dexterity': data.get('dexterity', 10),
            'constitution': data.get('constitution', 10),
            'intelligence': data.get('intelligence', 10),
            'wisdom': data.get('wisdom', 10),
            'charisma': data.get('charisma', 10),
            'hit_points': data.get('hit_points', data.get('hp', 1)),
            'armor_class': data.get('armor_class', data.get('ac', 10)),
            'speed': data.get('speed', ''),
            'str_save': data.get('str_save'),
            'dex_save': data.get('dex_save'),
            'con_save': data.get('con_save'),
            'int_save': data.get('int_save'),
            'wis_save': data.get('wis_save'),
            'cha_save': data.get('cha_save'),
            'athletics': data.get('athletics'),
            'acrobatics': data.get('acrobatics'),
            'sleight_of_hand': data.get('sleight_of_hand'),
            'stealth': data.get('stealth'),
            'arcana': data.get('arcana'),
            'history': data.get('history'),
            'investigation': data.get('investigation'),
            'nature': data.get('nature'),
            'religion': data.get('religion'),
            'animal_handling': data.get('animal_handling'),
            'insight': data.get('insight'),
            'medicine': data.get('medicine'),
            'perception': data.get('perception'),
            'survival': data.get('survival'),
            'deception': data.get('deception'),
            'intimidation': data.get('intimidation'),
            'performance': data.get('performance'),
            'persuasion': data.get('persuasion'),
            'darkvision': data.get('darkvision'),
            'blindsight': data.get('blindsight'),
            'tremorsense': data.get('tremorsense'),
            'truesight': data.get('truesight'),
            'passive_perception': data.get('passive_perception'),
            'spell_save_dc': data.get('spell_save_dc'),
            'spell_attack_bonus': data.get('spell_attack_bonus')
        }

        # Remove None values
        stats_data = {k: v for k, v in stats_data.items() if v is not None}

        EnemyStats.objects.update_or_create(
            enemy=monster,
            defaults=stats_data
        )

    def create_attacks(self, monster, data):
        """Create enemy attacks"""
        attacks = data.get('attacks', [])
        for attack_data in attacks:
            EnemyAttack.objects.get_or_create(
                enemy=monster,
                name=attack_data.get('name', 'Attack'),
                defaults={
                    'bonus': attack_data.get('bonus', 0),
                    'damage': attack_data.get('damage', '1d4')
                }
            )

    def create_abilities(self, monster, data):
        """Create enemy abilities"""
        abilities = data.get('abilities', [])
        for ability_data in abilities:
            EnemyAbility.objects.get_or_create(
                enemy=monster,
                name=ability_data.get('name', 'Ability'),
                defaults={
                    'description': ability_data.get('description', '')
                }
            )

    def create_spells(self, monster, data):
        """Create enemy spells"""
        spells = data.get('spells', [])
        for spell_data in spells:
            spell, created = EnemySpell.objects.get_or_create(
                enemy=monster,
                name=spell_data.get('name', 'Spell'),
                defaults={
                    'save_dc': spell_data.get('save_dc')
                }
            )
            
            # Create spell slots if provided
            slots = spell_data.get('slots', [])
            for slot_data in slots:
                EnemySpellSlot.objects.get_or_create(
                    spell=spell,
                    level=slot_data.get('level', 1),
                    defaults={
                        'uses': slot_data.get('uses', 1)
                    }
                )

    def create_resistances(self, monster, data):
        """Create enemy resistances"""
        resistances = data.get('resistances', [])
        for res_data in resistances:
            damage_type_name = res_data.get('damage_type', res_data.get('type', ''))
            resistance_type = res_data.get('resistance_type', res_data.get('type', 'resistance'))
            
            try:
                damage_type = DamageType.objects.get(name=damage_type_name)
                EnemyResistance.objects.get_or_create(
                    enemy=monster,
                    damage_type=damage_type,
                    resistance_type=resistance_type,
                    defaults={
                        'notes': res_data.get('notes', '')
                    }
                )
            except DamageType.DoesNotExist:
                self.stdout.write(f'Warning: Damage type "{damage_type_name}" not found')

    def create_languages(self, monster, data):
        """Create enemy languages"""
        languages = data.get('languages', [])
        for lang_name in languages:
            try:
                language = Language.objects.get(name=lang_name)
                EnemyLanguage.objects.get_or_create(
                    enemy=monster,
                    language=language
                )
            except Language.DoesNotExist:
                self.stdout.write(f'Warning: Language "{lang_name}" not found')

    def parse_dndbeyond_format(self, data):
        """Parse D&D Beyond specific format"""
        from bestiary.importers import DnDBeyondAPI
        api = DnDBeyondAPI()
        return api.parse_monster_data(data)

