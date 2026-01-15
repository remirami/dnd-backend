"""
Tests for Encounter API Endpoints

Tests the REST API endpoints for encounter generation
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from encounters.models import (
    EncounterTheme, EnemyThemeAssociation, BiomeEncounterWeight
)
from bestiary.models import Enemy, EnemyStats


class EncounterGenerateAPITests(TestCase):
    """Test the generate_encounter API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create theme with enemies
        self.theme = EncounterTheme.objects.create(
            name="Test Theme",
            category="humanoid",
            description="Test",
            min_cr=1,
            max_cr=10
        )
        
        self.enemy = Enemy.objects.create(
            name="Test Enemy",
            creature_type="humanoid",
            challenge_rating="2"
        )
        EnemyStats.objects.create(
            enemy=self.enemy,
            hit_points=20,
            armor_class=14
        )
        
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="support"
        )
    
    def test_generate_encounter_success(self):
        """Test successful encounter generation"""
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 5,
                'party_size': 4,
                'difficulty': 'medium'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('encounter', response.data)
        self.assertIn('message', response.data)
    
    def test_generate_with_biome(self):
        """Test generating encounter for specific biome"""
        # Create biome weight
        BiomeEncounterWeight.objects.create(
            biome='forest',
            theme=self.theme,
            category='endemic'
        )
        
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 3,
                'party_size': 4,
                'biome': 'forest'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['encounter']['biome'], 'forest')
    
    def test_generate_with_forced_theme(self):
        """Test forcing specific theme"""
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 5,
                'party_size': 4,
                'force_theme_id': self.theme.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['encounter']['theme'], self.theme.id)
    
    def test_generate_missing_required_fields(self):
        """Test generation fails with missing required fields"""
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 5
                # Missing party_size
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_generate_invalid_party_level(self):
        """Test validation of party level"""
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 25,  # Too high
                'party_size': 4
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_generate_invalid_theme_id(self):
        """Test error when theme doesn't exist"""
        response = self.client.post(
            '/api/encounters/generate/',
            {
                'party_level': 5,
                'party_size': 4,
                'force_theme_id': 99999
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class EncounterThemeAPITests(TestCase):
    """Test EncounterTheme API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        self.theme1 = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws"
        )
        
        self.theme2 = EncounterTheme.objects.create(
            name="Undead Horde",
            category="undead",
            description="Zombies"
        )
    
    def test_list_themes(self):
        """Test listing all themes"""
        response = self.client.get('/api/encounter-themes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRF pagination returns results in 'results' key
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)
    
    def test_get_theme_detail(self):
        """Test getting single theme"""
        response = self.client.get(f'/api/encounter-themes/{self.theme1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Bandit Ambush")
    
    def test_get_categories(self):
        """Test getting list of categories"""
        response = self.client.get('/api/encounter-themes/categories/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
    
    def test_get_biomes(self):
        """Test getting list of biomes"""
        response = self.client.get('/api/encounter-themes/biomes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
