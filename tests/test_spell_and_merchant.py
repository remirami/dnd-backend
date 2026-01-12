"""
Test suite for Spell Library and Merchant System
Tests spell imports, merchant discovery, weight progression, and purchases
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from spells.models import Spell, SpellDamage
from merchants.models import MerchantEncounter, MerchantInventoryItem, MerchantTransaction
from merchants.rarity_weights import get_rarity_weights, select_random_items, generate_merchant_name
from campaigns.models import Campaign, CampaignCharacter
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from items.models import Item


class SpellLibraryTests(TransactionTestCase):
    """Test spell library functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
   
    def test_create_spell(self):
        """Test creating a spell"""
        spell = Spell.objects.create(
            name="Fireball",
            slug="fireball",
            level=3,
            school='evocation',
            casting_time='1 action',
            range='150 feet',
            components='V, S, M',
            material='a tiny ball of bat guano and sulfur',
            duration='Instantaneous',
            description='A bright streak flashes from your pointing finger...',
            concentration=False,
            ritual=False
        )
        
        self.assertEqual(spell.name, "Fireball")
        self.assertEqual(spell.level, 3)
        self.assertFalse(spell.concentration)
    
    def test_spell_api_list(self):
        """Test listing spells via API"""
        Spell.objects.create(
            name="Magic Missile",
            slug="magic-missile",
            level=1,
            school='evocation',
            casting_time='1 action',
            range='120 feet',
            components='V, S',
            duration='Instantaneous',
            description='You create three glowing darts...'
        )
        
        response = self.client.get('/api/spells/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_spell_filtering(self):
        """Test filtering spells by level and school"""
        Spell.objects.create(
            name="Cure Wounds",
            slug="cure-wounds",
            level=1,
            school='evocation',
            casting_time='1 action',
            range='Touch',
            components='V, S',
            duration='Instantaneous',
            description='A creature you touch regains hit points...'
        )
        Spell.objects.create(
            name="Fireball",
            slug="fireball",
            level=3,
            school='evocation',
            casting_time='1 action',
            range='150 feet',
            components='V, S, M',
            duration='Instantaneous',
            description='A bright streak flashes...'
        )
        
        # Filter by level
        response = self.client.get('/api/spells/?level=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by school
        response = self.client.get('/api/spells/?school=evocation')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)


class MerchantRarityTests(TestCase):
    """Test merchant rarity weight system"""
    
    def test_early_encounter_weights(self):
        """Test rarity weights for early encounters (1-3)"""
        weights = get_rarity_weights(1)
        self.assertEqual(weights['common'], 70)
        self.assertEqual(weights['uncommon'], 25)
        self.assertEqual(weights['rare'], 5)
        self.assertEqual(weights['legendary'], 0)
    
    def test_mid_encounter_weights(self):
        """Test rarity weights for mid encounters (4-6)"""
        weights = get_rarity_weights(5)
        self.assertEqual(weights['common'], 40)
        self.assertEqual(weights['uncommon'], 40)
        self.assertEqual(weights['rare'], 15)
        self.assertEqual(weights['very_rare'], 5)
    
    def test_late_encounter_weights(self):
        """Test rarity weights for late encounters (7-9)"""
        weights = get_rarity_weights(8)
        self.assertEqual(weights['common'], 15)
        self.assertEqual(weights['rare'], 35)
        self.assertEqual(weights['legendary'], 3)
    
    def test_endgame_encounter_weights(self):
        """Test rarity weights for endgame encounters (10+)"""
        weights = get_rarity_weights(12)
        self.assertEqual(weights['common'], 5)
        self.assertEqual(weights['legendary'], 13)
        self.assertEqual(weights['artifact'], 2)
    
    def test_merchant_name_generation(self):
        """Test merchant name generation"""
        name = generate_merchant_name()
        self.assertIsInstance(name, str)
        self.assertIn(' ', name)  # Should have space between prefix and suffix


class MerchantSystemTests(TransactionTestCase):
    """Test merchant system functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        
        # Create character class and race
        self.char_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR, CON'
        )
        self.race = CharacterRace.objects.create(
            name='human',
            speed=30
        )
        
        # Create character
        self.character = Character.objects.create(
            user=self.user,
            name='Test Hero',
            level=1,
            character_class=self.char_class,
            race=self.race
        )
        
        # Create character stats
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=15,
            dexterity=14,
            constitution=13,
            intelligence=12,
            wisdom=10,
            charisma=8,
            hit_points=15,
            max_hit_points=15,
            armor_class=14  # Added missing field
        )
        
        # Create campaign
        self.campaign = Campaign.objects.create(
            owner=self.user,
            name='Test Gauntlet',
            starting_level=1,
            status='active'
        )
        
        # Add character to campaign
        self.campaign_char = CampaignCharacter.objects.create(
            campaign=self.campaign,
            character=self.character,
            current_hp=15,
            max_hp=15,
            gold=100  # Give character gold for testing
        )
        
        # Create items with different rarities
        self.common_item = Item.objects.create(
            name='Iron Sword',
            rarity='common',
            value=10
        )
        self.rare_item = Item.objects.create(
            name='Flame Tongue',
            rarity='rare',
            value=500
        )
    
    def test_merchant_discovery(self):
        """Test discovering a merchant in campaign"""
        response = self.client.post(f'/api/campaigns/{self.campaign.id}/discover_merchant/')
        self.assertEqual(response.status_code, 201)
        self.assertIn('merchant', response.data)
        self.assertIn('Merchant discovered:', response.data['message'])
        
        # Verify merchant was created
        merchant = MerchantEncounter.objects.get(campaign=self.campaign)
        self.assertEqual(merchant.encounter_number, 1)
        self.assertTrue(merchant.is_active)
    
    def test_merchant_inventory_generation(self):
        """Test that merchant generates inventory"""
        merchant = MerchantEncounter.objects.create(
            campaign=self.campaign,
            encounter_number=1,
            merchant_name="Test Merchant"
        )
        
        merchant.generate_inventory(count=5)
        inventory_count = merchant.inventory.count()
        self.assertEqual(inventory_count, 5)
    
    def test_purchase_item(self):
        """Test purchasing an item from merchant"""
        # Create merchant with inventory
        merchant = MerchantEncounter.objects.create(
            campaign=self.campaign,
            encounter_number=1,
            merchant_name="Test Merchant"
        )
        
        inventory_item = MerchantInventoryItem.objects.create(
            merchant=merchant,
            item=self.common_item,
            price=20,
            quantity=1
        )
        
        # Purchase the item
        response = self.client.post(f'/api/merchants/{merchant.id}/purchase/', {
            'inventory_item_id': inventory_item.id,
            'campaign_character_id': self.campaign_char.id
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Purchase successful', response.data['message'])
        
        # Verify gold was deducted
        self.campaign_char.refresh_from_db()
        self.assertEqual(self.campaign_char.gold, 80)  # 100 - 20
        
        # Verify item is marked as sold
        inventory_item.refresh_from_db()
        self.assertTrue(inventory_item.is_sold)
    
    def test_purchase_insufficient_gold(self):
        """Test purchase fails with insufficient gold"""
        merchant = MerchantEncounter.objects.create(
            campaign=self.campaign,
            encounter_number=1,
            merchant_name="Test Merchant"
        )
        
        inventory_item = MerchantInventoryItem.objects.create(
            merchant=merchant,
            item=self.rare_item,
            price=500,
            quantity=1
        )
        
        # Try to purchase (character only has 100 gold)
        response = self.client.post(f'/api/merchants/{merchant.id}/purchase/', {
            'inventory_item_id': inventory_item.id,
            'campaign_character_id': self.campaign_char.id
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Not enough gold', response.data['error'])
    
    def test_merchant_transaction_record(self):
        """Test that transactions are recorded"""
        merchant = MerchantEncounter.objects.create(
            campaign=self.campaign,
            encounter_number=1,
            merchant_name="Test Merchant"
        )
        
        inventory_item = MerchantInventoryItem.objects.create(
            merchant=merchant,
            item=self.common_item,
            price=20,
            quantity=1
        )
        
        response = self.client.post(f'/api/merchants/{merchant.id}/purchase/', {
            'inventory_item_id': inventory_item.id,
            'campaign_character_id': self.campaign_char.id
        })
        
        # Verify transaction was recorded
        transaction = MerchantTransaction.objects.get(merchant=merchant)
        self.assertEqual(transaction.item_name, 'Iron Sword')
        self.assertEqual(transaction.price, 20)

