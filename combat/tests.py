from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from bestiary.models import Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from encounters.models import Encounter, EncounterEnemy

from .models import CombatParticipant, CombatSession


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
        
        new_hp, _ = participant.take_damage(10)
        self.assertEqual(new_hp, 35)
        self.assertTrue(participant.is_active)
        
        # Test going to 0 HP
        new_hp, _ = participant.take_damage(35)
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

    def test_cannot_heal_dead_enemy(self):
        """Test that defeated enemies (0 HP) cannot be healed or reactivated"""
        enemy = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            name='Goblin',
            initiative=0,
            current_hp=0,
            max_hp=15,
            armor_class=12,
            is_active=False
        )
        
        new_hp = enemy.heal(10)
        self.assertEqual(new_hp, 0)
        self.assertEqual(enemy.current_hp, 0)
        self.assertFalse(enemy.is_active)
    
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
        
        # Create reference data - wizard for spell casting
        self.character_class = CharacterClass.objects.create(
            name='wizard',
            hit_dice='d6',
            primary_ability='INT',
            saving_throw_proficiencies='INT,WIS'
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
        # Add character participant
        CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        # Add enemy participant (required by start endpoint)
        CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=12,
            current_hp=7,
            max_hp=7,
            armor_class=15
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
        # Add Fireball spell to character
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(
            character=self.character,
            name='Fireball',
            level=3,
            school='evocation',
            is_prepared=True
        )
        
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
    
    def test_death_save(self):
        """Test death saving throw"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=0,  # Unconscious
            max_hp=45,
            armor_class=18
        )
        
        self.combat_session.status = 'active'
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/death_save/',
            {'participant_id': participant.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success', response.data)
        self.assertIn('death_save_successes', response.data)
        self.assertIn('death_save_failures', response.data)
    
    def test_concentration_check(self):
        """Test concentration check"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18,
            is_concentrating=True,
            concentration_spell='Haste'
        )
        
        self.combat_session.status = 'active'
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/check_concentration/',
            {
                'participant_id': participant.id,
                'damage_amount': 15
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('concentration_broken', response.data)
        self.assertIn('save_roll', response.data)
        self.assertIn('save_dc', response.data)
    
    def test_opportunity_attack(self):
        """Test opportunity attack"""
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
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/opportunity_attack/',
            {
                'attacker_id': participant1.id,
                'target_id': participant2.id,
                'attack_name': 'Opportunity Attack'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('hit', response.data)
        participant1.refresh_from_db()
        self.assertTrue(participant1.reaction_used)
    
    def test_legendary_action(self):
        """Test legendary action"""
        participant = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=15,
            current_hp=100,
            max_hp=100,
            armor_class=18,
            legendary_actions_max=3,
            legendary_actions_remaining=3
        )
        
        self.combat_session.status = 'active'
        self.combat_session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/legendary_action/',
            {
                'participant_id': participant.id,
                'action_cost': 1,
                'action_name': 'Wing Attack'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('legendary_actions_remaining', response.data)
        participant.refresh_from_db()
        self.assertEqual(participant.legendary_actions_remaining, 2)


class EmptyPreparingCombatCleanupTests(TestCase):
    """Tests for auto-cleanup and exclusion of abandoned empty preparing sessions"""

    def setUp(self):
        from django.contrib.auth.models import User
        self.client = APIClient()
        self.user = User.objects.create_user(username='tactician', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_empty_preparing_session_purged_on_new_create(self):
        """Creating an empty preparing session and then creating another purges the first empty one"""
        # First session created (empty)
        res1 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        session1_id = res1.data['id']
        self.assertTrue(CombatSession.objects.filter(id=session1_id).exists())

        # Second session created (should auto-purge session1 because it had 0 participants)
        res2 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        session2_id = res2.data['id']

        # session1 should be deleted, session2 should exist
        self.assertFalse(CombatSession.objects.filter(id=session1_id).exists())
        self.assertTrue(CombatSession.objects.filter(id=session2_id).exists())

    def test_empty_preparing_session_not_in_list(self):
        """Listing sessions excludes and deletes abandoned empty preparing sessions"""
        res1 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        session_id = res1.data['id']

        # Query list
        list_res = self.client.get('/api/combat/sessions/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        results = list_res.data.get('results', list_res.data) if isinstance(list_res.data, dict) else list_res.data
        ids_in_list = [s['id'] for s in results]
        self.assertNotIn(session_id, ids_in_list)
        # Verify it was purged from the database
        self.assertFalse(CombatSession.objects.filter(id=session_id).exists())

    def test_empty_preparing_session_does_not_block_active_limit(self):
        """Empty preparing sessions do not count against the 2 active combats limit"""
        # Create 2 empty sessions sequentially (each cleans up the previous empty one)
        res1 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        res3 = self.client.post('/api/combat/sessions/', {}, format='json')
        self.assertEqual(res3.status_code, status.HTTP_201_CREATED)


class CombatItemAndFeatureTests(TestCase):
    """Tests for using supplies (potions) and class features (Lay on Hands) in combat"""

    def setUp(self):
        from django.contrib.auth.models import User
        from characters.models import Character, CharacterClass, CharacterFeature, CharacterRace
        self.client = APIClient()
        self.user = User.objects.create_user(username='paladin_tester', password='password123')
        self.client.force_authenticate(user=self.user)

        self.paladin_class = CharacterClass.objects.create(name='paladin', hit_dice='d10')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.paladin = Character.objects.create(
            user=self.user,
            name='Sir Kaelen',
            level=2,
            character_class=self.paladin_class,
            race=self.race
        )
        CharacterFeature.objects.create(
            character=self.paladin,
            name='Lay on Hands',
            feature_type='class',
            description='Pool of healing power.'
        )

        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        self.paladin_part = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.paladin,
            initiative=15,
            current_hp=10,
            max_hp=20,
            armor_class=16,
            attacks_remaining=1,
            action_used=False
        )
        self.goblin_part = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin',
            initiative=10,
            current_hp=0,
            max_hp=12,
            armor_class=12,
            is_active=False
        )

    def test_use_item_potion_heals_self_and_consumes_action(self):
        """Drinking a healing potion heals the drinker and consumes action"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_item/',
            {
                'participant_id': self.paladin_part.id,
                'item_name': 'Potion of Healing'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.paladin_part.refresh_from_db()
        self.assertTrue(self.paladin_part.action_used)
        self.assertEqual(self.paladin_part.attacks_remaining, 0)
        self.assertGreater(self.paladin_part.current_hp, 10)

    def test_use_item_cannot_heal_enemy(self):
        """Supplies cannot be used on an enemy"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_item/',
            {
                'participant_id': self.paladin_part.id,
                'target_id': self.goblin_part.id,
                'item_name': 'Potion of Healing'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("hostile enemy", response.data['error'])

    def test_lay_on_hands_heals_and_tracks_pool(self):
        """Paladin uses Lay on Hands to heal self, pool reduces correctly"""
        max_pool = self.paladin_part.get_lay_on_hands_pool()
        self.assertEqual(max_pool, 10)  # Level 2 Paladin = 10 HP pool

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/use_feature/',
            {
                'participant_id': self.paladin_part.id,
                'target_id': self.paladin_part.id,
                'feature_name': 'Lay on Hands',
                'amount': 6
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['remaining_pool'], 4)

        self.paladin_part.refresh_from_db()
        self.assertEqual(self.paladin_part.current_hp, 16)  # 10 + 6
        self.assertTrue(self.paladin_part.action_used)
        self.assertEqual(self.paladin_part.attacks_remaining, 0)


class AoESpellCombatTests(TestCase):
    """Test 5e AoE spell multi-target targeting and environmental effects"""

    def setUp(self):
        self.client = APIClient()
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        self.wizard_class = CharacterClass.objects.create(name='wizard', hit_dice='d6', primary_ability='INT')
        self.race = CharacterRace.objects.create(name='elf', speed=30)
        self.character = Character.objects.create(name='Mage', level=5, character_class=self.wizard_class, race=self.race)
        self.stats = CharacterStats.objects.create(
            character=self.character,
            intelligence=16,
            spell_save_dc=14,
            spell_attack_bonus=6,
            hit_points=25,
            max_hit_points=25,
            armor_class=12,
            spell_slots={'1': 4, '2': 3, '3': 2},
            expended_spell_slots={}
        )
        self.caster = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            name='Mage',
            initiative=20,
            current_hp=25,
            max_hp=25,
            armor_class=12,
            position_x=10,
            position_y=15,
            attacks_remaining=1,
            action_used=False
        )
        self.goblin1 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin 1',
            initiative=15,
            current_hp=15,
            max_hp=15,
            armor_class=13,
            position_x=20,
            position_y=15
        )
        self.goblin2 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin 2',
            initiative=14,
            current_hp=15,
            max_hp=15,
            armor_class=13,
            position_x=25,
            position_y=15
        )

    def test_aoe_fireball_multi_target_and_save_resolution(self):
        """Fireball affects multiple targets with save and damage halving/full damage"""
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.character, name='Fireball', level=3, is_prepared=True)

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_ids': [self.goblin1.id, self.goblin2.id],
                'spell_name': 'Fireball',
                'spell_level': 3,
                'save_type': 'DEX',
                'save_dc': 14,
                'damage_string': '8d6',
                'half_on_save': True
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data['target_results']), 2)
        # Both goblins should have taken damage
        self.goblin1.refresh_from_db()
        self.goblin2.refresh_from_db()
        self.assertLess(self.goblin1.current_hp, 15)
        self.assertLess(self.goblin2.current_hp, 15)

    def test_aoe_persistent_environmental_effect_web(self):
        """Web creates a persistent terrain environmental effect on grid"""
        from characters.models import CharacterSpell
        from combat.models import EnvironmentalEffect
        CharacterSpell.objects.create(character=self.character, name='Web', level=2, is_prepared=True)

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_ids': [self.goblin1.id],
                'spell_name': 'Web',
                'spell_level': 2,
                'save_type': 'DEX',
                'save_dc': 14,
                'requires_concentration': True
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eff = EnvironmentalEffect.objects.filter(combat_session=self.session, effect_type='terrain').first()
        self.assertIsNotNone(eff)
        self.assertEqual(eff.terrain_type, 'thick_vegetation')
        self.assertEqual(eff.cover_area_radius, 10)


