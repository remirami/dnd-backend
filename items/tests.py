from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from bestiary.models import DamageType
from items.models import Armor, Consumable, ItemCategory, ItemProperty, Weapon


class ItemModelTests(TestCase):
    """Test item models"""
    
    def setUp(self):
        self.category = ItemCategory.objects.create(name='Weapon', description='Combat items')
        self.property = ItemProperty.objects.create(name='Finesse', description='Use DEX instead of STR')
        self.damage_type = DamageType.objects.create(name='Piercing')
    
    def test_create_weapon(self):
        """Test creating a weapon"""
        weapon = Weapon.objects.create(
            name='Shortsword',
            category=self.category,
            weapon_type='martial_melee',
            damage_dice='1d6',
            damage_type=self.damage_type,
            finesse=True,
            weight=2.0,
            value=10
        )
        weapon.properties.add(self.property)
        
        self.assertEqual(weapon.name, 'Shortsword')
        self.assertTrue(weapon.finesse)
        self.assertIn(self.property, weapon.properties.all())
    
    def test_create_armor(self):
        """Test creating armor"""
        armor = Armor.objects.create(
            name='Leather Armor',
            category=self.category,
            armor_type='light',
            base_ac=11,
            weight=10.0,
            value=10
        )
        
        self.assertEqual(armor.name, 'Leather Armor')
        self.assertEqual(armor.base_ac, 11)
        self.assertEqual(armor.armor_type, 'light')
    
    def test_create_consumable(self):
        """Test creating a consumable"""
        consumable = Consumable.objects.create(
            name='Healing Potion',
            category=self.category,
            consumable_type='potion',
            effect='Restores 2d4+2 hit points',
            weight=0.5,
            value=50
        )
        
        self.assertEqual(consumable.name, 'Healing Potion')
        self.assertEqual(consumable.consumable_type, 'potion')


class ItemAPITests(APITestCase):
    """Test item API endpoints"""
    
    def setUp(self):
        self.category = ItemCategory.objects.create(name='Weapon')
        self.damage_type = DamageType.objects.create(name='Slashing')
        self.weapon = Weapon.objects.create(
            name='Longsword',
            category=self.category,
            weapon_type='martial_melee',
            damage_dice='1d8',
            damage_type=self.damage_type,
            weight=3.0,
            value=15
        )
    
    def test_list_weapons(self):
        """Test listing weapons"""
        response = self.client.get('/api/weapons/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertGreater(len(results), 0)
    
    def test_get_weapon(self):
        """Test getting a specific weapon"""
        response = self.client.get(f'/api/weapons/{self.weapon.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Longsword')
    
    def test_filter_weapons_by_type(self):
        """Test filtering weapons by type"""
        response = self.client.get('/api/weapons/?weapon_type=martial_melee')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertGreater(len(results), 0)
    
    def test_list_items(self):
        """Test listing all items"""
        response = self.client.get('/api/items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_armor(self):
        """Test listing armor"""
        Armor.objects.create(
            name='Leather Armor',
            category=self.category,
            armor_type='light',
            base_ac=11,
            weight=10.0,
            value=10
        )
        response = self.client.get('/api/armor/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertGreater(len(results), 0)


class MagicItemMechanicsTests(TestCase):
    """Tests for magic item bonuses, attunement, and character stat interactions"""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterItem
        from items.models import MagicItem, ItemCategory

        User = get_user_model()
        self.user = User.objects.create_user(username='itemtester', password='password123')
        self.char_class = CharacterClass.objects.create(name='Fighter', hit_dice='d10')
        self.race = CharacterRace.objects.create(name='Human')
        self.category = ItemCategory.objects.create(name='Magic Item')

        self.character = Character.objects.create(
            user=self.user,
            name='Arthur',
            character_class=self.char_class,
            race=self.race,
            level=1
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=10,
            dexterity=14,  # +2 mod -> Base AC 12
            constitution=12,
            intelligence=10,
            wisdom=10,
            charisma=10,
            hit_points=12,
            max_hit_points=12,
            armor_class=12
        )

        self.ring_protection = MagicItem.objects.create(
            name='Ring of Protection',
            category=self.category,
            bonus_to_ac=1,
            bonus_to_saves=1,
            requires_attunement=True,
            attunement_required=True
        )

        self.amulet_health = MagicItem.objects.create(
            name='Amulet of Health',
            category=self.category,
            requires_attunement=True,
            attunement_required=True
        )

        self.shield_plus_one = MagicItem.objects.create(
            name='Shield +1',
            category=self.category,
            bonus_to_ac=1,
            requires_attunement=False,
            attunement_required=False
        )

    def test_unattuned_item_does_not_grant_ac_bonus(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item, recalculate_armor_class

        equip_item(self.character, self.ring_protection, slot='ring')
        ac = recalculate_armor_class(self.character)
        # Ring requires attunement; since it's not attuned, AC remains 12
        self.assertEqual(ac, 12)

    def test_attuned_ring_grants_ac_bonus(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item, recalculate_armor_class

        equip_item(self.character, self.ring_protection, slot='ring')
        ci = CharacterItem.objects.get(character=self.character, item=self.ring_protection)
        ci.is_attuned = True
        ci.save()

        ac = recalculate_armor_class(self.character)
        # With Ring of Protection attuned, AC becomes 12 + 1 = 13
        self.assertEqual(ac, 13)

    def test_non_attunement_item_grants_bonus_on_equip(self):
        from characters.inventory_management import equip_item, recalculate_armor_class

        equip_item(self.character, self.shield_plus_one, slot='off_hand')
        ac = recalculate_armor_class(self.character)
        # 12 base + 2 shield + 1 magic bonus = 15
        self.assertEqual(ac, 15)

    def test_amulet_of_health_overrides_constitution(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item

        equip_item(self.character, self.amulet_health, slot='amulet')
        ci = CharacterItem.objects.get(character=self.character, item=self.amulet_health)
        ci.is_attuned = True
        ci.save()

        # Clear cache and check effective constitution
        if hasattr(self.stats, '_cached_effective_scores'):
            del self.stats._cached_effective_scores
        self.assertEqual(self.stats.effective_constitution, 19)
        self.assertEqual(self.stats.constitution_modifier, 4)
        # Base con was 12 (+1 mod). Effective con is 19 (+4 mod). Diff is +3 per level. Level 1 -> +3 HP
        self.assertEqual(self.stats.effective_max_hit_points, self.stats.max_hit_points + 3)

    def test_universal_stat_modification_items(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item
        from items.models import MagicItem

        # 1. Gauntlets of Ogre Power (STR 19)
        gauntlets = MagicItem.objects.create(
            name="Gauntlets of Ogre Power",
            description="Your Strength score is 19 while you wear these gauntlets.",
            attunement_required=True
        )
        equip_item(self.character, gauntlets, slot='gloves')
        ci_g = CharacterItem.objects.get(character=self.character, item=gauntlets)
        ci_g.is_attuned = True
        ci_g.save()

        # 2. Headband of Intellect (INT 19)
        headband = MagicItem.objects.create(
            name="Headband of Intellect",
            description="Your Intelligence score is 19 while you wear this headband.",
            attunement_required=True
        )
        equip_item(self.character, headband, slot='helmet')
        ci_h = CharacterItem.objects.get(character=self.character, item=headband)
        ci_h.is_attuned = True
        ci_h.save()

        if hasattr(self.stats, '_cached_effective_scores'):
            del self.stats._cached_effective_scores

        self.assertEqual(self.stats.effective_strength, 19)
        self.assertEqual(self.stats.strength_modifier, 4)
        self.assertEqual(self.stats.effective_intelligence, 19)
        self.assertEqual(self.stats.intelligence_modifier, 4)

    def test_dynamic_bonus_stat_item(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item
        from items.models import MagicItem

        # Belt of Dwarvenkind (+2 CON)
        belt = MagicItem.objects.create(
            name="Belt of Dwarvenkind",
            description="While wearing this belt, your Constitution score increases by 2, to a maximum of 20.",
            attunement_required=True
        )
        equip_item(self.character, belt, slot='belt')
        ci_b = CharacterItem.objects.get(character=self.character, item=belt)
        ci_b.is_attuned = True
        ci_b.save()

        if hasattr(self.stats, '_cached_effective_scores'):
            del self.stats._cached_effective_scores

        # Base 12 + 2 = 14
        self.assertEqual(self.stats.effective_constitution, 14)
        self.assertEqual(self.stats.constitution_modifier, 2)

    def test_accessory_bonus_to_damage_applies_to_combat(self):
        from characters.models import CharacterItem
        from characters.inventory_management import equip_item
        from items.models import MagicItem
        from combat.models import CombatSession, CombatParticipant

        # Create a magical ring with +1 bonus to damage
        ring_striking = MagicItem.objects.create(
            name="Ring of Striking",
            description="While wearing this ring, your weapon attacks deal an extra 1 point of damage.",
            bonus_to_damage=1,
            attunement_required=True
        )
        equip_item(self.character, ring_striking, slot='ring')
        ci = CharacterItem.objects.get(character=self.character, item=ring_striking)
        ci.is_attuned = True
        ci.save()

        session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        participant = CombatParticipant.objects.create(
            combat_session=session,
            character=self.character,
            current_hp=12,
            max_hp=12,
            armor_class=12
        )

        bonuses = participant.get_magic_item_bonuses()
        self.assertEqual(bonuses['to_damage'], 1)


