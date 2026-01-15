# encounters/models.py
from django.db import models
from bestiary.models import Enemy, Condition


class EncounterTheme(models.Model):
    """Defines thematic encounter groups (e.g., Bandit Ambush, Beholder Lair)"""
    
    CATEGORY_CHOICES = [
        ('humanoid', 'Humanoid Threats'),
        ('undead', 'Undead Hordes'),
        ('beast', 'Beast Packs'),
        ('aberration', 'Aberrations'),
        ('elemental', 'Elemental Forces'),
        ('fiend', 'Fiendish Incursions'),
        ('dragon', 'Draconic Encounters'),
        ('fey', 'Fey Tricksters'),
        ('giant', 'Giant Clans'),
        ('dungeon', 'Dungeon Denizens'),
    ]
    
    ENVIRONMENT_CHOICES = [
        ('forest', 'Forest'),
        ('underdark', 'Underdark'),
        ('urban', 'Urban'),
        ('dungeon', 'Dungeon'),
        ('mountain', 'Mountain'),
        ('desert', 'Desert'),
        ('swamp', 'Swamp'),
        ('plains', 'Plains'),
        ('coast', 'Coast'),
        ('arctic', 'Arctic'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    
    min_cr = models.IntegerField(default=0, help_text="Minimum challenge rating")
    max_cr = models.IntegerField(default=30, help_text="Maximum challenge rating")
    
    # Frequency weight (higher = more common)
    weight = models.IntegerField(default=100)
    
    # Narrative flavor
    flavor_text = models.TextField(blank=True, help_text="Story description for DM")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class EnemyThemeAssociation(models.Model):
    """Links enemies to themes with specific roles"""
    
    ROLE_CHOICES = [
        ('primary', 'Primary Threat'),
        ('elite', 'Elite Unit'),
        ('support', 'Support/Minion'),
        ('leader', 'Leader'),
        ('artillery', 'Ranged Attacker'),
        ('controller', 'Battlefield Control'),
        ('tank', 'Defensive Wall'),
    ]
    
    theme = models.ForeignKey(
        EncounterTheme,
        on_delete=models.CASCADE,
        related_name='enemy_associations'
    )
    enemy = models.ForeignKey(
        Enemy,
        on_delete=models.CASCADE,
        related_name='theme_associations'
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    weight = models.IntegerField(default=100, help_text="Likelihood of appearing in theme")
    
    min_count = models.IntegerField(default=1, help_text="Minimum enemies of this type")
    max_count = models.IntegerField(default=4, help_text="Maximum enemies of this type")
    
    class Meta:
        unique_together = ['theme', 'enemy', 'role']
        ordering = ['theme', 'role', 'enemy']
    
    def __str__(self):
        return f"{self.enemy.name} as {self.get_role_display()} in {self.theme.name}"


class ThemeIncompatibility(models.Model):
    """Defines which themes should never mix (except in chaotic encounters)"""
    
    theme1 = models.ForeignKey(
        EncounterTheme,
        on_delete=models.CASCADE,
        related_name='incompatible_with'
    )
    theme2 = models.ForeignKey(
        EncounterTheme,
        on_delete=models.CASCADE,
        related_name='incompatible_as'
    )
    
    reason = models.TextField(help_text="Why these themes don't mix")
    allow_chaotic = models.BooleanField(
        default=True,
        help_text="Allow in chaotic encounters (5% chance)"
    )
    
    class Meta:
        unique_together = ['theme1', 'theme2']
    
    def __str__(self):
        return f"{self.theme1.name} incompatible with {self.theme2.name}"


class BiomeEncounterWeight(models.Model):
    """Defines theme probabilities per biome (60/20/15/5 distribution)"""
    
    BIOME_CHOICES = [
        ('forest', 'Forest'),
        ('desert', 'Desert'),
        ('mountain', 'Mountain'),
        ('swamp', 'Swamp'),
        ('plains', 'Plains'),
        ('coast', 'Coast'),
        ('arctic', 'Arctic'),
        ('underdark', 'Underdark'),
        ('urban', 'Urban'),
        ('dungeon', 'Dungeon'),
    ]
    
    CATEGORY_CHOICES = [
        ('endemic', 'Endemic - 60%'),
        ('adapted', 'Adapted - 20%'),
        ('traveler', 'Traveler - 15%'),
        ('anomaly', 'Anomaly - 5%'),
    ]
    
    biome = models.CharField(max_length=20, choices=BIOME_CHOICES)
    theme = models.ForeignKey(
        EncounterTheme,
        on_delete=models.CASCADE,
        related_name='biome_weights'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    weight = models.IntegerField(default=100, help_text="Relative likelihood")
    narrative_reason = models.TextField(
        blank=True,
        help_text="Explanation for non-endemic encounters"
    )
    
    class Meta:
        unique_together = ['biome', 'theme', 'category']
        ordering = ['biome', 'category', 'theme']
    
    def __str__(self):
        return f"{self.theme.name} in {self.get_biome_display()} ({self.get_category_display()})"


class Encounter(models.Model):
    """Represents a group of enemies that the party encounters"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Theme and biome support
    theme = models.ForeignKey(
        EncounterTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encounters',
        help_text="Thematic group this encounter belongs to"
    )
    biome = models.CharField(
        max_length=20,
        choices=BiomeEncounterWeight.BIOME_CHOICES,
        blank=True,
        help_text="Environment where encounter takes place"
    )
    is_chaotic = models.BooleanField(
        default=False,
        help_text="True if this encounter mixes incompatible themes"
    )
    narrative_justification = models.TextField(
        blank=True,
        help_text="Story reason for anomalies or chaotic encounters"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class EncounterEnemy(models.Model):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='enemies')
    enemy = models.ForeignKey(Enemy, on_delete=models.PROTECT, related_name='encounter_instances')

    # Instance-specific stats
    name = models.CharField(max_length=100)
    initiative = models.IntegerField(default=0)
    current_hp = models.IntegerField()
    is_alive = models.BooleanField(default=True)

    # Optional fields for combat tracking
    conditions = models.TextField(blank=True, help_text="Comma-separated list of conditions (e.g., stunned, poisoned)")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} (Encounter: {self.encounter.name})"

    def take_damage(self, amount):
        """Apply damage and update alive status"""
        self.current_hp -= amount
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive = False
        self.save()

    
    def heal(self, amount):
        """Increase HP, cannot exceed the enemy’s base HP."""
        # Try to get the max HP from EnemyStats if available
        if hasattr(self.enemy, "stats") and self.enemy.stats.hit_points:
            max_hp = self.enemy.stats.hit_points
        else:
            # fallback to Enemy.hp if stats are missing
            max_hp = getattr(self.enemy, "hp", self.current_hp)

        # Heal but not above max_hp
        self.current_hp = min(self.current_hp + amount, max_hp)
        if self.current_hp > 0:
            self.is_alive = True
        self.save()