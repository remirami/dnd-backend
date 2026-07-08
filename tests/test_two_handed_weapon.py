from django.test import TestCase
from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from items.models import Weapon, DamageType, ItemCategory
from characters.inventory_management import equip_item, can_equip_item

class TwoHandedWeaponEquipTests(TestCase):
    """Test two-handed weapon equipment rules and constraints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.char_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        self.race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
        self.character = Character.objects.create(
            user=self.user,
            name='Test Fighter',
            level=1,
            character_class=self.char_class,
            race=self.race
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=12,
            charisma=10,
            hit_points=12,
            max_hit_points=12,
            armor_class=16
        )
        
        self.weapon_category = ItemCategory.objects.create(name='Weapon')
        self.damage_type = DamageType.objects.create(name='Slashing')

        # Create a two-handed weapon
        self.greataxe = Weapon.objects.create(
            name='Greataxe',
            weapon_type='martial_melee',
            damage_dice='1d12',
            damage_type=self.damage_type,
            category=self.weapon_category,
            two_handed=True
        )

        # Create a one-handed weapon
        self.handaxe = Weapon.objects.create(
            name='Handaxe',
            weapon_type='simple_melee',
            damage_dice='1d6',
            damage_type=self.damage_type,
            category=self.weapon_category,
            two_handed=False
        )

    def test_cannot_equip_offhand_while_holding_2h(self):
        """Cannot equip a shield or another item in off_hand when holding a 2H weapon in main_hand"""
        # Equip Greataxe (2-handed) to main_hand
        equip_success, msg, _ = equip_item(self.character, self.greataxe, 'main_hand')
        self.assertTrue(equip_success, msg)

        # Try to equip Handaxe to off_hand
        can_equip, error_msg = can_equip_item(self.character, self.handaxe, 'off_hand')
        self.assertFalse(can_equip)
        self.assertEqual(error_msg, "Cannot equip to off-hand while holding two-handed weapon")

    def test_cannot_equip_2h_while_offhand_occupied(self):
        """Cannot equip a two-handed weapon to main_hand if off_hand is occupied"""
        # Equip Handaxe to off_hand
        equip_success, msg, _ = equip_item(self.character, self.handaxe, 'off_hand')
        self.assertTrue(equip_success, msg)

        # Try to equip Greataxe to main_hand
        can_equip, error_msg = can_equip_item(self.character, self.greataxe, 'main_hand')
        self.assertFalse(can_equip)
        self.assertEqual(error_msg, "Cannot equip two-handed weapon while off-hand is occupied")

    def test_can_equip_light_dual_wield(self):
        """Can equip two one-handed weapons (e.g. Handaxes) in main and off hand"""
        equip_success1, msg1, _ = equip_item(self.character, self.handaxe, 'main_hand')
        self.assertTrue(equip_success1, msg1)
        
        # Create a second handaxe character item row for off_hand
        equip_success2, msg2, _ = equip_item(self.character, self.handaxe, 'off_hand')
        self.assertTrue(equip_success2, msg2)
