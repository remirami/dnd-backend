from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from bestiary.models import Enemy
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from gauntlet.models import GauntletRun, GauntletSnapshotHero
from gauntlet.services.wave_generator import WaveGenerator


class GauntletModelAndServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hero_tester', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.cclass = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR', saving_throw_proficiencies='STR,CON')
        self.race = CharacterRace.objects.create(name='human')
        self.character = Character.objects.create(
            user=self.user,
            name='Arthur Pendragon',
            character_class=self.cclass,
            race=self.race,
            level=3
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=12,
            charisma=10,
            hit_points=28,
            max_hit_points=28,
            armor_class=16,
            spell_slots={'1': 2}
        )

        # Create a few test enemies
        self.goblin = Enemy.objects.create(
            name='Goblin',
            hp=7,
            ac=15,
            challenge_rating='1/4',
            creature_type='humanoid'
        )
        self.ogre = Enemy.objects.create(
            name='Ogre',
            hp=59,
            ac=11,
            challenge_rating='2',
            creature_type='giant'
        )

    def test_snapshot_hero_isolation(self):
        """Verify that Gauntlet runs operate on snapshots and never harm the original character."""
        run = GauntletRun.objects.create(user=self.user, name="Trial of Iron", theme="colosseum")
        snapshot = run.add_hero(self.character)

        self.assertEqual(snapshot.name, 'Arthur Pendragon')
        self.assertEqual(snapshot.current_hp, 28)
        self.assertEqual(snapshot.max_hp, 28)
        self.assertEqual(snapshot.level, 3)
        self.assertEqual(snapshot.hit_die_type, 'd10')

        # Mutate snapshot (e.g. hero takes damage in Gauntlet)
        snapshot.current_hp = 5
        snapshot.save()

        # Original character sheet must remain pristine!
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.hit_points, 28)

    def test_wave_generator_spawns_combat(self):
        """Verify that WaveGenerator builds an active CombatSession with participants."""
        run = GauntletRun.objects.create(user=self.user, name="Colosseum Trial", theme="colosseum")
        run.add_hero(self.character)
        combat_session = run.start_run()

        self.assertIsNotNone(combat_session)
        self.assertEqual(run.status, 'active')
        self.assertEqual(run.current_wave, 1)

        # Verify participants in session
        heroes_in_combat = combat_session.participants.filter(participant_type='character')
        enemies_in_combat = combat_session.participants.filter(participant_type='enemy')

        self.assertEqual(heroes_in_combat.count(), 1)
        self.assertTrue(enemies_in_combat.count() >= 1)

    def test_respite_choices(self):
        """Test applying respite bonuses (Breather and Tactical Boon)."""
        run = GauntletRun.objects.create(user=self.user, name="Respite Test", theme="colosseum", status='preparing')
        hero = run.add_hero(self.character)
        hero.current_hp = 10  # wounded
        hero.save()
        run.status = 'respite'
        run.save()

        # 1. Breather (healing)
        res = run.apply_respite('breather')
        hero.refresh_from_db()
        self.assertGreater(hero.current_hp, 10)
        self.assertEqual(hero.hit_dice_remaining, hero.level - 1)

        # 2. Tactical Boon
        run.status = 'respite'
        res2 = run.apply_respite('tactical_boon', {'boon_kind': 'ac_boost'})
        run.refresh_from_db()
        self.assertEqual(len(run.active_boons), 1)
        self.assertEqual(run.active_boons[0]['type'], 'ac_boost')

    def test_api_create_and_sync_wave(self):
        """Test the REST API endpoints for starting a run and syncing wave completion."""
        response = self.client.post('/api/gauntlet/', {
            'name': 'API Gauntlet',
            'theme': 'crypt',
            'character_ids': [self.character.id]
        }, format='json')

        self.assertEqual(response.status_code, 201)
        run_data = response.json()
        run_id = run_data['id']
        session_id = run_data['current_combat_session_id']
        self.assertIsNotNone(session_id)

        # Mark all enemies as dead in the combat session
        session = CombatSession.objects.get(id=session_id)
        session.participants.filter(participant_type='enemy').update(current_hp=0)

        # Sync wave
        sync_resp = self.client.post(f'/api/gauntlet/{run_id}/sync_wave/')
        self.assertEqual(sync_resp.status_code, 200)
        self.assertEqual(sync_resp.json()['run_status'], 'respite')

        # Pick respite
        respite_resp = self.client.post(f'/api/gauntlet/{run_id}/respite/', {
            'choice_type': 'supply_drop'
        }, format='json')
        self.assertEqual(respite_resp.status_code, 200)

        # Advance to next wave
        next_resp = self.client.post(f'/api/gauntlet/{run_id}/next_wave/')
        self.assertEqual(next_resp.status_code, 200)
        self.assertEqual(next_resp.json()['current_wave'], 2)

        # Verify old session was cleaned up
        self.assertFalse(CombatSession.objects.filter(id=session_id).exists())

    def test_gauntlet_active_and_total_limits_with_auto_delete(self):
        """Verify Gauntlet creation obeys active limit (2) and total limit (10), and supports auto_delete_oldest."""
        # 1. Create 2 active combat sessions for the user
        s1 = CombatSession.objects.create(created_by=self.user, status='active', is_practice=True)
        CombatParticipant.objects.create(combat_session=s1, participant_type='character', current_hp=10, max_hp=10, armor_class=12, attacks_remaining=1)
        s2 = CombatSession.objects.create(created_by=self.user, status='active', is_practice=True)
        CombatParticipant.objects.create(combat_session=s2, participant_type='character', current_hp=10, max_hp=10, armor_class=12, attacks_remaining=1)

        # Attempt to create a Gauntlet run when 2 active combats exist -> should be rejected
        resp = self.client.post('/api/gauntlet/', {
            'name': 'Over Active Limit Gauntlet',
            'theme': 'colosseum',
            'character_ids': [self.character.id]
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get('code'), 'ACTIVE_LIMIT_REACHED')

        # Now pass auto_delete_oldest=True -> should delete s1 and succeed
        resp_ok = self.client.post('/api/gauntlet/', {
            'name': 'Allowed Active Gauntlet',
            'theme': 'colosseum',
            'character_ids': [self.character.id],
            'auto_delete_oldest': True
        }, format='json')
        self.assertEqual(resp_ok.status_code, 201)
        self.assertFalse(CombatSession.objects.filter(id=s1.id).exists())

        # 2. Test total limit (10)
        # End all active sessions so active limit isn't hit
        CombatSession.objects.filter(created_by=self.user).update(status='ended')

        # Create enough ended sessions to reach 10
        current_count = CombatSession.objects.filter(created_by=self.user).count()
        for _ in range(10 - current_count):
            CombatSession.objects.create(created_by=self.user, status='ended', is_practice=True)

        self.assertEqual(CombatSession.objects.filter(created_by=self.user).count(), 10)

        # Attempt to create Gauntlet when at total limit -> should be rejected
        resp_full = self.client.post('/api/gauntlet/', {
            'name': 'Over Total Limit Gauntlet',
            'theme': 'colosseum',
            'character_ids': [self.character.id]
        }, format='json')
        self.assertEqual(resp_full.status_code, 400)
        self.assertEqual(resp_full.json().get('code'), 'TOTAL_LIMIT_REACHED')

        # With auto_delete_oldest=True -> should prune oldest ended session and succeed
        resp_pruned = self.client.post('/api/gauntlet/', {
            'name': 'Pruned Gauntlet',
            'theme': 'colosseum',
            'character_ids': [self.character.id],
            'auto_delete_oldest': True
        }, format='json')
        self.assertEqual(resp_pruned.status_code, 201)
        self.assertLessEqual(CombatSession.objects.filter(created_by=self.user).count(), 10)
