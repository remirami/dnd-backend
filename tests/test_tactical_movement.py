"""
Tests for 5E Tactical Movement, Grid Positioning & Opportunity Attacks (Pillar 6)
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatAction, CombatParticipant, CombatSession
from encounters.models import Encounter


class TacticalMovementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testtactician', password='password123')
        self.client.force_authenticate(user=self.user)

        self.encounter = Encounter.objects.create(name='Grid Arena')
        self.session = CombatSession.objects.create(
            encounter=self.encounter,
            status='active',
            current_round=1,
            current_turn_index=0
        )

        fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter')
        human_race, _ = CharacterRace.objects.get_or_create(name='human')
        self.character = Character.objects.create(
            name='Sir Vance',
            user=self.user,
            character_class=fighter_class,
            race=human_race,
            level=3
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=14,
            speed=30,
            hit_points=28,
            max_hit_points=28,
            armor_class=18
        )

        # Hero at (10, 10)
        self.hero = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=28,
            max_hp=28,
            armor_class=18,
            initiative=18,
            position_x=10,
            position_y=10
        )

        # Goblin enemy at (15, 10) - exactly 5 ft adjacent
        self.goblin = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Raider',
            current_hp=12,
            max_hp=12,
            armor_class=13,
            initiative=12,
            position_x=15,
            position_y=10
        )

    def test_move_within_speed(self):
        """Moving within speed budget successfully updates coordinates and deducts movement."""
        # Hero moves from (10, 10) to (10, 25) -> 15 ft straight down
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 10,
            'target_y': 25
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.hero.refresh_from_db()
        self.assertEqual(self.hero.position_x, 10)
        self.assertEqual(self.hero.position_y, 25)
        self.assertEqual(self.hero.movement_used, 15)
        self.assertEqual(self.hero.movement_remaining, 15)

    def test_move_exceeds_speed_rejected(self):
        """Moving beyond speed budget returns 400 error."""
        # 35 ft exceeds 30 ft speed
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 45,
            'target_y': 10
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough movement", response.data['error'])

    def test_move_to_occupied_square_rejected(self):
        """Moving onto an active combatant's tile is rejected."""
        # Goblin is at (15, 10)
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 15,
            'target_y': 10
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already occupied", response.data['error'])

    def test_move_triggers_opportunity_attack(self):
        """Leaving an adjacent enemy's reach without Disengage triggers an opportunity attack reaction."""
        # Hero is adjacent to goblin at (15, 10). Hero moves away to (0, 10)
        self.assertFalse(self.goblin.reaction_used)
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 0,
            'target_y': 10
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.goblin.refresh_from_db()
        self.assertTrue(self.goblin.reaction_used)
        self.assertGreater(len(response.data.get('opportunity_attacks', [])), 0)
        
        # Verify opportunity attack recorded in combat action log
        oa_action = CombatAction.objects.filter(
            combat_session=self.session,
            action_type='opportunity_attack'
        ).first()
        self.assertIsNotNone(oa_action)
        self.assertEqual(oa_action.actor, self.goblin)

    def test_disengage_prevents_opportunity_attack(self):
        """Using Disengage action prevents enemies from making opportunity attacks when leaving reach."""
        # 1. Hero takes Disengage action
        disengage_resp = self.client.post(f'/api/combat/sessions/{self.session.id}/disengage/', {
            'participant_id': self.hero.id
        })
        self.assertEqual(disengage_resp.status_code, status.HTTP_200_OK)
        self.hero.refresh_from_db()
        self.assertTrue(self.hero.action_used)

        # 2. Hero moves away from goblin to (0, 10)
        move_resp = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 0,
            'target_y': 10
        })
        self.assertEqual(move_resp.status_code, status.HTTP_200_OK)
        
        self.goblin.refresh_from_db()
        # Goblin did NOT use reaction
        self.assertFalse(self.goblin.reaction_used)
        self.assertEqual(len(move_resp.data.get('opportunity_attacks', [])), 0)

    def test_dash_action_extends_movement_budget(self):
        """Taking Dash action doubles the turn's movement pool (30 ft -> 60 ft)."""
        dash_resp = self.client.post(f'/api/combat/sessions/{self.session.id}/dash/', {
            'participant_id': self.hero.id
        })
        self.assertEqual(dash_resp.status_code, status.HTTP_200_OK)
        self.hero.refresh_from_db()
        self.assertEqual(self.hero.movement_remaining, 60)

        # Now moving 45 ft is valid
        move_resp = self.client.post(f'/api/combat/sessions/{self.session.id}/move/', {
            'participant_id': self.hero.id,
            'target_x': 10,
            'target_y': 35
        })
        self.assertEqual(move_resp.status_code, status.HTTP_200_OK)
        self.hero.refresh_from_db()
        self.assertEqual(self.hero.movement_used, 25)
        self.assertEqual(self.hero.movement_remaining, 35)

    def test_melee_attack_out_of_reach_rejected(self):
        """Melee weapon attacks against targets beyond 5 ft reach are rejected with 400 error."""
        distant_target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Distant Ogre',
            current_hp=50,
            max_hp=50,
            armor_class=12,
            position_x=30,
            position_y=30
        )
        # Hero is at (10, 10), Ogre is at (30, 30) -> 20 ft away
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.hero.id,
            'target_id': distant_target.id,
            'attack_name': 'Longsword'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("out of melee reach", response.data['error'])

    def test_initialize_grid_positions_on_start(self):
        """Starting a combat session deploys heroes to Left (X=10) and enemies to Right (X=35)."""
        new_session = CombatSession.objects.create(
            encounter=self.encounter,
            status='preparing'
        )
        h1 = CombatParticipant.objects.create(
            combat_session=new_session,
            participant_type='character',
            character=self.character,
            current_hp=20,
            max_hp=20,
            armor_class=14,
            position_x=0,
            position_y=0
        )
        e1 = CombatParticipant.objects.create(
            combat_session=new_session,
            participant_type='enemy',
            name='Orc',
            current_hp=15,
            max_hp=15,
            armor_class=13,
            position_x=0,
            position_y=0
        )
        start_resp = self.client.post(f'/api/combat/sessions/{new_session.id}/start/')
        self.assertEqual(start_resp.status_code, status.HTTP_200_OK)

        h1.refresh_from_db()
        e1.refresh_from_db()
        # Party deploys to unaligned 20ft cluster on Left flank (X in 5..15 ft, Y in 5..30 ft)
        self.assertIn(h1.position_x, [5, 10, 15])
        self.assertTrue(5 <= h1.position_y <= 35)
        # Enemies deploy to unaligned 20ft cluster on Right flank (X in 30..45 ft, Y in 5..30 ft)
        self.assertIn(e1.position_x, [30, 35, 40, 45])
        self.assertTrue(5 <= e1.position_y <= 35)

    def test_ranged_weapon_attack_at_distance_succeeds(self):
        """Attacking with a Longbow from 20 ft away must succeed and not be blocked by melee reach."""
        distant_target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Gremlin Bilge',
            current_hp=20,
            max_hp=20,
            armor_class=12,
            position_x=30,
            position_y=10  # Hero is at (10, 10) -> 20 ft away
        )
        response = self.client.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.hero.id,
            'target_id': distant_target.id,
            'attack_name': 'Longbow',
            'is_ranged': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('hit', response.data)
        # Ranged attacks must NOT receive Flanking advantage even if allies are engaged
        self.assertNotIn('Flanking', response.data.get('advantage_reasons', []))

    def test_tactical_flanking_only_applies_when_both_attacker_and_ally_adjacent(self):
        """Tactical flanking requires both the attacker and an ally to be adjacent (<= 5 ft) to target."""
        target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Target Goblin',
            current_hp=30,
            max_hp=30,
            armor_class=10,
            position_x=15,
            position_y=10  # Hero at (10, 10) -> 5 ft away (melee reach)
        )
        # Ally 1 is far away at (30, 30) -> 15-20 ft away from target
        ally = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=25,
            max_hp=25,
            armor_class=15,
            position_x=30,
            position_y=30
        )
        # Attack with ally far away -> NO Flanking
        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.hero.id,
            'target_id': target.id,
            'attack_name': 'Longsword',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn('Flanking', resp.data.get('advantage_reasons', []))

        # Reset attacks
        self.hero.attacks_remaining = 1
        self.hero.save()

        # Move ally into melee reach: (15, 15) -> adjacent to target (15, 10)
        ally.position_x = 15
        ally.position_y = 15
        ally.save()

        # Attack with ally adjacent -> FLANKING APPLIES!
        resp2 = self.client.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.hero.id,
            'target_id': target.id,
            'attack_name': 'Longsword',
        })
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertIn('Flanking', resp2.data.get('advantage_reasons', []))

    def test_ai_moves_towards_target_on_turn(self):
        """When an enemy is 20 ft away, resolve_enemy_turn moves the enemy within reach before attacking."""
        from combat.combat_ai import resolve_enemy_turn
        # Hero at (10, 10), Enemy at (30, 10) -> 20 ft away
        enemy = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Raider',
            current_hp=10,
            max_hp=10,
            armor_class=12,
            position_x=30,
            position_y=10,
        )
        actions = resolve_enemy_turn(self.session, enemy)
        enemy.refresh_from_db()

        # Enemy should have moved from (30, 10) closer to hero at (10, 10)
        self.assertLess(enemy.position_x, 30)
        # Enemy should now be within melee reach (5 ft)
        dist = max(abs(enemy.position_x - self.hero.position_x), abs(enemy.position_y - self.hero.position_y))
        self.assertLessEqual(dist, 5)
        # Actions should contain the move action
        move_actions = [a for a in actions if a.get('type') == 'move']
        self.assertTrue(len(move_actions) >= 1)

