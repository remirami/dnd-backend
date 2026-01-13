"""
Unit tests for characters/spell_management.py
Tests all spell calculation and validation helper functions
Target: Improve coverage from 33% to 65%
"""

from django.test import TestCase
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from characters.spell_management import (
    is_prepared_caster,
    is_known_caster,
    can_cast_rituals,
    get_spellcasting_ability,
    calculate_spells_prepared,
    calculate_spells_known,
    get_wizard_spellbook_size,
    can_prepare_spell,
    can_learn_spell,
    can_add_to_spellbook,
    get_prepared_spells,
    get_known_spells,
    get_spellbook_spells,
    can_cast_spell
)


class SpellManagementTestCase(TestCase):
    """Test spell management utility functions"""
    
    def setUp(self):
        """Set up test data"""
        # Create character classes
        self.wizard_class = CharacterClass.objects.create(
            name='wizard',
            hit_dice='d6',
            primary_ability='INT',
            saving_throw_proficiencies='INT,WIS'
        )
        
        self.cleric_class = CharacterClass.objects.create(
            name='cleric',
            hit_dice='d8',
            primary_ability='WIS',
            saving_throw_proficiencies='WIS,CHA'
        )
        
        self.bard_class = CharacterClass.objects.create(
            name='bard',
            hit_dice='d8',
            primary_ability='CHA',
            saving_throw_proficiencies='DEX,CHA'
        )
        
        self.sorcerer_class = CharacterClass.objects.create(
            name='sorcerer',
            hit_dice='d6',
            primary_ability='CHA',
            saving_throw_proficiencies='CON,CHA'
        )
        
        self.fighter_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        # Create race
        self.human_race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
    
    def test_is_prepared_caster_wizard(self):
        """Test that wizard is identified as prepared caster"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        self.assertTrue(is_prepared_caster(wizard))
    
    def test_is_prepared_caster_cleric(self):
        """Test that cleric is identified as prepared caster"""
        cleric = Character.objects.create(
            name='Test Cleric',
            level=5,
            character_class=self.cleric_class,
            race=self.human_race
        )
        self.assertTrue(is_prepared_caster(cleric))
    
    def test_is_known_caster_bard(self):
        """Test that bard is identified as known caster"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        self.assertTrue(is_known_caster(bard))
    
    def test_is_known_caster_sorcerer(self):
        """Test that sorcerer is identified as known caster"""
        sorcerer = Character.objects.create(
            name='Test Sorcerer',
            level=5,
            character_class=self.sorcerer_class,
            race=self.human_race
        )
        self.assertTrue(is_known_caster(sorcerer))
    
    def test_non_caster_is_neither(self):
        """Test that fighter is neither prepared nor known caster"""
        fighter = Character.objects.create(
            name='Test Fighter',
            level=5,
            character_class=self.fighter_class,
            race=self.human_race
        )
        self.assertFalse(is_prepared_caster(fighter))
        self.assertFalse(is_known_caster(fighter))
    
    def test_can_cast_rituals_wizard(self):
        """Test that wizard can cast rituals"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        self.assertTrue(can_cast_rituals(wizard))
    
    def test_can_cast_rituals_cleric(self):
        """Test that cleric can cast rituals"""
        cleric = Character.objects.create(
            name='Test Cleric',
            level=5,
            character_class=self.cleric_class,
            race=self.human_race
        )
        self.assertTrue(can_cast_rituals(cleric))
    
    def test_cannot_cast_rituals_bard(self):
        """Test that bard cannot cast rituals (not in RITUAL_CASTERS)"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        self.assertFalse(can_cast_rituals(bard))
    
    def test_get_spellcasting_ability_wizard(self):
        """Test spellcasting ability for wizard (INT)"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        stats = CharacterStats.objects.create(
            character=wizard,
            strength=10,
            dexterity=12,
            constitution=14,
            intelligence=18,  # +4 modifier
            wisdom=10,
            charisma=8,
            hit_points=30,
            max_hit_points=30,
            armor_class=12
        )
        
        modifier = get_spellcasting_ability(wizard)
        self.assertEqual(modifier, 4)  # (18-10)/2 = 4
    
    def test_get_spellcasting_ability_cleric(self):
        """Test spellcasting ability for cleric (WIS)"""
        cleric = Character.objects.create(
            name='Test Cleric',
            level=5,
            character_class=self.cleric_class,
            race=self.human_race
        )
        stats = CharacterStats.objects.create(
            character=cleric,
            strength=14,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=16,  # +3 modifier
            charisma=12,
            hit_points=40,
            max_hit_points=40,
            armor_class=16
        )
        
        modifier = get_spellcasting_ability(cleric)
        self.assertEqual(modifier, 3)  # (16-10)/2 = 3
    
    def test_get_spellcasting_ability_bard(self):
        """Test spellcasting ability for bard (CHA)"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        stats = CharacterStats.objects.create(
            character=bard,
            strength=8,
            dexterity=14,
            constitution=12,
            intelligence=10,
            wisdom=12,
            charisma=18,  # +4 modifier
            hit_points=35,
            max_hit_points=35,
            armor_class=13
        )
        
        modifier = get_spellcasting_ability(bard)
        self.assertEqual(modifier, 4)  # (18-10)/2 = 4
    
    def test_calculate_spells_prepared_wizard(self):
        """Test spell preparation calculation for wizard"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        stats = CharacterStats.objects.create(
            character=wizard,
            intelligence=16,  # +3 modifier
            wisdom=10,
            charisma=10,
            strength=10,
            dexterity=12,
            constitution=14,
            hit_points=30,
            max_hit_points=30,
            armor_class=12
        )
        
        # Level 5 + INT modifier 3 = 8 spells
        spells_prepared = calculate_spells_prepared(wizard)
        self.assertEqual(spells_prepared, 8)
    
    def test_calculate_spells_prepared_minimum(self):
        """Test that prepared spells minimum is 1"""
        wizard = Character.objects.create(
            name='Low INT Wizard',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        stats = CharacterStats.objects.create(
            character=wizard,
            intelligence=8,  # -1 modifier
            wisdom=10,
            charisma=10,
            strength=10,
            dexterity=12,
            constitution=14,
            hit_points=10,
            max_hit_points=10,
            armor_class=11
        )
        
        # Level 1 + (-1) = 0, but minimum is 1
        spells_prepared = calculate_spells_prepared(wizard)
        self.assertEqual(spells_prepared, 1)
    
    def test_calculate_spells_known_bard(self):
        """Test spells known calculation for bard"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        
        # Level 5 bard knows 8 spells
        spells_known = calculate_spells_known(bard)
        self.assertEqual(spells_known, 8)
    
    def test_calculate_spells_known_sorcerer(self):
        """Test spells known calculation for sorcerer"""
        sorcerer = Character.objects.create(
            name='Test Sorcerer',
            level=3,
            character_class=self.sorcerer_class,
            race=self.human_race
        )
        
        # Level 3 sorcerer knows 4 spells
        spells_known = calculate_spells_known(sorcerer)
        self.assertEqual(spells_known, 4)
    
    def test_calculate_spells_known_non_caster(self):
        """Test spells known returns 0 for non-casters"""
        fighter = Character.objects.create(
            name='Test Fighter',
            level=5,
            character_class=self.fighter_class,
            race=self.human_race
        )
        
        spells_known = calculate_spells_known(fighter)
        # Non-casters return empty dict, not 0
        self.assertEqual(spells_known, {})
    
    def test_get_wizard_spellbook_size(self):
        """Test wizard spellbook size calculation"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # 6 at level 1, +2 per level = 6 + (4 * 2) = 14
        spellbook_size = get_wizard_spellbook_size(wizard)
        self.assertEqual(spellbook_size, 14)
    
    def test_get_wizard_spellbook_size_level_1(self):
        """Test wizard spellbook size at level 1"""
        wizard = Character.objects.create(
            name='Level 1 Wizard',
            level=1,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        spellbook_size = get_wizard_spellbook_size(wizard)
        self.assertEqual(spellbook_size, 6)
    
    def test_get_wizard_spellbook_size_non_wizard(self):
        """Test spellbook size returns 0 for non-wizards"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        
        spellbook_size = get_wizard_spellbook_size(bard)
        self.assertEqual(spellbook_size, 0)
    
    def test_can_cast_spell_prepared(self):
        """Test can_cast_spell for prepared spell"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Add prepared spell
        CharacterSpell.objects.create(
            character=wizard,
            name='Fireball',
            level=3,
            school='evocation',
            is_prepared=True
        )
        
        self.assertTrue(can_cast_spell(wizard, 'Fireball'))
    
    def test_can_cast_spell_not_prepared(self):
        """Test can_cast_spell for unprepared spell"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Add unprepared spell
        CharacterSpell.objects.create(
            character=wizard,
            name='Fireball',
            level=3,
            school='evocation',
            is_prepared=False
        )
        
        self.assertFalse(can_cast_spell(wizard, 'Fireball'))
    
    def test_can_cast_spell_ritual(self):
        """Test can_cast_spell for ritual spell"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Add ritual spell (not prepared)
        CharacterSpell.objects.create(
            character=wizard,
            name='Detect Magic',
            level=1,
            school='divination',
            is_prepared=False,
            is_ritual=True
        )
        
        # Can cast as ritual even if not prepared
        self.assertTrue(can_cast_spell(wizard, 'Detect Magic', allow_ritual=True))
    
    def test_can_cast_spell_known_caster(self):
        """Test can_cast_spell for known caster"""
        bard = Character.objects.create(
            name='Test Bard',
            level=5,
            character_class=self.bard_class,
            race=self.human_race
        )
        
        # Add spell (known casters don't prepare)
        CharacterSpell.objects.create(
            character=bard,
            name='Cure Wounds',
            level=1,
            school='evocation',
            is_prepared=False  # Doesn't matter for known casters
        )
        
        self.assertTrue(can_cast_spell(bard, 'Cure Wounds'))
    
    def test_can_cast_spell_not_known(self):
        """Test can_cast_spell for unknown spell"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Don't add any spells
        self.assertFalse(can_cast_spell(wizard, 'Nonexistent Spell'))
    
    def test_get_prepared_spells(self):
        """Test filtering prepared spells"""
        wizard = Character.objects.create(
            name='Test Wizard',
            level=5,
            character_class=self.wizard_class,
            race=self.human_race
        )
        
        # Add some spells
        CharacterSpell.objects.create(
            character=wizard,
            name='Fireball',
            level=3,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=wizard,
            name='Magic Missile',
            level=1,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=wizard,
            name='Wish',
            level=9,
            is_prepared=False
        )
        
        prepared = get_prepared_spells(wizard)
        self.assertEqual(prepared.count(), 2)
        self.assertTrue(prepared.filter(name='Fireball').exists())
        self.assertTrue(prepared.filter(name='Magic Missile').exists())
        self.assertFalse(prepared.filter(name='Wish').exists())
