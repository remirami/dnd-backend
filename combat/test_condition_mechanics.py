from django.test import TestCase
from django.contrib.auth.models import User

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession


class ConditionMechanicsCombatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='condition_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Conditions
        self.incapacitated, _ = Condition.objects.get_or_create(name='incapacitated')
        self.stunned, _ = Condition.objects.get_or_create(name='stunned')
        self.paralyzed, _ = Condition.objects.get_or_create(name='paralyzed')
        self.poisoned, _ = Condition.objects.get_or_create(name='poisoned')
        self.prone, _ = Condition.objects.get_or_create(name='prone')

        # Character
        self.char_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.hero = Character.objects.create(
            name='Arthur', user=self.user, level=1, character_class=self.char_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.hero, hit_points=20, max_hit_points=20, armor_class=14, strength=14, dexterity=14
        )

        self.hero_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.hero,
            current_hp=20,
            max_hp=20,
            armor_class=14,
            initiative=20
        )

        # Enemy
        self.goblin = Enemy.objects.create(name='Goblin Raider', hp=15, ac=12, challenge_rating='1/4')
        EnemyStats.objects.create(
            enemy=self.goblin, strength=10, dexterity=14, constitution=10, intelligence=10, wisdom=10, charisma=8,
            hit_points=15, armor_class=12
        )
        self.goblin_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Raider',
            current_hp=15,
            max_hp=15,
            armor_class=12,
            initiative=10
        )

    def test_incapacitated_character_cannot_attack(self):
        """An incapacitated character should receive HTTP 400 when attempting an attack."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        self.hero_p.conditions.add(self.incapacitated)
        self.assertTrue(self.hero_p.is_incapacitated())

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot take actions', response.data['error'])

    def test_stunned_character_cannot_attack(self):
        """A stunned character is incapacitated and cannot attack."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        self.hero_p.conditions.add(self.stunned)
        self.assertTrue(self.hero_p.is_incapacitated())
        self.assertEqual(self.hero_p.get_incapacitating_condition(), 'Stunned')

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot take actions', response.data['error'])

    def test_incapacitated_enemy_ai_skips_turn(self):
        """An incapacitated enemy AI should skip its turn without executing attacks."""
        from combat.combat_ai import resolve_enemy_turn

        self.goblin_p.conditions.add(self.paralyzed)
        self.assertTrue(self.goblin_p.is_incapacitated())

        actions = resolve_enemy_turn(self.session, self.goblin_p)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'skip')
        self.assertIn('cannot take actions', actions[0]['message'])

    def test_auto_critical_on_paralyzed_target(self):
        """Melee attacks that hit a paralyzed target become critical hits."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet
        import unittest.mock as mock

        self.goblin_p.conditions.add(self.paralyzed)

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        # Mock roll to 15 (which hits AC 12, but is not a natural 20)
        with mock.patch('combat.utils.random.randint', return_value=15):
            response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['hit'])
        self.assertTrue(response.data['critical'])

    def test_client_cannot_arbitrarily_claim_advantage(self):
        """Passing advantage=True without conditions or dm_override must be ignored."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
                'advantage': True,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data.get('advantage', False))

    def test_dm_override_allows_manual_advantage(self):
        """In test mode with dm_override=True, manual advantage is respected."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
                'advantage': True,
                'dm_override': True,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('advantage', False))

    def test_prone_target_grants_melee_advantage(self):
        """Attacking a prone target with a melee attack automatically grants advantage."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        self.goblin_p.conditions.add(self.prone)
        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero_p.id,
                'target_id': self.goblin_p.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('advantage', False))
        self.assertTrue(any('prone' in r.lower() for r in response.data.get('advantage_reasons', [])))
