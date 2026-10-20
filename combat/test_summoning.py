"""
Tests for 5e Summoning & Persistent Minion / Token Spells Engine
Covers:
- Spiritual Weapon (2nd level Evocation, bonus action attack, force damage)
- Flaming Sphere (2nd level Conjuration, concentration, ram DEX save)
- Animate Dead (3rd level Necromancy, Skeleton/Zombie minion)
- Find Familiar (1st level Conjuration, Owl Help action)
- Concentration loss dismisses concentration summons but preserves non-concentration summons
- Spell objects excluded from standalone initiative turns
"""

from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from bestiary.models import Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterSpell, CharacterStats
from combat.models import CombatAction, CombatParticipant, CombatSession
from combat.summoning import is_summoning_spell, spawn_summon, command_summon_action
from combat.views.session_views import CombatSessionViewSet
from spells.models import Spell


class SummoningEngineTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='summon_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Classes & Race
        self.cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric', defaults={'hit_dice': 'd8', 'primary_ability': 'WIS'})
        self.wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard', defaults={'hit_dice': 'd6', 'primary_ability': 'INT'})
        self.race, _ = CharacterRace.objects.get_or_create(name='human', defaults={'size': 'M', 'speed': 30})

        # Hero 1: Beverly (Cleric)
        self.cleric = Character.objects.create(
            name='Beverly', user=self.user, level=5, character_class=self.cleric_class, race=self.race
        )
        self.cleric_stats = CharacterStats.objects.create(
            character=self.cleric, hit_points=35, max_hit_points=35, armor_class=16,
            strength=10, dexterity=12, constitution=14, wisdom=16, charisma=12,
            spell_slots={'1': 4, '2': 3, '3': 2}, expended_spell_slots={'1': 0, '2': 0, '3': 0}
        )
        self.cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.cleric,
            current_hp=35,
            max_hp=35,
            armor_class=16,
            initiative=20,
            position_x=10,
            position_y=10,
        )

        # Hero 2: Morpheus (Wizard)
        self.wizard = Character.objects.create(
            name='Morpheus', user=self.user, level=5, character_class=self.wizard_class, race=self.race
        )
        self.wizard_stats = CharacterStats.objects.create(
            character=self.wizard, hit_points=25, max_hit_points=25, armor_class=12,
            strength=8, dexterity=14, constitution=12, wisdom=10, charisma=10, intelligence=16,
            spell_slots={'1': 4, '2': 3, '3': 2}, expended_spell_slots={'1': 0, '2': 0, '3': 0}
        )
        self.wizard_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.wizard,
            current_hp=25,
            max_hp=25,
            armor_class=12,
            initiative=15,
            position_x=15,
            position_y=10,
        )

        # Enemy: Ogre
        self.ogre = Enemy.objects.create(name='Ogre', hp=50, ac=11, challenge_rating='2')
        EnemyStats.objects.create(
            enemy=self.ogre, strength=19, dexterity=8, constitution=16, intelligence=5, wisdom=7, charisma=7,
            hit_points=50, armor_class=11
        )
        self.ogre_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Ogre',
            current_hp=50,
            max_hp=50,
            armor_class=11,
            initiative=8,
            position_x=20,
            position_y=10,
        )

        # Register Spells in library
        Spell.objects.get_or_create(
            name='Spiritual Weapon',
            defaults={
                'slug': 'spiritual-weapon', 'level': 2, 'range': '60 feet', 'casting_time': '1 bonus action',
                'school': 'evocation', 'duration': '1 minute', 'description': 'Spectral weapon attacks target.'
            }
        )
        Spell.objects.get_or_create(
            name='Flaming Sphere',
            defaults={
                'slug': 'flaming-sphere', 'level': 2, 'range': '60 feet', 'casting_time': '1 action',
                'school': 'conjuration', 'duration': 'Concentration, up to 1 minute', 'concentration': True,
                'description': 'A 5-ft sphere of fire that rams targets.'
            }
        )
        Spell.objects.get_or_create(
            name='Animate Dead',
            defaults={
                'slug': 'animate-dead', 'level': 3, 'range': '10 feet', 'casting_time': '1 action',
                'school': 'necromancy', 'duration': 'Instantaneous', 'description': 'Creates an undead servant.'
            }
        )
        Spell.objects.get_or_create(
            name='Find Familiar',
            defaults={
                'slug': 'find-familiar', 'level': 1, 'range': '10 feet', 'casting_time': '1 hour',
                'school': 'conjuration', 'duration': 'Instantaneous', 'description': 'Gains the service of a familiar.'
            }
        )

    def test_is_summoning_spell_helper(self):
        """Helper correctly identifies all registered 5e summoning & token spells."""
        self.assertTrue(is_summoning_spell('Spiritual Weapon'))
        self.assertTrue(is_summoning_spell('Flaming Sphere'))
        self.assertTrue(is_summoning_spell('animate dead'))
        self.assertTrue(is_summoning_spell('Find Familiar'))
        self.assertTrue(is_summoning_spell('Conjure Elemental'))
        self.assertFalse(is_summoning_spell('Fireball'))
        self.assertFalse(is_summoning_spell('Cure Wounds'))

    def test_spiritual_weapon_cast_spawns_token_and_attacks_target(self):
        """Casting Spiritual Weapon creates a spell object participant and attacks primary target."""
        CharacterSpell.objects.create(character=self.cleric, name='Spiritual Weapon', level=2, is_prepared=True)

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.ogre_p.id,
                'spell_name': 'Spiritual Weapon',
                'spell_level': 2,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)

        # Check summon spawned
        summons = self.session.participants.filter(name__icontains='Spiritual Weapon')
        self.assertEqual(summons.count(), 1)
        weapon = summons.first()

        self.assertTrue(weapon.is_summon())
        self.assertTrue(weapon.is_spell_object())
        self.assertEqual(weapon.get_summoner().id, self.cleric_p.id)
        self.cleric_p.refresh_from_db()
        self.assertTrue(self.cleric_p.bonus_action_used)

        # Non-concentration spell
        self.assertFalse(weapon.feature_uses.get('requires_concentration'))
        self.assertFalse(self.cleric_p.is_concentrating)

    def test_command_spiritual_weapon_move_and_attack(self):
        """Caster can command Spiritual Weapon to move up to 20 ft and attack with a bonus action."""
        weapon = spawn_summon(self.session, self.cleric_p, 'Spiritual Weapon', position_x=10, position_y=10)
        self.assertEqual(weapon.position_x, 10)
        self.assertEqual(weapon.position_y, 10)

        # Ogre is at (20, 10) - 10 ft away. Weapon moves to (15, 10) and attacks.
        self.cleric_p.bonus_action_used = False
        self.cleric_p.save()

        # Step 1: Move command
        view = CombatSessionViewSet.as_view({'post': 'command_summon'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.cleric_p.id,
                'summon_id': weapon.id,
                'command_type': 'move',
                'destination_x': 15,
                'destination_y': 10,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        weapon.refresh_from_db()
        self.assertEqual(weapon.position_x, 15)
        self.assertEqual(weapon.position_y, 10)

        # Step 2: Attack command with DM override or fresh turn
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.cleric_p.id,
                'summon_id': weapon.id,
                'command_type': 'attack',
                'target_id': self.ogre_p.id,
                'manual_roll': 18,
                'dm_override': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data['command_result']['hit'])
        self.ogre_p.refresh_from_db()
        self.assertLess(self.ogre_p.current_hp, 50)

    def test_flaming_sphere_concentration_and_ram(self):
        """Flaming sphere concentration tracking and ram DEX save damage."""
        sphere = spawn_summon(self.session, self.wizard_p, 'Flaming Sphere', position_x=15, position_y=10)
        self.wizard_p.refresh_from_db()
        self.assertTrue(self.wizard_p.is_concentrating)
        self.assertEqual(self.wizard_p.concentration_spell, 'Flaming Sphere')

        # Advance turn to Morpheus
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'command_summon'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.wizard_p.id,
                'summon_id': sphere.id,
                'command_type': 'ram',
                'target_id': self.ogre_p.id,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.ogre_p.refresh_from_db()
        self.assertLess(self.ogre_p.current_hp, 50)

    def test_concentration_break_dismisses_flaming_sphere(self):
        """Breaking concentration removes Flaming Sphere from the active participants."""
        sphere = spawn_summon(self.session, self.wizard_p, 'Flaming Sphere', position_x=15, position_y=10)
        self.wizard_p.refresh_from_db()
        self.assertTrue(sphere.is_active)
        self.assertTrue(self.wizard_p.is_concentrating)

        # Wizard takes massive damage and falls unconscious -> concentration drops
        self.wizard_p.take_damage(30)
        self.wizard_p.refresh_from_db()
        self.assertFalse(self.wizard_p.is_concentrating)

        sphere.refresh_from_db()
        self.assertFalse(sphere.is_active)

    def test_animate_dead_spawns_skeleton_minion(self):
        """Animate Dead spawns a controllable Skeleton minion with weapon attacks."""
        minion = spawn_summon(self.session, self.wizard_p, 'Animate Dead', position_x=12, position_y=10, creature_choice='skeleton')
        self.assertTrue(minion.is_summon())
        self.assertFalse(minion.is_spell_object())
        self.assertEqual(minion.current_hp, 13)
        self.assertEqual(minion.armor_class, 13)

        # Minion attacks Ogre
        view = CombatSessionViewSet.as_view({'post': 'command_summon'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.wizard_p.id,
                'summon_id': minion.id,
                'command_type': 'attack',
                'target_id': self.ogre_p.id,
                'attack_index': 1,  # Shortbow (range 80)
                'manual_roll': 19,
                'dm_override': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data['command_result']['hit'])
        self.ogre_p.refresh_from_db()
        self.assertLess(self.ogre_p.current_hp, 50)

    def test_spell_object_skipped_by_initiative_next_turn(self):
        """Spell objects like Spiritual Weapon do not receive standalone turns in next_turn()."""
        weapon = spawn_summon(self.session, self.cleric_p, 'Spiritual Weapon', position_x=10, position_y=10)

        # Beverly is index 0. Advance turn.
        self.session.current_turn_index = 0
        self.session.save()
        next_p = self.session.next_turn()

        # Turn must advance to Morpheus (index 1), NEVER to the Spiritual Weapon!
        self.assertIsNotNone(next_p)
        self.assertEqual(next_p.id, self.wizard_p.id)
        self.assertNotEqual(next_p.id, weapon.id)

    def test_find_familiar_help_action(self):
        """Find Familiar can take the Help action to distract an enemy."""
        familiar = spawn_summon(self.session, self.wizard_p, 'Find Familiar', creature_choice='owl')
        self.assertEqual(familiar.current_hp, 1)

        view = CombatSessionViewSet.as_view({'post': 'command_summon'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.wizard_p.id,
                'summon_id': familiar.id,
                'command_type': 'help',
                'target_id': self.ogre_p.id,
                'dm_override': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.ogre_p.refresh_from_db()
        self.assertTrue(self.ogre_p.feature_uses.get('distracted_by_familiar'))

    def test_dismiss_summon(self):
        """Caster can dismiss their summon, freeing concentration and removing it from combat."""
        sphere = spawn_summon(self.session, self.wizard_p, 'Flaming Sphere')
        self.wizard_p.refresh_from_db()
        self.assertTrue(self.wizard_p.is_concentrating)

        view = CombatSessionViewSet.as_view({'post': 'command_summon'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/command_summon/',
            {
                'caster_id': self.wizard_p.id,
                'summon_id': sphere.id,
                'command_type': 'dismiss',
                'dm_override': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)

        sphere.refresh_from_db()
        self.assertFalse(sphere.is_active)
        self.wizard_p.refresh_from_db()
        self.assertFalse(self.wizard_p.is_concentrating)
