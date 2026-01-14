import json
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
    help = 'Import monsters from Open5e API (free, no API key required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['open5e', 'json'],
            default='open5e',
            help='Source for monster import'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to JSON file (if using json source)'
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
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of monsters to import (for testing)'
        )
        parser.add_argument(
            '--cr-min',
            type=str,
            help='Minimum challenge rating (e.g., "1/4", "1", "5")'
        )
        parser.add_argument(
            '--cr-max',
            type=str,
            help='Maximum challenge rating (e.g., "5", "10", "20")'
        )

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        limit = options.get('limit')
        cr_min = options.get('cr_min')
        cr_max = options.get('cr_max')

        if not REQUESTS_AVAILABLE and source == 'open5e':
            raise CommandError('Requests library not available. Install with: pip install requests')

        try:
            if source == 'open5e':
                self.import_from_open5e(dry_run, update_existing, limit, cr_min, cr_max)
            elif source == 'json':
                self.import_from_json(options['file'], dry_run, update_existing)
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def import_from_open5e(self, dry_run, update_existing, limit=None, cr_min=None, cr_max=None):
        """Import monsters from Open5e API"""
        self.stdout.write('Fetching monsters from Open5e API...')
        
        # Open5e API endpoint
        url = 'https://api.open5e.com/monsters/'
        
        # Add CR filters if provided
        params = {}
        if cr_min:
            params['challenge_rating_min'] = cr_min
        if cr_max:
            params['challenge_rating_max'] = cr_max
        
        monsters = self._fetch_paginated_data(url, limit, params)
        
        self.stdout.write(f'\nTotal monsters to process: {len(monsters)}')
        self.process_monsters(monsters, dry_run, update_existing)

    def _fetch_paginated_data(self, url, limit=None, params=None):
        """Fetch all pages of data from Open5e API"""
        monsters = []
        page = 1
        
        while url:
            try:
                response = requests.get(url, params=params if page == 1 else None, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                monsters.extend(results)
                
                self.stdout.write(f'  Page {page}: {len(results)} monsters')
                
                # Check if we've hit the limit
                if limit and len(monsters) >= limit:
                    monsters = monsters[:limit]
                    break
                
                # Get next page
                url = data.get('next')
                page += 1
                
            except requests.RequestException as e:
                self.stdout.write(self.style.WARNING(f'Failed to fetch page {page}: {str(e)}'))
                break
        
        return monsters

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

    def process_monsters(self, monsters, dry_run, update_existing):
        """Process and import monster data"""
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for monster_data in monsters:
            try:
                if dry_run:
                    cr = monster_data.get('challenge_rating', 'N/A')
                    self.stdout.write(
                        f'[DRY RUN] Would import: {monster_data.get("name", "Unknown")} (CR {cr})'
                    )
                    continue

                with transaction.atomic():
                    monster, created = self.create_or_update_monster(monster_data, update_existing)
                    
                    if monster:
                        if created:
                            imported_count += 1
                            self.stdout.write(
                                f'[+] Imported: {monster.name} (CR {monster.challenge_rating})'
                            )
                        elif update_existing:
                            updated_count += 1
                            self.stdout.write(f'[*] Updated: {monster.name}')
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'[!] Failed to import {monster_data.get("name", "Unknown")}: {str(e)}'
                    )
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n========================================\n'
                    f'Import complete!\n'
                    f'  Imported: {imported_count}\n'
                    f'  Updated:  {updated_count}\n'
                    f'  Skipped:  {skipped_count}\n'
                    f'  Errors:   {error_count}\n'
                    f'========================================'
                )
            )

    def create_or_update_monster(self, data, update_existing):
        """Create or update a monster from Open5e data"""
        name = data.get('name', 'Unknown Monster')
        
        # Check if monster exists
        try:
            monster = Enemy.objects.get(name=name)
            if not update_existing:
                return monster, False
        except Enemy.DoesNotExist:
            monster = None

        # Parse CR
        cr = str(data.get('challenge_rating', '0'))
        
        # Create or update basic enemy data
        enemy_data = {
            'name': name,
            'hp': data.get('hit_points', 1),
            'ac': data.get('armor_class', 10),
            'challenge_rating': cr,
        }

        if monster:
            for key, value in enemy_data.items():
                setattr(monster, key, value)
            monster.save()
        else:
            monster = Enemy.objects.create(**enemy_data)

        # Create or update stats
        self.create_or_update_stats(monster, data)
        
        # Create actions (attacks and abilities)
        self.create_actions(monster, data)
        
        # Create special abilities
        self.create_special_abilities(monster, data)
        
        # Create legendary actions
        self.create_legendary_actions(monster, data)
        
        # Create resistances/immunities/vulnerabilities
        self.create_resistances(monster, data)
        
        # Create languages
        self.create_languages(monster, data)
        
        # Create spells from spellcasting abilities
        self.create_spells(monster, data)

        return monster, monster is not None

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
            'hit_points': data.get('hit_points', 1),
            'armor_class': data.get('armor_class', 10),
            'speed': data.get('speed', {}).get('walk', '30 ft.') if isinstance(data.get('speed'), dict) else data.get('speed', '30 ft.'),
            'str_save': data.get('strength_save'),
            'dex_save': data.get('dexterity_save'),
            'con_save': data.get('constitution_save'),
            'int_save': data.get('intelligence_save'),
            'wis_save': data.get('wisdom_save'),
            'cha_save': data.get('charisma_save'),
            'perception': data.get('perception'),
            'stealth': data.get('stealth'),
            'athletics': data.get('athletics'),
            'acrobatics': data.get('acrobatics'),
            'darkvision': data.get('senses', {}).get('darkvision') if isinstance(data.get('senses'), dict) else None,
            'passive_perception': data.get('senses', {}).get('passive_perception', 10) if isinstance(data.get('senses'), dict) else 10,
        }

        # Remove None values
        stats_data = {k: v for k, v in stats_data.items() if v is not None}

        EnemyStats.objects.update_or_create(
            enemy=monster,
            defaults=stats_data
        )

    def create_actions(self, monster, data):
        """Create enemy actions (attacks)"""
        # Clear existing attacks
        EnemyAttack.objects.filter(enemy=monster).delete()
        
        actions = data.get('actions', [])
        if not actions:
            return
        
        for action in actions:
            # Try to parse attack bonus and damage
            desc = action.get('desc', '')
            name = action.get('name', 'Attack')
            
            # Parse attack bonus (e.g., "+5 to hit")
            import re
            bonus_match = re.search(r'\+(\d+) to hit', desc)
            bonus = int(bonus_match.group(1)) if bonus_match else 0
            
            # Parse damage (e.g., "1d8+3 slashing")
            damage_match = re.search(r'(\d+d\d+(?:\+\d+)?)\s+(\w+)', desc)
            damage = damage_match.group(1) if damage_match else '1d4'
            damage_type = damage_match.group(2) if damage_match else 'bludgeoning'
            
            EnemyAttack.objects.create(
                enemy=monster,
                name=name,
                bonus=bonus,
                damage=f'{damage} {damage_type}'
            )

    def create_special_abilities(self, monster, data):
        """Create enemy special abilities"""
        # Clear existing abilities
        EnemyAbility.objects.filter(enemy=monster).delete()
        
        abilities = data.get('special_abilities', [])
        if not abilities:
            return
        
        for ability in abilities:
            EnemyAbility.objects.create(
                enemy=monster,
                name=ability.get('name', 'Ability'),
                description=ability.get('desc', '')
            )

    def create_legendary_actions(self, monster, data):
        """Create legendary actions"""
        legendary_actions = data.get('legendary_actions', [])
        if not legendary_actions:
            return
        
        for action in legendary_actions:
            EnemyAbility.objects.create(
                enemy=monster,
                name=f'[Legendary] {action.get("name", "Action")}',
                description=action.get('desc', '')
            )

    def create_resistances(self, monster, data):
        """Create enemy resistances, immunities, and vulnerabilities"""
        # Clear existing resistances
        EnemyResistance.objects.filter(enemy=monster).delete()
        
        # Process damage resistances
        resistances = data.get('damage_resistances', '')
        if resistances:
            self._add_resistances(monster, resistances, 'resistance')
        
        # Process damage immunities
        immunities = data.get('damage_immunities', '')
        if immunities:
            self._add_resistances(monster, immunities, 'immunity')
        
        # Process damage vulnerabilities
        vulnerabilities = data.get('damage_vulnerabilities', '')
        if vulnerabilities:
            self._add_resistances(monster, vulnerabilities, 'vulnerability')

    def _add_resistances(self, monster, damage_types_str, resistance_type):
        """Helper to add resistances"""
        if not damage_types_str:
            return
        
        # Split by comma or semicolon
        damage_types = [dt.strip().title() for dt in damage_types_str.replace(';', ',').split(',')]
        
        for damage_type_name in damage_types:
            if not damage_type_name:
                continue
            
            try:
                damage_type = DamageType.objects.get(name__iexact=damage_type_name)
                EnemyResistance.objects.get_or_create(
                    enemy=monster,
                    damage_type=damage_type,
                    resistance_type=resistance_type
                )
            except DamageType.DoesNotExist:
                # Try to create the damage type
                damage_type, _ = DamageType.objects.get_or_create(
                    name=damage_type_name
                )
                EnemyResistance.objects.get_or_create(
                    enemy=monster,
                    damage_type=damage_type,
                    resistance_type=resistance_type
                )

    def create_languages(self, monster, data):
        """Create enemy languages"""
        # Clear existing languages
        EnemyLanguage.objects.filter(enemy=monster).delete()
        
        languages_str = data.get('languages', '')
        if not languages_str or languages_str == '—' or languages_str == '-':
            return
        
        # Split by comma
        language_names = [lang.strip() for lang in languages_str.split(',')]
        
        for lang_name in language_names:
            if not lang_name or lang_name == '—':
                continue
            
            # Clean up language name (remove things like "understands but can't speak")
            import re
            clean_name = re.sub(r'\(.*?\)', '', lang_name).strip()
            clean_name = clean_name.split('but')[0].strip()
            clean_name = clean_name.split('understands')[0].strip()
            
            if not clean_name:
                continue
            
            try:
                language = Language.objects.get(name__iexact=clean_name)
                EnemyLanguage.objects.get_or_create(
                    enemy=monster,
                    language=language
                )
            except Language.DoesNotExist:
                # Try to create the language
                language, _ = Language.objects.get_or_create(
                    name=clean_name.title()
                )
                EnemyLanguage.objects.get_or_create(
                    enemy=monster,
                    language=language
                )

    
    def create_spells(self, monster, data):
        """Parse and create enemy spells from spellcasting abilities"""
        # Clear existing spells and spell slots
        EnemySpell.objects.filter(enemy=monster).delete()
        
        # Look for spellcasting in special abilities
        for ability in data.get('special_abilities', []):
            ability_name = ability.get('name', '').lower()
            if 'spellcasting' in ability_name or 'innate spellcasting' in ability_name:
                self._parse_spellcasting(monster, ability)
    
    def _parse_spellcasting(self, monster, ability):
        """Parse a spellcasting ability description"""
        import re
        
        desc = ability.get('desc', '')
        
        # Extract spell save DC
        save_dc_match = re.search(r'spell save DC (\d+)', desc)
        save_dc = int(save_dc_match.group(1)) if save_dc_match else None
        
        # Parse at-will spells (including cantrips)
        at_will_patterns = [
            r'at will:([^\n]+)',
            r'Cantrips \(at will\):([^\n]+)',
        ]
        
        for pattern in at_will_patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                self._create_at_will_spells(monster, match.group(1), save_dc)
        
        # Parse X/day spells
        day_pattern = r'(\d+)/day(?:\s+each)?:([^\n]+)'
        for match in re.finditer(day_pattern, desc):
            uses = int(match.group(1))
            spell_list = match.group(2)
            self._create_daily_spells(monster, spell_list, uses, save_dc)
        
        # Parse slotted spells by level
        level_pattern = r'(\d+)(?:st|nd|rd|th) level \((\d+) slots?\):([^\n]+)'
        for match in re.finditer(level_pattern, desc):
            level = int(match.group(1))
            slots = int(match.group(2))
            spell_list = match.group(3)
            self._create_slotted_spells(monster, spell_list, level, slots, save_dc)
    
    def _create_at_will_spells(self, monster, spell_text, save_dc):
        """Create at-will spells (no usage limit)"""
        spell_names = self._parse_spell_names(spell_text)
        for name in spell_names:
            EnemySpell.objects.create(
                enemy=monster,
                name=name,
                save_dc=save_dc
            )
            # No EnemySpellSlot = unlimited uses
    
    def _create_daily_spells(self, monster, spell_text, uses, save_dc):
        """Create X/day spells"""
        spell_names = self._parse_spell_names(spell_text)
        for name in spell_names:
            spell = EnemySpell.objects.create(
                enemy=monster,
                name=name,
                save_dc=save_dc
            )
            EnemySpellSlot.objects.create(
                spell=spell,
                level=0,  # Daily spells don't have a specific level
                uses=uses
            )
    
    def _create_slotted_spells(self, monster, spell_text, level, slots, save_dc):
        """Create spells with spell slots by level"""
        spell_names = self._parse_spell_names(spell_text)
        for name in spell_names:
            spell = EnemySpell.objects.create(
                enemy=monster,
                name=name,
                save_dc=save_dc
            )
            EnemySpellSlot.objects.create(
                spell=spell,
                level=level,
                uses=slots
            )
    
    def _parse_spell_names(self, spell_text):
        """Extract spell names from comma-separated text"""
        import re
        
        # Remove asterisks and parentheticals
        cleaned = re.sub(r'\*', '', spell_text)
        cleaned = re.sub(r'\([^)]+\)', '', cleaned)
        
        # Split by comma or "and"
        cleaned = cleaned.replace(' and ', ', ')
        spells = [s.strip() for s in cleaned.split(',')]
        
        # Filter out empty strings and clean
        spell_names = []
        for s in spells:
            s = s.strip()
            if s and len(s) > 1:
                # Title case for consistency
                spell_names.append(s.title())
        
        return spell_names
