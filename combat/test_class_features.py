from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet
from items.models import DamageType, Weapon


class ClassFeaturesCombatTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='barbarian_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Damage types
        self.slashing, _ = DamageType.objects.get_or_create(name='Slashing')
        self.fire, _ = DamageType.objects.get_or_create(name='Fire')

        # Barbarian Character
        self.barb_class = CharacterClass.objects.create(name='barbarian', hit_dice='d12', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.barb = Character.objects.create(
            name='Conan', user=self.user, level=3, character_class=self.barb_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.barb, hit_points=35, max_hit_points=35, armor_class=14, strength=16, dexterity=14, constitution=16
        )

        self.barb_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.barb,
            current_hp=35,
            max_hp=35,
            armor_class=14,
            initiative=20
        )

        # Enemy
        self.orc = Enemy.objects.create(name='Orc Berserker', hp=30, ac=13, challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.orc, strength=16, dexterity=12, constitution=16, intelligence=7, wisdom=11, charisma=10,
            hit_points=30, armor_class=13
        )
        self.orc_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Orc Berserker',
            current_hp=30,
            max_hp=30,
            armor_class=13,
            initiative=10
        )

    def test_barbarian_rage_activation_and_damage_resistance(self):
        """Entering Rage grants resistance to Slashing damage (half damage)."""
        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': self.barb_p.id, 'feature_name': 'Rage'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        self.barb_p.refresh_from_db()
        self.assertTrue(self.barb_p.is_raging())
        self.assertTrue(self.barb_p.bonus_action_used)
        self.assertEqual(self.barb_p.get_rage_uses_remaining(), 2)  # Level 3 Barbarian starts with 3, uses 1 -> 2 left

        # Test physical damage resistance (20 Slashing damage -> 10 taken)
        new_hp, _ = self.barb_p.take_damage(20, damage_type=self.slashing)
        self.assertEqual(new_hp, 25)

        # Test non-physical damage (not resisted, 10 Fire damage -> 10 taken)
        new_hp, _ = self.barb_p.take_damage(10, damage_type=self.fire)
        self.assertEqual(new_hp, 15)

    def test_barbarian_reckless_attack_activation(self):
        """Barbarian can activate Reckless Attack on their turn."""
        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': self.barb_p.id, 'feature_name': 'Reckless Attack'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        self.barb_p.refresh_from_db()
        self.assertTrue(self.barb_p.feature_uses.get('reckless_attack_active'))

    def test_fighter_action_surge(self):
        """Fighter can use Action Surge to recover an action on their turn."""
        fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        fighter = Character.objects.create(
            name='Arthur', user=self.user, level=2, character_class=fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=fighter, hit_points=20, max_hit_points=20, armor_class=16, strength=16, dexterity=12
        )
        fighter_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=fighter,
            current_hp=20,
            max_hp=20,
            armor_class=16,
            initiative=15,
            action_used=True,
            attacks_remaining=0
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': fighter_p.id, 'feature_name': 'Action Surge'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        fighter_p.refresh_from_db()
        self.assertFalse(fighter_p.action_used)
        self.assertGreater(fighter_p.attacks_remaining, 0)
        self.assertTrue(fighter_p.feature_uses.get('action_surge_used'))

        # Second attempt should fail (1/rest)
        request2 = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': fighter_p.id, 'feature_name': 'Action Surge'},
            format='json'
        )
        response2 = view(request2, pk=self.session.id)
        self.assertEqual(response2.status_code, 400)
