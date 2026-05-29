"""
Environment Views - Environmental effects, positions, tactical delegations.

Contains the CombatEnvironmentMixin with environment, position, stats,
and tactical combat action endpoints.
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging

from combat.models import EnvironmentalEffect, ParticipantPosition, CombatParticipant
from combat.environmental_effects import get_environmental_effects_summary
from combat.serializers import (
    CombatLogSerializer, EnvironmentalEffectSerializer, ParticipantPositionSerializer,
)

logger = logging.getLogger('combat')


class CombatEnvironmentMixin:
    """Mixin providing environment, positioning, stats, report, and tactical delegation actions."""

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get combat statistics"""
        session = self.get_object()
        log = session.get_or_create_log()
        log.calculate_statistics()
        
        serializer = CombatLogSerializer(log)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Get comprehensive combat report"""
        session = self.get_object()
        report = session.get_combat_report()
        return Response(report)

    @action(detail=True, methods=['get', 'post'])
    def environmental_effects(self, request, pk=None):
        """
        Get or add environmental effects to combat session.
        
        GET: List all environmental effects
        POST: Add a new environmental effect
        """
        session = self.get_object()
        
        if request.method == 'GET':
            effects = EnvironmentalEffect.objects.filter(combat_session=session, is_active=True)
            serializer = EnvironmentalEffectSerializer(effects, many=True)
            
            # Get weather (applies to entire combat)
            weather_effect = effects.filter(effect_type='weather').first()
            weather = weather_effect.weather_type if weather_effect else None
            
            # Get summary
            summary = get_environmental_effects_summary(
                terrain=None,
                cover=None,
                lighting=None,
                weather=weather,
                hazards=None
            )
            
            return Response({
                'environmental_effects': serializer.data,
                'summary': summary
            })
        
        elif request.method == 'POST':
            # Create new environmental effect
            effect_type = request.data.get('effect_type')
            
            if not effect_type:
                return Response(
                    {"error": "effect_type is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            effect_data = {
                'combat_session': session.id,
                'effect_type': effect_type,
                'description': request.data.get('description', ''),
            }
            
            # Set type-specific fields
            if effect_type == 'terrain':
                effect_data['terrain_type'] = request.data.get('terrain_type')
            elif effect_type == 'cover':
                effect_data['cover_type'] = request.data.get('cover_type')
                effect_data['cover_area_x'] = request.data.get('cover_area_x')
                effect_data['cover_area_y'] = request.data.get('cover_area_y')
                effect_data['cover_area_radius'] = request.data.get('cover_area_radius')
            elif effect_type == 'lighting':
                effect_data['lighting_type'] = request.data.get('lighting_type')
                effect_data['lighting_area_x'] = request.data.get('lighting_area_x')
                effect_data['lighting_area_y'] = request.data.get('lighting_area_y')
                effect_data['lighting_area_radius'] = request.data.get('lighting_area_radius')
            elif effect_type == 'weather':
                effect_data['weather_type'] = request.data.get('weather_type')
            elif effect_type == 'hazard':
                effect_data['hazard_type'] = request.data.get('hazard_type')
                effect_data['hazard_area_x'] = request.data.get('hazard_area_x')
                effect_data['hazard_area_y'] = request.data.get('hazard_area_y')
                effect_data['hazard_area_radius'] = request.data.get('hazard_area_radius')
            
            serializer = EnvironmentalEffectSerializer(data=effect_data)
            if serializer.is_valid():
                effect = serializer.save()
                return Response({
                    "message": f"Environmental effect added: {effect.get_effect_type_display()}",
                    "effect": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_participant_position(self, request, pk=None):
        """Set or update participant position"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        x = request.data.get('x', 0)
        y = request.data.get('y', 0)
        z = request.data.get('z', 0)
        
        if not participant_id:
            return Response(
                {"error": "participant_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create position
        position, created = ParticipantPosition.objects.get_or_create(
            participant=participant,
            defaults={'x': x, 'y': y, 'z': z}
        )
        
        if not created:
            position.x = x
            position.y = y
            position.z = z
            position.save()
        
        # Update environmental effects at this position
        self._update_position_environmental_effects(position, session)
        
        serializer = ParticipantPositionSerializer(position)
        return Response({
            "message": f"Position updated for {participant.get_name()}",
            "position": serializer.data
        })

    def _update_position_environmental_effects(self, position, session):
        """Update environmental effects at participant's position"""
        # Check for terrain
        terrain_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='terrain',
            is_active=True
        )
        if terrain_effects.exists():
            position.current_terrain = terrain_effects.first().terrain_type
        
        # Check for cover
        cover_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='cover',
            is_active=True
        )
        for cover_effect in cover_effects:
            if cover_effect.cover_area_x and cover_effect.cover_area_y and cover_effect.cover_area_radius:
                if position.is_in_area(cover_effect.cover_area_x, cover_effect.cover_area_y, cover_effect.cover_area_radius):
                    position.current_cover = cover_effect.cover_type
                    break
        
        # Check for lighting
        lighting_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='lighting',
            is_active=True
        )
        for lighting_effect in lighting_effects:
            if lighting_effect.lighting_area_x and lighting_effect.lighting_area_y and lighting_effect.lighting_area_radius:
                if position.is_in_area(lighting_effect.lighting_area_x, lighting_effect.lighting_area_y, lighting_effect.lighting_area_radius):
                    position.current_lighting = lighting_effect.lighting_type
                    break
        
        # Check for hazards
        hazard_effects = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='hazard',
            is_active=True
        )
        hazards = []
        for hazard_effect in hazard_effects:
            if hazard_effect.hazard_area_x and hazard_effect.hazard_area_y and hazard_effect.hazard_area_radius:
                if position.is_in_area(hazard_effect.hazard_area_x, hazard_effect.hazard_area_y, hazard_effect.hazard_area_radius):
                    hazards.append(hazard_effect.hazard_type)
        position.current_hazards = hazards
        
        position.save()

    # --- Tactical combat delegations (to tactical_endpoints.py) ---

    @action(detail=True, methods=['post'])
    def cast_aoe_spell(self, request, pk=None):
        """Cast an area of effect spell hitting multiple targets."""
        from combat.tactical_endpoints import cast_aoe_spell_endpoint
        return cast_aoe_spell_endpoint(self, request, pk)

    @action(detail=True, methods=['post'])
    def grapple(self, request, pk=None):
        """Initiate a grapple."""
        from combat.tactical_endpoints import grapple_endpoint
        return grapple_endpoint(self, request, pk)

    @action(detail=True, methods=['post'])
    def escape_grapple(self, request, pk=None):
        """Attempt to escape a grapple."""
        from combat.tactical_endpoints import escape_grapple_endpoint
        return escape_grapple_endpoint(self, request, pk)

    @action(detail=True, methods=['post'])
    def set_cover(self, request, pk=None):
        """Set cover type for a participant."""
        from combat.tactical_endpoints import set_cover_endpoint
        return set_cover_endpoint(self, request, pk)
