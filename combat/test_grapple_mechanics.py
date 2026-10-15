from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, Feat, CharacterFeat
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet


class GrappleMechanicsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.viewset = CombatSessionViewSet.as_view({
            'post': 'grapple'
        })
        self.user = User.objects.create_user(username='grapple_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Standard conditions
        self.grappled_cond, _ = Condition.objects.get_or_create(name='Grappled')
        self.restrained_cond, _ = Condition.objects.get_or_create(name='Restrained')

        # Grappler Feat
        self.grappler_feat, _ = Feat.objects.get_or_create(
            name='Grappler',
            defaults={
                'description': 'Prerequisite: Strength 13 or higher. You have advantage on attack rolls against a creature you are grappling. You can use your action to try to pin a creature grappled by you.',
                'strength_requirement': 13
            }
        )

        # Fighter character (Medium size, STR 16)
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.human_race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.fighter_char = Character.objects.create(
            name='Valeros', user=self.user, level=5, character_class=self.fighter_class, race=self.human_race
        )
        CharacterStats.objects.create(
            character=self.fighter_char, hit_points=40, max_hit_points=40, armor_class=16, strength=16, dexterity=12
        )
        self.fighter_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter_char,
            current_hp=40,
            max_hp=40,
            armor_class=16,
            initiative=20,
            position_x=10,
            position_y=10,
            attacks_remaining=2
        )

        # Target enemy 1 (Medium goblin warrior, STR 10, DEX 14)
        self.orc = Enemy.objects.create(name='Orc Bruiser', hp=25, ac=13, size='Medium')
        EnemyStats.objects.create(
            enemy=self.orc, strength=14, dexterity=12, constitution=14, intelligence=8, wisdom=10, charisma=8,
            hit_points=25, armor_class=13
        )
        self.orc_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Orc Bruiser',
            current_hp=25,
            max_hp=25,
            armor_class=13,
            initiative=10,
            position_x=15,
            position_y=10
        )

        # Huge enemy (Giant)
        self.giant = Enemy.objects.create(name='Hill Giant', hp=105, ac=13, size='Huge')
        EnemyStats.objects.create(
            enemy=self.giant, strength=21, dexterity=8, constitution=19, intelligence=5, wisdom=9, charisma=6,
            hit_points=105, armor_class=13
        )
        self.giant_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Hill Giant',
            current_hp=105,
            max_hp=105,
            armor_class=13,
            initiative=5,
            position_x=15,
            position_y=10
        )

    def test_grapple_out_of_reach_fails(self):
        """Grapple fails if target is farther than 5 ft away."""
        self.orc_p.position_x = 25
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'grapple'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/grapple/', {
            'grappler_id': self.fighter_p.id,
            'target_id': self.orc_p.id
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('reach', response.data['error'].lower())

    def test_grapple_too_large_fails(self):
        """Medium creature cannot grapple a Huge creature (more than 1 size larger)."""
        view = CombatSessionViewSet.as_view({'post': 'grapple'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/grapple/', {
            'grappler_id': self.fighter_p.id,
            'target_id': self.giant_p.id
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('too large', response.data['error'].lower())

    def test_grapple_success_contested_check(self):
        """Successful grapple contest sets Grappled condition and speed 0."""
        view = CombatSessionViewSet.as_view({'post': 'grapple'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/grapple/', {
            'grappler_id': self.fighter_p.id,
            'target_id': self.orc_p.id
        })
        # Mock roll_d20: grappler rolls 18, defender rolls 8
        with patch('combat.tactical_endpoints.roll_d20', side_effect=[(18, '18'), (8, '8')]):
            response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertTrue(self.fighter_p.is_grappling)
        self.assertEqual(self.orc_p.grappled_by_id, self.fighter_p.id)
        self.assertTrue(self.orc_p.conditions.filter(name__iexact='grappled').exists())
        self.assertEqual(self.orc_p.speed, 0)

    def test_moving_while_grappling_halves_speed_and_drags_target(self):
        """Grappler moving halves speed and drags the victim along."""
        # Setup grapple
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.save()

        # Speed should be halved (30 -> 15)
        self.assertEqual(self.fighter_p.speed, 15)

        # Move fighter from (10, 10) to (10, 15)
        view = CombatSessionViewSet.as_view({'post': 'move'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.fighter_p.id,
            'target_x': 10,
            'target_y': 15
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        # 5e Rule: Grappled victim dragged along does not provoke/make Opportunity Attack
        self.assertEqual(len(response.data.get('opportunity_attacks', [])), 0)

        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertEqual((self.fighter_p.position_x, self.fighter_p.position_y), (10, 15))
        # Orc was dragged adjacent to (10, 15)
        dist = max(abs(self.orc_p.position_x - 10), abs(self.orc_p.position_y - 15))
        self.assertLessEqual(dist, 5)

    def test_grappled_participant_cannot_move(self):
        """Grappled victim cannot move (speed 0)."""
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'move'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.orc_p.id,
            'target_x': 20,
            'target_y': 10
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('grappled', response.data['error'].lower())

    def test_escape_grapple(self):
        """Victim successfully escapes grapple via contested check."""
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'escape_grapple'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/escape_grapple/', {
            'participant_id': self.orc_p.id
        })
        # Mock roll_d20: defender rolls 19, grappler rolls 5
        with patch('combat.tactical_endpoints.roll_d20', side_effect=[(19, '19'), (5, '5')]):
            response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertFalse(self.fighter_p.is_grappling)
        self.assertIsNone(self.orc_p.grappled_by_id)
        self.assertFalse(self.orc_p.conditions.filter(name__iexact='grappled').exists())

    def test_release_grapple(self):
        """Grappler cleanly releases target as free action."""
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'release_grapple'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/release_grapple/', {
            'grappler_id': self.fighter_p.id
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertFalse(self.fighter_p.is_grappling)
        self.assertIsNone(self.orc_p.grappled_by)

    def test_grappler_feat_advantage_on_attacks(self):
        """Attacker with Grappler feat gains advantage on attack rolls against grappled target."""
        CharacterFeat.objects.create(character=self.fighter_char, feat=self.grappler_feat, level_taken=4)
        self.assertTrue(self.fighter_p.has_grappler_feat())

        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'attack'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.fighter_p.id,
            'target_id': self.orc_p.id
        })
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        # Should have advantage in action description or breakdown
        last_action = self.session.actions.latest('id')
        self.assertTrue(last_action.is_advantage or 'Advantage' in last_action.description or 'Grappler' in last_action.description)

    def test_grappler_feat_pin_restrains_both(self):
        """Grappler pin action restrains both the grappler and defender on success."""
        CharacterFeat.objects.create(character=self.fighter_char, feat=self.grappler_feat, level_taken=4)

        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'pin'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/pin/', {
            'grappler_id': self.fighter_p.id
        })
        # Mock roll_d20: grappler rolls 18, defender rolls 8
        with patch('combat.tactical_endpoints.roll_d20', side_effect=[(18, '18'), (8, '8')]):
            response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertTrue(self.fighter_p.conditions.filter(name__iexact='restrained').exists())
        self.assertTrue(self.orc_p.conditions.filter(name__iexact='restrained').exists())

        # Releasing grapple clears the pin restraint
        self.fighter_p.release_grapple()
        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertFalse(self.fighter_p.conditions.filter(name__iexact='restrained').exists())
        self.assertFalse(self.orc_p.conditions.filter(name__iexact='restrained').exists())

    def test_grapple_breaks_when_grappler_falls_unconscious(self):
        """Grapple breaks automatically when grappler drops to 0 HP."""
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.save()

        # Deal lethal damage to fighter
        self.fighter_p.take_damage(50)
        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertFalse(self.fighter_p.is_grappling)
        self.assertIsNone(self.orc_p.grappled_by)
        self.assertFalse(self.orc_p.conditions.filter(name__iexact='grappled').exists())

    def test_ai_cannot_move_while_grappled(self):
        """5e Rules: Grappled creatures have speed 0 and AI cannot move."""
        from combat.combat_ai import _execute_ai_movement
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.position_x = 5
        self.orc_p.position_y = 0
        self.orc_p.save()

        # Attempt AI movement
        result = _execute_ai_movement(self.session, self.orc_p, self.fighter_p)
        self.assertIsNone(result)
        self.orc_p.refresh_from_db()
        self.assertEqual(self.orc_p.position_x, 5)
        self.assertEqual(self.orc_p.position_y, 0)

    def test_ai_attempts_escape_grapple_when_pinned_or_caster(self):
        """Grappled AI uses its action to attempt an escape check."""
        from combat.combat_ai import _attempt_ai_escape_grapple
        self.fighter_p.is_grappling = True
        self.fighter_p.save()
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.save()

        with patch('combat.combat_ai.roll_d20', side_effect=[(18, False), (2, False)]):
            action_entry, success = _attempt_ai_escape_grapple(self.session, self.orc_p, self.fighter_p)
            self.assertTrue(success)
            self.orc_p.refresh_from_db()
            self.fighter_p.refresh_from_db()
            self.assertIsNone(self.orc_p.grappled_by)
            self.assertTrue(self.orc_p.action_used)

    def test_pin_fails_if_target_out_of_reach(self):
        """Pin attempt fails and clears grapple if target is separated beyond melee reach."""
        self.fighter_p.feature_uses = {'has_grappler': True}
        self.fighter_p.is_grappling = True
        self.fighter_p.position_x = 0
        self.fighter_p.position_y = 0
        self.fighter_p.save()

        # Place target 25 ft away
        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.position_x = 25
        self.orc_p.position_y = 0
        self.orc_p.save()

        view = CombatSessionViewSet.as_view({'post': 'pin'})
        request = self.factory.post(f'/api/combat/sessions/{self.session.id}/pin/', {
            'grappler_id': self.fighter_p.id,
            'target_id': self.orc_p.id,
        }, format='json')
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("out of melee reach", response.data['error'])

        # Grapple should be cleared
        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()
        self.assertFalse(self.fighter_p.is_grappling)
        self.assertIsNone(self.orc_p.grappled_by)

    def test_clean_grapple_states_breaks_grapple_beyond_reach(self):
        """CombatSession.clean_grapple_states automatically ends grapples where distance > reach."""
        self.fighter_p.is_grappling = True
        self.fighter_p.position_x = 0
        self.fighter_p.position_y = 0
        self.fighter_p.save()

        self.orc_p.grappled_by = self.fighter_p
        self.orc_p.conditions.add(self.grappled_cond)
        self.orc_p.position_x = 20
        self.orc_p.position_y = 20
        self.orc_p.save()

        self.session.clean_grapple_states()
        self.fighter_p.refresh_from_db()
        self.orc_p.refresh_from_db()

        self.assertFalse(self.fighter_p.is_grappling)
        self.assertIsNone(self.orc_p.grappled_by)
        self.assertFalse(self.orc_p.conditions.filter(name__iexact='grappled').exists())

