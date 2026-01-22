"""
Character Builder Service - Validators and Calculators

Handles ability score validation and racial bonus calculations
"""


class AbilityScoreValidator:
    """Validates ability scores based on different methods"""
    
    STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
    
    # Point buy costs (score: cost)
    POINT_BUY_COSTS = {
        8: 0,
        9: 1,
        10: 2,
        11: 3,
        12: 4,
        13: 5,
        14: 7,
        15: 9
    }
    
    POINT_BUY_BUDGET = 27
    
    @classmethod
    def validate_standard_array(cls, scores):
        """
        Validate that scores match standard array exactly
        
        Args:
            scores: dict like {"str": 15, "dex": 14, ...}
            
        Returns:
            (bool, str): (is_valid, error_message)
        """
        if not isinstance(scores, dict):
            return False, "Scores must be a dictionary"
        
        # Check we have all 6 abilities
        required = {'str', 'dex', 'con', 'int', 'wis', 'cha'}
        if set(scores.keys()) != required:
            return False, f"Must provide all 6 ability scores: {required}"
        
        # Get sorted values
        values = sorted(scores.values())
        expected = sorted(cls.STANDARD_ARRAY)
        
        if values != expected:
            return False, f"Scores must use standard array: {cls.STANDARD_ARRAY}"
        
        return True, ""
    
    @classmethod
    def validate_point_buy(cls, scores):
        """
        Validate point buy allocation
        
        Args:
            scores: dict like {"str": 15, "dex": 14, ...}
            
        Returns:
            (bool, str, int): (is_valid, error_message, points_used)
        """
        if not isinstance(scores, dict):
            return False, "Scores must be a dictionary", 0
        
        # Check we have all 6 abilities
        required = {'str', 'dex', 'con', 'int', 'wis', 'cha'}
        if set(scores.keys()) != required:
            return False, f"Must provide all 6 ability scores", 0
        
        # Calculate cost
        points_used = 0
        for ability, score in scores.items():
            if score < 8 or score > 15:
                return False, f"{ability.upper()} score {score} out of range (8-15)", 0
            
            points_used += cls.POINT_BUY_COSTS[score]
        
        if points_used > cls.POINT_BUY_BUDGET:
            return False, f"Point buy budget exceeded: {points_used}/{cls.POINT_BUY_BUDGET}", points_used
        
        if points_used < cls.POINT_BUY_BUDGET:
            return False, f"Must use all {cls.POINT_BUY_BUDGET} points (used {points_used})", points_used
        
        return True, "", points_used
    
    @classmethod
    def validate_manual(cls, scores):
        """
        Validate manually entered scores (DM discretion)
        
        Args:
            scores: dict like {"str": 15, "dex": 14, ...}
            
        Returns:
            (bool, str, list): (is_valid, error_message, warnings)
        """
        if not isinstance(scores, dict):
            return False, "Scores must be a dictionary", []
        
        # Check we have all 6 abilities
        required = {'str', 'dex', 'con', 'int', 'wis', 'cha'}
        if set(scores.keys()) != required:
            return False, f"Must provide all 6 ability scores", []
        
        warnings = []
        
        # Check range (3-18 is normal)
        for ability, score in scores.items():
            if score < 3:
                return False, f"{ability.upper()} score {score} is too low (minimum 3)", warnings
            
            if score > 20:
                return False, f"{ability.upper()} score {score} is too high (maximum 20)", warnings
            
            # Warnings for unusual values
            if score < 6:
                warnings.append(f"{ability.upper()} is very low ({score})")
            
            if score > 17:
                warnings.append(f"{ability.upper()} is very high ({score})")
        
        return True, "", warnings


class RacialBonusCalculator:
    """Calculates final ability scores after racial bonuses"""
    
    @classmethod
    def parse_bonuses(cls, race):
        """
        Parse ability score increases from race model
        
        Args:
            race: CharacterRace object
            
        Returns:
            dict: {"str": 1, "dex": 2} etc
        """
        bonuses = {}
        if not race or not race.ability_score_increases:
             return bonuses
             
        # Format is "STR+1,DEX+1"
        try:
            parts = race.ability_score_increases.split(',')
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                # Extract ability and amount (e.g. STR+2 or STR-1)
                ability_code = part[:3].lower()
                amount = int(part[3:])
                
                if ability_code in ['str', 'dex', 'con', 'int', 'wis', 'cha']:
                    bonuses[ability_code] = amount
        except (ValueError, IndexError):
            pass
            
        return bonuses

    @classmethod
    def apply_bonuses(cls, base_scores, race):
        """
        Apply racial bonuses to base scores
        
        Args:
            base_scores: dict like {"str": 15, "dex": 14, ...}
            race: CharacterRace object
            
        Returns:
            dict: Final scores with bonuses applied
        """
        bonuses = cls.parse_bonuses(race)
        final_scores = base_scores.copy()
        
        for ability, bonus in bonuses.items():
            if ability in final_scores:
                final_scores[ability] += bonus
        
        return final_scores
    
    @classmethod
    def get_bonuses(cls, race):
        """Get racial bonuses for a race"""
        return cls.parse_bonuses(race)


class MulticlassPrerequisiteChecker:
    """Checks multiclass ability score prerequisites"""
    
    MULTICLASS_REQUIREMENTS = {
        'barbarian': {'str': 13},
        'bard': {'cha': 13},
        'cleric': {'wis': 13},
        'druid': {'wis': 13},
        'fighter': {'str': 13, 'dex': 13},  # STR OR DEX (whichever is primary)
        'monk': {'dex': 13, 'wis': 13},
        'paladin': {'str': 13, 'cha': 13},
        'ranger': {'dex': 13, 'wis': 13},
        'rogue': {'dex': 13},
        'sorcerer': {'cha': 13},
        'warlock': {'cha': 13},
        'wizard': {'int': 13}
    }
    
    @classmethod
    def can_multiclass_into(cls, class_name, ability_scores):
        """
        Check if character can multiclass into a class
        
        Args:
            class_name: Name of class to multiclass into
            ability_scores: dict like {"str": 15, "dex": 14, ...}
            
        Returns:
            (bool, str): (can_multiclass, reason)
        """
        if class_name not in cls.MULTICLASS_REQUIREMENTS:
            return True, ""  # No requirements
        
        requirements = cls.MULTICLASS_REQUIREMENTS[class_name]
        
        # Special case: Fighter (STR OR DEX)
        if class_name == 'fighter':
            str_score = ability_scores.get('str', 0)
            dex_score = ability_scores.get('dex', 0)
            
            if str_score >= 13 or dex_score >= 13:
                return True, ""
            
            return False, "Fighter requires Strength 13 OR Dexterity 13"
        
        # Standard check: all requirements must be met
        for ability, required_score in requirements.items():
            actual_score = ability_scores.get(ability, 0)
            
            if actual_score < required_score:
                ability_name = ability.upper()
                return False, f"{class_name.title()} requires {ability_name} {required_score}"
        
        return True, ""


def calculate_ability_modifier(score):
    """Calculate D&D ability modifier from score"""
    return (score - 10) // 2


def calculate_modifiers(ability_scores):
    """Calculate all ability modifiers"""
    return {
        ability: calculate_ability_modifier(score)
        for ability, score in ability_scores.items()
    }
