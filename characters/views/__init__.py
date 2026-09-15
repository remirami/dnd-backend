"""
Characters Views Package

This package contains all ViewSets for the characters app, split into domain-specific modules.

All ViewSets are re-exported here for backwards compatibility.
Usage:
    from characters.views import CharacterViewSet, CharacterClassViewSet, ...
"""

# Import from reference views (Classes, Races, Backgrounds, etc.)
# Import the main CharacterViewSet
from .character_views import CharacterViewSet
from .reference_views import (
    CharacterBackgroundViewSet,
    CharacterClassViewSet,
    CharacterFeatureViewSet,
    CharacterProficiencyViewSet,
    CharacterRaceViewSet,
    CharacterResistanceViewSet,
    CharacterSpellViewSet,
    CharacterStatsViewSet,
)

# Export all for backwards compatibility
__all__ = [
    'CharacterBackgroundViewSet',
    'CharacterClassViewSet',
    'CharacterFeatureViewSet',
    'CharacterProficiencyViewSet',
    'CharacterRaceViewSet',
    'CharacterResistanceViewSet',
    'CharacterSpellViewSet',
    'CharacterStatsViewSet',
    'CharacterViewSet',
]
