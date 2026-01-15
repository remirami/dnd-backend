"""
Encounter Generator Service

Generates themed encounters with 95% thematic coherence / 5% chaotic mix
"""
import random
from django.db.models import Q

from encounters.models import (
    Encounter, EncounterEnemy, EncounterTheme,
    EnemyThemeAssociation, ThemeIncompatibility
)


class EncounterGenerator:
    """Generate thematically cohesive or chaotic encounters"""
    
    CHAOS_THRESHOLD = 0.05  # 5% chance of chaotic encounter
    
    # XP thresholds per party level (D&D 5e standard)
    XP_THRESHOLDS = {
        1: {'easy': 25, 'medium': 50, 'hard': 75, 'deadly': 100},
        2: {'easy': 50, 'medium': 100, 'hard': 150, 'deadly': 200},
        3: {'easy': 75, 'medium': 150, 'hard': 225, 'deadly': 400},
        4: {'easy': 125, 'medium': 250, 'hard': 375, 'deadly': 500},
        5: {'easy': 250, 'medium': 500, 'hard': 750, 'deadly': 1100},
        6: {'easy': 300, 'medium': 600, 'hard': 900, 'deadly': 1400},
        7: {'easy': 350, 'medium': 750, 'hard': 1100, 'deadly': 1700},
        8: {'easy': 450, 'medium': 900, 'hard': 1400, 'deadly': 2100},
        9: {'easy': 550, 'medium': 1100, 'hard': 1600, 'deadly': 2400},
        10: {'easy': 600, 'medium': 1200, 'hard': 1900, 'deadly': 2800},
        11: {'easy': 800, 'medium': 1600, 'hard': 2400, 'deadly': 3600},
        12: {'easy': 1000, 'medium': 2000, 'hard': 3000, 'deadly': 4500},
        13: {'easy': 1100, 'medium': 2200, 'hard': 3400, 'deadly': 5100},
        14: {'easy': 1250, 'medium': 2500, 'hard': 3800, 'deadly': 5700},
        15: {'easy': 1400, 'medium': 2800, 'hard': 4300, 'deadly': 6400},
        16: {'easy': 1600, 'medium': 3200, 'hard': 4800, 'deadly': 7200},
        17: {'easy': 2000, 'medium': 3900, 'hard': 5900, 'deadly': 8800},
        18: {'easy': 2100, 'medium': 4200, 'hard': 6300, 'deadly': 9500},
        19: {'easy': 2400, 'medium': 4900, 'hard': 7300, 'deadly': 10900},
        20: {'easy': 2800, 'medium': 5700, 'hard': 8500, 'deadly': 12700},
    }
    
    def generate_encounter(self, party_level, party_size, 
                          difficulty='medium', force_theme=None,
                          allow_chaotic=True):
        """
        Generate an encounter for the party
        
        Args:
            party_level: Average party level (1-20)
            party_size: Number of players
            difficulty: 'easy', 'medium', 'hard', or 'deadly'
            force_theme: Optional EncounterTheme to use
            allow_chaotic: Allow chaotic encounters (default True)
            
        Returns:
            Encounter object with enemies
        """
        # Roll for chaos (if allowed and no forced theme)
        is_chaotic = (
            allow_chaotic and 
            not force_theme and 
            random.random() < self.CHAOS_THRESHOLD
        )
        
        if is_chaotic:
            return self._generate_chaotic_encounter(
                party_level, party_size, difficulty
            )
        
        # Normal themed encounter
        return self._generate_themed_encounter(
            party_level, party_size, difficulty, force_theme
        )
    
    def _generate_themed_encounter(self, party_level, party_size,
                                   difficulty, force_theme):
        """Generate normal cohesive encounter from single theme"""
        
        # Calculate XP budget
        xp_budget = self._calculate_xp_budget(party_level, party_size, difficulty)
        
        # Select theme
        if force_theme:
            theme = force_theme
        else:
            theme = self._select_theme(party_level)
        
        # Create encounter
        encounter = Encounter.objects.create(
            name=f"{theme.name} - Level {party_level}",
            description=theme.flavor_text,
            theme=theme,
            is_chaotic=False
        )
        
        # Select enemies from theme
        self._add_enemies_from_theme(encounter, theme, xp_budget, party_level)
        
        return encounter
    
    def _generate_chaotic_encounter(self, party_level, party_size, difficulty):
        """Generate rare chaotic encounter with mixed themes"""
        
        xp_budget = self._calculate_xp_budget(party_level, party_size, difficulty)
        
        # Select 2-3 incompatible themes
        num_themes = random.randint(2, 3)
        themes = self._select_incompatible_themes(num_themes, party_level)
        
        # Create chaotic encounter
        encounter = Encounter.objects.create(
            name=f"Chaotic Encounter - Level {party_level}",
            description=self._generate_chaos_narrative(themes),
            is_chaotic=True,
            narrative_justification=self._generate_chaos_narrative(themes)
        )
        
        # Split XP budget among themes
        remaining_budget = xp_budget
        for i, theme in enumerate(themes):
            # Allocate portion of budget
            theme_budget = remaining_budget // (len(themes) - i)
            
            self._add_enemies_from_theme(
                encounter, theme, theme_budget, party_level
            )
            
            remaining_budget -= theme_budget
        
        return encounter
    
    def _select_theme(self, party_level):
        """Select theme appropriate for party level"""
        
        # Filter themes by CR range
        themes = EncounterTheme.objects.filter(
            min_cr__lte=party_level,
            max_cr__gte=party_level
        )
        
        if not themes.exists():
            # Fallback: get any theme
            themes = EncounterTheme.objects.all()
        
        # Weighted random selection
        theme_list = list(themes)
        weights = [t.weight for t in theme_list]
        
        return random.choices(theme_list, weights=weights, k=1)[0]
    
    def _select_incompatible_themes(self, num_themes, party_level):
        """Select multiple incompatible themes"""
        
        # Get themes suitable for level
        suitable_themes = list(EncounterTheme.objects.filter(
            min_cr__lte=party_level,
            max_cr__gte=party_level
        ))
        
        if len(suitable_themes) < num_themes:
            suitable_themes = list(EncounterTheme.objects.all())
        
        # Randomly select themes
        selected = random.sample(suitable_themes, k=min(num_themes, len(suitable_themes)))
        
        return selected
    
    def _add_enemies_from_theme(self, encounter, theme, xp_budget, party_level):
        """Add enemies from theme to encounter within XP budget"""
        
        # Get enemy associations for this theme
        associations = theme.enemy_associations.all()
        
        if not associations.exists():
            return  # No enemies defined for theme yet
        
        # Separate by role
        leaders = list(associations.filter(role='leader'))
        primaries = list(associations.filter(role='primary'))
        elites = list(associations.filter(role='elite'))
        supports = list(associations.filter(role='support'))
        
        remaining_xp = xp_budget
        
        # Add 1 leader (if exists)
        if leaders and remaining_xp > 0:
            leader_assoc = random.choice(leaders)
            count = random.randint(1, 1)  # Usually 1 leader
            xp_used = self._add_enemy_to_encounter(
                encounter, leader_assoc.enemy, count
            )
            remaining_xp -= xp_used
        
        # Add 1-2 primary/elite enemies
        heavy_hitters = (primaries if primaries else []) + (elites if elites else [])
        if heavy_hitters and remaining_xp > xp_budget * 0.3:
            assoc = random.choice(heavy_hitters)
            count = random.randint(1, 2)
            xp_used = self._add_enemy_to_encounter(
                encounter, assoc.enemy, count
            )
            remaining_xp -= xp_used
        
        # Fill rest with support enemies
        if supports:
            while remaining_xp > xp_budget * 0.1:  # Keep adding until < 10% budget
                assoc = random.choice(supports)
                count = random.randint(assoc.min_count, assoc.max_count)
                xp_used = self._add_enemy_to_encounter(
                    encounter, assoc.enemy, count
                )
                remaining_xp -= xp_used
                
                if xp_used == 0:  # Prevent infinite loop
                    break
    
    def _add_enemy_to_encounter(self, encounter, enemy, count):
        """Add enemy instance to encounter and return XP"""
        
        # Get enemy HP
        if hasattr(enemy, 'stats') and enemy.stats:
            hp = enemy.stats.hit_points
        else:
            hp = getattr(enemy, 'hp', 10)  # Default 10
        
        # Create enemy instance
        for i in range(count):
            EncounterEnemy.objects.create(
                encounter=encounter,
                enemy=enemy,
                name=f"{enemy.name} {i+1}" if count > 1 else enemy.name,
                current_hp=hp
            )
        
        # Estimate XP (simplified - in real D&D this is complex)
        cr = self._cr_to_float(enemy.challenge_rating)
        xp_per_enemy = self._cr_to_xp(cr)
        
        return xp_per_enemy * count
    
    def _calculate_xp_budget(self, party_level, party_size, difficulty):
        """Calculate XP budget for encounter"""
        
        # Clamp level to valid range
        level = max(1, min(20, party_level))
        
        # Get XP threshold
        threshold = self.XP_THRESHOLDS.get(level, self.XP_THRESHOLDS[5])
        xp_per_player = threshold.get(difficulty, threshold['medium'])
        
        return xp_per_player * party_size
    
    def _cr_to_float(self, cr_string):
        """Convert CR string to float (e.g., '1/4' -> 0.25)"""
        if '/' in str(cr_string):
            num, denom = str(cr_string).split('/')
            return float(num) / float(denom)
        return float(cr_string)
    
    def _cr_to_xp(self, cr):
        """Convert CR to XP (D&D 5e standard)"""
        CR_XP_MAP = {
            0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
            1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
            6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
            11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
            16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000,
        }
        
        # Find closest CR
        closest_cr = min(CR_XP_MAP.keys(), key=lambda x: abs(x - cr))
        return CR_XP_MAP[closest_cr]
    
    def _generate_chaos_narrative(self, themes):
        """Generate story reason for chaotic mix"""
        if not themes or len(themes) == 0:
            return "A mysterious force brought these unlikely foes together"
        
        theme_names = ', '.join(t.name for t in themes)
        
        narratives = [
            f"A strange magical accident brought these unlikely foes together: {theme_names}",
            f"An ancient curse binds these natural enemies",
            "A mad wizard's experiment forced these foes into uneasy cooperation",
            "A planar convergence created this bizarre alliance",
            "Desperate circumstances forced unusual cooperation between natural enemies",
            f"A powerful artifact's influence corrupted the area, drawing in {theme_names}",
        ]
        return random.choice(narratives)
