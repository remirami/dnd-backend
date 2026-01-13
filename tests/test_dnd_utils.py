"""
Tests for D&D 5e utility functions in core.dnd_utils

This test suite verifies that all D&D 5e game mechanic calculations
are implemented correctly according to the official rules.
"""

from django.test import TestCase
from core.dnd_utils import (
    calculate_ability_modifier,
    calculate_proficiency_bonus,
    get_xp_for_level,
    get_level_from_xp,
    roll_dice,
    calculate_hit_points,
    calculate_spell_save_dc,
    calculate_spell_attack_bonus,
    calculate_armor_class,
    calculate_initiative,
    calculate_carrying_capacity,
    get_encumbrance_thresholds,
)


class AbilityModifierTests(TestCase):
    """Test ability score to modifier conversion"""
    
    def test_standard_scores(self):
        """Test common ability scores"""
        self.assertEqual(calculate_ability_modifier(10), 0)  # Average
        self.assertEqual(calculate_ability_modifier(11), 0)
        self.assertEqual(calculate_ability_modifier(12), 1)
        self.assertEqual(calculate_ability_modifier(14), 2)
        self.assertEqual(calculate_ability_modifier(16), 3)
        self.assertEqual(calculate_ability_modifier(18), 4)
        self.assertEqual(calculate_ability_modifier(20), 5)  # Max normal
    
    def test_low_scores(self):
        """Test below-average ability scores"""
        self.assertEqual(calculate_ability_modifier(8), -1)
        self.assertEqual(calculate_ability_modifier(6), -2)
        self.assertEqual(calculate_ability_modifier(4), -3)
        self.assertEqual(calculate_ability_modifier(3), -4)
        self.assertEqual(calculate_ability_modifier(1), -5)
    
    def test_high_scores(self):
        """Test exceptionally high ability scores"""
        self.assertEqual(calculate_ability_modifier(22), 6)
        self.assertEqual(calculate_ability_modifier(24), 7)
        self.assertEqual(calculate_ability_modifier(30), 10)


class ProficiencyBonusTests(TestCase):
    """Test proficiency bonus calculation"""
    
    def test_level_1_to_4(self):
        """Proficiency bonus +2 for levels 1-4"""
        self.assertEqual(calculate_proficiency_bonus(1), 2)
        self.assertEqual(calculate_proficiency_bonus(2), 2)
        self.assertEqual(calculate_proficiency_bonus(3), 2)
        self.assertEqual(calculate_proficiency_bonus(4), 2)
    
    def test_level_5_to_8(self):
        """Proficiency bonus +3 for levels 5-8"""
        self.assertEqual(calculate_proficiency_bonus(5), 3)
        self.assertEqual(calculate_proficiency_bonus(6), 3)
        self.assertEqual(calculate_proficiency_bonus(7), 3)
        self.assertEqual(calculate_proficiency_bonus(8), 3)
    
    def test_level_9_to_12(self):
        """Proficiency bonus +4 for levels 9-12"""
        self.assertEqual(calculate_proficiency_bonus(9), 4)
        self.assertEqual(calculate_proficiency_bonus(10), 4)
        self.assertEqual(calculate_proficiency_bonus(11), 4)
        self.assertEqual(calculate_proficiency_bonus(12), 4)
    
    def test_level_13_to_16(self):
        """Proficiency bonus +5 for levels 13-16"""
        self.assertEqual(calculate_proficiency_bonus(13), 5)
        self.assertEqual(calculate_proficiency_bonus(14), 5)
        self.assertEqual(calculate_proficiency_bonus(15), 5)
        self.assertEqual(calculate_proficiency_bonus(16), 5)
    
    def test_level_17_to_20(self):
        """Proficiency bonus +6 for levels 17-20"""
        self.assertEqual(calculate_proficiency_bonus(17), 6)
        self.assertEqual(calculate_proficiency_bonus(18), 6)
        self.assertEqual(calculate_proficiency_bonus(19), 6)
        self.assertEqual(calculate_proficiency_bonus(20), 6)
    
    def test_edge_cases(self):
        """Test edge cases"""
        self.assertEqual(calculate_proficiency_bonus(0), 2)  # Below min
        self.assertEqual(calculate_proficiency_bonus(21), 6)  # Above max


class ExperiencePointsTests(TestCase):
    """Test XP and level calculations"""
    
    def test_xp_for_level(self):
        """Test XP requirements for each level"""
        self.assertEqual(get_xp_for_level(1), 0)
        self.assertEqual(get_xp_for_level(2), 300)
        self.assertEqual(get_xp_for_level(3), 900)
        self.assertEqual(get_xp_for_level(4), 2700)
        self.assertEqual(get_xp_for_level(5), 6500)
        self.assertEqual(get_xp_for_level(10), 64000)
        self.assertEqual(get_xp_for_level(15), 165000)
        self.assertEqual(get_xp_for_level(20), 355000)
    
    def test_level_from_xp(self):
        """Test calculating level from XP"""
        self.assertEqual(get_level_from_xp(0), 1)
        self.assertEqual(get_level_from_xp(299), 1)
        self.assertEqual(get_level_from_xp(300), 2)
        self.assertEqual(get_level_from_xp(899), 2)
        self.assertEqual(get_level_from_xp(900), 3)
        self.assertEqual(get_level_from_xp(7000), 5)
        self.assertEqual(get_level_from_xp(64000), 10)
        self.assertEqual(get_level_from_xp(355000), 20)
        self.assertEqual(get_level_from_xp(999999), 20)  # Beyond max
    
    def test_xp_level_roundtrip(self):
        """Test that XP -> Level -> XP roundtrip works"""
        for level in range(1, 21):
            min_xp = get_xp_for_level(level)
            calculated_level = get_level_from_xp(min_xp)
            self.assertEqual(calculated_level, level)


class DiceRollingTests(TestCase):
    """Test dice rolling utility"""
    
    def test_simple_dice(self):
        """Test simple dice rolls without modifiers"""
        total, rolls, modifier = roll_dice('1d6')
        self.assertEqual(len(rolls), 1)
        self.assertTrue(1 <= rolls[0] <= 6)
        self.assertEqual(modifier, 0)
        self.assertTrue(1 <= total <= 6)
    
    def test_multiple_dice(self):
        """Test rolling multiple dice"""
        total, rolls, modifier = roll_dice('2d6')
        self.assertEqual(len(rolls), 2)
        for roll in rolls:
            self.assertTrue(1 <= roll <= 6)
        self.assertEqual(modifier, 0)
        self.assertTrue(2 <= total <= 12)
    
    def test_dice_with_positive_modifier(self):
        """Test dice with positive modifier"""
        total, rolls, modifier = roll_dice('1d20+5')
        self.assertEqual(len(rolls), 1)
        self.assertTrue(1 <= rolls[0] <= 20)
        self.assertEqual(modifier, 5)
        self.assertTrue(6 <= total <= 25)
    
    def test_dice_with_negative_modifier(self):
        """Test dice with negative modifier"""
        total, rolls, modifier = roll_dice('1d8-2')
        self.assertEqual(len(rolls), 1)
        self.assertTrue(1 <= rolls[0] <= 8)
        self.assertEqual(modifier, -2)
    
    def test_complex_dice(self):
        """Test complex dice notation"""
        total, rolls, modifier = roll_dice('3d10+7')
        self.assertEqual(len(rolls), 3)
        for roll in rolls:
            self.assertTrue(1 <= roll <= 10)
        self.assertEqual(modifier, 7)
        self.assertTrue(10 <= total <= 37)
    
    def test_invalid_dice_string(self):
        """Test that invalid dice strings raise errors"""
        with self.assertRaises(ValueError):
            roll_dice('invalid')
        with self.assertRaises(ValueError):
            roll_dice('2x6')


class HitPointsTests(TestCase):
    """Test HP calculation"""
    
    def test_level_1_hp(self):
        """Test level 1 HP (always max die + CON)"""
        # Fighter (d10) with +2 CON
        hp = calculate_hit_points(1, 10, 2, use_average=True)
        self.assertEqual(hp, 12)  # 10 + 2
        
        # Wizard (d6) with +1 CON
        hp = calculate_hit_points(1, 6, 1, use_average=True)
        self.assertEqual(hp, 7)  # 6 + 1
    
    def test_average_hp(self):
        """Test average HP calculation"""
        # Fighter (d10) level 5 with +3 CON
        # Level 1: 10 + 3 = 13
        # Levels 2-5: (6 + 3) * 4 = 36
        # Total: 13 + 36 = 49
        hp = calculate_hit_points(5, 10, 3, use_average=True)
        self.assertEqual(hp, 49)
        
        # Wizard (d6) level 3 with +1 CON
        # Level 1: 6 + 1 = 7
        # Levels 2-3: (4 + 1) * 2 = 10
        # Total: 7 + 10 = 17
        hp = calculate_hit_points(3, 6, 1, use_average=True)
        self.assertEqual(hp, 17)
    
    def test_negative_con_modifier(self):
        """Test HP with negative CON modifier"""
        # Level 1 should still give at least 1 HP
        hp = calculate_hit_points(1, 6, -2, use_average=True)
        self.assertGreaterEqual(hp, 1)
    
    def test_minimum_hp_per_level(self):
        """Test that HP is at least 1 per level"""
        # Even with -5 CON, should get minimum HP
        hp = calculate_hit_points(5, 6, -5, use_average=True)
        self.assertGreaterEqual(hp, 5)


class SpellcastingTests(TestCase):
    """Test spellcasting calculations"""
    
    def test_spell_save_dc(self):
        """Test spell save DC calculation"""
        # 8 + proficiency + spellcasting modifier
        self.assertEqual(calculate_spell_save_dc(2, 3), 13)  # 8 + 2 + 3
        self.assertEqual(calculate_spell_save_dc(3, 4), 15)  # 8 + 3 + 4
        self.assertEqual(calculate_spell_save_dc(6, 5), 19)  # 8 + 6 + 5
    
    def test_spell_attack_bonus(self):
        """Test spell attack bonus calculation"""
        # proficiency + spellcasting modifier
        self.assertEqual(calculate_spell_attack_bonus(2, 3), 5)  # 2 + 3
        self.assertEqual(calculate_spell_attack_bonus(3, 4), 7)  # 3 + 4
        self.assertEqual(calculate_spell_attack_bonus(6, 5), 11)  # 6 + 5


class ArmorClassTests(TestCase):
    """Test AC calculation"""
    
    def test_basic_ac(self):
        """Test basic AC with just armor and DEX"""
        # Leather armor (AC 11) + DEX +2
        self.assertEqual(calculate_armor_class(11, 2), 13)
        
        # Chain mail (AC 16) + DEX +0
        self.assertEqual(calculate_armor_class(16, 0), 16)
    
    def test_ac_with_shield(self):
        """Test AC with shield bonus"""
        # Leather armor + DEX +3 + shield +2
        self.assertEqual(calculate_armor_class(11, 3, shield_bonus=2), 16)
    
    def test_ac_with_magic_items(self):
        """Test AC with magic item bonuses"""
        # Chain mail + DEX +0 + magic +1
        self.assertEqual(calculate_armor_class(16, 0, magic_bonus=1), 17)
    
    def test_ac_all_bonuses(self):
        """Test AC with all bonuses combined"""
        # Base 14 + DEX +2 + shield +2 + magic +1
        self.assertEqual(calculate_armor_class(14, 2, shield_bonus=2, magic_bonus=1), 19)


class InitiativeTests(TestCase):
    """Test initiative calculation"""
    
    def test_basic_initiative(self):
        """Test initiative with just DEX modifier"""
        self.assertEqual(calculate_initiative(3), 3)
        self.assertEqual(calculate_initiative(-1), -1)
    
    def test_initiative_with_bonus(self):
        """Test initiative with additional bonuses"""
        # DEX +3 + Improved Initiative +4
        self.assertEqual(calculate_initiative(3, bonus=4), 7)


class EncumbranceTests(TestCase):
    """Test carrying capacity and encumbrance"""
    
    def test_carrying_capacity(self):
        """Test carrying capacity calculation"""
        self.assertEqual(calculate_carrying_capacity(10), 150)  # 10 * 15
        self.assertEqual(calculate_carrying_capacity(15), 225)  # 15 * 15
        self.assertEqual(calculate_carrying_capacity(20), 300)  # 20 * 15
    
    def test_encumbrance_thresholds(self):
        """Test encumbrance threshold calculation"""
        thresholds = get_encumbrance_thresholds(15)
        
        self.assertEqual(thresholds['normal'], 75)  # 225 / 3
        self.assertEqual(thresholds['encumbered'], 150)  # 225 * 2 / 3
        self.assertEqual(thresholds['max'], 225)  # 225
    
    def test_encumbrance_different_strengths(self):
        """Test encumbrance at different strength scores"""
        # STR 10
        thresholds = get_encumbrance_thresholds(10)
        self.assertEqual(thresholds['max'], 150)
        
        # STR 20
        thresholds = get_encumbrance_thresholds(20)
        self.assertEqual(thresholds['max'], 300)
