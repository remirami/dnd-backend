from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from characters.models import Character, CharacterBackground, CharacterClass, CharacterRace
from characters.services.random_character import (
    create_random_character,
    generate_random_character_data,
    generate_random_name,
    roll_4d6_drop_lowest,
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

    def test_api_confirm_preview_creates_exact_character(self):
        """Previewing then confirming with character_data creates that exact character"""
        preview_res = self.client.post('/api/characters/generate_random/', {'preview': True}, format='json')
        self.assertEqual(preview_res.status_code, status.HTTP_200_OK)
        preview_data = preview_res.json()
        preview_name = preview_data['name']
        preview_str = preview_data['strength']
        self.assertIn('gold_pieces', preview_data)
        self.assertGreaterEqual(preview_data['gold_pieces'], 5)
        self.assertLessEqual(preview_data['gold_pieces'], 35)

        confirm_res = self.client.post(
            '/api/characters/generate_random/',
            {'preview': False, 'character_data': preview_data},
            format='json'
        )
        self.assertEqual(confirm_res.status_code, status.HTTP_201_CREATED)
        created_data = confirm_res.json()
        self.assertEqual(created_data['name'], preview_name)
        char = Character.objects.get(pk=created_data['id'])
        self.assertEqual(char.name, preview_name)
        self.assertEqual(char.stats.strength, preview_str)
        self.assertEqual(char.gold_pieces, preview_data['gold_pieces'])
        self.assertEqual(char.stats.armor_class, preview_data['armor_class'])

    def test_fighter_starting_armor_and_ac(self):
        """Fighters start with Chain Mail or Leather Armor and calculate AC realistically"""
        char = create_random_character(self.user, ruleset_version='2014', character_class_id=self.fighter_cls.id)
        armor_items = char.character_items.filter(item__category__name='Armor')
        self.assertTrue(armor_items.exists(), "Fighter should receive armor or shield")
        self.assertGreaterEqual(char.stats.armor_class, 11)

    def test_paladin_starting_armor_and_ac(self):
        """Paladins start with Chain Mail and have AC >= 16"""
        paladin_cls, _ = CharacterClass.objects.get_or_create(
            name='paladin',
            defaults={'hit_dice': 'd10', 'primary_ability': 'STR', 'source_ruleset': '2014'}
        )
        char = create_random_character(self.user, ruleset_version='2014', character_class_id=paladin_cls.id)
        has_chain_mail = char.character_items.filter(item__name='Chain Mail').exists()
        self.assertTrue(has_chain_mail, "Paladin must start with Chain Mail")
        self.assertGreaterEqual(char.stats.armor_class, 16)

    def test_barbarian_smart_hybrid_ac(self):
        """Barbarians receive either Scale Mail or Unarmored gear and calculate optimal AC"""
        barb_cls, _ = CharacterClass.objects.get_or_create(
            name='barbarian',
            defaults={'hit_dice': 'd12', 'primary_ability': 'STR', 'source_ruleset': '2014'}
        )
        char = create_random_character(self.user, ruleset_version='2014', character_class_id=barb_cls.id)
        dex_mod = (char.stats.dexterity - 10) // 2
        con_mod = (char.stats.constitution - 10) // 2
        unarmored_ac = 10 + dex_mod + con_mod
        # AC must be at least their Unarmored Defense (or higher if Scale Mail was better)
        self.assertGreaterEqual(char.stats.armor_class, unarmored_ac)

    def test_barbarian_duplicate_item_consolidation_and_preview_fields(self):
        """Verify duplicate starting items (e.g. Javelins) consolidate without UniqueConstraint error, and preview returns equipment/defense metadata"""
        barb_cls, _ = CharacterClass.objects.get_or_create(
            name='barbarian',
            defaults={'hit_dice': 'd12', 'primary_ability': 'STR', 'source_ruleset': '2014'}
        )
        Item.objects.get_or_create(name='Javelin', defaults={'category_id': self.sword.category_id, 'weight': 2.0, 'value': 1})
        preview = generate_random_character_data(ruleset_version='2014', character_class_id=barb_cls.id)
        self.assertIn('equipment_list', preview)
        self.assertIn('defense_summary', preview)
        self.assertIn('has_scale_mail', preview)

        # Force Choice 4 to Unarmored Warrior (which awards 2 extra Javelins alongside default 4 Javelins)
        preview['equipment_selections']['4'] = '(b) Unarmored Warrior (Two Extra Javelins)'

        char = create_random_character(self.user, ruleset_version='2014', character_data=preview)
        self.assertIsNotNone(char)
        javelin_ci = char.character_items.filter(item__name='Javelin')
        self.assertEqual(javelin_ci.count(), 1, "Duplicate Javelins should consolidate into a single CharacterItem row")
        self.assertGreaterEqual(javelin_ci.first().quantity, 6)

