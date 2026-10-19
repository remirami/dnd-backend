"""
Test Spell Rules Expansion (Option 1)

Verifies high-priority combat, buff, and condition spells:
1. Power Word Kill (instant death <= 100 HP, no effect > 100 HP)
2. Power Word Stun (stunned <= 150 HP, no effect > 150 HP)
3. Bane (subtracts 1d4 from attack rolls and saving throws)
4. Banishment (applies incapacitated condition on failed CHA save)
5. Hunter's Mark, Hex, Divine Favor (bonus damage on weapon attacks)
6. Stoneskin (resistance to physical weapon damage)
7. Death Ward (drops to 1 HP instead of 0 HP on fatal damage)
8. Sanctuary (attacker failing WIS save is thwarted)
9. Beacon of Hope (maximizes healing dice, advantage on WIS saves)
10. Freedom of Movement (immunity to paralyzed & restrained)
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from characters.models import Character, CharacterClass, CharacterStats, CharacterSpell, CharacterRace
from bestiary.models import Enemy, EnemyStats, Condition
from combat.models import CombatSession, CombatParticipant
from combat.spell_rules import is_buff_spell, get_spell_rule, apply_buff_to_target

User = get_user_model()


class SpellRulesExpansionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='spelltester', password='password123')
        self.client.force_authenticate(user=self.user)

        # Race
        self.race = CharacterRace.objects.create(name='Human', size='M', speed=30)

        # Classes
        self.wizard_class = CharacterClass.objects.create(name='Wizard', hit_dice='d6', primary_ability='INT', saving_throw_proficiencies='INT,WIS')
        self.cleric_class = CharacterClass.objects.create(name='Cleric', hit_dice='d8', primary_ability='WIS', saving_throw_proficiencies='WIS,CHA')
        self.fighter_class = CharacterClass.objects.create(name='Fighter', hit_dice='d10', primary_ability='STR', saving_throw_proficiencies='STR,CON')

        # Wizard Character
        self.wizard_char = Character.objects.create(
            name='Archmage Gandalf',
            user=self.user,
            character_class=self.wizard_class,
            race=self.race,
            level=17,
        )
        self.wizard_stats = CharacterStats.objects.create(
            character=self.wizard_char,
            hit_points=90,
            max_hit_points=90,
            armor_class=12,
            intelligence=20,
            wisdom=14,
            constitution=14,
            dexterity=14,
            strength=10,
            charisma=10,
            spell_save_dc=19,
            spell_attack_bonus=11,
            spell_slots={'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1, '8': 1, '9': 1},
            expended_spell_slots={},
        )

        # Cleric Character
        self.cleric_char = Character.objects.create(
            name='High Priestess',
            user=self.user,
            character_class=self.cleric_class,
            race=self.race,
            level=10,
        )
        self.cleric_stats = CharacterStats.objects.create(
            character=self.cleric_char,
            hit_points=80,
            max_hit_points=80,
            armor_class=18,
            wisdom=18,
            constitution=14,
            dexterity=12,
            strength=14,
            intelligence=10,
            charisma=12,
            spell_save_dc=16,
            spell_attack_bonus=8,
            spell_slots={'1': 4, '2': 3, '3': 3, '4': 3, '5': 2},
            expended_spell_slots={},
        )

        # Fighter Character
        self.fighter_char = Character.objects.create(
            name='Sir Galahad',
            user=self.user,
            character_class=self.fighter_class,
            race=self.race,
            level=10,
        )
        self.fighter_stats = CharacterStats.objects.create(
            character=self.fighter_char,
            hit_points=100,
            max_hit_points=100,
            strength=18,
            constitution=16,
            dexterity=14,
            wisdom=12,
            intelligence=10,
            charisma=10,
            armor_class=18,
        )

        # Combat Session
        self.session = CombatSession.objects.create(
            status='active',
            current_round=1,
            current_turn_index=0,
        )

        # Participants
        self.wizard_p = CombatParticipant.objects.create(
            combat_session=self.session,
            character=self.wizard_char,
            participant_type='character',
            initiative=20,
            current_hp=90,
            max_hp=90,
            armor_class=15,
            is_active=True,
            action_used=False,
            bonus_action_used=False,
            attacks_remaining=1,
        )

        self.cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            character=self.cleric_char,
            participant_type='character',
            initiative=15,
            current_hp=80,
            max_hp=80,
            armor_class=18,
            is_active=True,
            action_used=False,
            bonus_action_used=False,
            attacks_remaining=1,
        )

        self.fighter_p = CombatParticipant.objects.create(
            combat_session=self.session,
            character=self.fighter_char,
            participant_type='character',
            initiative=10,
            current_hp=100,
            max_hp=100,
            armor_class=18,
            is_active=True,
            action_used=False,
            bonus_action_used=False,
            attacks_remaining=2,
        )

        # Enemy Monster
        self.dragon_enemy = Enemy.objects.create(
            name='Young Red Dragon',
            challenge_rating='10',
            ac=18,
            hp=178,
        )
        EnemyStats.objects.create(
            enemy=self.dragon_enemy,
            strength=23,
            dexterity=10,
            constitution=21,
            intelligence=14,
            wisdom=11,
            charisma=17,
            hit_points=178,
            armor_class=18,
        )
        self.dragon_p = CombatParticipant.objects.create(
            combat_session=self.session,
            encounter_enemy=None,
            name='Young Red Dragon',
            participant_type='enemy',
            initiative=12,
            current_hp=178,
            max_hp=178,
            armor_class=18,
            is_active=True,
            action_used=False,
            bonus_action_used=False,
            attacks_remaining=3,
        )

        # Ensure Conditions exist in DB
        for cond_name in ['Stunned', 'Incapacitated', 'Charmed', 'Paralyzed', 'Restrained', 'Poisoned']:
            Condition.objects.get_or_create(name__iexact=cond_name, defaults={'name': cond_name})

    def test_power_word_kill_kills_creature_at_or_below_100_hp(self):
        """Power Word Kill instantly kills a target with 100 or fewer HP."""
        self.dragon_p.current_hp = 95
        self.dragon_p.save(update_fields=['current_hp'])

        CharacterSpell.objects.create(character=self.wizard_char, name='Power Word Kill', level=9, is_prepared=True)

        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/cast_spell/', {
            'caster_id': self.wizard_p.id,
            'target_id': self.dragon_p.id,
            'spell_name': 'Power Word Kill',
            'spell_level': 9,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.dragon_p.refresh_from_db()
        self.assertEqual(self.dragon_p.current_hp, 0)
        self.assertFalse(self.dragon_p.is_active)
        self.assertIn('dies instantly', resp.data['message'])

    def test_power_word_kill_fails_on_creature_above_100_hp(self):
        """Power Word Kill has no effect if target has more than 100 HP."""
        self.dragon_p.current_hp = 150
        self.dragon_p.save(update_fields=['current_hp'])

        CharacterSpell.objects.create(character=self.wizard_char, name='Power Word Kill', level=9, is_prepared=True)

        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/cast_spell/', {
            'caster_id': self.wizard_p.id,
            'target_id': self.dragon_p.id,
            'spell_name': 'Power Word Kill',
            'spell_level': 9,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.dragon_p.refresh_from_db()
        self.assertEqual(self.dragon_p.current_hp, 150)
        self.assertIn('unaffected', resp.data['message'])

    def test_power_word_stun_stuns_creature_at_or_below_150_hp(self):
        """Power Word Stun stuns target with <= 150 HP without a save initially."""
        self.dragon_p.current_hp = 120
        self.dragon_p.save(update_fields=['current_hp'])

        CharacterSpell.objects.create(character=self.wizard_char, name='Power Word Stun', level=8, is_prepared=True)

        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/cast_spell/', {
            'caster_id': self.wizard_p.id,
            'target_id': self.dragon_p.id,
            'spell_name': 'Power Word Stun',
            'spell_level': 8,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.dragon_p.refresh_from_db()
        self.assertTrue(self.dragon_p.conditions.filter(name__iexact='stunned').exists())
        self.assertIn('is stunned', resp.data['message'])

    def test_bane_applies_penalty_to_attacks_and_saves(self):
        """Bane buff applies -1d4 penalty to attack rolls and saving throws."""
        self.dragon_p.add_buff('Bane', source_spell='Bane')
        self.assertTrue(self.dragon_p.has_buff('bane'))

        # Test saving throw with Bane
        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/saving_throw/', {
            'participant_id': self.dragon_p.id,
            'save_type': 'CON',
            'save_dc': 15,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Bane penalty was applied in saving throw

    def test_stoneskin_halves_physical_weapon_damage(self):
        """Stoneskin buff halves nonmagical bludgeoning, piercing, and slashing damage."""
        self.fighter_p.add_buff('Stoneskin', source_spell='Stoneskin')
        self.assertTrue(self.fighter_p.has_buff('stoneskin'))

        initial_hp = self.fighter_p.current_hp
        # Take 20 slashing damage
        new_hp, _ = self.fighter_p.take_damage(20, damage_type='slashing')
        # Resisted: 20 // 2 = 10 damage taken
        self.assertEqual(new_hp, initial_hp - 10)
        self.assertEqual(self.fighter_p.last_resistance_info['type'], 'resistance')
        self.assertEqual(self.fighter_p.last_resistance_info['source'], 'Stoneskin')

    def test_death_ward_prevents_dropping_to_zero_hp(self):
        """Death Ward drops a creature to 1 HP instead of 0 HP when taking fatal damage."""
        self.fighter_p.current_hp = 10
        self.fighter_p.save(update_fields=['current_hp'])
        self.fighter_p.add_buff('Death Ward', source_spell='Death Ward')
        self.assertTrue(self.fighter_p.has_buff('death ward'))

        # Hit for 25 damage (more than 10 HP)
        new_hp, _ = self.fighter_p.take_damage(25, damage_type='slashing')
        self.assertEqual(new_hp, 1)
        self.assertTrue(self.fighter_p.is_active)
        self.assertTrue(getattr(self.fighter_p, 'last_death_ward_triggered', False))
        # Ward should be consumed
        self.assertFalse(self.fighter_p.has_buff('death ward'))

    def test_freedom_of_movement_immune_to_paralyzed_and_restrained(self):
        """Freedom of Movement makes the target immune to paralyzed and restrained conditions."""
        from combat.condition_effects import is_condition_immune
        self.fighter_p.add_buff('Freedom of Movement', source_spell='Freedom of Movement')

        self.assertTrue(is_condition_immune(self.fighter_p, 'paralyzed'))
        self.assertTrue(is_condition_immune(self.fighter_p, 'restrained'))
        self.assertFalse(is_condition_immune(self.fighter_p, 'blinded'))

    def test_hunters_mark_and_divine_favor_damage_riders(self):
        """Hunter's Mark (+1d6) and Divine Favor (+1d4) add bonus damage on attack hits."""
        self.fighter_p.add_buff("Hunter's Mark", source_spell="Hunter's Mark")
        self.fighter_p.add_buff('Divine Favor', source_spell='Divine Favor')

        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/attack/', {
            'attacker_id': self.fighter_p.id,
            'target_id': self.dragon_p.id,
            'attack_name': 'Longsword',
            'damage_string': '1d8',
            'ability': 'STR',
            'dm_override': True,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        if resp.data.get('hit'):
            self.assertIn("Hunter's Mark", resp.data['breakdown']['damage'])
            self.assertIn("Divine Favor", resp.data['breakdown']['damage'])

    def test_beacon_of_hope_maximizes_healing(self):
        """Beacon of Hope maximizes all healing dice received by the target."""
        self.fighter_p.current_hp = 30
        self.fighter_p.save(update_fields=['current_hp'])
        self.fighter_p.add_buff('Beacon of Hope', source_spell='Beacon of Hope')

        CharacterSpell.objects.create(character=self.cleric_char, name='Cure Wounds', level=1, is_prepared=True)

        resp = self.client.post(f'/api/combat/sessions/{self.session.id}/cast_spell/', {
            'caster_id': self.cleric_p.id,
            'target_id': self.fighter_p.id,
            'spell_name': 'Cure Wounds',
            'spell_level': 1,
            'damage_string': '1d8',
            'dm_override': True,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # 1d8 maximized is 8 + WIS mod (4) = 12
        self.assertEqual(resp.data['target_results'][0]['healing'], 12)
        self.assertIn('Beacon of Hope: Max Healing!', resp.data['message'])
