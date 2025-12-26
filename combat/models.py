from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character
from bestiary.models import Condition, DamageType


class CombatSession(models.Model):
    """Represents an active combat encounter"""
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='combat_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    current_round = models.IntegerField(default=0)
    current_turn_index = models.IntegerField(default=0)  # Index in initiative order
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Combat: {self.encounter.name} (Round {self.current_round})"
    
    def get_current_participant(self):
        """Get the participant whose turn it is"""
        participants = self.participants.filter(is_active=True).order_by('-initiative', 'id')
        if participants.exists() and self.current_turn_index < participants.count():
            return participants[self.current_turn_index]
        return None
    
    def get_initiative_order(self):
        """Get all participants ordered by initiative (highest first)"""
        return self.participants.filter(is_active=True).order_by('-initiative', 'id')
    
    def next_turn(self):
        """Advance to the next turn"""
        participants = self.get_initiative_order()
        if not participants.exists():
            return None
        
        self.current_turn_index += 1
        
        # If we've gone through all participants, start a new round
        if self.current_turn_index >= participants.count():
            self.current_round += 1
            self.current_turn_index = 0
        
        self.save()
        return self.get_current_participant()


class CombatParticipant(models.Model):
    """Represents a character or enemy participating in combat"""
    PARTICIPANT_TYPES = [
        ('character', 'Character'),
        ('enemy', 'Enemy'),
    ]
    
    combat_session = models.ForeignKey(CombatSession, on_delete=models.CASCADE, related_name='participants')
    
    # Link to either Character or EncounterEnemy
    participant_type = models.CharField(max_length=20, choices=PARTICIPANT_TYPES)
    character = models.ForeignKey(Character, on_delete=models.CASCADE, blank=True, null=True, related_name='combat_participations')
    encounter_enemy = models.ForeignKey(EncounterEnemy, on_delete=models.CASCADE, blank=True, null=True, related_name='combat_participations')
    
    # Combat state
    initiative = models.IntegerField(default=0)
    current_hp = models.IntegerField()
    max_hp = models.IntegerField()
    armor_class = models.IntegerField()
    is_active = models.BooleanField(default=True)  # False if unconscious/dead
    
    # Action economy
    action_used = models.BooleanField(default=False)
    bonus_action_used = models.BooleanField(default=False)
    reaction_used = models.BooleanField(default=False)
    movement_used = models.IntegerField(default=0)  # Feet moved this turn
    
    # Conditions (many-to-many for multiple conditions)
    conditions = models.ManyToManyField(Condition, blank=True, related_name='combat_participants')
    
    # Death saves (for characters)
    death_save_successes = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(3)])
    death_save_failures = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(3)])
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-initiative', 'id']
        unique_together = ['combat_session', 'character', 'encounter_enemy']
    
    def __str__(self):
        name = self.get_name()
        return f"{name} (Initiative: {self.initiative})"
    
    def get_name(self):
        """Get the name of the participant"""
        if self.character:
            return self.character.name
        elif self.encounter_enemy:
            return self.encounter_enemy.name
        return "Unknown"
    
    def get_ability_modifier(self, ability):
        """Get ability modifier for a given ability (STR, DEX, etc.)"""
        if self.character and hasattr(self.character, 'stats'):
            stats = self.character.stats
            ability_map = {
                'STR': stats.strength_modifier,
                'DEX': stats.dexterity_modifier,
                'CON': stats.constitution_modifier,
                'INT': stats.intelligence_modifier,
                'WIS': stats.wisdom_modifier,
                'CHA': stats.charisma_modifier,
            }
            return ability_map.get(ability, 0)
        elif self.encounter_enemy and hasattr(self.encounter_enemy.enemy, 'stats'):
            stats = self.encounter_enemy.enemy.stats
            ability_map = {
                'STR': stats.strength_modifier,
                'DEX': stats.dexterity_modifier,
                'CON': stats.constitution_modifier,
                'INT': stats.intelligence_modifier,
                'WIS': stats.wisdom_modifier,
                'CHA': stats.charisma_modifier,
            }
            return ability_map.get(ability, 0)
        return 0
    
    def take_damage(self, amount, damage_type=None):
        """Apply damage to this participant"""
        # Check for resistances/immunities
        if damage_type:
            # This would check resistances - simplified for now
            pass
        
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp <= 0:
            self.is_active = False
        self.save()
        return self.current_hp
    
    def heal(self, amount):
        """Heal this participant"""
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        if self.current_hp > 0:
            self.is_active = True
        self.save()
        return self.current_hp
    
    def reset_turn(self):
        """Reset action economy for a new turn"""
        self.action_used = False
        self.bonus_action_used = False
        self.reaction_used = False
        self.movement_used = 0
        self.save()


class CombatAction(models.Model):
    """Log of actions taken during combat"""
    ACTION_TYPES = [
        ('attack', 'Attack'),
        ('spell', 'Spell'),
        ('move', 'Move'),
        ('dash', 'Dash'),
        ('dodge', 'Dodge'),
        ('disengage', 'Disengage'),
        ('help', 'Help'),
        ('hide', 'Hide'),
        ('ready', 'Ready'),
        ('search', 'Search'),
        ('use_object', 'Use Object'),
        ('other', 'Other'),
    ]
    
    combat_session = models.ForeignKey(CombatSession, on_delete=models.CASCADE, related_name='actions')
    actor = models.ForeignKey(CombatParticipant, on_delete=models.CASCADE, related_name='actions_taken')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    
    # Target (optional, for attacks/spells)
    target = models.ForeignKey(CombatParticipant, on_delete=models.SET_NULL, blank=True, null=True, related_name='actions_received')
    
    # Attack/spell details
    attack_name = models.CharField(max_length=100, blank=True)  # e.g. "Longsword", "Fireball"
    attack_roll = models.IntegerField(blank=True, null=True)  # d20 roll
    attack_modifier = models.IntegerField(blank=True, null=True)  # Total modifier
    attack_total = models.IntegerField(blank=True, null=True)  # Total attack roll
    hit = models.BooleanField(blank=True, null=True)  # Whether it hit
    
    # Damage
    damage_roll = models.CharField(max_length=100, blank=True)  # e.g. "2d6+3"
    damage_amount = models.IntegerField(blank=True, null=True)  # Actual damage dealt
    damage_type = models.ForeignKey(DamageType, on_delete=models.SET_NULL, blank=True, null=True)
    critical = models.BooleanField(default=False)
    
    # Saving throw
    save_type = models.CharField(max_length=3, blank=True)  # STR, DEX, CON, etc.
    save_dc = models.IntegerField(blank=True, null=True)
    save_roll = models.IntegerField(blank=True, null=True)
    save_success = models.BooleanField(blank=True, null=True)
    
    # Other details
    description = models.TextField(blank=True)
    round_number = models.IntegerField()
    turn_number = models.IntegerField()  # Turn within the round
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-round_number', '-turn_number', '-created_at']
    
    def __str__(self):
        return f"{self.actor.get_name()} - {self.get_action_type_display()} (Round {self.round_number})"
