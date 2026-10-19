"""
Tests for Phase 9: Combat Feats & Warlock Invocations
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.
"""

from unittest import mock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession, ParticipantPosition, EnvironmentalEffect
from combat.views.session_views import CombatSessionViewSet
from combat.views.reaction_views import CombatReactionMixin
from combat.feats_and_invocations import (
    has_feat,
    has_eldritch_invocation,
    has_sentinel,
    check_sentinel_provocation,
    apply_sentinel_opportunity_hit,
    has_sharpshooter,
    resolve_sharpshooter_cover,
    resolve_sharpshooter_range,
    has_great_weapon_master,
    apply_power_attack_modifiers,
    trigger_gwm_bonus_attack,
    has_polearm_master,
    check_polearm_entry_provocation,
    has_war_caster,
    apply_agonizing_blast_bonus,
    apply_repelling_blast_push,
    has_devils_sight,
)
from combat.environmental_effects import get_lighting_attack_modifier, can_see_target


class FeatsAndInvocationsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='phase9_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        self.fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.warlock_class, _ = CharacterClass.objects.get_or_create(name='warlock', hit_dice='d8', primary_ability='CHA')
        self.wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard', hit_dice='d6', primary_ability='INT')
        self.race, _ = CharacterRace.objects.get_or_create(name='human', size='M', speed=30)

    def _create_participant(self, name, char_class, level=5, stats_dict=None, x=0, y=0, current_hp=40, max_hp=40, ptype='player', feature_uses=None):
        char = Character.objects.create(
            user=self.user,
            name=name,
            level=level,
            character_class=char_class,
            race=self.race,
            ruleset_version='2024'
        )
        defaults = {
            'strength': 16,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 10,
            'wisdom': 12,
            'charisma': 16,
            'armor_class': 15,
            'hit_points': current_hp,
            'max_hit_points': max_hp,
            'speed': 30,
            'spell_save_dc': 14,
            'spell_attack_bonus': 6,
        }
        if stats_dict:
            defaults.update(stats_dict)
        CharacterStats.objects.create(character=char, **defaults)

        participant = CombatParticipant.objects.create(
            combat_session=self.session,
            name=name,
            character=char,
            participant_type=ptype,
            current_hp=current_hp,
            max_hp=max_hp,
            armor_class=defaults['armor_class'],
            initiative=15,
            is_active=True,
            position_x=x,
            position_y=y,
            feature_uses=feature_uses or {}
        )
        ParticipantPosition.objects.create(
            participant=participant,
            x=x,
            y=y,
            z=0
        )
        return participant

    def test_sentinel_feat_disengage_bypass_and_speed_zero(self):
        """Sentinel: ignores target's Disengage action and reduces target's speed to 0 on hit."""
        sentinel_fighter = self._create_participant('SentinelKnight', self.fighter_class, feature_uses={'has_sentinel': True}, x=5, y=0)
        enemy_rogue = self._create_participant('SlipperyRogue', self.fighter_class, ptype='enemy', x=0, y=0)

        # 1. Normal enemy without Sentinel cannot OA against disengaged mover
        normal_guard = self._create_participant('Guard', self.fighter_class, x=5, y=5)
        self.assertFalse(check_sentinel_provocation(enemy_rogue, normal_guard, is_disengaged=True))

        # 2. Sentinel bypasses Disengage
        self.assertTrue(check_sentinel_provocation(enemy_rogue, sentinel_fighter, is_disengaged=True))

        # 3. Sentinel hit reduces speed to 0 (halts movement)
        applied, msg = apply_sentinel_opportunity_hit(enemy_rogue, sentinel_fighter)
        self.assertTrue(applied)
        self.assertIn("speed becomes 0", msg)
        self.assertTrue(enemy_rogue.feature_uses.get('sentinel_halted'))
        self.assertGreaterEqual(enemy_rogue.movement_used, 30)

    def test_sharpshooter_cover_ignoring_and_range_penalty(self):
        """Sharpshooter: ignores half and three-quarters cover, and removes disadvantage at long range."""
        archer = self._create_participant('Legolas', self.fighter_class, feature_uses={'has_sharpshooter': True})

        # Cover ignoring
        self.assertEqual(resolve_sharpshooter_cover(archer, 'half'), 'none')
        self.assertEqual(resolve_sharpshooter_cover(archer, 'three_quarters'), 'none')
        self.assertEqual(resolve_sharpshooter_cover(archer, 'full'), 'full')  # Full cover still blocks

        # Long range (Longbow: 150 normal / 600 long)
        self.assertFalse(resolve_sharpshooter_range(archer, distance=300, normal_range=150, long_range=600))

        # Non-sharpshooter has disadvantage at 300 ft
        normal_archer = self._create_participant('Bob', self.fighter_class)
        self.assertTrue(resolve_sharpshooter_range(normal_archer, distance=300, normal_range=150, long_range=600))

    def test_power_attack_sharpshooter_and_gwm(self):
        """Power Attack: -5 to hit / +10 to damage for Sharpshooter (ranged) and GWM (heavy melee)."""
        sharpshooter = self._create_participant('Sniper', self.fighter_class, feature_uses={'has_sharpshooter': True})
        gwm_fighter = self._create_participant('Berserker', self.fighter_class, feature_uses={'has_great_weapon_master': True})

        # Sharpshooter power attack on ranged attack
        atk_pen, dmg_bon, note = apply_power_attack_modifiers(sharpshooter, is_ranged=True, is_heavy=False, power_attack_requested=True)
        self.assertEqual(atk_pen, -5)
        self.assertEqual(dmg_bon, 10)
        self.assertIn("Sharpshooter", note)

        # GWM power attack on heavy melee attack
        atk_pen, dmg_bon, note = apply_power_attack_modifiers(gwm_fighter, is_ranged=False, is_heavy=True, power_attack_requested=True)
        self.assertEqual(atk_pen, -5)
        self.assertEqual(dmg_bon, 10)
        self.assertIn("Great Weapon Master", note)

        # GWM rejects non-heavy melee attack
        atk_pen, dmg_bon, _ = apply_power_attack_modifiers(gwm_fighter, is_ranged=False, is_heavy=False, power_attack_requested=True)
        self.assertEqual(atk_pen, 0)
        self.assertEqual(dmg_bon, 0)

    def test_gwm_bonus_attack_trigger(self):
        """Great Weapon Master: critical hit or reducing a target to 0 HP unlocks bonus attack."""
        gwm_fighter = self._create_participant('Berserker', self.fighter_class, feature_uses={'has_great_weapon_master': True})

        # Critical hit triggers bonus attack
        unlocked = trigger_gwm_bonus_attack(gwm_fighter, is_critical=True, target_dropped_to_zero=False)
        self.assertTrue(unlocked)
        self.assertTrue(gwm_fighter.feature_uses.get('gwm_bonus_attack_available'))

        # Reset
        gwm_fighter.feature_uses['gwm_bonus_attack_available'] = False

        # Drop to 0 HP triggers bonus attack
        unlocked_drop = trigger_gwm_bonus_attack(gwm_fighter, is_critical=False, target_dropped_to_zero=True)
        self.assertTrue(unlocked_drop)
        self.assertTrue(gwm_fighter.feature_uses.get('gwm_bonus_attack_available'))

    def test_polearm_master_entry_provocation(self):
        """Polearm Master: entering weapon reach provokes an opportunity attack."""
        pam_sentinel = self._create_participant('Halberdier', self.fighter_class, feature_uses={'has_polearm_master': True}, x=0, y=0)
        # Mock equipped weapon as Halberd (10 ft reach)
        pam_sentinel.feature_uses['equipped_weapon_name'] = 'Halberd'

        mover = self._create_participant('OrcRunner', self.fighter_class, ptype='enemy')

        # Moving from (20, 0) to (10, 0) enters 10 ft reach of halberdier at (0, 0)
        with mock.patch('combat.feats_and_invocations.is_polearm_weapon', return_value=True):
            provoked = check_polearm_entry_provocation(mover, pam_sentinel, step_from=(20, 0), step_to=(10, 0))
            self.assertTrue(provoked)

            # Moving within reach (10, 0) to (5, 0) does not trigger entry provocation
            not_entry = check_polearm_entry_provocation(mover, pam_sentinel, step_from=(10, 0), step_to=(5, 0))
            self.assertFalse(not_entry)

    def test_war_caster_concentration_advantage_and_reaction(self):
        """War Caster: advantage on concentration checks and reaction spell casting."""
        caster = self._create_participant('WarMage', self.wizard_class, feature_uses={'has_war_caster': True})
        caster.is_concentrating = True
        caster.concentration_spell = 'Hold Person'
        caster.save()

        # In check_concentration, War Caster forces roll_d20(advantage=True)
        with mock.patch('combat.utils.roll_d20', return_value=(14, '14 (Advantage: 8, 14)')) as mock_roll:
            broken, save_total, dc, msg = caster.check_concentration(damage_amount=20)
            mock_roll.assert_called_with(advantage=True, lucky=False)
            self.assertFalse(broken)
            self.assertIn("Concentration maintained", msg)

    def test_warlock_agonizing_and_repelling_blast(self):
        """Agonizing Blast adds CHA modifier to Eldritch Blast damage; Repelling Blast pushes target 10 ft away."""
        warlock = self._create_participant('Lock', self.warlock_class, stats_dict={'charisma': 18}, feature_uses={'has_agonizing_blast': True, 'has_repelling_blast': True}, x=0, y=0)
        target = self._create_participant('Victim', self.fighter_class, ptype='enemy', x=10, y=0)

        # 1. Agonizing Blast (+4 CHA mod per beam)
        bonus_dmg, annot = apply_agonizing_blast_bonus(warlock, 'Eldritch Blast', beam_count=2)
        # 2 beams * +4 CHA mod = 8
        self.assertEqual(bonus_dmg, 8)
        self.assertIn("Agonizing Blast (+8 CHA)", annot)

        # 2. Repelling Blast: pushes target from (10, 0) to (20, 0)
        pushed, push_desc = apply_repelling_blast_push(warlock, target, 'Eldritch Blast', self.session)
        self.assertTrue(pushed)
        self.assertIn("pushed 10 ft away to (20 ft, 0 ft)", push_desc)
        target.refresh_from_db()
        self.assertEqual(target.position_x, 20)
        self.assertEqual(target.position_y, 0)

    def test_warlock_devils_sight_in_magical_darkness(self):
        """Devil's Sight: allows seeing in magical darkness without disadvantage."""
        warlock = self._create_participant('ShadowWarlock', self.warlock_class, feature_uses={'has_devils_sight': True})

        # Non-warlock gets disadvantage in magical darkness
        self.assertEqual(get_lighting_attack_modifier('magical_darkness', has_darkvision=True, has_devils_sight=False), 'disadvantage')

        # Warlock with Devil's Sight sees normally (modifier 0)
        self.assertEqual(get_lighting_attack_modifier('magical_darkness', has_darkvision=True, has_devils_sight=True), 0)

        # can_see_target returns True for Devil's Sight within 120 ft
        can_see, _ = can_see_target('magical_darkness', 'magical_darkness', attacker_darkvision=False, target_distance=60, has_devils_sight=True)
        self.assertTrue(can_see)
