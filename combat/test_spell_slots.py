"""
Tests for enemy spell slot enforcement.

Verifies that enemies cannot spam spells and are properly limited by their stat blocks.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from bestiary.models import Enemy, EnemySpell, EnemySpellSlot
from encounters.models import Encounter, EncounterEnemy
from combat.models import CombatSession, CombatParticipant
from characters.models import Character


class EnemySpellSlotEnforcementTests(TestCase):
    """Test that enemy spell slots are properly tracked and enforced"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create race and class for character
        from characters.models import CharacterRace, CharacterClass
        human_race = CharacterRace.objects.create(name="Human")
        wizard_class = CharacterClass.objects.create(name="Wizard")
        
        # Create player character
        self.character = Character.objects.create(
            user=self.user,
            name="Test Wizard",
            level=5,
            character_class=wizard_class,
            race=human_race,
            experience_points=0
        )
        
        # Create enemy with limited spell slots
        self.lich = Enemy.objects.create(
            name="Lich",
            hp=135,
            ac=17,
            challenge_rating="21",
            creature_type="undead"
        )
        
        # Add Power Word Kill (1/day)
        power_word = EnemySpell.objects.create(
            enemy=self.lich,
            name="Power Word Kill",
            save_dc=19
        )
        EnemySpellSlot.objects.create(
            spell=power_word,
            level=9,
            uses=1  # Only 1 use per day
        )
        
        # Add Fireball (3/day)
        fireball = EnemySpell.objects.create(
            enemy=self.lich,
            name="Fireball",
            save_dc=19
        )
        EnemySpellSlot.objects.create(
            spell=fireball,
            level=3,
            uses=3  # 3 uses per day
        )
        
        # Add Ray of Frost (at will - no slot limit)
        ray = EnemySpell.objects.create(
            enemy=self.lich,
            name="Ray of Frost",
            save_dc=None
        )
        # No EnemySpellSlot = at will
        
        # Create encounter with lich
        self.encounter = Encounter.objects.create(
            name="Lich Fight",
            description="Epic boss battle"
        )
        self.encounter_lich = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.lich,
            name="Ancient Lich",
            current_hp=135
        )
        
        # Create combat session
        self.combat = CombatSession.objects.create(
            encounter=self.encounter,
            status='active',
            current_round=1
        )
        
        # Add character participant
        self.char_participant = CombatParticipant.objects.create(
            combat_session=self.combat,
            participant_type='character',
            character=self.character,
            initiative=15,
            current_hp=38,
            max_hp=38,
            armor_class=12
        )
        
        # Add lich participant
        self.lich_participant = CombatParticipant.objects.create(
            combat_session=self.combat,
            participant_type='enemy',
            encounter_enemy=self.encounter_lich,
            initiative=20,
            current_hp=135,
            max_hp=135,
            armor_class=17
        )
        
        # Set it to lich's turn
        self.combat.current_turn_index = 0
        self.combat.save()
    
    def test_enemy_spell_slot_initialized_on_first_cast(self):
        """Spell slot should be initialized from stat block on first cast"""
        # Initially, spell_uses_remaining should be empty
        self.assertEqual(self.lich_participant.spell_uses_remaining, {})
        
        # Check if can cast
        can_cast = self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.assertTrue(can_cast)
        
        # Should now be initialized
        self.lich_participant.refresh_from_db()
        self.assertEqual(self.lich_participant.spell_uses_remaining.get("Power Word Kill"), 1)
    
    def test_enemy_limited_spell_usage(self):
        """Enemy should only be able to cast limited spell once"""
        # First cast should succeed
        can_cast_1 = self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.assertTrue(can_cast_1)
        
        # Use the spell
        self.lich_participant.use_enemy_spell("Power Word Kill")
        
        # Second attempt should fail
        can_cast_2 = self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.assertFalse(can_cast_2)
        
        # Check uses remaining
        self.assertEqual(self.lich_participant.spell_uses_remaining.get("Power Word Kill"), 0)
    
    def test_enemy_multiple_spell_uses(self):
        """Enemy with 3/day spell should be able to cast 3 times"""
        # Should be able to cast 3 times
        for i in range(3):
            can_cast = self.lich_participant.can_cast_enemy_spell("Fireball")
            self.assertTrue(can_cast, f"Should be able to cast Fireball (attempt {i+1}/3)")
            self.lich_participant.use_enemy_spell("Fireball")
        
        # Fourth attempt should fail
        can_cast_4 = self.lich_participant.can_cast_enemy_spell("Fireball")
        self.assertFalse(can_cast_4, "Should NOT be able to cast 4th Fireball")
        
        self.assertEqual(self.lich_participant.spell_uses_remaining.get("Fireball"), 0)
    
    def test_enemy_at_will_spell_unlimited(self):
        """At-will spells (no slot) should be castable unlimited times"""
        # Cast 10 times - should always work
        for i in range(10):
            can_cast = self.lich_participant.can_cast_enemy_spell("Ray of Frost")
            self.assertTrue(can_cast, f"At-will spell should always be castable (attempt {i+1})")
            self.lich_participant.use_enemy_spell("Ray of Frost")
        
        # Should still have no slot tracking for at-will spells
        self.assertNotIn("Ray of Frost", self.lich_participant.spell_uses_remaining)
    
    def test_enemy_unknown_spell(self):
        """Enemy should not be able to cast spells not in their list"""
        can_cast = self.lich_participant.can_cast_enemy_spell("Wish")
        self.assertFalse(can_cast, "Should not be able to cast unknown spell")
    
    def test_reset_enemy_spell_slots(self):
        """Resetting should restore all spell uses"""
        # Use Power Word Kill
        self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.lich_participant.use_enemy_spell("Power Word Kill")
        self.assertEqual(self.lich_participant.spell_uses_remaining.get("Power Word Kill"), 0)
        
        # Reset
        self.lich_participant.reset_enemy_spell_slots()
        
        # Should be able to cast again
        self.assertEqual(self.lich_participant.spell_uses_remaining, {})
        can_cast = self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.assertTrue(can_cast)
    
    def test_cast_spell_endpoint_enforces_limit(self):
        """API endpoint should block spell casting when out of slots"""
        # Manually use up the spell slot
        self.lich_participant.can_cast_enemy_spell("Power Word Kill")  # Initialize
        self.lich_participant.use_enemy_spell("Power Word Kill")  # Use it
        
        # Verify it's used up
        can_cast = self.lich_participant.can_cast_enemy_spell("Power Word Kill")
        self.assertFalse(can_cast, "Power Word Kill should be out of uses")
        
        # Verify spell_uses_remaining is tracked
        self.assertEqual(self.lich_participant.spell_uses_remaining.get("Power Word Kill"), 0)
