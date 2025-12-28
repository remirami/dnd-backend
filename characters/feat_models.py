"""
Feat Models for D&D 5e

Feats are special abilities that characters can take instead of Ability Score Improvements
at levels 4, 8, 12, 16, and 19.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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
    
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='character_feats')
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

