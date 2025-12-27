from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from encounters.models import Encounter
from characters.models import Character
from combat.models import CombatSession


class Campaign(models.Model):
    """A roguelike gauntlet campaign with sequential encounters"""
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns', null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    
    # Encounter tracking
    current_encounter_index = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_encounters = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Rest management
    short_rests_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    long_rests_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    long_rests_available = models.IntegerField(default=2, validators=[MinValueValidator(0)])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def start(self):
        """Start the campaign"""
        if self.status != 'preparing':
            raise ValueError("Campaign must be in 'preparing' status to start")
        
        # Check for characters and their status
        total_characters = self.campaign_characters.count()
        alive_characters = self.campaign_characters.filter(is_alive=True)
        alive_count = alive_characters.count()
        
        if total_characters == 0:
            raise ValueError("Campaign must have at least one character. Add characters before starting.")
        
        if alive_count == 0:
            # Try to re-initialize dead characters if they exist
            dead_characters = self.campaign_characters.filter(is_alive=False)
            for char in dead_characters:
                try:
                    char.initialize_from_character()
                    alive_count += 1
                except (ValueError, AttributeError):
                    # Skip characters that can't be initialized
                    pass
            
            if alive_count == 0:
                raise ValueError(
                    f"Campaign must have at least one alive character. "
                    f"Found {total_characters} character(s) but none are alive. "
                    f"All characters may need to be re-initialized or added properly."
                )
        
        if not self.campaign_encounters.exists():
            raise ValueError("Campaign must have at least one encounter")
        
        self.status = 'active'
        self.started_at = timezone.now()
        self.current_encounter_index = 0
        self.total_encounters = self.campaign_encounters.count()
        self.save()
    
    def get_current_encounter(self):
        """Get the current encounter"""
        if self.current_encounter_index < self.campaign_encounters.count():
            return self.campaign_encounters.order_by('encounter_number')[self.current_encounter_index]
        return None
    
    def get_alive_characters(self):
        """Get all alive characters in the campaign"""
        return self.campaign_characters.filter(is_alive=True)
    
    def check_campaign_status(self):
        """Check if campaign should end (all characters dead or all encounters completed)"""
        alive_count = self.get_alive_characters().count()
        
        if alive_count == 0:
            self.status = 'failed'
            self.ended_at = timezone.now()
            self.save()
            return 'failed'
        
        if self.current_encounter_index >= self.total_encounters:
            self.status = 'completed'
            self.ended_at = timezone.now()
            self.save()
            return 'completed'
        
        return 'active'
    
    def can_take_short_rest(self):
        """Check if party can take a short rest"""
        return self.status == 'active' and self.get_alive_characters().exists()
    
    def can_take_long_rest(self):
        """Check if party can take a long rest"""
        return (
            self.status == 'active' and 
            self.get_alive_characters().exists() and
            self.long_rests_used < self.long_rests_available
        )


class CampaignCharacter(models.Model):
    """A character participating in a campaign (with permadeath)"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_characters')
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='campaign_participations')
    
    # Current state in campaign
    current_hp = models.IntegerField(validators=[MinValueValidator(0)])
    max_hp = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Hit dice tracking (stored as JSON: {"d8": 3} means 3d8 available)
    hit_dice_remaining = models.JSONField(default=dict)
    
    # Spell slots tracking (stored as JSON: {"1": 3, "2": 2} means 3 level-1, 2 level-2 slots)
    spell_slots = models.JSONField(default=dict)
    
    # Permadeath
    is_alive = models.BooleanField(default=True)
    died_in_encounter = models.IntegerField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['campaign', 'character']
    
    def __str__(self):
        status = "Alive" if self.is_alive else "Dead"
        return f"{self.character.name} in {self.campaign.name} ({status})"
    
    def initialize_from_character(self):
        """Initialize campaign character from base character"""
        if not hasattr(self.character, 'stats'):
            raise ValueError("Character must have stats to join campaign")
        
        stats = self.character.stats
        self.max_hp = stats.max_hit_points
        self.current_hp = stats.max_hit_points
        
        # Ensure character is marked as alive
        self.is_alive = True
        
        # Initialize hit dice based on character level and class
        hit_dice_type = self.character.character_class.hit_dice  # e.g., "d8"
        self.hit_dice_remaining = {hit_dice_type: self.character.level}
        
        # Initialize spell slots (simplified - would need class-specific logic)
        # For now, we'll leave this empty and let it be set manually or via class features
        self.spell_slots = {}
        
        self.save()
    
    def take_damage(self, amount):
        """Apply damage to this character"""
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp == 0:
            self.is_alive = False
        self.save()
        return self.current_hp
    
    def heal(self, amount):
        """Heal this character"""
        if not self.is_alive:
            return self.current_hp  # Can't heal dead characters
        
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        self.save()
        return self.current_hp - old_hp  # Return actual healing done
    
    def spend_hit_die(self, dice_type=None):
        """Spend one hit die to heal (returns healing amount)"""
        if not dice_type:
            # Get the first available hit dice type
            if not self.hit_dice_remaining:
                return 0, "No hit dice remaining"
            dice_type = list(self.hit_dice_remaining.keys())[0]
        
        if dice_type not in self.hit_dice_remaining or self.hit_dice_remaining[dice_type] <= 0:
            return 0, "No hit dice of that type remaining"
        
        # Roll hit die (simplified: average of die + CON mod)
        # In D&D 5e, you roll the die and add CON modifier
        import random
        die_size = int(dice_type[1:])  # Extract number from "d8" -> 8
        roll = random.randint(1, die_size)
        
        # Get CON modifier from character stats
        if hasattr(self.character, 'stats'):
            con_score = self.character.stats.constitution
            con_mod = (con_score - 10) // 2
            healing = roll + con_mod
        else:
            healing = roll
        
        # Spend the hit die
        if dice_type in self.hit_dice_remaining:
            self.hit_dice_remaining[dice_type] -= 1
            if self.hit_dice_remaining[dice_type] <= 0:
                del self.hit_dice_remaining[dice_type]
        
        # Apply healing
        actual_healing = self.heal(healing)
        self.save()
        
        return actual_healing, f"Rolled {roll} on {dice_type}, healed {actual_healing} HP"
    
    def get_available_hit_dice(self):
        """Get total number of available hit dice"""
        return sum(self.hit_dice_remaining.values())
    
    def restore_all_hit_dice(self):
        """Restore all hit dice (long rest)"""
        hit_dice_type = self.character.character_class.hit_dice
        self.hit_dice_remaining = {hit_dice_type: self.character.level}
        self.save()


class CampaignEncounter(models.Model):
    """An encounter in a campaign"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_encounters')
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='campaign_encounters')
    encounter_number = models.IntegerField(validators=[MinValueValidator(1)])
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Link to combat session if combat occurred
    combat_session = models.ForeignKey(CombatSession, on_delete=models.SET_NULL, blank=True, null=True, related_name='campaign_encounters')
    
    # Rewards (stored as JSON)
    rewards = models.JSONField(default=dict)  # e.g., {"gold": 100, "items": [1, 2], "xp": 200}
    
    completed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['campaign', 'encounter_number']
        ordering = ['encounter_number']
    
    def __str__(self):
        return f"Encounter {self.encounter_number}: {self.encounter.name} ({self.get_status_display()})"
    
    def start(self):
        """Start this encounter"""
        if self.status != 'pending':
            raise ValueError("Encounter must be in 'pending' status to start")
        
        self.status = 'active'
        self.save()
    
    def complete(self, combat_session=None, rewards=None):
        """Mark encounter as completed"""
        if self.status != 'active':
            raise ValueError("Encounter must be in 'active' status to complete")
        
        self.status = 'completed'
        self.combat_session = combat_session
        if rewards:
            self.rewards = rewards
        self.completed_at = timezone.now()
        self.save()
        
        # Advance campaign to next encounter
        self.campaign.current_encounter_index += 1
        self.campaign.save()
        
        # Check campaign status
        self.campaign.check_campaign_status()
    
    def fail(self):
        """Mark encounter as failed (all characters died)"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.save()
        
        # Mark campaign as failed
        self.campaign.status = 'failed'
        self.campaign.ended_at = timezone.now()
        self.campaign.save()
