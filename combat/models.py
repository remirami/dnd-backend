import random
import re

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from bestiary.models import Condition, DamageType
from characters.models import Character
from encounters.models import Encounter, EncounterEnemy


class CombatSession(models.Model):
    """Represents an active combat encounter"""
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='combat_sessions',
        help_text="User who created this combat session"
    )
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
    
    def get_initiative_order(self):
        """Get all participants ordered by initiative (highest first)"""
        return self.participants.all().order_by('-initiative', 'id')

    def get_current_participant(self):
        """Get the participant whose turn it is from the stable initiative order"""
        participants = list(self.get_initiative_order())
        if participants and 0 <= self.current_turn_index < len(participants):
            p = participants[self.current_turn_index]
            if not p.is_dead() and not p.is_spell_object():
                return p
        return None

    def next_turn(self):
        """Advance to the next turn, skipping defeated participants, and remove expired conditions"""
        participants = list(self.get_initiative_order())
        if not participants:
            return None
        
        # 5e Legendary Action Weaving:
        # At the end of another creature's turn, an active boss can use a legendary action.
        previous_participant = self.get_current_participant()
        if previous_participant and previous_participant.is_active:
            boss = self.participants.filter(
                participant_type='enemy',
                is_active=True,
                current_hp__gt=0,
                legendary_actions_remaining__gt=0
            ).exclude(id=previous_participant.id).first()
            if not boss:
                boss = self.participants.filter(
                    participant_type='enemy',
                    is_active=True,
                    current_hp__gt=0,
                    legendary_actions_max__gt=0
                ).exclude(id=previous_participant.id).first()
            if boss and not boss.is_incapacitated():
                from combat.combat_ai import execute_ai_legendary_action
                try:
                    execute_ai_legendary_action(self, boss, trigger_participant=previous_participant)
                except Exception:
                    pass

        # Advance turn index, wrapping around to new rounds and skipping dead/defeated participants
        max_steps = len(participants) + 1
        steps = 0
        found_active = False
        while steps < max_steps:
            steps += 1
            self.current_turn_index += 1
            
            # If we've gone through all participants, start a new round
            if self.current_turn_index >= len(participants):
                self.current_round += 1
                self.current_turn_index = 0
                for participant in participants:
                    if participant.legendary_actions_max > 0:
                        participant.reset_legendary_actions()
                    participant.reset_reaction()

                from combat.summoning import decrement_summon_durations
                try:
                    decrement_summon_durations(self)
                except Exception:
                    pass

            candidate = participants[self.current_turn_index]
            # Skip dead/defeated participants and persistent spell objects (which act on caster's turn)
            if candidate.is_dead() or candidate.is_spell_object():
                continue
            found_active = True
            break
        
        if not found_active:
            self.save()
            return None
        
        # Reset action economy for the new turn's participant
        current_participant = self.get_current_participant()
        if current_participant:
            current_participant.reset_turn()
        
        # Remove expired conditions
        self.remove_expired_conditions()
        
        # 5e Grapple reach check: Release any grapples if separated beyond reach
        self.clean_grapple_states()
        
        self.save()
        return current_participant
    
    def clean_grapple_states(self):
        """
        5e Rule (PHB p. 195): The condition ends if an effect removes the grappled creature
        from the reach of the grappler or grappling effect.
        Verify that all actively grappled creatures are within melee reach of their grappler.
        """
        for p in self.participants.filter(is_active=True):
            if p.grappled_by:
                reach = p.grappled_by.get_reach() if hasattr(p.grappled_by, 'get_reach') else 5
                dist = p.get_distance_to(p.grappled_by)
                if dist > reach:
                    p.release_grapple()
            elif p.is_grappling:
                reach = p.get_reach() if hasattr(p, 'get_reach') else 5
                for victim in list(p.grappling_targets.all()):
                    if p.get_distance_to(victim) > reach:
                        p.release_grapple()

    
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

    
    def sanitize_grid_positions(self):
        """
        Verify that all living combatants fit completely inside arena bounds (0..45ft X, 0..35ft Y)
        and that NO square of their multi-tile footprint overlaps an impassable solid obstacle.
        If an overlap or out-of-bounds is detected, nudges the creature to the nearest valid tile.
        """
        from combat.battlefield import is_tile_solid
        all_participants = list(self.participants.filter(is_active=True, current_hp__gt=0).order_by('id'))
        
        # Track all occupied cells by creature
        occupied_by = {}
        for p in all_participants:
            tiles = p.get_size_dimensions()['tiles'] if hasattr(p, 'get_size_dimensions') else 1
            for ox in range(tiles):
                for oy in range(tiles):
                    cell = (p.position_x + ox * 5, p.position_y + oy * 5)
                    occupied_by[cell] = p.id

        changed = False
        for p in all_participants:
            tiles = p.get_size_dimensions()['tiles'] if hasattr(p, 'get_size_dimensions') else 1
            
            def is_valid(tx, ty):
                for ox in range(tiles):
                    for oy in range(tiles):
                        cx = tx + ox * 5
                        cy = ty + oy * 5
                        if cx < 0 or cx > 45 or cy < 0 or cy > 35:
                            return False
                        if is_tile_solid(self.id or 0, cx // 5, cy // 5):
                            return False
                        other_id = occupied_by.get((cx, cy))
                        if other_id and other_id != p.id:
                            return False
                return True

            if not is_valid(p.position_x, p.position_y):
                # Find closest valid tile within widening search radius
                for radius in range(1, 10):
                    candidates = []
                    for dx in range(-radius, radius + 1):
                        for dy in range(-radius, radius + 1):
                            if max(abs(dx), abs(dy)) == radius:
                                nx = p.position_x + dx * 5
                                ny = p.position_y + dy * 5
                                if is_valid(nx, ny):
                                    candidates.append((nx, ny))
                    if candidates:
                        # Choose candidate closest to current position
                        best_cand = min(candidates, key=lambda pt: (pt[0] - p.position_x)**2 + (pt[1] - p.position_y)**2)
                        for ox in range(tiles):
                            for oy in range(tiles):
                                occupied_by.pop((p.position_x + ox * 5, p.position_y + oy * 5), None)
                        p.position_x, p.position_y = best_cand
                        p.save(update_fields=['position_x', 'position_y'])
                        for ox in range(tiles):
                            for oy in range(tiles):
                                occupied_by[(p.position_x + ox * 5, p.position_y + oy * 5)] = p.id
                        changed = True
                        break
        return changed

    def initialize_grid_positions(self):
        """
        Deploy participants to tactical starting zones on a 10x8 grid (50ft x 40ft).
        Ensures multi-tile footprints (Large 2x2, Huge 3x3) never spawn overlapping solid obstacles
        or extending out of arena bounds.
        """
        from combat.battlefield import is_tile_solid
        party = list(self.participants.filter(participant_type='character').order_by('id'))
        enemies = list(self.participants.filter(participant_type='enemy').order_by('id'))
        
        occupied = set()
        for p in self.participants.filter(is_active=True, current_hp__gt=0):
            if p.position_x > 0 or p.position_y > 0:
                p_tiles = p.get_size_dimensions()['tiles'] if hasattr(p, 'get_size_dimensions') else 1
                for ox in range(p_tiles):
                    for oy in range(p_tiles):
                        occupied.add((p.position_x + ox * 5, p.position_y + oy * 5))

        def find_spawn_spot(creature, candidate_pts):
            c_tiles = creature.get_size_dimensions()['tiles'] if hasattr(creature, 'get_size_dimensions') else 1
            for cx, cy in candidate_pts:
                valid = True
                for ox in range(c_tiles):
                    for oy in range(c_tiles):
                        fx = cx + ox * 5
                        fy = cy + oy * 5
                        if fx < 0 or fx > 45 or fy < 0 or fy > 35:
                            valid = False
                            break
                        if is_tile_solid(self.id or 0, fx // 5, fy // 5):
                            valid = False
                            break
                        if (fx, fy) in occupied:
                            valid = False
                            break
                    if not valid:
                        break
                if valid:
                    return cx, cy
            return None

        # 1. Party candidate starting tiles (Left flank)
        party_candidates = [
            (x, y)
            for y in [15, 20, 10, 25, 5, 30]
            for x in [5, 10, 15, 0]
        ]
        rng_party = random.Random(self.id or None)
        rng_party.shuffle(party_candidates)

        for hero in party:
            if hero.position_x == 0 and hero.position_y == 0:
                h_tiles = hero.get_size_dimensions()['tiles'] if hasattr(hero, 'get_size_dimensions') else 1
                spot = find_spawn_spot(hero, party_candidates)
                if spot:
                    hero.position_x, hero.position_y = spot
                else:
                    fallback_pts = [(x, y) for x in range(0, 20, 5) for y in range(0, 35, 5)]
                    spot = find_spawn_spot(hero, fallback_pts)
                    if spot:
                        hero.position_x, hero.position_y = spot
                for ox in range(h_tiles):
                    for oy in range(h_tiles):
                        occupied.add((hero.position_x + ox * 5, hero.position_y + oy * 5))
                hero.save(update_fields=['position_x', 'position_y'])

        # 2. Enemy candidate starting tiles (Right flank)
        enemy_candidates = [
            (x, y)
            for y in [15, 20, 10, 25, 5, 30]
            for x in [35, 30, 40, 25]
        ]
        rng_enemy = random.Random((self.id or 0) + 77)
        rng_enemy.shuffle(enemy_candidates)

        for enemy in enemies:
            if enemy.position_x == 0 and enemy.position_y == 0:
                e_tiles = enemy.get_size_dimensions()['tiles'] if hasattr(enemy, 'get_size_dimensions') else 1
                spot = find_spawn_spot(enemy, enemy_candidates)
                if spot:
                    enemy.position_x, enemy.position_y = spot
                else:
                    fallback_pts = [(x, y) for x in range(25, 45, 5) for y in range(0, 35, 5)]
                    spot = find_spawn_spot(enemy, fallback_pts)
                    if spot:
                        enemy.position_x, enemy.position_y = spot
                for ox in range(e_tiles):
                    for oy in range(e_tiles):
                        occupied.add((enemy.position_x + ox * 5, enemy.position_y + oy * 5))
                enemy.save(update_fields=['position_x', 'position_y'])


    def get_or_create_log(self):
        """Get or create combat log for this session"""
        log, _created = CombatLog.objects.get_or_create(combat_session=self)
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
        ('spike_growth', 'Spike Growth'),
        ('wall_of_fire', 'Wall of Fire'),
        ('moonbeam', 'Moonbeam'),
        ('cloudkill', 'Cloudkill'),
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
    attacks_remaining = models.IntegerField(default=1)  # Attacks left this turn (Extra Attack, Multiattack)
    
    # Conditions (many-to-many for multiple conditions)
    conditions = models.ManyToManyField(Condition, blank=True, related_name='combat_participants')
    exhaustion_level = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="2024 Cumulative Exhaustion level (0-10)"
    )
    
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
    
    # Recharge ability tracking for enemies (Format: {'Fire Breath (Recharge 5-6)': True})
    recharge_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tracks recharge ability states for monsters."
    )
    
    # Combat feature uses (Format: {'lay_on_hands_pool': 5, 'second_wind_used': False})
    feature_uses = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tracks active combat feature uses, e.g. lay_on_hands_pool, second_wind, rage_uses"
    )
    
    # Phase 1: Position tracking for AOE targeting
    position_x = models.IntegerField(default=0, help_text="X coordinate on battlefield grid (in feet)")
    position_y = models.IntegerField(default=0, help_text="Y coordinate on battlefield grid (in feet)")
    altitude = models.IntegerField(default=0, help_text="Current altitude above ground in feet (Z-axis)")
    is_flying = models.BooleanField(default=False, help_text="True if participant is currently airborne")
    
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
    
    def resolve_enemy(self):
        """Resolve the Enemy model for this participant (supports encounter & practice mode)."""
        if hasattr(self, '_resolved_enemy_cache'):
            return self._resolved_enemy_cache

        enemy = None
        if self.encounter_enemy:
            enemy = self.encounter_enemy.enemy
        elif self.participant_type == 'enemy' and self.name:
            import re
            from bestiary.models import Enemy as EnemyModel
            # 1. Exact match
            enemy = EnemyModel.objects.filter(name__iexact=self.name).first()
            if not enemy:
                # 2. Strip numeric or alphabetic suffixes (e.g. "Goblin 1", "Dire Wolf #2", "Skeleton A")
                base_name = re.sub(r'\s*(?:#?\d+|[A-Z])$', '', self.name).strip()
                if base_name:
                    enemy = EnemyModel.objects.filter(name__iexact=base_name).first()
            if not enemy:
                # 3. Fuzzy first word match (e.g. "Goblin Archer" -> "Goblin")
                first_word = self.name.split()[0] if self.name.split() else ''
                if first_word:
                    enemy = EnemyModel.objects.filter(name__iexact=first_word).first()
        self._resolved_enemy_cache = enemy
        return enemy

    def _has_character_feature(self, *terms, exact: bool = False) -> bool:
        """Helper to check if character has a feature by name, using prefetch cache when available."""
        if not self.character:
            return False
        if hasattr(self.character, '_prefetched_objects_cache') and 'features' in self.character._prefetched_objects_cache:
            for feat in self.character._prefetched_objects_cache['features']:
                feat_name = (feat.name or '').lower()
                for term in terms:
                    term_lower = term.lower()
                    if exact:
                        if feat_name == term_lower:
                            return True
                    else:
                        if term_lower in feat_name:
                            return True
            return False

        q = models.Q()
        for term in terms:
            if exact:
                q |= models.Q(name__iexact=term)
            else:
                q |= models.Q(name__icontains=term)
        return self.character.features.filter(q).exists()

    def init_recharge_state(self):
        """Initialize all recharge abilities to charged (ready)."""
        enemy = self.resolve_enemy()
        if enemy:
            recharges = {}
            for act in enemy.actions.filter(has_recharge=True):
                recharges[act.name] = True
            self.recharge_state = recharges

    def check_recharges(self):
        """
        Roll d6 for uncharged abilities at start of turn.
        Returns list of newly recharged ability names.
        """
        enemy = self.resolve_enemy()
        if not enemy:
            return []

        # Ensure recharge_state is initialized if enemy has recharge actions
        if not self.recharge_state:
            self.init_recharge_state()
            if not self.recharge_state:
                return []
            self.save(update_fields=['recharge_state'])

        import random
        recharged = []
        updated = False
        recharge_actions = {a.name: a for a in enemy.actions.filter(has_recharge=True)}

        for name, is_charged in list(self.recharge_state.items()):
            if not is_charged:
                act = recharge_actions.get(name)
                min_roll = act.recharge_min_roll if act and act.recharge_min_roll else 5
                roll = random.randint(1, 6)
                if roll >= min_roll:
                    self.recharge_state[name] = True
                    recharged.append(name)
                    updated = True

        if updated:
            self.save(update_fields=['recharge_state'])
        return recharged

    def has_trait(self, trait_type):
        """Check if enemy participant has a specific trait type."""
        enemy = self.resolve_enemy()
        if enemy:
            normalized = trait_type.lower().replace('_', ' ')
            if hasattr(enemy, '_prefetched_objects_cache') and 'traits' in enemy._prefetched_objects_cache:
                for t in enemy._prefetched_objects_cache['traits']:
                    tt = (getattr(t, 'trait_type', None) or '').lower()
                    t_name = (getattr(t, 'name', None) or '').lower()
                    if tt == trait_type.lower() or normalized in t_name:
                        return True
                return False
            return enemy.traits.filter(
                models.Q(trait_type__iexact=trait_type) |
                models.Q(name__icontains=normalized)
            ).exists()
        return False

    def has_grappler_feat(self) -> bool:
        """Check if participant has the 5e Grappler feat."""
        if self.feature_uses and (self.feature_uses.get('has_grappler') or self.feature_uses.get('grappler_feat')):
            return True
        if self.character:
            if hasattr(self.character, '_prefetched_objects_cache') and 'character_feats' in self.character._prefetched_objects_cache:
                for cf in self.character._prefetched_objects_cache['character_feats']:
                    feat = getattr(cf, 'feat', None)
                    if feat and (feat.name or '').strip().lower() == 'grappler':
                        return True
                return False
            return self.character.character_feats.filter(feat__name__iexact='Grappler').exists()
        enemy = self.resolve_enemy()
        if enemy:
            if hasattr(enemy, '_prefetched_objects_cache') and 'traits' in enemy._prefetched_objects_cache:
                return any('grappler' in (t.name or '').lower() for t in enemy._prefetched_objects_cache['traits'])
            return enemy.traits.filter(name__icontains='grappler').exists()
        return False

    def has_feat(self, feat_name: str) -> bool:
        """Check if participant has a specific 5e feat."""
        from combat.feats_and_invocations import has_feat as _hf
        return _hf(self, feat_name)

    def has_eldritch_invocation(self, invocation_name: str) -> bool:
        """Check if participant has a specific Warlock Eldritch Invocation."""
        from combat.feats_and_invocations import has_eldritch_invocation as _hei
        return _hei(self, invocation_name)

    def has_sentinel(self) -> bool:
        return self.has_feat('Sentinel')

    def has_sharpshooter(self) -> bool:
        return self.has_feat('Sharpshooter')

    def has_great_weapon_master(self) -> bool:
        return self.has_feat('Great Weapon Master')

    def has_polearm_master(self) -> bool:
        return self.has_feat('Polearm Master')

    def has_war_caster(self) -> bool:
        return self.has_feat('War Caster')

    def has_devils_sight(self) -> bool:
        return self.has_eldritch_invocation('devils_sight') or self.has_eldritch_invocation("devil's sight")

    def has_fighting_style(self, style_name: str) -> bool:
        """
        Check if participant has a specific 5e Fighting Style.
        Supports Archery, Defense, Dueling, Great Weapon Fighting, Two-Weapon Fighting, etc.
        Checks:
        1. participant.feature_uses (e.g. mock combat, direct flags, fighting_styles list)
        2. character.features (CharacterFeature selection or name)
        3. character.character_feats (Feat name or category)
        4. enemy traits
        """
        if not style_name:
            return False

        target = style_name.strip().lower().replace('_', ' ')
        target_slug = target.replace(' ', '_')
        aliases = {target, target_slug}
        if 'great weapon' in target:
            aliases.update({'great weapon', 'great weapon fighting', 'great_weapon', 'great_weapon_fighting'})
        if 'two weapon' in target:
            aliases.update({'two weapon', 'two weapon fighting', 'two_weapon', 'two_weapon_fighting'})

        # 1. Check feature_uses on participant
        if self.feature_uses and isinstance(self.feature_uses, dict):
            for alias in aliases:
                slug = alias.replace(' ', '_')
                if self.feature_uses.get(f'has_{slug}') or self.feature_uses.get(f'{slug}_fighting_style') or self.feature_uses.get(slug):
                    return True
            fs = self.feature_uses.get('fighting_style')
            if isinstance(fs, str) and any(alias in fs.lower().strip() for alias in aliases):
                return True
            styles_list = self.feature_uses.get('fighting_styles') or self.feature_uses.get('styles')
            if isinstance(styles_list, list):
                for s in styles_list:
                    if isinstance(s, str) and any(alias in s.lower().strip() for alias in aliases):
                        return True

        # 2. Check character features and feats
        if self.character:
            # Check CharacterFeature objects
            try:
                features = self.character.features.all()
                for feat in features:
                    f_name = (feat.name or '').lower()
                    # Check direct name match e.g. "Archery" or "Fighting Style: Archery"
                    if any(alias in f_name for alias in aliases):
                        return True
                    # Check selection list inside "Fighting Style" feature
                    if 'fighting style' in f_name and feat.selection:
                        for sel in feat.selection:
                            if isinstance(sel, str) and any(alias in sel.lower().strip() for alias in aliases):
                                return True
            except Exception:
                pass

            # Check CharacterFeat objects (2024 rules store fighting styles as Feats)
            try:
                if hasattr(self.character, '_prefetched_objects_cache') and 'character_feats' in self.character._prefetched_objects_cache:
                    for char_feat in self.character._prefetched_objects_cache['character_feats']:
                        feat_obj = getattr(char_feat, 'feat', None)
                        if feat_obj:
                            feat_name = (feat_obj.name or '').lower()
                            if any(alias in feat_name for alias in aliases):
                                return True
                else:
                    for char_feat in self.character.character_feats.select_related('feat').all():
                        feat_obj = char_feat.feat
                        feat_name = (feat_obj.name or '').lower()
                        if any(alias in feat_name for alias in aliases):
                            return True
            except Exception:
                pass

        # 3. Check enemy traits
        enemy = self.resolve_enemy()
        if enemy:
            if hasattr(enemy, '_prefetched_objects_cache') and 'traits' in enemy._prefetched_objects_cache:
                for t in enemy._prefetched_objects_cache['traits']:
                    t_name = (getattr(t, 'name', None) or '').lower()
                    t_desc = (getattr(t, 'description', None) or '').lower()
                    if any(alias in t_name or alias in t_desc for alias in aliases):
                        return True
            else:
                for alias in aliases:
                    if enemy.traits.filter(
                        models.Q(name__icontains=alias) |
                        models.Q(description__icontains=alias)
                    ).exists():
                        return True

        return False

    def get_creature_type(self) -> str:
        """
        Return the creature type of this participant in lowercase (e.g. 'beast', 'dragon', 'undead', 'humanoid').
        """
        if self.encounter_enemy and hasattr(self.encounter_enemy, 'enemy') and self.encounter_enemy.enemy:
            return (self.encounter_enemy.enemy.creature_type or 'humanoid').lower().strip()
        enemy = self.resolve_enemy()
        if enemy and hasattr(enemy, 'creature_type') and enemy.creature_type:
            return enemy.creature_type.lower().strip()
        # For characters, races define creature type; 5e default is 'humanoid'
        return 'humanoid'

    def get_favored_enemies(self) -> list:
        """
        Return list of normalized, lowercase favored enemy types for this participant.
        Sources:
        1. participant.feature_uses (e.g. {'favored_enemies': ['beast', 'dragon']})
        2. character.features (CharacterFeature selection list for 'Favored Enemy')
        """
        favored = []
        # 1. Feature uses
        if self.feature_uses and isinstance(self.feature_uses, dict):
            fu_fe = self.feature_uses.get('favored_enemies') or self.feature_uses.get('favored_enemy')
            if isinstance(fu_fe, list):
                for item in fu_fe:
                    if isinstance(item, str) and item.strip():
                        favored.append(item.lower().strip().rstrip('s'))
            elif isinstance(fu_fe, str) and fu_fe.strip():
                favored.append(fu_fe.lower().strip().rstrip('s'))

        # 2. Character features
        if self.character:
            try:
                for feat in self.character.features.all():
                    if 'favored enemy' in (feat.name or '').lower():
                        if feat.selection and isinstance(feat.selection, list):
                            for sel in feat.selection:
                                if isinstance(sel, str) and sel.strip():
                                    favored.append(sel.lower().strip().rstrip('s'))
            except Exception:
                pass

        return list(set(favored))

    def has_favored_enemy_trait(self) -> bool:
        """Check if participant has the Favored Enemy feature (Ranger Level 1+)."""
        if self.feature_uses and isinstance(self.feature_uses, dict):
            if self.feature_uses.get('has_favored_enemy') or self.feature_uses.get('favored_enemies'):
                return True
        if self.character:
            try:
                if self.character.character_class and self.character.character_class.name.lower() == 'ranger':
                    return True
                return self._has_character_feature('favored enemy')
            except Exception:
                pass
        return False

    def is_favored_enemy(self, target) -> bool:
        """
        Check if target creature matches any of attacker's favored enemies.
        Supports both exact and singular/plural matching.
        Also returns True if target is marked by attacker's Hunter's Mark quarry.
        """
        if not target:
            return False
        # Also check if target is quarry of Hunter's Mark
        if hasattr(self, 'has_buff') and self.has_buff("hunter's mark"):
            quarry_id = (self.feature_uses or {}).get('hunters_mark_target_id')
            if quarry_id is None or quarry_id == getattr(target, 'id', None):
                return True

        favored_types = self.get_favored_enemies()
        if not favored_types:
            return False

        t_type = target.get_creature_type() if hasattr(target, 'get_creature_type') else 'humanoid'
        clean_target = t_type.lower().strip().rstrip('s')
        for ft in favored_types:
            clean_ft = ft.lower().strip().rstrip('s')
            if clean_ft == clean_target or clean_ft in clean_target or clean_target in clean_ft:
                return True
        return False

    def has_foe_slayer(self) -> bool:
        """Check if participant has Level 20 Ranger Foe Slayer."""
        if self.feature_uses and isinstance(self.feature_uses, dict):
            if self.feature_uses.get('has_foe_slayer'):
                return True
        if self.character:
            try:
                if self.character.character_class and self.character.character_class.name.lower() == 'ranger' and (self.character.level or 1) >= 20:
                    return True
                return self._has_character_feature('foe slayer')
            except Exception:
                pass
        return False

    def get_speed(self) -> int:
        """Calculate effective walking speed for combat participant"""
        return self.speed

    def has_weapon_mastery(self, weapon_name: str = None, property_name: str = None) -> bool:
        """
        Check if participant can use 2024 Weapon Mastery for a weapon and/or property.
        Delegates to combat.weapon_mastery.can_use_weapon_mastery.
        """
        from combat.weapon_mastery import can_use_weapon_mastery
        return can_use_weapon_mastery(self, weapon_name=weapon_name, property_name=property_name)

    def get_sorcery_points(self) -> dict:
        """Get Sorcery Points status (max, current, used) for participant."""
        from combat.sorcery import get_sorcery_points_info
        return get_sorcery_points_info(self)

    def spend_sorcery_points(self, amount: int) -> bool:
        """Spend Sorcery Points. Returns True if successful."""
        from combat.sorcery import spend_sorcery_points
        return spend_sorcery_points(self, amount)

    def regain_sorcery_points(self, amount: int) -> int:
        """Regain Sorcery Points up to max. Returns points regained."""
        from combat.sorcery import regain_sorcery_points
        return regain_sorcery_points(self, amount)

    @property
    def temporary_hp(self) -> int:
        """Get current temporary hit points from feature_uses or character stats."""
        if self.feature_uses and isinstance(self.feature_uses, dict):
            if 'temporary_hp' in self.feature_uses:
                return int(self.feature_uses.get('temporary_hp') or 0)
        if self.character and hasattr(self.character, 'stats') and hasattr(self.character.stats, 'temporary_hit_points'):
            return int(self.character.stats.temporary_hit_points or 0)
        return 0

    @temporary_hp.setter
    def temporary_hp(self, value: int):
        """Set current temporary hit points and synchronize with character stats."""
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        val = max(0, int(value or 0))
        self.feature_uses['temporary_hp'] = val
        if self.character and hasattr(self.character, 'stats') and hasattr(self.character.stats, 'temporary_hit_points'):
            try:
                self.character.stats.temporary_hit_points = val
                self.character.stats.save(update_fields=['temporary_hit_points'])
            except Exception:
                pass

    # ---------------------------------------------------------------------------
    # SRD 5.2 Subclass Specialization Helpers
    # ---------------------------------------------------------------------------

    def is_champion(self) -> bool:
        """Check if participant is a Champion Fighter."""
        from combat.subclasses import is_champion
        return is_champion(self)

    def get_critical_threshold(self) -> int:
        """Get the d20 natural roll needed for a critical hit (e.g. 19 for Champion, 18 for Superior Critical)."""
        from combat.subclasses import get_critical_threshold
        return get_critical_threshold(self)

    def is_hunter(self) -> bool:
        """Check if participant is a Hunter Ranger."""
        from combat.subclasses import is_hunter
        return is_hunter(self)

    def is_fiend_warlock(self) -> bool:
        """Check if participant is a Fiend Patron Warlock."""
        from combat.subclasses import is_fiend_warlock
        return is_fiend_warlock(self)

    def is_open_hand_monk(self) -> bool:
        """Check if participant is a Warrior of the Open Hand Monk."""
        from combat.subclasses import is_open_hand_monk
        return is_open_hand_monk(self)

    def is_thief(self) -> bool:
        """Check if participant is a Thief Rogue."""
        from combat.subclasses import is_thief
        return is_thief(self)

    def is_lore_bard(self) -> bool:
        """Check if participant is a College of Lore Bard."""
        from combat.subclasses import is_lore_bard
        return is_lore_bard(self)

    def is_land_druid(self) -> bool:
        """Check if participant is a Circle of the Land Druid."""
        from combat.subclasses import is_land_druid
        return is_land_druid(self)

    def is_draconic_sorcerer(self) -> bool:
        """Check if participant is a Draconic Sorcery / Draconic Bloodline Sorcerer."""
        from combat.subclasses import is_draconic_sorcerer
        return is_draconic_sorcerer(self)

    def has_elemental_affinity_resistance(self, damage_type: str) -> bool:
        """Check if participant has active Elemental Affinity damage resistance."""
        from combat.subclasses import has_elemental_affinity_resistance
        return has_elemental_affinity_resistance(self, damage_type)

    def has_natures_ward(self) -> bool:
        """Check if participant has Nature's Ward (Circle of the Land level 10+)."""
        from combat.subclasses import has_natures_ward
        return has_natures_ward(self)

    def has_lands_stride(self) -> bool:
        """Check if participant has Land's Stride (Circle of the Land level 6+)."""
        from combat.subclasses import has_lands_stride
        return has_lands_stride(self)

    def has_aura_of_protection(self) -> bool:
        """Check if participant has Aura of Protection (Paladin level 6+)."""
        from combat.high_tier_passives import has_aura_of_protection
        return has_aura_of_protection(self)

    def get_aura_of_protection_bonus(self) -> int:
        """Get the Aura of Protection saving throw bonus affecting this participant."""
        from combat.high_tier_passives import get_aura_of_protection_bonus
        return get_aura_of_protection_bonus(self)

    def has_aura_of_courage(self) -> bool:
        """Check if participant has Aura of Courage (Paladin level 10+)."""
        from combat.high_tier_passives import has_aura_of_courage
        return has_aura_of_courage(self)

    def is_protected_by_aura_of_courage(self) -> bool:
        """Check if participant is protected by an Aura of Courage."""
        from combat.high_tier_passives import is_protected_by_aura_of_courage
        return is_protected_by_aura_of_courage(self)

    def has_reliable_talent(self) -> bool:
        """Check if participant has Reliable Talent (Rogue level 11+)."""
        from combat.high_tier_passives import has_reliable_talent
        return has_reliable_talent(self)

    def has_indomitable_might(self) -> bool:
        """Check if participant has Indomitable Might (Barbarian level 18+)."""
        from combat.high_tier_passives import has_indomitable_might
        return has_indomitable_might(self)

    def has_relentless_rage(self) -> bool:
        """Check if participant has Relentless Rage (Barbarian level 11+)."""
        from combat.high_tier_passives import has_relentless_rage
        return has_relentless_rage(self)


    def get_proficiency_bonus(self) -> int:
        """Get proficiency bonus for this participant"""
        if self.character and hasattr(self.character, 'stats') and hasattr(self.character.stats, 'proficiency_bonus'):
            return self.character.stats.proficiency_bonus
        if self.character:
            level = getattr(self.character, 'level', 1) or 1
            return 2 + (level - 1) // 4
        enemy = self.resolve_enemy()
        if enemy and hasattr(enemy, 'proficiency_bonus'):
            return enemy.proficiency_bonus
        return 2

    def get_attack_bonus(self, weapon=None, is_melee=True) -> int:
        """
        Calculate total static attack roll bonus for the participant with the given weapon/attack mode.
        Includes ability modifier, proficiency bonus, magic weapon bonus, and Fighting Style (Archery).
        """
        if weapon and getattr(weapon, 'finesse', False):
            ability_mod = max(self.get_ability_modifier('STR'), self.get_ability_modifier('DEX'))
        elif not is_melee or (weapon and ('ranged' in str(getattr(weapon, 'weapon_type', '')).lower() or getattr(weapon, 'range_normal', 0) > 5)):
            ability_mod = self.get_ability_modifier('DEX')
        else:
            ability_mod = self.get_ability_modifier('STR')

        prof_bonus = self.get_proficiency_bonus()
        magic_bonuses = self.get_magic_item_bonuses() if hasattr(self, 'get_magic_item_bonuses') else {'to_hit': 0, 'to_damage': 0}
        total_bonus = ability_mod + prof_bonus + magic_bonuses.get('to_hit', 0)

        # Archery Fighting Style (+2 for ranged weapons)
        is_ranged = (not is_melee) or (weapon and 'ranged' in str(getattr(weapon, 'weapon_type', '')).lower())
        if is_ranged and self.has_fighting_style('archery'):
            total_bonus += 2

        return total_bonus


    def release_grapple(self):
        """Release grapple on this participant or by this participant, clearing conditions."""
        grappled_cond = Condition.objects.filter(name__iexact='Grappled').first()
        restrained_cond = Condition.objects.filter(name__iexact='Restrained').first()

        # If this participant is grappled by someone
        if self.grappled_by:
            grappler = self.grappled_by
            self.grappled_by = None
            if grappled_cond:
                self.conditions.remove(grappled_cond)
            if self.feature_uses and self.feature_uses.pop('pinned_by', None):
                if restrained_cond:
                    self.conditions.remove(restrained_cond)
            self.save(update_fields=['grappled_by', 'feature_uses'])

            # Check if grappler still grapples anyone else
            if not self.combat_session.participants.filter(grappled_by=grappler).exists():
                grappler.is_grappling = False
                if grappler.feature_uses and grappler.feature_uses.pop('is_pinning', None):
                    if restrained_cond:
                        grappler.conditions.remove(restrained_cond)
                grappler.save(update_fields=['is_grappling', 'feature_uses'])

        # If this participant is grappling others
        for victim in self.grappling_targets.all():
            victim.grappled_by = None
            if grappled_cond:
                victim.conditions.remove(grappled_cond)
            if victim.feature_uses and victim.feature_uses.pop('pinned_by', None):
                if restrained_cond:
                    victim.conditions.remove(restrained_cond)
            victim.save(update_fields=['grappled_by', 'feature_uses'])

        self.is_grappling = False
        if self.feature_uses and self.feature_uses.pop('is_pinning', None):
            if restrained_cond:
                self.conditions.remove(restrained_cond)
        self.save(update_fields=['is_grappling', 'feature_uses'])

    def check_legendary_resistance(self, save_ability, save_dc, save_total):
        """
        Check if this enemy participant can use Legendary Resistance to turn a failed saving throw into a success.
        Returns: (used, new_success, log_message)
        """
        if self.participant_type != 'enemy':
            return False, (save_total >= save_dc), ""
        if not self.has_trait('legendary_resistance'):
            return False, (save_total >= save_dc), ""
        if save_total >= save_dc:
            return False, True, ""

        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}

        if 'legendary_resistance_remaining' not in self.feature_uses:
            self.feature_uses['legendary_resistance_remaining'] = 3

        remaining = self.feature_uses.get('legendary_resistance_remaining', 0)
        if remaining > 0:
            self.feature_uses['legendary_resistance_remaining'] = remaining - 1
            self.save(update_fields=['feature_uses'])
            rem = self.feature_uses['legendary_resistance_remaining']
            msg = f"🛡️ {self.get_name()} used Legendary Resistance to turn a failed DC {save_dc} {save_ability} save into a SUCCESS! ({rem} uses remaining)"
            return True, True, msg

        return False, False, ""

    def has_condition(self, name):
        """Check if participant has a specific condition by name."""
        if hasattr(self, '_prefetched_objects_cache') and 'conditions' in self._prefetched_objects_cache:
            return any(c.name.lower() == name.lower() for c in self.conditions.all())
        return self.conditions.filter(name__iexact=name).exists()

    def is_incapacitated(self):
        """Check if participant has any condition that causes the incapacitated state."""
        incapacitating = {'incapacitated', 'paralyzed', 'petrified', 'stunned', 'unconscious'}
        if hasattr(self, '_prefetched_objects_cache') and 'conditions' in self._prefetched_objects_cache:
            return any(c.name in incapacitating for c in self.conditions.all())
        return self.conditions.filter(name__in=incapacitating).exists()

    def get_incapacitating_condition(self):
        """Return the display name of the primary condition causing incapacitation."""
        priority = ['unconscious', 'paralyzed', 'petrified', 'stunned', 'incapacitated']
        all_conds = list(self.conditions.all())
        for inc in priority:
            for c in all_conds:
                if c.name == inc:
                    return c.get_name_display() if hasattr(c, 'get_name_display') else c.name.title()
        return "incapacitated"

    def get_condition_names(self):
        """Return a list of lowercase names of all active conditions."""
        return [c.name.lower() for c in self.conditions.all()]

    @property
    def speed(self):
        """Effective movement speed in feet (standard 5e rules)."""
        if not self.is_active or self.current_hp <= 0:
            return 0
        
        # Conditions that reduce speed to 0
        zero_speed_conditions = {'grappled', 'restrained', 'paralyzed', 'petrified', 'stunned', 'unconscious'}
        if hasattr(self, '_prefetched_objects_cache') and 'conditions' in self._prefetched_objects_cache:
            conds = {c.name.lower() for c in self.conditions.all()}
        else:
            conds = {c.lower() for c in self.conditions.values_list('name', flat=True)}
        
        if self.grappled_by or any(c in zero_speed_conditions for c in conds):
            return 0

        if self.character and hasattr(self.character, 'stats') and self.character.stats:
            base = self.character.stats.speed or 30
        elif self.encounter_enemy and self.encounter_enemy.enemy and hasattr(self.encounter_enemy.enemy, 'stats') and self.encounter_enemy.enemy.stats:
            base = self.encounter_enemy.enemy.stats.speed or 30
        else:
            base = 30

        try:
            if isinstance(base, str):
                import re
                nums = re.findall(r'\d+', base)
                base = int(nums[0]) if nums else 30
            else:
                base = int(base)
        except (ValueError, TypeError):
            base = 30

        # 5e Moving a Grappled Creature: Speed is halved unless target is 2+ sizes smaller
        if self.is_grappling:
            victim = self.grappling_targets.filter(is_active=True).first()
            if victim:
                size_rank = {'T': 0, 'S': 1, 'M': 2, 'L': 3, 'H': 4, 'G': 5}
                g_rank = size_rank.get(self.get_size(), 2)
                v_rank = size_rank.get(victim.get_size(), 2)
                if v_rank > g_rank - 2:
                    base = base // 2

        # 2024 Cumulative Exhaustion: -5 ft per exhaustion level
        ex_level = self.get_exhaustion_level()
        if ex_level > 0:
            base = max(0, base - (5 * ex_level))

        speed_penalty = (self.feature_uses or {}).get('speed_penalty', 0) + (self.feature_uses or {}).get('slowed_speed_reduction', 0)
        return max(0, base - speed_penalty)

    def get_exhaustion_level(self) -> int:
        """Return active 2024 exhaustion level (0-10)."""
        if self.exhaustion_level is not None and self.exhaustion_level > 0:
            return self.exhaustion_level
        if self.character and hasattr(self.character, 'stats') and self.character.stats:
            return getattr(self.character.stats, 'exhaustion_level', 0) or 0
        return 0

    def set_exhaustion_level(self, level: int) -> int:
        """Set exhaustion level, synchronize exhaustion condition, and handle 10-level death."""
        lvl = min(10, max(0, int(level)))
        self.exhaustion_level = lvl
        
        # Synchronize conditions M2M
        from bestiary.models import Condition
        exhaustion_cond, _ = Condition.objects.get_or_create(
            name='exhaustion',
            defaults={'description': 'Levels of exhaustion have cumulative effects'}
        )
        if lvl > 0:
            if not self.conditions.filter(name='exhaustion').exists():
                self.conditions.add(exhaustion_cond)
        else:
            self.conditions.remove(exhaustion_cond)

        # 2024 SRD 5.2 Rules: Level 10 Exhaustion is fatal
        if lvl >= 10:
            self.current_hp = 0
            self.is_active = False
            if not self.feature_uses:
                self.feature_uses = {}
            self.feature_uses['is_dead'] = True

        # Sync to linked character stats
        if self.character and hasattr(self.character, 'stats') and self.character.stats:
            self.character.stats.exhaustion_level = lvl
            if lvl >= 10:
                self.character.stats.hit_points = 0
                self.character.stats.save(update_fields=['exhaustion_level', 'hit_points'])
            else:
                self.character.stats.save(update_fields=['exhaustion_level'])

        self.save()
        return lvl

    def apply_exhaustion(self, amount: int = 1) -> int:
        """Increase exhaustion by amount (clamps 0-10)."""
        return self.set_exhaustion_level(self.get_exhaustion_level() + amount)

    def recover_exhaustion(self, amount: int = 1) -> int:
        """Decrease exhaustion by amount (clamps 0-10)."""
        return self.set_exhaustion_level(self.get_exhaustion_level() - amount)

    @property
    def movement_remaining(self):
        """Remaining movement budget in feet for current turn."""
        base_speed = self.speed
        dash_bonus = 0
        if self.feature_uses and self.feature_uses.get('dash_active'):
            dash_bonus = base_speed
        total_speed = base_speed + dash_bonus
        return max(0, total_speed - self.movement_used)

    def get_distance_to(self, other):
        """
        Calculate true 5e Chebyshev 3D distance between two creatures in feet.
        Accounts for multi-square footprints (Large, Huge, Gargantuan) and 3D altitude.
        Measures distance between the closest occupied squares of both creatures.
        """
        if not other:
            return 999

        dim_self = self.get_size_dimensions()
        dim_other = other.get_size_dimensions()

        self_min_x = self.position_x
        self_max_x = self.position_x + dim_self['feet'] - 5
        self_min_y = self.position_y
        self_max_y = self.position_y + dim_self['feet'] - 5

        other_min_x = other.position_x
        other_max_x = other.position_x + dim_other['feet'] - 5
        other_min_y = other.position_y
        other_max_y = other.position_y + dim_other['feet'] - 5

        # Horizontal dx (closest edge to closest edge)
        if self_max_x < other_min_x:
            dx = other_min_x - self_max_x
        elif other_max_x < self_min_x:
            dx = self_min_x - other_max_x
        else:
            dx = 0

        # Vertical dy (closest edge to closest edge)
        if self_max_y < other_min_y:
            dy = other_min_y - self_max_y
        elif other_max_y < self_min_y:
            dy = self_min_y - other_max_y
        else:
            dy = 0

        # Altitude dz
        dz = abs((self.altitude or 0) - (other.altitude or 0))

        return max(dx, dy, dz)

    def is_adjacent_to(self, other):
        """Check if target is within 5 feet (adjacent square in 5e grid)."""
        return self.get_distance_to(other) <= 5


    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            if self.attacks_remaining == 1 or not self.attacks_remaining:
                self.attacks_remaining = self._calculate_attacks_per_action()
            if self.participant_type == 'enemy' and not self.recharge_state:
                self.init_recharge_state()
        super().save(*args, **kwargs)
    
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
        else:
            enemy = self.resolve_enemy()
            if enemy and hasattr(enemy, 'stats'):
                stats = enemy.stats
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
        
        # In-memory prefetch check to avoid extra DB queries
        if hasattr(self.character, '_prefetched_objects_cache') and 'character_items' in self.character._prefetched_objects_cache:
            for ci in self.character.character_items.all():
                if ci.is_equipped and hasattr(ci.item, 'weapon'):
                    if slot and ci.equipment_slot == slot:
                        return ci.item.weapon
                    elif not slot and ci.equipment_slot in ('main_hand', 'off_hand', 'two_handed'):
                        return ci.item.weapon
            return None

        from characters.models import CharacterItem
        try:
            filter_kwargs = {
                'character': self.character,
                'is_equipped': True,
                'item__weapon__isnull': False,
            }
            if slot:
                filter_kwargs['equipment_slot'] = slot
            else:
                filter_kwargs['equipment_slot__in'] = ['main_hand', 'off_hand', 'two_handed']
            
            character_item = CharacterItem.objects.select_related('item__weapon').filter(**filter_kwargs).first()
            return character_item.item.weapon if character_item else None
        except Exception:
            return None
    
    def get_equipped_armor(self):
        """Get equipped armor from character inventory"""
        if not self.character:
            return None
        
        # In-memory prefetch check to avoid extra DB queries
        if hasattr(self.character, '_prefetched_objects_cache') and 'character_items' in self.character._prefetched_objects_cache:
            for ci in self.character.character_items.all():
                if ci.is_equipped and ci.equipment_slot == 'armor' and hasattr(ci.item, 'armor'):
                    return ci.item.armor
            return None

        from characters.models import CharacterItem
        try:
            character_item = CharacterItem.objects.select_related('item__armor').filter(
                character=self.character,
                is_equipped=True,
                equipment_slot='armor',
                item__armor__isnull=False
            ).first()
            return character_item.item.armor if character_item else None
        except Exception:
            return None
    
    def get_equipped_shield(self):
        """Get equipped shield from character inventory (supports 'shield' and 'off_hand' slots)"""
        if not self.character:
            return None
        
        # In-memory prefetch check to avoid extra DB queries
        if hasattr(self.character, '_prefetched_objects_cache') and 'character_items' in self.character._prefetched_objects_cache:
            for ci in self.character.character_items.all():
                if ci.is_equipped and ci.equipment_slot in ('shield', 'off_hand') and hasattr(ci.item, 'armor') and getattr(ci.item.armor, 'armor_type', None) == 'shield':
                    return ci.item.armor
            return None

        from characters.models import CharacterItem
        try:
            character_item = CharacterItem.objects.select_related('item__armor').filter(
                character=self.character,
                is_equipped=True,
                equipment_slot__in=['shield', 'off_hand'],
                item__armor__isnull=False,
                item__armor__armor_type='shield'
            ).first()
            return character_item.item.armor if character_item else None
        except Exception:
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
        
        if spell_name in self.spell_uses_remaining and self.spell_uses_remaining[spell_name] > 0:
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
        from characters.inventory_management import get_equipped_armor, get_equipped_shield
        
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
        
        has_armor = bool(get_equipped_armor(self.character))
        has_shield = bool(get_equipped_shield(self.character))
        
        for char_item in equipped_magic_items:
            magic_item = char_item.item.magicitem
            requires_attune = getattr(char_item.item, 'requires_attunement', False) or magic_item.attunement_required
            if requires_attune and not char_item.is_attuned:
                continue

            if 'bracers of defense' in magic_item.name.lower() and (has_armor or has_shield):
                continue

            bonuses['to_hit'] += magic_item.bonus_to_hit
            bonuses['to_damage'] += magic_item.bonus_to_damage
            bonuses['to_ac'] += magic_item.bonus_to_ac
            bonuses['to_saves'] += magic_item.bonus_to_saves
        
        return bonuses
    
    def get_active_buffs(self):
        """Get list of active buffs stored on this participant."""
        if not isinstance(self.feature_uses, dict):
            return []
        return self.feature_uses.get('active_buffs', [])

    def has_buff(self, buff_name):
        """Check if participant has a specific active buff (case-insensitive)."""
        if not buff_name:
            return False
        clean = str(buff_name).strip().lower()
        alias_map = {
            'protection from undead': 'protection from evil and good',
            'protect from undead': 'protection from evil and good',
            'protect from evil and good': 'protection from evil and good',
            'protection from evil & good': 'protection from evil and good',
            'protect from evil & good': 'protection from evil and good',
        }
        clean = alias_map.get(clean, clean)
        for b in self.get_active_buffs():
            b_clean = b.get('name', '').strip().lower()
            b_clean = alias_map.get(b_clean, b_clean)
            if b_clean == clean:
                return True
        return False

    def get_buff(self, buff_name):
        """Get buff dict if active, else None."""
        if not buff_name:
            return None
        clean = str(buff_name).strip().lower()
        alias_map = {
            'protection from undead': 'protection from evil and good',
            'protect from undead': 'protection from evil and good',
            'protect from evil and good': 'protection from evil and good',
            'protection from evil & good': 'protection from evil and good',
            'protect from evil & good': 'protection from evil and good',
        }
        clean = alias_map.get(clean, clean)
        for b in self.get_active_buffs():
            b_clean = b.get('name', '').strip().lower()
            b_clean = alias_map.get(b_clean, b_clean)
            if b_clean == clean:
                return b
        return None

    def add_buff(self, name, caster_id=None, source_spell=None, ac_bonus=0, bonus_dice=None, concentration=True, description=""):
        """Add or update an active buff."""
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        buffs = list(self.feature_uses.get('active_buffs', []))
        buffs = [b for b in buffs if b.get('name', '').lower() != name.lower()]
        new_buff = {
            'name': name,
            'caster_id': caster_id,
            'source_spell': source_spell or name,
            'ac_bonus': ac_bonus,
            'bonus_dice': bonus_dice,
            'concentration': concentration,
            'description': description,
            'is_buff': True,
        }
        buffs.append(new_buff)
        self.feature_uses['active_buffs'] = buffs
        self.save(update_fields=['feature_uses'])
        return new_buff

    def remove_buff(self, buff_name):
        """Remove an active buff by name."""
        if not isinstance(self.feature_uses, dict):
            return
        buffs = list(self.feature_uses.get('active_buffs', []))
        clean = str(buff_name).strip().lower()
        new_buffs = [b for b in buffs if b.get('name', '').lower() != clean]
        if len(new_buffs) != len(buffs):
            self.feature_uses['active_buffs'] = new_buffs
            update_fields = ['feature_uses']
            if clean == 'haste':
                self.attacks_remaining = max(0, (self.attacks_remaining or 1) - 1)
                if self.attacks_remaining == 0:
                    self.action_used = True
                update_fields.extend(['attacks_remaining', 'action_used'])
            self.save(update_fields=update_fields)

    def remove_buffs_by_caster(self, caster_id):
        """Remove all concentration buffs cast by a specific caster."""
        if not isinstance(self.feature_uses, dict) or caster_id is None:
            return
        buffs = list(self.feature_uses.get('active_buffs', []))
        has_haste_removed = any(b.get('name', '').lower() == 'haste' and b.get('caster_id') == caster_id for b in buffs)
        new_buffs = [b for b in buffs if not (b.get('caster_id') == caster_id and b.get('concentration'))]
        if len(new_buffs) != len(buffs):
            self.feature_uses['active_buffs'] = new_buffs
            update_fields = ['feature_uses']
            if has_haste_removed:
                self.attacks_remaining = max(0, (self.attacks_remaining or 1) - 1)
                if self.attacks_remaining == 0:
                    self.action_used = True
                update_fields.extend(['attacks_remaining', 'action_used'])
            self.save(update_fields=update_fields)

    def get_cover_details(self):
        """
        Determines if participant is within low cover (half-cover, +2 AC)
        or in an environmental cover area. Solid obstacles provide line-of-sight
        blocking (Total Cover), not a passive AC bonus aura.
        """
        try:
            from combat.battlefield import get_participant_cover
            sess_id = self.combat_session_id or (self.combat_session.id if self.combat_session else 0)
            alt = getattr(self, 'altitude', 0) or 0
            size_tiles = self.get_size_dimensions()['tiles'] if hasattr(self, 'get_size_dimensions') else 1
            cover_info = get_participant_cover(sess_id, self.position_x, self.position_y, altitude=alt, size_tiles=size_tiles)

            if cover_info and cover_info.get('bonus', 0) > 0:
                return cover_info
        except Exception:
            pass

        # Also check ParticipantPosition.current_cover if set by EnvironmentalEffect
        try:
            if hasattr(self, 'position') and self.position and self.position.current_cover:
                ctype = self.position.current_cover
                if ctype == 'half':
                    return {'type': 'half', 'bonus': 2, 'source': 'Environmental Cover'}
                elif ctype in ['three_quarters', 'three-quarters']:
                    return {'type': 'three_quarters', 'bonus': 5, 'source': 'Environmental Cover'}
                elif ctype in ['total', 'full']:
                    return {'type': 'total', 'bonus': 0, 'source': 'Total Cover'}
        except Exception:
            pass

        return None

    def calculate_effective_ac(self, cover_bonus=0):
        """Calculate effective AC including armor, magic items, cover, and active buffs"""
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
                pass
        else:
            # Check for Mage Armor buff if not wearing armor: base AC is 13 + Dex mod
            if self.has_buff('mage armor'):
                dex_mod = self.get_ability_modifier('DEX')
                base_ac = max(base_ac, 13 + dex_mod)
        
        # Defense Fighting Style (+1 AC while wearing armor)
        is_armored = (armor is not None) or bool(self.feature_uses and self.feature_uses.get('wearing_armor'))
        if is_armored and self.has_fighting_style('defense'):
            base_ac += 1

        # Add shield bonus
        if shield:
            shield_bonus = getattr(shield, 'ac_bonus', None)
            if shield_bonus is None:
                shield_bonus = shield.base_ac if (hasattr(shield, 'base_ac') and shield.base_ac <= 5) else 2
            base_ac += shield_bonus
        
        # Add magic item bonuses
        magic_bonuses = self.get_magic_item_bonuses()
        base_ac += magic_bonuses['to_ac']
        
        # Add active buffs AC bonuses (e.g. Shield of Faith +2, Haste +2, Shield +5)
        for buff in self.get_active_buffs():
            base_ac += buff.get('ac_bonus', 0)

        # Ensure Shield spell +5 AC is applied if active via action or flag without duplicate
        has_shield_buff = any(b.get('name', '').lower() == 'shield' for b in self.get_active_buffs())
        if not has_shield_buff:
            try:
                from combat.spell_rules import has_active_shield
                if has_active_shield(self):
                    base_ac += 5
            except Exception:
                pass
            
        # Barkskin: Target's AC cannot be less than 16
        if self.has_buff('barkskin'):
            base_ac = max(base_ac, 16)
        
        # Add directional/situational cover bonus if explicitly passed for an attack
        if cover_bonus > 0:
            base_ac += cover_bonus
        
        return base_ac

    
    def take_damage(self, amount, damage_type=None, check_concentration=True, is_critical=False):
        """
        Apply damage to this participant, factoring in:
        1. Barbarian Rage resistance (bludgeoning/piercing/slashing)
        2. EnemyResistance model (resistance/immunity/vulnerability by damage type)
        3. CharacterResistance model (racial/class/item resistances)
        
        Returns (current_hp, concentration_broken).
        Sets self.last_resistance_info to a dict with details, or None.
        """
        from combat.utils import apply_resistance
        
        actual_damage = amount
        was_resisted = False
        self.last_resistance_info = None
        
        # Normalize damage type name for comparisons
        dtype_name = ''
        if isinstance(damage_type, str):
            dtype_name = damage_type.lower()
        elif damage_type and hasattr(damage_type, 'name'):
            dtype_name = damage_type.name.lower()
        
        # 1. Barbarian Rage Resistance: resistance to bludgeoning, piercing, slashing damage
        if self.is_raging():
            # Physical damage types or untyped weapon attacks
            if not dtype_name or dtype_name in ['bludgeoning', 'piercing', 'slashing', 'untyped', 'physical']:
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Barbarian Rage',
                    'damage_type': dtype_name or 'physical',
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }
        
        # 2. Check EnemyResistance (for enemy targets taking damage)
        if not was_resisted and dtype_name and self.encounter_enemy:
            try:
                enemy = self.encounter_enemy.enemy
                resistance = enemy.resistances.filter(
                    damage_type__name__iexact=dtype_name
                ).first()
                if resistance:
                    actual_damage = apply_resistance(actual_damage, resistance.resistance_type)
                    was_resisted = True
                    self.last_resistance_info = {
                        'type': resistance.resistance_type,
                        'source': f'{enemy.name}',
                        'damage_type': dtype_name,
                        'original_damage': amount,
                        'actual_damage': actual_damage,
                    }
            except Exception:
                pass  # Graceful fallback — don't block damage on lookup errors
        
        # 3. Check CharacterResistance (for PC targets taking damage)
        if not was_resisted and dtype_name and self.character:
            try:
                resistance = self.character.resistances.filter(
                    damage_type__name__iexact=dtype_name
                ).first()
                if resistance:
                    actual_damage = apply_resistance(actual_damage, resistance.resistance_type)
                    was_resisted = True
                    self.last_resistance_info = {
                        'type': resistance.resistance_type,
                        'source': resistance.source or 'Character',
                        'damage_type': dtype_name,
                        'original_damage': amount,
                        'actual_damage': actual_damage,
                    }
            except Exception:
                pass  # Graceful fallback

        # 4. Inherent Racial Resistances fallback (Dwarven Resilience for poison, Hellish Resistance for fire)
        if not was_resisted and dtype_name and self.character:
            if dtype_name in ['poison'] and self.has_dwarven_resilience():
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Dwarven Resilience',
                    'damage_type': dtype_name,
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }
            elif dtype_name in ['fire'] and self.has_hellish_resistance():
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Hellish Resistance',
                    'damage_type': dtype_name,
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }
            elif self.has_elemental_affinity_resistance(dtype_name):
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Elemental Affinity',
                    'damage_type': dtype_name,
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }
            elif dtype_name == 'poison' and self.has_natures_ward():
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': "Nature's Ward",
                    'damage_type': dtype_name,
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }

        # 5. Magical Buff Resistances (Stoneskin, Protection from Poison)
        if not was_resisted and hasattr(self, 'has_buff'):
            if self.has_buff('stoneskin') and (not dtype_name or dtype_name in ['bludgeoning', 'piercing', 'slashing', 'physical', 'untyped']):
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Stoneskin',
                    'damage_type': dtype_name or 'physical',
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }
            elif self.has_buff('protection from poison') and dtype_name == 'poison':
                actual_damage = max(1, amount // 2)
                was_resisted = True
                self.last_resistance_info = {
                    'type': 'resistance',
                    'source': 'Protection from Poison',
                    'damage_type': 'poison',
                    'original_damage': amount,
                    'actual_damage': actual_damage,
                }


        self.last_relentless_endurance_triggered = False
        self.last_relentless_rage_triggered = False
        self.relentless_rage_details = None
        self.last_undead_fortitude_triggered = False
        self.undead_fortitude_details = None
        self.last_death_ward_triggered = False
        concentration_broken = False

        # Temporary Hit Points absorb incoming damage first per 5e rules
        cur_thp = self.temporary_hp
        if cur_thp > 0 and actual_damage > 0:
            if cur_thp >= actual_damage:
                self.temporary_hp = cur_thp - actual_damage
                actual_damage = 0
            else:
                actual_damage -= cur_thp
                self.temporary_hp = 0

        # 5e Rules: Damage taken while ALREADY at 0 HP
        if self.current_hp <= 0 and actual_damage > 0:
            if self.participant_type == 'character':
                if not isinstance(self.feature_uses, dict):
                    self.feature_uses = {}
                # Taking damage breaks stabilization
                self.feature_uses['is_stable'] = False
                
                # Check instant death from damage at 0 HP:
                # If damage equals or exceeds max HP, creature dies instantly
                if actual_damage >= self.max_hp:
                    self.death_save_failures = 3
                    self.is_active = False
                    self.feature_uses['instant_death'] = True
                    self.feature_uses['is_dead'] = True
                    self.last_instant_death_triggered = True
                else:
                    # Critical hit = 2 failures, normal hit = 1 failure
                    failures_added = 2 if is_critical else 1
                    self.death_save_failures = min(3, self.death_save_failures + failures_added)
                    if self.death_save_failures >= 3:
                        self.is_active = False
                        self.feature_uses['is_dead'] = True
                self.save()
            return (self.current_hp, concentration_broken)

        potential_hp = self.current_hp - actual_damage
        if potential_hp <= 0 and self.current_hp > 0 and hasattr(self, 'has_buff') and self.has_buff('death ward'):
            # 5e Death Ward: First time dropping to 0 HP, drop to 1 HP instead and spell ends
            self.current_hp = 1
            self.is_active = True
            self.last_death_ward_triggered = True
            if hasattr(self, 'remove_buff'):
                self.remove_buff('Death Ward')
            if isinstance(self.feature_uses, dict):
                self.feature_uses.pop('death_ward_active', None)
            self.save(update_fields=['current_hp', 'is_active', 'feature_uses'])
        elif potential_hp <= 0 and self.current_hp > 0 and self.has_relentless_endurance():
            uses = self.feature_uses or {}
            if not uses.get('relentless_endurance_used', False):
                excess_damage = actual_damage - self.current_hp
                if excess_damage < self.max_hp:
                    self.current_hp = 1
                    self.is_active = True
                    if not isinstance(self.feature_uses, dict):
                        self.feature_uses = {}
                    self.feature_uses['relentless_endurance_used'] = True
                    self.last_relentless_endurance_triggered = True
                else:
                    self.current_hp = 0
                    self.is_active = False
                    self.death_save_failures = 3
                    if not isinstance(self.feature_uses, dict):
                        self.feature_uses = {}
                    self.feature_uses['instant_death'] = True
                    self.feature_uses['is_dead'] = True
                    self.last_instant_death_triggered = True
            else:
                self.current_hp = 0
                self.is_active = False
        elif potential_hp <= 0 and self.current_hp > 0 and self.is_raging() and self.has_relentless_rage():
            # Barbarian Relentless Rage (Level 11+): DC 10 (scaling +5) CON save to drop to 1 HP instead of 0
            excess_damage = actual_damage - self.current_hp
            if excess_damage < self.max_hp:
                from combat.high_tier_passives import check_relentless_rage
                success, dc, save_total, msg = check_relentless_rage(self)
                if success:
                    self.current_hp = 1
                    self.is_active = True
                    self.last_relentless_rage_triggered = True
                    self.relentless_rage_details = {
                        'dc': dc,
                        'total': save_total,
                        'message': msg,
                    }
                else:
                    self.current_hp = 0
                    self.is_active = False
            else:
                self.current_hp = 0
                self.is_active = False
                self.death_save_failures = 3
                if not isinstance(self.feature_uses, dict):
                    self.feature_uses = {}
                self.feature_uses['instant_death'] = True
                self.feature_uses['is_dead'] = True
                self.last_instant_death_triggered = True
        elif potential_hp <= 0 and self.current_hp > 0 and self.participant_type == 'enemy' and self.has_trait('undead_fortitude'):
            # 5e Undead Fortitude: DC 5 + damage taken CON save (unless radiant damage or critical hit)
            is_radiant = (dtype_name == 'radiant')
            if not is_radiant and not is_critical:
                from combat.utils import roll_d20
                dc = 5 + actual_damage
                con_mod = self.get_ability_modifier('CON')
                r, _ = roll_d20()
                save_total = r + con_mod
                if save_total >= dc:
                    self.current_hp = 1
                    self.is_active = True
                    self.last_undead_fortitude_triggered = True
                    self.undead_fortitude_details = {
                        'roll': r,
                        'con_mod': con_mod,
                        'total': save_total,
                        'dc': dc,
                    }
                else:
                    self.current_hp = 0
                    self.is_active = False
            else:
                self.current_hp = 0
                self.is_active = False
        else:
            excess_damage = actual_damage - self.current_hp
            if self.participant_type == 'character' and excess_damage >= self.max_hp:
                # 5e Massive damage instant death
                self.current_hp = 0
                self.is_active = False
                self.death_save_failures = 3
                if not isinstance(self.feature_uses, dict):
                    self.feature_uses = {}
                self.feature_uses['instant_death'] = True
                self.feature_uses['is_dead'] = True
                self.last_instant_death_triggered = True
            else:
                self.current_hp = max(0, potential_hp)
                if self.current_hp <= 0:
                    self.is_active = False
                    if self.participant_type == 'character':
                        self.death_save_successes = 0
                        self.death_save_failures = 0
                        if not isinstance(self.feature_uses, dict):
                            self.feature_uses = {}
                        self.feature_uses['is_stable'] = False
                        try:
                            unconscious_cond, _ = Condition.objects.get_or_create(name='Unconscious')
                            self.conditions.add(unconscious_cond)
                            prone_cond, _ = Condition.objects.get_or_create(name='Prone')
                            self.conditions.add(prone_cond)
                        except Exception:
                            pass
                    # Falling unconscious drops Rage
                    if self.is_raging():
                        self.feature_uses['is_raging'] = False
                        self.feature_uses['rage_rounds_left'] = 0
                    # Falling unconscious breaks concentration immediately
                    if self.is_concentrating:
                        self.is_concentrating = False
                        self.concentration_spell = ""
                        concentration_broken = True
                        try:
                            from combat.spell_rules import remove_caster_concentration_buffs
                            remove_caster_concentration_buffs(self)
                        except Exception:
                            pass
                    # Falling unconscious breaks any active grapple
                    if self.is_grappling or self.grappled_by:
                        try:
                            self.release_grapple()
                        except Exception:
                            pass
        
        # Check if target was turned by Turn Undead - taking damage ends the turned effect per 5e rules
        if actual_damage > 0 and self.feature_uses and self.feature_uses.get('is_turned'):
            self.feature_uses['is_turned'] = False
            frightened_cond = self.conditions.filter(name__iexact='frightened').first()
            if frightened_cond:
                self.conditions.remove(frightened_cond)

        # 5e Wild Shape: Revert to normal form when beast HP drops to 0
        if self.feature_uses and self.feature_uses.get('wild_shaped') and potential_hp <= 0:
            excess = abs(potential_hp)
            orig_hp = self.feature_uses.get('pre_wild_shape_hp', self.max_hp)
            orig_max_hp = self.feature_uses.get('pre_wild_shape_max_hp', self.max_hp)
            orig_ac = self.feature_uses.get('pre_wild_shape_ac', self.armor_class)
            self.feature_uses['wild_shaped'] = False
            self.feature_uses['wild_shape_beast'] = None
            self.max_hp = orig_max_hp
            self.armor_class = orig_ac
            self.current_hp = max(0, orig_hp - excess)
            self.is_active = (self.current_hp > 0)

        # Check concentration if taking damage while concentrating
        concentration_broken_check = False
        if check_concentration and self.is_concentrating and actual_damage > 0:
            concentration_broken_check, _, _, _ = self.check_concentration(actual_damage)
            if concentration_broken_check:
                concentration_broken = True
        
        self.save()
        return self.current_hp, concentration_broken
    
    def take_damage_simple(self, amount, damage_type=None):
        """Simple version that doesn't check concentration (for backward compatibility)"""
        return self.take_damage(amount, damage_type, check_concentration=False)[0]

    def is_raging(self):
        """Check if this participant is currently in a Barbarian Rage"""
        if not isinstance(self.feature_uses, dict):
            return False
        return bool(self.feature_uses.get('is_raging', False))

    def get_max_rage_uses(self):
        """Get maximum Rage uses per long rest based on Barbarian level"""
        if not self.character or not self.is_barbarian():
            return 0
        lvl = self.character.level or 1
        if lvl >= 20:
            return 999  # Unlimited
        elif lvl >= 17:
            return 6
        elif lvl >= 12:
            return 5
        elif lvl >= 6:
            return 4
        elif lvl >= 3:
            return 3
        else:
            return 2

    def get_rage_uses_remaining(self):
        """Get remaining Rage uses for this Barbarian"""
        max_uses = self.get_max_rage_uses()
        if max_uses <= 0:
            return 0
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        return self.feature_uses.get('rage_uses_remaining', max_uses)

    def get_rage_damage_bonus(self):
        """Get melee damage bonus from active Rage (+2, +3, +4 depending on level)"""
        if not self.is_raging():
            return 0
        lvl = (self.character.level or 1) if self.character else 1
        if lvl >= 16:
            return 4
        elif lvl >= 9:
            return 3
        else:
            return 2

    def is_barbarian(self):
        """Check if participant is a barbarian or has barbarian features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'barbarian' or self._has_character_feature('rage', 'barbarian rage')

    def has_reckless_attack(self):
        """Check if participant has access to Reckless Attack"""
        if not self.character:
            return False
        if self._has_character_feature('reckless attack'):
            return True
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'barbarian' and (self.character.level or 1) >= 2

    def is_fighter(self):
        """Check if participant is a fighter or has fighter features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'fighter' or self._has_character_feature('second wind')

    def is_rogue(self):
        """Check if participant is a rogue or has rogue features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'rogue' or self._has_character_feature('sneak attack')

    def is_paladin(self):
        """Check if participant is a paladin or has paladin features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'paladin' or self._has_character_feature('lay on hands')
    
    def get_lay_on_hands_pool(self):
        """Get remaining Lay on Hands pool for Paladin participant"""
        if not self.character:
            return 0
        
        # Check if character has Lay on Hands feature or is a Paladin
        has_loh = self._has_character_feature('lay on hands')
        class_name = getattr(self.character.character_class, 'name', '').lower()
        if not has_loh and class_name != 'paladin':
            return 0

        paladin_level = self.character.level or 1
        max_pool = paladin_level * 5
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        
        return self.feature_uses.get('lay_on_hands_pool', max_pool)

    def is_cleric(self):
        """Check if participant is a cleric or has cleric-specific features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'cleric' or self._has_character_feature('turn undead', 'preserve life', 'destroy undead')

    def is_monk(self):
        """Check if participant is a monk or has monk features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'monk' or self._has_character_feature('ki', 'ki points', 'ki-fueled', 'flurry of blows', 'martial arts', 'stunning strike')

    def is_bard(self):
        """Check if participant is a bard or has bard features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'bard' or self._has_character_feature('bardic inspiration')

    def is_druid(self):
        """Check if participant is a druid or has druid features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'druid' or self._has_character_feature('wild shape')

    def is_sorcerer(self):
        """Check if participant is a sorcerer or has sorcerer features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'sorcerer' or self._has_character_feature('font of magic')

    def is_warlock(self):
        """Check if participant is a warlock"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'warlock'

    def is_wizard(self):
        """Check if participant is a wizard or has wizard-specific features"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'wizard' or self._has_character_feature('arcane recovery')

    def has_arcane_recovery(self):
        """Check if participant has the Arcane Recovery feature available"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        has_feat = self._has_character_feature('arcane recovery')
        return class_name == 'wizard' or has_feat

    def get_arcane_recovery_max_levels(self):
        """Get max combined slot levels that can be recovered (ceil(wizard_level / 2))"""
        if not self.has_arcane_recovery():
            return 0
        lvl = self.character.level or 1
        return (lvl + 1) // 2

    def is_arcane_recovery_used(self):
        """Check if Arcane Recovery has already been used in this combat/session"""
        if not isinstance(self.feature_uses, dict):
            return False
        return bool(self.feature_uses.get('arcane_recovery_used', False))

    def is_ranger(self):
        """Check if participant is a ranger"""
        if not self.character:
            return False
        class_name = getattr(self.character.character_class, 'name', '').lower()
        return class_name == 'ranger'

    def get_creature_type(self):
        """Get creature type ('undead', 'fiend', 'humanoid', 'beast', etc.)"""
        if self.encounter_enemy and self.encounter_enemy.enemy:
            return (self.encounter_enemy.enemy.creature_type or '').lower()
        if self.participant_type == 'enemy' and self.name:
            from bestiary.models import Enemy
            enemy = Enemy.objects.filter(name=self.name).first()
            if enemy:
                return (enemy.creature_type or '').lower()
        if self.character:
            return 'humanoid'
        return ''

    def is_undead(self):
        """Check if participant is undead"""
        return self.get_creature_type() == 'undead'

    def is_fiend(self):
        """Check if participant is a fiend"""
        return self.get_creature_type() == 'fiend'

    def get_challenge_rating_value(self):
        """Get challenge rating as float value (e.g. 0.5 for 1/2)"""
        cr_str = None
        if self.encounter_enemy and self.encounter_enemy.enemy:
            cr_str = self.encounter_enemy.enemy.challenge_rating
        elif self.participant_type == 'enemy' and self.name:
            from bestiary.models import Enemy
            enemy = Enemy.objects.filter(name=self.name).first()
            if enemy:
                cr_str = enemy.challenge_rating
        
        if not cr_str:
            return 0.0
        
        cr_str = str(cr_str).strip()
        if '/' in cr_str:
            parts = cr_str.split('/')
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return 0.0
        try:
            return float(cr_str)
        except ValueError:
            return 0.0

    def get_spell_save_dc(self, ability=None):
        """Calculate spell save DC: 8 + proficiency + ability modifier, adjusted by 2024 exhaustion"""
        if not self.character:
            base_dc = 13
        elif hasattr(self.character, 'stats') and self.character.stats and self.character.stats.spell_save_dc:
            base_dc = self.character.stats.spell_save_dc
        else:
            prof = self.character.proficiency_bonus
            if not ability:
                if self.is_cleric() or self.is_druid() or self.is_ranger() or self.is_monk():
                    ability = 'WIS'
                elif self.is_paladin() or self.is_bard() or self.is_sorcerer() or self.is_warlock():
                    ability = 'CHA'
                elif self.is_wizard():
                    ability = 'INT'
                else:
                    ability = 'WIS'
            mod = self.get_ability_modifier(ability)
            base_dc = 8 + prof + mod
        
        # 2024 SRD 5.2 Rules: Subtract exhaustion level from spell save DC
        ex_level = self.get_exhaustion_level()
        if ex_level > 0:
            base_dc = max(1, base_dc - ex_level)
        return base_dc

    def get_channel_divinity_max_uses(self):
        """
        Get max Channel Divinity uses based on Cleric / Paladin level:
        Cleric:
          Level 2-5: 1 use
          Level 6-17: 2 uses
          Level 18-20: 3 uses
        Paladin:
          Level 3+: 1 use
        """
        if not self.character:
            return 0
        lvl = self.character.level or 1
        if self.is_cleric():
            if lvl >= 18:
                return 3
            elif lvl >= 6:
                return 2
            elif lvl >= 2:
                return 1
            return 0
        elif self.is_paladin():
            return 1 if lvl >= 3 else 0
        return 0

    def get_channel_divinity_uses_remaining(self):
        """Get remaining Channel Divinity uses"""
        max_uses = self.get_channel_divinity_max_uses()
        if max_uses <= 0:
            return 0
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        return self.feature_uses.get('channel_divinity_uses_remaining', max_uses)

    def get_ki_pool_max(self):
        """Get max Ki points for Monk (equal to monk level, level 2+)"""
        if not self.character or not self.is_monk():
            return 0
        lvl = self.character.level or 1
        return lvl if lvl >= 2 else 0

    def get_ki_pool_remaining(self):
        """Get remaining Ki points"""
        max_ki = self.get_ki_pool_max()
        if max_ki <= 0:
            return 0
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        return self.feature_uses.get('ki_pool_remaining', max_ki)

    def get_martial_arts_die(self):
        """Get martial arts damage die based on Monk level"""
        if not self.character or not self.is_monk():
            return "1d4"
        lvl = self.character.level or 1
        if lvl >= 17:
            return "1d10"
        elif lvl >= 11:
            return "1d8"
        elif lvl >= 5:
            return "1d6"
        return "1d4"

    def get_bardic_inspiration_max_uses(self):
        """Get max Bardic Inspiration uses = max(1, Charisma modifier)"""
        if not self.character or not self.is_bard():
            return 0
        return max(1, self.get_ability_modifier('CHA'))

    def get_bardic_inspiration_die_size(self):
        """Get Bardic Inspiration die size based on Bard level"""
        if not self.character or not self.is_bard():
            return 'd6'
        lvl = self.character.level or 1
        if lvl >= 15:
            return 'd12'
        elif lvl >= 10:
            return 'd10'
        elif lvl >= 5:
            return 'd8'
        return 'd6'

    def get_bardic_inspiration_uses_remaining(self):
        """Get remaining Bardic Inspiration uses"""
        max_uses = self.get_bardic_inspiration_max_uses()
        if max_uses <= 0:
            return 0
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        return self.feature_uses.get('bardic_inspiration_uses_remaining', max_uses)

    def get_wild_shape_max_uses(self):
        """Druid Wild Shape: 2 uses per short/long rest at level 2+"""
        if not self.character or not self.is_druid():
            return 0
        lvl = self.character.level or 1
        return 2 if lvl >= 2 else 0

    def get_wild_shape_uses_remaining(self):
        """Get remaining Wild Shape uses"""
        max_uses = self.get_wild_shape_max_uses()
        if max_uses <= 0:
            return 0
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        return self.feature_uses.get('wild_shape_uses_remaining', max_uses)

    def heal(self, amount, allow_revive=False):
        """
        Heal this participant.
        Per 5e rules:
        - Defeated enemies/monsters (0 HP) are dead and cannot be healed by simple healing.
        - Characters with 3 death save failures are dead and cannot be healed without resurrection.
        """
        # Defeated enemies cannot be restored by healing
        if self.participant_type == 'enemy' and (self.current_hp <= 0 or not self.is_active):
            return self.current_hp
        
        # Dead characters cannot be healed without true resurrection
        if self.death_save_failures >= 3 and not allow_revive:
            return self.current_hp

        self.current_hp = min(self.max_hp, self.current_hp + amount)
        if self.current_hp > 0:
            self.is_active = True
            # Regaining HP resets death save counts (5e PHB rules)
            self.death_save_successes = 0
            self.death_save_failures = 0
            if isinstance(self.feature_uses, dict):
                self.feature_uses.pop('is_stable', None)
                self.feature_uses.pop('instant_death', None)
                self.feature_uses.pop('is_dead', None)
            try:
                self.conditions.filter(name__iexact='unconscious').delete()
            except Exception:
                pass
        self.save()
        return self.current_hp
    

    def has_lucky_trait(self) -> bool:
        """Check if participant has Halfling Lucky trait (reroll 1s on d20)."""
        if not self.character:
            return False
        if self.character.race and 'halfling' in self.character.race.name.lower():
            return True
        return self._has_character_feature('lucky')

    def has_halfling_nimbleness(self) -> bool:
        """Check if participant has Halfling Nimbleness trait (move through larger creatures' space)."""
        if not self.character:
            return False
        if self.character.race and 'halfling' in self.character.race.name.lower():
            return True
        return self._has_character_feature('nimbleness')

    def has_relentless_endurance(self) -> bool:
        """Check if participant has Half-Orc Relentless Endurance."""
        if not self.character:
            return False
        if self.character.race and any(r in self.character.race.name.lower() for r in ['orc', 'half-orc']):
            return True
        return self._has_character_feature('relentless endurance')

    def has_fey_ancestry(self) -> bool:
        """Check if participant has Elf/Half-Elf Fey Ancestry (advantage vs charm, immune to magical sleep)."""
        if not self.character:
            return False
        if self.character.race and any(r in self.character.race.name.lower() for r in ['elf', 'half-elf', 'eladrin', 'drow']):
            return True
        return self._has_character_feature('fey ancestry')

    def has_brave_trait(self) -> bool:
        """Check if participant has Halfling Brave trait (advantage vs frightened)."""
        if not self.character:
            return False
        if self.character.race and 'halfling' in self.character.race.name.lower():
            return True
        return self._has_character_feature('brave')

    def has_gnome_cunning(self) -> bool:
        """Check if participant has Gnome Cunning (advantage on INT, WIS, CHA saves vs magic)."""
        if not self.character:
            return False
        if self.character.race and 'gnome' in self.character.race.name.lower():
            return True
        return self._has_character_feature('gnome cunning')

    def has_dwarven_resilience(self) -> bool:
        """Check if participant has Dwarven Resilience (poison resistance and save advantage)."""
        if not self.character:
            return False
        if self.character.race and 'dwarf' in self.character.race.name.lower():
            return True
        return self._has_character_feature('dwarven resilience')

    def has_hellish_resistance(self) -> bool:
        """Check if participant has Tiefling Hellish Resistance (fire resistance)."""
        if not self.character:
            return False
        if self.character.race and 'tiefling' in self.character.race.name.lower():
            return True
        return self._has_character_feature('hellish resistance')

    SIZE_SCALE = {
        'T': {'tiles': 1, 'feet': 5, 'name': 'Tiny'},
        'S': {'tiles': 1, 'feet': 5, 'name': 'Small'},
        'M': {'tiles': 1, 'feet': 5, 'name': 'Medium'},
        'L': {'tiles': 2, 'feet': 10, 'name': 'Large'},
        'H': {'tiles': 3, 'feet': 15, 'name': 'Huge'},
        'G': {'tiles': 4, 'feet': 20, 'name': 'Gargantuan'},
    }

    def get_size(self) -> str:
        """Get 5E creature size letter ('T', 'S', 'M', 'L', 'H', 'G')."""
        if self.character:
            if self.character.race:
                race_name = self.character.race.name.lower()
                if any(k in race_name for k in ['halfling', 'gnome', 'goblin', 'kobold']):
                    return 'S'
                size_str = getattr(self.character.race, 'size', 'M') or 'M'
                return size_str.upper()[:1]
            return 'M'
        enemy = self.resolve_enemy()
        if enemy and hasattr(enemy, 'size') and enemy.size:
            size_raw = str(enemy.size).strip().upper()
            return size_raw[:1]
        return 'M'

    def get_size_dimensions(self):
        """Return dict with tile count, width/height in feet, and display name."""
        size_code = self.get_size()
        return self.SIZE_SCALE.get(size_code, self.SIZE_SCALE['M'])

    def get_occupied_cells(self):
        """
        Return list of (x, y) coordinates in feet occupied by this creature on the grid.
        Position (position_x, position_y) is the top-left tile of the footprint.
        """
        feet = self.get_size_dimensions()['feet']
        cells = []
        for dx in range(0, feet, 5):
            for dy in range(0, feet, 5):
                cells.append((self.position_x + dx, self.position_y + dy))
        return cells

    def get_fly_speed(self) -> int:
        """Extract fly speed in feet from enemy speed string or character features."""
        if self.participant_type == 'enemy':
            enemy = self.resolve_enemy()
            if enemy and hasattr(enemy, 'stats') and enemy.stats and enemy.stats.speed:
                speed_str = enemy.stats.speed.lower()
                import re
                match = re.search(r'fly\s+(\d+)\s*ft', speed_str)
                if match:
                    return int(match.group(1))
        # Check active buff/spell like Fly
        if hasattr(self, 'has_buff') and self.has_buff('fly'):
            return 60
        # Check Dragon Wings feature
        if self.feature_uses and isinstance(self.feature_uses, dict) and self.feature_uses.get('dragon_wings_active'):
            return self.speed
        return 0


    def has_hover(self) -> bool:
        """Check if creature has hover flight trait."""
        if self.participant_type == 'enemy':
            enemy = self.resolve_enemy()
            if enemy and hasattr(enemy, 'stats') and enemy.stats and enemy.stats.speed:
                if 'hover' in enemy.stats.speed.lower():
                    return True
            if self.has_trait('hover'):
                return True
        return False

    def can_fly(self) -> bool:
        """Check if participant has an active fly speed."""
        return self.get_fly_speed() > 0

    def handle_flying_fall(self, session=None):
        """
        5e Rule: If a flying creature is knocked prone, its fly speed is reduced to 0,
        or it is incapacitated, and it does not have the hover trait, it falls immediately.
        Takes 1d6 bludgeoning damage per 10 feet fallen (max 20d6) and lands prone on the ground.
        """
        if not self.is_flying or (self.altitude or 0) <= 0:
            return 0, ""

        if self.has_hover():
            return 0, f"{self.get_name()} hovers safely in place!"

        fall_dist = self.altitude
        dice_count = min(20, max(1, fall_dist // 10)) if fall_dist >= 10 else 0
        fall_dmg = 0
        import random
        if dice_count > 0:
            fall_dmg = sum(random.randint(1, 6) for _ in range(dice_count))
            self.take_damage(fall_dmg, damage_type='bludgeoning', is_critical=False)

        self.altitude = 0
        self.is_flying = False
        self.save(update_fields=['altitude', 'is_flying'])

        from bestiary.models import Condition
        prone_cond, _ = Condition.objects.get_or_create(name='prone')
        if not self.conditions.filter(name='prone').exists():
            self.conditions.add(prone_cond)

        msg = f"📉 {self.get_name()} fell {fall_dist} ft from the sky"
        if fall_dmg > 0:
            msg += f", taking {fall_dmg} falling damage ({dice_count}d6) and crashing prone!"
        else:
            msg += " and landed prone!"

        if session:
            from combat.models import CombatAction
            try:
                CombatAction.objects.create(
                    combat_session=session,
                    actor=self,
                    action_type='other',
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=msg,
                )
            except Exception:
                pass

        return fall_dmg, msg
    
    def is_dead(self) -> bool:
        """Check if participant is dead (3 death save failures, instant death, or defeated enemy at 0 HP)."""
        if self.participant_type == 'enemy':
            return self.current_hp <= 0 or not self.is_active
        # For characters
        if self.death_save_failures >= 3:
            return True
        if self.feature_uses and (self.feature_uses.get('instant_death') or self.feature_uses.get('is_dead')):
            return True
        return False

    def is_stable(self) -> bool:
        """Check if 0 HP participant is stabilized (stops rolling death saves until damaged)."""
        if self.current_hp > 0:
            return False
        if self.is_dead():
            return False
        if self.death_save_successes >= 3:
            return True
        if self.feature_uses and self.feature_uses.get('is_stable'):
            return True
        return False

    def is_dying(self) -> bool:
        """Check if participant is at 0 HP, unconscious, and actively rolling death saves."""
        return self.participant_type == 'character' and self.current_hp <= 0 and not self.is_dead() and not self.is_stable()

    def stabilize(self):
        """Stabilize an unconscious character at 0 HP."""
        if self.current_hp > 0 or self.is_dead():
            return False
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}
        self.feature_uses['is_stable'] = True
        self.death_save_successes = 0
        self.death_save_failures = 0
        self.save(update_fields=['death_save_successes', 'death_save_failures', 'feature_uses'])
        return True

    def is_summon(self):
        """Check if this participant is a summoned minion or persistent spell object."""
        return bool((self.feature_uses or {}).get('is_summon', False))

    def is_spell_object(self):
        """Check if this participant is an intangible spell object (e.g. Spiritual Weapon, Flaming Sphere)."""
        return bool(self.is_summon() and (self.feature_uses or {}).get('summon_type') == 'spell_object')

    def get_summoner(self):
        """Return the CombatParticipant who summoned this entity."""
        caster_id = (self.feature_uses or {}).get('summoned_by') or (self.feature_uses or {}).get('caster_id')
        if caster_id and self.combat_session_id:
            return self.combat_session.participants.filter(id=caster_id).first()
        return None

    def make_death_save(self, roll=None):
        """
        Make a death saving throw per 5e rules.
        Returns: (success, is_stable, is_dead, message, roll_total, natural_roll)
        """
        from .utils import roll_d20
        
        if self.current_hp > 0:
            return False, False, False, "Character is not unconscious", 0, 0
        
        if self.is_dead():
            return False, False, True, "Character is dead", 0, 0
            
        if self.is_stable():
            return True, True, False, "Character is already stable", 0, 0
        
        if roll is None:
            roll, _ = roll_d20(lucky=self.has_lucky_trait())
        
        aura_bonus = self.get_aura_of_protection_bonus() if hasattr(self, 'get_aura_of_protection_bonus') else 0
        total_roll = roll + aura_bonus
        
        if not isinstance(self.feature_uses, dict):
            self.feature_uses = {}

        # 5e Natural 20: Character regains 1 HP immediately and regains consciousness!
        if roll == 20:
            self.current_hp = 1
            self.is_active = True
            self.death_save_successes = 0
            self.death_save_failures = 0
            self.feature_uses['is_stable'] = False
            # Remove unconscious condition
            try:
                self.conditions.filter(name__iexact='unconscious').delete()
            except Exception:
                pass
            self.save()
            return True, True, False, "Natural 20! Character stabilizes and regains 1 HP!", total_roll, roll
        
        # 5e Natural 1: Counts as two failures
        elif roll == 1:
            self.death_save_failures = min(3, self.death_save_failures + 2)
            if self.death_save_failures >= 3:
                self.is_active = False
                self.feature_uses['is_dead'] = True
                self.save()
                return False, False, True, f"Natural 1! Suffered 2 failures ({self.death_save_failures}/3). Character dies.", total_roll, roll
            else:
                self.save()
                return False, False, False, f"Natural 1! Suffered 2 failures ({self.death_save_failures}/3).", total_roll, roll

        # Normal roll: 10+ is success (Paladin Aura of Protection applies to death saves)
        elif total_roll >= 10:
            self.death_save_successes += 1
            if self.death_save_successes >= 3:
                self.death_save_successes = 0
                self.death_save_failures = 0
                self.feature_uses['is_stable'] = True
                self.save()
                bonus_msg = f" (d20: {roll} + {aura_bonus} Aura)" if aura_bonus > 0 else f" (d20: {roll})"
                return True, True, False, f"Death save: {total_roll}{bonus_msg} — 3rd Success! Character is now stable.", total_roll, roll
            else:
                self.save()
                bonus_msg = f" (d20: {roll} + {aura_bonus} Aura)" if aura_bonus > 0 else f" (d20: {roll})"
                return True, False, False, f"Death save: {total_roll}{bonus_msg} (Success {self.death_save_successes}/3).", total_roll, roll
        else:
            self.death_save_failures += 1
            if self.death_save_failures >= 3:
                self.is_active = False
                self.feature_uses['is_dead'] = True
                self.save()
                bonus_msg = f" (d20: {roll} + {aura_bonus} Aura)" if aura_bonus > 0 else f" (d20: {roll})"
                return False, False, True, f"Death save: {total_roll}{bonus_msg} — 3rd Failure! Character dies.", total_roll, roll
            else:
                self.save()
                bonus_msg = f" (d20: {roll} + {aura_bonus} Aura)" if aura_bonus > 0 else f" (d20: {roll})"
                return False, False, False, f"Death save: {total_roll}{bonus_msg} (Failure {self.death_save_failures}/3).", total_roll, roll
    
    def check_concentration(self, damage_amount=0):
        """
        Check if concentration is broken due to damage
        DC = 10 or half damage, whichever is higher
        Returns: (concentration_broken, save_roll, save_dc, message)
        """
        if not self.is_concentrating:
            return False, None, None, "Not concentrating on any spell"
        
        from .utils import calculate_saving_throw, roll_d20
        
        # Calculate DC: 10 or half damage, whichever is higher
        save_dc = max(10, damage_amount // 2)
        
        # Roll CON saving throw (War Caster grants advantage)
        has_war_caster_adv = self.has_war_caster()
        roll, _ = roll_d20(advantage=has_war_caster_adv, lucky=self.has_lucky_trait())
        con_mod = self.get_ability_modifier('CON')
        proficiency_bonus = self.character.proficiency_bonus if self.character else 2
        proficiency = False
        if self.character and hasattr(self.character, 'saving_throw_proficiencies') and self.character.saving_throw_proficiencies:
            proficiency = 'con' in [s.lower() for s in self.character.saving_throw_proficiencies]
        
        aura_bonus = self.get_aura_of_protection_bonus()
        save_total, _ = calculate_saving_throw(roll, con_mod, proficiency_bonus, proficiency, other_modifiers=aura_bonus)
        concentration_broken = save_total < save_dc
        
        if concentration_broken:
            self.is_concentrating = False
            spell_name = self.concentration_spell
            self.concentration_spell = ""
            self.save()
            try:
                from combat.spell_rules import remove_caster_concentration_buffs
                remove_caster_concentration_buffs(self)
            except Exception:
                pass
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
        self.attacks_remaining = self._calculate_attacks_per_action()
        if self.legendary_actions_max > 0:
            self.legendary_actions_remaining = self.legendary_actions_max
        elif self.participant_type == 'enemy':
            enemy = self.resolve_enemy()
            if enemy and (enemy.legendary_actions.exists() or enemy.actions.filter(action_type='legendary_action').exists()):
                self.legendary_actions_max = 3
                self.legendary_actions_remaining = 3
        if self.feature_uses:
            self.feature_uses['dash_active'] = False
            self.feature_uses['disengaged'] = False
            self.feature_uses['dodging'] = False
            self.feature_uses['dodge_active'] = False
            self.feature_uses['hidden'] = False
            self.feature_uses['reckless_attack_active'] = False
            self.feature_uses['sneak_attack_used_this_turn'] = False
            self.feature_uses['shield_spell_active'] = False
            self.feature_uses['colossus_slayer_used_this_turn'] = False
            self.feature_uses['open_hand_flurry_attacks_remaining'] = 0

        # Champion Fighter: Survivor (regain 5 + CON modifier HP if <= half HP at turn start)
        try:
            from combat.subclasses import apply_champion_survivor
            apply_champion_survivor(self)
        except Exception:
            pass

        if self.participant_type == 'enemy':
            recharged_items = self.check_recharges()
            session = getattr(self, 'combat_session', None) or getattr(self, 'session', None)
            if recharged_items and session:
                try:
                    for rec_name in recharged_items:
                        CombatAction.objects.create(
                            combat_session=session,
                            actor=self,
                            action_type='other',
                            attack_name=rec_name,
                            round_number=session.current_round,
                            turn_number=session.current_turn_index,
                            description=f"✦ {self.get_name()}'s {rec_name} has recharged! ✦",
                        )
                except Exception:
                    pass
        self.save()
    
    def _calculate_attacks_per_action(self):
        """
        Calculate how many attacks this participant gets per Attack action.
        - Characters: based on Extra Attack class feature, with class/level fallback
        - Enemies: based on Multiattack ability (encounter or practice mode)
        """
        attacks = 1
        if self.character:
            from characters.models import CharacterFeature
            features = CharacterFeature.objects.filter(
                character=self.character
            ).values_list('name', flat=True)
            
            feature_names = [f.lower() for f in features]
            
            # Fighter level 20: 4 attacks
            if any('extra attack (3)' in f or 'three extra attack' in f for f in feature_names):
                attacks = 4
            # Fighter level 11: 3 attacks
            elif any('extra attack (2)' in f or 'two extra attack' in f for f in feature_names):
                attacks = 3
            # Most martial classes level 5: 2 attacks
            elif any('extra attack' in f for f in feature_names):
                attacks = 2
            # Fallback based on class and level if CharacterFeature records are missing
            elif hasattr(self.character, 'character_class') and self.character.character_class:
                class_name = self.character.character_class.name.lower().split('(')[0].strip()
                lvl = self.character.level
                if class_name == 'fighter':
                    if lvl >= 20:
                        attacks = 4
                    elif lvl >= 11:
                        attacks = 3
                    elif lvl >= 5:
                        attacks = 2
                elif class_name in ['barbarian', 'paladin', 'ranger', 'monk']:
                    if lvl >= 5:
                        attacks = 2
        
        elif self.participant_type == 'enemy':
            enemy = self.resolve_enemy()
            if enemy:
                if hasattr(enemy, 'multiattack'):
                    attacks = enemy.multiattack.action_count
                else:
                    for ability in enemy.abilities.all():
                        if 'multiattack' in ability.name.lower():
                            desc = ability.description.lower()
                            number_words = {
                                'two': 2, 'three': 3, 'four': 4, 'five': 5,
                                '2': 2, '3': 3, '4': 4, '5': 5,
                            }
                            for word, count in number_words.items():
                                if word in desc:
                                    attacks = count
                                    break
                            else:
                                attacks = 2
                            break

        # 5e Haste spell: grants +1 additional action/attack each turn
        if hasattr(self, 'has_buff') and self.has_buff('haste'):
            attacks += 1

        return attacks
    
    def reset_reaction(self):
        """Reset reaction at start of round (reactions reset each round)"""
        # Check if reaction is locked by Open Hand Technique
        if self.feature_uses and isinstance(self.feature_uses, dict):
            lock_until = self.feature_uses.get('no_reactions_until_round')
            if lock_until:
                session = getattr(self, 'combat_session', None) or getattr(self, 'session', None)
                cur_round = session.current_round if session else 1
                if cur_round < lock_until:
                    self.reaction_used = True
                    self.save(update_fields=['reaction_used'])
                    return
                else:
                    self.feature_uses.pop('no_reactions_until_round', None)
                    self.save(update_fields=['feature_uses'])

        self.reaction_used = False
        self.save(update_fields=['reaction_used'])
    
    def can_use_reaction(self):
        """Check if participant can use a reaction"""
        if self.feature_uses and isinstance(self.feature_uses, dict):
            lock_until = self.feature_uses.get('no_reactions_until_round')
            if lock_until:
                session = getattr(self, 'combat_session', None) or getattr(self, 'session', None)
                cur_round = session.current_round if session else 1
                if cur_round < lock_until:
                    return False
        return not self.reaction_used and self.is_active
    
    def use_reaction(self):
        """Mark reaction as used"""
        self.reaction_used = True
        self.save(update_fields=['reaction_used'])
    
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
    is_advantage = models.BooleanField(default=False)
    is_disadvantage = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['round_number', 'turn_number', 'created_at']
    
    def __str__(self):
        actor_name = self.actor.get_name() if self.actor else "System"
        return f"{actor_name} - {self.get_action_type_display()} (Round {self.round_number})"


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
        enc_name = self.combat_session.encounter.name if (self.combat_session and self.combat_session.encounter) else f"Combat #{self.combat_session_id}"
        return f"Combat Log: {enc_name} ({self.total_rounds} rounds)"
    
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
            actor_id = action.actor.id if action.actor else None
            if actor_id and actor_id in participant_stats:
                participant_stats[actor_id]['actions_by_type'][action_type] = \
                    participant_stats[actor_id]['actions_by_type'].get(action_type, 0) + 1
            
            # Track damage
            if action.damage_amount:
                # Damage dealt
                if actor_id and actor_id in participant_stats:
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
            if action.action_type == 'attack' and actor_id and actor_id in participant_stats:
                participant_stats[actor_id]['attacks_made'] += 1
                if action.hit:
                    participant_stats[actor_id]['attacks_hit'] += 1
                    if action.critical:
                        participant_stats[actor_id]['critical_hits'] += 1
                else:
                    participant_stats[actor_id]['attacks_missed'] += 1
            
            # Track spells
            if action.action_type == 'spell' and actor_id and actor_id in participant_stats:
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
