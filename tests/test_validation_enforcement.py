"""
Validation Enforcement Tests

Tests that multiclass and feat prerequisites are properly enforced
and cannot be bypassed via API endpoints.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from characters.models import (
    Character, CharacterClass, CharacterRace, CharacterBackground,
    CharacterStats, Feat, CharacterFeat, CharacterClassLevel
)


class MulticlassValidationTests(TestCase):
    """Test multiclass prerequisite enforcement"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create classes
        self.fighter = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        self.wizard = CharacterClass.objects.create(
            name='wizard',
            hit_dice='d6',
            primary_ability='INT',
            saving_throw_proficiencies='INT,WIS'
        )
        
        self.monk = CharacterClass.objects.create(
            name='monk',
            hit_dice='d8',
            primary_ability='DEX',
            saving_throw_proficiencies='STR,DEX'
        )
        
        self.paladin = CharacterClass.objects.create(
            name='paladin',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='WIS,CHA'
        )
        
        # Create race and background
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.background = CharacterBackground.objects.create(
            name='soldier',
            skill_proficiencies='Athletics,Intimidation'
        )
    
    def create_character_with_stats(self, str_val=10, dex_val=10, con_val=10, 
                                   int_val=10, wis_val=10, cha_val=10):
        """Helper to create character with specific ability scores"""
        character = Character.objects.create(
            user=self.user,
            name='Test Character',
            character_class=self.fighter,
            race=self.race,
            background=self.background,
            level=1
        )
        
        CharacterStats.objects.create(
            character=character,
            strength=str_val,
            dexterity=dex_val,
            constitution=con_val,
            intelligence=int_val,
            wisdom=wis_val,
            charisma=cha_val,
            hit_points=10,
            max_hit_points=10,
            armor_class=10
        )
        
        return character
    
    def test_fighter_multiclass_with_str_13_success(self):
        """Test Fighter multiclass with STR 13 (meets OR requirement)"""
        character = self.create_character_with_stats(str_val=13, dex_val=10)
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.fighter.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('level', response.data)
    
    def test_fighter_multiclass_with_dex_13_success(self):
        """Test Fighter multiclass with DEX 13 (meets OR requirement)"""
        character = self.create_character_with_stats(str_val=10, dex_val=13)
        character.character_class = self.wizard  # Start as wizard
        character.save()
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_name': 'fighter'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have both classes now
        self.assertEqual(CharacterClassLevel.objects.filter(character=character).count(), 2)
    
    def test_fighter_multiclass_without_prereqs_fails(self):
        """Test Fighter multiclass fails without STR 13 OR DEX 13"""
        character = self.create_character_with_stats(str_val=12, dex_val=12)
        character.character_class = self.wizard
        character.save()
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_name': 'fighter'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('13', response.data['error'])
    
    def test_wizard_multiclass_without_int_13_fails(self):
        """Test Wizard multiclass fails without INT 13"""
        character = self.create_character_with_stats(int_val=12)
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.wizard.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('INT', response.data['error'])
    
    def test_monk_multiclass_with_both_prereqs_success(self):
        """Test Monk multiclass succeeds with DEX 13 AND WIS 13"""
        character = self.create_character_with_stats(dex_val=13, wis_val=13)
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.monk.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_monk_multiclass_with_only_dex_fails(self):
        """Test Monk multiclass fails with only DEX 13 (needs WIS too)"""
        character = self.create_character_with_stats(dex_val=13, wis_val=12)
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.monk.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('WIS', response.data['error'])
    
    def test_paladin_multiclass_with_both_prereqs_success(self):
        """Test Paladin multiclass succeeds with STR 13 AND CHA 13"""
        character = self.create_character_with_stats(str_val=13, cha_val=13)
        
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.paladin.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_level_up_existing_multiclass_succeeds(self):
        """Test leveling up an existing multiclass (no prereq check needed)"""
        character = self.create_character_with_stats(str_val=13, int_val=13)
        
        # First multiclass into wizard
        CharacterClassLevel.objects.create(
            character=character,
            character_class=self.wizard,
            level=1
        )
        character.level = 2
        character.save()
        
        # Now level up wizard again (should work without checking prereqs again)
        response = self.client.post(
            f'/api/characters/{character.id}/level_up/',
            {'class_id': self.wizard.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class FeatValidationTests(TestCase):
    """Test feat prerequisite enforcement"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        char_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        race = CharacterRace.objects.create(name='human', size='M', speed=30)
        background = CharacterBackground.objects.create(name='soldier')
        
        self.character = Character.objects.create(
            user=self.user,
            name='Test Fighter',
            character_class=char_class,
            race=race,
            background=background,
            level=4,
            pending_asi_levels  =[4]  # Has ASI available at level 4
        )
        
        CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
            hit_points=35,
            max_hit_points=35,
            armor_class=16
        )
        
        # Create feats
        self.basic_feat = Feat.objects.create(
            name='Tough',
            description='Your hit point maximum increases by an amount equal to twice your level',
            minimum_level=1
        )
        
        self.str_feat = Feat.objects.create(
            name='Heavy Armor Master',
            description='Reduce damage from nonmagical weapons',
            strength_requirement=13,
            minimum_level=4,
            proficiency_requirements='Heavy Armor'
        )
        
        self.high_level_feat = Feat.objects.create(
            name='Epic Boon',
            description='A gift from the gods',
            minimum_level=10
        )
    
    def test_valid_feat_selection_succeeds(self):
        """Test taking a feat with all prerequisites met"""
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'feat',
                'feat_id': self.basic_feat.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            CharacterFeat.objects.filter(
                character=self.character,
                feat=self.basic_feat
            ).exists()
        )
    
    def test_feat_below_minimum_level_fails(self):
        """Test feat requiring higher level is rejected"""
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'feat',
                'feat_id': self.high_level_feat.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('level 10', response.data['error'].lower())
    
    def test_feat_missing_ability_requirement_fails(self):
        """Test feat with unmet ability requirement is rejected"""
        # Set STR to 12 (below requirement)
        self.character.stats.strength = 12
        self.character.stats.save()
        
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'feat',
                'feat_id': self.str_feat.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Strength', response.data['error'])
    
    def test_duplicate_feat_prevention(self):
        """Test cannot take the same feat twice"""
        # Take feat first time
        CharacterFeat.objects.create(
            character=self.character,
            feat=self.basic_feat,
            level_taken=4
        )
        
        # Try to take it again
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'feat',
                'feat_id': self.basic_feat.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has', response.data['error'].lower())
    
    def test_asi_instead_of_feat_succeeds(self):
        """Test choosing ASI instead of feat"""
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'asi',
                'asi_choice': {
                    'strength': 2
                }
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify STR increased
        self.character.stats.refresh_from_db()
        self.assertEqual(self.character.stats.strength, 18)
    
    def test_ability_score_capped_at_20(self):
        """Test ability scores cannot exceed 20 via ASI"""
        # Set STR to 19
        self.character.stats.strength = 19
        self.character.stats.save()
        
        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 4,
                'choice_type': 'asi',
                'asi_choice': {
                    'strength': 2  # Should cap at 20, not go to 21
                }
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.character.stats.refresh_from_db()
        self.assertEqual(self.character.stats.strength, 20)  # Capped
