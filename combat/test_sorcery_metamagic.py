"""
Automated Test Suite for Sorcery Points & Metamagic Mechanics (Phase 4).
Tests:
- Sorcery Points pool calculation & scaling (Level 2+)
- Font of Magic: Slot-to-Points conversion & Points-to-Slot creation
- Quickened Spell (action economy alteration to bonus action)
- Twinned Spell (single-target spell duplicate strike)
- Subtle Spell (verbal/somatic component bypass)
- Heightened Spell (disadvantage on saving throw)
- Empowered Spell (damage dice rerolls via CHA mod)
- Careful Spell (friendly auto-success on saves)
- Insufficient SP rejection & Non-Sorcerer isolation
"""
from unittest import mock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from bestiary.models import Enemy, EnemyStats
from combat.models import CombatSession, CombatParticipant
from combat.views import CombatSessionViewSet


class SorceryAndMetamagicTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='sorcerer_tester', password='password')

        # Classes
        self.sorcerer_class = CharacterClass.objects.create(name='sorcerer', hit_dice='d6', primary_ability='CHA')
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)

        # Combat Session
        self.session = CombatSession.objects.create(
            status='active',
            current_round=1,
            current_turn_index=0
        )

        # Level 5 Sorcerer (CHA 18 -> +4 mod, 5 max SP)
        self.sorcerer_char = Character.objects.create(
            name='Ignis',
            user=self.user,
            level=5,
            character_class=self.sorcerer_class,
            race=self.race,
            ruleset_version='2024'
        )
        self.sorcerer_stats = CharacterStats.objects.create(
            character=self.sorcerer_char,
            hit_points=35,
            max_hit_points=35,
            armor_class=13,
            strength=10,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=18,
            spell_save_dc=15,
            spell_attack_bonus=7,
            spell_slots={'1': 4, '2': 3, '3': 2},
            expended_spell_slots={}
        )
        # Learn Spells
        CharacterSpell.objects.create(character=self.sorcerer_char, name='Burning Hands', level=1)
        CharacterSpell.objects.create(character=self.sorcerer_char, name='Hold Person', level=2)
        CharacterSpell.objects.create(character=self.sorcerer_char, name='Fire Bolt', level=0)
        CharacterSpell.objects.create(character=self.sorcerer_char, name='Ray of Sickness', level=1)

        self.sorcerer_part = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.sorcerer_char,
            current_hp=35,
            max_hp=35,
            armor_class=13,
            initiative=100,
            position_x=0,
            position_y=0
        )

        # Level 5 Fighter (Non-Sorcerer)
        self.fighter_char = Character.objects.create(
            name='Valen',
            user=self.user,
            level=5,
            character_class=self.fighter_class,
            race=self.race,
            ruleset_version='2024'
        )
        CharacterStats.objects.create(
            character=self.fighter_char,
            hit_points=45,
            max_hit_points=45,
            armor_class=16,
            strength=18,
            dexterity=12,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10
        )
        self.fighter_part = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter_char,
            current_hp=45,
            max_hp=45,
            armor_class=16,
            initiative=90,
            position_x=5,
            position_y=0
        )

        # Enemy Targets
        self.enemy = Enemy.objects.create(name='Goblin Target', hp=50, ac=12, challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.enemy, strength=10, dexterity=14, constitution=10, intelligence=10, wisdom=10, charisma=10,
            hit_points=50, armor_class=12
        )
        self.target1 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Target 1',
            current_hp=50,
            max_hp=50,
            armor_class=12,
            initiative=10,
            position_x=15,
            position_y=0
        )
        self.target2 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Target 2',
            current_hp=50,
            max_hp=50,
            armor_class=12,
            initiative=9,
            position_x=15,
            position_y=5
        )

    def test_sorcery_points_pool_scaling(self):
        """Sorcery points equal Sorcerer level for level 2+; 0 for level 1 or non-sorcerers."""
        self.assertEqual(self.sorcerer_stats.sorcery_points_max, 5)
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 5)

        # Level 1 Sorcerer
        self.sorcerer_char.level = 1
        self.sorcerer_char.save()
        self.assertEqual(self.sorcerer_stats.sorcery_points_max, 0)

        # Fighter
        fighter_stats = self.fighter_char.stats
        self.assertEqual(fighter_stats.sorcery_points_max, 0)

    def test_font_of_magic_convert_slot_to_points(self):
        """Converting a level 2 spell slot grants 2 Sorcery Points (Bonus Action)."""
        view = CombatSessionViewSet.as_view({'post': 'font_of_magic'})
        # Start with 2 SP spent (3/5 remaining)
        self.sorcerer_stats.sorcery_points_used = 2
        self.sorcerer_stats.save()
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 3)

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/font_of_magic/',
            {
                'participant_id': self.sorcerer_part.id,
                'action_type': 'convert_slot',
                'slot_level': 2,
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        self.sorcerer_part.refresh_from_db()
        # Sorcery points restored to 5
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 5)
        # Level 2 slot marked expended
        self.assertEqual(self.sorcerer_stats.expended_spell_slots.get('2'), 1)
        # Bonus action consumed
        self.assertTrue(self.sorcerer_part.bonus_action_used)

    def test_font_of_magic_create_slot_from_points(self):
        """Creating a level 1 spell slot costs 2 Sorcery Points (Bonus Action)."""
        view = CombatSessionViewSet.as_view({'post': 'font_of_magic'})
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 5)

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/font_of_magic/',
            {
                'participant_id': self.sorcerer_part.id,
                'action_type': 'create_slot',
                'slot_level': 1,
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        # 2 SP spent -> 3 remaining
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 3)
        self.assertEqual(self.sorcerer_stats.created_spell_slots.get('1'), 1)

    def test_quickened_spell_casts_as_bonus_action(self):
        """Quickened Spell (2 SP): Casts a 1-action spell as a Bonus Action, leaving Action intact."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        self.sorcerer_part.action_used = False
        self.sorcerer_part.bonus_action_used = False
        self.sorcerer_part.save()

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.sorcerer_part.id,
                'target_id': self.target1.id,
                'spell_name': 'Burning Hands',
                'spell_level': 1,
                'save_type': 'DEX',
                'save_dc': 15,
                'damage_string': '3d6',
                'metamagic': 'quickened',
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        self.sorcerer_part.refresh_from_db()
        # 2 SP spent
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 3)
        # Cast as bonus action
        self.assertTrue(res.data['is_bonus_action'])
        self.assertTrue(self.sorcerer_part.bonus_action_used)
        # Main action is NOT consumed!
        self.assertFalse(self.sorcerer_part.action_used)

    def test_twinned_spell_hits_second_target(self):
        """Twinned Spell: Striking a primary target with Ray of Sickness also strikes a twinned target."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        hp1_before = self.target1.current_hp
        hp2_before = self.target2.current_hp

        # Fail save for both
        with mock.patch('combat.utils.roll_d20', return_value=(2, "2")):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/cast_spell/',
                {
                    'caster_id': self.sorcerer_part.id,
                    'target_id': self.target1.id,
                    'twinned_target_id': self.target2.id,
                    'spell_name': 'Ray of Sickness',
                    'spell_level': 1,
                    'save_type': 'CON',
                    'save_dc': 15,
                    'damage_string': '2d8',
                    'metamagic': 'twinned',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        self.target1.refresh_from_db()
        self.target2.refresh_from_db()
        # 1 SP spent for 1st level spell
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 4)
        # Both targets damaged
        self.assertLess(self.target1.current_hp, hp1_before)
        self.assertLess(self.target2.current_hp, hp2_before)
        self.assertEqual(len(res.data['target_results']), 2)

    def test_subtle_spell_casts_without_components(self):
        """Subtle Spell (1 SP): Casts without verbal or somatic components."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.sorcerer_part.id,
                'target_id': self.target1.id,
                'spell_name': 'Burning Hands',
                'spell_level': 1,
                'save_type': 'DEX',
                'save_dc': 15,
                'damage_string': '3d6',
                'metamagic': 'subtle',
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 4)
        self.assertIn("Subtle Spell", str(res.data.get('metamagic_annotation')))

    def test_heightened_spell_imposes_disadvantage(self):
        """Heightened Spell (2/3 SP): Target suffers Disadvantage on the saving throw."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})

        # Mock roll_d20 to spy on disadvantage parameter
        with mock.patch('combat.views.combat_action_views.roll_d20', return_value=(10, "10")) as mock_roll:
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/cast_spell/',
                {
                    'caster_id': self.sorcerer_part.id,
                    'target_id': self.target1.id,
                    'spell_name': 'Hold Person',
                    'spell_level': 2,
                    'save_type': 'WIS',
                    'save_dc': 15,
                    'metamagic': 'heightened',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)
            # Verify disadvantage was passed to roll_d20
            self.assertTrue(mock_roll.call_args[1].get('disadvantage'))

        self.sorcerer_stats.refresh_from_db()
        # In 2024 rules: Heightened costs 2 SP (or 3 in 2014)
        self.assertLess(self.sorcerer_stats.sorcery_points_current, 5)

    def test_empowered_spell_rerolls_damage(self):
        """Empowered Spell (1 SP): Rerolls lowest damage dice up to Charisma modifier."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.sorcerer_part.id,
                'target_id': self.target1.id,
                'spell_name': 'Burning Hands',
                'spell_level': 1,
                'save_type': 'DEX',
                'save_dc': 15,
                'damage_string': '3d6',
                'metamagic': 'empowered',
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        self.sorcerer_stats.refresh_from_db()
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 4)
        self.assertIn("Empowered Spell", str(res.data.get('empowered_annotation') or res.data.get('metamagic_annotation')))

    def test_careful_spell_auto_saves_allies(self):
        """Careful Spell (1 SP): Chosen friendly targets in area automatically succeed on the saving throw."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})

        # Include ally fighter in target_ids
        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.sorcerer_part.id,
                'target_ids': [self.target1.id, self.fighter_part.id],
                'careful_target_ids': [self.fighter_part.id],
                'spell_name': 'Burning Hands',
                'spell_level': 1,
                'save_type': 'DEX',
                'save_dc': 15,
                'damage_string': '3d6',
                'metamagic': 'careful',
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)

        # Fighter result has save_success == True
        results = {r['target_id']: r for r in res.data['target_results']}
        self.assertTrue(results[self.fighter_part.id]['save_success'])

    def test_insufficient_sorcery_points_rejected(self):
        """Attempting Metamagic when lacking sufficient Sorcery Points returns 400."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        # Drain all SP
        self.sorcerer_stats.sorcery_points_used = 5
        self.sorcerer_stats.save()
        self.assertEqual(self.sorcerer_stats.sorcery_points_current, 0)

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.sorcerer_part.id,
                'target_id': self.target1.id,
                'spell_name': 'Burning Hands',
                'spell_level': 1,
                'damage_string': '3d6',
                'metamagic': 'quickened',
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Not enough Sorcery Points", str(res.data.get('error', '')))

    def test_non_sorcerer_cannot_use_font_of_magic(self):
        """Fighter participant cannot use font_of_magic endpoint."""
        view = CombatSessionViewSet.as_view({'post': 'font_of_magic'})

        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/font_of_magic/',
            {
                'participant_id': self.fighter_part.id,
                'action_type': 'create_slot',
                'slot_level': 1,
                'dm_override': True
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 400)
        self.assertIn("does not have the Font of Magic feature", str(res.data.get('error', '')))
