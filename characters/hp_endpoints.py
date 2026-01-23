"""
HP Management endpoints for CharacterViewSet
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from characters.models import CharacterStats


def add_hp_endpoints(cls):
    """
    Decorator to add HP management endpoints to CharacterViewSet
    """
    
    @action(detail=True, methods=['post'])
    def update_hp(self, request, pk=None):
        """
        Update character HP (Heal, Damage, or Temp HP).
        
        Body:
        { 
            "action": "heal" | "damage" | "temp",
            "amount": <int>
        }
        """
        character = self.get_object()
        stats = character.stats
        
        action_type = request.data.get('action')
        try:
            amount = int(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Amount must be a number"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if amount < 0:
            return Response(
                {"error": "Amount must be non-negative"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action_type == 'heal':
            # Healing cannot exceed max HP
            # If at 0 HP, healing stabilizes (implicit in 5e)
            
            old_hp = stats.hit_points
            stats.hit_points = min(stats.hit_points + amount, stats.max_hit_points)
            stats.save()
            
            healed_amount = stats.hit_points - old_hp
            
            return Response({
                "message": f"Healed for {healed_amount} HP",
                "current_hp": stats.hit_points,
                "max_hp": stats.max_hit_points,
                "temp_hp": stats.temporary_hit_points
            })

        elif action_type == 'damage':
            damage_remaining = amount
            
            # 1. Absorb with Temp HP first
            if stats.temporary_hit_points > 0:
                absorbed = min(stats.temporary_hit_points, damage_remaining)
                stats.temporary_hit_points -= absorbed
                damage_remaining -= absorbed
            
            # 2. Apply remaining damage to regular HP
            if damage_remaining > 0:
                old_hp = stats.hit_points
                stats.hit_points = max(0, stats.hit_points - damage_remaining)
                
                # Check for death/unconsciousness (simplified)
                if old_hp > 0 and stats.hit_points == 0:
                    status_msg = "Character is now unconscious!"
                else:
                    status_msg = f"Took {amount} damage"
            else:
                status_msg = f"Absorbed {amount} damage with temporary HP"

            stats.save()
            
            return Response({
                "message": status_msg,
                "current_hp": stats.hit_points,
                "max_hp": stats.max_hit_points,
                "temp_hp": stats.temporary_hit_points
            })

        elif action_type == 'temp':
            # 5e Rule: Temp HP doesn't stack. You decide whether to keep current or take new.
            # We'll assume taking new if higher, or if forcing (not implemented yet, simple replacement logic usually fine for API)
            
            # Let's implement "Take Higher" by default as per RAW
            old_temp = stats.temporary_hit_points
            
            if amount > old_temp:
                stats.temporary_hit_points = amount
                stats.save()
                msg = f"Gained {amount} Temporary HP"
            else:
                 msg = f"Current Temporary HP ({old_temp}) is higher than new amount ({amount}). No change."

            return Response({
                "message": msg,
                "current_hp": stats.hit_points,
                "max_hp": stats.max_hit_points,
                "temp_hp": stats.temporary_hit_points
            })
            
        else:
            return Response(
                {"error": "Invalid action. Must be 'heal', 'damage', or 'temp'"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Add methods to class
    cls.update_hp = update_hp
    
    return cls
