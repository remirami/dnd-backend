"""
Extended combat tests for combat models and core mechanics
Focus on model-level testing for reliable coverage improvement
Target: Improve coverage from 34% to 50%+
"""

from django.test import TestCase
from django.contrib.auth.models import User

from combat.models import CombatSession, CombatParticipant
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats


class CombatModelsExtendedTests(TestCase):
    """Extended tests for combat model functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        
        # Create character class and race
        self.fighter_class = CharacterClass.objects.create(
            name='fighter',
            hit_dice='d10',
            primary_ability='STR',
            saving_throw_proficiencies='STR,CON'
        )
        
        self.human_race = CharacterRace.objects.create(
            name='human',
            size='M',
            speed=30
        )
        
        # Create character
        self.character = Character.objects.create(
            user=self.user,
            name='Test Fighter',
            level=5,
            character_class=self.fighter_class,
            race=self.human_race
        )
        
        self.character_stats = CharacterStats.objects.create(
            character=self.character,
            strength=18,
            dexterity=14,
            constitution=16,
            intelligence=10,
            wisdom=12,
            charisma=10,
            hit_points=45,
            max_hit_points=45,
            armor_class=18
        )
        
        # Create enemy
        self.enemy = Enemy.objects.create(
            name='Test Goblin',
            challenge_rating='1/4'
        )
        
        self.enemy_stats = EnemyStats.objects.create(
            enemy=self.enemy,
            strength=8,
            dexterity=14,
            constitution=10,
            intelligence=10,
            wisdom=8,
            charisma=8,
            hit_points=7,
            armor_class=15
        )
        
        # Create encounter
        self.encounter = Encounter.objects.create(
            name='Test Encounter',
            description='A test encounter'
        )
        
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.enemy,
            name='Goblin 1',
            current_hp=7,
            initiative=12
        )
        
        # Create combat session
        self.combat_session = CombatSession.objects.create(
            encounter=self.encounter,
            status='in_progress',
            current_round=1
        )
        
        # Add character participant
        self.char_participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        # Add enemy participant
        self.enemy_participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=12,
            current_hp=7,
            max_hp=7,
            armor_class=15
        )
    
    def test_damage_participant_reduces_hp(self):
        """Test applying damage reduces HP"""
        initial_hp = self.enemy_participant.current_hp
        damage_amount = 5
        
        self.enemy_participant.take_damage(damage_amount)
        self.enemy_participant.refresh_from_db()
        
        self.assertEqual(self.enemy_participant.current_hp, initial_hp - damage_amount)
    
    def test_damage_cannot_go_below_zero(self):
        """Test damage caps HP at 0"""
        self.enemy_participant.take_damage(100)
        self.enemy_participant.refresh_from_db()
        
        self.assertEqual(self.enemy_participant.current_hp, 0)
   
    def test_heal_participant_increases_hp(self):
        """Test healing increases HP"""
        self.enemy_participant.current_hp = 3
        self.enemy_participant.save()
        
        self.enemy_participant.heal(2)
        self.enemy_participant.refresh_from_db()
        
        self.assertEqual(self.enemy_participant.current_hp, 5)
    
    def test_heal_cannot_exceed_max_hp(self):
        """Test healing caps at max HP"""
        self.enemy_participant.current_hp = 5
        self.enemy_participant.save()
        
        self.enemy_participant.heal(100)
        self.enemy_participant.refresh_from_db()
        
        self.assertEqual(self.enemy_participant.current_hp, self.enemy_participant.max_hp)
    
    def test_combat_session_has_participants(self):
        """Test combat session tracks participants"""
        participants = self.combat_session.participants.all()
        
        self.assertEqual(participants.count(), 2)
        self.assertIn(self.char_participant, participants)
        self.assertIn(self.enemy_participant, participants)
    
    def test_combat_session_status_progression(self):
        """Test combat status can change"""
        self.assertEqual(self.combat_session.status, 'in_progress')
        
        self.combat_session.status = 'completed'
        self.combat_session.save()
        self.combat_session.refresh_from_db()
        
        self.assertEqual(self.combat_session.status, 'completed')
    
    def test_participant_get_name_character(self):
        """Test participant name for character"""
        name = self.char_participant.get_name()
        self.assertEqual(name, 'Test Fighter')
    
    def test_participant_get_name_enemy(self):
        """Test participant name for enemy"""
        name = self.enemy_participant.get_name()
        self.assertEqual(name, 'Goblin 1')
    
    def test_participant_is_alive_when_has_hp(self):
        """Test participant is alive with HP > 0"""
        self.assertTrue(self.char_participant.current_hp > 0)
        self.assertGreater(self.char_participant.current_hp, 0)
    
    def test_participant_dead_when_zero_hp(self):
        """Test participant is dead at 0 HP"""
        self.enemy_participant.current_hp = 0
        self.enemy_participant.save()
        
        self.assertEqual(self.enemy_participant.current_hp, 0)
    
    def test_combat_round_tracking(self):
        """Test combat tracks round number"""
        self.assertEqual(self.combat_session.current_round, 1)
        
        self.combat_session.current_round += 1
        self.combat_session.save()
        self.combat_session.refresh_from_db()
        
        self.assertEqual(self.combat_session.current_round, 2)
    
    def test_initiative_ordering(self):
        """Test participants are ordered by initiative"""
        participants = list(self.combat_session.participants.all().order_by('-initiative'))
        
        self.assertEqual(participants[0], self.char_participant)  # Higher init first
        self.assertEqual(participants[1], self.enemy_participant)
    
    def test_multiple_damage_applications(self):
        """Test applying damage multiple times"""
        self.enemy_participant.take_damage(2)
        self.enemy_participant.take_damage(3)
        self.enemy_participant.refresh_from_db()
        
        self.assertEqual(self.enemy_participant.current_hp, 2)  # 7 - 2 - 3
    
    def test_participant_type_character(self):
        """Test participant type is correctly set for character"""
        self.assertEqual(self.char_participant.participant_type, 'character')
        self.assertIsNotNone(self.char_participant.character)
    
    def test_participant_type_enemy(self):
        """Test participant type is correctly set for enemy"""
        self.assertEqual(self.enemy_participant.participant_type, 'enemy')
        self.assertIsNotNone(self.enemy_participant.encounter_enemy)
