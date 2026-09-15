from rest_framework import status
from rest_framework.test import APITestCase

from characters.models import CharacterClass
from spells.models import Spell


class StartingChoicesEndpointTests(APITestCase):
    def setUp(self):
        # Create test classes
        self.wizard_class, _ = CharacterClass.objects.get_or_create(
            name='wizard',
            defaults={'hit_dice': 'd6', 'primary_ability': 'INT'}
        )
        self.cleric_class, _ = CharacterClass.objects.get_or_create(
            name='cleric',
            defaults={'hit_dice': 'd8', 'primary_ability': 'WIS'}
        )
        self.fighter_class, _ = CharacterClass.objects.get_or_create(
            name='fighter',
            defaults={'hit_dice': 'd10', 'primary_ability': 'STR'}
        )

        # Create test spells
        self.cantrip = Spell.objects.create(
            name='Fire Bolt Test',
            slug='fire-bolt-test',
            level=0,
            school='evocation',
            casting_time='1 action',
            range='120 feet',
            components='V, S',
            duration='Instantaneous',
            description='Test cantrip'
        )
        self.cantrip.classes.add(self.wizard_class)

        self.spell1 = Spell.objects.create(
            name='Magic Missile Test',
            slug='magic-missile-test',
            level=1,
            school='evocation',
            casting_time='1 action',
            range='120 feet',
            components='V, S',
            duration='Instantaneous',
            description='Test 1st-level spell'
        )
        self.spell1.classes.add(self.wizard_class)

    def test_starting_spell_choices_anonymous_access(self):
        """starting_spell_choices should be accessible without authentication"""
        response = self.client.get('/api/characters/starting_spell_choices/?class_name=wizard')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['class_name'], 'wizard')
        self.assertEqual(data['cantrips_count'], 3)
        self.assertIn('available_cantrips', data)
        self.assertIn('available_spells', data)

    def test_starting_spell_choices_with_rule_version_suffix(self):
        """starting_spell_choices handles class names with ruleset suffix e.g. 'Wizard (2024)'"""
        response = self.client.get('/api/characters/starting_spell_choices/?class_name=Wizard%20(2024)')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['class_name'], 'Wizard')
        self.assertEqual(data['cantrips_count'], 3)

    def test_starting_spell_choices_non_caster(self):
        """Non-caster class returns informative message without error"""
        response = self.client.get('/api/characters/starting_spell_choices/?class_name=fighter')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('not a spellcasting class', data['message'])

    def test_starting_spell_choices_missing_param(self):
        """Missing class_name returns 400 bad request"""
        response = self.client.get('/api/characters/starting_spell_choices/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_starting_equipment_choices_anonymous_access(self):
        """starting_equipment_choices should be accessible without authentication"""
        response = self.client.get('/api/characters/starting_equipment_choices/?class_name=wizard')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('choices', data)
        self.assertIn('available_packs', data)

    def test_starting_equipment_choices_with_suffix(self):
        """starting_equipment_choices handles 'Fighter (2024)'"""
        response = self.client.get('/api/characters/starting_equipment_choices/?class_name=Fighter%20(2024)')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['class_name'], 'Fighter')
