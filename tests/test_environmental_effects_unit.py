"""
Comprehensive Unit Tests for Environmental Effects System

Tests terrain, cover, lighting, weather, and hazards utility functions.
All pure functi

ons - no database operations needed.
"""
from django.test import TestCase

from combat.environmental_effects import (
    calculate_movement_cost,
    calculate_cover_ac_bonus,
    calculate_cover_save_bonus,
    has_full_cover,
    get_lighting_attack_modifier,
    get_lighting_perception_modifier,
    get_weather_ranged_modifier,
    calculate_hazard_damage,
    can_see_target,
    get_environmental_effects_summary
)


class TerrainMovementTests(TestCase):
    """Test difficult terrain movement calculations"""
    
    def test_normal_movement(self):
        """Test movement with no terrain effects"""
        movement, multiplier = calculate_movement_cost(30)
        
        self.assertEqual(movement, 30)
        self.assertEqual(multiplier, 1.0)
    
    def test_rubble_doubles_cost(self):
        """Test rubble doubles movement cost"""
        movement, multiplier = calculate_movement_cost(30, terrain_type='rubble')
        self.assertEqual(movement, 15)
        self.assertEqual(multiplier, 2.0)
    
    def test_quicksand_triples_cost(self):
        """Test quicksand triples movement cost"""
        movement, multiplier = calculate_movement_cost(30, terrain_type='quicksand')
        self.assertEqual(movement, 10)
        self.assertEqual(multiplier, 3.0)
    
    def test_snow_weather_reduces_movement(self):
        """Test snow weather reduces movement"""
        movement, multiplier = calculate_movement_cost(30, weather='snow')
        self.assertEqual(movement, 15)
        self.assertGreater(multiplier, 1.0)


class CoverMechanicsTests(TestCase):
    """Test cover bonuses"""
    
    def test_half_cover_bonuses(self):
        """Test half cover grants +2 AC and DEX saves"""
        self.assertEqual(calculate_cover_ac_bonus('half'), 2)
        self.assertEqual(calculate_cover_save_bonus('half'), 2)
    
    def test_three_quarters_cover_bonuses(self):
        """Test three-quarters cover grants +5 AC and DEX saves"""
        self.assertEqual(calculate_cover_ac_bonus('three_quarters'), 5)
        self.assertEqual(calculate_cover_save_bonus('three_quarters'), 5)
    
    def test_full_cover_prevents_targeting(self):
        """Test full cover detection and no bonuses"""
        self.assertTrue(has_full_cover('full'))
        self.assertIsNone(calculate_cover_ac_bonus('full'))
        self.assertFalse(has_full_cover('half'))


class LightingTests(TestCase):
    """Test lighting effects"""
    
    def test_bright_light_no_penalty(self):
        """Test bright light has no penalties"""
        self.assertEqual(get_lighting_attack_modifier('bright_light'), 0)
    
    def test_darkness_without_darkvision(self):
        """Test darkness gives disadvantage without darkvision"""
        self.assertEqual(get_lighting_attack_modifier('darkness'), 'disadvantage')
    
    def test_darkness_with_darkvision(self):
        """Test darkvision negates darkness"""
        self.assertEqual(get_lighting_attack_modifier('darkness', has_darkvision=True), 0)
    
    def test_magical_darkness_blocks_darkvision(self):
        """Test magical darkness blocks darkvision"""
        self.assertEqual(get_lighting_attack_modifier('magical_darkness', has_darkvision=True), 'disadvantage')
    
    def test_visibility_checks(self):
        """Test visibility in different lighting"""
        can_see, _ = can_see_target('bright_light', 'bright_light')
        self.assertTrue(can_see)
        
        can_see, reason = can_see_target('darkness', 'darkness', attacker_darkvision=False)
        self.assertFalse(can_see)
        self.assertIn('darkness', reason.lower())


class WeatherTests(TestCase):
    """Test weather effects"""
    
    def test_clear_weather(self):
        """Test clear weather has no penalties"""
        self.assertEqual(get_weather_ranged_modifier('clear'), 0)
    
    def test_heavy_rain_penalty(self):
        """Test heavy rain gives -2 to ranged"""
        self.assertEqual(get_weather_ranged_modifier('heavy_rain'), -2)
    
    def test_strong_wind_disadvantage(self):
        """Test strong wind gives disadvantage"""
        self.assertEqual(get_weather_ranged_modifier('strong_wind'), 'disadvantage')


class HazardTests(TestCase):
    """Test environmental hazards"""
    
    def test_lava_damage(self):
        """Test lava hazard"""
        dice, dmg_type, save_type, save_dc, _ = calculate_hazard_damage('lava')
        self.assertEqual(dice, '6d10')
        self.assertEqual(dmg_type, 'fire')
        self.assertEqual(save_dc, 15)
    
    def test_poison_gas_condition(self):
        """Test poison gas applies poisoned condition"""
        _, _, _, _, condition = calculate_hazard_damage('poison_gas')
        self.assertEqual(condition, 'poisoned')


class EnvironmentalSummaryTests(TestCase):
    """Test environmental summary function"""
    
    def test_complex_environment(self):
        """Test complete environmental summary"""
        summary = get_environmental_effects_summary(
            terrain='mud',
            cover='three_quarters',
            lighting='darkness',
            weather='snow',
            hazards=['lava']
        )
        
        self.assertIsNotNone(summary['terrain'])
        self.assertIsNotNone(summary['cover'])
        self.assertIsNotNone(summary['lighting'])
        self.assertIsNotNone(summary['weather'])
        self.assertEqual(len(summary['hazards']), 1)
