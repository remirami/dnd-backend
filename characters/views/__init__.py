"""
Characters Views Package

This package contains all ViewSets for the characters app, split into domain-specific modules.

All ViewSets are re-exported here for backwards compatibility.
Usage:
    from characters.views import CharacterViewSet, CharacterClassViewSet, ...
"""

# Import from reference views (Classes, Races, Backgrounds, etc.)
from .reference_views import (
    CharacterClassViewSet,
    CharacterRaceViewSet,
    CharacterBackgroundViewSet,
    CharacterStatsViewSet,
    CharacterProficiencyViewSet,
    CharacterFeatureViewSet,
    CharacterSpellViewSet,
    CharacterResistanceViewSet,
)

# Import the main CharacterViewSet
from .character_views import CharacterViewSet

# Export all for backwards compatibility
__all__ = [
    'CharacterViewSet',
    'CharacterClassViewSet',
    'CharacterRaceViewSet',
    'CharacterBackgroundViewSet',
    'CharacterStatsViewSet',
    'CharacterProficiencyViewSet',
    'CharacterFeatureViewSet',
    'CharacterSpellViewSet',
    'CharacterResistanceViewSet',
]
