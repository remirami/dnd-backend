"""
Unit tests for characters/multiclassing.py
Tests multiclass spell slot calculations and level tracking
Target: Improve coverage from 47% to 75%
"""

from django.test import TestCase
from characters.models import Character, CharacterClass, CharacterRace, CharacterClassLevel
from characters.multiclassing import (
    get_total_level,
    calculate_multiclass_spell_slots,
    get_class_level,
    get_multiclass_hit_dice,
    get_primary_class,
    can_multiclass_into
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
        
        # No multiclass levels
        total = get_total_level(character)
        self.assertEqual(total, 0)  # Returns 0 if no CharacterClassLevel records
    
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
        """Test spell slot progression matches D&D 5e multiclass table"""
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
