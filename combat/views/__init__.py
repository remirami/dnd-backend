"""
Combat Views Package

This package contains all ViewSets for the combat app, split into domain-specific modules.

All ViewSets are re-exported here for backwards compatibility.
Usage:
    from combat.views import CombatSessionViewSet, CombatParticipantViewSet, ...
"""

# Import the main composed viewset
from .session_views import CombatSessionViewSet

# Import standalone viewsets
from .participant_views import CombatParticipantViewSet
from .log_views import CombatActionViewSet, CombatLogViewSet

# Export all for backwards compatibility
__all__ = [
    'CombatSessionViewSet',
    'CombatParticipantViewSet',
    'CombatActionViewSet',
    'CombatLogViewSet',
]
