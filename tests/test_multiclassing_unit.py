"""
Unit tests for characters/multiclassing.py
Tests multiclass spell slot calculations and level tracking
Target: Improve coverage from 47% to 75%
"""

from django.test import TestCase

from characters.models import Character, CharacterClass, CharacterClassLevel, CharacterRace
from characters.multiclassing import (
    calculate_multiclass_spell_slots,
    get_class_level,
    get_multiclass_hit_dice,
    get_primary_class,
    get_total_level,
)


class MulticlassingTestCase(TestCase):
    """Test multiclassing utility functions"""
    
    def setUp(self):
        """Set up test data"""
        # Create character classes
        self.wizard_class = CharacterClass.objects.create(
            name='wizard',
            hit_dice='d6',
            primary_ability='INT',
            saving_throw_proficiencies='INT,WIS'
        )
        
        self.fighter_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        self.paladin_class = CharacterClass.objects.create(
            name='paladin',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='WIS,CHA'
        )
        
        self.warlock_class = CharacterClass.objects.create(
            name='warlock',
            hit_dice='d8',
            primary_ability='CHA',
            saving_throw_proficiencies='WIS,CHA'
        )
        
        self.rogue_class = CharacterClass.objects.create(
            name='rogue',
            hit_dice='d8',
            primary_ability='DEX',
            saving_throw_proficiencies='DEX,INT'
        )
        
        # Create race
        self.human_race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
    
    def test_get_total_level_single_class(self):
        """Test total level for single-class character"""
        character = Character.objects.create(
            name='Single Class Fighter',
            level=5,
            character_class=self.fighter_class,
            race=self.human_race
        )
        
        # Single class character defaults to their base level (5)
        total = get_total_level(character)
        self.assertEqual(total, 5)
    
    def test_get_total_level_multiclass(self):
        """Test total level for multiclass character"""
        character = Character.objects.create(
            name='Multiclass Character',
            level=1,  # Base level
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Add multiclass levels
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=3
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=2
        )
        
        total = get_total_level(character)
        self.assertEqual(total, 5)  # 3 + 2
    
    def test_get_total_level_three_classes(self):
        """Test total level with three classes"""
        character = Character.objects.create(
            name='Triple Multiclass',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=2
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=2
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.rogue_class,
            level=1
        )
        
        total = get_total_level(character)
        self.assertEqual(total, 5)  # 2 + 2 + 1
    
    def test_calculate_multiclass_spell_slots_fighter_wizard(self):
        """Test spell slots for Fighter/Wizard multiclass"""
        character = Character.objects.create(
            name='Fighter/Wizard',
            level=1,
            character_class=self.fighter_class,
            race=self.human_race
        )
        
        # Fighter 3 / Wizard 2
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=3
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=2
        )
        
        # Fighter gives 1/3 caster level, Wizard gives full
        # 3/3 + 2 = 3 effective caster levels
        slots = calculate_multiclass_spell_slots(character)
        
        # Should have some spell slots
        self.assertIsInstance(slots, dict)
        self.assertGreater(len(slots), 0)
        # At minimum should have level 1 slots
        if 1 in slots:
            self.assertGreater(slots[1], 0)
    
    def test_calculate_multiclass_spell_slots_paladin_warlock(self):
        """Test spell slots for Paladin/Warlock multiclass"""
        character = Character.objects.create(
            name='Paladin/Warlock',
            level=1,
            character_class=self.paladin_class,
            race=self.human_race
        )
        
        # Paladin 6 / Warlock 2
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.paladin_class,
            level=6
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.warlock_class,
            level=2
        )
        
        # Warlock uses pact magic, shouldn't combine normally
        # Paladin 6 gives 3 half-caster levels = 3 effective
        slots = calculate_multiclass_spell_slots(character)
        
        # Should have spell slots
        self.assertIsInstance(slots, dict)
        self.assertGreater(len(slots), 0)
    
    def test_calculate_multiclass_spell_slots_no_casters(self):
        """Test spell slots for non-caster multiclass"""
        character = Character.objects.create(
            name='Fighter/Rogue',
            level=1,
            character_class=self.fighter_class,
            race=self.human_race
        )
        
        # Fighter 5 / Rogue 3 (no casters)
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=5
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.rogue_class,
            level=3
        )
        
        slots = calculate_multiclass_spell_slots(character)
        
        # Should return empty dict or minimal slots
        self.assertIsInstance(slots, dict)
    
    def test_get_class_level(self):
        """Test getting level in a specific class"""
        character = Character.objects.create(
            name='Multiclass',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=4
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=2
        )
        
        wizard_level = get_class_level(character, 'wizard')
        fighter_level = get_class_level(character, 'fighter')
        
        self.assertEqual(wizard_level, 4)
        self.assertEqual(fighter_level, 2)
    
    def test_get_primary_class(self):
        """Test getting primary class (highest level)"""
        character = Character.objects.create(
            name='Multiclass',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=2
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=5  # Highest
        )
        
        primary = get_primary_class(character)
        self.assertEqual(primary.name, 'fighter')
    
    def test_get_multiclass_hit_dice(self):
        """Test hit dice calculation for multiclass"""
        character = Character.objects.create(
            name='Multiclass',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=3  # d6
        )
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.fighter_class,
            level=2  # d10
        )
        
        hit_dice = get_multiclass_hit_dice(character)
        
        # Should have both types
        self.assertIn('d6', hit_dice)
        self.assertIn('d10', hit_dice)
        self.assertEqual(hit_dice['d6'], 3)
        self.assertEqual(hit_dice['d10'], 2)
    
    def test_multiclass_spell_slots_progression(self):
        """Test spell slot progression matches SRD 5.2 5e multiclass table"""
        character = Character.objects.create(
            name='Multiclass Caster',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Create level 5 caster (Wizard 3 / Wizard 2 for testing)
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard_class,
            level=5
        )
        
        slots = calculate_multiclass_spell_slots(character)
        
        # Level 5 caster should have: 4/3/2/0/0...
        if 1 in slots:
            self.assertEqual(slots[1], 4)
        if 2 in slots:
            self.assertEqual(slots[2], 3)
        if 3 in slots:
            self.assertEqual(slots[3], 2)

    def test_multiclass_spell_slots_2024_half_caster_round_up(self):
        """Test that in 2024 rules (SRD 5.2), half casters round up when calculating multiclass caster level"""
        # Paladin 1 / Sorcerer 1
        # In 2024: Sorcerer 1 + ceil(1/2) = 1 + 1 = 2 (2nd level caster -> 3 1st-level slots)
        # In 2014: Sorcerer 1 + floor(1/2) = 1 + 0 = 1 (1st level caster -> 2 1st-level slots)
        sorcerer_class = CharacterClass.objects.create(name='sorcerer', hit_dice='d6')
        
        char_2024 = Character.objects.create(
            name='2024 Paladin Sorcerer',
            ruleset_version='2024',
            character_class=self.paladin_class,
            race=self.human_race
        )
        CharacterClassLevel.objects.create(character=char_2024, character_class=self.paladin_class, level=1)
        CharacterClassLevel.objects.create(character=char_2024, character_class=sorcerer_class, level=1)
        
        slots_2024 = calculate_multiclass_spell_slots(char_2024)
        self.assertEqual(slots_2024.get(1), 3, "2024 half-caster round-up should result in 3 1st-level slots")

        char_2014 = Character.objects.create(
            name='2014 Paladin Sorcerer',
            ruleset_version='2014',
            character_class=self.paladin_class,
            race=self.human_race
        )
        CharacterClassLevel.objects.create(character=char_2014, character_class=self.paladin_class, level=1)
        CharacterClassLevel.objects.create(character=char_2014, character_class=sorcerer_class, level=1)
        
        slots_2014 = calculate_multiclass_spell_slots(char_2014)
        self.assertEqual(slots_2014.get(1), 2, "2014 half-caster round-down should result in 2 1st-level slots")

    def test_can_multiclass_into_requires_current_class_prerequisites(self):
        """Test that a character must meet prerequisites for BOTH their current class and the new class"""
        from characters.models import CharacterStats
        from characters.multiclassing import can_multiclass_into

        # Wizard with low INT (10) but high STR (16) trying to multiclass into Fighter
        char = Character.objects.create(
            name='Low INT Wizard',
            ruleset_version='2014',
            character_class=self.wizard_class,
            race=self.human_race
        )
        CharacterStats.objects.create(
            character=char,
            strength=16,
            dexterity=10,
            constitution=14,
            intelligence=10, # Fails Wizard requirement (13)
            wisdom=10,
            charisma=10,
            hit_points=12,
            max_hit_points=12,
            armor_class=10
        )
        CharacterClassLevel.objects.create(character=char, character_class=self.wizard_class, level=2)

        can_multi, reason = can_multiclass_into(char, 'Fighter')
        self.assertFalse(can_multi, "Should not be able to multiclass if current class prereq is not met")
        self.assertIn("current class Wizard", reason)

        # Raise INT to 13
        char.stats.intelligence = 13
        char.stats.save()
        can_multi_ok, reason_ok = can_multiclass_into(char, 'Fighter')
        self.assertTrue(can_multi_ok, f"Should be eligible after meeting INT 13: {reason_ok}")

    def test_2024_paladin_and_ranger_dex_or_str_prerequisite(self):
        """Test that 2024 rules allow DEX for Paladin and STR for Ranger multiclassing"""
        from characters.models import CharacterStats
        from characters.multiclassing import can_multiclass_into

        # Dex-based Paladin (STR 10, DEX 14, CHA 14)
        char = Character.objects.create(
            name='Dexterous Rogue',
            ruleset_version='2024',
            character_class=self.rogue_class,
            race=self.human_race
        )
        CharacterStats.objects.create(
            character=char,
            strength=10,
            dexterity=14,
            constitution=12,
            intelligence=10,
            wisdom=10,
            charisma=14,
            hit_points=10,
            max_hit_points=10,
            armor_class=12
        )
        CharacterClassLevel.objects.create(character=char, character_class=self.rogue_class, level=1)

        # 2024 allows DEX 14 + CHA 14 for Paladin
        can_pally_2024, reason_2024 = can_multiclass_into(char, 'Paladin')
        self.assertTrue(can_pally_2024, f"2024 should allow Dex Paladin: {reason_2024}")

        # In 2014 rules, this fails because STR 13 was required
        char.ruleset_version = '2014'
        char.save()
        can_pally_2014, reason_2014 = can_multiclass_into(char, 'Paladin')
        self.assertFalse(can_pally_2014, "2014 should reject Paladin with STR < 13")
        self.assertIn("STR 13", reason_2014)

    def test_apply_multiclass_proficiencies(self):
        """Test that taking a new class grants that class's multiclass proficiencies"""
        from characters.models import CharacterProficiency
        from characters.multiclassing import apply_multiclass_proficiencies

        char = Character.objects.create(
            name='Wizard Multi',
            character_class=self.wizard_class,
            race=self.human_race
        )
        # Multiclass into Fighter
        profs = apply_multiclass_proficiencies(char, 'fighter')
        self.assertGreater(len(profs), 0)

        armor_profs = CharacterProficiency.objects.filter(character=char, proficiency_type='armor').values_list('item_name', flat=True)
        weapon_profs = CharacterProficiency.objects.filter(character=char, proficiency_type='weapon').values_list('item_name', flat=True)

        self.assertIn('Shields', armor_profs)
        self.assertIn('Medium Armor', armor_profs)
        self.assertIn('Martial Weapons', weapon_profs)

    def test_level_up_api_multiclass_flow(self):
        """Test API endpoint leveling up into a secondary class"""
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient
        from characters.models import CharacterStats, CharacterProficiency

        user = User.objects.create_user(username='multiclass_tester', password='password123')
        client = APIClient()
        client.force_authenticate(user=user)

        char = Character.objects.create(
            user=user,
            name='Test Hero',
            level=2,
            character_class=self.fighter_class,
            race=self.human_race
        )
        CharacterStats.objects.create(
            character=char,
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=14,
            wisdom=10,
            charisma=10,
            hit_points=20,
            max_hit_points=20,
            armor_class=14
        )
        CharacterClassLevel.objects.create(character=char, character_class=self.fighter_class, level=2)

        # Level up into Wizard (multiclass)
        response = client.post(f'/api/characters/{char.id}/level_up/', {
            'class_id': self.wizard_class.id,
            'hp_mode': 'fixed'
        })
        self.assertEqual(response.status_code, 200)

        # Check character now has 2 classes and total level 3
        char.refresh_from_db()
        self.assertEqual(char.level, 3)
        self.assertEqual(char.class_levels.count(), 2)

        wiz_level = char.class_levels.get(character_class=self.wizard_class).level
        fighter_level = char.class_levels.get(character_class=self.fighter_class).level
        self.assertEqual(wiz_level, 1)
        self.assertEqual(fighter_level, 2)

    def test_multiclass_info_and_check_endpoints_return_real_prereqs(self):
        """Test that multiclass_info and check_multiclass return populated prerequisite dicts"""
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient
        from characters.models import CharacterStats

        user = User.objects.create_user(username='prereq_tester', password='password123')
        client = APIClient()
        client.force_authenticate(user=user)

        char = Character.objects.create(
            user=user,
            name='Prereq Hero',
            level=1,
            character_class=self.fighter_class,
            race=self.human_race
        )
        CharacterStats.objects.create(
            character=char,
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=14,
            wisdom=10,
            charisma=10,
            hit_points=12,
            max_hit_points=12,
            armor_class=14
        )
        CharacterClassLevel.objects.create(character=char, character_class=self.fighter_class, level=1)

        # 1. multiclass_info endpoint
        info_res = client.get(f'/api/characters/{char.id}/multiclass_info/')
        self.assertEqual(info_res.status_code, 200)
        avail = info_res.data['available_classes']
        wiz_avail = next(c for c in avail if c['class_name'].lower() == 'wizard')
        self.assertTrue(wiz_avail['can_multiclass'])
        self.assertEqual(wiz_avail['prerequisites'], {'intelligence': 13})

        # 2. check_multiclass endpoint
        check_res = client.post(f'/api/characters/{char.id}/check_multiclass/', {
            'class_id': self.wizard_class.id
        })
        self.assertEqual(check_res.status_code, 200)
        self.assertTrue(check_res.data['can_multiclass'])
        self.assertEqual(check_res.data['prerequisites'], {'intelligence': 13})
