"""
Validation and calculation services for characters.
"""
import re


class RacialBonusCalculator:
    """Calculates final ability scores after racial bonuses."""

    @classmethod
    def parse_bonuses(cls, race):
        """
        Parse ability score increases from race model or string.

        Args:
            race: CharacterRace object or string like "STR+2,DEX+1"

        Returns:
            dict: {"str": 1, "dex": 2} etc.
        """
        bonuses = {}
        if not race:
            return bonuses

        increases_str = ""
        if hasattr(race, 'ability_score_increases'):
            increases_str = race.ability_score_increases or ""
        elif isinstance(race, str):
            increases_str = race

        if not increases_str:
            return bonuses

        # Handles formats like "STR+2, DEX+1", "+2 str, +1 con", "STR+2,CON+1"
        parts = [p.strip() for p in increases_str.split(',') if p.strip()]
        for part in parts:
            part_lower = part.lower()
            ability_map = {
                'str': 'str',
                'dex': 'dex',
                'con': 'con',
                'int': 'int',
                'wis': 'wis',
                'cha': 'cha'
            }

            matched_ability = None
            for key in ability_map:
                if key in part_lower:
                    matched_ability = key
                    break

            if matched_ability:
                num_match = re.search(r'[+-]?\d+', part)
                if num_match:
                    bonuses[matched_ability] = int(num_match.group())

        return bonuses

    @classmethod
    def apply_bonuses(cls, base_scores, race):
        """
        Apply racial bonuses to base scores.

        Args:
            base_scores: dict like {"str": 15, "dex": 14, ...}
            race: CharacterRace object or string

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
        """Get racial bonuses for a race."""
        return cls.parse_bonuses(race)


class AbilityScoreValidator:
    """Validates ability scores."""

    STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

    @classmethod
    def validate_standard_array(cls, scores):
        """Validate standard array allocation."""
        if not isinstance(scores, dict):
            return False, "Scores must be a dictionary"

        required = {'str', 'dex', 'con', 'int', 'wis', 'cha'}
        if set(scores.keys()) != required:
            return False, f"Must provide all 6 ability scores: {required}"

        values = sorted(scores.values())
        expected = sorted(cls.STANDARD_ARRAY)

        if values != expected:
            return False, f"Scores must use standard array: {cls.STANDARD_ARRAY}"

        return True, ""


def calculate_ability_modifier(score):
    """Calculate D&D ability modifier from score."""
    return (score - 10) // 2


def calculate_modifiers(ability_scores):
    """Calculate all ability modifiers."""
    return {
        ability: calculate_ability_modifier(score)
        for ability, score in ability_scores.items()
    }
