from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance
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
