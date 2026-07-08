"""
Practice Views - Practice mode, AI turns, and export.

Contains the CombatPracticeMixin with practice_mode, export, ai_turn,
and auto_enemy_turns actions.
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging

from combat.models import CombatSession, CombatParticipant
from characters.models import Character

logger = logging.getLogger('combat')


class CombatPracticeMixin:
    """Mixin providing practice mode, AI, and export actions."""

    @action(detail=False, methods=['post'])
    def practice_mode(self, request):
        """
        Create a practice combat session quickly.
        
        Request body:
        {
            "name": "Practice Combat",  // Optional name
            "character_ids": [1, 2, 3],  // List of character IDs
            "enemies": [  // List of enemies
                {"enemy_id": 1, "name": "Goblin 1", "hp": 7},
                {"enemy_id": 1, "name": "Goblin 2", "hp": 7}
            ]
        }
        """
        from bestiary.models import Enemy
        
        name = request.data.get('name', 'Practice Combat')
        character_ids = request.data.get('character_ids', [])
        enemies = request.data.get('enemies', [])
        
        # Create practice session
        session = CombatSession.objects.create(
            encounter=None,
            is_practice=True,
            status='preparing',
            notes=f"Practice session: {name}"
        )
        
        added_characters = []
        added_enemies = []
        
        # Add characters
        for char_id in character_ids:
            try:
                character = Character.objects.get(pk=char_id)
                if not hasattr(character, 'stats'):
                    continue
                
                stats = character.stats
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='character',
                    character=character,
                    initiative=0,
                    current_hp=stats.hit_points,
                    max_hp=stats.max_hit_points,
                    armor_class=stats.armor_class
                )
                session.participants.add(participant)
                added_characters.append({
                    'id': character.id,
                    'name': character.name,
                    'participant_id': participant.id
                })
            except Character.DoesNotExist:
                continue
        
        # Add enemies
        for enemy_data in enemies:
            enemy_id = enemy_data.get('enemy_id')
            enemy_name = enemy_data.get('name', 'Enemy')
            enemy_hp = enemy_data.get('hp')
            
            if not enemy_id:
                continue
            
            try:
                enemy = Enemy.objects.get(pk=enemy_id)
                if not hasattr(enemy, 'stats'):
                    continue
                
                hp = enemy_hp if enemy_hp is not None else enemy.stats.hit_points
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=None,
                    initiative=0,
                    current_hp=hp,
                    max_hp=enemy.stats.hit_points,
                    armor_class=enemy.stats.armor_class
                )
                session.participants.add(participant)
                added_enemies.append({
                    'id': enemy.id,
                    'name': enemy_name,
                    'participant_id': participant.id
                })
            except Enemy.DoesNotExist:
                continue
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"Practice combat session created: {name}",
            "session": serializer.data,
            "characters_added": added_characters,
            "enemies_added": added_enemies,
            "next_steps": [
                "1. Roll initiative: POST /api/combat/sessions/{id}/roll_initiative/",
                "2. Start combat: POST /api/combat/sessions/{id}/start/",
                "3. Make attacks: POST /api/combat/sessions/{id}/attack/"
            ]
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export combat log in various formats"""
        session = self.get_object()
        format_type = request.query_params.get('format', 'json').lower()
        
        if format_type == 'json':
            report = session.get_combat_report()
            return Response(report)
        
        elif format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            log = session.get_or_create_log()
            log.calculate_statistics()
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="combat_{session.id}.csv"'
            
            writer = csv.writer(response)
            # Write header
            writer.writerow(['Round', 'Turn', 'Timestamp', 'Actor', 'Action Type', 'Target', 'Hit', 'Damage', 'Critical'])
            
            # Write actions
            for action in session.actions.all().order_by('round_number', 'turn_number', 'created_at'):
                writer.writerow([
                    action.round_number,
                    action.turn_number,
                    action.created_at.isoformat(),
                    action.actor.get_name(),
                    action.get_action_type_display(),
                    action.target.get_name() if action.target else '',
                    'Yes' if action.hit else 'No' if action.hit is not None else '',
                    action.damage_amount or 0,
                    'Yes' if action.critical else 'No',
                ])
            
            return response
        
        else:
            return Response(
                {"error": f"Unsupported format: {format_type}. Supported: json, csv"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def ai_turn(self, request, pk=None):
        """
        Resolve the current enemy's turn using AI.
        The AI selects targets, executes attacks, then advances the turn.
        """
        from combat.combat_ai import resolve_enemy_turn
        
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current = session.get_current_participant()
        if not current:
            return Response(
                {"error": "No active participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if current.participant_type != 'enemy':
            return Response(
                {"error": f"It is {current.get_name()}'s turn (a player character). AI only controls enemies."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Resolve the enemy's turn
            actions = resolve_enemy_turn(session, current)
            
            # Advance to next turn
            next_participant = session.next_turn()
            
            serializer = self.get_serializer(session)
            return Response({
                "message": f"{current.get_name()}'s turn resolved by AI",
                "actor": current.get_name(),
                "actor_id": current.id,
                "actions": actions,
                "next_turn": next_participant.get_name() if next_participant else None,
                "session": serializer.data,
            })
        except Exception as e:
            logger.exception(f"AI turn error for {current.get_name()}: {e}")
            return Response(
                {"error": f"AI turn failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def auto_enemy_turns(self, request, pk=None):
        """
        Automatically resolve all consecutive enemy turns.
        Stops when it's a player character's turn or combat ends.
        """
        from combat.combat_ai import resolve_enemy_turn
        
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            all_actions = []
            turns_resolved = 0
            max_turns = 20  # Safety limit
            
            while turns_resolved < max_turns:
                current = session.get_current_participant()
                if not current:
                    break
                
                # Stop if it's a player's turn
                if current.participant_type != 'enemy':
                    break
                
                # Resolve this enemy's turn
                actions = resolve_enemy_turn(session, current)
                all_actions.append({
                    "actor": current.get_name(),
                    "actor_id": current.id,
                    "actions": actions,
                })
                turns_resolved += 1
                
                # Advance turn
                next_participant = session.next_turn()
                if not next_participant:
                    break
                
                # Check if all players are dead (combat should end)
                living_players = session.participants.filter(
                    participant_type='character',
                    is_active=True,
                    current_hp__gt=0,
                ).count()
                if living_players == 0:
                    break
            
            serializer = self.get_serializer(session)
            current = session.get_current_participant()
            
            return Response({
                "message": f"Resolved {turns_resolved} enemy turn(s)",
                "turns_resolved": turns_resolved,
                "enemy_turns": all_actions,
                "current_turn": current.get_name() if current else None,
                "session": serializer.data,
            })
        except Exception as e:
            logger.exception(f"Auto enemy turns error: {e}")
            return Response(
                {"error": f"Auto enemy turns failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
