"""
Phase 2 Tests: Advanced Combat Mechanics

Tests for opportunity_attack, use_reaction, environmental_effects, set_participant_position
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant, EnvironmentalEffect, ParticipantPosition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats
from encounters.models import Encounter, EncounterEnemy


class OpportunityAttackTests(TestCase):
    """Test opportunity_attack endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create attacker
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        self.attacker_char = Character.objects.create(
            user=self.user,
            name="Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.attacker_char,
            strength=16,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        # Create target
        self.enemy = Enemy.objects.create(
            name="Goblin",
            creature_type="humanoid",
            size="S",
            challenge_rating="1/4"
        )
        EnemyStats.objects.create(
            enemy=self.enemy,
            hit_points=7,
            armor_class=13,
            speed=30
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
        
        self.attacker = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.attacker_char,
            initiative=20,
            current_hp=45,
            max_hp=45,
            armor_class=18,
            reaction_used=False
        )
        
        encounter_enemy = EncounterEnemy.objects.create(
            encounter=encounter,
            enemy=self.enemy,
            name="Goblin",
            current_hp=7
        )
        
        self.target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=encounter_enemy,
            initiative=15,
            current_hp=7,
            max_hp=7,
            armor_class=13
        )
    
    def test_opportunity_attack_success(self):
        """Test successful opportunity attack"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/opportunity_attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attack_total', response.data)
        self.assertIn('message', response.data)
        
        # Verify reaction was used
        self.attacker.refresh_from_db()
        self.assertTrue(self.attacker.reaction_used)
    
    def test_opportunity_attack_reaction_used(self):
        """Test opportunity attack fails when reaction already used"""
        self.attacker.reaction_used = True
        self.attacker.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/opportunity_attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_opportunity_attack_missing_fields(self):
        """Test opportunity attack with missing fields"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/opportunity_attack/',
            {
                'attacker_id': self.attacker.id
                # Missing target_id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_opportunity_attack_invalid_participant(self):
        """Test opportunity attack with invalid participant"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/opportunity_attack/',
            {
                'attacker_id': 99999,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReactionTests(TestCase):
    """Test use_reaction endpoint"""
    
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
        encounter = Encounter.objects.create(name="Test")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=30,
            max_hp=30,
            armor_class=12,
            reaction_used=False
        )
    
    def test_use_reaction_spell_success(self):
        """Test using spell reaction successfully"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_reaction/',
            {
                'participant_id': self.participant.id,
                'reaction_type': 'spell',
                'spell_name': 'Shield'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reaction_type', response.data)
        self.assertEqual(response.data['reaction_type'], 'spell')
    
    def test_use_reaction_ability_success(self):
        """Test using ability reaction successfully"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_reaction/',
            {
                'participant_id': self.participant.id,
                'reaction_type': 'ability',
                'ability_name': 'Uncanny Dodge'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reaction_type'], 'ability')
    
    def test_use_reaction_already_used(self):
        """Test reaction fails when already used"""
        # Use reaction first time
        self.participant.use_reaction()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_reaction/',
            {
                'participant_id': self.participant.id,
                'reaction_type': 'spell',
                'spell_name': 'Shield'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_use_reaction_invalid_type(self):
        """Test reaction with invalid type"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_reaction/',
            {
                'participant_id': self.participant.id,
                'reaction_type': 'invalid_type'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EnvironmentalEffectsTests(TestCase):
    """Test environmental_effects endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create combat
        encounter = Encounter.objects.create(name="Test Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active'
        )
    
    def test_get_environmental_effects(self):
        """Test getting list of environmental effects"""
        # Create an effect
        EnvironmentalEffect.objects.create(
            combat_session=self.session,
            effect_type='terrain',
            terrain_type='difficult',
            description='Muddy ground'
        )
        
        response = self.client.get(f'/api/combat/sessions/{self.session.id}/environmental_effects/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('environmental_effects', response.data)
        self.assertGreater(len(response.data['environmental_effects']), 0)
    
    def test_add_environmental_effect_weather(self):
        """Test adding weather environmental effect"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/environmental_effects/',
            {
                'effect_type': 'weather',
                'weather_type': 'heavy_rain',  # Valid choice from model
                'description': 'Heavy rain'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('effect', response.data)
        self.assertEqual(response.data['effect']['effect_type'], 'weather')
    
    def test_add_environmental_effect_cover(self):
        """Test adding cover environmental effect"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/environmental_effects/',
            {
                'effect_type': 'cover',
                'cover_type': 'half',
                'cover_area_x': 10,
                'cover_area_y': 10,
                'cover_area_radius': 5,
                'description': 'Stone wall'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['effect']['effect_type'], 'cover')
    
    def test_add_environmental_effect_missing_type(self):
        """Test adding effect without effect_type"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/environmental_effects/',
            {
                'description': 'Some effect'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ParticipantPositionTests(TestCase):
    """Test set_participant_position endpoint"""
    
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
    
    def test_set_position_success(self):
        """Test setting participant position"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_participant_position/',
            {
                'participant_id': self.participant.id,
                'x': 10,
                'y': 15,
                'z': 0
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('position', response.data)
        self.assertEqual(response.data['position']['x'], 10)
        self.assertEqual(response.data['position']['y'], 15)
    
    def test_update_position(self):
        """Test updating existing position"""
        # Create initial position
        ParticipantPosition.objects.create(
            participant=self.participant,
            x=5,
            y=5,
            z=0
        )
        
        # Update position
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_participant_position/',
            {
                'participant_id': self.participant.id,
                'x': 20,
                'y': 25,
                'z': 0
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['position']['x'], 20)
        self.assertEqual(response.data['position']['y'], 25)
    
    def test_set_position_missing_participant(self):
        """Test setting position without participant_id"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_participant_position/',
            {
                'x': 10,
                'y': 15
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
