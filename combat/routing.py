"""
WebSocket URL routing for combat module.

Maps WebSocket URLs to consumers.
"""
try:
    from django.urls import re_path
    from . import consumers
    
    websocket_urlpatterns = [
        re_path(r'ws/combat/(?P<combat_id>\w+)/$', consumers.CombatConsumer.as_asgi()),
    ]
except ImportError:
    # Channels not installed
    websocket_urlpatterns = []
