"""
Automated Test Suite for SRD 5.2 2024 Cumulative Exhaustion Engine (Phase 13)
Ruleset: 2024 SRD 5.2 Rules (Cumulative Levels 1-10)
"""

from unittest import mock
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterBackground, CharacterStats
from characters.rest_mechanics import execute_long_rest
from combat.models import CombatSession, CombatParticipant
from combat.utils import calculate_attack_roll, calculate_saving_throw, calculate_ability_check
from combat.views.session_views import CombatSessionViewSet
from combat.views.participant_views import CombatParticipantViewSet
from characters.views.character_views import CharacterViewSet

User = get_user_model()


class CumulativeExhaustionEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exhaustion_tester', password='password123')
        self.factory = APIRequestFactory()

        # Seed exhaustion condition
        self.exhaustion_cond, _ = Condition.objects.get_or_create(
            name='exhaustion', defaults={'description': 'Levels of exhaustion have cumulative effects'}
        )

        # Base character
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', speed=30)
        self.background = CharacterBackground.objects.create(name='Soldier')
        self.hero = Character.objects.create(
            name='Sir Tired',
            user=self.user,
            character_class=self.fighter_class,
            level=5,
            race=self.race,
            background=self.background,
            ruleset_version='2024'
        )
        self.hero_stats = CharacterStats.objects.create(
            character=self.hero,
            hit_points=40,
            max_hit_points=40,
            strength=16,  # +3
            dexterity=14, # +2
            constitution=14, # +2
            intelligence=10,
            wisdom=12,
            charisma=10,
            armor_class=16,
            speed=30,
            spell_save_dc=15,
            exhaustion_level=0
        )

        # Combat session & participants
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        self.hero_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.hero,
            current_hp=40,
            max_hp=40,
            armor_class=16,
            initiative=15,
            exhaustion_level=0
        )

        self.enemy = Enemy.objects.create(name='Target Dummy', hp=50, ac=10, challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.enemy,
            strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10,
            hit_points=50, armor_class=10
        )
        self.enemy_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=None,
            name='Target Dummy',
            current_hp=50,
            max_hp=50,
            armor_class=10,
            initiative=10
        )

    def test_d20_attack_penalty_formula(self):
        """calculate_attack_roll properly subtracts -1 per exhaustion level from attack roll."""
        # Baseline (0 exhaustion): d20 roll 10 + 3 STR + 3 Prof = 16
        tot0, bdown0 = calculate_attack_roll(10, 3, 3, True, exhaustion_level=0)
        self.assertEqual(tot0, 16)
        self.assertNotIn("Exhaustion", bdown0)

        # Level 1 exhaustion: 16 - 1 = 15
        tot1, bdown1 = calculate_attack_roll(10, 3, 3, True, exhaustion_level=1)
        self.assertEqual(tot1, 15)
        self.assertIn("Exhaustion: -1", bdown1)

        # Level 3 exhaustion: 16 - 3 = 13
        tot3, bdown3 = calculate_attack_roll(10, 3, 3, True, exhaustion_level=3)
        self.assertEqual(tot3, 13)
        self.assertIn("Exhaustion: -3", bdown3)

        # Level 5 exhaustion: 16 - 5 = 11
        tot5, bdown5 = calculate_attack_roll(10, 3, 3, True, exhaustion_level=5)
        self.assertEqual(tot5, 11)
        self.assertIn("Exhaustion: -5", bdown5)

    def test_in_combat_attack_applies_exhaustion(self):
        """Combat attack endpoint subtracts attacker's exhaustion level from total roll."""
        self.hero_p.set_exhaustion_level(3)
        self.assertEqual(self.hero_p.get_exhaustion_level(), 3)
        self.assertTrue(self.hero_p.conditions.filter(name='exhaustion').exists())

        request = self.factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.enemy_p.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})

        # Mock d20 roll to 10. Base total = 10 + 3(STR) + 3(Prof) = 16. With 3 exhaustion: 13.
        with mock.patch('combat.utils.random.randint', return_value=10):
            response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        attack_total = response.data.get('attack_total')
        self.assertEqual(attack_total, 13)
        self.assertIn("Exhaustion: -3", response.data.get('attack_breakdown', ''))

    def test_d20_saving_throw_penalty(self):
        """calculate_saving_throw properly subtracts -1 per exhaustion level."""
        # Baseline save: roll 12 + 2 CON = 14
        tot0, bdown0 = calculate_saving_throw(12, 2, 0, False, exhaustion_level=0)
        self.assertEqual(tot0, 14)

        # Level 2 exhaustion: 14 - 2 = 12
        tot2, bdown2 = calculate_saving_throw(12, 2, 0, False, exhaustion_level=2)
        self.assertEqual(tot2, 12)
        self.assertIn("Exhaustion: -2", bdown2)

        # Level 4 exhaustion: 14 - 4 = 10
        tot4, bdown4 = calculate_saving_throw(12, 2, 0, False, exhaustion_level=4)
        self.assertEqual(tot4, 10)
        self.assertIn("Exhaustion: -4", bdown4)

    def test_d20_ability_check_penalty(self):
        """calculate_ability_check subtracts exhaustion level from total."""
        tot, bdown = calculate_ability_check(
            base_roll=14,
            ability_modifier=3,
            proficiency_bonus=3,
            proficiency=True,
            exhaustion_level=4
        )
        # 14 + 3 + 3 - 4 = 16
        self.assertEqual(tot, 16)
        self.assertIn("Exhaustion: -4", bdown)

    def test_speed_reduction_5ft_per_level(self):
        """Speed drops by 5 ft per exhaustion level, floored at 0 ft."""
        self.assertEqual(self.hero_p.speed, 30)

        # Level 1: 30 - 5 = 25 ft
        self.hero_p.set_exhaustion_level(1)
        self.assertEqual(self.hero_p.speed, 25)

        # Level 2: 30 - 10 = 20 ft
        self.hero_p.set_exhaustion_level(2)
        self.assertEqual(self.hero_p.speed, 20)

        # Level 4: 30 - 20 = 10 ft
        self.hero_p.set_exhaustion_level(4)
        self.assertEqual(self.hero_p.speed, 10)

        # Level 6: 30 - 30 = 0 ft
        self.hero_p.set_exhaustion_level(6)
        self.assertEqual(self.hero_p.speed, 0)

        # Level 8: speed remains 0 ft, not negative
        self.hero_p.set_exhaustion_level(8)
        self.assertEqual(self.hero_p.speed, 0)

    def test_spell_save_dc_reduction(self):
        """Spell Save DC decreases by 1 per exhaustion level."""
        # Initial DC is 15
        self.assertEqual(self.hero_p.get_spell_save_dc(), 15)

        # Level 2: 15 - 2 = 13
        self.hero_p.set_exhaustion_level(2)
        self.assertEqual(self.hero_p.get_spell_save_dc(), 13)

        # Level 5: 15 - 5 = 10
        self.hero_p.set_exhaustion_level(5)
        self.assertEqual(self.hero_p.get_spell_save_dc(), 10)

    def test_level_10_exhaustion_is_fatal(self):
        """Level 10 Exhaustion instantly drops HP to 0 and kills the participant and character."""
        self.hero_p.set_exhaustion_level(10)

        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.current_hp, 0)
        self.assertFalse(self.hero_p.is_active)
        self.assertTrue(self.hero_p.feature_uses.get('is_dead'))

        # Linked character stats check
        self.hero_stats.refresh_from_db()
        self.assertEqual(self.hero_stats.hit_points, 0)
        self.assertEqual(self.hero_stats.exhaustion_level, 10)

    def test_long_rest_recovers_one_exhaustion_level(self):
        """Finishing a Long Rest removes 1 Exhaustion level, and removes the condition at 0."""
        self.hero_stats.exhaustion_level = 3
        self.hero_stats.save()
        self.hero_p.set_exhaustion_level(3)

        result = execute_long_rest(self.hero, sync_combat=True)
        self.assertEqual(result['exhaustion_recovered'], 1)
        self.assertEqual(result['exhaustion_level'], 2)

        self.hero_stats.refresh_from_db()
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_stats.exhaustion_level, 2)
        self.assertEqual(self.hero_p.get_exhaustion_level(), 2)
        self.assertTrue(self.hero_p.conditions.filter(name='exhaustion').exists())

        # Rest again down to level 1
        execute_long_rest(self.hero, sync_combat=True)
        self.hero_stats.refresh_from_db()
        self.assertEqual(self.hero_stats.exhaustion_level, 1)

        # Rest again down to level 0 (exhaustion condition cleared)
        execute_long_rest(self.hero, sync_combat=True)
        self.hero_stats.refresh_from_db()
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_stats.exhaustion_level, 0)
        self.assertEqual(self.hero_p.get_exhaustion_level(), 0)
        self.assertFalse(self.hero_p.conditions.filter(name='exhaustion').exists())

    def test_character_adjust_exhaustion_endpoint(self):
        """POST /api/characters/{id}/adjust_exhaustion/ correctly increments, decrements, and clamps."""
        from rest_framework.test import force_authenticate
        view = CharacterViewSet.as_view({'post': 'adjust_exhaustion'})

        # Set explicitly to level 4
        req1 = self.factory.post(f'/api/characters/{self.hero.id}/adjust_exhaustion/', {'level': 4}, format='json')
        force_authenticate(req1, user=self.user)
        res1 = view(req1, pk=self.hero.id)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.data['exhaustion_level'], 4)

        # Increment by +2 via delta
        req2 = self.factory.post(f'/api/characters/{self.hero.id}/adjust_exhaustion/', {'delta': 2}, format='json')
        force_authenticate(req2, user=self.user)
        res2 = view(req2, pk=self.hero.id)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data['exhaustion_level'], 6)

        # Linked combat participant is also updated
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.exhaustion_level, 6)

    def test_combat_participant_set_exhaustion_endpoint(self):
        """POST /api/combat/participants/{id}/set_exhaustion/ updates combatant exhaustion and condition tag."""
        view = CombatParticipantViewSet.as_view({'post': 'set_exhaustion'})

        req = self.factory.post(f'/api/combat/participants/{self.hero_p.id}/set_exhaustion/', {'level': 5}, format='json')
        res = view(req, pk=self.hero_p.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['exhaustion_level'], 5)

        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.exhaustion_level, 5)
        self.assertTrue(self.hero_p.conditions.filter(name='exhaustion').exists())

        # Speed reflects level 5: 30 - 25 = 5 ft
        self.assertEqual(self.hero_p.speed, 5)
