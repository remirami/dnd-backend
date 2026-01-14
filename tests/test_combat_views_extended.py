"""
Comprehensive Tests for Combat Views - Core Combat Flow

Tests for untested endpoints in combat/views.py to improve coverage from 36% to 50%+.
Covers: roll_initiative, next_turn, attack, saving_throw, end, stats, report
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant, CombatAction
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats
from encounters.models import Encounter, EncounterEnemy


class InitiativeTests(TestCase):
    """Test roll_initiative endpoint"""
    
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
            dexterity=14,  # +2 modifier
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
            initiative=0,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
    
    def test_roll_initiative_success(self):
        """Test rolling initiative for all participants"""
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/roll_initiative/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('initiative', response.data['results'][0])
        self.assertGreater(response.data['results'][0]['initiative'], 0)
    
    def test_roll_initiative_no_participants(self):
        """Test rolling initiative with no participants"""
        empty_session = CombatSession.objects.create(
            encounter=self.session.encounter,
            status='active'
        )
        
        response = self.client.post(f'/api/combat/sessions/{empty_session.id}/roll_initiative/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_roll_initiative_updates_participants(self):
        """Test initiative is saved to participants"""
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/roll_initiative/')
        
        self.participant.refresh_from_db()
        self.assertGreater(self.participant.initiative, 0)


class TurnManagementTests(TestCase):
    """Test next_turn and end endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create two characters
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.char1 = Character.objects.create(
            user=self.user,
            name="Fighter 1",
            level=5,
            character_class=fighter_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.char1,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        self.char2 = Character.objects.create(
            user=self.user,
            name="Fighter 2",
            level=5,
            character_class=fighter_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.char2,
            max_hit_points=40,
            hit_points=40,
            armor_class=16
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Test Combat")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1,
            current_turn_index=0
        )
        
        self.participant1 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.char1,
            initiative=20,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        self.participant2 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.char2,
            initiative=15,
            current_hp=40,
            max_hp=40,
            armor_class=16
        )
    
    def test_next_turn_success(self):
        """Test advancing to next turn"""
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/next_turn/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        self.session.refresh_from_db()
        self.assertGreater(self.session.current_turn_index, 0)
    
    def test_next_turn_inactive_combat(self):
        """Test next_turn fails on inactive combat"""
        self.session.status = 'pending'
        self.session.save()
        
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/next_turn/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_next_turn_no_participants(self):
        """Test next_turn with no active participants"""
        self.participant1.is_active = False
        self.participant1.save()
        self.participant2.is_active = False
        self.participant2.save()
        
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/next_turn/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_end_combat_success(self):
        """Test ending combat session"""
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/end/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('log_id', response.data)
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'ended')
        self.assertIsNotNone(self.session.ended_at)
    
    def test_end_combat_twice(self):
        """Test ending already ended combat"""
        self.session.status = 'ended'
        self.session.save()
        
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/end/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_end_combat_creates_log(self):
        """Test ending combat creates combat log"""
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/end/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('log_id', response.data)
        self.assertIsNotNone(response.data['log_id'])


class AttackTests(TestCase):
    """Test attack endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create attacker
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        self.attacker_char = Character.objects.create(
            user=self.user,
            name="Attacker",
            level=5,
            character_class=fighter_class,
            race=race
        )
        CharacterStats.objects.create(
            character=self.attacker_char,
            strength=16,  # +3 modifier
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        # Create target enemy
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
            status='active',
            current_round=1,
            current_turn_index=0
        )
        
        self.attacker = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.attacker_char,
            initiative=20,
            current_hp=45,
            max_hp=45,
            armor_class=18
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
    
    def test_attack_success(self):
        """Test successful attack"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id,
                'attack_name': 'Longsword'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('attack_total', response.data)
    
    def test_attack_not_your_turn(self):
        """Test attack fails when not attacker's turn"""
        self.session.current_turn_index = 1  # Target's turn
        self.session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_attack_inactive_combat(self):
        """Test attack fails on inactive combat"""
        self.session.status = 'pending'
        self.session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_attack_invalid_participant(self):
        """Test attack with non-existent participant"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': 99999,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_attack_inactive_attacker(self):
        """Test attack with inactive attacker"""
        self.attacker.is_active = False
        self.attacker.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.attacker.id,
                'target_id': self.target.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_attack_missing_fields(self):
        """Test attack with missing required fields"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.attacker.id
                # Missing target_id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SavingThrowTests(TestCase):
    """Test saving_throw endpoint"""
    
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
            dexterity=14,  # +2 DEX save
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
            armor_class=12
        )
    
    def test_saving_throw_success(self):
        """Test successful saving throw"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/saving_throw/',
            {
                'participant_id': self.participant.id,
                'save_type': 'DEX',
                'save_dc': 15
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('save_total', response.data)
        self.assertIn('save_success', response.data)
        self.assertIn('roll', response.data)
    
    def test_saving_throw_inactive_combat(self):
        """Test saving throw on inactive combat"""
        self.session.status = 'ended'
        self.session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/saving_throw/',
            {
                'participant_id': self.participant.id,
                'save_type': 'DEX',
                'save_dc': 15
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_saving_throw_missing_fields(self):
        """Test saving throw with missing fields"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/saving_throw/',
            {
                'participant_id': self.participant.id
                # Missing save_type and save_dc
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_saving_throw_invalid_participant(self):
        """Test saving throw with invalid participant"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/saving_throw/',
            {
                'participant_id': 99999,
                'save_type': 'DEX',
                'save_dc': 15
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CombatStatsTests(TestCase):
    """Test stats and report endpoints"""
    
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
            status='active',
            current_round=3
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
        
        # Create some combat actions for stats
        CombatAction.objects.create(
            combat_session=self.session,
            actor=self.participant,
            action_type='attack',
            round_number=1,
            turn_number=0,
            description="Attack"
        )
    
    def test_stats_success(self):
        """Test getting combat stats"""
        response = self.client.get(f'/api/combat/sessions/{self.session.id}/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
    
    def test_report_success(self):
        """Test getting combat report"""
        response = self.client.get(f'/api/combat/sessions/{self.session.id}/report/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_stats_creates_log_if_needed(self):
        """Test stats endpoint creates log if it doesn't exist"""
        # Ensure no log exists
        self.session.logs.all().delete()
        
        response = self.client.get(f'/api/combat/sessions/{self.session.id}/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.session.logs.exists())
