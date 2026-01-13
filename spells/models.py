from django.db import models
from characters.models import CharacterClass
from bestiary.models import DamageType


class Spell(models.Model):
    """
    Central spell library for D&D 5e spells.
    Integrates with Open5e API for comprehensive spell data.
    """
    SPELL_LEVEL_CHOICES = [
        (0, 'Cantrip'),
        (1, '1st Level'),
        (2, '2nd Level'),
        (3, '3rd Level'),
        (4, '4th Level'),
        (5, '5th Level'),
        (6, '6th Level'),
        (7, '7th Level'),
        (8, '8th Level'),
        (9, '9th Level'),
    ]
    
    SCHOOL_CHOICES = [
        ('abjuration', 'Abjuration'),
        ('conjuration', 'Conjuration'),
        ('divination', 'Divination'),
        ('enchantment', 'Enchantment'),
        ('evocation', 'Evocation'),
        ('illusion', 'Illusion'),
        ('necromancy', 'Necromancy'),
        ('transmutation', 'Transmutation'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly name for API reference")
    level = models.IntegerField(choices=SPELL_LEVEL_CHOICES, default=0)
    school = models.CharField(max_length=20, choices=SCHOOL_CHOICES)
    
    # Casting Information
    casting_time = models.CharField(max_length=100, help_text="e.g., '1 action', '1 bonus action', '1 minute'")
    range = models.CharField(max_length=100, help_text="e.g., 'Self', '60 feet', 'Touch'")
    components = models.CharField(max_length=100, help_text="V, S, M components")
    material = models.TextField(blank=True, help_text="Material component description if M is required")
    duration = models.CharField(max_length=100, help_text="e.g., 'Instantaneous', '1 hour', 'Concentration, up to 1 minute'")
    concentration = models.BooleanField(default=False)
    ritual = models.BooleanField(default=False)
    
    # Effects and Description
    description = models.TextField(help_text="Full spell description")
    higher_level = models.TextField(blank=True, help_text="Description of effects when cast at higher levels")
    
    # Class Availability
    classes = models.ManyToManyField(
        CharacterClass,
        related_name='available_spells',
        blank=True,
        help_text="Which classes can learn this spell"
    )
    
    # Metadata
    source = models.CharField(max_length=50, default='PHB', help_text="Source book (PHB, XGE, TCE, etc.)")
    page = models.CharField(max_length=10, blank=True, help_text="Page number in source book")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level', 'name']
        indexes = [
            models.Index(fields=['level', 'school']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"
    
    def requires_concentration(self):
        """Check if spell requires concentration"""
        return self.concentration
    
    def is_ritual(self):
        """Check if spell can be cast as ritual"""
        return self.ritual


class SpellDamage(models.Model):
    """
    Damage progression for spells at different spell slot levels.
    Example: Fireball deals 8d6 at 3rd level, 9d6 at 4th level, etc.
    """
    spell = models.ForeignKey(Spell, on_delete=models.CASCADE, related_name='damage_progression')
    spell_slot_level = models.IntegerField(help_text="Spell slot level used to cast")
    damage_dice = models.CharField(max_length=20, help_text="e.g., '8d6', '3d8+3'")
    damage_type = models.ForeignKey(
        DamageType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Type of damage dealt"
    )
    
    class Meta:
        ordering = ['spell', 'spell_slot_level']
        unique_together = ['spell', 'spell_slot_level']
    
    def __str__(self):
        return f"{self.spell.name} at level {self.spell_slot_level}: {self.damage_dice}"
