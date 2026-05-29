"""
Participant Views - CombatParticipantViewSet.

Contains the full CombatParticipantViewSet with damage, heal, move,
hazard, condition, and concentration endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import logging

from combat.models import (
    CombatParticipant, CombatAction, ConditionApplication,
    EnvironmentalEffect, ParticipantPosition
)
from combat.environmental_effects import calculate_movement_cost
from combat.serializers import CombatParticipantSerializer, ParticipantPositionSerializer
from combat.utils import roll_d20, calculate_damage, calculate_saving_throw

logger = logging.getLogger('combat')


class CombatParticipantViewSet(viewsets.ModelViewSet):
    """API endpoint for managing combat participants"""
    queryset = CombatParticipant.objects.all()
    serializer_class = CombatParticipantSerializer
    
    @action(detail=True, methods=['post'])
    def damage(self, request, pk=None):
        """Apply damage to a participant"""
        participant = self.get_object()
        amount = int(request.data.get('amount', 0))
        source_id = request.data.get('source_id')
        damage_type = request.data.get('damage_type')
        
        if amount <= 0:
            return Response(
                {"error": "Damage amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_hp, concentration_broken = participant.take_damage(amount)
        
        # Create combat action log
        session = participant.combat_session
        actor = None
        if source_id:
            try:
                actor = session.participants.get(pk=source_id)
            except CombatParticipant.DoesNotExist:
                pass
        
        CombatAction.objects.create(
            combat_session=session,
            actor=actor,
            target=participant,
            action_type='attack',  # Use 'attack' type for damage visualization
            attack_name='Manual Damage',
            damage_amount=amount,
            damage_type=None,  # Need to handle damage type object lookup if provided
            hit=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"Manual damage applied: {amount} damage"
        )
        
        serializer = self.get_serializer(participant)
        response_data = {
            "message": f"{participant.get_name()} took {amount} damage",
            "current_hp": new_hp,
            "participant": serializer.data
        }
        if concentration_broken:
            response_data["concentration_broken"] = True
            response_data["concentration_message"] = f"Lost concentration on {participant.concentration_spell}"
        return Response(response_data)
    
    @action(detail=True, methods=['post'])
    def heal(self, request, pk=None):
        """Heal a participant"""
        participant = self.get_object()
        amount = int(request.data.get('amount', 0))
        source_id = request.data.get('source_id')
        
        if amount <= 0:
            return Response(
                {"error": "Heal amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_hp = participant.heal(amount)
        
         # Create combat action log
        session = participant.combat_session
        actor = None
        if source_id:
            try:
                actor = session.participants.get(pk=source_id)
            except CombatParticipant.DoesNotExist:
                pass
                
        CombatAction.objects.create(
            combat_session=session,
            actor=actor,
            target=participant,
            action_type='other',  # Healing isn't a standard type yet, use 'other'
            attack_name='Manual Healing',
            damage_amount=amount, # Store healing amount in damage_amount positive? Or maybe negative?
            # Usually healing is separate, but for simple log we can put it in description
            hit=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"Manual healing applied: {amount} HP"
        )

        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} healed {amount} HP",
            "current_hp": new_hp,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Move a participant, considering difficult terrain.
        
        Request body:
        {
            "distance": 30,  // Distance to move in feet
            "x": 10,  // Optional: new X position
            "y": 10,  // Optional: new Y position
            "z": 0   // Optional: new Z position
        }
        """
        participant = self.get_object()
        session = participant.combat_session
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distance = request.data.get('distance', 0)
        x = request.data.get('x')
        y = request.data.get('y')
        z = request.data.get('z', 0)
        
        # Get participant's base speed
        base_speed = 30  # Default
        if participant.character and hasattr(participant.character, 'stats'):
            base_speed = participant.character.stats.speed or 30
        
        # Get current position
        try:
            position = participant.position
        except ParticipantPosition.DoesNotExist:
            position = ParticipantPosition.objects.create(
                participant=participant,
                x=x or 0,
                y=y or 0,
                z=z or 0
            )
        
        # Calculate movement cost considering terrain
        terrain_type = position.current_terrain
        weather_effect = EnvironmentalEffect.objects.filter(
            combat_session=session,
            effect_type='weather',
            is_active=True
        ).first()
        weather = weather_effect.weather_type if weather_effect else None
        
        effective_movement, cost_multiplier = calculate_movement_cost(
            base_speed,
            terrain_type=terrain_type,
            weather=weather
        )
        
        # Calculate actual movement cost
        movement_cost = int(distance * cost_multiplier)
        
        # Check if participant has enough movement
        movement_remaining = effective_movement - participant.movement_used
        if movement_cost > movement_remaining:
            return Response(
                {"error": f"Not enough movement. Need {movement_cost} feet, have {movement_remaining} feet remaining"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update position if provided
        if x is not None and y is not None:
            position.x = x
            position.y = y
            position.z = z
            # Update environmental effects at new position
            # Import CombatEnvironmentMixin's helper via the composed viewset
            from combat.views.environment_views import CombatEnvironmentMixin
            mixin = CombatEnvironmentMixin()
            mixin._update_position_environmental_effects(position, session)
            position.save()
        
        # Update movement used
        participant.movement_used += movement_cost
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} moved {distance} feet (cost: {movement_cost} feet)",
            "movement_used": participant.movement_used,
            "movement_remaining": effective_movement - participant.movement_used,
            "terrain_multiplier": cost_multiplier,
            "position": ParticipantPositionSerializer(position).data if hasattr(position, 'id') else None,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def apply_hazard_damage(self, request, pk=None):
        """
        Apply damage from hazards at participant's position.
        Called automatically at start of turn if in hazard area.
        """
        participant = self.get_object()
        
        try:
            position = participant.position
        except ParticipantPosition.DoesNotExist:
            return Response(
                {"error": "Participant has no position"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not position.current_hazards:
            return Response(
                {"error": "Participant is not in any hazard area"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = participant.combat_session
        hazards_applied = []
        
        for hazard_type in position.current_hazards:
            from combat.environmental_effects import calculate_hazard_damage
            damage_dice, damage_type_name, save_type, save_dc, condition = calculate_hazard_damage(hazard_type)
            
            if not damage_dice:
                continue
            
            # Roll damage
            damage_amount, damage_breakdown = calculate_damage(damage_dice, 0, False)
            
            # Make saving throw if applicable
            if save_type and save_dc:
                save_roll, _ = roll_d20()
                ability_mod = participant.get_ability_modifier(save_type)
                proficiency_bonus = participant.character.proficiency_bonus if participant.character else 2
                save_total, _ = calculate_saving_throw(save_roll, ability_mod, proficiency_bonus, False)
                
                if save_total >= save_dc:
                    damage_amount = damage_amount // 2  # Half damage on successful save
            
            # Apply damage
            new_hp, _ = participant.take_damage(damage_amount)
            
            # Apply condition if applicable
            if condition:
                from bestiary.models import Condition
                try:
                    cond = Condition.objects.get(name=condition)
                    participant.conditions.add(cond)
                except Condition.DoesNotExist:
                    pass
            
            hazards_applied.append({
                'hazard_type': hazard_type,
                'damage': damage_amount,
                'damage_type': damage_type_name,
                'save_success': save_total >= save_dc if save_type else None,
            })
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} took damage from hazards",
            "hazards_applied": hazards_applied,
            "current_hp": participant.current_hp,
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def reset_turn(self, request, pk=None):
        """Reset turn resources for a participant"""
        participant = self.get_object()
        participant.reset_turn()
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()}'s turn reset",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_condition(self, request, pk=None):
        """Add a condition to a participant"""
        participant = self.get_object()
        condition_id = request.data.get('condition_id')
        
        if not condition_id:
            return Response(
                {"error": "Missing 'condition_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from bestiary.models import Condition
        try:
            condition = Condition.objects.get(pk=condition_id)
        except Condition.DoesNotExist:
            return Response(
                {"error": "Condition not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant.conditions.add(condition)
        
        # Create condition application record
        session = participant.combat_session
        ConditionApplication.objects.create(
            participant=participant,
            condition=condition,
            applied_round=session.current_round,
            applied_turn=session.current_turn_index,
            duration_type=request.data.get('duration_type', 'instant'),
            duration_rounds=request.data.get('duration_rounds', 0),
            expires_at_round=request.data.get('expires_at_round'),
            source_type=request.data.get('source_type', 'manual'),
            source_name=request.data.get('source_name', ''),
        )
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{condition.get_name_display()} added to {participant.get_name()}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def remove_condition(self, request, pk=None):
        """Remove a condition from a participant"""
        participant = self.get_object()
        condition_id = request.data.get('condition_id')
        
        if not condition_id:
            return Response(
                {"error": "Missing 'condition_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from bestiary.models import Condition
        try:
            condition = Condition.objects.get(pk=condition_id)
        except Condition.DoesNotExist:
            return Response(
                {"error": "Condition not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant.conditions.remove(condition)
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{condition.get_name_display()} removed from {participant.get_name()}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def start_concentration(self, request, pk=None):
        """Start concentrating on a spell"""
        participant = self.get_object()
        spell_name = request.data.get('spell_name', '')
        
        if not spell_name:
            return Response(
                {"error": "Missing 'spell_name'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if participant.is_concentrating:
            return Response(
                {"error": f"Already concentrating on {participant.concentration_spell}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.is_concentrating = True
        participant.concentration_spell = spell_name
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} starts concentrating on {spell_name}",
            "participant": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def end_concentration(self, request, pk=None):
        """End concentration"""
        participant = self.get_object()
        
        if not participant.is_concentrating:
            return Response(
                {"error": "Not concentrating on any spell"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_name = participant.concentration_spell
        participant.is_concentrating = False
        participant.concentration_spell = ""
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response({
            "message": f"{participant.get_name()} loses concentration on {spell_name}",
            "participant": serializer.data
        })
