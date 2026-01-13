from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from bestiary.models import Language, DamageType


class CharacterClass(models.Model):
    """D&D 5e character classes"""
    CLASS_CHOICES = [
        ('barbarian', 'Barbarian'),
        ('bard', 'Bard'),
        ('cleric', 'Cleric'),
        ('druid', 'Druid'),
        ('fighter', 'Fighter'),
        ('monk', 'Monk'),
        ('paladin', 'Paladin'),
        ('ranger', 'Ranger'),
        ('rogue', 'Rogue'),
        ('sorcerer', 'Sorcerer'),
        ('warlock', 'Warlock'),
        ('wizard', 'Wizard'),
    ]
    
    name = models.CharField(max_length=20, choices=CLASS_CHOICES, unique=True)
    hit_dice = models.CharField(max_length=10)  # e.g. "d8", "d10"
    primary_ability = models.CharField(max_length=3)  # STR, DEX, CON, INT, WIS, CHA
    saving_throw_proficiencies = models.CharField(max_length=10)  # e.g. "STR,CON"
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.get_name_display()


class CharacterRace(models.Model):
    """D&D 5e character races"""
    RACE_CHOICES = [
        ('human', 'Human'),
        ('elf', 'Elf'),
        ('dwarf', 'Dwarf'),
        ('halfling', 'Halfling'),
        ('dragonborn', 'Dragonborn'),
        ('gnome', 'Gnome'),
        ('half-elf', 'Half-Elf'),
        ('half-orc', 'Half-Orc'),
        ('tiefling', 'Tiefling'),
    ]
    
    name = models.CharField(max_length=20, choices=RACE_CHOICES, unique=True)
    size = models.CharField(max_length=1, choices=[
        ('S', 'Small'),
        ('M', 'Medium'),
    ], default='M')
    speed = models.IntegerField(default=30)  # Base speed in feet
    ability_score_increases = models.CharField(max_length=50, blank=True)  # e.g. "STR+1,DEX+1"
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.get_name_display()


class CharacterBackground(models.Model):
    """D&D 5e character backgrounds"""
    BACKGROUND_CHOICES = [
        ('acolyte', 'Acolyte'),
        ('criminal', 'Criminal'),
        ('folk-hero', 'Folk Hero'),
        ('noble', 'Noble'),
        ('sage', 'Sage'),
        ('soldier', 'Soldier'),
        ('hermit', 'Hermit'),
        ('outlander', 'Outlander'),
        ('entertainer', 'Entertainer'),
        ('guild-artisan', 'Guild Artisan'),
        ('charlatan', 'Charlatan'),
        ('sailor', 'Sailor'),
    ]
    
    name = models.CharField(max_length=20, choices=BACKGROUND_CHOICES, unique=True)
    skill_proficiencies = models.CharField(max_length=100, blank=True)  # e.g. "Insight,Religion"
    tool_proficiencies = models.CharField(max_length=100, blank=True)  # e.g. "Disguise Kit,Thieves' Tools"
    languages = models.IntegerField(default=0)  # Number of additional languages
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.get_name_display()


class Character(models.Model):
    """Player character"""
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters', null=True, blank=True)
    name = models.CharField(max_length=100)
    level = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    character_class = models.ForeignKey(CharacterClass, on_delete=models.PROTECT, related_name='characters')
    race = models.ForeignKey(CharacterRace, on_delete=models.PROTECT, related_name='characters')
    background = models.ForeignKey(CharacterBackground, on_delete=models.PROTECT, related_name='characters', blank=True, null=True)
    
    # Subclass (chosen at level 2 or 3 depending on class)
    subclass = models.CharField(max_length=100, blank=True, null=True, help_text="Character's subclass (e.g., 'Champion', 'Battle Master', 'College of Lore')")
    
    # Basic properties
    size = models.CharField(max_length=1, choices=SIZE_CHOICES, default='M')
    alignment = models.CharField(max_length=2, choices=ALIGNMENT_CHOICES, default='N')
    
    # Experience points
    experience_points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Pending choices (for standalone character tracking)
    pending_asi_levels = models.JSONField(default=list, blank=True, help_text="List of levels where ASI/Feat is pending player choice (e.g., [4, 8])")
    pending_subclass_selection = models.BooleanField(default=False, help_text="True if character needs to select subclass")
    
    # Character description
    player_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True, null=True)
    backstory = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (Level {self.level} {self.character_class.get_name_display()})"
    
    def clean(self):
        """Validate character data"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate level range
        if not (1 <= self.level <= 20):
            errors['level'] = 'Level must be between 1 and 20'
        
        # Validate XP is non-negative
        if self.experience_points < 0:
            errors['experience_points'] = 'Experience points cannot be negative'
        
        # Validate XP matches level (minimum XP for that level)
        xp_table = {
            1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
            6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
            11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
            16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000,
        }
        min_xp = xp_table.get(self.level, 0)
        if self.level > 1 and self.experience_points < min_xp:
            errors['experience_points'] = f'XP ({self.experience_points}) is too low for level {self.level}. Minimum XP required: {min_xp}'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def proficiency_bonus(self):
        """Calculate proficiency bonus based on total level"""
        from core.dnd_utils import calculate_proficiency_bonus
        total_level = self.level
        # Check for multiclass
        try:
            from .multiclassing import get_total_level
            multiclass_level = get_total_level(self)
            # Only use multiclass level if it's greater than 0
            if multiclass_level > 0:
                total_level = multiclass_level
        except:
            pass
        return calculate_proficiency_bonus(total_level)


class CharacterStats(models.Model):
    """Comprehensive D&D 5e stat block for player characters"""
    character = models.OneToOneField(Character, on_delete=models.CASCADE, related_name="stats")
    
    # Core Stats (ability scores)
    strength = models.IntegerField(default=10)
    dexterity = models.IntegerField(default=10)
    constitution = models.IntegerField(default=10)
    intelligence = models.IntegerField(default=10)
    wisdom = models.IntegerField(default=10)
    charisma = models.IntegerField(default=10)
    
    # Combat Stats
    hit_points = models.IntegerField()
    max_hit_points = models.IntegerField()  # Maximum HP (for healing)
    armor_class = models.IntegerField()
    speed = models.IntegerField(default=30)  # Base speed in feet
    initiative = models.IntegerField(default=0)  # Initiative modifier
    
    # Hit Dice
    hit_dice_total = models.CharField(max_length=20, blank=True, null=True)  # e.g. "5d8"
    hit_dice_current = models.CharField(max_length=20, blank=True, null=True)  # e.g. "3d8" (remaining)
    
    # Senses
    darkvision = models.IntegerField(default=0)  # Range in feet
    passive_perception = models.IntegerField(default=10)
    passive_investigation = models.IntegerField(default=10)
    passive_insight = models.IntegerField(default=10)
    
    # Spellcasting (if applicable)
    spell_save_dc = models.IntegerField(blank=True, null=True)
    spell_attack_bonus = models.IntegerField(blank=True, null=True)
    
    # Spell slots tracking (stored as JSON: {"1": 3, "2": 2} means 3 level-1, 2 level-2 slots remaining)
    spell_slots = models.JSONField(default=dict, blank=True, help_text="Current spell slots remaining by level")
    
    def __str__(self):
        return f"{self.character.name} - Stats"
    
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


class CharacterProficiency(models.Model):
    """Character proficiencies (skills, tools, weapons, armor, languages)"""
    PROFICIENCY_TYPES = [
        ('skill', 'Skill'),
        ('tool', 'Tool'),
        ('weapon', 'Weapon'),
        ('armor', 'Armor'),
        ('language', 'Language'),
        ('saving_throw', 'Saving Throw'),
    ]
    
    PROFICIENCY_LEVELS = [
        ('proficient', 'Proficient'),
        ('expertise', 'Expertise'),  # Double proficiency (Rogues, Bards)
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="proficiencies")
    proficiency_type = models.CharField(max_length=20, choices=PROFICIENCY_TYPES)
    proficiency_level = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS, default='proficient')
    
    # For skills
    skill_name = models.CharField(max_length=50, blank=True, null=True)  # e.g. "Athletics", "Stealth"
    
    # For tools, weapons, armor
    item_name = models.CharField(max_length=100, blank=True, null=True)  # e.g. "Thieves' Tools", "Longsword"
    
    # For languages
    language = models.ForeignKey(Language, on_delete=models.CASCADE, blank=True, null=True, related_name='character_proficiencies')
    
    # For saving throws
    ability_score = models.CharField(max_length=3, blank=True, null=True)  # STR, DEX, CON, INT, WIS, CHA
    
    source = models.CharField(max_length=50, blank=True)  # e.g. "Class", "Race", "Background", "Feat"
    
    def __str__(self):
        if self.proficiency_type == 'skill':
            return f"{self.character.name} - {self.skill_name} ({self.proficiency_level})"
        elif self.proficiency_type == 'language':
            return f"{self.character.name} - {self.language.name}"
        elif self.proficiency_type == 'saving_throw':
            return f"{self.character.name} - {self.ability_score} Save"
        else:
            return f"{self.character.name} - {self.item_name} ({self.proficiency_type})"
    
    class Meta:
        unique_together = [
            ['character', 'proficiency_type', 'skill_name'],
            ['character', 'proficiency_type', 'item_name'],
            ['character', 'proficiency_type', 'language'],
            ['character', 'proficiency_type', 'ability_score'],
        ]


class CharacterFeature(models.Model):
    """Character features (class features, racial features, feats)"""
    FEATURE_TYPES = [
        ('class', 'Class Feature'),
        ('racial', 'Racial Feature'),
        ('background', 'Background Feature'),
        ('feat', 'Feat'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="features")
    name = models.CharField(max_length=100)
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPES)
    description = models.TextField()
    source = models.CharField(max_length=100, blank=True)  # e.g. "Fighter Level 2", "Elf Race"
    
    def __str__(self):
        return f"{self.character.name} - {self.name}"


class CharacterSpell(models.Model):
    """Spells known/prepared by a character"""
    SPELL_LEVELS = [
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
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="spells")
    name = models.CharField(max_length=100)
    level = models.IntegerField(choices=SPELL_LEVELS)
    school = models.CharField(max_length=50, blank=True)  # e.g. "Evocation", "Abjuration"
    is_prepared = models.BooleanField(default=False)  # For prepared casters
    is_ritual = models.BooleanField(default=False)
    in_spellbook = models.BooleanField(default=False)  # For Wizards - spell is in spellbook
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.character.name} - {self.name} (Level {self.level})"
    
    class Meta:
        unique_together = ['character', 'name']


class CharacterResistance(models.Model):
    """Damage resistances/immunities for characters"""
    RESISTANCE_TYPES = [
        ('resistance', 'Resistance'),
        ('immunity', 'Immunity'),
        ('vulnerability', 'Vulnerability'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="resistances")
    damage_type = models.ForeignKey(DamageType, on_delete=models.CASCADE)
    resistance_type = models.CharField(max_length=20, choices=RESISTANCE_TYPES)
    source = models.CharField(max_length=100, blank=True)  # e.g. "Racial", "Class Feature", "Item"
    
    def __str__(self):
        return f"{self.character.name} - {self.resistance_type.title()} to {self.damage_type.name}"
    
    class Meta:
        unique_together = ['character', 'damage_type', 'resistance_type']


class CharacterItem(models.Model):
    """Tracks items in character inventory and equipment"""
    EQUIPMENT_SLOTS = [
        ('main_hand', 'Main Hand'),
        ('off_hand', 'Off Hand'),
        ('armor', 'Armor'),
        ('shield', 'Shield'),
        ('ring', 'Ring'),
        ('amulet', 'Amulet'),
        ('boots', 'Boots'),
        ('gloves', 'Gloves'),
        ('helmet', 'Helmet'),
        ('cloak', 'Cloak'),
        ('inventory', 'Inventory'),  # Not equipped
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='character_items')
    item = models.ForeignKey('items.Item', on_delete=models.CASCADE, related_name='character_items')
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    is_equipped = models.BooleanField(default=False)
    equipment_slot = models.CharField(max_length=20, choices=EQUIPMENT_SLOTS, default='inventory')
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['character', 'item', 'equipment_slot']
        ordering = ['equipment_slot', 'item__name']
    
    def __str__(self):
        status = "equipped" if self.is_equipped else "inventory"
        return f"{self.character.name} - {self.item.name} x{self.quantity} ({status})"


class Feat(models.Model):
    """D&D 5e feats that can be taken instead of ASI"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Prerequisites
    strength_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    dexterity_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    constitution_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    intelligence_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    wisdom_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    charisma_requirement = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(20)])
    
    # Level requirements
    minimum_level = models.IntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(20)])
    
    # Proficiency requirements
    proficiency_requirements = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Comma-separated list of required proficiencies (e.g., 'Heavy Armor,Martial Weapons')"
    )
    
    # Ability score increases granted by this feat (some feats give +1 to a stat)
    ability_score_increase = models.CharField(
        max_length=3,
        blank=True,
        choices=[
            ('STR', 'Strength'),
            ('DEX', 'Dexterity'),
            ('CON', 'Constitution'),
            ('INT', 'Intelligence'),
            ('WIS', 'Wisdom'),
            ('CHA', 'Charisma'),
        ],
        help_text="If this feat grants +1 to an ability score, specify which one"
    )
    
    # Source book
    source = models.CharField(max_length=100, default='Player\'s Handbook')
    
    def __str__(self):
        return self.name
    
    def check_prerequisites(self, character):
        """
        Check if a character meets the prerequisites for this feat.
        
        Args:
            character: Character instance
        
        Returns:
            tuple: (is_eligible, reason_if_not)
        """
        if not hasattr(character, 'stats'):
            return False, "Character must have stats"
        
        stats = character.stats
        
        # Check level requirement
        if character.level < self.minimum_level:
            return False, f"Requires level {self.minimum_level}"
        
        # Check ability score requirements
        if stats.strength < self.strength_requirement:
            return False, f"Requires Strength {self.strength_requirement}"
        if stats.dexterity < self.dexterity_requirement:
            return False, f"Requires Dexterity {self.dexterity_requirement}"
        if stats.constitution < self.constitution_requirement:
            return False, f"Requires Constitution {self.constitution_requirement}"
        if stats.intelligence < self.intelligence_requirement:
            return False, f"Requires Intelligence {self.intelligence_requirement}"
        if stats.wisdom < self.wisdom_requirement:
            return False, f"Requires Wisdom {self.wisdom_requirement}"
        if stats.charisma < self.charisma_requirement:
            return False, f"Requires Charisma {self.charisma_requirement}"
        
        # Check proficiency requirements
        if self.proficiency_requirements:
            required_profs = [p.strip() for p in self.proficiency_requirements.split(',')]
            character_profs = set(
                character.proficiencies.values_list('skill_name', flat=True)
            ) | set(
                character.proficiencies.values_list('item_name', flat=True)
            )
            
            for req_prof in required_profs:
                if req_prof not in character_profs:
                    return False, f"Requires proficiency in {req_prof}"
        
        return True, None
    
    class Meta:
        ordering = ['name']


class CharacterFeat(models.Model):
    """Tracks which feats a character has taken"""
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='character_feats')
    feat = models.ForeignKey(Feat, on_delete=models.CASCADE, related_name='character_feats')
    level_taken = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Level at which this feat was taken"
    )
    taken_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['character', 'feat']
        ordering = ['level_taken', 'feat__name']
    
    def __str__(self):
        return f"{self.character.name} - {self.feat.name} (Level {self.level_taken})"


class CharacterClassLevel(models.Model):
    """Tracks levels in each class for multiclass characters"""
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='class_levels')
    character_class = models.ForeignKey(CharacterClass, on_delete=models.PROTECT, related_name='character_levels')
    level = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    
    # Subclass for this class (if applicable)
    subclass = models.CharField(max_length=100, blank=True, null=True, help_text="Subclass for this class")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['character', 'character_class']
        ordering = ['-level', 'character_class__name']
    
    def __str__(self):
        return f"{self.character.name} - {self.character_class.get_name_display()} Level {self.level}"