"""
Test script for Environmental Effects System

Tests:
1. Difficult terrain movement costs
2. Cover AC bonuses
3. Lighting effects on attacks
4. Weather effects on ranged attacks
5. Hazard damage
6. Position tracking
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from django.contrib.auth.models import User
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from encounters.models import Encounter
from combat.models import CombatSession, CombatParticipant, EnvironmentalEffect, ParticipantPosition
from combat.environmental_effects import (
    calculate_movement_cost, calculate_cover_ac_bonus, calculate_cover_save_bonus,
    has_full_cover, get_lighting_attack_modifier, get_weather_ranged_modifier,
    get_environmental_effects_summary
)

# Configure stdout for Unicode
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def print_test(name):
    """Print test header"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def test_difficult_terrain():
    """Test difficult terrain movement costs"""
    print_test("Difficult Terrain Movement Costs")
    
    base_speed = 30
    
    test_cases = [
        (None, None, 30, 1.0),  # No terrain
        ('rubble', None, 15, 2.0),  # Difficult terrain doubles cost
        ('mud', None, 15, 2.0),
        ('quicksand', None, 10, 3.0),  # Quicksand triples cost
        ('rubble', 'snow', 7, 4.0),  # Terrain + weather
    ]
    
    for terrain, weather, expected_movement, expected_multiplier in test_cases:
        effective_movement, cost_multiplier = calculate_movement_cost(
            base_speed,
            terrain_type=terrain,
            weather=weather
        )
        print(f"  Terrain: {terrain or 'None'}, Weather: {weather or 'None'}")
        print(f"    Base speed: {base_speed} → Effective: {effective_movement} (multiplier: {cost_multiplier}x)")
        assert effective_movement == expected_movement, f"Expected {expected_movement}, got {effective_movement}"
        assert abs(cost_multiplier - expected_multiplier) < 0.1, f"Expected {expected_multiplier}, got {cost_multiplier}"
    
    print("  ✅ All difficult terrain tests passed!")


def test_cover():
    """Test cover AC bonuses"""
    print_test("Cover AC Bonuses")
    
    test_cases = [
        (None, 0),
        ('half', 2),
        ('three_quarters', 5),
        ('full', None),  # Full cover prevents targeting
    ]
    
    for cover_type, expected_bonus in test_cases:
        bonus = calculate_cover_ac_bonus(cover_type)
        print(f"  Cover: {cover_type or 'None'} → AC Bonus: {bonus}")
        
        if cover_type == 'full':
            assert has_full_cover(cover_type), "Full cover should prevent targeting"
        else:
            assert bonus == expected_bonus, f"Expected {expected_bonus}, got {bonus}"
    
    print("  ✅ All cover tests passed!")


def test_lighting():
    """Test lighting effects on attacks"""
    print_test("Lighting Effects on Attacks")
    
    test_cases = [
        ('bright_light', False, 0),
        ('dim_light', False, 0),
        ('darkness', False, 'disadvantage'),
        ('darkness', True, 0),  # Darkvision can see in darkness
        ('magical_darkness', True, 'disadvantage'),  # Even darkvision doesn't help
    ]
    
    for lighting, has_darkvision, expected_modifier in test_cases:
        modifier = get_lighting_attack_modifier(lighting, has_darkvision)
        print(f"  Lighting: {lighting}, Darkvision: {has_darkvision} → Modifier: {modifier}")
        assert modifier == expected_modifier, f"Expected {expected_modifier}, got {modifier}"
    
    print("  ✅ All lighting tests passed!")


def test_weather():
    """Test weather effects"""
    print_test("Weather Effects")
    
    test_cases = [
        ('clear', 0),
        ('light_rain', 0),
        ('heavy_rain', -2),
        ('fog', 0),
        ('strong_wind', 'disadvantage'),
    ]
    
    for weather, expected_modifier in test_cases:
        modifier = get_weather_ranged_modifier(weather)
        print(f"  Weather: {weather} → Ranged Modifier: {modifier}")
        assert modifier == expected_modifier, f"Expected {expected_modifier}, got {modifier}"
    
    print("  ✅ All weather tests passed!")


def test_environmental_effects_integration():
    """Test environmental effects integration with combat"""
    print_test("Environmental Effects Integration")
    
    # Create test combat session
    user, _ = User.objects.get_or_create(username='test_user')
    char_class, _ = CharacterClass.objects.get_or_create(name='Fighter')
    race, _ = CharacterRace.objects.get_or_create(name='Human')
    
    character = Character.objects.create(
        user=user,
        name="Test Fighter",
        character_class=char_class,
        race=race,
        level=5
    )
    
    stats, _ = CharacterStats.objects.get_or_create(
        character=character,
        defaults={
            'hit_points': 50,
            'max_hit_points': 50,
            'armor_class': 15,
            'speed': 30,
            'strength': 16,
            'dexterity': 14,
        }
    )
    
    encounter = Encounter.objects.create(name="Test Encounter")
    session = CombatSession.objects.create(encounter=encounter, status='active')
    
    participant = CombatParticipant.objects.create(
        combat_session=session,
        participant_type='character',
        character=character,
        initiative=15,
        current_hp=50,
        max_hp=50,
        armor_class=15
    )
    
    # Test 1: Add difficult terrain
    terrain_effect = EnvironmentalEffect.objects.create(
        combat_session=session,
        effect_type='terrain',
        terrain_type='rubble',
        description='Rubble covers the battlefield'
    )
    print(f"  ✓ Created terrain effect: {terrain_effect}")
    
    # Test 2: Add cover
    cover_effect = EnvironmentalEffect.objects.create(
        combat_session=session,
        effect_type='cover',
        cover_type='half',
        cover_area_x=10,
        cover_area_y=10,
        cover_area_radius=5,
        description='Half cover at (10, 10)'
    )
    print(f"  ✓ Created cover effect: {cover_effect}")
    
    # Test 3: Add lighting
    lighting_effect = EnvironmentalEffect.objects.create(
        combat_session=session,
        effect_type='lighting',
        lighting_type='dim_light',
        lighting_area_x=0,
        lighting_area_y=0,
        lighting_area_radius=30,
        description='Dim light in center area'
    )
    print(f"  ✓ Created lighting effect: {lighting_effect}")
    
    # Test 4: Add weather
    weather_effect = EnvironmentalEffect.objects.create(
        combat_session=session,
        effect_type='weather',
        weather_type='heavy_rain',
        description='Heavy rain'
    )
    print(f"  ✓ Created weather effect: {weather_effect}")
    
    # Test 5: Set participant position
    position = ParticipantPosition.objects.create(
        participant=participant,
        x=10,
        y=10,
        z=0,
        current_terrain='rubble',
        current_cover='half',
        current_lighting='dim_light'
    )
    print(f"  ✓ Created participant position: {position}")
    
    # Test 6: Calculate movement with terrain
    effective_movement, cost_multiplier = calculate_movement_cost(30, terrain_type='rubble')
    print(f"  ✓ Movement with rubble: {effective_movement} feet (cost multiplier: {cost_multiplier}x)")
    assert effective_movement == 15, "Rubble should halve movement"
    
    # Test 7: Calculate AC with cover
    cover_bonus = calculate_cover_ac_bonus('half')
    effective_ac = participant.calculate_effective_ac(cover_bonus=cover_bonus)
    print(f"  ✓ AC with half cover: {effective_ac} (base: {participant.armor_class}, bonus: +{cover_bonus})")
    assert effective_ac == participant.armor_class + cover_bonus
    
    # Cleanup
    session.delete()
    character.delete()
    
    print("  ✅ All integration tests passed!")


def test_hazard_damage():
    """Test hazard damage calculation"""
    print_test("Hazard Damage")
    
    from combat.environmental_effects import calculate_hazard_damage
    
    test_cases = [
        ('lava', '6d10', 'fire', 'DEX', 15),
        ('acid', '4d6', 'acid', 'DEX', 12),
        ('poison_gas', '2d6', 'poison', 'CON', 13),
    ]
    
    for hazard_type, expected_dice, expected_damage_type, expected_save_type, expected_dc in test_cases:
        damage_dice, damage_type, save_type, save_dc, condition = calculate_hazard_damage(hazard_type)
        print(f"  Hazard: {hazard_type}")
        print(f"    Damage: {damage_dice}, Type: {damage_type}, Save: {save_type} DC {save_dc}")
        assert damage_dice == expected_dice, f"Expected {expected_dice}, got {damage_dice}"
        assert damage_type == expected_damage_type, f"Expected {expected_damage_type}, got {damage_type}"
        assert save_type == expected_save_type, f"Expected {expected_save_type}, got {save_type}"
        assert save_dc == expected_dc, f"Expected {expected_dc}, got {save_dc}"
    
    print("  ✅ All hazard damage tests passed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ENVIRONMENTAL EFFECTS SYSTEM TESTS")
    print("="*60)
    
    try:
        test_difficult_terrain()
        test_cover()
        test_lighting()
        test_weather()
        test_hazard_damage()
        test_environmental_effects_integration()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

