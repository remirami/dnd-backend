from django.core.management.base import BaseCommand
from items.models import ItemCategory, ItemProperty, Weapon, Armor, Consumable, DamageType


class Command(BaseCommand):
    help = 'Populate initial item data (categories, properties, and basic items)'
    
    def handle(self, *args, **options):
        self.stdout.write('Populating item data...')
        
        # Create categories
        categories = {
            'Weapon': 'Items used for combat',
            'Armor': 'Protective equipment',
            'Consumable': 'Items that are used up',
            'Tool': 'Utility items',
            'Adventuring Gear': 'General equipment',
            'Magic Item': 'Items with magical properties',
        }
        
        for name, desc in categories.items():
            category, created = ItemCategory.objects.get_or_create(name=name, defaults={'description': desc})
            if created:
                self.stdout.write(f'  Created category: {name}')
        
        # Create properties
        properties = {
            'Versatile': 'Can be used one-handed or two-handed',
            'Finesse': 'Can use DEX instead of STR for attack and damage',
            'Two-Handed': 'Requires two hands to use',
            'Light': 'Light weapon, can be dual-wielded',
            'Heavy': 'Heavy weapon, small creatures have disadvantage',
            'Reach': 'Extended reach (10 feet)',
            'Thrown': 'Can be thrown as a ranged weapon',
            'Ammunition': 'Requires ammunition to use',
            'Loading': 'Can only fire once per action',
        }
        
        for name, desc in properties.items():
            prop, created = ItemProperty.objects.get_or_create(name=name, defaults={'description': desc})
            if created:
                self.stdout.write(f'  Created property: {name}')
        
        # Get damage types
        slashing = DamageType.objects.filter(name__icontains='slashing').first()
        piercing = DamageType.objects.filter(name__icontains='piercing').first()
        bludgeoning = DamageType.objects.filter(name__icontains='bludgeoning').first()
        
        # Create basic weapons
        weapons = [
            {
                'name': 'Longsword',
                'weapon_type': 'martial_melee',
                'damage_dice': '1d8',
                'damage_type': slashing,
                'properties': ['Versatile'],
                'versatile_damage': '1d10',
                'weight': 3.0,
                'value': 15,
            },
            {
                'name': 'Shortsword',
                'weapon_type': 'martial_melee',
                'damage_dice': '1d6',
                'damage_type': piercing,
                'properties': ['Finesse', 'Light'],
                'weight': 2.0,
                'value': 10,
            },
            {
                'name': 'Dagger',
                'weapon_type': 'simple_melee',
                'damage_dice': '1d4',
                'damage_type': piercing,
                'properties': ['Finesse', 'Light', 'Thrown'],
                'range_normal': 20,
                'range_long': 60,
                'weight': 1.0,
                'value': 2,
            },
            {
                'name': 'Longbow',
                'weapon_type': 'martial_ranged',
                'damage_dice': '1d8',
                'damage_type': piercing,
                'properties': ['Heavy', 'Two-Handed', 'Ammunition'],
                'range_normal': 150,
                'range_long': 600,
                'weight': 2.0,
                'value': 50,
            },
        ]
        
        weapon_category = ItemCategory.objects.get(name='Weapon')
        for weapon_data in weapons:
            props = weapon_data.pop('properties', [])
            weapon, created = Weapon.objects.get_or_create(
                name=weapon_data['name'],
                defaults={**weapon_data, 'category': weapon_category}
            )
            if created:
                for prop_name in props:
                    prop = ItemProperty.objects.get(name=prop_name)
                    weapon.properties.add(prop)
                self.stdout.write(f'  Created weapon: {weapon.name}')
        
        # Create basic armor
        armor_items = [
            {
                'name': 'Leather Armor',
                'armor_type': 'light',
                'base_ac': 11,
                'max_dex_bonus': None,
                'weight': 10.0,
                'value': 10,
            },
            {
                'name': 'Chain Shirt',
                'armor_type': 'medium',
                'base_ac': 13,
                'max_dex_bonus': 2,
                'weight': 20.0,
                'value': 50,
            },
            {
                'name': 'Plate Armor',
                'armor_type': 'heavy',
                'base_ac': 18,
                'max_dex_bonus': 0,
                'min_strength': 15,
                'stealth_disadvantage': True,
                'weight': 65.0,
                'value': 1500,
            },
            {
                'name': 'Shield',
                'armor_type': 'shield',
                'base_ac': 2,
                'weight': 6.0,
                'value': 10,
            },
        ]
        
        armor_category = ItemCategory.objects.get(name='Armor')
        for armor_data in armor_items:
            armor, created = Armor.objects.get_or_create(
                name=armor_data['name'],
                defaults={**armor_data, 'category': armor_category}
            )
            if created:
                self.stdout.write(f'  Created armor: {armor.name}')
        
        # Create basic consumables
        consumables = [
            {
                'name': 'Healing Potion',
                'consumable_type': 'potion',
                'effect': 'Restores 2d4+2 hit points',
                'duration': 'Instant',
                'weight': 0.5,
                'value': 50,
            },
            {
                'name': 'Rations (1 day)',
                'consumable_type': 'food',
                'effect': 'Sustains a creature for one day',
                'weight': 2.0,
                'value': 0.5,
            },
        ]
        
        consumable_category = ItemCategory.objects.get(name='Consumable')
        for consumable_data in consumables:
            consumable, created = Consumable.objects.get_or_create(
                name=consumable_data['name'],
                defaults={**consumable_data, 'category': consumable_category}
            )
            if created:
                self.stdout.write(f'  Created consumable: {consumable.name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated item data!'))

