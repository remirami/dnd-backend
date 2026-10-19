"""
Tests for High-Tier Class Passives (Levels 11-20)
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.
"""

from unittest import mock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession, ParticipantPosition
from combat.views.session_views import CombatSessionViewSet
from combat.high_tier_passives import (
    get_aura_of_protection_bonus,
    is_protected_by_aura_of_courage,
    apply_reliable_talent,
    apply_indomitable_might,
    check_relentless_rage,
    reset_relentless_rage_dc,
)
from combat.utils import calculate_ability_check, calculate_saving_throw
from combat.condition_effects import is_condition_immune, auto_apply_condition_from_spell


class HighTierPassivesTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='hightier_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Classes
        self.paladin_class, _ = CharacterClass.objects.get_or_create(name='paladin', hit_dice='d10', primary_ability='CHA')
        self.rogue_class, _ = CharacterClass.objects.get_or_create(name='rogue', hit_dice='d8', primary_ability='DEX')
        self.barbarian_class, _ = CharacterClass.objects.get_or_create(name='barbarian', hit_dice='d12', primary_ability='STR')
        self.fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race, _ = CharacterRace.objects.get_or_create(name='human', size='M', speed=30)

        # Conditions
        self.frightened_cond, _ = Condition.objects.get_or_create(name='frightened')
        self.paralyzed_cond, _ = Condition.objects.get_or_create(name='paralyzed')

    def _create_character(self, name, char_class, level=6, stats_dict=None, ruleset='2024'):
        char = Character.objects.create(
            user=self.user,
            name=name,
            level=level,
            character_class=char_class,
            race=self.race,
            ruleset_version=ruleset
        )
        defaults = {
            'strength': 16,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 10,
            'wisdom': 14,
            'charisma': 14,
            'armor_class': 15,
            'max_hit_points': 50,
            'hit_points': 50
        }
        if stats_dict:
            defaults.update(stats_dict)
        CharacterStats.objects.create(character=char, **defaults)
        return char

    def _create_participant(self, name, character=None, p_type='character', hp=50, max_hp=50, ac=15, feature_uses=None):
        return CombatParticipant.objects.create(
            combat_session=self.session,
            name=name,
            participant_type=p_type,
            character=character,
            current_hp=hp,
            max_hp=max_hp,
            armor_class=ac,
            initiative=10,
            feature_uses=feature_uses or {}
        )

    def test_aura_of_protection_bonus_calculation(self):
        """Paladin Level 6+ grants +CHA modifier (min +1) to saving throws within 10 ft."""
        # Paladin with CHA 16 (+3 modifier), Level 6
        paladin_char = self._create_character('Sir Gareth', self.paladin_class, level=6, stats_dict={'charisma': 16})
        paladin_p = self._create_participant('Sir Gareth', character=paladin_char, hp=50, max_hp=50)
        ParticipantPosition.objects.create(participant=paladin_p, x=0, y=0, z=0)

        # Self receives bonus
        self.assertEqual(paladin_p.get_aura_of_protection_bonus(), 3)

        # Allied Fighter at (5, 0) - within 10 ft
        ally_char = self._create_character('Roderick', self.fighter_class, level=6)
        ally_p = self._create_participant('Roderick', character=ally_char, hp=50, max_hp=50)
        ally_pos = ParticipantPosition.objects.create(participant=ally_p, x=5, y=0, z=0)

        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 3)

        # Move ally beyond 10 ft -> (15, 0)
        ally_pos.x = 15
        ally_pos.save()
        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 0)

        # Upgrade Paladin to Level 18 (aura radius extends to 30 ft)
        paladin_char.level = 18
        paladin_char.save()
        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 3)

    def test_aura_of_protection_unconscious_or_incapacitated(self):
        """Conscious requirement: an incapacitated or unconscious Paladin does not grant Aura of Protection."""
        paladin_char = self._create_character('Lady Brienne', self.paladin_class, level=8, stats_dict={'charisma': 18})
        paladin_p = self._create_participant('Lady Brienne', character=paladin_char, hp=60, max_hp=60)
        ParticipantPosition.objects.create(participant=paladin_p, x=0, y=0, z=0)

        ally_char = self._create_character('Pippin', self.fighter_class, level=8)
        ally_p = self._create_participant('Pippin', character=ally_char, hp=40, max_hp=40)
        ParticipantPosition.objects.create(participant=ally_p, x=5, y=0, z=0)

        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 4)

        # Paladin is incapacitated / paralyzed
        paladin_p.conditions.add(self.paralyzed_cond)
        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 0)

        # Paladin at 0 HP
        paladin_p.conditions.clear()
        paladin_p.current_hp = 0
        paladin_p.save()
        self.assertEqual(ally_p.get_aura_of_protection_bonus(), 0)

    def test_aura_of_courage_frightened_immunity(self):
        """Paladin Level 10+ grants immunity to frightened to self and allies within 10 ft."""
        paladin_char = self._create_character('Arthur', self.paladin_class, level=10, stats_dict={'charisma': 14})
        paladin_p = self._create_participant('Arthur', character=paladin_char, hp=80, max_hp=80)
        ParticipantPosition.objects.create(participant=paladin_p, x=0, y=0, z=0)

        ally_char = self._create_character('Bedivere', self.fighter_class, level=10)
        ally_p = self._create_participant('Bedivere', character=ally_char, hp=70, max_hp=70)
        ParticipantPosition.objects.create(participant=ally_p, x=5, y=0, z=0)

        self.assertTrue(is_condition_immune(paladin_p, 'frightened'))
        self.assertTrue(is_condition_immune(ally_p, 'frightened'))

        # Auto-apply condition from 'Cause Fear' is blocked
        cond = auto_apply_condition_from_spell(ally_p, 'Cause Fear')
        self.assertIsNone(cond)
        self.assertEqual(getattr(ally_p, 'last_condition_immune', None), 'frightened')
        self.assertFalse(ally_p.conditions.filter(name='frightened').exists())

    def test_rogue_reliable_talent(self):
        """Rogue Level 11+ treats proficient check d20 rolls of 1-9 as 10."""
        rogue_char = self._create_character('Shadow', self.rogue_class, level=11, stats_dict={'dexterity': 18})
        rogue_p = self._create_participant('Shadow', character=rogue_char, hp=50, max_hp=50)

        self.assertTrue(rogue_p.has_reliable_talent())

        # Proficient roll of 3 -> treated as 10!
        adj_roll, triggered = apply_reliable_talent(rogue_p, base_roll=3, proficiency=True)
        self.assertEqual(adj_roll, 10)
        self.assertTrue(triggered)

        # Full check calculation: DEX +4, Prof +4, base roll 2 -> 10 + 4 + 4 = 18
        total, breakdown = calculate_ability_check(
            base_roll=2,
            ability_modifier=4,
            proficiency_bonus=4,
            proficiency=True,
            reliable_talent=True
        )
        self.assertEqual(total, 18)
        self.assertIn('Reliable Talent from 2', breakdown)

        # Non-proficient check does not trigger
        adj_roll_nonprof, triggered_nonprof = apply_reliable_talent(rogue_p, base_roll=3, proficiency=False)
        self.assertEqual(adj_roll_nonprof, 3)
        self.assertFalse(triggered_nonprof)

    def test_barbarian_indomitable_might(self):
        """Barbarian Level 18+ replaces Strength check totals below Strength score with Strength score."""
        barb_char = self._create_character('Krag', self.barbarian_class, level=18, stats_dict={'strength': 20})
        barb_p = self._create_participant('Krag', character=barb_char, hp=200, max_hp=200)

        self.assertTrue(barb_p.has_indomitable_might())

        # STR check with total 12 (less than STR score 20) -> adjusted to 20
        adj_total, triggered = apply_indomitable_might(barb_p, 'STR', 12)
        self.assertEqual(adj_total, 20)
        self.assertTrue(triggered)

        # STR check with total 24 -> remains 24
        adj_total_high, triggered_high = apply_indomitable_might(barb_p, 'STR', 24)
        self.assertEqual(adj_total_high, 24)
        self.assertFalse(triggered_high)

        # Check in calculate_ability_check utility
        total, breakdown = calculate_ability_check(
            base_roll=2,
            ability_modifier=5,
            indomitable_might_score=20
        )
        self.assertEqual(total, 20)
        self.assertIn('Indomitable Might: adjusted 7 -> 20', breakdown)

    def test_barbarian_relentless_rage_success_and_scaling(self):
        """Barbarian Level 11+ raging makes CON save DC 10 (+5 scaling) to remain at 1 HP."""
        barb_char = self._create_character('Wulfgar', self.barbarian_class, level=11, stats_dict={'constitution': 16, 'strength': 18})
        barb_p = self._create_participant(
            'Wulfgar',
            character=barb_char,
            hp=20,
            max_hp=100,
            feature_uses={'is_raging': True, 'rage_rounds_left': 10, 'relentless_rage_dc': 10}
        )

        self.assertTrue(barb_p.has_relentless_rage())

        # Incoming 25 damage while at 20 HP (lethal damage drops potential HP to -5)
        # CON modifier +3, prof +4 -> total +7 on save.
        # Patch roll to 5 -> total 12 vs DC 10 -> SUCCESS!
        with mock.patch('combat.utils.roll_d20', return_value=(5, '')):
            hp, conc = barb_p.take_damage(25, damage_type='force')
            self.assertEqual(hp, 1)
            self.assertTrue(barb_p.is_active)
            self.assertTrue(barb_p.last_relentless_rage_triggered)
            self.assertEqual(barb_p.feature_uses['relentless_rage_dc'], 15)

        # Next hit: 10 damage. DC is now 15.
        # Patch roll to 10 -> total 17 vs DC 15 -> SUCCESS!
        with mock.patch('combat.utils.roll_d20', return_value=(10, '')):
            hp2, _ = barb_p.take_damage(10, damage_type='force')
            self.assertEqual(hp2, 1)
            self.assertEqual(barb_p.feature_uses['relentless_rage_dc'], 20)

        # Third hit: 10 damage. DC is now 20.
        # Patch roll to 2 -> total 9 vs DC 20 -> FAILS!
        with mock.patch('combat.utils.roll_d20', return_value=(2, '')):
            hp3, _ = barb_p.take_damage(10, damage_type='force')
            self.assertEqual(hp3, 0)
            self.assertFalse(barb_p.is_active)

    def test_fighter_indomitable_reroll_feature(self):
        """Fighter Level 9+ Indomitable rerolls saving throw adding Fighter level in 2024 rules."""
        fighter_char = self._create_character('Valerius', self.fighter_class, level=9, stats_dict={'constitution': 14}, ruleset='2024')
        fighter_p = self._create_participant('Valerius', character=fighter_char, hp=80, max_hp=80)

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        # Roll = 8. CON mod = +2, Fighter level bonus (2024) = +9 -> Total = 8 + 2 + 9 = 19
        with mock.patch('combat.utils.roll_d20', return_value=(8, '')):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/use_feature/',
                {
                    'actor_id': fighter_p.id,
                    'feature_name': 'Indomitable',
                    'save_type': 'CON'
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)
            self.assertIn('Indomitable', res.data.get('message', ''))
            self.assertIn('+9 Fighter level bonus', res.data.get('message', ''))
            fighter_p.refresh_from_db()
            self.assertEqual(fighter_p.feature_uses.get('indomitable_used_count'), 1)
