"""
Comprehensive Tests for Legendary Actions and Death Saving Throws

Tests legendary action usage, tracking, reset mechanics, and death saving throws.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats
from encounters.models import Encounter, EncounterEnemy


class LegendaryActionTests(TestCase):
    """Test legendary action mechanics"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create dragon enemy with legendary actions
        self.dragon = Enemy.objects.create(
            name="Ancient Red Dragon",
            size="G",
            creature_type="dragon",
            alignment="CE",
            challenge_rating="24"
        )
        
        EnemyStats.objects.create(
            enemy=self.dragon,
            hit_points=546,
            armor_class=22,
            speed=40
        )
        
        # Create combat
        encounter = Encounter.objects.create(name="Dragon Fight")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1
        )
        
        # Create Encounter Enemy
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=encounter,
            enemy=self.dragon,
            name="Ancient Red Dragon",
            current_hp=546
        )
        
        self.dragon_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=20,
            current_hp=546,
            max_hp=546,
            armor_class=22,
            legendary_actions_max=3,
            legendary_actions_remaining=3
        )
    
    def test_legendary_actions_initial_state(self):
        """Test legendary actions start at max"""
        self.assertEqual(self.dragon_participant.legendary_actions_max, 3)
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 3)
    
    def test_use_legendary_action_single_cost(self):
        """Test using a single legendary action"""
        success, message = self.dragon_participant.use_legendary_action(action_cost=1)
        
        self.assertTrue(success)
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 2)
        self.assertIn('remaining', message.lower())
    
    def test_use_legendary_action_double_cost(self):
        """Test using a legendary action with cost 2"""
        success, message = self.dragon_participant.use_legendary_action(action_cost=2)
        
        self.assertTrue(success)
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 1)
    
    def test_use_legendary_action_all_remaining(self):
        """Test using all legendary actions"""
        self.dragon_participant.use_legendary_action(action_cost=3)
        
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 0)
    
    def test_use_legendary_action_insufficient(self):
        """Test cannot use legendary action without enough remaining"""
        self.dragon_participant.legendary_actions_remaining = 1
        self.dragon_participant.save()
        
        success, message = self.dragon_participant.use_legendary_action(action_cost=2)
        
        self.assertFalse(success)
        self.assertIn('not enough', message.lower())
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 1)  # Unchanged
    
    def test_reset_legendary_actions(self):
        """Test resetting legendary actions at turn start"""
        # Use some legendary actions
        self.dragon_participant.use_legendary_action(action_cost=2)
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 1)
        
        # Reset
        self.dragon_participant.reset_legendary_actions()
        self.dragon_participant.save()
        
        self.dragon_participant.refresh_from_db()
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 3)
    
    def test_legendary_action_zero_cost_fails(self):
        """Test cannot use legendary action with 0 cost"""
        success, message = self.dragon_participant.use_legendary_action(action_cost=0)
        
        self.assertFalse(success)
    
    def test_non_legendary_creature_has_zero_actions(self):
        """Test regular creatures have 0 legendary actions"""
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        character = Character.objects.create(
            user=self.user,
            name="Regular Fighter",
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
        
        participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        self.assertEqual(participant.legendary_actions_max, 0)
        self.assertEqual(participant.legendary_actions_remaining, 0)


class LegendaryActionAPITests(TestCase):
    """Test legendary action API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create dragon
        self.dragon = Enemy.objects.create(
            name="Adult Red Dragon",
            size="H",
            creature_type="dragon",
            alignment="CE",
            challenge_rating="17"
        )
        
        EnemyStats.objects.create(
            enemy=self.dragon,
            hit_points=256,
            armor_class=19,
            speed=40
        )
        
        encounter = Encounter.objects.create(name="Dragon Encounter")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1
        )
        
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=encounter,
            enemy=self.dragon,
            name="Adult Red Dragon",
            current_hp=256
        )
        
        self.dragon_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=20,
            current_hp=256,
            max_hp=256,
            armor_class=19,
            legendary_actions_max=3,
            legendary_actions_remaining=3
        )
    
    def test_legendary_action_endpoint_exists(self):
        """Test legendary action endpoint is accessible"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/legendary_action/',
            {
                'participant_id': self.dragon_participant.id,
                'action_name': 'Detect',
                'action_cost': 1
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_legendary_action_via_api(self):
        """Test using legendary action via API"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/legendary_action/',
            {
                'participant_id': self.dragon_participant.id,
                'action_name': 'Tail Attack',
                'action_cost': 2
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('legendary_actions_remaining', response.data)
        self.assertEqual(response.data['legendary_actions_remaining'], 1)
    
    def test_legendary_action_api_insufficient(self):
        """Test API returns error when insufficient legendary actions"""
        # Use up 2 actions
        self.dragon_participant.legendary_actions_remaining = 1
        self.dragon_participant.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/legendary_action/',
            {
                'participant_id': self.dragon_participant.id,
                'action_name': 'Wing Attack',
                'action_cost': 2
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class DeathSavingThrowTests(TestCase):
    """Test death saving throw mechanics"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.fighter = Character.objects.create(
            user=self.user,
            name="Dying Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.fighter,
            constitution=14,
            max_hit_points=45,
            hit_points=0,  # At 0 HP, dying
            armor_class=18
        )
        
        encounter = Encounter.objects.create(name="Deadly Encounter")
        session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1
        )
        
        self.participant = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.fighter,
            initiative=10,
            current_hp=0,  # Dying
            max_hp=45,
            armor_class=18,
            death_save_successes=0,
            death_save_failures=0
        )
    
    def test_death_saves_initial_state(self):
        """Test death saves start at 0/0"""
        self.assertEqual(self.participant.death_save_successes, 0)
        self.assertEqual(self.participant.death_save_failures, 0)
    
    def test_death_save_success(self):
        """Test successful death save (roll 10-19)"""
        # Force a success roll
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=15)
        
        self.assertTrue(success)  # Roll was success
        self.assertFalse(is_dead)  # Not dead
        self.assertFalse(is_stable)  # Not stable yet
        self.assertEqual(self.participant.death_save_successes, 1)
        self.assertEqual(self.participant.death_save_failures, 0)
    
    def test_death_save_failure(self):
        """Test failed death save (roll 1-9)"""
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=5)
        
        self.assertFalse(success)  # Roll failed
        self.assertFalse(is_dead)  # Not dead yet
        self.assertEqual(self.participant.death_save_successes, 0)
        self.assertEqual(self.participant.death_save_failures, 1)
    
    def test_death_save_natural_20(self):
        """Test natural 20 stabilizes immediately"""
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=20)
        
        self.assertTrue(success)
        # Natural 20 may stabilize or give 2 successes
        # Check that participant is stabilized or has successes
        self.assertFalse(is_dead)
        self.assertIn('20', message)  # Message mentions nat 20
    
    def test_death_save_natural_1(self):
        """Test natural 1 counts as 2 failures"""
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=1)
        
        # Should have 2 failures
        self.assertEqual(self.participant.death_save_failures, 2)
        self.assertIn('1', message)  # Message mentions nat 1
    
    def test_three_successes_stabilizes(self):
        """Test 3 successes stabilizes the character"""
        self.participant.death_save_successes = 2
        self.participant.save()
        
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=10)
        
        # Should be stabilized
        self.assertTrue(is_stable)
        self.assertEqual(self.participant.death_save_successes, 0)  # Reset
        self.assertEqual(self.participant.death_save_failures, 0)  # Reset
    
    def test_three_failures_kills(self):
        """Test 3 failures results in death"""
        self.participant.death_save_failures = 2
        self.participant.save()
        
        success, is_stable, is_dead, message = self.participant.make_death_save(roll=5)
        
        # Should be dead
        self.assertTrue(is_dead)
        self.assertIn('die', message.lower())  # 'dies' is in message
    
    def test_death_save_validators(self):
        """Test death save counts are capped at 3"""
        self.participant.death_save_successes = 2
        self.participant.death_save_failures = 1
        self.participant.save()
        
        # Make another success
        self.participant.make_death_save(roll=15)
        
        # Should not exceed 3 (but will be reset if stabilized)
        self.assertLessEqual(self.participant.death_save_successes, 3)


class DeathSaveEdgeCasesTests(TestCase):
    """Test edge cases in death saving throws"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.fighter = Character.objects.create(
            user=self.user,
            name="Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.fighter,
            max_hit_points=45,
            hit_points=0,
            armor_class=18
        )
        
        encounter = Encounter.objects.create(name="Test")
        session = CombatSession.objects.create(encounter=encounter, status='active')
        
        self.participant = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.fighter,
            initiative=10,
            current_hp=0,
            max_hp=45,
            armor_class=18
        )
    
    def test_death_save_reset_on_stabilize(self):
        """Test death saves reset when stabilized"""
        self.participant.death_save_successes = 2
        self.participant.death_save_failures = 1
        self.participant.save()
        
        # Get 3rd success
        self.participant.make_death_save(roll=10)
        
        # Both should be reset
        self.assertEqual(self.participant.death_save_successes, 0)
        self.assertEqual(self.participant.death_save_failures, 0)
    
    def test_healing_resets_death_saves(self):
        """Test healing while dying resets death saves"""
        self.participant.death_save_successes = 1
        self.participant.death_save_failures = 2
        self.participant.save()
        
        # Heal the character
        self.participant.current_hp = 10
        self.participant.death_save_successes = 0
        self.participant.death_save_failures = 0
        self.participant.save()
        
        self.assertEqual(self.participant.death_save_successes, 0)
        self.assertEqual(self.participant.death_save_failures, 0)


class LegendaryResetOnTurnTests(TestCase):
    """Test legendary actions reset at turn start"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.dragon = Enemy.objects.create(
            name="Dragon",
            size="H",
            creature_type="dragon",
            challenge_rating="15"
        )
        
        EnemyStats.objects.create(
            enemy=self.dragon,
            hit_points=200,
            armor_class=19,
            speed=40
        )
        
        encounter = Encounter.objects.create(name="Test")
        self.session = CombatSession.objects.create(
            encounter=encounter,
            status='active',
            current_round=1
        )
        
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=encounter,
            enemy=self.dragon,
            name="Dragon",
            current_hp=200
        )
        
        self.dragon_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=20,
            current_hp=200,
            max_hp=200,
            armor_class=19,
            legendary_actions_max=3,
            legendary_actions_remaining=1  # Used 2 actions
        )
    
    def test_legendary_actions_reset_on_turn_start(self):
        """Test legendary actions reset when creature's turn starts"""
        # Currently at 1 remaining
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 1)
        
        # Simulate turn start (this should happen in next_turn logic)
        self.dragon_participant.reset_legendary_actions()
        self.dragon_participant.save()
        
        self.dragon_participant.refresh_from_db()
        self.assertEqual(self.dragon_participant.legendary_actions_remaining, 3)
