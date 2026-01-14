"""
High-ROI Spell Casting Combat Tests

Tests spell casting in combat - core gameplay mechanic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from combat.models import CombatSession, CombatParticipant, CombatAction
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from bestiary.models import Enemy, EnemyStats, EnemySpell, EnemySpellSlot
from encounters.models import Encounter, EncounterEnemy


class SpellCastingCombatTests(TestCase):
    """Test spell casting in combat"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create wizard character
        race = CharacterRace.objects.create(name="Human")
        wizard_class = CharacterClass.objects.create(
            name="wizard",
            hit_dice="d6",
            primary_ability="INT"
        )
        
        self.wizard = Character.objects.create(
            user=self.user,
            name="Test Wizard",
            level=5,
            character_class=wizard_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.wizard,
            intelligence=18,  # +4 modifier
            max_hit_points=30,
            hit_points=30,
            armor_class=12
        )
        
        # Add a prepared spell
        CharacterSpell.objects.create(
            character=self.wizard,
            name="Fireball",
            level=3,
            is_prepared=True
        )
        
        # Create enemy
        self.goblin = Enemy.objects.create(
            name="Goblin",
            hp=7,
            ac=15,
            challenge_rating="1/4"
        )
        
        EnemyStats.objects.create(
            enemy=self.goblin,
            dexterity=14,
            constitution=10,
            hit_points=7,
            armor_class=15
        )
        
        # Create encounter
        self.encounter = Encounter.objects.create(name="Test Encounter")
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.goblin,
            name="Goblin Warrior",
            current_hp=7
        )
        
        # Create combat
        self.session = CombatSession.objects.create(
            status='active',
            current_round=1,
            current_turn_index=0,
            encounter=self.encounter
        )
        
        # Add participants
        self.wizard_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.wizard,
            initiative=20,
            current_hp=30,
            max_hp=30,
            armor_class=12
        )
        
        self.goblin_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=15,
            current_hp=7,
            max_hp=7,
            armor_class=15
        )
    
    def test_cast_spell_basic(self):
        """Test basic spell casting"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.wizard_participant.id,
                'target_id': self.goblin_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3,
                'damage_string': '8d6'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('action', response.data)
        
        # Verify action was created
        actions = CombatAction.objects.filter(
            combat_session=self.session,
            action_type='spell'
        )
        self.assertEqual(actions.count(), 1)
    
    def test_cast_spell_with_saving_throw(self):
        """Test spell with saving throw"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.wizard_participant.id,
                'target_id': self.goblin_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3,
                'save_type': 'dex',
                'save_dc': 15,
                'damage_string': '8d6'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)  
        self.assertIn('save_success', response.data)
        self.assertIn('damage', response.data)  # Field is 'damage' not 'damage_dealt'
    
    def test_cast_spell_wrong_turn_fails(self):
        """Test casting spell when it's not your turn fails"""
        # Set turn to goblin
        self.session.current_turn_index = 1
        self.session.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.wizard_participant.id,
                'target_id': self.goblin_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('turn', response.data['error'].lower())
    
    def test_cast_unprepared_spell_fails(self):
        """Test casting unprepared spell fails"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.wizard_participant.id,
                'target_id': self.goblin_participant.id,
                'spell_name': 'Lightning Bolt',  # Not prepared
                'spell_level': 3
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cast_spell_marks_action_used(self):
        """Test casting spell marks action as used"""
        self.wizard_participant.action_used = False
        self.wizard_participant.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.wizard_participant.id,
                'target_id': self.goblin_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.wizard_participant.refresh_from_db()
        self.assertTrue(self.wizard_participant.action_used)


class EnemySpellCastingTests(TestCase):
    """Test enemy spell casting with slot enforcement"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create fighter
        race = CharacterRace.objects.create(name="Human")
        fighter_class = CharacterClass.objects.create(name="Fighter", hit_dice="d10")
        
        self.fighter = Character.objects.create(
            user=self.user,
            name="Fighter",
            level=5,
            character_class=fighter_class,
            race=race
        )
        
        CharacterStats.objects.create(
            character=self.fighter,
            max_hit_points=45,
            hit_points=45,
            armor_class=18
        )
        
        # Create enemy spellcaster
        self.mage = Enemy.objects.create(
            name="Evil Mage",
            hp=40,
            ac=12,
            challenge_rating="5"
        )
        
        EnemyStats.objects.create(
            enemy=self.mage,
            intelligence=16,
            hit_points=40,
            armor_class=12
        )
        
        # Add spell with limited uses
        spell = EnemySpell.objects.create(
            enemy=self.mage,
            name="Fireball",
            save_dc=14
        )
        EnemySpellSlot.objects.create(
            spell=spell,
            level=3,
            uses=2  # Can cast twice
        )
        
        # Create encounter and combat
        self.encounter = Encounter.objects.create(name="Mage Fight")
        self.encounter_enemy = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.mage,
            name="Evil Mage",
            current_hp=40
        )
        
        self.session = CombatSession.objects.create(
            status='active',
            current_round=1,
           current_turn_index=0,  # Start at mage's turn (higher initiative)
            encounter=self.encounter
        )
        
        self.fighter_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter,
            initiative=15,
            current_hp=45,
            max_hp=45,
            armor_class=18
        )
        
        self.mage_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.encounter_enemy,
            initiative=20,
            current_hp=40,
            max_hp=40,
            armor_class=12
        )
    
    def test_enemy_can_cast_spell_with_slots(self):
        """Test enemy can cast spell when slots available"""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.mage_participant.id,
                'target_id': self.fighter_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3,
                'save_type': 'dex',
                'save_dc': 14,
                'damage_string': '8d6'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_enemy_spell_slot_enforcement(self):
        """Test enemy cannot cast when slots exhausted"""
        # Use up spell slots
        self.mage_participant.spell_uses_remaining = {"Fireball": 0}
        self.mage_participant.save()
        
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.mage_participant.id,
                'target_id': self.fighter_participant.id,
                'spell_name': 'Fireball',
                'spell_level': 3
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('slot', response.data['error'].lower())
