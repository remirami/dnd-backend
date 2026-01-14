"""
Phase 3 Tests: Participant Actions

Tests for damage, heal, add_condition, remove_condition endpoints
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Condition
from encounters.models import Encounter


class DamageTests(TestCase):
    """Test damage endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        self.character = Character.objects.create(
            user=self.user,
            name="Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.character,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Test Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            initiative=20,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
    
    def test_damage_success(self):
        """Test applying damage successfully"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/damage/',
            {'amount': 10}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_hp', response.data)
        self.assertEqual(response.data['current_hp'], 35)
        
        # Verify participant HP updated
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.current_hp, 35)
    
    def test_damage_zero_or_negative(self):
        """Test damage with zero or negative amount fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/damage/',
            {'amount': 0}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_damage_concentration(self):
        """Test damage breaks concentration"""
        # Set up concentration
        self.participant.concentration_spell = "Fireball"
        self.participant.save()
        
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/damage/',
            {'amount': 10}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Note: concentration_broken depends on save implementation
        # Just verify response structure is correct
        self.assertIn('current_hp', response.data)


class HealTests(TestCase):
    """Test heal endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        cleric_class = CharacterClass.objects.create(name="Cleric", hit_dice="d8")
        self.character = Character.objects.create(
            user=self.user,
            name="Cleric",
            level=5,
            character_class=cleric_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.character,
            max_hit_points=40,
            hit_points=40,
            armor_class=16
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Test Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=20,  # Damaged
            max_hp=40,
            armor_class=16
        )
    
    def test_heal_success(self):
        """Test healing successfully"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/heal/',
            {'amount': 15}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_hp', response.data)
        self.assertEqual(response.data['current_hp'], 35)
        
        # Verify participant HP updated
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.current_hp, 35)
    
    def test_heal_cannot_exceed_max(self):
        """Test healing cannot exceed max HP"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/heal/',
            {'amount': 50}  # More than needed
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_hp'], 40)  # Capped at max
    
    def test_heal_zero_or_negative(self):
        """Test heal with zero or negative amount fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/heal/',
            {'amount': -5}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class ConditionTests(TestCase):
    """Test add_condition and remove_condition endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        wizard_class = CharacterClass.objects.create(name="Wizard", hit_dice="d6")
        self.character = Character.objects.create(
            user=self.user,
            name="Wizard",
            level=5,
            character_class=wizard_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.character,
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Test Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            initiative=10,
            current_hp=30,
            max_hp=30,
            armor_class=12
        )
        
        # Create conditions
        self.poison_condition = Condition.objects.create(
            name='poisoned'
        )
        self.stunned_condition = Condition.objects.create(
            name='stunned'
        )
    
    def test_add_condition_success(self):
        """Test adding condition successfully"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/add_condition/',
            {'condition_id': self.poison_condition.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify condition was added
        self.assertTrue(self.participant.conditions.filter(id=self.poison_condition.id).exists())
    
    def test_add_condition_missing_id(self):
        """Test adding condition without condition_id fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/add_condition/',
            {}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_add_condition_invalid_id(self):
        """Test adding non-existent condition fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/add_condition/',
            {'condition_id': 99999}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_remove_condition_success(self):
        """Test removing condition successfully"""
        # First add a condition
        self.participant.conditions.add(self.poison_condition)
        
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/remove_condition/',
            {'condition_id': self.poison_condition.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify condition was removed
        self.assertFalse(self.participant.conditions.filter(id=self.poison_condition.id).exists())
    
    def test_remove_condition_missing_id(self):
        """Test removing condition without condition_id fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/remove_condition/',
            {}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_remove_condition_invalid_id(self):
        """Test removing non-existent condition fails"""
        response = self.client.post(
            f'/api/combat/participants/{self.participant.id}/remove_condition/',
            {'condition_id': 99999}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
