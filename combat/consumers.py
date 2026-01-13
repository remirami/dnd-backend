"""
WebSocket consumer for real-time combat updates.

Allows clients to connect to a combat session and receive live updates
when actions occur (attacks, damage, healing, turn progression, etc.)
"""
import json
import logging

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False
    # Fallback class if channels not installed
    class AsyncWebsocketConsumer:
        pass

logger = logging.getLogger('combat')


class CombatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for combat sessions.
    
    URL: ws://localhost:8000/ws/combat/<combat_id>/
    
    Clients can connect to this WebSocket to receive real-time updates
    about combat actions, damage, healing, turn changes, etc.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.combat_id = self.scope['url_route']['kwargs']['combat_id']
        self.combat_group_name = f'combat_{self.combat_id}'
        
        # Join combat group
        await self.channel_layer.group_add(
            self.combat_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected to combat {self.combat_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave combat group
        await self.channel_layer.group_discard(
            self.combat_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected from combat {self.combat_id}")
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket client.
        
        This consumer is primarily for broadcasting server-side events,
        so we don't expect many client messages. But we can handle simple
        commands if needed.
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'ping':
                # Respond to ping
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            else:
                logger.warning(f"Unknown action received: {action}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
    
    # Event handlers for different combat events
    
    async def combat_action(self, event):
        """
        Handle combat action event (attack, spell, etc.)
        
        Event structure:
        {
            'type': 'combat.action',
            'action_type': 'attack'|'spell'|'heal'|etc,
            'actor': 'Character name',
            'target': 'Target name' (optional),
            'result': {...},
            'message': 'Readable description'
        }
        """
        await self.send(text_data=json.dumps({
            'type': 'combat_action',
            'action_type': event['action_type'],
            'actor': event.get('actor'),
            'target': event.get('target'),
            'result': event.get('result'),
            'message': event.get('message'),
            'timestamp': event.get('timestamp')
        }))
    
    async def combat_damage(self, event):
        """Handle damage event"""
        await self.send(text_data=json.dumps({
            'type': 'combat_damage',
            'target': event['target'],
            'damage': event['damage'],
            'damage_type': event.get('damage_type'),
            'new_hp': event.get('new_hp'),
            'message': event.get('message')
        }))
    
    async def combat_healing(self, event):
        """Handle healing event"""
        await self.send(text_data=json.dumps({
            'type': 'combat_healing',
            'target': event['target'],
            'healing': event['healing'],
            'new_hp': event.get('new_hp'),
            'message': event.get('message')
        }))
    
    async def combat_turn(self, event):
        """Handle turn change event"""
        await self.send(text_data=json.dumps({
            'type': 'combat_turn',
            'round': event['round'],
            'current_turn': event['current_turn'],
            'message': event.get('message')
        }))
    
    async def combat_status(self, event):
        """Handle status/condition change"""
        await self.send(text_data=json.dumps({
            'type': 'combat_status',
            'target': event['target'],
            'status': event['status'],
            'added': event.get('added', True),
            'message': event.get('message')
        }))
    
    async def combat_update(self, event):
        """Generic combat update"""
        await self.send(text_data=json.dumps({
            'type': 'combat_update',
            'update_type': event.get('update_type'),
            'data': event.get('data'),
            'message': event.get('message')
        }))
