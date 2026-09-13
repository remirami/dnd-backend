from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterBackground
from characters.services.random_character import (
    roll_4d6_drop_lowest,
    generate_random_name,
    generate_random_character_data,
    create_random_character
)
from items.models import Item, ItemCategory
from spells.models import Spell


class RandomCharacterGenerationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dnd_player', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        # Setup standard classes
        self.fighter_cls, _ = CharacterClass.objects.get_or_create(
            name='fighter',
            defaults={'hit_dice': 'd10', 'primary_ability': 'STR', 'source_ruleset': '2014'}
        )
        self.wizard_cls, _ = CharacterClass.objects.get_or_create(
            name='wizard',
            defaults={'hit_dice': 'd6', 'primary_ability': 'INT', 'source_ruleset': '2014'}
        )

        # Setup race
        self.dwarf_race, _ = CharacterRace.objects.get_or_create(
            name='dwarf',
            defaults={
                'size': 'M',
                'speed': 25,
                'ability_score_increases': 'CON+2',
                'source_ruleset': '2014'
            }
        )

        # Setup background
        self.soldier_bg, _ = CharacterBackground.objects.get_or_create(
            name='soldier',
            defaults={'skill_proficiencies': 'Athletics,Intimidation', 'source_ruleset': '2014'}
        )

        # Setup items
        gear_cat, _ = ItemCategory.objects.get_or_create(name='Weapon')
        self.sword, _ = Item.objects.get_or_create(
            name='Longsword',
            defaults={'category': gear_cat, 'weight': 3, 'value': 15, 'rarity': 'common'}
        )

        # Setup spells for wizard
        self.firebolt, _ = Spell.objects.get_or_create(
            name='Fire Bolt Sample',
            defaults={
                'slug': 'fire-bolt-sample',
                'level': 0,
                'school': 'evocation',
                'casting_time': '1 action',
                'range': '120 feet',
                'components': 'V, S',
                'duration': 'Instantaneous',
                'description': 'Hurls a mote of fire'
            }
        )
        self.firebolt.classes.add(self.wizard_cls)

        self.magic_missile, _ = Spell.objects.get_or_create(
            name='Magic Missile Sample',
            defaults={
                'slug': 'magic-missile-sample',
                'level': 1,
                'school': 'evocation',
                'casting_time': '1 action',
                'range': '120 feet',
                'components': 'V, S',
                'duration': 'Instantaneous',
                'description': 'Darts of magical force'
            }
        )
        self.magic_missile.classes.add(self.wizard_cls)

    def test_roll_4d6_drop_lowest(self):
        """Dice roller should produce numbers strictly within 3 to 18"""
        for _ in range(50):
            score = roll_4d6_drop_lowest()
            self.assertGreaterEqual(score, 3)
            self.assertLessEqual(score, 18)

    def test_generate_random_name(self):
        """Generates a non-empty name with first and last name"""
        name = generate_random_name('dwarf')
        self.assertTrue(len(name.split()) >= 2)

    def test_generate_random_character_data_preview(self):
        """Preview mode generates complete valid dictionary without touching database"""
        initial_char_count = Character.objects.count()
        data = generate_random_character_data(ruleset_version='2014')

        self.assertEqual(Character.objects.count(), initial_char_count)
        self.assertIn('name', data)
        self.assertIn('race_id', data)
        self.assertIn('character_class_id', data)
        self.assertIn('strength', data)
        self.assertIn('dexterity', data)
        self.assertIn('constitution', data)
        self.assertIn('intelligence', data)
        self.assertIn('wisdom', data)
        self.assertIn('charisma', data)
        self.assertIn('equipment_selections', data)

    def test_create_random_character_service(self):
        """create_random_character creates a fully fleshed out Character instance"""
        char = create_random_character(self.user, ruleset_version='2014')
        self.assertIsNotNone(char.id)
        self.assertEqual(char.user, self.user)
        self.assertEqual(char.level, 1)
        self.assertTrue(hasattr(char, 'stats'))
        self.assertGreater(char.stats.hit_points, 0)
        self.assertGreater(char.stats.armor_class, 0)
        self.assertGreater(char.gold_pieces, 0)

    def test_api_generate_random_preview(self):
        """POST /api/characters/generate_random/ with preview=True returns 200 without DB write"""
        initial_count = Character.objects.count()
        response = self.client.post('/api/characters/generate_random/', {'preview': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Character.objects.count(), initial_count)
        data = response.json()
        self.assertIn('name', data)
        self.assertIn('character_class_name', data)
        self.assertIn('strength', data)

    def test_api_generate_random_create(self):
        """POST /api/characters/generate_random/ creates character and returns 201"""
        initial_count = Character.objects.count()
        response = self.client.post('/api/characters/generate_random/', {'preview': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Character.objects.count(), initial_count + 1)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertEqual(data['level'], 1)

    def test_wizard_random_generation_has_spells(self):
        """Random Wizard has cantrips and level 1 spells properly assigned"""
        response = self.client.post(
            '/api/characters/generate_random/',
            {'preview': False, 'character_class_id': self.wizard_cls.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        char_id = response.json()['id']
        char = Character.objects.get(pk=char_id)
        self.assertEqual(char.character_class.name, 'wizard')
        # Check that spells were created
        self.assertTrue(char.spells.filter(level=0).exists())
        self.assertTrue(char.spells.filter(level=1).exists())
