from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import math
import random

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
        """
        character = self.get_object()
        if not hasattr(character, 'stats'):
             return Response({"error": "Character has no stats"}, status=400)
             
        stats = character.stats
        
        # 1. Reset HP
        stats.hit_points = stats.max_hit_points
        stats.temporary_hit_points = 0 
        
        # 2. Recover Hit Dice
        # Ensure hit_dice_used is initialized
        if stats.hit_dice_used is None:
            stats.hit_dice_used = 0
            
        total_level = character.level
        recover_amount = max(1, total_level // 2)
        stats.hit_dice_used = max(0, stats.hit_dice_used - recover_amount)
        
        # 3. Reset Spell Slots (Clear expended)
        stats.expended_spell_slots = {}
        
        # 4. Save
        stats.save()
        
        return Response({
            "message": "Long rest completed. HP and Spell Slots restored.",
            "hit_points": stats.hit_points,
            "expended_spell_slots": stats.expended_spell_slots,
            "hit_dice_used": stats.hit_dice_used
        })

    @action(detail=True, methods=['post'])
    def short_rest(self, request, pk=None):
        """
        Perform a short rest.
        Body: { "hit_dice_to_spend": 2 }
        """
        character = self.get_object()
        if not hasattr(character, 'stats'):
             return Response({"error": "Character has no stats"}, status=400)
             
        stats = character.stats
        
        hit_dice_to_spend = int(request.data.get('hit_dice_to_spend', 0))
        
        # Validate Hit Dice
        total_hit_dice = character.level
        
        if stats.hit_dice_used is None:
            stats.hit_dice_used = 0
            
        current_hit_dice = total_hit_dice - stats.hit_dice_used
        
        if hit_dice_to_spend > current_hit_dice:
             return Response({"error": f"Not enough hit dice. have {current_hit_dice}, want {hit_dice_to_spend}"}, status=400)
        
        hp_recovered = 0
        if hit_dice_to_spend > 0:
            from core.dnd_utils import calculate_ability_modifier
            con_mod = calculate_ability_modifier(stats.constitution)
            
            # Identify Hit Die size (e.g. d8, d10)
            hit_dice_str = character.character_class.hit_dice # "d8"
            try:
                die_size = int(hit_dice_str.replace('d', ''))
            except:
                die_size = 8
            
            # Roll
            rolls = []
            for _ in range(hit_dice_to_spend):
                roll = random.randint(1, die_size)
                total = max(0, roll + con_mod) 
                rolls.append(total)
                hp_recovered += total
            
            # Apply HP
            stats.hit_points = min(stats.max_hit_points, stats.hit_points + hp_recovered)
            stats.hit_dice_used += hit_dice_to_spend
            

        # 3. Ki Point Restoration (Monk)
        stats.ki_points_used = 0
        
        # 4. Warlock Slot Restoration (Pact Magic)
        # Handle Multiclass safely: Only reset slots that Warlock provides.
        warlock_level = 0
        if character.character_class.name.lower() == 'warlock':
             warlock_level = character.level
        else:
             from characters.multiclassing import get_class_level
             warlock_level = get_class_level(character, 'warlock')
             
        if warlock_level > 0:
             # Calculate Warlock Slots
             # Table:
             # 1: 1 @ 1
             # 2-9: 2 @ X
             # 10+:... (Simplified for now or import utils)
             from campaigns.utils import calculate_spell_slots
             # Note: calculate_spell_slots might return total slots if we pass the character?
             # But we want specifically Warlock contribution.
             # Let's use a pact magic helper or simple lookup for common tiers.
             
             pact_slots = 0
             pact_level = 0
             
             # Standard Warlock Table (SRD)
             if warlock_level >= 17: pact_slots, pact_level = 4, 5
             elif warlock_level >= 11: pact_slots, pact_level = 3, 5
             elif warlock_level >= 9: pact_slots, pact_level = 2, 5
             elif warlock_level >= 7: pact_slots, pact_level = 2, 4
             elif warlock_level >= 5: pact_slots, pact_level = 2, 3
             elif warlock_level >= 3: pact_slots, pact_level = 2, 2
             elif warlock_level >= 2: pact_slots, pact_level = 2, 1
             elif warlock_level >= 1: pact_slots, pact_level = 1, 1
             
             pact_level_str = str(pact_level)
             
             if stats.expended_spell_slots and pact_level_str in stats.expended_spell_slots:
                 current_expended = stats.expended_spell_slots[pact_level_str]
                 new_expended = max(0, current_expended - pact_slots)
                 if new_expended == 0:
                     del stats.expended_spell_slots[pact_level_str]
                 else:
                     stats.expended_spell_slots[pact_level_str] = new_expended
        
        stats.save()
        
        return Response({
            "message": f"Short rest completed. Recovered {hp_recovered} HP. Reset Warlock slots and Ki points.",
            "hit_points": stats.hit_points,
            "hit_dice_used": stats.hit_dice_used,
            "hp_gained": hp_recovered,
            "ki_points_used": stats.ki_points_used,
            "expended_spell_slots": stats.expended_spell_slots
        })

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
