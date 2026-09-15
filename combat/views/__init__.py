"""
Combat Views Package

This package contains all ViewSets for the combat app, split into domain-specific modules.

All ViewSets are re-exported here for backwards compatibility.
Usage:
    from combat.views import CombatSessionViewSet, CombatParticipantViewSet, ...
"""

# Import the main composed viewset
from .log_views import CombatActionViewSet, CombatLogViewSet

# Import standalone viewsets
from .participant_views import CombatParticipantViewSet
from .session_views import CombatSessionViewSet

# Export all for backwards compatibility
__all__ = [
    'CombatActionViewSet',
    'CombatLogViewSet',
    'CombatParticipantViewSet',
    'CombatSessionViewSet',
]
