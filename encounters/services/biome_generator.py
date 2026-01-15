"""
Biome Encounter Generator Service

Generates encounters with biome-based distribution (60/20/15/5 endemic/adapted/traveler/anomaly)
"""
import random

from encounters.models import BiomeEncounterWeight
from .encounter_generator import EncounterGenerator


class BiomeEncounterGenerator:
    """Generate encounters based on biome with 60/20/15/5 distribution"""
    
    # Distribution percentages
    DISTRIBUTION = {
        'endemic': 0.60,
        'adapted': 0.20,
        'traveler': 0.15,
        'anomaly': 0.05
    }
    
    def __init__(self):
        self.encounter_generator = EncounterGenerator()
    
    def generate_by_biome(self, biome, party_level, party_size,
                          difficulty='medium', force_category=None):
        """
        Generate encounter for specific biome
        
        Args:
            biome: Biome name (desert, forest, etc.)
            party_level: Average party level
            party_size: Number of players
            difficulty: Encounter difficulty
            force_category: Force specific category (endemic/adapted/traveler/anomaly)
            
        Returns:
            Encounter object
        """
        # Roll for category
        if force_category:
            category = force_category
        else:
            category = self._roll_category()
        
        # Get themes for this biome + category
        weights = BiomeEncounterWeight.objects.filter(
            biome=biome,
            category=category
        )
        
        if not weights.exists():
            # Fallback: use any theme for this biome
            weights = BiomeEncounterWeight.objects.filter(biome=biome)
            
            if not weights.exists():
                # Last resort: generate without biome constraint
                return self.encounter_generator.generate_encounter(
                    party_level, party_size, difficulty
                )
        
        # Select theme from weighted options
        theme = self._select_theme_from_weights(weights, party_level)
        
        # Generate encounter from selected theme
        encounter = self.encounter_generator.generate_encounter(
            party_level=party_level,
            party_size=party_size,
            difficulty=difficulty,
            force_theme=theme.theme,
            allow_chaotic=False  # Biome encounters don't use chaos
        )
        
        # Update encounter with biome info
        encounter.biome = biome
        
        # Add narrative for anomalies
        if category == 'anomaly':
            # Get the weight object for narrative
            weight_obj = weights.filter(theme=theme.theme).first()
            if weight_obj and weight_obj.narrative_reason:
                encounter.narrative_justification = weight_obj.narrative_reason
            else:
                encounter.narrative_justification = (
                    f"{theme.theme.name} is rarely found in {biome} environments"
                )
        
        encounter.save()
        return encounter
    
    def _roll_category(self):
        """Roll for category using distribution percentages"""
        roll = random.random()
        cumulative = 0
        
        for category, probability in self.DISTRIBUTION.items():
            cumulative += probability
            if roll <= cumulative:
                return category
        
        return 'endemic'  # Fallback
    
    def _select_theme_from_weights(self, weights, party_level):
        """Select theme from weighted biome options"""
        
        # Filter by party level if possible
        level_appropriate = weights.filter(
            theme__min_cr__lte=party_level,
            theme__max_cr__gte=party_level
        )
        
        if level_appropriate.exists():
            weights = level_appropriate
        
        # Weighted random selection
        weight_list = list(weights)
        if not weight_list:
            # Should never happen, but handle gracefully
            return weights.first()
        
        theme_weights = [w.weight for w in weight_list]
        selected = random.choices(weight_list, weights=theme_weights, k=1)[0]
        
        return selected
    
    def get_distribution_stats(self, biome, num_samples=1000):
        """
        Generate statistics to verify 60/20/15/5 distribution
        
        Used for testing purposes
        
        Args:
            biome: Biome to test
            num_samples: Number of encounters to generate
            
        Returns:
            Dict with category counts
        """
        stats = {
            'endemic': 0,
            'adapted': 0,
            'traveler': 0,
            'anomaly': 0
        }
        
        for _ in range(num_samples):
            category = self._roll_category()
            stats[category] += 1
        
        # Convert to percentages
        return {
            category: (count / num_samples) * 100
            for category, count in stats.items()
        }
