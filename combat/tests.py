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

    def test_cantrip_scaling_eldritch_blast(self):
        """Test that Eldritch Blast cantrip scales with character level (5e rules)"""
        from characters.models import CharacterSpell
        
        # Level 20 Warlock character
        warlock = Character.objects.create(
            name='Level 20 Warlock',
            level=20,
            character_class=self.character_class,
            race=self.race
        )
        CharacterSpell.objects.create(
            character=warlock,
            name='Eldritch Blast',
            level=0,
            school='evocation',
            is_prepared=True
        )

        p_warlock = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='character',
            character=warlock,
            initiative=20,
            current_hp=100,
            max_hp=100,
            armor_class=15
        )
        p_target = CombatParticipant.objects.create(
            combat_session=self.combat_session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=5,
            current_hp=200,
            max_hp=200,
            armor_class=10
        )

        self.combat_session.status = 'active'
        self.combat_session.current_round = 1
        self.combat_session.current_turn_index = 0
        self.combat_session.save()

        # Cast without damage_string: backend should resolve 4d10 for lvl 20
        response = self.client.post(
            f'/api/combat/sessions/{self.combat_session.id}/cast_spell/',
            {
                'caster_id': p_warlock.id,
                'target_id': p_target.id,
                'spell_name': 'Eldritch Blast',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 4d10 produces damage between 4 and 40 (or 80 on critical)
        self.assertGreaterEqual(response.data['damage'], 4)
        self.assertLessEqual(response.data['damage'], 80)
        self.assertIn('eldritch blast', response.data['message'].lower())

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


class CantripScalingTests(TestCase):
    """Test comprehensive 5e cantrip scaling based on character level and CR"""

    def setUp(self):
        self.client = APIClient()
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        self.warlock_class = CharacterClass.objects.create(name='warlock', hit_dice='d8', primary_ability='CHA')
        self.tiefling = CharacterRace.objects.create(name='tiefling', speed=30)
        
        # Level 20 Warlock
        self.char_lvl20 = Character.objects.create(name='Epic Warlock', level=20, character_class=self.warlock_class, race=self.tiefling)
        self.stats_lvl20 = CharacterStats.objects.create(
            character=self.char_lvl20,
            charisma=20,
            spell_save_dc=19,
            spell_attack_bonus=11,
            hit_points=150,
            max_hit_points=150,
            armor_class=15,
            spell_slots={'5': 4},
            expended_spell_slots={}
        )
        self.caster_lvl20 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.char_lvl20,
            name='Epic Warlock',
            initiative=20,
            current_hp=150,
            max_hp=150,
            armor_class=15,
            attacks_remaining=1,
            action_used=False,
            position_x=10,
            position_y=15
        )

        # Level 5 Wizard
        self.wizard_class = CharacterClass.objects.create(name='wizard', hit_dice='d6', primary_ability='INT')
        self.char_lvl5 = Character.objects.create(name='Adept Mage', level=5, character_class=self.wizard_class, race=self.tiefling)
        self.stats_lvl5 = CharacterStats.objects.create(
            character=self.char_lvl5,
            intelligence=18,
            spell_save_dc=15,
            spell_attack_bonus=7,
            hit_points=32,
            max_hit_points=32,
            armor_class=12,
            spell_slots={'1': 4, '2': 3, '3': 2},
            expended_spell_slots={}
        )
        self.caster_lvl5 = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.char_lvl5,
            name='Adept Mage',
            initiative=18,
            current_hp=32,
            max_hp=32,
            armor_class=12,
            attacks_remaining=1,
            action_used=False,
            position_x=10,
            position_y=15
        )

        # Target 1: Uninjured Orc (Full HP)
        self.orc_full = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Orc Warrior',
            initiative=10,
            current_hp=45,
            max_hp=45,
            armor_class=13,
            position_x=10,
            position_y=10
        )

        # Target 2: Injured Orc (Damaged)
        self.orc_injured = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Injured Orc',
            initiative=9,
            current_hp=20,
            max_hp=45,
            armor_class=13,
            position_x=15,
            position_y=10
        )

    def test_cantrip_formula_scaling_levels(self):
        """Test scale_cantrip_damage unit scaling across all tiers (1, 5, 11, 17)"""
        from combat.spell_rules import scale_cantrip_damage

        # Level 1-4: 1x dice
        self.assertEqual(scale_cantrip_damage('1d10', 1), '1d10')
        self.assertEqual(scale_cantrip_damage('1d8', 4), '1d8')

        # Level 5-10: 2x dice
        self.assertEqual(scale_cantrip_damage('1d10', 5), '2d10')
        self.assertEqual(scale_cantrip_damage('1d8', 10), '2d8')
        self.assertEqual(scale_cantrip_damage('1d6', 5), '2d6')
        self.assertEqual(scale_cantrip_damage('1d12', 8), '2d12')
        self.assertEqual(scale_cantrip_damage('1d4', 6), '2d4')

        # Level 11-16: 3x dice
        self.assertEqual(scale_cantrip_damage('1d10', 11), '3d10')
        self.assertEqual(scale_cantrip_damage('1d8', 14), '3d8')
        self.assertEqual(scale_cantrip_damage('1d6', 16), '3d6')

        # Level 17-20: 4x dice
        self.assertEqual(scale_cantrip_damage('1d10', 17), '4d10')
        self.assertEqual(scale_cantrip_damage('1d10', 20), '4d10')
        self.assertEqual(scale_cantrip_damage('1d8', 20), '4d8')
        self.assertEqual(scale_cantrip_damage('1d6', 20), '4d6')
        self.assertEqual(scale_cantrip_damage('1d12', 20), '4d12')
        self.assertEqual(scale_cantrip_damage('1d4', 20), '4d4')

    def test_cast_spell_eldritch_blast_scaling_lvl20(self):
        """Level 20 warlock casting Eldritch Blast receives 4d10 force damage roll"""
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.char_lvl20, name='Eldritch Blast', level=0, is_prepared=True)

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl20.id,
                'target_id': self.orc_full.id,
                'spell_name': 'Eldritch Blast',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertIn('4d10', data.get('damage_string', ''))

    def test_cast_spell_fire_bolt_scaling_lvl5(self):
        """Level 5 mage casting Fire Bolt receives 2d10 fire damage roll"""
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.char_lvl5, name='Fire Bolt', level=0, is_prepared=True)
        self.session.current_turn_index = 1
        self.session.save()

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl5.id,
                'target_id': self.orc_full.id,
                'spell_name': 'Fire Bolt',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertIn('2d10', data.get('damage_string', ''))

    def test_toll_the_dead_uninjured_vs_injured_scaling(self):
        """Toll the Dead deals d8 to uninjured targets and d12 to injured targets, both scaled by level"""
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.char_lvl20, name='Toll the Dead', level=0, is_prepared=True)

        # Cast on uninjured target -> 4d8 necrotic
        resp_uninjured = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl20.id,
                'target_id': self.orc_full.id,
                'spell_name': 'Toll the Dead',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(resp_uninjured.status_code, status.HTTP_200_OK)
        self.assertIn('4d8', resp_uninjured.data.get('damage_string', ''))

        # Reset caster actions
        self.caster_lvl20.action_used = False
        self.caster_lvl20.attacks_remaining = 1
        self.caster_lvl20.save()

        # Cast on injured target -> 4d12 necrotic
        resp_injured = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl20.id,
                'target_id': self.orc_injured.id,
                'spell_name': 'Toll the Dead',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(resp_injured.status_code, status.HTTP_200_OK)
        self.assertIn('4d12', resp_injured.data.get('damage_string', ''))

    def test_other_cantrips_scaling(self):
        """Test Ray of Frost (4d8), Acid Splash (4d6), and Poison Spray (4d12) scaling at level 20"""
        from characters.models import CharacterSpell
        for spell_name in ['Ray of Frost', 'Acid Splash', 'Poison Spray']:
            CharacterSpell.objects.create(character=self.char_lvl20, name=spell_name, level=0, is_prepared=True)

        # Ray of Frost -> 4d8
        resp = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl20.id,
                'target_id': self.orc_full.id,
                'spell_name': 'Ray of Frost',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('4d8', resp.data.get('damage_string', ''))

        self.caster_lvl20.action_used = False
        self.caster_lvl20.attacks_remaining = 1
        self.caster_lvl20.save()

        # Poison Spray -> 4d12
        resp = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_lvl20.id,
                'target_id': self.orc_full.id,
                'spell_name': 'Poison Spray',
                'spell_level': 0,
            },
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('4d12', resp.data.get('damage_string', ''))


class SpellUpcastingTests(TestCase):
    """
    SRD 5.2 5e Upcasting Tests ('At Higher Levels'):
    Verifies that leveled spells scale appropriately when cast with higher-level spell slots.
    """
    def setUp(self):
        from django.contrib.auth.models import User
        from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
        from combat.models import CombatSession, CombatParticipant
        from encounters.models import Encounter

        self.client = APIClient()
        self.user = User.objects.create_user(username='upcast_tester', password='password123')
        self.client.force_authenticate(user=self.user)

        self.encounter = Encounter.objects.create(name='Upcast Encounter', description='Upcast tests')
        self.session = CombatSession.objects.create(
            encounter=self.encounter,
            status='active',
            current_round=1,
            current_turn_index=0
        )

        char_race = CharacterRace.objects.create(name='Tiefling')
        warlock_class = CharacterClass.objects.create(name='Warlock')

        self.character = Character.objects.create(
            user=self.user,
            name='Upcast Caster',
            level=9,
            race=char_race,
            character_class=warlock_class
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=10,
            dexterity=14,
            constitution=14,
            intelligence=12,
            wisdom=10,
            charisma=18,
            spell_save_dc=16,
            spell_attack_bonus=8,
            hit_points=60,
            max_hit_points=60,
            armor_class=14,
            spell_slots={'1': 4, '2': 3, '3': 3, '4': 3, '5': 2},
            expended_spell_slots={}
        )

        self.caster = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            name='Upcast Caster',
            initiative=20,
            current_hp=60,
            max_hp=60,
            armor_class=14,
            attacks_remaining=1,
            action_used=False,
            position_x=10,
            position_y=10
        )

        self.target = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Target Dummy',
            initiative=10,
            current_hp=100,
            max_hp=100,
            armor_class=10,
            position_x=15,
            position_y=10
        )

        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=self.character, name='Fireball', level=3, is_prepared=True)
        CharacterSpell.objects.create(character=self.character, name='Magic Missile', level=1, is_prepared=True)
        CharacterSpell.objects.create(character=self.character, name='Guiding Bolt', level=1, is_prepared=True)
        CharacterSpell.objects.create(character=self.character, name='Armor of Agathys', level=1, is_prepared=True)
        CharacterSpell.objects.create(character=self.character, name='Aid', level=2, is_prepared=True)

    def test_scale_upcast_spell_damage_formulas(self):
        """Test unit formula scaling for standard, stepped, and multi-die spells"""
        from combat.spell_rules import scale_upcast_spell_damage

        # Fireball (base 3): 8d6 -> 9d6 @ lvl 4, 10d6 @ lvl 5
        self.assertEqual(scale_upcast_spell_damage('fireball', '8d6 fire', 3, 3), '8d6 fire')
        self.assertEqual(scale_upcast_spell_damage('fireball', '8d6 fire', 3, 4), '9d6 fire')
        self.assertEqual(scale_upcast_spell_damage('fireball', '8d6 fire', 3, 5), '10d6 fire')

        # Guiding Bolt (base 1): 4d6 -> 5d6 @ lvl 2, 6d6 @ lvl 3
        self.assertEqual(scale_upcast_spell_damage('guiding bolt', '4d6 radiant', 1, 1), '4d6 radiant')
        self.assertEqual(scale_upcast_spell_damage('guiding bolt', '4d6 radiant', 1, 2), '5d6 radiant')
        self.assertEqual(scale_upcast_spell_damage('guiding bolt', '4d6 radiant', 1, 3), '6d6 radiant')

        # Cure Wounds (base 1): 1d8 -> 2d8 @ lvl 2
        self.assertEqual(scale_upcast_spell_damage('cure wounds', '1d8', 1, 2), '2d8')

        # Scorching Ray (base 2): 6d6 (3 rays) -> 8d6 (4 rays) @ lvl 3, 10d6 (5 rays) @ lvl 4
        self.assertEqual(scale_upcast_spell_damage('scorching ray', '6d6 fire', 2, 2), '6d6 fire')
        self.assertEqual(scale_upcast_spell_damage('scorching ray', '6d6 fire', 2, 3), '8d6 fire')
        self.assertEqual(scale_upcast_spell_damage('scorching ray', '6d6 fire', 2, 4), '10d6 fire')

        # Sleep (base 1): 5d8 -> 7d8 @ lvl 2, 9d8 @ lvl 3
        self.assertEqual(scale_upcast_spell_damage('sleep', '5d8', 1, 2), '7d8')
        self.assertEqual(scale_upcast_spell_damage('sleep', '5d8', 1, 3), '9d8')

        # Spiritual Weapon (base 2): +1d8 per 2 slot levels above 2nd
        self.assertEqual(scale_upcast_spell_damage('spiritual weapon', '1d8 force', 2, 2), '1d8 force')
        self.assertEqual(scale_upcast_spell_damage('spiritual weapon', '1d8 force', 2, 3), '1d8 force')
        self.assertEqual(scale_upcast_spell_damage('spiritual weapon', '1d8 force', 2, 4), '2d8 force')
        self.assertEqual(scale_upcast_spell_damage('spiritual weapon', '1d8 force', 2, 5), '2d8 force')
        self.assertEqual(scale_upcast_spell_damage('spiritual weapon', '1d8 force', 2, 6), '3d8 force')

        # Disintegrate (base 6): 10d6+40 -> 13d6+40 @ lvl 7
        self.assertEqual(scale_upcast_spell_damage('disintegrate', '10d6+40 force', 6, 7), '13d6+40 force')

    def test_get_spell_base_level(self):
        """Test base level lookup for cantrips and leveled spells"""
        from combat.spell_rules import get_spell_base_level

        self.assertEqual(get_spell_base_level('fire bolt'), 0)
        self.assertEqual(get_spell_base_level('eldritch blast'), 0)
        self.assertEqual(get_spell_base_level('magic missile'), 1)
        self.assertEqual(get_spell_base_level('guiding bolt'), 1)
        self.assertEqual(get_spell_base_level('armor of agathys'), 1)
        self.assertEqual(get_spell_base_level('scorching ray'), 2)
        self.assertEqual(get_spell_base_level('shatter'), 2)
        self.assertEqual(get_spell_base_level('aid'), 2)
        self.assertEqual(get_spell_base_level('fireball'), 3)
        self.assertEqual(get_spell_base_level('lightning bolt'), 3)
        self.assertEqual(get_spell_base_level('ice storm'), 4)
        self.assertEqual(get_spell_base_level('cone of cold'), 5)
        self.assertEqual(get_spell_base_level('disintegrate'), 6)

    def test_cast_spell_fireball_upcast_to_level_4(self):
        """Casting Fireball at level 4 deals 9d6 fire damage (base 8d6 + 1d6)"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_id': self.target.id,
                'spell_name': 'Fireball',
                'spell_level': 4,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertIn('9d6', data.get('damage_string', ''))

    def test_cast_spell_magic_missile_upcast_to_level_2(self):
        """Casting Magic Missile at level 2 fires 4 darts (3 base + 1 upcast)"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_id': self.target.id,
                'spell_name': 'Magic Missile',
                'spell_level': 2,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        target_results = data.get('target_results', [])
        self.assertTrue(len(target_results) > 0)
        self.assertEqual(target_results[0].get('darts_count'), 4)

    def test_cast_spell_guiding_bolt_upcast_to_level_2(self):
        """Casting Guiding Bolt at level 2 deals 5d6 radiant damage (base 4d6 + 1d6)"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_id': self.target.id,
                'spell_name': 'Guiding Bolt',
                'spell_level': 2,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertIn('5d6', data.get('damage_string', ''))

    def test_cast_spell_armor_of_agathys_upcast_to_level_3(self):
        """Casting Armor of Agathys at level 3 grants 15 temp HP and 15 cold retaliation"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_id': self.caster.id,
                'spell_name': 'Armor of Agathys',
                'spell_level': 3,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.caster.refresh_from_db()
        self.assertEqual(self.caster.feature_uses.get('temp_hp'), 15)
        self.assertEqual(self.caster.feature_uses.get('armor_of_agathys_damage'), 15)

    def test_cast_spell_aid_upcast_to_level_3(self):
        """Casting Aid at level 3 boosts target max & current HP by 10 (5 base + 5 upcast)"""
        initial_max_hp = self.target.max_hp
        initial_cur_hp = self.target.current_hp

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster.id,
                'target_id': self.target.id,
                'spell_name': 'Aid',
                'spell_level': 3,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.target.refresh_from_db()
        self.assertEqual(self.target.max_hp, initial_max_hp + 10)
        self.assertEqual(self.target.current_hp, initial_cur_hp + 10)




