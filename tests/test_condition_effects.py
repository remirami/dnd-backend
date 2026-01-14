"""
Comprehensive Tests for Condition Effects System

Tests condition application, duration tracking, effects, and removal.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant, ConditionApplication
from combat.condition_effects import (
    get_condition_for_spell,
    get_condition_effects,
    apply_condition_effects,
    auto_apply_condition_from_spell,
    calculate_effective_speed,
    has_attack_disadvantage,
    has_attack_advantage_against
)
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Condition
from encounters.models import Encounter


class ConditionEffectsUtilityTests(TestCase):
    """Test condition effects utility functions"""
    
    def test_get_condition_for_spell(self):
        """Test getting condition from spell name"""
        self.assertEqual(get_condition_for_spell('Hold Person'), 'paralyzed')
        self.assertEqual(get_condition_for_spell('Blindness/Deafness'), 'blinded')
        self.assertIsNone(get_condition_for_spell('Fireball'))  # No condition
    
    def test_get_condition_effects(self):
        """Test getting effects for a condition"""
        effects = get_condition_effects('blinded')
        
        self.assertIsNotNone(effects)
        self.assertTrue(effects.get('attack_disadvantage'))
        self.assertTrue(effects.get('attack_advantage_against'))
    
    def test_paralyzed_condition_effects(self):
        """Test paralyzed condition effects"""
        effects = get_condition_effects('paralyzed')
        
        self.assertEqual(effects.get('speed'), 0)
        self.assertTrue(effects.get('cannot_take_actions'))
        self.assertTrue(effects.get('str_dex_saves_fail'))
    
    def test_invalid_condition_returns_none(self):
        """Test invalid condition name returns empty dict"""
        effects = get_condition_effects('invalid_condition')
        self.assertEqual(effects, {})  # Returns empty dict, not None


class ConditionApplicationTests(TestCase):
    """Test condition application to combat participants"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.character = Character.objects.create(
            user=self.user,
            name="Test Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.character,
            max_hit_points=45,
            hit_points=45,
            armor_class=18,
            speed=30
        )
        
        # Create combat session
        encounter = Encounter.objects.create(name="Test Encounter")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        # Create condition
        self.blinded_condition = Condition.objects.create(
            name="Blinded",
            description="Cannot see"
        )
    
    def test_create_condition_application(self):
        """Test creating a condition application"""
        app = ConditionApplication.objects.create(
            participant=self.participant,
            condition=self.blinded_condition,
            applied_round=1,
            applied_turn=0,
            duration_type='round',
            duration_rounds=3
        )
        
        self.assertEqual(app.participant, self.participant)
        self.assertEqual(app.condition, self.blinded_condition)
        self.assertFalse(app.is_expired(self.session.current_round))  # Method, not property
    
    def test_condition_expiry_by_round(self):
        """Test condition expires after N rounds"""
        app = ConditionApplication.objects.create(
            participant=self.participant,
            condition=self.blinded_condition,
            applied_round=1,
            applied_turn=0,
            duration_type='round',
            duration_rounds=2,
            expires_at_round=3  # Expires at round 3
        )
        
        # Should not be expired at round 2
        self.assertFalse(app.is_expired(2))
        
        # Should be expired after round 3 (expires_at_round means expires AFTER that round)
        self.assertTrue(app.is_expired(4))
    
    def test_concentration_based_condition(self):
        """Test condition tied to concentration"""
        app = ConditionApplication.objects.create(
            participant=self.participant,
            condition=self.blinded_condition,
            applied_round=1,
            duration_type='concentration',
            source_type='spell',
            source_name='Blindness/Deafness'
        )
        
        self.assertEqual(app.duration_type, 'concentration')
        self.assertEqual(app.source_name, 'Blindness/Deafness')
    
    def test_multiple_conditions_on_participant(self):
        """Test applying multiple conditions to one participant"""
        blinded = ConditionApplication.objects.create(
            participant=self.participant,
            condition=self.blinded_condition,
            applied_round=1,
            duration_type='round',
            duration_rounds=3
        )
        
        prone_condition = Condition.objects.create(name="Prone", description="Lying down")
        prone = ConditionApplication.objects.create(
            participant=self.participant,
            condition=prone_condition,
            applied_round=1,
            duration_type='round',
            duration_rounds=1
        )
        
        conditions = ConditionApplication.objects.filter(participant=self.participant)
        self.assertEqual(conditions.count(), 2)


class ConditionEffectsOnStatsTests(TestCase):
    """Test how conditions affect participant stats"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        character = Character.objects.create(
            user=self.user,
            name="Test Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=character,
            max_hit_points=45,
            hit_points=45,
            armor_class=18,
            speed=30
        )
        
        encounter = Encounter.objects.create(name="Test Encounter")
        session = CombatSession.objects.create(encounter=encounter, status='active')
        
        self.participant = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
    
    def test_blinded_condition_data(self):
        """Test blinded condition has correct data"""
        # Just verify the condition_effects module has the blinded data
        effects = get_condition_effects('blinded')
        self.assertIsNotNone(effects)
        self.assertIn('attack_disadvantage', effects)
    
    def test_prone_condition_data(self):
        """Test prone condition has correct data"""
        effects = get_condition_effects('prone')
        self.assertIsNotNone(effects)
        self.assertIn('melee_attack_advantage_against', effects)
    
    def test_paralyzed_condition_data(self):
        """Test paralyzed condition has speed 0"""
        effects = get_condition_effects('paralyzed')
        self.assertIsNotNone(effects)
        self.assertEqual(effects.get('speed'), 0)


class AutoConditionApplicationTests(TestCase):
    """Test automatic condition application from spells"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        character = Character.objects.create(
            user=self.user,
            name="Test Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=character,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        encounter = Encounter.objects.create(name="Test Encounter")
        session = CombatSession.objects.create(encounter=encounter, status='active')
        
        self.participant = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
    
    def test_hold_person_maps_to_paralyzed(self):
        """Test Hold Person spell maps to paralyzed condition"""
        condition_name = get_condition_for_spell('Hold Person')
        self.assertEqual(condition_name, 'paralyzed')
    
    def test_auto_apply_from_non_condition_spell(self):
        """Test spells without conditions return None"""
        result = auto_apply_condition_from_spell(self.participant, 'Fireball')
        self.assertIsNone(result)
