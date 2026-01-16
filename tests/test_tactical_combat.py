"""
Tests for Tactical Combat Features

Tests for AOE targeting, grappling, and cover systems.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant
from characters.models import Character, CharacterClass, CharacterRace, CharacterBackground, CharacterStats
from encounters.models import Encounter, EncounterEnemy
from bestiary.models import Enemy


class AOETargetingTests(TestCase):
    """Test AOE spell targeting"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create encounter
        self.encounter = Encounter.objects.create()
        
        # Create combat session
        self.session = CombatSession.objects.create(
            encounter=self.encounter,
            status='active'
        )
        
        # Create participants
        self.caster = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            initiative=15,
            current_hp=50,
            max_hp=50,
            armor_class=15,
            position_x=0,
            position_y=0
        )
        
        self.target1 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            initiative=10,
            current_hp=30,
            max_hp=30,
            armor_class=13,
            position_x=15,
            position_y=15
        )
        
        self.target2 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            initiative=8,
            current_hp=25,
            max_hp=25,
            armor_class=12,
            position_x=18,
            position_y=18
        )
        
        self.distant_target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            initiative=5,
            current_hp=20,
            max_hp=20,
            armor_class=10,
            position_x=100,
            position_y=100
        )
    
    def test_fireball_hits_multiple_targets(self):
        """Test Fire ball hits all targets in 20ft radius"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_aoe_spell/',
            {
                'caster_id': self.caster.id,
                'spell_name': 'fireball',
                'origin_x': 15,
                'origin_y': 15,
                'radius': 20,
                'save_dc': 15
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['spell_name'], 'fireball')
        self.assertGreater(response.data['total_targets'], 0)
        
        # Should hit target1 and target2 (within 20ft of origin)
        # Should NOT hit distant_target (100ft away)
        targets_hit = [t['participant_id'] for t in response.data['targets_affected']]
        self.assertIn(self.target1.id, targets_hit)
        self.assertIn(self.target2.id, targets_hit)
        self.assertNotIn(self.distant_target.id, targets_hit)
    
    def test_aoe_successful_save_half_damage(self):
        """Test successful save results in half damage"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_aoe_spell/',
            {
                'caster_id': self.caster.id,
                'spell_name': 'fireball',
                'origin_x': 15,
                'origin_y': 15,
                'save_dc': 1  # Very low DC to ensure success
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # All targets should succeed save with DC 1
        for target_data in response.data['targets_affected']:
            if target_data['save_result'] == 'success':
                # Damage taken should be less than damage rolled
                self.assertLess(target_data['damage_taken'], target_data['damage_rolled'])


class GrapplingTests(TestCase):
    """Test grappling mechanics"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        self.encounter = Encounter.objects.create()
        self.session = CombatSession.objects.create(encounter=self.encounter, status='active')
        
        self.grappler = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            initiative=15,
            current_hp=50,
            max_hp=50,
            armor_class=15
        )
        
        self.target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            initiative=10,
            current_hp=30,
            max_hp=30,
            armor_class=13
        )
    
    def test_grapple_initiates_successfully(self):
        """Test grapple can be initiated"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/grapple/',
            {
                'grappler_id': self.grappler.id,
                'target_id': self.target.id
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success', response.data)
        self.assertIn('grappler_total', response.data)
        self.assertIn('target_total', response.data)
    
    def test_cannot_grapple_when_action_used(self):
        """Test cannot grapple after using action"""
        self.grappler.action_used = True
        self.grappler.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/grapple/',
            {
                'grappler_id': self.grappler.id,
                'target_id': self.target.id
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_escape_grapple(self):
        """Test escaping a grapple"""
        # First grapple
        self.grappler.is_grappling = True
        self.grappler.save()
        
        self.target.grappled_by = self.grappler
        self.target.save()
        
        # Then escape
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/escape_grapple/',
            {'participant_id': self.target.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success', response.data)


class CoverSystemTests(TestCase):
    """Test cover system"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Fix: Ensure encounter and session are created before participant
        self.encounter = Encounter.objects.create() # Removed name, difficulty, total_xp as they are not strictly needed for basic functionality tests
        self.session = CombatSession.objects.create(encounter=self.encounter, status='active')
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            initiative=15,
            current_hp=50,
            max_hp=50,
            armor_class=15,
            cover_type='none'
        )
    
    def test_set_half_cover(self):
        """Test setting half cover"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_cover/',
            {
                'participant_id': self.participant.id,
                'cover_type': 'half'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['new_cover'], 'half')
        self.assertEqual(response.data['ac_bonus'], 2)
        self.assertEqual(response.data['dex_save_bonus'], 2)
        
        # Verify database updated
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.cover_type, 'half')
    
    def test_set_three_quarters_cover(self):
        """Test setting three-quarters cover"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_cover/',
            {
                'participant_id': self.participant.id,
                'cover_type': 'three_quarters'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ac_bonus'], 5)
    
    def test_invalid_cover_type(self):
        """Test invalid cover type rejected"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/set_cover/',
            {
                'participant_id': self.participant.id,
                'cover_type': 'super'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
