from django.test import TestCase
from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterItem
from items.models import Armor, ItemCategory
from characters.inventory_management import recalculate_armor_class

class UnarmoredDefenseTests(TestCase):
    """Test Unarmored Defense calculation rules (Barbarian, Monk, Sorcerer)"""

    def setUp(self):
        self.user = User.objects.create_user(username='test_ac_user', password='testpass123')
        self.race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
        self.armor_category = ItemCategory.objects.create(name='Armor')
        
        # Barbarian Class
        self.barbarian_class = CharacterClass.objects.create(
            name='barbarian',
            hit_dice='d12',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        # Fighter Class
        self.fighter_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        # Monk Class
        self.monk_class = CharacterClass.objects.create(
            name='monk',
            hit_dice='d8',
            primary_ability='DEX,WIS',
            saving_throw_proficiencies='STR,DEX'
        )

        # Standard leather armor
        self.leather_armor_item = Armor.objects.create(
            name='Leather Armor',
            category=self.armor_category,
            armor_type='light',
            base_ac=11,
            min_strength=0,
            stealth_disadvantage=False,
            weight=10
        )
        
        # Standard shield
        self.shield_item = Armor.objects.create(
            name='Shield',
            category=self.armor_category,
            armor_type='shield',
            base_ac=2,
            min_strength=0,
            stealth_disadvantage=False,
            weight=6
        )

    def test_default_unarmored_ac(self):
        """A non-barbarian/monk gets 10 + DEX mod unarmored"""
        character = Character.objects.create(
            user=self.user, name='Fighter Char', level=1, character_class=self.fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=15, constitution=15, intelligence=10, wisdom=10, charisma=10,
            hit_points=10, max_hit_points=10, armor_class=10
        )
        
        ac = recalculate_armor_class(character)
        # Dex mod: +2. Con mod is +2 (but shouldn't apply). 10 + 2 = 12.
        self.assertEqual(ac, 12)

    def test_barbarian_unarmored_defense(self):
        """A barbarian gets 10 + DEX mod + CON mod unarmored"""
        character = Character.objects.create(
            user=self.user, name='Barbarian Char', level=1, character_class=self.barbarian_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=15, constitution=15, intelligence=10, wisdom=10, charisma=10,
            hit_points=12, max_hit_points=12, armor_class=10
        )
        
        ac = recalculate_armor_class(character)
        # Dex mod is +2, Con mod is +2. 10 + 2 + 2 = 14
        self.assertEqual(ac, 14)

    def test_barbarian_unarmored_defense_with_shield(self):
        """A barbarian gets 10 + DEX mod + CON mod + 2 from shield"""
        character = Character.objects.create(
            user=self.user, name='Barbarian Shield Char', level=1, character_class=self.barbarian_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=15, constitution=15, intelligence=10, wisdom=10, charisma=10,
            hit_points=12, max_hit_points=12, armor_class=10
        )
        
        # Equip shield
        CharacterItem.objects.create(
            character=character, item=self.shield_item, quantity=1, is_equipped=True, equipment_slot='off_hand'
        )
        
        ac = recalculate_armor_class(character)
        # 10 + 2 (Dex) + 2 (Con) + 2 (Shield) = 16
        self.assertEqual(ac, 16)

    def test_barbarian_armored_does_not_get_unarmored_defense(self):
        """A barbarian wearing armor gets normal armor class (no CON mod)"""
        character = Character.objects.create(
            user=self.user, name='Barbarian Armor Char', level=1, character_class=self.barbarian_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=15, constitution=15, intelligence=10, wisdom=10, charisma=10,
            hit_points=12, max_hit_points=12, armor_class=10
        )
        
        # Equip leather armor
        CharacterItem.objects.create(
            character=character, item=self.leather_armor_item, quantity=1, is_equipped=True, equipment_slot='armor'
        )
        
        ac = recalculate_armor_class(character)
        # Leather armor is 11 + Dex (2) = 13.
        self.assertEqual(ac, 13)

    def test_monk_unarmored_defense_no_shield(self):
        """A monk gets 10 + DEX mod + WIS mod unarmored with no shield"""
        character = Character.objects.create(
            user=self.user, name='Monk Char', level=1, character_class=self.monk_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=16, constitution=10, intelligence=10, wisdom=16, charisma=10,
            hit_points=8, max_hit_points=8, armor_class=10
        )
        
        ac = recalculate_armor_class(character)
        # Dex mod is +3, Wis mod is +3. 10 + 3 + 3 = 16.
        self.assertEqual(ac, 16)

    def test_monk_unarmored_defense_with_shield(self):
        """A monk wielding a shield loses Unarmored Defense and gets base (10 + DEX) + shield"""
        character = Character.objects.create(
            user=self.user, name='Monk Shield Char', level=1, character_class=self.monk_class, race=self.race
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=16, constitution=10, intelligence=10, wisdom=16, charisma=10,
            hit_points=8, max_hit_points=8, armor_class=10
        )
        
        # Equip shield
        CharacterItem.objects.create(
            character=character, item=self.shield_item, quantity=1, is_equipped=True, equipment_slot='off_hand'
        )
        
        ac = recalculate_armor_class(character)
        # Shield invalidates Monk's defense. AC reverts to 10 + DEX (3) + Shield (2) = 15.
        self.assertEqual(ac, 15)

    def test_draconic_resilience_unarmored(self):
        """A character with Draconic subclass gets 13 + DEX mod unarmored"""
        character = Character.objects.create(
            user=self.user, name='Draconic Sorcerer Char', level=1, character_class=self.fighter_class, race=self.race,
            subclass='Draconic Bloodline'
        )
        CharacterStats.objects.create(
            character=character, strength=10, dexterity=16, constitution=10, intelligence=10, wisdom=10, charisma=16,
            hit_points=10, max_hit_points=10, armor_class=10
        )
        
        ac = recalculate_armor_class(character)
        # 13 + Dex mod (+3) = 16.
        self.assertEqual(ac, 16)
