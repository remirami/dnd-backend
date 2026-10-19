from rest_framework.decorators import action
from rest_framework.response import Response
from characters.rest_mechanics import execute_short_rest, execute_long_rest


def add_rest_endpoints(viewset_class):
    """
    Decorator to add rest and resource management endpoints to CharacterViewSet
    """
    
    @action(detail=True, methods=['post'])
    def long_rest(self, request, pk=None):
        """
        Perform a long rest:
        - Reset HP to max
        - Recover Hit Dice (half of total, min 1)
        - Reset spell slots (clear expended)
        - Reset all short/long rest class features
        """
        character = self.get_object()
        if not hasattr(character, 'stats') or not character.stats:
             return Response({"error": "Character has no stats"}, status=400)
             
        try:
            result = execute_long_rest(character, sync_combat=True)
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def short_rest(self, request, pk=None):
        """
        Perform a short rest.
        Body: { "hit_dice_to_spend": 2, "dice_choices": ["d10", "d6"] }
        """
        character = self.get_object()
        if not hasattr(character, 'stats') or not character.stats:
             return Response({"error": "Character has no stats"}, status=400)
             
        try:
            hit_dice_to_spend = int(request.data.get('hit_dice_to_spend', 0))
        except (ValueError, TypeError):
            return Response({"error": "hit_dice_to_spend must be an integer"}, status=400)

        dice_choices = request.data.get('dice_choices') or request.data.get('dice')

        try:
            result = execute_short_rest(
                character,
                hit_dice_to_spend=hit_dice_to_spend,
                dice_choices=dice_choices,
                sync_combat=True
            )
            return Response(result)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def expend_spell_slot(self, request, pk=None):
        """
        Use a spell slot.
        Body: { "level": 1 }
        """
        character = self.get_object()
        if not hasattr(character, 'stats'):
             return Response({"error": "Character has no stats"}, status=400)
             
        stats = character.stats
        slot_level = str(request.data.get('level'))
        
        # Max slots
        if not stats.spell_slots:
            stats.spell_slots = {}
        max_slots = stats.spell_slots.get(slot_level, 0)
        
        if not max_slots:
             return Response({"error": f"No slots of level {slot_level}"}, status=400)
        
        # Currently used
        if not stats.expended_spell_slots:
            stats.expended_spell_slots = {}
            
        current_used = stats.expended_spell_slots.get(slot_level, 0)
        
        if current_used >= max_slots:
            return Response({"error": "No slots remaining of this level"}, status=400)
            
        stats.expended_spell_slots[slot_level] = current_used + 1
        stats.save()
        
        return Response({
            "message": f"Level {slot_level} spell slot expended.",
            "level": slot_level,
            "remaining": max_slots - (current_used + 1),
            "expended": stats.expended_spell_slots
        })
        
    @action(detail=True, methods=['post'])
    def restore_spell_slot(self, request, pk=None):
        """
        Undo expending a spell slot (misclick fix).
        Body: { "level": 1 }
        """
        character = self.get_object()
        stats = character.stats
        slot_level = str(request.data.get('level'))
        
        if not stats.expended_spell_slots:
            return Response({"error": "No slots expended"}, status=400)
            
        current_used = stats.expended_spell_slots.get(slot_level, 0)
        if current_used <= 0:
             return Response({"error": "No slots used of this level"}, status=400)
             
        stats.expended_spell_slots[slot_level] = current_used - 1
        if stats.expended_spell_slots[slot_level] <= 0:
            del stats.expended_spell_slots[slot_level]
            
        stats.save()
        return Response({
            "message": f"Level {slot_level} spell slot restored.",
            "expended": stats.expended_spell_slots
        })

    # Attach actions
    viewset_class.long_rest = long_rest
    viewset_class.short_rest = short_rest
    viewset_class.expend_spell_slot = expend_spell_slot
    viewset_class.restore_spell_slot = restore_spell_slot
    
    return viewset_class
