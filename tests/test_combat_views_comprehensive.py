"""
Comprehensive tests for Combat Views API endpoints.

Tests combat session management matching actual API implementation.
"""
from django.test import TestCase  
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from bestiary.models import Enemy, EnemyStats
from encounters.models import Encounter, EncounterEnemy


class CombatSessionAPITests(TestCase):
    """Test combat session CRUD operations"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create character
        race = CharacterRace.objects.create(name="Human")
        char_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.character = Character.objects.create(
            user=self.user,
            name="Test Fighter",
            level=5,
            character_class=char_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=14,
            constitution=15,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        # Create enemy for combat tests
        self.enemy = Enemy.objects.create(
            name='Test Goblin',
            challenge_rating='1/4'
        )
        EnemyStats.objects.create(
            enemy=self.enemy,
            strength=8, dexterity=14, constitution=10,
            intelligence=10, wisdom=8, charisma=8,
            hit_points=7, armor_class=15
        )
        self.encounter = Encounter.objects.create(name='Test Encounter')
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.enemy,
            name='Goblin 1',
            current_hp=7,
            initiative=12
        )
    
    def test_create_combat_session(self):
        """Test creating a new combat session"""
        response = self.client.post('/api/combat/sessions/', {
            'status': 'preparing'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'preparing')
    
    def test_list_combat_sessions(self):
        """Test listing combat sessions"""
        CombatSession.objects.create(status='preparing')
        CombatSession.objects.create(status='active')
        
        response = self.client.get('/api/combat/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_get_combat_session_detail(self):
        """Test retrieving a specific combat session"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.get(f'/api/combat/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], session.id)
    
    def test_add_participant_to_session(self):
        """Test adding a participant to combat"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {
                'participant_type': 'character',
                'character_id': self.character.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('participant', response.data)

    def test_remove_participant_from_session(self):
        """Test removing a participant from combat (de-selecting character)"""
        session = CombatSession.objects.create(status='preparing')
        add_res = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {
                'participant_type': 'character',
                'character_id': self.character.id
            }
        )
        self.assertEqual(add_res.status_code, status.HTTP_200_OK)
        self.assertEqual(session.participants.count(), 1)

        # Remove by character_id
        remove_res = self.client.post(
            f'/api/combat/sessions/{session.id}/remove_participant/',
            {'character_id': self.character.id}
        )
        self.assertEqual(remove_res.status_code, status.HTTP_200_OK)
        self.assertEqual(session.participants.count(), 0)
    
    def test_start_combat_with_participants(self):
        """Test starting combat with participants"""
        session = CombatSession.objects.create(
            status='preparing',
            encounter=self.encounter
        )
        
        # Add character participant
        CombatParticipant.objects.create(
            combat_session=session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        # Add enemy participant (required by start endpoint)
        CombatParticipant.objects.create(
            combat_session=session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=12,
            current_hp=7,
            max_hp=7,
            armor_class=15
        )
        
        response = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session']['status'], 'active')
    
    def test_start_combat_no_participants_fails(self):
        """Test starting combat without participants fails"""
        session = CombatSession.objects.create(status='preparing')
        
        response = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_character_addition_prevented(self):
        """Test that adding the same character twice to a session is rejected"""
        session = CombatSession.objects.create(status='preparing')
        
        # Add character first time
        res1 = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {'participant_type': 'character', 'character_id': self.character.id}
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Attempt to add same character a second time
        res2 = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {'participant_type': 'character', 'character_id': self.character.id}
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already in this combat session", res2.data.get('error', ''))

    def test_party_participant_limit_enforced(self):
        """Test that party limit of 6 characters is strictly enforced"""
        session = CombatSession.objects.create(status='preparing')
        race = CharacterRace.objects.first()
        char_class = CharacterClass.objects.first()

        # Create and add 6 distinct characters
        characters = []
        for i in range(6):
            c = Character.objects.create(
                user=self.user,
                name=f"Hero {i+1}",
                level=1,
                character_class=char_class,
                race=race
            )
            CharacterStats.objects.create(
                character=c,
                strength=10, dexterity=10, constitution=10,
                max_hit_points=10, hit_points=10, armor_class=10
            )
            characters.append(c)
            res = self.client.post(
                f'/api/combat/sessions/{session.id}/add_participant/',
                {'participant_type': 'character', 'character_id': c.id}
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(session.participants.filter(participant_type='character').count(), 6)

        # 7th character must be rejected
        c7 = Character.objects.create(
            user=self.user,
            name="Hero 7",
            level=1,
            character_class=char_class,
            race=race
        )
        CharacterStats.objects.create(
            character=c7,
            strength=10, dexterity=10, constitution=10,
            max_hit_points=10, hit_points=10, armor_class=10
        )
        res7 = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {'participant_type': 'character', 'character_id': c7.id}
        )
        self.assertEqual(res7.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Party roster is full", res7.data.get('error', ''))

    def test_enemy_participant_limit_enforced(self):
        """Test that enemy limit of 10 enemies is strictly enforced"""
        session = CombatSession.objects.create(status='preparing')

        # Add 10 enemies in practice mode
        for i in range(10):
            res = self.client.post(
                f'/api/combat/sessions/{session.id}/add_participant/',
                {
                    'participant_type': 'enemy',
                    'enemy_id': self.enemy.id,
                    'enemy_name': f"Goblin {i+1}"
                }
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(session.participants.filter(participant_type='enemy').count(), 10)

        # 11th enemy must be rejected
        res11 = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {
                'participant_type': 'enemy',
                'enemy_id': self.enemy.id,
                'enemy_name': "Goblin 11"
            }
        )
        self.assertEqual(res11.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Enemy roster is full", res11.data.get('error', ''))

    def test_total_participant_limit_enforced(self):
        """Test that total participant limit of 16 is strictly enforced"""
        session = CombatSession.objects.create(status='preparing')
        race = CharacterRace.objects.first()
        char_class = CharacterClass.objects.first()

        # Add 6 characters directly
        for i in range(6):
            c = Character.objects.create(
                user=self.user,
                name=f"Party {i+1}",
                level=1,
                character_class=char_class,
                race=race
            )
            stats = CharacterStats.objects.create(
                character=c,
                strength=10, dexterity=10, constitution=10,
                max_hit_points=10, hit_points=10, armor_class=10
            )
            CombatParticipant.objects.create(
                combat_session=session,
                participant_type='character',
                character=c,
                initiative=10,
                current_hp=10,
                max_hp=10,
                armor_class=10
            )

        # Add 10 enemies directly
        for i in range(10):
            CombatParticipant.objects.create(
                combat_session=session,
                participant_type='enemy',
                name=f"Monster {i+1}",
                initiative=10,
                current_hp=10,
                max_hp=10,
                armor_class=10
            )

        self.assertEqual(session.participants.count(), 16)

        # Attempt to add any 17th participant via API
        c17 = Character.objects.create(
            user=self.user,
            name="Party 7",
            level=1,
            character_class=char_class,
            race=race
        )
        CharacterStats.objects.create(
            character=c17,
            strength=10, dexterity=10, constitution=10,
            max_hit_points=10, hit_points=10, armor_class=10
        )
        res = self.client.post(
            f'/api/combat/sessions/{session.id}/add_participant/',
            {'participant_type': 'character', 'character_id': c17.id}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Encounter participant limit reached", res.data.get('error', ''))

    def test_start_combat_exceeding_limits_fails(self):
        """Test starting combat with more than 16 participants fails"""
        session = CombatSession.objects.create(status='preparing')

        # Directly insert 17 participants
        for i in range(17):
            CombatParticipant.objects.create(
                combat_session=session,
                participant_type='enemy',
                name=f"Monster {i+1}",
                initiative=10,
                current_hp=10,
                max_hp=10,
                armor_class=10
            )

        response = self.client.post(f'/api/combat/sessions/{session.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceed limit of 16", response.data.get('error', ''))


