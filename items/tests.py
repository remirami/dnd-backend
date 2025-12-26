from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from items.models import Item, Weapon, Armor, Consumable, ItemCategory, ItemProperty
from bestiary.models import DamageType


class ItemModelTests(TestCase):
    """Test item models"""
    
    def setUp(self):
        self.category = ItemCategory.objects.create(name='Weapon', description='Combat items')
        self.property = ItemProperty.objects.create(name='Finesse', description='Use DEX instead of STR')
        self.damage_type = DamageType.objects.create(name='Piercing')
    
    def test_create_weapon(self):
        """Test creating a weapon"""
        weapon = Weapon.objects.create(
            name='Shortsword',
            category=self.category,
            weapon_type='martial_melee',
            damage_dice='1d6',
            damage_type=self.damage_type,
            finesse=True,
            weight=2.0,
            value=10
        )
        weapon.properties.add(self.property)
        
        self.assertEqual(weapon.name, 'Shortsword')
        self.assertTrue(weapon.finesse)
        self.assertIn(self.property, weapon.properties.all())
    
    def test_create_armor(self):
        """Test creating armor"""
        armor = Armor.objects.create(
            name='Leather Armor',
            category=self.category,
            armor_type='light',
            base_ac=11,
            weight=10.0,
            value=10
        )
        
        self.assertEqual(armor.name, 'Leather Armor')
        self.assertEqual(armor.base_ac, 11)
        self.assertEqual(armor.armor_type, 'light')
    
    def test_create_consumable(self):
        """Test creating a consumable"""
        consumable = Consumable.objects.create(
            name='Healing Potion',
            category=self.category,
            consumable_type='potion',
            effect='Restores 2d4+2 hit points',
            weight=0.5,
            value=50
        )
        
        self.assertEqual(consumable.name, 'Healing Potion')
        self.assertEqual(consumable.consumable_type, 'potion')


class ItemAPITests(APITestCase):
    """Test item API endpoints"""
    
    def setUp(self):
        self.category = ItemCategory.objects.create(name='Weapon')
        self.damage_type = DamageType.objects.create(name='Slashing')
        self.weapon = Weapon.objects.create(
            name='Longsword',
            category=self.category,
            weapon_type='martial_melee',
            damage_dice='1d8',
            damage_type=self.damage_type,
            weight=3.0,
            value=15
        )
    
    def test_list_weapons(self):
        """Test listing weapons"""
        response = self.client.get('/api/weapons/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_get_weapon(self):
        """Test getting a specific weapon"""
        response = self.client.get(f'/api/weapons/{self.weapon.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Longsword')
    
    def test_filter_weapons_by_type(self):
        """Test filtering weapons by type"""
        response = self.client.get('/api/weapons/?weapon_type=martial_melee')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_list_items(self):
        """Test listing all items"""
        response = self.client.get('/api/items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_armor(self):
        """Test listing armor"""
        Armor.objects.create(
            name='Leather Armor',
            category=self.category,
            armor_type='light',
            base_ac=11,
            weight=10.0,
            value=10
        )
        response = self.client.get('/api/armor/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
