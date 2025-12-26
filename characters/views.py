from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance, CharacterItem
)
from .serializers import (
    CharacterSerializer, CharacterStatsSerializer, CharacterClassSerializer,
    CharacterRaceSerializer, CharacterBackgroundSerializer, CharacterProficiencySerializer,
    CharacterFeatureSerializer, CharacterSpellSerializer, CharacterResistanceSerializer
)


class CharacterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing player characters."""
    queryset = Character.objects.all().order_by('-created_at')
    serializer_class = CharacterSerializer
    
    @action(detail=True, methods=['post'])
    def level_up(self, request, pk=None):
        """Level up a character"""
        character = self.get_object()
        character.level += 1
        character.save()
        
        serializer = self.get_serializer(character)
        return Response({
            "message": f"{character.name} leveled up to level {character.level}!",
            "character": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def take_damage(self, request, pk=None):
        """Apply damage to a character"""
        character = self.get_object()
        damage = request.data.get('damage', 0)
        
        if not isinstance(damage, int) or damage < 0:
            return Response(
                {"error": "Damage must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = character.stats
        stats.hit_points = max(0, stats.hit_points - damage)
        stats.save()
        
        serializer = CharacterStatsSerializer(stats)
        return Response({
            "message": f"{character.name} took {damage} damage. HP: {stats.hit_points}/{stats.max_hit_points}",
            "stats": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def heal(self, request, pk=None):
        """Heal a character"""
        character = self.get_object()
        amount = request.data.get('amount', 0)
        
        if not isinstance(amount, int) or amount < 0:
            return Response(
                {"error": "Heal amount must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = character.stats
        stats.hit_points = min(stats.max_hit_points, stats.hit_points + amount)
        stats.save()
        
        serializer = CharacterStatsSerializer(stats)
        return Response({
            "message": f"{character.name} healed {amount} HP. HP: {stats.hit_points}/{stats.max_hit_points}",
            "stats": serializer.data
        })
    
    @action(detail=True, methods=['get', 'post'])
    def inventory(self, request, pk=None):
        """Get or add items to character inventory"""
        character = self.get_object()
        
        if request.method == 'GET':
            # Get inventory
            items = CharacterItem.objects.filter(character=character)
            inventory_data = []
            for item in items:
                inventory_data.append({
                    'id': item.id,
                    'item': {
                        'id': item.item.id,
                        'name': item.item.name,
                        'category': item.item.category.name if item.item.category else None,
                    },
                    'quantity': item.quantity,
                    'is_equipped': item.is_equipped,
                    'equipment_slot': item.equipment_slot,
                    'equipment_slot_display': item.get_equipment_slot_display(),
                })
            return Response({'inventory': inventory_data})
        
        elif request.method == 'POST':
            # Add item to inventory
            item_id = request.data.get('item_id')
            quantity = int(request.data.get('quantity', 1))
            equipment_slot = request.data.get('equipment_slot', 'inventory')
            
            if not item_id:
                return Response(
                    {"error": "Missing 'item_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from items.models import Item
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                return Response(
                    {"error": "Item not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if character already has this item in this slot
            character_item, created = CharacterItem.objects.get_or_create(
                character=character,
                item=item,
                equipment_slot=equipment_slot,
                defaults={'quantity': quantity}
            )
            
            if not created:
                character_item.quantity += quantity
                character_item.save()
            
            return Response({
                "message": f"Added {quantity}x {item.name} to {character.name}'s inventory",
                "character_item": {
                    'id': character_item.id,
                    'item': item.name,
                    'quantity': character_item.quantity,
                    'equipment_slot': character_item.equipment_slot,
                }
            })
    
    @action(detail=True, methods=['post'])
    def equip_item(self, request, pk=None):
        """Equip an item"""
        character = self.get_object()
        character_item_id = request.data.get('character_item_id')
        equipment_slot = request.data.get('equipment_slot')
        
        if not character_item_id:
            return Response(
                {"error": "Missing 'character_item_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_item = CharacterItem.objects.get(pk=character_item_id, character=character)
        except CharacterItem.DoesNotExist:
            return Response(
                {"error": "Item not found in character's inventory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Unequip any item in the same slot
        if equipment_slot:
            CharacterItem.objects.filter(
                character=character,
                equipment_slot=equipment_slot,
                is_equipped=True
            ).update(is_equipped=False)
            character_item.equipment_slot = equipment_slot
        
        character_item.is_equipped = True
        character_item.save()
        
        return Response({
            "message": f"{character.name} equipped {character_item.item.name}",
            "character_item": {
                'id': character_item.id,
                'item': character_item.item.name,
                'equipment_slot': character_item.equipment_slot,
                'is_equipped': character_item.is_equipped,
            }
        })
    
    @action(detail=True, methods=['post'])
    def unequip_item(self, request, pk=None):
        """Unequip an item"""
        character = self.get_object()
        character_item_id = request.data.get('character_item_id')
        
        if not character_item_id:
            return Response(
                {"error": "Missing 'character_item_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_item = CharacterItem.objects.get(pk=character_item_id, character=character)
        except CharacterItem.DoesNotExist:
            return Response(
                {"error": "Item not found in character's inventory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        character_item.is_equipped = False
        character_item.equipment_slot = 'inventory'
        character_item.save()
        
        return Response({
            "message": f"{character.name} unequipped {character_item.item.name}",
            "character_item": {
                'id': character_item.id,
                'item': character_item.item.name,
                'is_equipped': character_item.is_equipped,
            }
        })
    
    @action(detail=True, methods=['get'])
    def combat_stats(self, request, pk=None):
        """Get character's lifetime combat statistics"""
        character = self.get_object()
        
        from combat.models import CombatParticipant, CombatLog
        
        # Get all combat participations
        participations = CombatParticipant.objects.filter(character=character)
        sessions = [p.combat_session for p in participations]
        
        # Aggregate statistics
        total_combats = len(sessions)
        total_damage_dealt = 0
        total_damage_received = 0
        total_attacks = 0
        total_hits = 0
        total_crits = 0
        total_spells_cast = 0
        favorite_weapon = {}
        favorite_spell = {}
        victories = 0
        
        for participation in participations:
            session = participation.combat_session
            log = session.get_or_create_log()
            log.calculate_statistics()
            
            # Get participant stats from log
            participant_stats = log.participant_stats.get(participation.id, {})
            total_damage_dealt += participant_stats.get('damage_dealt', 0)
            total_damage_received += participant_stats.get('damage_received', 0)
            total_attacks += participant_stats.get('attacks_made', 0)
            total_hits += participant_stats.get('attacks_hit', 0)
            total_crits += participant_stats.get('critical_hits', 0)
            total_spells_cast += participant_stats.get('spells_cast', 0)
            
            # Track favorite weapons and spells
            for action in session.actions.filter(actor=participation):
                if action.action_type == 'attack' and action.attack_name:
                    favorite_weapon[action.attack_name] = favorite_weapon.get(action.attack_name, 0) + 1
                elif action.action_type == 'spell' and action.attack_name:
                    favorite_spell[action.attack_name] = favorite_spell.get(action.attack_name, 0) + 1
            
            # Check if character was a victor
            if participation.id in log.victors:
                victories += 1
        
        # Calculate averages
        hit_rate = (total_hits / total_attacks * 100) if total_attacks > 0 else 0
        crit_rate = (total_crits / total_attacks * 100) if total_attacks > 0 else 0
        win_rate = (victories / total_combats * 100) if total_combats > 0 else 0
        
        return Response({
            'character': {
                'id': character.id,
                'name': character.name,
                'level': character.level,
            },
            'summary': {
                'total_combats': total_combats,
                'victories': victories,
                'win_rate': round(win_rate, 2),
            },
            'combat_statistics': {
                'total_damage_dealt': total_damage_dealt,
                'total_damage_received': total_damage_received,
                'total_attacks': total_attacks,
                'total_hits': total_hits,
                'hit_rate': round(hit_rate, 2),
                'total_critical_hits': total_crits,
                'critical_hit_rate': round(crit_rate, 2),
                'total_spells_cast': total_spells_cast,
                'average_damage_per_combat': round(total_damage_dealt / total_combats, 2) if total_combats > 0 else 0,
            },
            'favorites': {
                'weapon': max(favorite_weapon.items(), key=lambda x: x[1])[0] if favorite_weapon else None,
                'spell': max(favorite_spell.items(), key=lambda x: x[1])[0] if favorite_spell else None,
            },
            'weapon_usage': favorite_weapon,
            'spell_usage': favorite_spell,
        })


class CharacterClassViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character classes."""
    queryset = CharacterClass.objects.all()
    serializer_class = CharacterClassSerializer


class CharacterRaceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character races."""
    queryset = CharacterRace.objects.all()
    serializer_class = CharacterRaceSerializer


class CharacterBackgroundViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character backgrounds."""
    queryset = CharacterBackground.objects.all()
    serializer_class = CharacterBackgroundSerializer


class CharacterStatsViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character stats."""
    queryset = CharacterStats.objects.all()
    serializer_class = CharacterStatsSerializer


class CharacterProficiencyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character proficiencies."""
    queryset = CharacterProficiency.objects.all()
    serializer_class = CharacterProficiencySerializer


class CharacterFeatureViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character features."""
    queryset = CharacterFeature.objects.all()
    serializer_class = CharacterFeatureSerializer


class CharacterSpellViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character spells."""
    queryset = CharacterSpell.objects.all()
    serializer_class = CharacterSpellSerializer


class CharacterResistanceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character resistances."""
    queryset = CharacterResistance.objects.all()
    serializer_class = CharacterResistanceSerializer
