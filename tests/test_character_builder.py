"""
Tests for Character Builder Service - Phase 1

Testing validators, calculators, and core service functionality
"""
from django.test import TestCase
from django.contrib.auth.models import User

from characters.services import (
    AbilityScoreValidator,
    RacialBonusCalculator,
    MulticlassPrerequisiteChecker,
    CharacterBuilderService
)
from characters.builder_models import CharacterBuilderSession
from characters.models import CharacterClass, CharacterRace, CharacterBackground


class AbilityScoreValidatorTests(TestCase):
    """Test ability score validation"""
    
    def test_standard_array_valid(self):
        """Test valid standard array"""
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        valid, error = AbilityScoreValidator.validate_standard_array(scores)
        self.assertTrue(valid)
        self.assertEqual(error, "")
    
    def test_standard_array_invalid_values(self):
        """Test invalid standard array values"""
        scores = {'str': 16, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        valid, error = AbilityScoreValidator.validate_standard_array(scores)
        self.assertFalse(valid)
        self.assertIn("standard array", error)
    
    def test_point_buy_valid(self):
        """Test valid point buy (27 points)"""
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        # 9 + 7 + 5 + 4 + 2 + 0 = 27
        valid, error, points = AbilityScoreValidator.validate_point_buy(scores)
        self.assertTrue(valid)
        self.assertEqual(points, 27)
    
    def test_point_buy_over_budget(self):
        """Test point buy over budget"""
        scores = {'str': 15, 'dex': 15, 'con': 15, 'int': 15, 'wis': 15, 'cha': 15}
        # 9*6 = 54 points
        valid, error, points = AbilityScoreValidator.validate_point_buy(scores)
        self.assertFalse(valid)
        self.assertIn("budget exceeded", error)
    
    def test_point_buy_under_budget(self):
        """Test point buy under budget"""
        scores = {'str': 8, 'dex': 8, 'con': 8, 'int': 8, 'wis': 8, 'cha': 8}
        # 0 points
        valid, error, points = AbilityScoreValidator.validate_point_buy(scores)
        self.assertFalse(valid)
        self.assertIn("Must use all", error)
    
    def test_manual_valid(self):
        """Test manual entry (DM discretion)"""
        scores = {'str': 18, 'dex': 16, 'con': 14, 'int': 12, 'wis': 10, 'cha': 8}
        valid, error, warnings = AbilityScoreValidator.validate_manual(scores)
        self.assertTrue(valid)
        self.assertIn("very high", warnings[0])  # 18 STR warning
    
    def test_manual_too_low(self):
        """Test manual score too low"""
        scores = {'str': 2, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        valid, error, warnings = AbilityScoreValidator.validate_manual(scores)
        self.assertFalse(valid)
        self.assertIn("too low", error)


class RacialBonusCalculatorTests(TestCase):
    """Test racial bonus calculations"""
    
    def test_human_bonuses(self):
        """Test human gets +1 to all"""
        base = {'str': 10, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        final = RacialBonusCalculator.apply_bonuses(base, 'human')
        expected = {'str': 11, 'dex': 11, 'con': 11, 'int': 11, 'wis': 11, 'cha': 11}
        self.assertEqual(final, expected)
    
    def test_elf_bonuses(self):
        """Test elf gets +2 DEX"""
        base = {'str': 10, 'dex': 14, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        final = RacialBonusCalculator.apply_bonuses(base, 'elf')
        self.assertEqual(final['dex'], 16)
        self.assertEqual(final['str'], 10)  # Unchanged
    
    def test_dwarf_bonuses(self):
        """Test dwarf gets +2 CON"""
        base = {'str': 10, 'dex': 10, 'con': 13, 'int': 10, 'wis': 10, 'cha': 10}
        final = RacialBonusCalculator.apply_bonuses(base, 'dwarf')
        self.assertEqual(final['con'], 15)
    
    def test_unknown_race(self):
        """Test unknown race returns unchanged scores"""
        base = {'str': 10, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        final = RacialBonusCalculator.apply_bonuses(base, 'unknown')
        self.assertEqual(final, base)


class MulticlassPrerequisiteCheckerTests(TestCase):
    """Test multiclass prerequisite checking"""
    
    def test_fighter_with_strength(self):
        """Test Fighter with 13 STR can multiclass"""
        scores = {'str': 13, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('fighter', scores)
        self.assertTrue(can_multiclass)
    
    def test_fighter_with_dexterity(self):
        """Test Fighter with 13 DEX can multiclass (STR OR DEX)"""
        scores = {'str': 10, 'dex': 13, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('fighter', scores)
        self.assertTrue(can_multiclass)
    
    def test_fighter_insufficient(self):
        """Test Fighter without 13 STR or DEX cannot multiclass"""
        scores = {'str': 12, 'dex': 12, 'con': 10, 'int': 10, 'wis': 10, 'cha': 10}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('fighter', scores)
        self.assertFalse(can_multiclass)
        self.assertIn("13", reason)
    
    def test_wizard_requirement(self):
        """Test Wizard requires INT 13"""
        scores_ok = {'str': 10, 'dex': 10, 'con': 10, 'int': 13, 'wis': 10, 'cha': 10}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('wizard', scores_ok)
        self.assertTrue(can_multiclass)
        
        scores_fail = {'str': 10, 'dex': 10, 'con': 10, 'int': 12, 'wis': 10, 'cha': 10}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('wizard', scores_fail)
        self.assertFalse(can_multiclass)
        self.assertIn("INT", reason)
    
    def test_paladin_requirements(self):
        """Test Paladin requires STR 13 AND CHA 13"""
        scores_ok = {'str': 13, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 13}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('paladin', scores_ok)
        self.assertTrue(can_multiclass)
        
        scores_fail = {'str': 13, 'dex': 10, 'con': 10, 'int': 10, 'wis': 10, 'cha': 12}
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into('paladin', scores_fail)
        self.assertFalse(can_multiclass)


class CharacterBuilderServiceTests(TestCase):
    """Test Character Builder Service"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create test data
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
        
        self.background = CharacterBackground.objects.create(
            name='soldier',
            skill_proficiencies='Athletics,Intimidation'
        )
    
    def test_start_session(self):
        """Test starting a builder session"""
        session = CharacterBuilderService.start_session(self.user, 'standard_array')
        
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.current_step, 1)
        self.assertEqual(session.data['method'], 'standard_array')
        self.assertFalse(session.is_expired())
    
    def test_assign_abilities_standard_array(self):
        """Test assigning abilities with standard array"""
        session = CharacterBuilderService.start_session(self.user, 'standard_array')
        
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        success, error, data = CharacterBuilderService.assign_abilities(session, scores)
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertEqual(data['current_step'], 2)
        self.assertIn('modifiers', data)
    
    def test_assign_abilities_invalid(self):
        """Test assigning invalid abilities"""
        session = CharacterBuilderService.start_session(self.user, 'standard_array')
        
        scores = {'str': 18, 'dex': 18, 'con': 18, 'int': 18, 'wis': 18, 'cha': 18}
        success, error, data = CharacterBuilderService.assign_abilities(session, scores)
        
        self.assertFalse(success)
        self.assertIn("standard array", error)
    
    def test_choose_race(self):
        """Test choosing race"""
        session = CharacterBuilderService.start_session(self.user)
        
        # Assign abilities first
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        CharacterBuilderService.assign_abilities(session, scores)
        
        # Choose race
        success, error, data = CharacterBuilderService.choose_race(session, self.race.id)
        
        self.assertTrue(success)
        self.assertEqual(data['current_step'], 3)
        self.assertIn('racial_bonuses', data)
        # Human gets +1 to all
        self.assertEqual(data['final_scores']['strength'], 16)  # 15 + 1
    
    def test_choose_class(self):
        """Test choosing class"""
        session = CharacterBuilderService.start_session(self.user)
        
        # Set up session with abilities and race
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        CharacterBuilderService.assign_abilities(session, scores)
        CharacterBuilderService.choose_race(session, self.race.id)
        
        # Choose class
        success, error, data = CharacterBuilderService.choose_class(session, self.char_class.id)
        
        self.assertTrue(success)
        self.assertEqual(data['current_step'], 4)
        self.assertIn('hit_dice', data['class'])
    
    def test_finalize_character(self):
        """Test finalizing character creation"""
        session = CharacterBuilderService.start_session(self.user)
        
        # Complete all steps
        scores = {'str': 15, 'dex': 14, 'con': 13, 'int': 12, 'wis': 10, 'cha': 8}
        CharacterBuilderService.assign_abilities(session, scores)
        CharacterBuilderService.choose_race(session, self.race.id)
        CharacterBuilderService.choose_class(session, self.char_class.id)
        CharacterBuilderService.choose_background(session, self.background.id)
        
        # Finalize
        success, error, character = CharacterBuilderService.finalize_character(
            session, "Test Character", "LG"
        )
        
        if not success:
            print(f"Finalize failed: {error}")  # Debug output
        
        self.assertTrue(success, f"Finalize failed: {error}")
        self.assertIsNotNone(character)
        self.assertEqual(character.name, "Test Character")
        self.assertEqual(character.level, 1)
        self.assertEqual(character.user, self.user)
        
        # Verify stats were created
        self.assertTrue(hasattr(character, 'stats'))
        self.assertEqual(character.stats.strength, 16)  # 15 + 1 human
        
        # Verify session was deleted
        with self.assertRaises(CharacterBuilderSession.DoesNotExist):
            CharacterBuilderSession.objects.get(id=session.id)
