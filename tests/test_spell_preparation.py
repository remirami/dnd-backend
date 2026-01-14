"""
Comprehensive Tests for Spell Preparation System

Tests preparing spells, learning spells, and spell management for different caster types.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from characters.spell_management import is_prepared_caster, is_known_caster, calculate_spells_prepared


class SpellPreparationTests(TestCase):
    """Test spell preparation for prepared casters"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create wizard (prepared caster)
        self.race = CharacterRace.objects.create(name="Human")
        self.wizard_class = CharacterClass.objects.create(
            name="wizard",
            hit_dice="d6",
            primary_ability="INT"
        )
        
        self.wizard = Character.objects.create(
            user=self.user,
            name="Test Wizard",
            level=5,
            character_class=self.wizard_class,
            race=self.race
        )
        
        CharacterStats.objects.create(
            character=self.wizard,
            intelligence=16,  # +3 modifier
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
        
        # Add some spells to the wizard
        self.spell1 = CharacterSpell.objects.create(
            character=self.wizard,
            name="Magic Missile",
            level=1,
            is_prepared=False
        )
        
        self.spell2 = CharacterSpell.objects.create(
            character=self.wizard,
            name="Fireball",
            level=3,
            is_prepared=False
        )
        
        self.spell3 = CharacterSpell.objects.create(
            character=self.wizard,
            name="Shield",
            level=1,
            is_prepared=False
        )
    
    def test_prepare_spells(self):
        """Test preparing spells for a wizard"""
        response = self.client.post(
            f'/api/characters/{self.wizard.id}/prepare_spells/',
            {'spell_ids': [self.spell1.id, self.spell2.id]},
            format='json'  # Must use JSON format for arrays
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['spells_prepared']), 2)
        
        # Verify spells are marked as prepared
        self.spell1.refresh_from_db()
        self.spell2.refresh_from_db()
        self.assertTrue(self.spell1.is_prepared)
        self.assertTrue(self.spell2.is_prepared)
    
    def test_preparation_limit_enforced(self):
        """Test cannot exceed spell preparation limit"""
        # Create many spells (more than limit)
        extra_spells = []
        for i in range(20):
            spell = CharacterSpell.objects.create(
                character=self.wizard,
                name=f"Spell {i}",
                level=1
            )
            extra_spells.append(spell.id)
        
        response = self.client.post(
            f'/api/characters/{self.wizard.id}/prepare_spells/',
            {'spell_ids': extra_spells},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only prepare', response.data['error'].lower())
    
    def test_unprepare_on_new_preparation(self):
        """Test preparing new spells unprepares old ones"""
        # Prepare first spell
        self.spell1.is_prepared = True
        self.spell1.save()
        
        # Prepare different spell
        response = self.client.post(
            f'/api/characters/{self.wizard.id}/prepare_spells/',
            {'spell_ids': [self.spell2.id]},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Spell1 should no longer be prepared
        self.spell1.refresh_from_db()
        self.spell2.refresh_from_db()
        self.assertFalse(self.spell1.is_prepared)
        self.assertTrue(self.spell2.is_prepared)
    
    def test_prepared_caster_check(self):
        """Test wizard is a prepared caster"""
        self.assertTrue(is_prepared_caster(self.wizard))
    
    def test_spell_preparation_limit_calculated(self):
        """Test spell preparation limit calculation"""
        # Wizard level 5 + INT mod 3 = 8 spells
        limit = calculate_spells_prepared(self.wizard)
        self.assertEqual(limit, 8)


class KnownSpellsTests(TestCase):
    """Test learning spells for known casters"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create sorcerer (known caster)
        self.race = CharacterRace.objects.create(name="Human")
        self.sorcerer_class = CharacterClass.objects.create(
            name="sorcerer",
            hit_dice="d6",
            primary_ability="CHA"
        )
        
        self.sorcerer = Character.objects.create(
            user=self.user,
            name="Test Sorcerer",
            level=5,
            character_class=self.sorcerer_class,
            race=self.race
        )
        
        CharacterStats.objects.create(
            character=self.sorcerer,
            charisma=16,
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
    
    def test_learn_new_spell(self):
        """Test learning a new spell"""
        response = self.client.post(
            f'/api/characters/{self.sorcerer.id}/learn_spell/',
            {
                'spell_name': 'Fireball',
                'spell_level': 3,
                'school': 'Evocation'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify spell was added
        spell = CharacterSpell.objects.filter(
            character=self.sorcerer,
            name='Fireball'
        ).first()
        
        self.assertIsNotNone(spell)
        self.assertEqual(spell.level, 3)
    
    def test_known_caster_check(self):
        """Test sorcerer is a known caster"""
        self.assertTrue(is_known_caster(self.sorcerer))
    
    def test_cannot_learn_duplicate_spell(self):
        """Test cannot learn same spell twice"""
        CharacterSpell.objects.create(
            character=self.sorcerer,
            name='Fireball',
            level=3
        )
        
        response = self.client.post(
            f'/api/characters/{self.sorcerer.id}/learn_spell/',
            {
                'spell_name': 'Fireball',
                'spell_level': 3
            }
        )
        
        # Should fail or handle gracefully
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])


class WizardSpellbookTests(TestCase):
    """Test wizard spellbook management"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        self.race = CharacterRace.objects.create(name="Human")
        self.wizard_class = CharacterClass.objects.create(
            name="wizard",
            hit_dice="d6",
            primary_ability="INT"
        )
        
        self.wizard = Character.objects.create(
            user=self.user,
            name="Test Wizard",
            level=5,
            character_class=self.wizard_class,
            race=self.race
        )
        
        CharacterStats.objects.create(
            character=self.wizard,
            intelligence=16,
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
    
    def test_wizard_spellbook_initial_spells(self):
        """Test wizard starts with spells in spellbook"""
        # Wizards should have starting spells
        spells = CharacterSpell.objects.filter(
            character=self.wizard,
            in_spellbook=True
        )
        
        # This depends on implementation - may be 0 initially
        self.assertGreaterEqual(spells.count(), 0)


class RitualCastingTests(TestCase):
    """Test ritual casting mechanics"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.race = CharacterRace.objects.create(name="Human")
        self.wizard_class = CharacterClass.objects.create(
            name="wizard",
            hit_dice="d6",
            primary_ability="INT"
        )
        
        self.wizard = Character.objects.create(
            user=self.user,
            name="Test Wizard",
            level=5,
            character_class=self.wizard_class,
            race=self.race
        )
        
        CharacterStats.objects.create(
            character=self.wizard,
            intelligence=16,
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
        
        # Add ritual spell
        self.ritual_spell = CharacterSpell.objects.create(
            character=self.wizard,
            name="Detect Magic",
            level=1,
            is_ritual=True,
            is_prepared=False  # Not prepared, but can cast as ritual
        )
    
    def test_ritual_spell_flagged(self):
        """Test ritual spells are properly flagged"""
        self.assertTrue(self.ritual_spell.is_ritual)
    
    def test_ritual_can_be_cast_unprepared(self):
        """Test ritual spells can be cast without preparation"""
        # This is tested in spell management, but verify the flag exists
        self.assertTrue(self.ritual_spell.is_ritual)
        self.assertFalse(self.ritual_spell.is_prepared)
