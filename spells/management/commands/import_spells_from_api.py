import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from spells.models import Spell, SpellDamage
from characters.models import CharacterClass
from bestiary.models import DamageType


class Command(BaseCommand):
    help = 'Import spells from Open5e API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='open5e',
            help='API source (currently only open5e supported)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview spells without importing'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of spells to import'
        )

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        limit = options['limit']

        if source == 'open5e':
            self.import_from_open5e(dry_run, limit)
        else:
            self.stdout.write(self.style.ERROR(f'Unknown source: {source}'))

    def import_from_open5e(self, dry_run=False, limit=None):
        """Import spells from Open5e API"""
        self.stdout.write('Fetching spells from Open5e API...')
        
        base_url = 'https://api.open5e.com/spells'
        all_spells = []
        next_url = base_url
        
        # Fetch all pages
        while next_url:
            try:
                response = requests.get(next_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                all_spells.extend(data.get('results', []))
                next_url = data.get('next')
                
                self.stdout.write(f'Fetched {len(all_spells)} spells so far...')
                
                if limit and len(all_spells) >= limit:
                    all_spells = all_spells[:limit]
                    break
                    
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Error fetching spells: {e}'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(all_spells)} spells'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No spells will be imported'))
            for spell_data in all_spells[:10]:  # Show first 10
                self.stdout.write(f"  - {spell_data.get('name')} (Level {spell_data.get('level')})")
            return
        
        # Import spells
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for spell_data in all_spells:
            try:
                spell_name = spell_data.get('name', '').strip()
                if not spell_name:
                    skipped_count += 1
                    continue
                
                # Map Open5e data to our model
                spell_defaults = {
                    'slug': spell_data.get('slug', slugify(spell_name)),
                    'level': self._parse_level(spell_data.get('level', 0)),
                    'school': self._parse_school(spell_data.get('school', '')),
                    'casting_time': spell_data.get('casting_time', '1 action'),
                    'range': spell_data.get('range', 'Self'),
                    'components': spell_data.get('components', 'V, S'),
                    'material': spell_data.get('material', ''),
                    'duration': spell_data.get('duration', 'Instantaneous'),
                    'concentration': 'concentration' in spell_data.get('duration', '').lower(),
                    'ritual': spell_data.get('ritual', 'no').lower() == 'yes',
                    'description': spell_data.get('desc', ''),
                    'higher_level': spell_data.get('higher_level', ''),
                    'source': spell_data.get('document__slug', 'PHB'),
                    'page': spell_data.get('page', ''),
                }
                
                # Create or update spell
                spell, created = Spell.objects.update_or_create(
                    name=spell_name,
                    defaults=spell_defaults
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  Created: {spell_name}')
                else:
                    updated_count += 1
                    self.stdout.write(f'  Updated: {spell_name}')
                
                # Add classes that can learn this spell
                if 'dnd_class' in spell_data and spell_data['dnd_class']:
                    self._add_spell_classes(spell, spell_data['dnd_class'])
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing {spell_name}: {e}'))
                skipped_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\nImport complete!\n'
            f'  Created: {created_count}\n'
            f'  Updated: {updated_count}\n'
            f'  Skipped: {skipped_count}'
        ))

    def _parse_level(self, level_str):
        """Parse spell level from Open5e format"""
        if isinstance(level_str, int):
            return level_str
        
        level_str = str(level_str).lower()
        if 'cantrip' in level_str:
            return 0
        
        # Extract number from string like "1st-level" or "2nd-level"
        for i in range(10):
            if str(i) in level_str:
                return i
        
        return 0

    def _parse_school(self, school_str):
        """Parse spell school from Open5e format"""
        school_str = str(school_str).lower().strip()
        
        valid_schools = [
            'abjuration', 'conjuration', 'divination', 'enchantment',
            'evocation', 'illusion', 'necromancy', 'transmutation'
        ]
        
        for school in valid_schools:
            if school in school_str:
                return school
        
        return 'evocation'  # Default fallback

    def _add_spell_classes(self, spell, class_string):
        """Add classes that can learn this spell"""
        if not class_string:
            return
        
        # Parse class string (may be comma-separated)
        class_names = [c.strip().lower() for c in class_string.split(',')]
        
        for class_name in class_names:
            try:
                char_class = CharacterClass.objects.filter(name__iexact=class_name).first()
                if char_class:
                    spell.classes.add(char_class)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not add class {class_name}: {e}'))
