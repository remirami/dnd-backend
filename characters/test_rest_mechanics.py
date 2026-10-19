"""
Automated Test Suite for D&D 5e Rest Mechanics & Hit Dice Recovery (Phase 10)
Rulesets Evaluated: SRD 5.1 & 2024 SRD 5.2
"""

from unittest import mock
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from characters.models import Character, CharacterClass, CharacterRace, CharacterBackground, CharacterStats
from characters.views import CharacterViewSet
from characters.rest_mechanics import (
    execute_short_rest,
    execute_long_rest,
    get_available_hit_dice,
    get_character_hit_dice_pool,
    calculate_pact_magic_slots,
    calculate_channel_divinity_max,
)
from combat.models import CombatSession, CombatParticipant

User = get_user_model()


class RestMechanicsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rest_tester', password='password123')
        self.race = CharacterRace.objects.create(name='Human', speed=30)
        self.background = CharacterBackground.objects.create(name='Soldier')
        self.factory = APIRequestFactory()

        # Class definitions
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10')
        self.warlock_class = CharacterClass.objects.create(name='warlock', hit_dice='d8')
        self.wizard_class = CharacterClass.objects.create(name='wizard', hit_dice='d6')
        self.monk_class = CharacterClass.objects.create(name='monk', hit_dice='d8')
        self.cleric_class = CharacterClass.objects.create(name='cleric', hit_dice='d8')

    def _create_character(self, name, c_class, level=5, hp=20, max_hp=40, con=14, **stats_kwargs):
        char = Character.objects.create(
            name=name,
            user=self.user,
            character_class=c_class,
            level=level,
            race=self.race,
            background=self.background
        )
        stats = CharacterStats.objects.create(
            character=char,
            hit_points=hp,
            max_hit_points=max_hp,
            constitution=con,
            armor_class=14,
            **stats_kwargs
        )
        return char, stats

    def test_short_rest_spending_hit_dice_and_con_modifier(self):
        """Spending Hit Dice rolls the class hit die + CON mod (min 0) and heals up to max HP."""
        char, stats = self._create_character('Fighter1', self.fighter_class, level=5, hp=20, max_hp=50, con=14)
        # CON 14 = +2 modifier. Hit die = d10.
        self.assertEqual(get_available_hit_dice(char), 5)

        with mock.patch('random.randint', return_value=6):
            # 2 hit dice spent: 2 x (6 roll + 2 CON = 8) = 16 HP healed
            result = execute_short_rest(char, hit_dice_to_spend=2)

        stats.refresh_from_db()
        self.assertEqual(result['hp_gained'], 16)
        self.assertEqual(stats.hit_points, 36)
        self.assertEqual(stats.hit_dice_used, 2)
        self.assertEqual(result['hit_dice_remaining'], 3)
        self.assertEqual(len(result['dice_rolls']), 2)
        self.assertEqual(result['dice_rolls'][0]['healed'], 8)

    def test_short_rest_healing_capped_at_max_hp(self):
        """Short rest healing is capped at max_hit_points."""
        char, stats = self._create_character('WoundedHero', self.fighter_class, level=3, hp=28, max_hp=30, con=14)
        with mock.patch('random.randint', return_value=8):
            # 8 + 2 CON = 10 healed, but cap is 30 (only 2 actual HP needed)
            result = execute_short_rest(char, hit_dice_to_spend=1)

        stats.refresh_from_db()
        self.assertEqual(stats.hit_points, 30)
        self.assertEqual(result['hp_gained'], 2)

    def test_short_rest_not_enough_hit_dice(self):
        """Requesting more hit dice than remaining raises ValueError."""
        char, stats = self._create_character('Exhausted', self.wizard_class, level=3, hp=10, max_hp=20, hit_dice_used=3)
        with self.assertRaises(ValueError):
            execute_short_rest(char, hit_dice_to_spend=1)

    def test_short_rest_warlock_pact_magic_and_monk_ki_recovery(self):
        """Warlock pact magic slots and Monk Ki points reset on short rest even with 0 hit dice spent."""
        warlock, w_stats = self._create_character(
            'PactMage', self.warlock_class, level=5, hp=30, max_hp=30,
            spell_slots={'3': 2}, expended_spell_slots={'3': 2}
        )
        result = execute_short_rest(warlock, hit_dice_to_spend=0)
        w_stats.refresh_from_db()
        self.assertEqual(w_stats.expended_spell_slots, {})
        self.assertTrue(any("Warlock Pact Magic" in f for f in result['features_recovered']))

        monk, m_stats = self._create_character('ZenMonk', self.monk_class, level=5, hp=35, max_hp=35, ki_points_used=4)
        m_result = execute_short_rest(monk, hit_dice_to_spend=0)
        m_stats.refresh_from_db()
        self.assertEqual(m_stats.ki_points_used, 0)
        self.assertTrue(any("Ki points restored" in f for f in m_result['features_recovered']))

    def test_short_rest_multiclass_warlock_sorcerer_slot_persistence(self):
        """Multiclass character resets Warlock pact slots while Sorcerer long-rest slots remain expended."""
        from characters.models import CharacterClassLevel
        sorc_class = CharacterClass.objects.create(name='sorcerer', hit_dice='d6')
        mc_char, mc_stats = self._create_character(
            'WarlockSorcerer', self.warlock_class, level=6, hp=35, max_hp=35,
            spell_slots={'1': 2, '3': 2}, expended_spell_slots={'1': 2, '3': 2}
        )
        CharacterClassLevel.objects.create(character=mc_char, character_class=self.warlock_class, level=5)
        CharacterClassLevel.objects.create(character=mc_char, character_class=sorc_class, level=1)

        execute_short_rest(mc_char, hit_dice_to_spend=0)

        mc_stats.refresh_from_db()
        # Level 3 (Warlock pact) should be reset; Level 1 (Sorcerer) should persist
        self.assertNotIn('3', mc_stats.expended_spell_slots)
        self.assertEqual(mc_stats.expended_spell_slots.get('1'), 2)

    def test_long_rest_full_restoration(self):
        """Long rest restores HP to max, recovers half hit dice (min 1), and clears all expended spell slots."""
        char, stats = self._create_character(
            'HeroTired', self.wizard_class, level=6, hp=12, max_hp=36, hit_dice_used=4,
            temporary_hit_points=5,
            spell_slots={'1': 4, '2': 3, '3': 3},
            expended_spell_slots={'1': 3, '3': 2},
            sorcery_points_used=2,
            ki_points_used=3
        )
        result = execute_long_rest(char)
        stats.refresh_from_db()

        self.assertEqual(stats.hit_points, 36)
        self.assertEqual(stats.temporary_hit_points, 0)
        # Regained half total level: 6 // 2 = 3 hit dice regained (used drops from 4 to 1)
        self.assertEqual(stats.hit_dice_used, 1)
        self.assertEqual(result['hit_dice_recovered'], 3)
        self.assertEqual(stats.expended_spell_slots, {})
        self.assertEqual(stats.ki_points_used, 0)
        self.assertEqual(stats.sorcery_points_used, 0)

    def test_combat_participant_synchronization_on_rest(self):
        """Resting updates associated combat participants' HP, feature tags, and death saves."""
        session = CombatSession.objects.create(status='active')
        char, stats = self._create_character('FighterInCombat', self.fighter_class, level=4, hp=10, max_hp=40)
        participant = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=char,
            current_hp=10,
            max_hp=40,
            armor_class=16,
            death_save_failures=2,
            death_save_successes=1,
            feature_uses={'action_surge_used': True, 'second_wind_used': True}
        )

        # Short rest resets short-rest features and updates current_hp
        with mock.patch('random.randint', return_value=8):
            execute_short_rest(char, hit_dice_to_spend=1)

        participant.refresh_from_db()
        stats.refresh_from_db()
        self.assertEqual(participant.current_hp, stats.hit_points)
        self.assertFalse(participant.feature_uses.get('action_surge_used'))
        self.assertFalse(participant.feature_uses.get('second_wind_used'))

        # Long rest also clears death save counters and resets HP to max
        execute_long_rest(char)
        participant.refresh_from_db()
        self.assertEqual(participant.current_hp, 40)
        self.assertEqual(participant.death_save_failures, 0)
        self.assertEqual(participant.death_save_successes, 0)

    def test_character_viewset_rest_api_endpoints(self):
        """CharacterViewSet /short_rest/ and /long_rest/ endpoints handle JSON requests properly."""
        char, stats = self._create_character('APIRester', self.fighter_class, level=4, hp=15, max_hp=35)
        view = CharacterViewSet.as_view({'post': 'short_rest'})

        # Short rest request via API
        request = self.factory.post(
            f'/api/characters/{char.id}/short_rest/',
            {'hit_dice_to_spend': 1},
            format='json'
        )
        force_authenticate(request, user=self.user)
        response = view(request, pk=char.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('hp_gained', response.data)
        self.assertIn('hit_dice_remaining', response.data)

        # Long rest request via API
        view_long = CharacterViewSet.as_view({'post': 'long_rest'})
        req_long = self.factory.post(f'/api/characters/{char.id}/long_rest/', format='json')
        force_authenticate(req_long, user=self.user)
        res_long = view_long(req_long, pk=char.id)

        self.assertEqual(res_long.status_code, 200)
        self.assertEqual(res_long.data['hit_points'], 35)
        self.assertEqual(res_long.data['current_hp'], 35)
