from django.db import models


class Enemy(models.Model):
    SIZE_CHOICES = [
        ('T', 'Tiny'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('H', 'Huge'),
        ('G', 'Gargantuan'),
    ]
    
    CREATURE_TYPE_CHOICES = [
        ('aberration', 'Aberration'),
        ('beast', 'Beast'),
        ('celestial', 'Celestial'),
        ('construct', 'Construct'),
        ('dragon', 'Dragon'),
        ('elemental', 'Elemental'),
        ('fey', 'Fey'),
        ('fiend', 'Fiend'),
        ('giant', 'Giant'),
        ('humanoid', 'Humanoid'),
        ('monstrosity', 'Monstrosity'),
        ('ooze', 'Ooze'),
        ('plant', 'Plant'),
        ('undead', 'Undead'),
    ]
    
    ALIGNMENT_CHOICES = [
        ('LG', 'Lawful Good'),
        ('NG', 'Neutral Good'),
        ('CG', 'Chaotic Good'),
        ('LN', 'Lawful Neutral'),
        ('N', 'Neutral'),
        ('CN', 'Chaotic Neutral'),
        ('LE', 'Lawful Evil'),
        ('NE', 'Neutral Evil'),
        ('CE', 'Chaotic Evil'),
        ('U', 'Unaligned'),
    ]
    
    name = models.CharField(max_length=100)
    hp = models.IntegerField(blank=True, null=True)
    ac = models.IntegerField(blank=True, null=True)
    challenge_rating = models.CharField(max_length=10, blank=True, null=True)
    
    # Creature Properties
    size = models.CharField(max_length=1, choices=SIZE_CHOICES, default='M')
    creature_type = models.CharField(max_length=20, choices=CREATURE_TYPE_CHOICES, default='humanoid')
    alignment = models.CharField(max_length=2, choices=ALIGNMENT_CHOICES, default='N')

    class Meta:
        indexes = [
            models.Index(fields=['challenge_rating'], name='enemy_cr_idx'),
            models.Index(fields=['creature_type'], name='enemy_type_idx'),
            models.Index(fields=['name'], name='enemy_name_idx'),
        ]

    def __str__(self):
        return self.name


class EnemyStats(models.Model):
    """Comprehensive D&D 5e stat block for enemies"""
    enemy = models.OneToOneField(Enemy, on_delete=models.CASCADE, related_name="stats")
    
    # Core Stats (ability scores)
    strength = models.IntegerField(default=10)
    dexterity = models.IntegerField(default=10)
    constitution = models.IntegerField(default=10)
    intelligence = models.IntegerField(default=10)
    wisdom = models.IntegerField(default=10)
    charisma = models.IntegerField(default=10)
    
    # Combat Stats
    hit_points = models.IntegerField()
    armor_class = models.IntegerField()
    speed = models.CharField(max_length=100, blank=True, null=True)  # e.g. "30 ft., fly 60 ft."
    
    # Saving Throws (proficiency bonus applied)
    str_save = models.IntegerField(blank=True, null=True)
    dex_save = models.IntegerField(blank=True, null=True)
    con_save = models.IntegerField(blank=True, null=True)
    int_save = models.IntegerField(blank=True, null=True)
    wis_save = models.IntegerField(blank=True, null=True)
    cha_save = models.IntegerField(blank=True, null=True)
    
    # Skills (proficiency bonus applied)
    athletics = models.IntegerField(blank=True, null=True)
    acrobatics = models.IntegerField(blank=True, null=True)
    sleight_of_hand = models.IntegerField(blank=True, null=True)
    stealth = models.IntegerField(blank=True, null=True)
    arcana = models.IntegerField(blank=True, null=True)
    history = models.IntegerField(blank=True, null=True)
    investigation = models.IntegerField(blank=True, null=True)
    nature = models.IntegerField(blank=True, null=True)
    religion = models.IntegerField(blank=True, null=True)
    animal_handling = models.IntegerField(blank=True, null=True)
    insight = models.IntegerField(blank=True, null=True)
    medicine = models.IntegerField(blank=True, null=True)
    perception = models.IntegerField(blank=True, null=True)
    survival = models.IntegerField(blank=True, null=True)
    deception = models.IntegerField(blank=True, null=True)
    intimidation = models.IntegerField(blank=True, null=True)
    performance = models.IntegerField(blank=True, null=True)
    persuasion = models.IntegerField(blank=True, null=True)
    
    # Senses
    darkvision = models.CharField(max_length=50, blank=True, null=True)  # e.g. "60 ft."
    blindsight = models.CharField(max_length=50, blank=True, null=True)
    tremorsense = models.CharField(max_length=50, blank=True, null=True)
    truesight = models.CharField(max_length=50, blank=True, null=True)
    
    # Passive Perception
    passive_perception = models.IntegerField(blank=True, null=True)
    
    # Spellcasting
    spell_save_dc = models.IntegerField(blank=True, null=True)
    spell_attack_bonus = models.IntegerField(blank=True, null=True)
    
    # Hit Dice & Proficiency
    hit_dice = models.CharField(max_length=20, blank=True, null=True)  # e.g. "8d8+16"
    hit_dice_average = models.IntegerField(blank=True, null=True)  # Average HP
    proficiency_bonus = models.IntegerField(blank=True, null=True)  # Based on CR
    
    def __str__(self):
        return f"{self.enemy.name} - Stats"
    
    @property
    def strength_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.strength)
    
    @property
    def dexterity_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.dexterity)
    
    @property
    def constitution_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.constitution)
    
    @property
    def intelligence_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.intelligence)
    
    @property
    def wisdom_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.wisdom)
    
    @property
    def charisma_modifier(self):
        from core.dnd_utils import calculate_ability_modifier
        return calculate_ability_modifier(self.charisma)


class DamageType(models.Model):
    """Damage types in D&D 5e"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class EnemyResistance(models.Model):
    """Damage resistances for enemies"""
    RESISTANCE_TYPES = [
        ('resistance', 'Resistance'),
        ('immunity', 'Immunity'),
        ('vulnerability', 'Vulnerability'),
    ]
    
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="resistances")
    damage_type = models.ForeignKey(DamageType, on_delete=models.CASCADE)
    resistance_type = models.CharField(max_length=20, choices=RESISTANCE_TYPES)
    notes = models.TextField(blank=True, null=True)  # For special conditions
    
    def __str__(self):
        return f"{self.enemy.name} - {self.resistance_type.title()} to {self.damage_type.name}"
    
    class Meta:
        unique_together = ['enemy', 'damage_type', 'resistance_type']


class Language(models.Model):
    """Languages in D&D 5e"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class EnemyLanguage(models.Model):
    """Languages known by enemies"""
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="languages")
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.enemy.name} - {self.language.name}"
    
    class Meta:
        unique_together = ['enemy', 'language']


class Condition(models.Model):
    """D&D 5e conditions"""
    CONDITION_CHOICES = [
        ('blinded', 'Blinded'),
        ('charmed', 'Charmed'),
        ('deafened', 'Deafened'),
        ('frightened', 'Frightened'),
        ('grappled', 'Grappled'),
        ('incapacitated', 'Incapacitated'),
        ('invisible', 'Invisible'),
        ('paralyzed', 'Paralyzed'),
        ('petrified', 'Petrified'),
        ('poisoned', 'Poisoned'),
        ('prone', 'Prone'),
        ('restrained', 'Restrained'),
        ('stunned', 'Stunned'),
        ('unconscious', 'Unconscious'),
        ('exhaustion', 'Exhaustion'),
    ]
    
    name = models.CharField(max_length=20, choices=CONDITION_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.get_name_display()


class EnemyConditionImmunity(models.Model):
    """Condition immunities for enemies"""
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="condition_immunities")
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, null=True)  # For special conditions
    
    def __str__(self):
        return f"{self.enemy.name} - Immune to {self.condition.get_name_display()}"
    
    class Meta:
        unique_together = ['enemy', 'condition']


class EnemyLegendaryAction(models.Model):
    """Legendary actions for powerful creatures"""
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="legendary_actions")
    name = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.IntegerField(default=1)  # Legendary action points (1, 2, or 3)
    
    def __str__(self):
        return f"{self.enemy.name} - {self.name} ({self.cost} action{'s' if self.cost > 1 else ''})"


class Environment(models.Model):
    """Environments where creatures can be found"""
    ENVIRONMENT_CHOICES = [
        ('arctic', 'Arctic'),
        ('coastal', 'Coastal'),
        ('desert', 'Desert'),
        ('forest', 'Forest'),
        ('grassland', 'Grassland'),
        ('hill', 'Hill'),
        ('mountain', 'Mountain'),
        ('swamp', 'Swamp'),
        ('underdark', 'Underdark'),
        ('underwater', 'Underwater'),
        ('urban', 'Urban'),
        ('any', 'Any'),
    ]
    
    name = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, unique=True)
    
    def __str__(self):
        return self.get_name_display()


class EnemyEnvironment(models.Model):
    """Environments where enemies can be found"""
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="environments")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.enemy.name} - {self.environment.get_name_display()}"
    
    class Meta:
        unique_together = ['enemy', 'environment']


class EnemyTreasure(models.Model):
    """Treasure that enemies might have"""
    TREASURE_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('hoard', 'Hoard'),
        ('both', 'Both'),
    ]
    
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="treasure")
    treasure_type = models.CharField(max_length=10, choices=TREASURE_TYPE_CHOICES)
    description = models.TextField()
    
    def __str__(self):
        return f"{self.enemy.name} - {self.get_treasure_type_display()}"


class EnemyAttack(models.Model):
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="attacks")
    name = models.CharField(max_length=100)
    bonus = models.IntegerField()
    damage = models.CharField(max_length=50)  # e.g. "2d6+3 slashing"

    def __str__(self):
        return f"{self.enemy.name} - {self.name}"


class EnemyAbility(models.Model):
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="abilities")
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"{self.enemy.name} - {self.name}"


class EnemySpell(models.Model):
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE, related_name="spells")
    name = models.CharField(max_length=100)
    save_dc = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.enemy.name} - {self.name}"


class EnemySpellSlot(models.Model):
    spell = models.ForeignKey(EnemySpell, on_delete=models.CASCADE, related_name="slots")
    level = models.IntegerField()
    uses = models.IntegerField()  # e.g. 1/day or 3 uses per long rest

    def __str__(self):
        return f"{self.spell.name} - Level {self.level} ({self.uses} uses)"
