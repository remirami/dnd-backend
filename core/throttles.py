"""
Custom throttle classes for DRF API rate limiting.

Provides specialized throttling for different API endpoints and operations.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """
    Throttle for burst protection - prevents rapid-fire abuse.
    
    Rate: 60 requests per minute
    Scope: 'burst'
    
    Use this to prevent users from hammering the API with rapid requests.
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle for sustained usage limits - daily cap.
    
    Rate: 1000 requests per day
    Scope: 'sustained'
    
    Use this to prevent excessive daily usage.
    """
    scope = 'sustained'


class CombatActionThrottle(UserRateThrottle):
    """
    Throttle for combat actions.
    
    Rate: 300 requests per minute (5 per second)
    Scope: 'combat'
    
    Combat actions are time-sensitive but shouldn't be spammed.
    Allows for interactive combat (1 action every 0.2 seconds if needed)
    but prevents abuse.
    """
    scope = 'combat'


class SpellLookupThrottle(UserRateThrottle):
    """
    Throttle for spell lookups and filtering.
    
    Rate: 200 requests per hour
    Scope: 'spells'
    
    Spell data is relatively static and cached, so we can be more restrictive.
    """
    scope = 'spells'


class CharacterOperationThrottle(UserRateThrottle):
    """
    Throttle for character creation and modifications.
    
    Rate: 500 requests per hour
    Scope: 'character'
    
    Character operations are important but shouldn't happen too frequently.
    """
    scope = 'character'


class CampaignOperationThrottle(UserRateThrottle):
    """
    Throttle for campaign operations.
    
    Rate: 200 requests per hour
    Scope: 'campaign'
    
    Campaign management operations are relatively infrequent.
    """
    scope = 'campaign'


class AnonymousStrictThrottle(AnonRateThrottle):
    """
    Stricter throttling for anonymous users.
    
    Rate: Inherits from DEFAULT_THROTTLE_RATES['anon']
    
    Use this for public endpoints that should be rate-limited more strictly.
    """
    pass


class NoThrottle:
    """
    Dummy throttle class that allows all requests.
    
    Use this to explicitly disable throttling on specific endpoints
    (e.g., health checks, status endpoints).
    """
    def allow_request(self, request, view):
        return True
    
    def wait(self):
        return None
