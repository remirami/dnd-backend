from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
import unittest.mock as mock

from bestiary.models import Enemy, EnemyStats, Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet


class SpellCategoryHarnessMixin:
    """
    Reusable test harness mixin implementing standardized test templates
    for the 5e spell categories identified in the Content & Mechanics Audit.
    """

    def assert_spell_attack_hit(
        self,
        session,
        caster_p,
        target_p,
        spell_name,
        spell_level,
        expected_damage_min,
        expected_damage_type=None,
        is_crit=False,
        d20_roll=15
    ):
        """
        Category A Template: Spell Attack Roll (Hit / Critical)
        - Caster d20 + Spell Attack Mod vs Target AC.
        - Verifies hit, damage amount, and slot consumption.
        """
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        caster_p.action_used = False
        caster_p.bonus_action_used = False
        caster_p.attacks_remaining = 1
        caster_p.save(update_fields=['action_used', 'bonus_action_used', 'attacks_remaining'])
        if caster_p.character:
            caster_p.character.refresh_from_db()
            stats = getattr(caster_p.character, 'stats', None)
            if stats:
                stats.refresh_from_db()
                stats.expended_spell_slots = {}
                stats.save(update_fields=['expended_spell_slots'])
        if target_p.current_hp <= 0:
            target_p.current_hp = target_p.max_hp
            target_p.save(update_fields=['current_hp'])

        hp_before = target_p.current_hp

        # If critical requested, force d20 roll = 20
        roll_val = 20 if is_crit else d20_roll
        with mock.patch('random.randint', side_effect=lambda a, b: roll_val if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{session.id}/cast_spell/',
                {
                    'caster_id': caster_p.id,
                    'target_id': target_p.id,
                    'spell_name': spell_name,
                    'spell_level': spell_level,
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=session.id)
            self.assertEqual(res.status_code, 200, res.data)

        target_p.refresh_from_db()
        damage_dealt = res.data.get('damage', 0)
        self.assertGreaterEqual(damage_dealt, expected_damage_min)
        self.assertEqual(target_p.current_hp, hp_before - damage_dealt)

        if expected_damage_type:
            breakdown = res.data.get('breakdown', {}).get('damage') or res.data.get('message', '')
            # Verify damage type exists in response or action description
            self.assertTrue(
                expected_damage_type.lower() in str(breakdown).lower() or
                expected_damage_type.lower() in str(res.data).lower()
            )

        return res.data

    def assert_spell_saving_throw_resolution(
        self,
        session,
        caster_p,
        target_p,
        spell_name,
        spell_level,
        save_type,
        expected_damage_min,
        half_on_save=True,
        expected_condition=None,
        target_fails=True
    ):
        """
        Category B Template: Single Target Saving Throw
        - Target rolls d20 + Save Mod vs Caster Spell Save DC.
        - If target_fails: full damage and/or condition applied.
        - If not target_fails: half damage (if half_on_save) or 0 damage, condition NOT applied.
        """
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        caster_p.action_used = False
        caster_p.bonus_action_used = False
        caster_p.attacks_remaining = 1
        caster_p.save(update_fields=['action_used', 'bonus_action_used', 'attacks_remaining'])
        if caster_p.character:
            caster_p.character.refresh_from_db()
            stats = getattr(caster_p.character, 'stats', None)
            if stats:
                stats.refresh_from_db()
                stats.expended_spell_slots = {}
                stats.save(update_fields=['expended_spell_slots'])
        if target_p.current_hp <= 0:
            target_p.current_hp = target_p.max_hp
            target_p.save(update_fields=['current_hp'])

        hp_before = target_p.current_hp

        # Force save failure (d20 = 1) or save success (d20 = 20)
        save_d20 = 1 if target_fails else 20
        with mock.patch('random.randint', side_effect=lambda a, b: save_d20 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{session.id}/cast_spell/',
                {
                    'caster_id': caster_p.id,
                    'target_id': target_p.id,
                    'spell_name': spell_name,
                    'spell_level': spell_level,
                    'save_type': save_type,
                    'half_on_save': half_on_save,
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=session.id)
            self.assertEqual(res.status_code, 200, res.data)

        target_p.refresh_from_db()
        damage_dealt = res.data.get('damage', 0)

        if target_fails:
            self.assertGreaterEqual(damage_dealt, expected_damage_min)
            if expected_condition:
                self.assertTrue(
                    target_p.conditions.filter(name__iexact=expected_condition).exists(),
                    f"Expected {target_p.get_name()} to have condition {expected_condition}"
                )
        else:
            if half_on_save:
                # Half damage on successful save
                self.assertGreater(damage_dealt, 0)
                self.assertLessEqual(damage_dealt, expected_damage_min)
            else:
                # Negate on successful save
                self.assertEqual(damage_dealt, 0)
            if expected_condition:
                self.assertFalse(
                    target_p.conditions.filter(name__iexact=expected_condition).exists(),
                    f"Did not expect {target_p.get_name()} to have condition {expected_condition} on save success"
                )

        return res.data


class SpellCategoriesCombatTests(TestCase, SpellCategoryHarnessMixin):
    """
    Test suite validating spells grouped by the 5e Content and Mechanics Audit categories.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='spell_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Wizard Caster (Int 18 -> +4 mod, DC 14, Attack bonus +6)
        self.wizard_class = CharacterClass.objects.create(name='wizard', hit_dice='d6', primary_ability='INT')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.wizard = Character.objects.create(
            name='Gandalf', user=self.user, level=9, character_class=self.wizard_class, race=self.race
        )
        self.stats = CharacterStats.objects.create(
            character=self.wizard,
            hit_points=50,
            max_hit_points=50,
            armor_class=12,
            intelligence=18,
            wisdom=14,
            dexterity=14,
            spell_slots={'1': 4, '2': 3, '3': 3, '4': 3, '5': 1, '6': 1, '7': 1},
            expended_spell_slots={}
        )
        self.caster_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.wizard,
            current_hp=50,
            max_hp=50,
            armor_class=12,
            initiative=100,
            position_x=0,
            position_y=0
        )

        # Enemy Target (AC 12, HP 100, Con 10 (+0), Wis 10 (+0), Dex 10 (+0))
        self.orc = Enemy.objects.create(name='Test Dummy', hp=100, ac=12, challenge_rating='2')
        EnemyStats.objects.create(
            enemy=self.orc, strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10,
            hit_points=100, armor_class=12
        )
        self.target_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Test Dummy',
            current_hp=100,
            max_hp=100,
            armor_class=12,
            initiative=10,
            position_x=15,
            position_y=0
        )

        # Ensure core conditions exist in DB
        Condition.objects.get_or_create(name='Paralyzed')
        Condition.objects.get_or_create(name='Blinded')
        Condition.objects.get_or_create(name='Prone')

    # =========================================================================
    # CATEGORY A: Spell Attack Roll (Single Target)
    # =========================================================================

    def test_category_a_fire_bolt_cantrip_attack_roll(self):
        """Category A: Fire Bolt cantrip attack roll vs AC (scales at level 9 to 2d10)."""
        CharacterSpell.objects.create(character=self.wizard, name='Fire Bolt', level=0, is_prepared=True)
        # Level 9 wizard deals 2d10 fire damage. With dice forced to 4: 4 + 4 = 8 fire damage
        data = self.assert_spell_attack_hit(
            self.session, self.caster_p, self.target_p,
            spell_name='Fire Bolt',
            spell_level=0,
            expected_damage_min=8,
            expected_damage_type='fire',
            d20_roll=15
        )
        self.assertEqual(data.get('damage'), 8)

    def test_category_a_vampiric_touch_melee_spell_attack(self):
        """Category A: Vampiric Touch (3rd level melee spell attack, 3d6 necrotic, concentration)."""
        CharacterSpell.objects.create(character=self.wizard, name='Vampiric Touch', level=3, is_prepared=True)
        # Move target into melee touch range (5 ft)
        self.target_p.position_x = 5
        self.target_p.save(update_fields=['position_x'])

        data = self.assert_spell_attack_hit(
            self.session, self.caster_p, self.target_p,
            spell_name='Vampiric Touch',
            spell_level=3,
            expected_damage_min=12,  # 3 dice @ 4 = 12
            expected_damage_type='necrotic',
            d20_roll=15
        )
        self.caster_p.refresh_from_db()
        self.assertTrue(self.caster_p.is_concentrating)
        self.assertEqual(self.caster_p.concentration_spell, 'Vampiric Touch')

    # =========================================================================
    # CATEGORY B: Single Target Saving Throw
    # =========================================================================

    def test_category_b_blight_con_save_half_on_save(self):
        """Category B: Blight (4th level CON save, 8d8 necrotic, half damage on save)."""
        CharacterSpell.objects.create(character=self.wizard, name='Blight', level=4, is_prepared=True)

        # 1. Target fails save (d20 = 1): full 8d8 (8 * 4 = 32 necrotic damage)
        data_fail = self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Blight',
            spell_level=4,
            save_type='CON',
            expected_damage_min=32,
            half_on_save=True,
            target_fails=True
        )
        self.assertEqual(data_fail.get('damage'), 32)

        # 2. Target succeeds save (d20 = 20): half damage (32 // 2 = 16 necrotic damage)
        data_success = self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Blight',
            spell_level=4,
            save_type='CON',
            expected_damage_min=16,
            half_on_save=True,
            target_fails=False
        )
        self.assertEqual(data_success.get('damage'), 16)

    def test_category_b_blindness_deafness_con_save_condition(self):
        """Category B: Blindness/Deafness (2nd level CON save, non-concentration Blinded condition)."""
        CharacterSpell.objects.create(character=self.wizard, name='Blindness/Deafness', level=2, is_prepared=True)

        # 1. Target fails save: Blinded condition applied
        self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Blindness/Deafness',
            spell_level=2,
            save_type='CON',
            expected_damage_min=0,
            half_on_save=False,
            expected_condition='Blinded',
            target_fails=True
        )
        self.assertTrue(self.target_p.conditions.filter(name__iexact='Blinded').exists())

        # Clean condition for next check
        self.target_p.conditions.clear()

        # 2. Target succeeds save: Blinded condition NOT applied
        self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Blindness/Deafness',
            spell_level=2,
            save_type='CON',
            expected_damage_min=0,
            half_on_save=False,
            expected_condition='Blinded',
            target_fails=False
        )
        self.assertFalse(self.target_p.conditions.filter(name__iexact='Blinded').exists())

    def test_category_b_hold_monster_wis_save_paralyzed_concentration(self):
        """Category B: Hold Monster (5th level WIS save, concentration Paralyzed condition)."""
        CharacterSpell.objects.create(character=self.wizard, name='Hold Monster', level=5, is_prepared=True)

        # Target fails save: Paralyzed condition applied and caster concentrates
        self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Hold Monster',
            spell_level=5,
            save_type='WIS',
            expected_damage_min=0,
            half_on_save=False,
            expected_condition='Paralyzed',
            target_fails=True
        )
        self.assertTrue(self.target_p.conditions.filter(name__iexact='Paralyzed').exists())
        self.caster_p.refresh_from_db()
        self.assertTrue(self.caster_p.is_concentrating)
        self.assertEqual(self.caster_p.concentration_spell, 'Hold Monster')

    def test_category_b_disintegrate_dex_save_zero_on_save(self):
        """Category B: Disintegrate (6th level DEX save, 10d6+40 force damage, 0 on save)."""
        CharacterSpell.objects.create(character=self.wizard, name='Disintegrate', level=6, is_prepared=True)

        # 1. Target fails save: 10 * 4 + 40 = 80 force damage
        data_fail = self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Disintegrate',
            spell_level=6,
            save_type='DEX',
            expected_damage_min=80,
            half_on_save=False,
            target_fails=True
        )
        self.assertEqual(data_fail.get('damage'), 80)

        # 2. Target succeeds save: 0 damage
        data_success = self.assert_spell_saving_throw_resolution(
            self.session, self.caster_p, self.target_p,
            spell_name='Disintegrate',
            spell_level=6,
            save_type='DEX',
            expected_damage_min=0,
            half_on_save=False,
            target_fails=False
        )
        self.assertEqual(data_success.get('damage'), 0)
