from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.conf import settings

from core.throttles import SpellLookupThrottle

from .models import Spell, SpellDamage
from .serializers import SpellSerializer, SpellListSerializer


class SpellViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing spells.
    
    Provides filtering by level, school, concentration, ritual, and classes.
    Search by name or description.
    Read operations are cached for 1 hour.
    Rate limited to 200 requests per hour.
    """
    queryset = Spell.objects.all().prefetch_related('classes', 'damage_progression')
    serializer_class = SpellSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['level', 'name', 'school']
    ordering = ['level', 'name']
    
    # Rate limiting: 200 requests per hour for spell lookups
    throttle_classes = [SpellLookupThrottle]
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level is not None:
            queryset = queryset.filter(level=level)
        
        # Filter by school
        school = self.request.query_params.get('school')
        if school:
            queryset = queryset.filter(school=school)
        
        # Filter by concentration
        concentration = self.request.query_params.get('concentration')
        if concentration is not None:
            queryset = queryset.filter(concentration=concentration.lower() == 'true')
        
        # Filter by ritual
        ritual = self.request.query_params.get('ritual')
        if ritual is not None:
            queryset = queryset.filter(ritual=ritual.lower() == 'true')
        
        # Filter by class
        class_name = self.request.query_params.get('classes')
        if class_name:
            queryset = queryset.filter(classes__name__iexact=class_name)
        
        return queryset
    
    def get_serializer_class(self):
        """Use lighter serializer for list view"""
        if self.action == 'list':
            return SpellListSerializer
        return SpellSerializer
    
    
    @method_decorator(cache_page(settings.CACHE_TTL.get('spell', 3600), key_prefix='spells_by_class'))
    @action(detail=False, methods=['get'])
    def by_class(self, request):
        """
        Get spells available to a specific class.
        Query param: class_name (e.g., 'wizard', 'cleric')
        Cached for 1 hour.
        """
        class_name = request.query_params.get('class_name', '').lower()
        if not class_name:
            return Response(
                {'error': 'class_name query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spells = self.queryset.filter(classes__name__iexact=class_name)
        serializer = self.get_serializer(spells, many=True)
        return Response(serializer.data)
    
    @method_decorator(cache_page(settings.CACHE_TTL.get('spell', 3600), key_prefix='spells_cantrips'))
    @action(detail=False, methods=['get'])
    def cantrips(self, request):
        """Get all cantrips (level 0 spells). Cached for 1 hour."""
        cantrips = self.queryset.filter(level=0)
        serializer = self.get_serializer(cantrips, many=True)
        return Response(serializer.data)
    
    @method_decorator(cache_page(settings.CACHE_TTL.get('spell', 3600), key_prefix='spells_rituals'))
    @action(detail=False, methods=['get'])
    def rituals(self, request):
        """Get all ritual spells. Cached for 1 hour."""
        rituals = self.queryset.filter(ritual=True)
        serializer = self.get_serializer(rituals, many=True)
        return Response(serializer.data)
    
    @method_decorator(cache_page(settings.CACHE_TTL.get('spell', 3600), key_prefix='spells_concentration'))
    @action(detail=False, methods=['get'])
    def concentration(self, request):
        """Get all concentration spells. Cached for 1 hour."""
        concentration_spells = self.queryset.filter(concentration=True)
        serializer = self.get_serializer(concentration_spells, many=True)
        return Response(serializer.data)
