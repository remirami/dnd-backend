# encounters/models.py
from django.db import models
from bestiary.models import Enemy


class Encounter(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
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