"""
Reference ViewSets for lookup data (Classes, Races, Backgrounds, etc.)
These are simpler read-only or basic CRUD ViewSets for reference data.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    CharacterClass, CharacterRace, CharacterBackground,
    CharacterStats, CharacterProficiency, CharacterFeature,
    CharacterSpell, CharacterResistance
)
from ..serializers import (
    CharacterClassSerializer, CharacterRaceSerializer, CharacterBackgroundSerializer,
    CharacterStatsSerializer, CharacterProficiencySerializer, CharacterFeatureSerializer,
    CharacterSpellSerializer, CharacterResistanceSerializer
)


class CharacterClassViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character classes."""
    queryset = CharacterClass.objects.all()
    serializer_class = CharacterClassSerializer
    
    @action(detail=True, methods=['get'])
    def subclasses(self, request, pk=None):
        """Get available subclasses for this class"""
        character_class = self.get_object()
        ruleset = request.query_params.get('ruleset', '2014')
        
        from campaigns.class_features_data import AVAILABLE_SUBCLASSES_2014, AVAILABLE_SUBCLASSES_2024
        
        if ruleset == '2024':
            subclasses = AVAILABLE_SUBCLASSES_2024.get(character_class.name, [])
        else:
            subclasses = AVAILABLE_SUBCLASSES_2014.get(character_class.name, [])
            
        data = []
        for sc_name in subclasses:
            data.append({
                'name': sc_name,
                'id': sc_name,
                'description': f"A valid subclass for {character_class.name}"
            })
            
        return Response(data)


class CharacterRaceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character races."""
    queryset = CharacterRace.objects.all()
    serializer_class = CharacterRaceSerializer

    def get_queryset(self):
        queryset = CharacterRace.objects.all()
        ruleset = self.request.query_params.get('ruleset', '2014')
        
        if ruleset == '2024':
            return queryset.filter(source_ruleset__in=['2024', 'all'])
        else:
            return queryset.filter(source_ruleset__in=['2014', 'all'])


class CharacterBackgroundViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character backgrounds."""
    queryset = CharacterBackground.objects.all()
    serializer_class = CharacterBackgroundSerializer

    def get_queryset(self):
        queryset = CharacterBackground.objects.all()
        ruleset = self.request.query_params.get('ruleset', '2014')
        
        if ruleset == '2024':
            return queryset.filter(source_ruleset__in=['2024', 'all'])
        else:
            return queryset.filter(source_ruleset__in=['2014', 'all'])


class CharacterStatsViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character stats."""
    serializer_class = CharacterStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character stats to only show those for characters owned by the current user"""
        return CharacterStats.objects.filter(character__user=self.request.user)


class CharacterProficiencyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character proficiencies."""
    serializer_class = CharacterProficiencySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character proficiencies to only show those for characters owned by the current user"""
        return CharacterProficiency.objects.filter(character__user=self.request.user)


class CharacterFeatureViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character features."""
    serializer_class = CharacterFeatureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character features to only show those for characters owned by the current user"""
        return CharacterFeature.objects.filter(character__user=self.request.user)

    def perform_update(self, serializer):
        feature = serializer.save()
        self._sync_proficiencies(feature)
        
    def _sync_proficiencies(self, feature):
        """
        Syncs selected options to CharacterProficiency model.
        Handles 'Class Skills', 'Skilled' feat, etc.
        """
        from ..models import CharacterProficiency
        
        if not feature.selection:
            CharacterProficiency.objects.filter(
                character=feature.character,
                source=f"Feature: {feature.name}"
            ).delete()
            return

        CharacterProficiency.objects.filter(
            character=feature.character,
            source=f"Feature: {feature.name}"
        ).delete()
        
        ALL_SKILLS = {
            'Acrobatics', 'Animal Handling', 'Arcana', 'Athletics', 'Deception', 'History', 
            'Insight', 'Intimidation', 'Investigation', 'Medicine', 'Nature', 'Perception', 
            'Performance', 'Persuasion', 'Religion', 'Sleight of Hand', 'Stealth', 'Survival'
        }
        
        for item in feature.selection:
            if item in ALL_SKILLS:
                if not CharacterProficiency.objects.filter(
                    character=feature.character,
                    proficiency_type='skill',
                    skill_name=item
                ).exists():
                    CharacterProficiency.objects.create(
                        character=feature.character,
                        proficiency_type='skill',
                        skill_name=item,
                        proficiency_level='proficient',
                        source=f"Feature: {feature.name}"
                    )


class CharacterSpellViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character spells."""
    serializer_class = CharacterSpellSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character spells to only show those for characters owned by the current user"""
        return CharacterSpell.objects.filter(character__user=self.request.user)


class CharacterResistanceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character resistances."""
    serializer_class = CharacterResistanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character resistances to only show those for characters owned by the current user"""
        return CharacterResistance.objects.filter(character__user=self.request.user)
