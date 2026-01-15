"""
Tests for Character Builder API Endpoints
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from characters.models import CharacterClass, CharacterRace, CharacterBackground
from characters.builder_models import CharacterBuilderSession


class CharacterBuilderAPITests(TestCase):
    """Test Character Builder API endpoints"""
    
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
    
    def test_start_session(self):
        """Test starting a builder session"""
        response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'standard_array'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('session_id', response.data)
        self.assertEqual(response.data['current_step'], 1)
        self.assertEqual(response.data['method'], 'standard_array')
    
    def test_start_session_invalid_method(self):
        """Test starting session with invalid method"""
        response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'invalid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_session(self):
        """Test retrieving a session"""
        # Start session first
        start_response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'point_buy'
        })
        session_id = start_response.data['session_id']
        
        # Get session
        response = self.client.get(f'/api/characters/builder/session/{session_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_id'], session_id)
        self.assertEqual(response.data['current_step'], 1)
    
    def test_delete_session(self):
        """Test deleting a session"""
        # Start session
        start_response = self.client.post('/api/characters/builder/start/', {})
        session_id = start_response.data['session_id']
        
        # Delete session
        response = self.client.delete(f'/api/characters/builder/session/{session_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it's gone
        get_response = self.client.get(f'/api/characters/builder/session/{session_id}/')
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_assign_abilities(self):
        """Test assigning ability scores"""
        # Start session
        start_response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'standard_array'
        })
        session_id = start_response.data['session_id']
        
        # Assign abilities
        response = self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_step'], 2)
        self.assertIn('modifiers', response.data)
    
    def test_assign_abilities_invalid(self):
        """Test assigning invalid abilities"""
        start_response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'standard_array'
        })
        session_id = start_response.data['session_id']
        
        # Invalid scores
        response = self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 18, 'dex': 18, 'con': 18, 'int': 18, 'wis': 18, 'cha': 18
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_choose_race(self):
        """Test choosing race"""
        # Start and assign abilities
        start_response = self.client.post('/api/characters/builder/start/', {})
        session_id = start_response.data['session_id']
        
        self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        
        # Choose race
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-race/', {
            'race_id': self.race.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_step'], 3)
        self.assertIn('racial_bonuses', response.data)
        self.assertIn('final_scores', response.data)
    
    def test_choose_class(self):
        """Test choosing class"""
        # Setup session
        start_response = self.client.post('/api/characters/builder/start/', {})
        session_id = start_response.data['session_id']
        
        self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        
        self.client.post(f'/api/characters/builder/{session_id}/choose-race/', {
            'race_id': self.race.id
        })
        
        # Choose class
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-class/', {
            'class_id': self.char_class.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_step'], 4)
        self.assertIn('class', response.data)
    
    def test_choose_background(self):
        """Test choosing background"""
        # Setup session
        start_response = self.client.post('/api/characters/builder/start/', {})
        session_id = start_response.data['session_id']
        
        self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        self.client.post(f'/api/characters/builder/{session_id}/choose-race/', {
            'race_id': self.race.id
        })
        self.client.post(f'/api/characters/builder/{session_id}/choose-class/', {
            'class_id': self.char_class.id
        })
        
        # Choose background
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-background/', {
            'background_id': self.background.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_step'], 5)
        self.assertIn('background', response.data)
    
    def test_finalize_character(self):
        """Test finalizing character creation"""
        # Complete all steps
        start_response = self.client.post('/api/characters/builder/start/', {})
        session_id = start_response.data['session_id']
        
        self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        self.client.post(f'/api/characters/builder/{session_id}/choose-race/', {
            'race_id': self.race.id
        })
        self.client.post(f'/api/characters/builder/{session_id}/choose-class/', {
            'class_id': self.char_class.id
        })
        self.client.post(f'/api/characters/builder/{session_id}/choose-background/', {
            'background_id': self.background.id
        })
        
        # Finalize
        response = self.client.post(f'/api/characters/builder/{session_id}/finalize/', {
            'name': 'Test Hero',
            'alignment': 'LG'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('character', response.data)
        self.assertEqual(response.data['character']['name'], 'Test Hero')
        
        # Verify session was deleted
        get_response = self.client.get(f'/api/characters/builder/session/{session_id}/')
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_complete_workflow(self):
        """Test complete character creation workflow"""
        # 1. Start session
        response = self.client.post('/api/characters/builder/start/', {
            'ability_score_method': 'standard_array'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['session_id']
        
        # 2. Assign abilities
        response = self.client.post(f'/api/characters/builder/{session_id}/assign-abilities/', {
            'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Choose race
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-race/', {
            'race_id': self.race.id
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Choose class
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-class/', {
            'class_id': self.char_class.id
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Choose background
        response = self.client.post(f'/api/characters/builder/{session_id}/choose-background/', {
            'background_id': self.background.id
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 6. Finalize
        response = self.client.post(f'/api/characters/builder/{session_id}/finalize/', {
            'name': 'Complete Workflow Hero',
            'alignment': 'NG'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['character']['name'], 'Complete Workflow Hero')
        self.assertEqual(response.data['character']['level'], 1)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access builder"""
        client = APIClient()  # No authentication
        
        response = client.post('/api/characters/builder/start/', {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
