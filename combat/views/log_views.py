"""
Log Views - CombatActionViewSet and CombatLogViewSet.

Read-only viewsets for combat action history and combat log analytics.
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from combat.models import CombatAction, CombatLog
from combat.serializers import CombatActionSerializer, CombatLogSerializer


class CombatActionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing combat actions (read-only)"""
    queryset = CombatAction.objects.all()
    serializer_class = CombatActionSerializer


class CombatLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing combat logs"""
    queryset = CombatLog.objects.all()
    serializer_class = CombatLogSerializer
    
    def get_queryset(self):
        queryset = CombatLog.objects.all()
        session_id = self.request.query_params.get('session', None)
        is_public = self.request.query_params.get('public', None)
        
        if session_id:
            queryset = queryset.filter(combat_session_id=session_id)
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get detailed analytics for a combat log"""
        log = self.get_object()
        log.calculate_statistics()
        
        # Calculate additional metrics
        analytics = {
            'log_id': log.id,
            'session_id': log.combat_session.id,
            'encounter_name': log.combat_session.encounter.name,
            'duration': {
                'seconds': log.duration_seconds,
                'formatted': log.combat_session._format_duration(log.duration_seconds),
                'rounds': log.total_rounds,
                'turns': log.total_turns,
                'average_turns_per_round': round(log.total_turns / log.total_rounds, 2) if log.total_rounds > 0 else 0,
            },
            'damage_analysis': {
                'total_dealt': log.total_damage_dealt,
                'total_received': log.total_damage_received,
                'net_damage': log.total_damage_dealt - log.total_damage_received,
                'by_type': log.damage_by_type,
                'average_per_turn': round(log.total_damage_dealt / log.total_turns, 2) if log.total_turns > 0 else 0,
            },
            'action_analysis': {
                'total_actions': log.total_turns,
                'by_type': log.actions_by_type,
                'most_common_action': max(log.actions_by_type.items(), key=lambda x: x[1])[0] if log.actions_by_type else None,
            },
            'spell_analysis': {
                'total_spells_cast': sum(log.spells_cast.values()),
                'spells_by_name': log.spells_cast,
                'most_used_spell': max(log.spells_cast.items(), key=lambda x: x[1])[0] if log.spells_cast else None,
            },
            'participant_performance': {
                pid: {
                    'name': stats['name'],
                    'damage_dealt': stats['damage_dealt'],
                    'damage_received': stats['damage_received'],
                    'attacks_made': stats['attacks_made'],
                    'hit_rate': round((stats['attacks_hit'] / stats['attacks_made'] * 100), 2) if stats['attacks_made'] > 0 else 0,
                    'critical_hit_rate': round((stats['critical_hits'] / stats['attacks_made'] * 100), 2) if stats['attacks_made'] > 0 else 0,
                    'hp_change': stats['end_hp'] - stats['start_hp'],
                    'status': stats['status'],
                }
                for pid, stats in log.participant_stats.items()
            },
            'outcomes': {
                'victors': len(log.victors),
                'casualties': len(log.casualties),
                'victor_names': [log.participant_stats.get(pid, {}).get('name', 'Unknown') for pid in log.victors],
                'casualty_names': [log.participant_stats.get(pid, {}).get('name', 'Unknown') for pid in log.casualties],
            },
        }
        
        return Response(analytics)
