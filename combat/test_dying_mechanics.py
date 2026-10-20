from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet


class DyingMechanicsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='dying_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Conditions
        self.unconscious, _ = Condition.objects.get_or_create(name='unconscious')
        self.prone, _ = Condition.objects.get_or_create(name='prone')

        # Hero Class & Race
        self.fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter', defaults={'hit_dice': 'd10', 'primary_ability': 'STR'})
        self.cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric', defaults={'hit_dice': 'd8', 'primary_ability': 'WIS'})
        self.race, _ = CharacterRace.objects.get_or_create(name='human', defaults={'size': 'M', 'speed': 30})

        # Hero 1: Arthur (Fighter)
        self.hero = Character.objects.create(
            name='Arthur', user=self.user, level=3, character_class=self.fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.hero, hit_points=24, max_hit_points=24, armor_class=16, strength=16, dexterity=12, constitution=14, wisdom=10, charisma=8
        )
        self.hero_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.hero,
            current_hp=24,
            max_hp=24,
            armor_class=16,
            initiative=20,
            position_x=10,
            position_y=10,
        )

        # Hero 2: Beverly (Cleric / Healer)
        self.cleric = Character.objects.create(
            name='Beverly', user=self.user, level=3, character_class=self.cleric_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.cleric, hit_points=20, max_hit_points=20, armor_class=16, strength=10, dexterity=10, constitution=12, wisdom=16, charisma=12
        )
        self.cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.cleric,
            current_hp=20,
            max_hp=20,
            armor_class=16,
            initiative=15,
            position_x=15,
            position_y=10,
        )

        # Enemy: Goblin Raider
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
            initiative=10,
            position_x=10,
            position_y=15,
        )

    def test_dropping_to_zero_hp_applies_unconscious_and_prone(self):
        """When a character takes damage that reduces HP to 0, they fall unconscious and prone."""
        self.hero_p.take_damage(24)
        self.assertEqual(self.hero_p.current_hp, 0)
        self.assertTrue(self.hero_p.has_condition('unconscious'))
        self.assertTrue(self.hero_p.has_condition('prone'))
        self.assertFalse(self.hero_p.is_dead())
        self.assertTrue(self.hero_p.is_dying())

    def test_unconscious_pc_retains_turn_in_initiative(self):
        """Unconscious PCs at 0 HP are not skipped by next_turn, allowing them to roll death saves."""
        self.hero_p.take_damage(24)
        self.assertEqual(self.hero_p.current_hp, 0)
        # Arthur (initiative 20) is at index 0. Current turn index is 0.
        current = self.session.get_current_participant()
        self.assertEqual(current.id, self.hero_p.id)

        # Advance turn to Beverly
        self.session.next_turn()
        self.assertEqual(self.session.get_current_participant().id, self.cleric_p.id)

        # Advance to Goblin
        self.session.next_turn()
        self.assertEqual(self.session.get_current_participant().id, self.goblin_p.id)

        # Advance turn should wrap back to Arthur even at 0 HP
        self.session.next_turn()
        self.assertEqual(self.session.get_current_participant().id, self.hero_p.id)

    def test_dead_participant_is_skipped_in_initiative(self):
        """A dead participant (3 failures or massive damage) is skipped by next_turn()."""
        self.hero_p.take_damage(24)
        # Give 3 failures to make dead
        self.hero_p.death_save_failures = 3
        self.hero_p.save()
        self.assertTrue(self.hero_p.is_dead())

        # Start from Beverly
        self.session.current_turn_index = 1
        self.session.save()
        self.assertEqual(self.session.get_current_participant().id, self.cleric_p.id)

        # Advance to Goblin
        self.session.next_turn()
        self.assertEqual(self.session.get_current_participant().id, self.goblin_p.id)

        # Next turn should skip dead Arthur and go straight to Beverly
        self.session.next_turn()
        self.assertEqual(self.session.get_current_participant().id, self.cleric_p.id)

    def test_death_save_success_and_failure(self):
        """Standard death saving throw: roll >= 10 is success, < 10 is failure."""
        self.hero_p.take_damage(24)

        # Roll 12 -> 1 success
        success, is_stable, is_dead, msg, total, nat = self.hero_p.make_death_save(roll=12)
        self.assertTrue(success)
        self.assertFalse(is_stable)
        self.assertFalse(is_dead)
        self.assertEqual(self.hero_p.death_save_successes, 1)
        self.assertEqual(self.hero_p.death_save_failures, 0)

        # Roll 8 -> 1 failure
        success2, is_stable2, is_dead2, msg2, total2, nat2 = self.hero_p.make_death_save(roll=8)
        self.assertFalse(success2)
        self.assertEqual(self.hero_p.death_save_successes, 1)
        self.assertEqual(self.hero_p.death_save_failures, 1)

    def test_death_save_nat_20_revives_to_one_hp(self):
        """Natural 20 on death saving throw regains 1 HP and immediately wakes up."""
        self.hero_p.take_damage(24)
        self.hero_p.death_save_failures = 2
        self.hero_p.save()

        success, is_stable, is_dead, msg, total, nat = self.hero_p.make_death_save(roll=20)
        self.hero_p.refresh_from_db()

        self.assertTrue(success)
        self.assertEqual(self.hero_p.current_hp, 1)
        self.assertFalse(self.hero_p.has_condition('unconscious'))
        self.assertEqual(self.hero_p.death_save_successes, 0)
        self.assertEqual(self.hero_p.death_save_failures, 0)
        self.assertIn("Natural 20", msg)

    def test_death_save_nat_1_adds_two_failures(self):
        """Natural 1 on death saving throw counts as two failures."""
        self.hero_p.take_damage(24)

        success, is_stable, is_dead, msg, total, nat = self.hero_p.make_death_save(roll=1)
        self.assertFalse(success)
        self.assertEqual(self.hero_p.death_save_failures, 2)
        self.assertFalse(is_dead)

        # Another failed roll makes 3 failures -> Death
        success2, is_stable2, is_dead2, msg2, total2, nat2 = self.hero_p.make_death_save(roll=5)
        self.assertFalse(success2)
        self.assertEqual(self.hero_p.death_save_failures, 3)
        self.assertTrue(is_dead2)
        self.assertTrue(self.hero_p.is_dead())

    def test_three_death_save_successes_stabilizes(self):
        """Accumulating 3 successes stabilizes the creature at 0 HP."""
        self.hero_p.take_damage(24)
        self.hero_p.make_death_save(roll=10)
        self.hero_p.make_death_save(roll=14)
        success, is_stable, is_dead, msg, total, nat = self.hero_p.make_death_save(roll=18)

        self.assertTrue(is_stable)
        self.assertTrue(self.hero_p.is_stable())
        self.assertFalse(self.hero_p.is_dying())
        self.assertEqual(self.hero_p.current_hp, 0)

    def test_taking_damage_at_zero_hp(self):
        """Taking damage at 0 HP inflicts 1 failure (or 2 on critical hit) and breaks stabilization."""
        self.hero_p.take_damage(24)
        self.hero_p.stabilize()
        self.assertTrue(self.hero_p.is_stable())

        # Taking normal damage at 0 HP
        self.hero_p.take_damage(5, is_critical=False)
        self.hero_p.refresh_from_db()
        self.assertFalse(self.hero_p.is_stable())
        self.assertEqual(self.hero_p.death_save_failures, 1)

        # Taking critical hit at 0 HP inflicts 2 additional failures
        self.hero_p.take_damage(8, is_critical=True)
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.death_save_failures, 3)
        self.assertTrue(self.hero_p.is_dead())

    def test_damage_at_zero_hp_exceeding_max_hp_is_instant_death(self):
        """Damage at 0 HP >= max_hp causes instant death."""
        self.hero_p.take_damage(24)
        self.assertEqual(self.hero_p.current_hp, 0)
        self.assertFalse(self.hero_p.is_dead())

        # Max HP is 24. Damage of 24 causes instant death.
        self.hero_p.take_damage(24)
        self.hero_p.refresh_from_db()
        self.assertTrue(self.hero_p.is_dead())

    def test_massive_damage_instant_death_from_positive_hp(self):
        """Dropping to 0 HP with leftover damage >= max_hp causes instant death."""
        # Arthur has 24 HP, max HP 24. Hit for 48 damage (excess 24 >= 24).
        self.hero_p.take_damage(48)
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.current_hp, 0)
        self.assertTrue(self.hero_p.is_dead())

    def test_healing_at_zero_hp_clears_death_saves_and_unconscious(self):
        """Healing a dying character restores HP, removes unconscious condition, and clears death saves."""
        self.hero_p.take_damage(24)
        self.hero_p.make_death_save(roll=1) # 2 failures
        self.hero_p.refresh_from_db()
        self.assertEqual(self.hero_p.death_save_failures, 2)
        self.assertTrue(self.hero_p.has_condition('unconscious'))

        self.hero_p.heal(8)
        self.hero_p.refresh_from_db()

        self.assertEqual(self.hero_p.current_hp, 8)
        self.assertFalse(self.hero_p.has_condition('unconscious'))
        self.assertEqual(self.hero_p.death_save_failures, 0)
        self.assertEqual(self.hero_p.death_save_successes, 0)
        self.assertFalse(self.hero_p.is_stable())

    def test_stabilize_api_action_success_and_failure(self):
        """Using the stabilize action makes a DC 10 Wisdom (Medicine) check."""
        self.hero_p.take_damage(24)
        view = CombatSessionViewSet.as_view({'post': 'stabilize'})

        # Beverly is at (15, 10), Arthur is at (10, 10) - distance is 5 ft (within reach)
        # Advance turn to Beverly
        self.session.current_turn_index = 1
        self.session.save()

        # Beverly attempts stabilize with manual roll 5 (Wisdom mod is +3 -> total 8 < 10 -> fail)
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/stabilize/',
            {'healer_id': self.cleric_p.id, 'target_id': self.hero_p.id, 'manual_roll': 5},
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['success'])
        self.hero_p.refresh_from_db()
        self.assertFalse(self.hero_p.is_stable())

        # Reset Beverly's action and attempt with manual roll 10 (total 13 >= 10 -> success)
        self.cleric_p.action_used = False
        self.cleric_p.save()

        req2 = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/stabilize/',
            {'healer_id': self.cleric_p.id, 'target_id': self.hero_p.id, 'manual_roll': 10},
            format='json'
        )
        req2.user = self.user
        resp2 = view(req2, pk=self.session.id)
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(resp2.data['success'])
        self.hero_p.refresh_from_db()
        self.assertTrue(self.hero_p.is_stable())

    def test_stabilize_rejected_when_out_of_reach(self):
        """Stabilize action fails if the healer is not within reach (5 ft)."""
        self.hero_p.take_damage(24)
        # Move Beverly far away (30 ft)
        self.cleric_p.position_x = 40
        self.cleric_p.save()
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'stabilize'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/stabilize/',
            {'healer_id': self.cleric_p.id, 'target_id': self.hero_p.id},
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("within reach", resp.data['error'])

    def test_dead_participant_cannot_be_attacked(self):
        """Attacking a dead participant is rejected with HTTP 400."""
        self.hero_p.take_damage(24)
        self.hero_p.death_save_failures = 3
        self.hero_p.save()

        # Goblin's turn to attack Arthur
        self.session.current_turn_index = 2
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'attack'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/attack/',
            {'attacker_id': self.goblin_p.id, 'target_id': self.hero_p.id},
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("is dead and cannot be attacked", resp.data['error'])

    def test_spare_the_dying_cantrip_stabilizes(self):
        """Spare the Dying cantrip stabilizes a dying target at 0 HP."""
        self.hero_p.take_damage(24)
        self.hero_p.death_save_failures = 2
        self.hero_p.save()

        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.cleric, name='Spare the Dying', level=0, is_prepared=True)

        # Beverly's turn to cast Spare the Dying on Arthur
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'spell_name': 'Spare the Dying',
                'spell_level': 0,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.hero_p.refresh_from_db()
        self.assertTrue(self.hero_p.is_stable())
        self.assertEqual(self.hero_p.death_save_failures, 0)

    def test_stabilize_with_healers_kit_auto_succeeds_and_consumes_charge(self):
        """Using a Healer's Kit automatically stabilizes a dying participant without a Medicine roll."""
        from characters.models import CharacterItem
        from items.models import Item, ItemCategory

        cat, _ = ItemCategory.objects.get_or_create(name='Adventuring Gear')
        kit_item, _ = Item.objects.get_or_create(name="Healer's Kit", defaults={'category': cat, 'value': 5})
        ci = CharacterItem.objects.create(character=self.cleric, item=kit_item, quantity=10)

        self.hero_p.take_damage(24)
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'stabilize'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/stabilize/',
            {
                'healer_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'use_healers_kit': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data.get('used_healers_kit'))
        self.hero_p.refresh_from_db()
        self.assertTrue(self.hero_p.is_stable())

        ci.refresh_from_db()
        self.assertEqual(ci.quantity, 9)

    def test_stabilize_with_healers_kit_fails_if_no_kit(self):
        """Requesting use_healers_kit without one in inventory returns 400 error."""
        self.hero_p.take_damage(24)
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'stabilize'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/stabilize/',
            {
                'healer_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'use_healers_kit': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not have a Healer's Kit", resp.data['error'])

    def test_grave_cleric_spare_the_dying_range_30_ft(self):
        """Grave Domain Cleric has a 30 ft range for Spare the Dying (normally Touch / 5 ft)."""
        self.cleric.subclass = 'Grave Domain'
        self.cleric.save()

        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.cleric, name='Spare the Dying', level=0, is_prepared=True)

        self.hero_p.take_damage(24)
        # Move Beverly to 25 ft away: (35, 10) vs Arthur at (10, 10)
        self.cleric_p.position_x = 35
        self.cleric_p.position_y = 10
        self.cleric_p.save()

        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'spell_name': 'Spare the Dying',
                'spell_level': 0,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.hero_p.refresh_from_db()
        self.assertTrue(self.hero_p.is_stable())

    def test_grave_cleric_spare_the_dying_as_bonus_action(self):
        """Grave Domain Cleric can cast Spare the Dying as a bonus action when main action is used."""
        self.cleric.subclass = 'Grave Domain'
        self.cleric.save()

        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.cleric, name='Spare the Dying', level=0, is_prepared=True)

        self.hero_p.take_damage(24)
        self.cleric_p.action_used = True
        self.cleric_p.bonus_action_used = False
        self.cleric_p.save()

        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'spell_name': 'Spare the Dying',
                'spell_level': 0,
                'as_bonus_action': True,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.cleric_p.refresh_from_db()
        self.assertTrue(self.cleric_p.bonus_action_used)

    def test_grave_cleric_circle_of_mortality_max_healing_at_zero_hp(self):
        """Circle of Mortality maximizes all healing dice when healing a creature at 0 HP."""
        self.cleric.subclass = 'Grave Domain'
        self.cleric.save()

        from characters.models import CharacterSpell
        from spells.models import Spell
        Spell.objects.get_or_create(
            name='Cure Wounds',
            defaults={
                'slug': 'cure-wounds',
                'level': 1,
                'range': 'Touch',
                'casting_time': '1 action',
                'school': 'evocation',
                'duration': 'Instantaneous',
                'description': 'A creature you touch regains hit points equal to 1d8 + your spellcasting ability modifier.'
            }
        )
        CharacterSpell.objects.create(character=self.cleric, name='Cure Wounds', level=1, is_prepared=True)

        # Set cleric spell slots
        self.cleric.stats.spell_slots = {'1': 2}
        self.cleric.stats.expended_spell_slots = {'1': 0}
        self.cleric.stats.save()

        self.hero_p.take_damage(24)
        self.assertEqual(self.hero_p.current_hp, 0)

        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        req = self.factory.post(
            f'/api/combat-sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.hero_p.id,
                'spell_name': 'Cure Wounds',
                'spell_level': 1,
            },
            format='json'
        )
        req.user = self.user
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.hero_p.refresh_from_db()
        # 1d8 maxed = 8 + WIS mod (+3) = 11 HP restored!
        self.assertEqual(self.hero_p.current_hp, 11)
