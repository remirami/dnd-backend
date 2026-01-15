"""
Test Character Sheet Endpoint
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from characters.models import (
    Character, CharacterClass, CharacterRace, CharacterBackground,
    CharacterStats, CharacterProficiency, CharacterFeature
)


class CharacterSheetEndpointTests(TestCase):
    """Test the character sheet endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.char_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        self.race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
        
        self.background = CharacterBackground.objects.create(
            name='soldier',
            skill_proficiencies='Athletics,Intimidation'
        )
        
        # Create character
        self.character = Character.objects.create(
            user=self.user,
            name='Test Fighter',
            character_class=self.char_class,
            race=self.race,
            background=self.background,
            level=5,
            alignment='LG'
        )
        
        # Create stats
        CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
            hit_points=45,
            max_hit_points=50,
            armor_class=18,
            speed=30
        )
        
        # Add proficiencies
        CharacterProficiency.objects.create(
            character=self.character,
            proficiency_type='skill',
            skill_name='Athletics'
        )
        
        # Add feature
        CharacterFeature.objects.create(
            character=self.character,
            name='Second Wind',
            feature_type='class',
            description='Recover hit points',
            source='Fighter Level 1'
        )
    
    def test_character_sheet_endpoint(self):
        """Test GET /api/characters/{id}/sheet/"""
        response = self.client.get(f'/api/characters/{self.character.id}/sheet/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check basic info
        self.assertEqual(response.data['name'], 'Test Fighter')
        self.assertEqual(response.data['level'], 5)
        self.assertEqual(response.data['race_name'], 'Human')
        self.assertEqual(response.data['class_name'], 'Fighter')
        
        # Check ability scores
        self.assertIn('ability_scores', response.data)
        self.assertEqual(response.data['ability_scores']['strength']['score'], 16)
        self.assertEqual(response.data['ability_scores']['strength']['modifier'], 3)
        
        # Check combat stats
        self.assertIn('combat_stats', response.data)
        self.assertEqual(response.data['combat_stats']['hit_points']['current'], 45)
        self.assertEqual(response.data['combat_stats']['hit_points']['maximum'], 50)
        self.assertEqual(response.data['combat_stats']['armor_class'], 18)
        
        # Check proficiency bonus (level 5 = +3)
        self.assertEqual(response.data['proficiency_bonus'], 3)
        
        # Check saving throws
        self.assertIn('saving_throws', response.data)
        # STR save: +3 mod + +3 prof = +6
        self.assertEqual(response.data['saving_throws']['strength']['modifier'], 6)
        self.assertTrue(response.data['saving_throws']['strength']['proficient'])
        
        # Check skills
        self.assertIn('skills', response.data)
        # Athletics: +3 STR + +3 prof = +6
        self.assertEqual(response.data['skills']['Athletics']['modifier'], 6)
        self.assertTrue(response.data['skills']['Athletics']['proficient'])
        
        # Check features
        self.assertIn('features', response.data)
        self.assertTrue(any(f['name'] == 'Second Wind' for f in response.data['features']))
    
    def test_unauthenticated_access_denied(self):
        """Test unauthenticated users cannot access character sheet"""
        client = APIClient()
        
        response = client.get(f'/api/characters/{self.character.id}/sheet/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
