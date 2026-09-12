from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterFeature
from combat.models import CombatSession, CombatParticipant
from bestiary.models import Enemy, EnemyStats


class CombatExtraAttackRound1Tests(TestCase):
    """Test Extra Attack calculations on Turn 1 of combat and throughout rounds"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testbarbarian', password='password123')
        self.client.force_authenticate(user=self.user)

        self.barbarian_class = CharacterClass.objects.create(name='barbarian', hit_dice='d12')
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10')
        self.race = CharacterRace.objects.create(name='Human')

        # Level 5 Barbarian WITH explicit Extra Attack feature
        self.barbarian_lvl5 = Character.objects.create(
            user=self.user,
            name='Grog Lvl 5',
            level=5,
            character_class=self.barbarian_class,
            race=self.race
        )
        CharacterStats.objects.create(
            character=self.barbarian_lvl5,
            strength=18, dexterity=14, constitution=16,
            max_hit_points=55, hit_points=55, armor_class=15
        )
        CharacterFeature.objects.create(
            character=self.barbarian_lvl5,
            name='Extra Attack',
            feature_type='class'
        )

        # Level 5 Barbarian WITHOUT explicit CharacterFeature (tests class/level fallback)
        self.barbarian_no_feature = Character.objects.create(
            user=self.user,
            name='Conan No Feature',
            level=5,
            character_class=self.barbarian_class,
            race=self.race
        )
        CharacterStats.objects.create(
            character=self.barbarian_no_feature,
            strength=18, dexterity=14, constitution=16,
            max_hit_points=55, hit_points=55, armor_class=15
        )

        # Level 1 Barbarian (should have only 1 attack)
        self.barbarian_lvl1 = Character.objects.create(
            user=self.user,
            name='Rookie Barbarian',
            level=1,
            character_class=self.barbarian_class,
            race=self.race
        )
        CharacterStats.objects.create(
            character=self.barbarian_lvl1,
            strength=16, dexterity=14, constitution=16,
            max_hit_points=15, hit_points=15, armor_class=14
        )

        # Level 11 Fighter (should have 3 attacks via Extra Attack 2)
        self.fighter_lvl11 = Character.objects.create(
            user=self.user,
            name='Veteran Fighter',
            level=11,
            character_class=self.fighter_class,
            race=self.race
        )
        CharacterStats.objects.create(
            character=self.fighter_lvl11,
            strength=20, dexterity=12, constitution=16,
            max_hit_points=100, hit_points=100, armor_class=18
        )

        # Enemy target
        self.enemy = Enemy.objects.create(name='Target Dummy', challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.enemy,
            strength=10, dexterity=10, constitution=10,
            intelligence=10, wisdom=10, charisma=10,
            hit_points=100, armor_class=10
        )

    def test_participant_creation_initializes_extra_attack(self):
        """CombatParticipant should initialize attacks_remaining = 2 upon creation for level 5 Barbarian"""
        session = CombatSession.objects.create(status='preparing')
        p = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.barbarian_lvl5,
            initiative=15,
            current_hp=55,
            max_hp=55,
            armor_class=15
        )
        self.assertEqual(p.attacks_remaining, 2)

    def test_level_5_fallback_without_feature_record(self):
        """Even if CharacterFeature records are missing, Level 5 Barbarian gets 2 attacks via fallback"""
        session = CombatSession.objects.create(status='preparing')
        p = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.barbarian_no_feature,
            initiative=15,
            current_hp=55,
            max_hp=55,
            armor_class=15
        )
        self.assertEqual(p.attacks_remaining, 2)

    def test_level_1_has_single_attack(self):
        """Level 1 character gets 1 attack"""
        session = CombatSession.objects.create(status='preparing')
        p = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.barbarian_lvl1,
            initiative=15,
            current_hp=15,
            max_hp=15,
            armor_class=14
        )
        self.assertEqual(p.attacks_remaining, 1)

    def test_level_11_fighter_has_three_attacks(self):
        """Level 11 Fighter gets 3 attacks"""
        session = CombatSession.objects.create(status='preparing')
        p = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.fighter_lvl11,
            initiative=15,
            current_hp=100,
            max_hp=100,
            armor_class=18
        )
        self.assertEqual(p.attacks_remaining, 3)

    def test_round_1_turn_0_extra_attack_lifecycle(self):
        """Full lifecycle: start combat, execute 2 attacks on Round 1, verify action economy and round 2 reset"""
        session = CombatSession.objects.create(status='preparing')
        p_hero = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.barbarian_lvl5,
            initiative=20,  # Goes first
            current_hp=55,
            max_hp=55,
            armor_class=15
        )
        p_enemy = CombatParticipant.objects.create(
            combat_session=session,
            participant_type='enemy',
            name='Target Dummy',
            initiative=10,  # Goes second
            current_hp=100,
            max_hp=100,
            armor_class=10
        )

        # Start combat
        start_resp = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        self.assertEqual(start_resp.status_code, status.HTTP_200_OK)

        p_hero.refresh_from_db()
        self.assertEqual(p_hero.attacks_remaining, 2, "Hero should have 2 attacks at the start of Round 1")
        self.assertFalse(p_hero.action_used, "Hero action should not be used yet")

        # Attack 1
        atk1_resp = self.client.post(f'/api/combat/sessions/{session.id}/attack/', {
            'attacker_id': p_hero.id,
            'target_id': p_enemy.id
        })
        self.assertEqual(atk1_resp.status_code, status.HTTP_200_OK)
        p_hero.refresh_from_db()
        self.assertEqual(p_hero.attacks_remaining, 1, "Should have 1 attack remaining after first attack")
        self.assertFalse(p_hero.action_used, "Action should not be fully consumed after 1 of 2 attacks")

        # Attack 2
        atk2_resp = self.client.post(f'/api/combat/sessions/{session.id}/attack/', {
            'attacker_id': p_hero.id,
            'target_id': p_enemy.id
        })
        self.assertEqual(atk2_resp.status_code, status.HTTP_200_OK)
        p_hero.refresh_from_db()
        self.assertEqual(p_hero.attacks_remaining, 0, "Should have 0 attacks remaining after second attack")
        self.assertTrue(p_hero.action_used, "Action should now be marked as used")

        # 3rd attack attempt in same turn should fail
        atk3_resp = self.client.post(f'/api/combat/sessions/{session.id}/attack/', {
            'attacker_id': p_hero.id,
            'target_id': p_enemy.id
        })
        self.assertEqual(atk3_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("has no attacks remaining", atk3_resp.json()['error'])

        # Advance turns: hero -> enemy -> hero (Round 2)
        next_resp1 = self.client.post(f'/api/combat/sessions/{session.id}/next_turn/')
        self.assertEqual(next_resp1.status_code, status.HTTP_200_OK)

        next_resp2 = self.client.post(f'/api/combat/sessions/{session.id}/next_turn/')
        self.assertEqual(next_resp2.status_code, status.HTTP_200_OK)

        session.refresh_from_db()
        self.assertEqual(session.current_round, 2, "Should now be round 2")
        self.assertEqual(session.get_current_participant().id, p_hero.id, "Should be hero's turn again")

        p_hero.refresh_from_db()
        self.assertEqual(p_hero.attacks_remaining, 2, "Hero should have 2 attacks again in Round 2")
        self.assertFalse(p_hero.action_used, "Hero action should be refreshed for Round 2")
