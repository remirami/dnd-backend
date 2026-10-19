"""
Tests for Phase 8: Tactical Environmental Hazards & Reaction Interception Spells
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.
"""

from unittest import mock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession, EnvironmentalEffect, ParticipantPosition
from combat.views.session_views import CombatSessionViewSet
from combat.views.participant_views import CombatParticipantViewSet
from combat.environmental_effects import calculate_movement_cost, resolve_movement_hazards
from combat.reaction_spells import resolve_counterspell, resolve_dispel_magic


class EnvironmentalHazardsAndReactionsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='phase8_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        self.wizard_class, _ = CharacterClass.objects.get_or_create(name='wizard', hit_dice='d6', primary_ability='INT')
        self.cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric', hit_dice='d8', primary_ability='WIS')
        self.fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.race, _ = CharacterRace.objects.get_or_create(name='human', size='M', speed=30)

        self.paralyzed_cond, _ = Condition.objects.get_or_create(name='paralyzed')
        self.blinded_cond, _ = Condition.objects.get_or_create(name='blinded')

    def _create_participant(self, name, char_class, level=5, stats_dict=None, x=0, y=0, current_hp=40, max_hp=40, ptype='player'):
        char = Character.objects.create(
            user=self.user,
            name=name,
            level=level,
            character_class=char_class,
            race=self.race,
            ruleset_version='2024'
        )
        defaults = {
            'strength': 10,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 16,
            'wisdom': 12,
            'charisma': 10,
            'armor_class': 14,
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
            armor_class=14,
            initiative=15,
            is_active=True,
            position_x=x,
            position_y=y
        )
        ParticipantPosition.objects.create(
            participant=participant,
            x=x,
            y=y,
            z=0
        )
        return participant

    def test_spike_growth_movement_damage_and_difficult_terrain(self):
        """Spike Growth: 2d4 piercing per 5 ft moved, doubles movement cost as difficult terrain."""
        fighter = self._create_participant('Thorin', self.fighter_class, level=5, current_hp=50, max_hp=50, x=0, y=0)

        # Movement cost with spike_growth hazard
        effective_move, cost_mult = calculate_movement_cost(30, hazards=['spike_growth'])
        self.assertEqual(cost_mult, 2.0)
        self.assertEqual(effective_move, 15)

        # Resolve 15 ft movement through spike_growth (3 increments of 5 ft = 6d4 damage)
        with mock.patch('random.randint', return_value=3):  # each d4 = 3
            dmg, reports = resolve_movement_hazards(fighter, 15, ['spike_growth'])
            # 3 intervals of 5 ft -> 3 * (3 + 3) = 18 damage
            self.assertEqual(dmg, 18)
            self.assertEqual(fighter.current_hp, 32)
            self.assertTrue(any('Spike Growth' in r for r in reports))

    def test_wall_of_fire_entry_save_and_damage(self):
        """Wall of Fire: 5d8 fire damage, DEX save DC 15 for half."""
        rogue_participant = self._create_participant('Shadow', self.fighter_class, level=5, current_hp=40, max_hp=40, x=10, y=10)

        # Successful DEX save -> half damage
        with mock.patch('combat.utils.calculate_damage', return_value=(24, "5d8")):
            with mock.patch('combat.utils.roll_d20', return_value=(15, "15")):
                dmg, reports = resolve_movement_hazards(rogue_participant, 10, ['wall_of_fire'])
                # Dex mod = +2, roll 15 + 2 = 17 >= 15 -> Success -> 24 // 2 = 12
                self.assertEqual(dmg, 12)
                self.assertEqual(rogue_participant.current_hp, 28)
                self.assertTrue(any('succeeded DEX save' in r for r in reports))

        # Failed DEX save -> full damage
        with mock.patch('combat.utils.calculate_damage', return_value=(20, "5d8")):
            with mock.patch('combat.utils.roll_d20', return_value=(2, "2")):
                dmg, reports = resolve_movement_hazards(rogue_participant, 10, ['wall_of_fire'])
                # Roll 2 + 2 = 4 < 15 -> Failed -> 20 damage
                self.assertEqual(dmg, 20)
                self.assertEqual(rogue_participant.current_hp, 8)
                self.assertTrue(any('failed DEX save' in r for r in reports))

    def test_counterspell_range_and_reaction_rules(self):
        """Counterspell: 60 ft range limit and single-reaction consumption."""
        caster = self._create_participant('Gandalf', self.wizard_class, level=5, x=0, y=0)
        enemy = self._create_participant('Saruman', self.wizard_class, level=5, x=70, y=0, ptype='enemy')

        # 1. Out of range (> 60 ft)
        success, details = resolve_counterspell(caster, enemy, 'Fireball', target_spell_level=3, counter_slot_level=3)
        self.assertFalse(success)
        self.assertIn("out of range", details.get('error', ''))
        self.assertFalse(caster.reaction_used)

        # Move enemy within 50 ft
        enemy.position_x = 50
        enemy.save()
        pos = enemy.position
        pos.x = 50
        pos.save()

        # 2. In range & equal/higher slot level -> auto success
        success, details = resolve_counterspell(caster, enemy, 'Fireball', target_spell_level=3, counter_slot_level=3)
        self.assertTrue(success)
        self.assertTrue(details['success'])
        self.assertIn("automatically negating", details['message'])
        self.assertTrue(caster.reaction_used)

        # 3. Already used reaction -> blocked
        success_second, details_second = resolve_counterspell(caster, enemy, 'Lightning Bolt', target_spell_level=3, counter_slot_level=3)
        self.assertFalse(success_second)
        self.assertIn("already used their reaction", details_second.get('error', ''))

    def test_counterspell_ability_check_for_higher_level_spell(self):
        """Counterspell vs higher level spell requires ability check vs DC 10 + spell level."""
        caster = self._create_participant('Mage', self.wizard_class, level=5, stats_dict={'intelligence': 18}, x=0, y=0) # INT mod = +4
        enemy = self._create_participant('Lich', self.wizard_class, level=11, x=30, y=0, ptype='enemy')

        # Target casts 5th level spell, Counterspell cast at 3rd level -> DC = 10 + 5 = 15
        # Roll 10 + 4 (INT) = 14 < 15 -> Fails
        with mock.patch('combat.utils.roll_d20', return_value=(10, "10")):
            success, details = resolve_counterspell(caster, enemy, 'Cone of Cold', target_spell_level=5, counter_slot_level=3)
            self.assertFalse(success)
            self.assertEqual(details['dc'], 15)
            self.assertEqual(details['total'], 14)

        # Reset reaction
        caster.reaction_used = False
        caster.save()

        # Roll 11 + 4 = 15 >= 15 -> Succeeds
        with mock.patch('combat.utils.roll_d20', return_value=(11, "11")):
            success, details = resolve_counterspell(caster, enemy, 'Cone of Cold', target_spell_level=5, counter_slot_level=3)
            self.assertTrue(success)
            self.assertEqual(details['total'], 15)
            self.assertIn("Counterspell SUCCESS!", details['message'])

    def test_dispel_magic_buffs_concentration_and_conditions(self):
        """Dispel Magic: strips active buffs, breaks concentration, and cleanses associated conditions."""
        caster = self._create_participant('Cleric', self.cleric_class, level=5, stats_dict={'wisdom': 16}, x=0, y=0)
        target = self._create_participant('BuffedTarget', self.fighter_class, level=5, x=20, y=0, ptype='enemy')

        # Add active buffs: Bless (1st level), Haste (3rd level)
        target.add_buff('Bless', source_spell='Bless')
        target.add_buff('Haste', source_spell='Haste')
        target.is_concentrating = True
        target.concentration_spell = 'Hold Person'  # 2nd level spell
        target.save()

        # Add paralyzed condition from Hold Person
        target.conditions.add(self.paralyzed_cond)

        # Cast Dispel Magic at 3rd level -> auto-dispels spells of 3rd level and lower
        dispelled, details = resolve_dispel_magic(caster, target, dispel_slot_level=3)
        self.assertIn('Bless', dispelled)
        self.assertIn('Haste', dispelled)
        self.assertTrue(any('Hold Person' in s for s in dispelled))
        self.assertFalse(target.is_concentrating)
        self.assertFalse(target.conditions.filter(name='paralyzed').exists())
        self.assertEqual(len(target.get_active_buffs()), 0)

    def test_api_cast_spell_counterspell_interception(self):
        """Verify API /cast_spell/ correctly evaluates an incoming counterspell payload."""
        from characters.models import CharacterSpell
        caster = self._create_participant('WizardA', self.wizard_class, level=5, x=0, y=0)
        CharacterSpell.objects.create(character=caster.character, name='Fireball', level=3, is_prepared=True)
        stats = caster.character.stats
        stats.spell_slots = {'3': 2}
        stats.save()

        target = self._create_participant('TargetB', self.fighter_class, level=5, x=20, y=0, ptype='enemy')
        counterer = self._create_participant('EnemyWizard', self.wizard_class, level=5, x=30, y=0, ptype='enemy')

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        request = self.factory.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': caster.id,
                'target_ids': [target.id],
                'spell_name': 'Fireball',
                'spell_level': 3,
                'counterspell': {
                    'participant_id': counterer.id,
                    'slot_level': 3
                }
            },
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('countered'))
        self.assertIn('Counterspell', response.data.get('message', ''))
        # Counterer's reaction is consumed
        counterer.refresh_from_db()
        self.assertTrue(counterer.reaction_used)

    def test_api_participant_movement_through_spike_growth(self):
        """Verify participant /move/ endpoint calculates hazard difficult terrain and applies Spike Growth damage."""
        fighter = self._create_participant('GridRunner', self.fighter_class, level=5, current_hp=40, max_hp=40, x=0, y=0)

        # Place a Spike Growth hazard at (10, 0) with 20 ft radius
        EnvironmentalEffect.objects.create(
            combat_session=self.session,
            effect_type='hazard',
            hazard_type='spike_growth',
            hazard_area_x=10,
            hazard_area_y=0,
            hazard_area_radius=20,
            description="Spike Growth"
        )

        view = CombatParticipantViewSet.as_view({'post': 'move'})
        # Move 10 ft from (0, 0) to (10, 0)
        request = self.factory.post(
            f'/api/combat/participants/{fighter.id}/move/',
            {
                'distance': 10,
                'x': 10,
                'y': 0,
                'z': 0
            },
            format='json'
        )
        with mock.patch('random.randint', return_value=2):  # 2 increments of 5 ft -> 2x(2+2) = 8 damage
            response = view(request, pk=fighter.id)

        self.assertEqual(response.status_code, 200)
        fighter.refresh_from_db()
        self.assertGreater(response.data.get('hazard_damage', 0), 0)
        self.assertEqual(fighter.current_hp, 40 - response.data['hazard_damage'])
        self.assertEqual(fighter.position.x, 10)
        self.assertEqual(fighter.position.y, 0)
