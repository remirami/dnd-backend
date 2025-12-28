import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from items.models import (
    Item, ItemCategory, ItemProperty, Weapon, Armor, Consumable, MagicItem, DamageType
)


class Command(BaseCommand):
    help = 'Import items from Open5e API (free, no API key required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['open5e', 'json'],
            default='open5e',
            help='Source for item import'
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
            help='Update existing items instead of skipping'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of items to import (for testing)'
        )

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        limit = options.get('limit')

        if not REQUESTS_AVAILABLE and source == 'open5e':
            raise CommandError('Requests library not available. Install with: pip install requests')

        try:
            if source == 'open5e':
                self.import_from_open5e(dry_run, update_existing, limit)
            elif source == 'json':
                self.import_from_json(options['file'], dry_run, update_existing)
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def import_from_open5e(self, dry_run, update_existing, limit=None):
        """Import items from Open5e API"""
        self.stdout.write('Fetching items from Open5e API...')
        
        # Open5e API endpoints
        base_url = 'https://api.open5e.com'
        endpoints = {
            'magic-items': f'{base_url}/magicitems/',
            'weapons': f'{base_url}/weapons/',
            'armor': f'{base_url}/armor/',
        }
        
        all_items = []
        
        for item_type, url in endpoints.items():
            self.stdout.write(f'Fetching {item_type}...')
            items = self._fetch_paginated_data(url, limit)
            all_items.extend([(item, item_type) for item in items])
            self.stdout.write(f'  Found {len(items)} {item_type}')
        
        self.stdout.write(f'\nTotal items to process: {len(all_items)}')
        self.process_items(all_items, dry_run, update_existing)

    def _fetch_paginated_data(self, url, limit=None):
        """Fetch all pages of data from Open5e API"""
        items = []
        page = 1
        
        while url:
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                items.extend(results)
                
                self.stdout.write(f'  Page {page}: {len(results)} items')
                
                # Check if we've hit the limit
                if limit and len(items) >= limit:
                    items = items[:limit]
                    break
                
                # Get next page
                url = data.get('next')
                page += 1
                
            except requests.RequestException as e:
                self.stdout.write(self.style.WARNING(f'Failed to fetch page {page}: {str(e)}'))
                break
        
        return items

    def import_from_json(self, file_path, dry_run, update_existing):
        """Import items from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON: {str(e)}')

        if isinstance(data, list):
            items = [(item, 'unknown') for item in data]
        elif isinstance(data, dict) and 'items' in data:
            items = [(item, 'unknown') for item in data['items']]
        else:
            items = [(data, 'unknown')]

        self.process_items(items, dry_run, update_existing)

    def process_items(self, items, dry_run, update_existing):
        """Process and import item data"""
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for item_data, item_type in items:
            try:
                if dry_run:
                    self.stdout.write(f'[DRY RUN] Would import: {item_data.get("name", "Unknown")}')
                    continue

                with transaction.atomic():
                    item, created = self.create_or_update_item(item_data, item_type, update_existing)
                    
                    if item:
                        if created:
                            imported_count += 1
                            self.stdout.write(f'[+] Imported: {item.name}')
                        elif update_existing:
                            updated_count += 1
                            self.stdout.write(f'[*] Updated: {item.name}')
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'[!] Failed to import {item_data.get("name", "Unknown")}: {str(e)}')
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

    def create_or_update_item(self, data, item_type, update_existing):
        """Create or update an item from data"""
        name = data.get('name', 'Unknown Item')
        
        # Check if item exists
        try:
            item = Item.objects.get(name=name)
            if not update_existing:
                return item, False
        except Item.DoesNotExist:
            item = None

        # Determine rarity
        rarity = self._parse_rarity(data.get('rarity', 'common'))
        
        # Determine if magical
        is_magical = item_type == 'magic-items' or rarity in ['uncommon', 'rare', 'very_rare', 'legendary', 'artifact']
        
        # Get or create category
        category = self._get_or_create_category(item_type, data)
        
        # Parse description
        description = data.get('desc', '')
        if isinstance(description, list):
            description = '\n'.join(description)
        
        # Basic item data
        item_data = {
            'name': name,
            'description': description,
            'category': category,
            'rarity': rarity,
            'is_magical': is_magical,
            'requires_attunement': data.get('requires_attunement', False),
        }
        
        # Try to parse weight and value
        weight = self._parse_weight(data.get('weight'))
        if weight:
            item_data['weight'] = weight
        
        # Estimate value based on rarity if not provided
        value = self._parse_value(data.get('cost', data.get('value')))
        if not value:
            value = self._estimate_value_from_rarity(rarity)
        item_data['value'] = value
        
        # Create appropriate item type
        if item_type == 'weapons':
            return self._create_weapon(item_data, data, update_existing)
        elif item_type == 'armor':
            return self._create_armor(item_data, data, update_existing)
        elif item_type == 'magic-items':
            return self._create_magic_item(item_data, data, update_existing)
        else:
            # Generic item
            if item:
                for key, value in item_data.items():
                    setattr(item, key, value)
                item.save()
                return item, False
            else:
                item = Item.objects.create(**item_data)
                return item, True

    def _create_weapon(self, item_data, data, update_existing):
        """Create or update a weapon"""
        name = item_data['name']
        
        # Parse damage
        damage_dice = data.get('damage_dice', '1d4')
        damage_type_name = data.get('damage_type', 'Slashing')
        
        # Get or create damage type
        damage_type, _ = DamageType.objects.get_or_create(
            name=damage_type_name
        )
        
        weapon_data = {
            **item_data,
            'damage_dice': damage_dice,
            'damage_type': damage_type,
            'weapon_type': data.get('category', 'simple'),
            'range_normal': data.get('range', '5'),
        }
        
        try:
            weapon = Weapon.objects.get(name=name)
            if update_existing:
                for key, value in weapon_data.items():
                    setattr(weapon, key, value)
                weapon.save()
                return weapon, False
            return weapon, False
        except Weapon.DoesNotExist:
            weapon = Weapon.objects.create(**weapon_data)
            
            # Add properties
            self._add_weapon_properties(weapon, data)
            
            return weapon, True

    def _create_armor(self, item_data, data, update_existing):
        """Create or update armor"""
        name = item_data['name']
        
        # Parse AC
        ac_base = self._parse_ac(data.get('armor_class', {}).get('base', 11))
        
        armor_data = {
            **item_data,
            'armor_class': ac_base,
            'armor_type': data.get('armor_category', 'light'),
            'strength_requirement': data.get('strength_requirement'),
            'stealth_disadvantage': data.get('stealth_disadvantage', False),
        }
        
        try:
            armor = Armor.objects.get(name=name)
            if update_existing:
                for key, value in armor_data.items():
                    setattr(armor, key, value)
                armor.save()
                return armor, False
            return armor, False
        except Armor.DoesNotExist:
            armor = Armor.objects.create(**armor_data)
            return armor, True

    def _create_magic_item(self, item_data, data, update_existing):
        """Create or update a magic item"""
        name = item_data['name']
        
        magic_data = {
            **item_data,
            'attunement_required': data.get('requires_attunement', False),
        }
        
        # Try to parse magical properties from description
        desc = item_data.get('description', '').lower()
        if 'bonus to attack' in desc or '+1' in desc or '+2' in desc or '+3' in desc:
            # Try to extract bonus
            import re
            bonus_match = re.search(r'\+(\d+)', desc)
            if bonus_match:
                bonus = int(bonus_match.group(1))
                magic_data['bonus_to_hit'] = bonus
                magic_data['bonus_to_damage'] = bonus
        
        try:
            magic_item = MagicItem.objects.get(name=name)
            if update_existing:
                for key, value in magic_data.items():
                    setattr(magic_item, key, value)
                magic_item.save()
                return magic_item, False
            return magic_item, False
        except MagicItem.DoesNotExist:
            magic_item = MagicItem.objects.create(**magic_data)
            return magic_item, True

    def _get_or_create_category(self, item_type, data):
        """Get or create item category"""
        category_map = {
            'weapons': 'Weapon',
            'armor': 'Armor',
            'magic-items': 'Magic Item',
        }
        
        category_name = category_map.get(item_type, 'Adventuring Gear')
        
        # Check if there's a more specific category in the data
        if 'category' in data:
            specific_category = data['category'].title()
            category, _ = ItemCategory.objects.get_or_create(
                name=specific_category,
                defaults={'description': f'{specific_category} items'}
            )
            return category
        
        category, _ = ItemCategory.objects.get_or_create(
            name=category_name,
            defaults={'description': f'{category_name} items'}
        )
        return category

    def _add_weapon_properties(self, weapon, data):
        """Add weapon properties"""
        properties_text = data.get('properties', '')
        if isinstance(properties_text, list):
            properties_text = ', '.join(properties_text)
        
        property_keywords = {
            'versatile': 'Versatile',
            'finesse': 'Finesse',
            'two-handed': 'Two-Handed',
            'light': 'Light',
            'heavy': 'Heavy',
            'reach': 'Reach',
            'thrown': 'Thrown',
            'ammunition': 'Ammunition',
            'loading': 'Loading',
        }
        
        for keyword, prop_name in property_keywords.items():
            if keyword in properties_text.lower():
                prop, _ = ItemProperty.objects.get_or_create(
                    name=prop_name,
                    defaults={'description': f'{prop_name} weapon property'}
                )
                weapon.properties.add(prop)

    def _parse_rarity(self, rarity_str):
        """Parse rarity string to match model choices"""
        if not rarity_str:
            return 'common'
        
        rarity_map = {
            'common': 'common',
            'uncommon': 'uncommon',
            'rare': 'rare',
            'very rare': 'very_rare',
            'legendary': 'legendary',
            'artifact': 'artifact',
        }
        
        return rarity_map.get(rarity_str.lower(), 'common')

    def _parse_weight(self, weight_str):
        """Parse weight string to decimal"""
        if not weight_str:
            return None
        
        try:
            # Handle formats like "2 lb.", "2.5 lbs", "2"
            import re
            match = re.search(r'(\d+\.?\d*)', str(weight_str))
            if match:
                return float(match.group(1))
        except:
            pass
        
        return None

    def _parse_value(self, value_str):
        """Parse value string to integer (gold pieces)"""
        if not value_str:
            return None
        
        try:
            # Handle formats like "50 gp", "5 sp", "100"
            import re
            match = re.search(r'(\d+)', str(value_str))
            if match:
                value = int(match.group(1))
                
                # Convert to gold pieces
                if 'sp' in str(value_str).lower():
                    value = value // 10  # 10 sp = 1 gp
                elif 'cp' in str(value_str).lower():
                    value = value // 100  # 100 cp = 1 gp
                
                return value
        except:
            pass
        
        return None

    def _parse_ac(self, ac_value):
        """Parse AC value"""
        if isinstance(ac_value, int):
            return ac_value
        
        try:
            import re
            match = re.search(r'(\d+)', str(ac_value))
            if match:
                return int(match.group(1))
        except:
            pass
        
        return 10

    def _estimate_value_from_rarity(self, rarity):
        """Estimate item value based on rarity"""
        value_map = {
            'common': 50,
            'uncommon': 200,
            'rare': 2000,
            'very_rare': 20000,
            'legendary': 50000,
            'artifact': 100000,
        }
        
        return value_map.get(rarity, 50)

