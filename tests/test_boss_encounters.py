"""
Tests for Boss Encounter Integration in Campaign System
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from campaigns.models import Campaign, CampaignEncounter
from campaigns.services.campaign_generator import CampaignGenerator
from campaigns.boss_encounters import get_random_boss_for_biome, get_all_bosses_for_biome
from bestiary.models import Enemy, EnemyStats
from encounters.models import EncounterTheme, EnemyThemeAssociation
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats


class BossEncounterDataTests(TestCase):
    """Test boss encounter data structures"""
    
    def test_all_biomes_have_bosses(self):
        """Test that all defined biomes have boss encounters"""
        biomes = ['forest', 'desert', 'mountain', 'swamp', 'plains', 'underdark', 'urban', 'arctic']
        
        for biome in biomes:
            bosses = get_all_bosses_for_biome(biome)
            self.assertGreater(len(bosses), 0, f"{biome} should have at least one boss")
    
    def test_boss_variety_per_biome(self):
        """Test that biomes have multiple boss variants"""
        biomes_with_multiple = ['forest', 'desert', 'swamp', 'underdark']
        
        for biome in biomes_with_multiple:
            bosses = get_all_bosses_for_biome(biome)
            self.assertGreaterEqual(len(bosses), 2, f"{biome} should have at least 2 boss variants")
    
    def test_random_boss_selection(self):
        """Test random boss selection returns valid data"""
        boss = get_random_boss_for_biome('forest')
        
        self.assertIn('name', boss)
        self.assertIn('boss_enemy_name', boss)
        self.assertIn('minions', boss)
        self.assertIn('flavor_text', boss)
        self.assertIn('loot', boss)
        
        # Verify loot structure
        self.assertIn('guaranteed_items', boss['loot'])
        self.assertIn('gold', boss['loot'])
        self.assertIn('xp_multiplier', boss['loot'])


class CampaignGeneratorTests(TestCase):
    """Test campaign generation with bosses"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.generator = CampaignGenerator()
        
        # Create test enemies and theme
        self.create_test_data()
    
    def create_test_data(self):
        """Create minimal test data"""
        # Create a theme
        self.theme = EncounterTheme.objects.create(
            name="Test Theme",
            category="beast",
            min_cr=1,
            max_cr=10
        )
        
        # Create test enemy
        self.enemy = Enemy.objects.create(
            name="Test Beast",
            creature_type="beast",
            challenge_rating="3"
        )
        EnemyStats.objects.create(
            enemy=self.enemy,
            hit_points=50,
            armor_class=14
        )
        
        # Associate with theme
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="support"
        )
    
    def test_generate_gauntlet(self):
        """Test generating a complete gauntlet"""
        campaign = self.generator.generate_gauntlet(
            biome='forest',
            party_level=5,
            party_size=4,
            encounter_count=5,
            owner=self.user
        )
        
        self.assertEqual(campaign.biome, 'forest')
        self.assertEqual(campaign.starting_level, 5)
        self.assertEqual(campaign.starting_party_size, 4)
        
        # Should have 6 encounters (5 regular + 1 boss)
        encounters = campaign.campaign_encounters.all()
        self.assertEqual(encounters.count(), 6)
        
        # Last encounter should be boss
        boss = encounters.last()
        self.assertTrue(boss.is_boss)
        self.assertTrue(len(boss.boss_loot_table) > 0)
    
    def test_difficulty_progression(self):
        """Test encounters get progressively harder"""
        campaign = self.generator.generate_gauntlet(
            biome='desert',
            party_level=5,
            party_size=4,
            encounter_count=5
        )
        
        # Check difficulty progression
        diff1 = self.generator._get_difficulty_for_encounter(0, 5)
        diff2 = self.generator._get_difficulty_for_encounter(1, 5)
        diff3 = self.generator._get_difficulty_for_encounter(4, 5)
        
        self.assertEqual(diff1, 'easy')
        self.assertEqual(diff2, 'medium')
        self.assertEqual(diff3, 'deadly')
    
    def test_boss_has_enemies(self):
        """Test boss encounter includes boss and minions"""
        campaign = self.generator.generate_gauntlet(
            biome='mountain',
            party_level=3,
            party_size=4,
            encounter_count=3
        )
        
        boss_campaign_encounter = campaign.campaign_encounters.filter(is_boss=True).first()
        boss_encounter = boss_campaign_encounter.encounter
        
        # Should have at least 1 enemy (the boss)
        self.assertGreater(boss_encounter.enemies.count(), 0)


class CampaignAPITests(TestCase):
    """Test campaign API endpoints with boss support"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        theme = EncounterTheme.objects.create(
            name="Test Theme",
            category="humanoid",
            min_cr=1,
            max_cr=10
        )
        
        enemy = Enemy.objects.create(
            name="Test Human",
            creature_type="humanoid",
            challenge_rating="1"
        )
        EnemyStats.objects.create(enemy=enemy, hit_points=10, armor_class=12)
        
        EnemyThemeAssociation.objects.create(
            theme=theme,
            enemy=enemy,
            role="support"
        )
    
    def test_generate_gauntlet_api(self):
        """Test generate-gauntlet API endpoint"""
        response = self.client.post('/api/campaigns/generate-gauntlet/', {
            'biome': 'forest',
            'party_level': 5,
            'party_size': 4,
            'encounter_count': 5
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('campaign', response.data)
        self.assertIn('boss_encounter', response.data)
        self.assertEqual(response.data['encounters'], 6)
    
    def test_generate_gauntlet_missing_biome(self):
        """Test validation for missing biome"""
        response = self.client.post('/api/campaigns/generate-gauntlet/', {
            'party_level': 5,
            'party_size': 4
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_generate_gauntlet_invalid_party_level(self):
        """Test validation for invalid party level"""
        response = self.client.post('/api/campaigns/generate-gauntlet/', {
            'biome': 'forest',
            'party_level': 25,  # Too high
            'party_size': 4
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_generate_gauntlet_custom_name(self):
        """Test generating gauntlet with custom name"""
        response = self.client.post('/api/campaigns/generate-gauntlet/', {
            'biome': 'desert',
            'party_level': 3,
            'party_size': 2,
            'name': 'My Custom Gauntlet'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        campaign = Campaign.objects.get(id=response.data['campaign']['id'])
        self.assertEqual(campaign.name, 'My Custom Gauntlet')
