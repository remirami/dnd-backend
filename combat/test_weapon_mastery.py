from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
import unittest.mock as mock

from bestiary.models import Enemy, EnemyStats, Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet
from items.models import Weapon


class WeaponMasteryCombatTests(TestCase):
    """
    Test suite validating official 2024 SRD 5.2 Weapon Masteries:
    - Graze (Glaive, Greatsword)
    - Vex (Shortsword, Rapier, Handaxe, etc.)
    - Topple (Battleaxe, Maul, Quarterstaff, etc.)
    - Push (Warhammer, Pike, Greatclub, etc.)
    - Sap (Mace, Flail, Morningstar, etc.)
    - Slow (Longbow, Whip, Club, etc.)
    - Cleave (Greataxe, Halberd)
    - Nick (Dagger, Scimitar, etc.)
    - Isolation: 2014 rules characters do not trigger masteries.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='mastery_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)

        # 2024 Fighter (Level 5, STR 18 -> +4 mod, Proficiency +3)
        self.fighter_2024 = Character.objects.create(
            name='Krag 2024',
            user=self.user,
            level=5,
            character_class=self.fighter_class,
            race=self.race,
            ruleset_version='2024'
        )
        CharacterStats.objects.create(
            character=self.fighter_2024,
            hit_points=45,
            max_hit_points=45,
            armor_class=16,
            strength=18,
            dexterity=14,
            constitution=14
        )
        self.attacker_2024 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter_2024,
            current_hp=45,
            max_hp=45,
            armor_class=16,
            initiative=100,
            position_x=0,
            position_y=0
        )

        # 2014 Fighter (Level 5, STR 18 -> +4 mod)
        self.fighter_2014 = Character.objects.create(
            name='Krag 2014',
            user=self.user,
            level=5,
            character_class=self.fighter_class,
            race=self.race,
            ruleset_version='2014'
        )
        CharacterStats.objects.create(
            character=self.fighter_2014,
            hit_points=45,
            max_hit_points=45,
            armor_class=16,
            strength=18,
            dexterity=14,
            constitution=14
        )
        self.attacker_2014 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter_2014,
            current_hp=45,
            max_hp=45,
            armor_class=16,
            initiative=90,
            position_x=0,
            position_y=0
        )

        # Enemy Target 1 (AC 18, HP 100, CON +0)
        self.enemy = Enemy.objects.create(name='Target Dummy', hp=100, ac=18, challenge_rating='2')
        EnemyStats.objects.create(
            enemy=self.enemy, strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10,
            hit_points=100, armor_class=18
        )
        self.target_p1 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Target Dummy 1',
            current_hp=100,
            max_hp=100,
            armor_class=18,
            initiative=10,
            position_x=5,
            position_y=0
        )

        # Enemy Target 2 (Adjacent to Target 1 at x=5, y=5)
        self.target_p2 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Target Dummy 2',
            current_hp=100,
            max_hp=100,
            armor_class=14,
            initiative=9,
            position_x=5,
            position_y=5
        )

        # Prone condition
        Condition.objects.get_or_create(name='Prone')

    def test_graze_deals_ability_mod_on_miss_for_2024(self):
        """Graze: Missing with a 2024 Greatsword deals damage equal to ability modifier (4)."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        hp_before = self.target_p1.current_hp

        # Force d20 roll = 2 -> Total attack roll = 2 + 4 + 3 = 9 vs AC 18 -> Miss!
        with mock.patch('random.randint', side_effect=lambda a, b: 2 if b == 20 else 3):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Greatsword',
                    'damage_string': '2d6',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)

        self.target_p1.refresh_from_db()
        self.assertFalse(res.data['hit'])
        self.assertEqual(res.data['damage'], 4)  # STR mod is 4
        self.assertEqual(self.target_p1.current_hp, hp_before - 4)
        self.assertIn("Graze", str(res.data.get('breakdown', {}).get('damage') or ''))

    def test_graze_does_not_trigger_for_2014_rules(self):
        """2014 rules characters do not trigger Graze on a miss."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        hp_before = self.target_p1.current_hp

        # Force miss
        with mock.patch('random.randint', side_effect=lambda a, b: 2 if b == 20 else 3):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2014.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Greatsword',
                    'damage_string': '2d6',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)

        self.target_p1.refresh_from_db()
        self.assertFalse(res.data['hit'])
        self.assertEqual(res.data['damage'], 0)
        self.assertEqual(self.target_p1.current_hp, hp_before)

    def test_vex_grants_advantage_on_next_attack(self):
        """Vex: Hitting with a Shortsword grants Advantage on the next attack against that target."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})

        # 1. First attack: Hit with Shortsword (roll = 15 -> hit)
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req1 = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Shortsword',
                    'damage_string': '1d6',
                    'dm_override': True
                },
                format='json'
            )
            res1 = view(req1, pk=self.session.id)
            self.assertEqual(res1.status_code, 200)
            self.assertTrue(res1.data['hit'])

        self.attacker_2024.refresh_from_db()
        self.assertEqual(self.attacker_2024.feature_uses.get('vex_target_id'), self.target_p1.id)

        # 2. Second attack: Must automatically have Advantage
        self.attacker_2024.action_used = False
        self.attacker_2024.attacks_remaining = 1
        self.attacker_2024.save()

        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req2 = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Shortsword',
                    'damage_string': '1d6',
                    'dm_override': True
                },
                format='json'
            )
            res2 = view(req2, pk=self.session.id)
            self.assertEqual(res2.status_code, 200)

        self.assertTrue(res2.data['is_advantage'])
        self.assertIn("Weapon Mastery: Vex (Advantage vs target)", res2.data['advantage_reasons'])

    def test_topple_knocks_target_prone_on_failed_save(self):
        """Topple: Hitting with a Battleaxe forces a CON save; failure knocks target Prone."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})

        # Roll = 15 (hit vs AC 18 with +7 mod = 22). Topple CON save roll = 1 -> Fail!
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            with mock.patch('combat.utils.roll_d20', return_value=(1, "1")):
                req = self.factory.post(
                    f'/combat/sessions/{self.session.id}/attack/',
                    {
                        'attacker_id': self.attacker_2024.id,
                        'target_id': self.target_p1.id,
                        'attack_name': 'Battleaxe',
                        'damage_string': '1d8',
                        'dm_override': True
                    },
                    format='json'
                )
                res = view(req, pk=self.session.id)
                self.assertEqual(res.status_code, 200)

        self.target_p1.refresh_from_db()
        self.assertTrue(self.target_p1.conditions.filter(name__iexact='Prone').exists())
        self.assertIn("prone", str(res.data['breakdown']['damage']).lower())

    def test_push_forces_movement_away(self):
        """Push: Hitting with a Warhammer pushes target 10 ft straight away."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        # Attacker at (0, 0), Target at (5, 0). Push moves target to (15, 0).
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Warhammer',
                    'damage_string': '1d8',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        self.target_p1.refresh_from_db()
        self.assertEqual(self.target_p1.position_x, 15)
        self.assertEqual(self.target_p1.position_y, 0)
        self.assertIn("Push", str(res.data['breakdown']['damage']))

    def test_sap_inflicts_disadvantage_on_target_next_attack(self):
        """Sap: Hitting with a Mace causes target to have Disadvantage on its next attack."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})

        # 1. Fighter saps target
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Mace',
                    'damage_string': '1d6',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        self.target_p1.refresh_from_db()
        self.assertTrue(self.target_p1.feature_uses.get('sapped'))

        # Ensure no flanking ally interferes with disadvantage
        self.target_p2.position_y = 30
        self.target_p2.save()

        # 2. Target dummy makes an attack: must have Disadvantage
        with mock.patch('random.randint', side_effect=lambda a, b: 12 if b == 20 else 3):
            req2 = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.target_p1.id,
                    'target_id': self.attacker_2024.id,
                    'attack_name': 'Slam',
                    'damage_string': '1d6',
                    'dm_override': True
                },
                format='json'
            )
            res2 = view(req2, pk=self.session.id)
            self.assertEqual(res2.status_code, 200)

        self.assertTrue(res2.data['is_disadvantage'])
        self.assertIn("Weapon Mastery: Sap (Disadvantage on attack)", res2.data['disadvantage_reasons'])

    def test_slow_reduces_speed(self):
        """Slow: Hitting with a Longbow reduces target's walking speed by 10 ft."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        base_speed = self.target_p1.speed  # 30

        # Move target into longbow range (30 ft)
        self.target_p1.position_x = 30
        self.target_p1.save()

        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Longbow',
                    'damage_string': '1d8',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        self.target_p1.refresh_from_db()
        self.assertEqual(self.target_p1.speed, base_speed - 10)  # 20 ft

    def test_cleave_hits_second_target(self):
        """Cleave: Hitting with a Greataxe strikes a second adjacent target within 5 ft."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        hp_p2_before = self.target_p2.current_hp

        # Attacker at (0, 0), Target 1 at (5, 0), Target 2 at (5, 5) within reach
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Greataxe',
                    'damage_string': '1d12',
                    'cleave_target_id': self.target_p2.id,
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        self.target_p2.refresh_from_db()
        self.assertLess(self.target_p2.current_hp, hp_p2_before)
        self.assertIn("Cleave", str(res.data['breakdown']['damage']))

    def test_nick_does_not_consume_bonus_action(self):
        """Nick: Off-hand attack with a Dagger does not consume the character's bonus action."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        self.attacker_2024.bonus_action_used = False
        self.attacker_2024.save()

        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': self.attacker_2024.id,
                    'target_id': self.target_p1.id,
                    'attack_name': 'Dagger',
                    'damage_string': '1d4',
                    'is_off_hand': True,
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        self.attacker_2024.refresh_from_db()
        self.assertFalse(self.attacker_2024.bonus_action_used)
