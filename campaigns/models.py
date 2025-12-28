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
    
    # Roguelite features
    starting_level = models.IntegerField(
        default=1,
        choices=[(1, 'Level 1'), (3, 'Level 3'), (5, 'Level 5')],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    START_MODE_CHOICES = [
        ('solo', 'Solo - Start alone, recruit during run'),
        ('party', 'Party - Start with selected characters'),
    ]
    
    start_mode = models.CharField(
        max_length=10,
        choices=START_MODE_CHOICES,
        default='party',
        help_text="Solo mode: Start with 1 character, can recruit up to 3 more. Party mode: Start with selected characters, no recruitment."
    )
    starting_party_size = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Starting party size (1-4 characters). In solo mode, this is set to 1. In party mode, this is the number of characters added."
    )
    
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
        
        # Solo mode restrictions
        if self.start_mode == 'solo':
            if alive_count != 1:
                raise ValueError(
                    f"Solo mode requires exactly 1 character at start. "
                    f"Found {alive_count} alive character(s). Remove extra characters or switch to party mode."
                )
            # Set starting party size to 1 for solo mode
            self.starting_party_size = 1
        else:  # party mode
            if alive_count < 1:
                raise ValueError("Party mode requires at least 1 character at start. Add characters before starting.")
            if alive_count > 4:
                raise ValueError(f"Party mode supports up to 4 characters. Found {alive_count}. Remove extra characters.")
            # Set starting party size to current count
            self.starting_party_size = alive_count
        
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
        
        # Use campaign's starting level if character level doesn't match
        campaign_level = self.campaign.starting_level
        if self.character.level != campaign_level:
            self.character.level = campaign_level
            self.character.save()
        
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
        
        # Create XP tracking for this character
        CharacterXP.objects.get_or_create(
            campaign_character=self,
            defaults={'current_xp': 0}
        )
    
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


class CharacterXP(models.Model):
    """Tracks experience points and leveling for characters in a campaign"""
    campaign_character = models.OneToOneField(
        CampaignCharacter,
        on_delete=models.CASCADE,
        related_name='xp_tracking'
    )
    current_xp = models.IntegerField(default=0)
    total_xp_gained = models.IntegerField(default=0)
    level_ups_gained = models.IntegerField(default=0)  # Levels gained during campaign
    
    # Pending choices (player must make these choices before continuing)
    pending_asi_levels = models.JSONField(default=list, help_text="List of levels where ASI is pending player choice")
    pending_subclass_selection = models.BooleanField(default=False, help_text="True if character needs to select subclass")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.campaign_character.character.name} - {self.current_xp} XP"
    
    def add_xp(self, amount, source="combat"):
        """Add XP and check for level up"""
        self.current_xp += amount
        self.total_xp_gained += amount
        
        old_level = self.campaign_character.character.level
        new_level = self._calculate_level(self.current_xp)
        
        if new_level > old_level:
            levels_gained = new_level - old_level
            self._level_up(old_level, new_level, levels_gained)
        
        self.save()
        return {
            'xp_gained': amount,
            'current_xp': self.current_xp,
            'level_gained': new_level > old_level,
            'new_level': new_level if new_level > old_level else old_level
        }
    
    def _calculate_level(self, xp):
        """Calculate character level based on XP (D&D 5e progression)"""
        XP_THRESHOLDS = {
            1: 0,
            2: 300,
            3: 900,
            4: 2700,
            5: 6500,
            6: 14000,
            7: 23000,
            8: 34000,
            9: 48000,
            10: 64000,
            11: 85000,
            12: 100000,
            13: 120000,
            14: 140000,
            15: 165000,
            16: 195000,
            17: 225000,
            18: 265000,
            19: 305000,
            20: 355000,
        }
        
        level = 1
        for lvl, threshold in sorted(XP_THRESHOLDS.items(), reverse=True):
            if xp >= threshold:
                return lvl
        return level
    
    def _level_up(self, old_level, new_level, levels_gained):
        """Handle level up"""
        import random
        from characters.models import Character, CharacterStats
        
        character = self.campaign_character.character
        campaign = self.campaign_character.campaign
        
        # Update character level
        character.level = new_level
        
        # Calculate HP increase for each level gained
        total_hp_increase = 0
        for level in range(old_level + 1, new_level + 1):
            if hasattr(character, 'stats') and hasattr(character, 'character_class'):
                try:
                    stats = character.stats
                    # Get hit dice type from character class
                    hit_dice_type = character.character_class.hit_dice  # e.g., "d8" or "1d8"
                    # Extract die size (handle both "d8" and "1d8" formats)
                    if 'd' in hit_dice_type:
                        die_part = hit_dice_type.split('d')[-1]  # Get part after 'd'
                        die_size = int(die_part)
                    else:
                        die_size = 8  # Default fallback
                    
                    # Roll hit die (or use average)
                    roll = random.randint(1, die_size)
                    
                    # Add CON modifier
                    if hasattr(stats, 'constitution'):
                        con_mod = (stats.constitution - 10) // 2
                        hp_gain = roll + con_mod
                    else:
                        hp_gain = roll
                    
                    # Minimum 1 HP per level
                    hp_gain = max(1, hp_gain)
                    total_hp_increase += hp_gain
                except (AttributeError, ValueError, TypeError):
                    # Fallback: use average HP gain (assuming d8, +2 CON)
                    total_hp_increase += 7  # Average of d8 (4.5) + 2 CON mod ≈ 7
            else:
                # Fallback if no stats or class
                total_hp_increase += 7  # Default HP gain
        
        # Update campaign character HP
        if total_hp_increase > 0:
            self.campaign_character.max_hp += total_hp_increase
            self.campaign_character.current_hp += total_hp_increase  # Full heal on level up
        
        # Increase hit dice pool on level up
        hit_dice_type = character.character_class.hit_dice  # e.g., "d8"
        for _ in range(levels_gained):
            if hit_dice_type in self.campaign_character.hit_dice_remaining:
                self.campaign_character.hit_dice_remaining[hit_dice_type] += 1
            else:
                self.campaign_character.hit_dice_remaining[hit_dice_type] = 1
        
        # Update spell slots based on new level
        from .utils import calculate_spell_slots, get_spellcasting_ability, calculate_spell_save_dc, calculate_spell_attack_bonus
        class_name = character.character_class.name
        new_slots = calculate_spell_slots(class_name, new_level)
        if new_slots:
            self.campaign_character.spell_slots = new_slots
            
            # Update spell save DC and spell attack bonus
            spellcasting_ability = get_spellcasting_ability(class_name)
            if spellcasting_ability and hasattr(character, 'stats'):
                stats = character.stats
                stats.spell_save_dc = calculate_spell_save_dc(character, spellcasting_ability)
                stats.spell_attack_bonus = calculate_spell_attack_bonus(character, spellcasting_ability)
                stats.save()
        
        # Handle Ability Score Improvements (ASI) at levels 4, 8, 12, 16, 19
        asi_levels = [4, 8, 12, 16, 19]
        levels_with_asi = [lvl for lvl in range(old_level + 1, new_level + 1) if lvl in asi_levels]
        
        # Mark ASI as pending for player choice instead of auto-applying
        if levels_with_asi:
            # Add pending ASI levels to the list
            for level in levels_with_asi:
                if level not in self.pending_asi_levels:
                    self.pending_asi_levels.append(level)
            
            # Note: ASI will be applied when player makes choice via API endpoint
        
        # Check if subclass selection is needed
        # Most classes choose subclass at level 3, some at level 2 (Cleric, Druid, Wizard)
        subclass_levels = {
            'cleric': 1,  # Divine Domain at level 1
            'druid': 2,   # Druid Circle at level 2
            'wizard': 2,  # Arcane Tradition at level 2
            'sorcerer': 1, # Sorcerous Origin at level 1
            'warlock': 1,  # Otherworldly Patron at level 1
        }
        default_subclass_level = 3  # Most classes choose at level 3
        
        subclass_level = subclass_levels.get(character.character_class.name, default_subclass_level)
        
        if new_level >= subclass_level and not character.subclass:
            # Mark that subclass selection is needed
            self.pending_subclass_selection = True
        
        # Apply class features - create CharacterFeature instances
        from characters.models import CharacterFeature
        from .class_features_data import get_class_features, get_subclass_features
        
        features_gained = []
        for level in range(old_level + 1, new_level + 1):
            # Get features for this level from the class features data
            class_features = get_class_features(character.character_class.name, level)
            
            for feature_data in class_features:
                # Create CharacterFeature instance
                CharacterFeature.objects.create(
                    character=character,
                    name=feature_data['name'],
                    feature_type='class',
                    description=feature_data['description'],
                    source=f"{character.character_class.name} Level {level}"
                )
                
                # Track for return value
                features_gained.append({
                    'level': level,
                    'name': feature_data['name'],
                    'description': feature_data['description'],
                    'type': 'class'
                })
            
            # Apply subclass features if character has a subclass
            if character.subclass:
                subclass_features = get_subclass_features(character.subclass, level)
                
                for feature_data in subclass_features:
                    # Create CharacterFeature instance
                    CharacterFeature.objects.create(
                        character=character,
                        name=feature_data['name'],
                        feature_type='class',
                        description=feature_data['description'],
                        source=f"{character.subclass} Level {level}"
                    )
                    
                    # Track for return value
                    features_gained.append({
                        'level': level,
                        'name': feature_data['name'],
                        'description': feature_data['description'],
                        'type': 'subclass'
                    })
        
        # Save changes
        character.save()
        self.campaign_character.save()
        self.level_ups_gained += levels_gained
        
        return {
            'levels_gained': levels_gained,
            'hp_increase': total_hp_increase,
            'new_max_hp': self.campaign_character.max_hp,
            'spell_slots': new_slots if new_slots else None,
            'asi_levels': levels_with_asi,
            'features_gained': features_gained
        }


class TreasureRoom(models.Model):
    """A treasure room in the campaign that rewards players"""
    ROOM_TYPES = [
        ('equipment', 'Equipment Room'),
        ('consumables', 'Consumables Room'),
        ('gold', 'Gold Room'),
        ('magical', 'Magic Item Room'),
        ('mystery', 'Mystery Room'),
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='treasure_rooms')
    encounter_number = models.IntegerField()  # After which encounter this appears
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    discovered = models.BooleanField(default=False)
    loot_distributed = models.BooleanField(default=False)
    
    # Rewards stored as JSON
    # {"items": [{"item_id": 1, "quantity": 1}, ...], "gold": 100, "xp_bonus": 50}
    rewards = models.JSONField(default=dict)
    
    discovered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['encounter_number']
        unique_together = ['campaign', 'encounter_number']
    
    def __str__(self):
        return f"Treasure Room {self.encounter_number} ({self.get_room_type_display()}) - {self.campaign.name}"
    
    def discover(self):
        """Mark treasure room as discovered"""
        if not self.discovered:
            self.discovered = True
            self.discovered_at = timezone.now()
            self.save()
    
    def distribute_loot(self, character_id, reward_index=None):
        """Distribute loot to a character"""
        if self.loot_distributed:
            return {"error": "Loot already distributed"}
        
        # For now, simple distribution - can be enhanced later
        # Mark as distributed if all rewards claimed
        self.loot_distributed = True
        self.save()
        
        return {"message": "Loot distributed", "rewards": self.rewards}


class TreasureRoomReward(models.Model):
    """Individual rewards in a treasure room that can be claimed by specific characters"""
    treasure_room = models.ForeignKey(TreasureRoom, on_delete=models.CASCADE, related_name='reward_items')
    item = models.ForeignKey('items.Item', on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    gold_amount = models.IntegerField(default=0)
    xp_bonus = models.IntegerField(default=0)
    
    claimed_by = models.ForeignKey(
        CampaignCharacter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='claimed_rewards'
    )
    claimed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-gold_amount', 'item']
    
    def __str__(self):
        if self.item:
            return f"{self.item.name} x{self.quantity} ({self.treasure_room})"
        elif self.gold_amount > 0:
            return f"{self.gold_amount} gold ({self.treasure_room})"
        elif self.xp_bonus > 0:
            return f"{self.xp_bonus} XP ({self.treasure_room})"
        return f"Reward ({self.treasure_room})"
    
    def claim(self, campaign_character):
        """Claim this reward for a character"""
        if self.claimed_by:
            raise ValueError("This reward has already been claimed")
        
        from django.utils import timezone
        self.claimed_by = campaign_character
        self.claimed_at = timezone.now()
        self.save()
        
        return {
            'reward_id': self.id,
            'item': self.item.name if self.item else None,
            'quantity': self.quantity,
            'gold': self.gold_amount,
            'xp_bonus': self.xp_bonus
        }


class RecruitableCharacter(models.Model):
    """Templates for characters that can be recruited during solo campaigns"""
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('legendary', 'Legendary'),
    ]
    
    name = models.CharField(max_length=100)
    character_class = models.ForeignKey('characters.CharacterClass', on_delete=models.PROTECT)
    race = models.ForeignKey('characters.CharacterRace', on_delete=models.PROTECT)
    background = models.ForeignKey('characters.CharacterBackground', on_delete=models.PROTECT, blank=True, null=True)
    
    # Personality/flavor
    personality_trait = models.TextField(blank=True, help_text="Personality trait or flavor text")
    recruitment_description = models.TextField(help_text="Description shown when this recruit is available")
    
    # Starting stats (optional override - stored as JSON)
    # {"strength": 15, "dexterity": 13, ...} - if empty, uses defaults
    starting_stats = models.JSONField(default=dict, blank=True)
    
    # Rarity (affects when they appear)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    
    # Optional: starting equipment (item IDs)
    starting_equipment = models.JSONField(default=list, blank=True, help_text="List of item IDs to give this recruit")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['rarity', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.character_class.get_name_display()} {self.race.get_name_display()}) - {self.get_rarity_display()}"


class RecruitmentRoom(models.Model):
    """A room where players can recruit party members (solo mode only)"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recruitment_rooms')
    encounter_number = models.IntegerField(help_text="After which encounter this recruitment room appears")
    
    # Available recruits (ManyToMany for multiple options)
    available_recruits = models.ManyToManyField(RecruitableCharacter, related_name='recruitment_rooms')
    
    discovered = models.BooleanField(default=False)
    recruit_selected = models.ForeignKey(
        CampaignCharacter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='recruitment_source',
        help_text="The campaign character that was recruited from this room"
    )
    
    discovered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['encounter_number']
        unique_together = ['campaign', 'encounter_number']
    
    def __str__(self):
        return f"Recruitment Room {self.encounter_number} - {self.campaign.name}"
    
    def discover(self):
        """Mark recruitment room as discovered"""
        if not self.discovered:
            self.discovered = True
            self.discovered_at = timezone.now()
            self.save()
