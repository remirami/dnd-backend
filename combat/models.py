from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
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
    
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='combat_sessions', blank=True, null=True, help_text="Optional encounter. If null, this is a practice/simulation session.")
    is_practice = models.BooleanField(default=False, help_text="True if this is a practice/simulation session")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    current_round = models.IntegerField(default=0)
    current_turn_index = models.IntegerField(default=0)  # Index in initiative order
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['encounter', 'status'], name='combat_enc_status_idx'),
            models.Index(fields=['status'], name='combat_status_idx'),
            models.Index(fields=['-started_at'], name='combat_started_idx'),
        ]
    
    def __str__(self):
        if self.encounter:
            return f"Combat: {self.encounter.name} (Round {self.current_round})"
        return f"Practice Combat (Round {self.current_round})"
    
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
        """Advance to the next turn and remove expired conditions"""
        participants = self.get_initiative_order()
        if not participants.exists():
            return None
        
        # Reset legendary actions and reactions for all participants at start of new round
        if self.current_turn_index == 0:
            for participant in participants:
                if participant.legendary_actions_max > 0:
                    participant.reset_legendary_actions()
                participant.reset_reaction()  # Reactions reset each round
        
        self.current_turn_index += 1
        
        # If we've gone through all participants, start a new round
        if self.current_turn_index >= participants.count():
            self.current_round += 1
            self.current_turn_index = 0
            # Reset legendary actions and reactions at start of new round
            for participant in participants:
                if participant.legendary_actions_max > 0:
                    participant.reset_legendary_actions()
                participant.reset_reaction()  # Reactions reset each round
        
        # Reset action economy for the new turn's participant
        current_participant = self.get_current_participant()
        if current_participant:
            current_participant.reset_turn()
        
        # Remove expired conditions
        self.remove_expired_conditions()
        
        self.save()
        return self.get_current_participant()
    
    def remove_expired_conditions(self):
        """Remove conditions that have expired"""
        for participant in self.participants.all():
            expired_applications = ConditionApplication.objects.filter(
                participant=participant,
                removed_at__isnull=True
            )
            
            for app in expired_applications:
                if app.is_expired(self.current_round):
                    # Check if condition should be removed
                    from .condition_effects import should_remove_condition
                    if should_remove_condition(participant, app.condition.name, 'end_of_turn'):
                        app.remove('end_of_turn')
                    elif app.duration_type == 'round' and app.expires_at_round and self.current_round > app.expires_at_round:
                        app.remove('duration_expired')

    
    def get_or_create_log(self):
        """Get or create combat log for this session"""
        log, created = CombatLog.objects.get_or_create(combat_session=self)
        return log
    
    def generate_log(self):
        """Generate/update combat log statistics"""
        log = self.get_or_create_log()
        return log.calculate_statistics()


class EnvironmentalEffect(models.Model):
    """Environmental effects applied to a combat session"""
    EFFECT_TYPES = [
        ('terrain', 'Terrain'),
        ('cover', 'Cover'),
        ('lighting', 'Lighting'),
        ('weather', 'Weather'),
        ('hazard', 'Hazard'),
    ]
    
    TERRAIN_TYPES = [
        ('rubble', 'Rubble'),
        ('mud', 'Mud'),
        ('snow', 'Snow'),
        ('thick_vegetation', 'Thick Vegetation'),
        ('ice', 'Ice'),
        ('swamp', 'Swamp'),
        ('quicksand', 'Quicksand'),
    ]
    
    COVER_TYPES = [
        ('half', 'Half Cover'),
        ('three_quarters', 'Three-Quarters Cover'),
        ('full', 'Full Cover'),
    ]
    
    LIGHTING_TYPES = [
        ('bright_light', 'Bright Light'),
        ('dim_light', 'Dim Light'),
        ('darkness', 'Darkness'),
        ('magical_darkness', 'Magical Darkness'),
    ]
    
    WEATHER_TYPES = [
        ('clear', 'Clear'),
        ('light_rain', 'Light Rain'),
        ('heavy_rain', 'Heavy Rain'),
        ('fog', 'Fog'),
        ('heavy_fog', 'Heavy Fog'),
        ('snow', 'Snow'),
        ('strong_wind', 'Strong Wind'),
    ]
    
    HAZARD_TYPES = [
        ('lava', 'Lava'),
        ('acid', 'Acid'),
        ('poison_gas', 'Poison Gas'),
        ('spike_pit', 'Spike Pit'),
        ('electrified_water', 'Electrified Water'),
    ]
    
    combat_session = models.ForeignKey('CombatSession', on_delete=models.CASCADE, related_name='environmental_effects')
    effect_type = models.CharField(max_length=20, choices=EFFECT_TYPES)
    
    # Terrain
    terrain_type = models.CharField(max_length=20, choices=TERRAIN_TYPES, blank=True, null=True)
    
    # Cover (applied to specific areas or participants)
    cover_type = models.CharField(max_length=20, choices=COVER_TYPES, blank=True, null=True)
    cover_area_x = models.IntegerField(blank=True, null=True, help_text="X coordinate of cover area")
    cover_area_y = models.IntegerField(blank=True, null=True, help_text="Y coordinate of cover area")
    cover_area_radius = models.IntegerField(blank=True, null=True, help_text="Radius of cover area in feet")
    
    # Lighting
    lighting_type = models.CharField(max_length=20, choices=LIGHTING_TYPES, blank=True, null=True)
    lighting_area_x = models.IntegerField(blank=True, null=True)
    lighting_area_y = models.IntegerField(blank=True, null=True)
    lighting_area_radius = models.IntegerField(blank=True, null=True)
    
    # Weather (applies to entire combat)
    weather_type = models.CharField(max_length=20, choices=WEATHER_TYPES, blank=True, null=True)
    
    # Hazards
    hazard_type = models.CharField(max_length=20, choices=HAZARD_TYPES, blank=True, null=True)
    hazard_area_x = models.IntegerField(blank=True, null=True)
    hazard_area_y = models.IntegerField(blank=True, null=True)
    hazard_area_radius = models.IntegerField(blank=True, null=True)
    
    # General properties
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.effect_type == 'terrain':
            return f"{self.get_terrain_type_display()} - {self.combat_session}"
        elif self.effect_type == 'cover':
            return f"{self.get_cover_type_display()} - {self.combat_session}"
        elif self.effect_type == 'lighting':
            return f"{self.get_lighting_type_display()} - {self.combat_session}"
        elif self.effect_type == 'weather':
            return f"{self.get_weather_type_display()} - {self.combat_session}"
        elif self.effect_type == 'hazard':
            return f"{self.get_hazard_type_display()} - {self.combat_session}"
        return f"{self.get_effect_type_display()} - {self.combat_session}"


class ParticipantPosition(models.Model):
    """Tracks participant positions for environmental effects"""
    participant = models.OneToOneField('CombatParticipant', on_delete=models.CASCADE, related_name='position')
    x = models.IntegerField(default=0, help_text="X coordinate in feet")
    y = models.IntegerField(default=0, help_text="Y coordinate in feet")
    z = models.IntegerField(default=0, help_text="Z coordinate (height) in feet")
    
    # Current environmental effects at this position
    current_terrain = models.CharField(max_length=20, blank=True, null=True)
    current_cover = models.CharField(max_length=20, blank=True, null=True)
    current_lighting = models.CharField(max_length=20, blank=True, null=True)
    current_hazards = models.JSONField(default=list, blank=True, help_text="List of hazard types at this position")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.participant.get_name()} at ({self.x}, {self.y}, {self.z})"
    
    def distance_to(self, other_position):
        """Calculate distance to another position"""
        dx = self.x - other_position.x
        dy = self.y - other_position.y
        dz = self.z - other_position.z
        return int((dx**2 + dy**2 + dz**2)**0.5)
    
    def is_in_area(self, center_x, center_y, radius):
        """Check if position is within an area"""
        dx = self.x - center_x
        dy = self.y - center_y
        distance = (dx**2 + dy**2)**0.5
        return distance <= radius
    
    def trigger_opportunity_attack(self, attacker, target, movement_distance=0):
        """
        Trigger an opportunity attack from attacker against target.
        
        Args:
            attacker: CombatParticipant making the opportunity attack
            target: CombatParticipant leaving attacker's reach
            movement_distance: Distance target is moving (for reach calculations)
        
        Returns:
            dict: Result of the opportunity attack
        """
        if not attacker.can_make_opportunity_attack(target):
            return {
                'success': False,
                'reason': 'Cannot make opportunity attack (reaction used or not eligible)'
            }
        
        # Check if target used Disengage action (would prevent opportunity attacks)
        # This would need to be tracked - simplified for now
        
        # Mark reaction as used
        attacker.use_reaction()
        
        # Create opportunity attack action
        opportunity_attack = CombatAction.objects.create(
            combat_session=self,
            actor=attacker,
            target=target,
            action_type='opportunity_attack',
            round_number=self.current_round,
            turn_number=self.current_turn_index,
            description=f"{attacker.get_name()} makes an opportunity attack against {target.get_name()}"
        )
        
        return {
            'success': True,
            'action_id': opportunity_attack.id,
            'message': f"{attacker.get_name()} makes an opportunity attack against {target.get_name()}"
        }
    

    def get_combat_report(self):
        """Generate a comprehensive combat report"""
        log = self.get_or_create_log()
        log.calculate_statistics()
        
        participants = self.participants.all()
        actions = self.actions.all().order_by('round_number', 'turn_number', 'created_at')
        
        report = {
            'session_id': self.id,
            'encounter': {
                'name': self.encounter.name,
                'description': self.encounter.description,
                'location': self.encounter.location,
            },
            'summary': {
                'status': self.get_status_display(),
                'rounds': log.total_rounds,
                'turns': log.total_turns,
                'duration_seconds': log.duration_seconds,
                'duration_formatted': self._format_duration(log.duration_seconds),
                'started_at': self.started_at.isoformat() if self.started_at else None,
                'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            },
            'statistics': {
                'total_damage_dealt': log.total_damage_dealt,
                'total_damage_received': log.total_damage_received,
                'total_healing': log.total_healing,
                'actions_by_type': log.actions_by_type,
                'damage_by_type': log.damage_by_type,
                'spells_cast': log.spells_cast,
            },
            'participants': [
                {
                    'id': p.id,
                    'name': p.get_name(),
                    'type': p.get_participant_type_display(),
                    'stats': log.participant_stats.get(p.id, {}),
                }
                for p in participants
            ],
            'outcomes': {
                'victors': [
                    {'id': pid, 'name': log.participant_stats.get(pid, {}).get('name', 'Unknown')}
                    for pid in log.victors
                ],
                'casualties': [
                    {'id': pid, 'name': log.participant_stats.get(pid, {}).get('name', 'Unknown')}
                    for pid in log.casualties
                ],
            },
            'timeline': [
                {
                    'round': action.round_number,
                    'turn': action.turn_number,
                    'timestamp': action.created_at.isoformat(),
                    'actor': action.actor.get_name(),
                    'action_type': action.get_action_type_display(),
                    'target': action.target.get_name() if action.target else None,
                    'details': {
                        'attack_name': action.attack_name,
                        'hit': action.hit,
                        'damage': action.damage_amount,
                        'critical': action.critical,
                        'description': action.description,
                    }
                }
                for action in actions
            ],
        }
        
        return report
    
    def _format_duration(self, seconds):
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"


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
    
    # Optional name override (used for practice mode enemies without EncounterEnemy)
    name = models.CharField(max_length=100, blank=True, help_text="Optional name override for practice mode")
    
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
    
    # Concentration (for spellcasters)
    is_concentrating = models.BooleanField(default=False)
    concentration_spell = models.CharField(max_length=100, blank=True)  # Name of spell being concentrated on
    
    # Legendary actions (for powerful enemies)
    legendary_actions_remaining = models.IntegerField(default=0)  # Legendary actions available this round
    legendary_actions_max = models.IntegerField(default=0)  # Maximum legendary actions per round
    
    # Spell slot tracking for enemies (JSONField to track remaining uses)
    spell_uses_remaining = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tracks spell uses for enemy spellcasters. Format: {'Fireball': 3, 'Power Word Kill': 1}"
    )
    
    # Phase 1: Position tracking for AOE targeting
    position_x = models.IntegerField(default=0, help_text="X coordinate on battlefield grid (in feet)")
    position_y = models.IntegerField(default=0, help_text="Y coordinate on battlefield grid (in feet)")
    
    # Phase 2: Grappling mechanics
    is_grappling = models.BooleanField(default=False, help_text="True if this participant is grappling someone")
    grappled_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='grappling_targets',
        help_text="Participant who has grappled this one"
    )
    
    # Phase 3: Cover system
    COVER_CHOICES = [
        ('none', 'No Cover'),
        ('half', 'Half Cover'),
        ('three_quarters', 'Three-Quarters Cover'),
        ('full', 'Full Cover'),
    ]
    cover_type = models.CharField(
        max_length=20,
        choices=COVER_CHOICES,
        default='none',
        help_text="Type of cover this participant has"
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-initiative', 'id']
        unique_together = ['combat_session', 'character', 'encounter_enemy']
    
    def __str__(self):
        name = self.get_name()
        return f"{name} (Initiative: {self.initiative})"
    
    def clean(self):
        """Validate combat participant data"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate HP
        if hasattr(self, 'current_hp') and self.current_hp < 0:
            errors['current_hp'] = 'Current HP cannot be negative'
        
        if hasattr(self, 'max_hp') and self.max_hp < 1:
            errors['max_hp'] = 'Max HP must be at least 1'
        
        if hasattr(self, 'current_hp') and hasattr(self, 'max_hp') and self.current_hp > self.max_hp:
            errors['current_hp'] = f'Current HP ({self.current_hp}) cannot exceed max HP ({self.max_hp})'
        
        # Validate participant type has corresponding entity
        if self.participant_type == 'character' and not self.character:
            errors['character'] = 'Character must be specified for character participant type'
        
        if self.participant_type == 'enemy' and not self.encounter_enemy:
            errors['encounter_enemy'] = 'Enemy must be specified for enemy participant type'
        
        # Validate death saves are in range
        if hasattr(self, 'death_save_successes') and not (0 <= self.death_save_successes <= 3):
            errors['death_save_successes'] = 'Death save successes must be between 0 and 3'
        
        if hasattr(self, 'death_save_failures') and not (0 <= self.death_save_failures <= 3):
            errors['death_save_failures'] = 'Death save failures must be between 0 and 3'
        
        if errors:
            raise ValidationError(errors)
    
    def get_name(self):
        """Get the name of the participant"""
        # Check for explicit name override first (practice mode)
        if self.name:
            return self.name
        # Then check for linked entities
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
    
    def get_equipped_weapon(self, slot='main_hand'):
        """Get equipped weapon from character inventory"""
        if not self.character:
            return None
        
        from characters.models import CharacterItem
        from items.models import Weapon
        
        try:
            character_item = CharacterItem.objects.get(
                character=self.character,
                is_equipped=True,
                equipment_slot=slot,
                item__weapon__isnull=False
            )
            return character_item.item.weapon
        except CharacterItem.DoesNotExist:
            return None
    
    def get_equipped_armor(self):
        """Get equipped armor from character inventory"""
        if not self.character:
            return None
        
        from characters.models import CharacterItem
        from items.models import Armor
        
        try:
            character_item = CharacterItem.objects.get(
                character=self.character,
                is_equipped=True,
                equipment_slot='armor',
                item__armor__isnull=False
            )
            return character_item.item.armor
        except CharacterItem.DoesNotExist:
            return None
    
    def get_equipped_shield(self):
        """Get equipped shield from character inventory"""
        if not self.character:
            return None
        
        from characters.models import CharacterItem
        from items.models import Armor
        
        try:
            character_item = CharacterItem.objects.get(
                character=self.character,
                is_equipped=True,
                equipment_slot='shield',
                item__armor__isnull=False,
                item__armor__armor_type='shield'
            )
            return character_item.item.armor
        except CharacterItem.DoesNotExist:
            return None
    
    def can_cast_enemy_spell(self, spell_name):
        """
        Check if an enemy has spell uses remaining for the given spell.
        
        Args:
            spell_name: Name of the spell to check
        
        Returns:
            bool: True if spell can be cast, False otherwise
        """
        if not self.encounter_enemy:
            # Not an enemy - no restrictions
            return True
        
        # Get enemy's spell from stat block
        enemy = self.encounter_enemy.enemy
        enemy_spell = enemy.spells.filter(name__iexact=spell_name).first()
        
        if not enemy_spell:
            # Spell not in enemy's list
            return False
        
        # Check if we've tracked uses for this spell yet
        if spell_name not in self.spell_uses_remaining:
            # First time casting - initialize from stat block
            spell_slot = enemy_spell.slots.first()
            if spell_slot:
                self.spell_uses_remaining[spell_name] = spell_slot.uses
                self.save()
                return spell_slot.uses > 0
            else:
                # No slot information means "at will" - always available
                return True
        
        # Check remaining uses
        return self.spell_uses_remaining.get(spell_name, 0) > 0
    
    def use_enemy_spell(self, spell_name):
        """
        Decrement spell uses for an enemy after casting.
        
        Args:
            spell_name: Name of the spell that was cast
        """
        if not self.encounter_enemy:
            return  # Not an enemy
        
        if spell_name in self.spell_uses_remaining:
            if self.spell_uses_remaining[spell_name] > 0:
                self.spell_uses_remaining[spell_name] -= 1
                self.save()
    
    def reset_enemy_spell_slots(self):
        """Reset all enemy spell uses (for long rest or new day)"""
        if self.encounter_enemy:
            self.spell_uses_remaining = {}
            self.save()
    
    def get_magic_item_bonuses(self):
        """Get bonuses from equipped magic items"""
        if not self.character:
            return {
                'to_hit': 0,
                'to_damage': 0,
                'to_ac': 0,
                'to_saves': 0
            }
        
        from characters.models import CharacterItem
        from items.models import MagicItem
        
        bonuses = {
            'to_hit': 0,
            'to_damage': 0,
            'to_ac': 0,
            'to_saves': 0
        }
        
        equipped_magic_items = CharacterItem.objects.filter(
            character=self.character,
            is_equipped=True,
            item__magicitem__isnull=False
        ).select_related('item__magicitem')
        
        for char_item in equipped_magic_items:
            magic_item = char_item.item.magicitem
            bonuses['to_hit'] += magic_item.bonus_to_hit
            bonuses['to_damage'] += magic_item.bonus_to_damage
            bonuses['to_ac'] += magic_item.bonus_to_ac
            bonuses['to_saves'] += magic_item.bonus_to_saves
        
        return bonuses
    
    def calculate_effective_ac(self, cover_bonus=0):
        """Calculate effective AC including armor, magic items, and cover"""
        base_ac = self.armor_class
        
        # Get armor bonuses
        armor = self.get_equipped_armor()
        shield = self.get_equipped_shield()
        
        if armor:
            # Armor provides base AC
            base_ac = armor.base_ac
            
            # Add DEX modifier if applicable
            if armor.max_dex_bonus is not None:
                dex_mod = min(self.get_ability_modifier('DEX'), armor.max_dex_bonus)
            else:
                dex_mod = self.get_ability_modifier('DEX')
            
            # Light and medium armor add DEX, heavy doesn't
            if armor.armor_type in ['light', 'medium']:
                base_ac += dex_mod
            elif armor.armor_type == 'heavy':
                # Heavy armor doesn't add DEX
                pass
        
        # Add shield bonus
        if shield:
            base_ac += shield.base_ac
        
        # Add magic item bonuses
        magic_bonuses = self.get_magic_item_bonuses()
        base_ac += magic_bonuses['to_ac']
        
        # Add cover bonus
        base_ac += cover_bonus
        
        return base_ac
    
    def take_damage(self, amount, damage_type=None, check_concentration=True):
        """Apply damage to this participant"""
        # Check for resistances/immunities
        if damage_type:
            # This would check resistances - simplified for now
            pass
        
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp <= 0:
            self.is_active = False
        
        # Check concentration if taking damage while concentrating
        concentration_broken = False
        if check_concentration and self.is_concentrating and amount > 0:
            concentration_broken, _, _, _ = self.check_concentration(amount)
        
        self.save()
        return self.current_hp, concentration_broken
    
    def take_damage_simple(self, amount, damage_type=None):
        """Simple version that doesn't check concentration (for backward compatibility)"""
        return self.take_damage(amount, damage_type, check_concentration=False)[0]
    
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
        # Reset legendary actions at start of round (handled in next_turn)
        self.save()
    
    def make_death_save(self, roll=None):
        """
        Make a death saving throw
        Returns: (success, is_stable, is_dead, message)
        """
        from .utils import roll_d20
        
        if self.current_hp > 0:
            return False, False, False, "Character is not unconscious"
        
        if roll is None:
            roll, _ = roll_d20()
        
        # Natural 20 = instant success (2 successes) and regain 1 HP
        if roll == 20:
            self.death_save_successes = min(3, self.death_save_successes + 2)
            if self.death_save_successes >= 3:
                self.current_hp = 1
                self.is_active = True
                self.death_save_successes = 0
                self.death_save_failures = 0
                self.save()
                return True, True, False, "Natural 20! Character stabilizes and regains 1 HP!"
        
        # Natural 1 = 2 failures
        elif roll == 1:
            self.death_save_failures = min(3, self.death_save_failures + 2)
            if self.death_save_failures >= 3:
                self.save()
                return False, False, True, "Natural 1! Two failures. Character dies."
        
        # Normal roll: 10+ = success, 9- = failure
        elif roll >= 10:
            self.death_save_successes += 1
            if self.death_save_successes >= 3:
                self.death_save_successes = 0
                self.death_save_failures = 0
                self.save()
                return True, True, False, "Death save succeeded. Character stabilizes."
        else:
            self.death_save_failures += 1
            if self.death_save_failures >= 3:
                self.save()
                return False, False, True, "Death save failed. Character dies."
        
        self.save()
        return (roll >= 10), False, False, f"Death save: {roll} ({'Success' if roll >= 10 else 'Failure'})"
    
    def check_concentration(self, damage_amount=0):
        """
        Check if concentration is broken due to damage
        DC = 10 or half damage, whichever is higher
        Returns: (concentration_broken, save_roll, save_dc, message)
        """
        if not self.is_concentrating:
            return False, None, None, "Not concentrating on any spell"
        
        from .utils import roll_d20, calculate_saving_throw
        
        # Calculate DC: 10 or half damage, whichever is higher
        save_dc = max(10, damage_amount // 2)
        
        # Roll CON saving throw
        roll, _ = roll_d20()
        con_mod = self.get_ability_modifier('CON')
        proficiency_bonus = self.character.proficiency_bonus if self.character else 2
        proficiency = False  # Simplified - should check actual CON save proficiency
        
        save_total, _ = calculate_saving_throw(roll, con_mod, proficiency_bonus, proficiency)
        concentration_broken = save_total < save_dc
        
        if concentration_broken:
            self.is_concentrating = False
            spell_name = self.concentration_spell
            self.concentration_spell = ""
            self.save()
            return True, save_total, save_dc, f"Concentration broken! Lost concentration on {spell_name}"
        
        return False, save_total, save_dc, f"Concentration maintained (DC {save_dc}, rolled {save_total})"
    
    def use_legendary_action(self, action_cost=1):
        """Use a legendary action"""
        if action_cost < 1:
            return False, "Legendary action cost must be at least 1"
        
        if self.legendary_actions_remaining < action_cost:
            return False, "Not enough legendary actions remaining"
        
        self.legendary_actions_remaining -= action_cost
        self.save()
        return True, f"Used {action_cost} legendary action(s). {self.legendary_actions_remaining} remaining."
    
    def reset_legendary_actions(self):
        """Reset legendary actions at end of turn"""
        self.legendary_actions_remaining = self.legendary_actions_max
        self.save()
    
    def reset_turn(self):
        """Reset action economy at start of turn"""
        self.action_used = False
        self.bonus_action_used = False
        self.reaction_used = False
        self.movement_used = 0
        self.save()
    
    def reset_reaction(self):
        """Reset reaction at start of round (reactions reset each round)"""
        self.reaction_used = False
        self.save()
    
    def can_use_reaction(self):
        """Check if participant can use a reaction"""
        return not self.reaction_used and self.is_active
    
    def use_reaction(self):
        """Mark reaction as used"""
        self.reaction_used = True
        self.save()
    
    def get_reach(self):
        """Get melee reach in feet (default 5 feet)"""
        # Could be modified by weapons, size, etc.
        return 5
    
    def can_make_opportunity_attack(self, target):
        """
        Check if this participant can make an opportunity attack against target.
        
        Args:
            target: CombatParticipant instance
        
        Returns:
            bool: True if opportunity attack is possible
        """
        # Must have reaction available
        if not self.can_use_reaction():
            return False
        
        # Must be active
        if not self.is_active:
            return False
        
        # Target must be active
        if not target.is_active:
            return False
        
        # Must be within reach (simplified - assumes 5 feet)
        # In a full implementation, would check actual positions
        return True


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
        ('opportunity_attack', 'Opportunity Attack'),
        ('reaction', 'Reaction'),
        ('legendary_action', 'Legendary Action'),
        ('death_save', 'Death Saving Throw'),
        ('concentration_check', 'Concentration Check'),
        ('other', 'Other'),
    ]
    
    combat_session = models.ForeignKey(CombatSession, on_delete=models.CASCADE, related_name='actions')
    actor = models.ForeignKey(CombatParticipant, on_delete=models.SET_NULL, related_name='actions_taken', null=True, blank=True)
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
    save_type = models.CharField(max_length=3, blank=True, null=True)  # DEX, CON, WIS, etc.
    save_dc = models.IntegerField(blank=True, null=True)
    save_roll = models.IntegerField(blank=True, null=True)
    save_success = models.BooleanField(blank=True, null=True)
    
    # Other details
    description = models.TextField(blank=True)
    round_number = models.IntegerField()
    turn_number = models.IntegerField()  # Turn within the round
    
    # Phase 3: Advanced features
    is_opportunity_attack = models.BooleanField(default=False)
    is_reaction = models.BooleanField(default=False)
    is_legendary_action = models.BooleanField(default=False)
    legendary_action_cost = models.IntegerField(default=0)  # Cost in legendary action points
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['round_number', 'turn_number', 'created_at']
    
    def __str__(self):
        return f"{self.actor.get_name()} - {self.get_action_type_display()} (Round {self.round_number})"


class CombatLog(models.Model):
    """Enhanced combat logging with statistics and analytics"""
    combat_session = models.OneToOneField(CombatSession, on_delete=models.CASCADE, related_name='log')
    
    # Basic statistics
    total_rounds = models.IntegerField(default=0)
    total_turns = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0, help_text="Real-time duration in seconds")
    
    # Damage statistics
    total_damage_dealt = models.IntegerField(default=0)
    total_damage_received = models.IntegerField(default=0)
    total_healing = models.IntegerField(default=0)
    
    # Action statistics (JSON fields for flexibility)
    actions_by_type = models.JSONField(default=dict, help_text="Count of actions by type")
    damage_by_type = models.JSONField(default=dict, help_text="Damage totals by damage type")
    spells_cast = models.JSONField(default=dict, help_text="Spells cast with counts")
    
    # Participant statistics (JSON field)
    participant_stats = models.JSONField(default=dict, help_text="Statistics per participant")
    
    # Combat outcomes
    victors = models.JSONField(default=list, help_text="List of participant IDs who survived")
    casualties = models.JSONField(default=list, help_text="List of participant IDs who died/unconscious")
    
    # Sharing
    share_token = models.CharField(max_length=32, unique=True, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Combat Log: {self.combat_session.encounter.name} ({self.total_rounds} rounds)"
    
    def calculate_statistics(self):
        """Calculate and update all statistics from combat actions"""
        session = self.combat_session
        actions = session.actions.all()
        
        # Basic counts
        self.total_rounds = session.current_round
        self.total_turns = actions.count()
        
        # Calculate duration if combat has ended
        if session.ended_at and session.started_at:
            duration = session.ended_at - session.started_at
            self.duration_seconds = int(duration.total_seconds())
        
        # Initialize counters
        actions_by_type = {}
        damage_by_type = {}
        spells_cast = {}
        participant_stats = {}
        
        # Initialize participant stats
        for participant in session.participants.all():
            participant_stats[participant.id] = {
                'name': participant.get_name(),
                'damage_dealt': 0,
                'damage_received': 0,
                'healing_received': 0,
                'attacks_made': 0,
                'attacks_hit': 0,
                'attacks_missed': 0,
                'critical_hits': 0,
                'spells_cast': 0,
                'spells_by_name': {},
                'actions_by_type': {},
                'start_hp': participant.max_hp,
                'end_hp': participant.current_hp,
                'status': 'alive' if participant.is_active else 'unconscious',
            }
        
        # Process all actions
        for action in actions:
            # Count actions by type
            action_type = action.action_type
            actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1
            
            # Track participant actions
            actor_id = action.actor.id
            if actor_id in participant_stats:
                participant_stats[actor_id]['actions_by_type'][action_type] = \
                    participant_stats[actor_id]['actions_by_type'].get(action_type, 0) + 1
            
            # Track damage
            if action.damage_amount:
                # Damage dealt
                if actor_id in participant_stats:
                    participant_stats[actor_id]['damage_dealt'] += action.damage_amount
                
                # Damage received
                if action.target:
                    target_id = action.target.id
                    if target_id in participant_stats:
                        participant_stats[target_id]['damage_received'] += action.damage_amount
                
                # Damage by type
                if action.damage_type:
                    damage_type_name = action.damage_type.name
                    damage_by_type[damage_type_name] = damage_by_type.get(damage_type_name, 0) + action.damage_amount
            
            # Track healing (if action type is heal or spell with healing)
            if action.action_type in ['heal', 'spell'] and action.damage_amount and action.damage_amount < 0:
                # Negative damage is healing
                healing_amount = abs(action.damage_amount)
                if action.target and action.target.id in participant_stats:
                    participant_stats[action.target.id]['healing_received'] += healing_amount
            
            # Track attacks
            if action.action_type == 'attack':
                if actor_id in participant_stats:
                    participant_stats[actor_id]['attacks_made'] += 1
                    if action.hit:
                        participant_stats[actor_id]['attacks_hit'] += 1
                        if action.critical:
                            participant_stats[actor_id]['critical_hits'] += 1
                    else:
                        participant_stats[actor_id]['attacks_missed'] += 1
            
            # Track spells
            if action.action_type == 'spell':
                if actor_id in participant_stats:
                    participant_stats[actor_id]['spells_cast'] += 1
                    spell_name = action.attack_name
                    participant_stats[actor_id]['spells_by_name'][spell_name] = \
                        participant_stats[actor_id]['spells_by_name'].get(spell_name, 0) + 1
                    spells_cast[spell_name] = spells_cast.get(spell_name, 0) + 1
        
        # Calculate totals
        self.total_damage_dealt = sum(
            stats['damage_dealt'] for stats in participant_stats.values()
        )
        self.total_damage_received = sum(
            stats['damage_received'] for stats in participant_stats.values()
        )
        self.total_healing = sum(
            stats.get('healing_received', 0) for stats in participant_stats.values()
        )
        
        # Store statistics
        self.actions_by_type = actions_by_type
        self.damage_by_type = damage_by_type
        self.spells_cast = spells_cast
        self.participant_stats = participant_stats
        
        # Determine victors and casualties
        self.victors = [
            pid for pid, stats in participant_stats.items()
            if stats['status'] == 'alive'
        ]
        self.casualties = [
            pid for pid, stats in participant_stats.items()
            if stats['status'] == 'unconscious'
        ]
        
        self.save()
        return self


class ConditionApplication(models.Model):
    """Tracks condition applications with duration"""
    DURATION_TYPES = [
        ('instant', 'Instant'),  # No duration, removed manually
        ('turn', 'Turn'),  # Removed at end of turn
        ('round', 'Round'),  # Removed after N rounds
        ('spell', 'Spell'),  # Removed when spell ends
        ('saving_throw', 'Saving Throw'),  # Removed on successful save
        ('concentration', 'Concentration'),  # Removed when concentration ends
    ]
    
    participant = models.ForeignKey(CombatParticipant, on_delete=models.CASCADE, related_name='condition_applications')
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)
    applied_round = models.IntegerField(default=1)
    applied_turn = models.IntegerField(default=1)
    
    # Duration tracking
    duration_type = models.CharField(max_length=20, choices=DURATION_TYPES, default='instant')
    duration_rounds = models.IntegerField(default=0, help_text="Number of rounds (0 = until removed manually)")
    expires_at_round = models.IntegerField(null=True, blank=True, help_text="Round when condition expires")
    
    # Source information
    source_type = models.CharField(max_length=50, blank=True, help_text="e.g., 'spell', 'ability', 'attack'")
    source_name = models.CharField(max_length=100, blank=True, help_text="e.g., 'Hold Person', 'Stunning Strike'")
    
    # Removal tracking
    removed_at = models.DateTimeField(null=True, blank=True)
    removal_reason = models.CharField(max_length=50, blank=True, help_text="e.g., 'end_of_turn', 'saving_throw_success'")
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['participant', 'condition', 'applied_at']  # Prevent duplicates
    
    def __str__(self):
        return f"{self.participant.get_name()} - {self.condition.get_name_display()} (Round {self.applied_round})"
    
    def is_expired(self, current_round):
        """Check if condition has expired"""
        if self.removed_at:
            return True
        
        if self.duration_type == 'round' and self.expires_at_round:
            return current_round > self.expires_at_round
        
        return False
    
    def remove(self, reason='manual'):
        """Mark condition as removed"""
        self.removed_at = timezone.now()
        self.removal_reason = reason
        self.save()
        
        # Remove from participant's conditions
        self.participant.conditions.remove(self.condition)
