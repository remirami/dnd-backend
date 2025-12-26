from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import CombatSession, CombatParticipant, CombatAction
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats


class CombatModelTests(TestCase):
    """Test combat model functionality"""
    
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
            speed=30
        )
        
        # Create character
        self.character = Character.objects.create(
            name='Test Fighter',
            level=5,
            character_class=self.character_class,
            race=self.race
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
            status='preparing'
        )
    
    def test_create_combat_session(self):
        """Test creating a combat session"""
        self.assertEqual(self.combat_session.status, 'preparing')
        self.assertEqual(self.combat_session.current_round, 0)
    
    def test_add_character_participant(self):
        """Test adding a character to combat"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=0,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        self.assertEqual(participant.get_name(), 'Test Fighter')
        self.assertEqual(participant.current_hp, 45)
        self.assertTrue(participant.is_active)
    
    def test_add_enemy_participant(self):
        """Test adding an enemy to combat"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=0,
            current_hp=7,
            max_hp=7,
            armor_class=15
        )
        
        self.assertEqual(participant.get_name(), 'Goblin 1')
        self.assertEqual(participant.current_hp, 7)
    
    def test_participant_take_damage(self):
        """Test participant taking damage"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=0,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        new_hp = participant.take_damage(10)
        self.assertEqual(new_hp, 35)
        self.assertTrue(participant.is_active)
        
        # Test going to 0 HP
        new_hp = participant.take_damage(35)
        self.assertEqual(new_hp, 0)
        self.assertFalse(participant.is_active)
    
    def test_participant_heal(self):
        """Test participant healing"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=0,
            current_hp=20,
            max_hp=45,
            armor_class=18
        )
        
        new_hp = participant.heal(10)
        self.assertEqual(new_hp, 30)
        self.assertTrue(participant.is_active)
        
        # Test healing beyond max
        new_hp = participant.heal(20)
        self.assertEqual(new_hp, 45)  # Capped at max
    
    def test_get_ability_modifier(self):
        """Test getting ability modifier"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=0,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        str_mod = participant.get_ability_modifier('STR')
        self.assertEqual(str_mod, 4)  # (18-10)/2 = 4
        
        dex_mod = participant.get_ability_modifier('DEX')
        self.assertEqual(dex_mod, 2)  # (14-10)/2 = 2


class CombatAPITests(TestCase):
    """Test combat API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
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
        
        # Create character
        self.character = Character.objects.create(
            name='Test Fighter',
            level=5,
            character_class=self.character_class,
            race=self.race
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
            name='Test Encounter'
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
            status='preparing'
        )
    
    def test_create_combat_session(self):
        """Test creating a combat session via API"""
        encounter = Encounter.objects.create(name='New Encounter')
        response = self.client.post('/api/combat/sessions/', {
            'encounter_id': encounter.id,
            'status': 'preparing'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['encounter']['name'], 'New Encounter')
    
    def test_add_character_participant(self):
        """Test adding a character to combat via API"""
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/add_participant/',
            {
                'participant_type': 'character',
                'character_id': self.character.id
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('added to combat', response.data['message'])
    
    def test_roll_initiative(self):
        """Test rolling initiative"""
        # Add participants first
        CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=0,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/roll_initiative/',
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_start_combat(self):
        """Test starting combat"""
        # Add participant first
        CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/start/',
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.combat_session.refresh_from_db()
        self.assertEqual(self.combat_session.status, 'active')
        self.assertEqual(self.combat_session.current_round, 1)
    
    def test_cast_spell(self):
        """Test casting a spell"""
        # Add participants and start combat
        participant1 = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        participant2 = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=10,
            current_hp=7,
            max_hp=7,
            armor_class=15
        )
        
        self.combat_session.status = 'active'
        self.combat_session.current_round = 1
        self.combat_session.current_turn_index = 0
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/cast_spell/',
            {
                'caster_id': participant1.id,
                'target_id': participant2.id,
                'spell_name': 'Fireball',
                'spell_level': 3,
                'damage_string': '8d6',
                'save_type': 'DEX',
                'save_dc': 15
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('casts', response.data['message'].lower())
        self.assertIn('save_roll', response.data)
    
    def test_saving_throw(self):
        """Test making a saving throw"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        self.combat_session.status = 'active'
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/saving_throw/',
            {
                'participant_id': participant.id,
                'save_type': 'DEX',
                'save_dc': 15
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('save_total', response.data)
        self.assertIn('save_success', response.data)
    
    def test_add_condition(self):
        """Test adding a condition to a participant"""
        from bestiary.models import Condition
        
        # Create a condition
        condition = Condition.objects.create(
            name='poisoned',
            description='A poisoned creature has disadvantage on attack rolls and ability checks.'
        )
        
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        response = self.client.post(
            f'/api/combat/participants/{participant.id}/add_condition/',
            {'condition_id': condition.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        self.assertTrue(participant.conditions.filter(id=condition.id).exists())
    
    def test_remove_condition(self):
        """Test removing a condition from a participant"""
        from bestiary.models import Condition
        
        # Create a condition
        condition = Condition.objects.create(
            name='stunned',
            description='A stunned creature is incapacitated.'
        )
        
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        # Add condition first
        participant.conditions.add(condition)
        
        response = self.client.post(
            f'/api/combat/participants/{participant.id}/remove_condition/',
            {'condition_id': condition.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        self.assertFalse(participant.conditions.filter(id=condition.id).exists())
