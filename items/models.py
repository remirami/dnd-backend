from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from bestiary.models import DamageType


class ItemCategory(models.Model):
    """Categories for items (Weapon, Armor, Consumable, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Item Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ItemProperty(models.Model):
    """Properties that items can have (Versatile, Finesse, Two-Handed, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    
    class Meta:
        verbose_name_plural = "Item Properties"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Item(models.Model):
    """Base item model"""
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('very_rare', 'Very Rare'),
        ('legendary', 'Legendary'),
        ('artifact', 'Artifact'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Weight in pounds")
    value = models.IntegerField(default=0, help_text="Value in gold pieces")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    is_magical = models.BooleanField(default=False)
    requires_attunement = models.BooleanField(default=False)
    
    # Properties (many-to-many for items like versatile weapons)
    properties = models.ManyToManyField(ItemProperty, blank=True, related_name='items')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Weapon(Item):
    """Weapon items"""
    WEAPON_TYPE_CHOICES = [
        ('simple_melee', 'Simple Melee'),
        ('simple_ranged', 'Simple Ranged'),
        ('martial_melee', 'Martial Melee'),
        ('martial_ranged', 'Martial Ranged'),
    ]
    
    DAMAGE_TYPE_CHOICES = [
        ('bludgeoning', 'Bludgeoning'),
        ('piercing', 'Piercing'),
        ('slashing', 'Slashing'),
    ]
    
    weapon_type = models.CharField(max_length=20, choices=WEAPON_TYPE_CHOICES)
    damage_dice = models.CharField(max_length=20, help_text="e.g., '1d6', '2d4'")
    damage_type = models.ForeignKey(DamageType, on_delete=models.SET_NULL, null=True, blank=True)
    versatile_damage = models.CharField(max_length=20, blank=True, help_text="Damage when used two-handed, e.g., '1d10'")
    range_normal = models.IntegerField(default=0, help_text="Normal range in feet (0 for melee)")
    range_long = models.IntegerField(default=0, help_text="Long range in feet (0 for melee)")
    finesse = models.BooleanField(default=False, help_text="Can use DEX instead of STR")
    thrown = models.BooleanField(default=False, help_text="Can be thrown")
    ammunition = models.BooleanField(default=False, help_text="Requires ammunition")
    loading = models.BooleanField(default=False, help_text="Requires loading")
    two_handed = models.BooleanField(default=False, help_text="Requires two hands")
    heavy = models.BooleanField(default=False, help_text="Heavy weapon")
    light = models.BooleanField(default=False, help_text="Light weapon")
    reach = models.BooleanField(default=False, help_text="Has reach")
    
    # 2024 Weapon Mastery Property
    mastery_property = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Weapon Mastery Property (2024 Rules): Cleave, Graze, Nick, Push, Sap, Slow, Topple, Vex"
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_weapon_type_display()})"


class Armor(Item):
    """Armor items"""
    ARMOR_TYPE_CHOICES = [
        ('light', 'Light Armor'),
        ('medium', 'Medium Armor'),
        ('heavy', 'Heavy Armor'),
        ('shield', 'Shield'),
    ]
    
    armor_type = models.CharField(max_length=20, choices=ARMOR_TYPE_CHOICES)
    base_ac = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(30)], help_text="Base AC")
    max_dex_bonus = models.IntegerField(null=True, blank=True, help_text="Maximum DEX bonus (null = unlimited)")
    min_strength = models.IntegerField(default=0, help_text="Minimum STR requirement")
    stealth_disadvantage = models.BooleanField(default=False, help_text="Disadvantage on stealth checks")
    
    class Meta:
        ordering = ['armor_type', 'name']
    
    def __str__(self):
        return f"{self.name} (AC {self.base_ac})"


class Consumable(Item):
    """Consumable items (potions, scrolls, etc.)"""
    CONSUMABLE_TYPE_CHOICES = [
        ('potion', 'Potion'),
        ('scroll', 'Scroll'),
        ('food', 'Food'),
        ('other', 'Other'),
    ]
    
    consumable_type = models.CharField(max_length=20, choices=CONSUMABLE_TYPE_CHOICES, default='other')
    effect = models.TextField(help_text="Description of the item's effect")
    duration = models.CharField(max_length=50, blank=True, help_text="Duration of effect, e.g., '1 hour'")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_consumable_type_display()})"


class MagicItem(Item):
    """Magic items with special properties"""
    attunement_required = models.BooleanField(default=False)
    charges = models.IntegerField(null=True, blank=True, help_text="Number of charges (null = unlimited)")
    charges_per_day = models.IntegerField(default=0, help_text="Charges regained per day")
    spell_effect = models.TextField(blank=True, help_text="Spell effect description")
    bonus_to_hit = models.IntegerField(default=0, help_text="Bonus to attack rolls")
    bonus_to_damage = models.IntegerField(default=0, help_text="Bonus to damage rolls")
    bonus_to_ac = models.IntegerField(default=0, help_text="Bonus to AC")
    bonus_to_saves = models.IntegerField(default=0, help_text="Bonus to saving throws")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"
