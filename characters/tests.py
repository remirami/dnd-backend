from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground
)


class CharacterModelTests(TestCase):
    """Test character model functionality"""
    
    def setUp(self):
        # Create reference data
        self.character_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        self.race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30,
            ability_score_increases='STR+1,DEX+1'
        )
        self.background = CharacterBackground.objects.create(
            name='soldier',
            skill_proficiencies='Athletics,Intimidation',
            languages=0
        )
    
    def test_create_character(self):
        """Test creating a character"""
        character = Character.objects.create(
            name='Test Fighter',
            level=1,
            character_class=self.character_class,
            race=self.race,
            background=self.background,
            alignment='NG'
        )
        
        self.assertEqual(character.name, 'Test Fighter')
        self.assertEqual(character.level, 1)
        self.assertEqual(character.proficiency_bonus, 2)  # Level 1 = +2
    
    def test_proficiency_bonus_calculation(self):
        """Test proficiency bonus calculation based on level"""
        character = Character.objects.create(
            name='Test Character',
            level=1,
            character_class=self.character_class,
            race=self.race
        )
        self.assertEqual(character.proficiency_bonus, 2)  # Level 1-4
        
        character.level = 5
        character.save()
        self.assertEqual(character.proficiency_bonus, 3)  # Level 5-8
        
        character.level = 9
        character.save()
        self.assertEqual(character.proficiency_bonus, 4)  # Level 9-12
        
        character.level = 13
        character.save()
        self.assertEqual(character.proficiency_bonus, 5)  # Level 13-16
        
        character.level = 17
        character.save()
        self.assertEqual(character.proficiency_bonus, 6)  # Level 17-20
    
    def test_character_stats_modifiers(self):
        """Test ability score modifier calculations"""
        character = Character.objects.create(
            name='Test Character',
            level=1,
            character_class=self.character_class,
            race=self.race
        )
        
        stats = CharacterStats.objects.create(
            character=character,
            strength=16,
            dexterity=14,
            constitution=12,
            intelligence=10,
            wisdom=8,
            charisma=6,
            hit_points=10,
            max_hit_points=10,
            armor_class=16
        )
        
        self.assertEqual(stats.strength_modifier, 3)  # (16-10)/2 = 3
        self.assertEqual(stats.dexterity_modifier, 2)  # (14-10)/2 = 2
        self.assertEqual(stats.constitution_modifier, 1)  # (12-10)/2 = 1
        self.assertEqual(stats.intelligence_modifier, 0)  # (10-10)/2 = 0
        self.assertEqual(stats.wisdom_modifier, -1)  # (8-10)/2 = -1
        self.assertEqual(stats.charisma_modifier, -2)  # (6-10)/2 = -2


class CharacterAPITests(TestCase):
    """Test character API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create and authenticate user
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        
        # Create reference data
        self.character_class = CharacterClass.objects.create(
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
        
        # Create character with stats
        self.character = Character.objects.create(
            user=self.user,  # Link character to user
            name='Test Fighter',
            level=1,
            character_class=self.character_class,
            race=self.race,
            alignment='NG'
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=12,
            charisma=10,
            hit_points=12,
            max_hit_points=12,
            armor_class=16
        )
    
    def test_list_characters(self):
        """Test listing all characters"""
        response = self.client.get('/api/characters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_character_detail(self):
        """Test retrieving a specific character"""
        response = self.client.get(f'/api/characters/{self.character.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Fighter')
        self.assertIn('stats', response.data)
    
    def test_create_character(self):
        """Test creating a new character"""
        data = {
            'name': 'New Fighter',
            'level': 1,
            'character_class_id': self.character_class.id,
            'race_id': self.race.id,
            'alignment': 'CG'
        }
        response = self.client.post('/api/characters/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Fighter')
    
    def test_level_up_endpoint(self):
        """Test level up custom action"""
        response = self.client.post(f'/api/characters/{self.character.id}/level_up/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('leveled up', response.data['message'].lower())
        
        # Verify level increased
        self.character.refresh_from_db()
        self.assertEqual(self.character.level, 2)
    
    def test_take_damage_endpoint(self):
        """Test take damage custom action"""
        initial_hp = self.stats.hit_points
        damage = 5
        
        response = self.client.post(
            f'/api/characters/{self.character.id}/take_damage/',
            {'damage': damage},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('took', response.data['message'].lower())
        
        # Verify HP decreased
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.hit_points, initial_hp - damage)
    
    def test_heal_endpoint(self):
        """Test heal custom action"""
        # First damage the character
        self.stats.hit_points = 5
        self.stats.save()
        
        heal_amount = 3
        response = self.client.post(
            f'/api/characters/{self.character.id}/heal/',
            {'amount': heal_amount},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('healed', response.data['message'].lower())
        
        # Verify HP increased
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.hit_points, 8)
    
    def test_heal_cannot_exceed_max_hp(self):
        """Test that healing cannot exceed max HP"""
        self.stats.hit_points = 10
        self.stats.max_hit_points = 12
        self.stats.save()
        
        response = self.client.post(
            f'/api/characters/{self.character.id}/heal/',
            {'amount': 10},  # Would exceed max HP
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify HP capped at max
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.hit_points, 12)
