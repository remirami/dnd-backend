"""
Comprehensive tests for Combat Views API endpoints.

Tests combat session management matching actual API implementation.
"""
from django.test import TestCase  
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats


class CombatSessionAPITests(TestCase):
    """Test combat session CRUD operations"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        char_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.character = Character.objects.create(
            user=self.user,
            name="Test Fighter",
            level=5,
            character_class=char_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=15,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
    
    def test_create_combat_session(self):
        """Test creating a new combat session"""
        response = self.client.post('/api/combat/sessions/', {
            'status': 'preparing'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'preparing')
    
    def test_list_combat_sessions(self):
        """Test listing combat sessions"""
        CombatSession.objects.create(status='preparing')
        CombatSession.objects.create(status='active')
        
        response = self.client.get('/api/combat/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_get_combat_session_detail(self):
        """Test retrieving a specific combat session"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.get(f'/api/combat/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], session.id)
    
    def test_add_participant_to_session(self):
        """Test adding a participant to combat"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {
                'participant_type': 'character',
                'character_id': self.character.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('participant', response.data)
    
    def test_start_combat_with_participants(self):
        """Test starting combat with participants"""
        session = CombatSession.objects.create(status='preparing')
        
        # Add participant
        CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        response = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session']['status'], 'active')
    
    def test_start_combat_no_participants_fails(self):
        """Test starting combat without participants fails"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
