from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Encounter, EncounterEnemy, EncounterTheme, BiomeEncounterWeight
from .serializers import (
    EncounterSerializer, EncounterEnemySerializer, EncounterThemeSerializer,
    BiomeEncounterWeightSerializer
)
from .services import EncounterGenerator, BiomeEncounterGenerator


class EncounterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing encounters."""
    queryset = Encounter.objects.all().order_by('-created_at')
    serializer_class = EncounterSerializer

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_encounter(self, request):
        """
        Generate a random encounter
        
        POST /api/encounters/generate/
        {
            "party_level": 5,
            "party_size": 4,
            "difficulty": "hard",           // Optional: easy/medium/hard/deadly
            "biome": "desert",               // Optional
            "force_theme_id": 12,            // Optional
            "allow_chaotic": true            // Optional, default true
        }
        """
        # Extract parameters
        party_level = request.data.get('party_level')
        party_size = request.data.get('party_size')
        difficulty = request.data.get('difficulty', 'medium')
        biome = request.data.get('biome')
        force_theme_id = request.data.get('force_theme_id')
        allow_chaotic = request.data.get('allow_chaotic', True)
        
        # Validate required fields
        if not party_level or not party_size:
            return Response(
                {"error": "Missing required fields: party_level, party_size"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate values
        try:
            party_level = int(party_level)
            party_size = int(party_size)
        except ValueError:
            return Response(
                {"error": "party_level and party_size must be integers"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if party_level < 1 or party_level > 20:
            return Response(
                {"error": "party_level must be between 1 and 20"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if party_size < 1 or party_size > 10:
            return Response(
                {"error": "party_size must be between 1 and 10"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get theme if specified
        force_theme = None
        if force_theme_id:
            try:
                force_theme = EncounterTheme.objects.get(id=force_theme_id)
            except EncounterTheme.DoesNotExist:
                return Response(
                    {"error": f"Theme with id {force_theme_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Generate encounter
        if biome:
            # Use biome generator
            biome_generator = BiomeEncounterGenerator()
            encounter = biome_generator.generate_by_biome(
                biome=biome,
                party_level=party_level,
                party_size=party_size,
                difficulty=difficulty
            )
        else:
            # Use standard generator
            generator = EncounterGenerator()
            encounter = generator.generate_encounter(
                party_level=party_level,
                party_size=party_size,
                difficulty=difficulty,
                force_theme=force_theme,
                allow_chaotic=allow_chaotic
            )
        
        # Serialize and return
        serializer = self.get_serializer(encounter)
        return Response({
            "message": "Encounter generated successfully",
            "encounter": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='attack')
    def attack_enemy(self, request, pk=None):
        """
        Custom action: apply damage to an enemy in this encounter.
        Example payload:
        {
            "enemy_id": 5,
            "damage": 12
        }
        """
        encounter = self.get_object()
        enemy_id = request.data.get('enemy_id')
        damage = request.data.get('damage')

        if not enemy_id or damage is None:
            return Response(
                {"error": "Missing 'enemy_id' or 'damage'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            damage = int(damage)
        except ValueError:
            return Response(
                {"error": "'damage' must be an integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            encounter_enemy = encounter.enemies.get(id=enemy_id)
        except EncounterEnemy.DoesNotExist:
            return Response(
                {"error": f"Enemy with id {enemy_id} not found in this encounter."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Apply damage using the model's built-in logic
        encounter_enemy.take_damage(damage)

        serializer = EncounterEnemySerializer(encounter_enemy)
        return Response({
            "message": f"{encounter_enemy.name} took {damage} damage.",
            "enemy": serializer.data
        })


class EncounterThemeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing encounter themes"""
    queryset = EncounterTheme.objects.all().order_by('category', 'name')
    serializer_class = EncounterThemeSerializer
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of distinct categories"""
        categories = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EncounterTheme.CATEGORY_CHOICES
        ]
        return Response(categories)
    
    @action(detail=False, methods=['get'])
    def biomes(self, request):
        """Get list of biomes"""
        biomes = [
            {'value': choice[0], 'label': choice[1]}
            for choice in BiomeEncounterWeight.BIOME_CHOICES
        ]
        return Response(biomes)


class EncounterEnemyViewSet(viewsets.ModelViewSet):
    queryset = EncounterEnemy.objects.all()
    serializer_class = EncounterEnemySerializer

    @action(detail=True, methods=['post'])
    def damage(self, request, pk=None):
        """Apply damage to an encounter enemy"""
        enemy_instance = self.get_object()
        amount = int(request.data.get('amount', 0))
        if amount <= 0:
            return Response({'error': 'Damage amount must be positive.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        enemy_instance.take_damage(amount)
        serializer = self.get_serializer(enemy_instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def heal(self, request, pk=None):
        """Heal an encounter enemy"""
        enemy_instance = self.get_object()
        amount = int(request.data.get('amount', 0))
        if amount <= 0:
            return Response({'error': 'Heal amount must be positive.'},
                            status=status.HTTP_400_BAD_REQUEST)

        enemy_instance.heal(amount)

        serializer = self.get_serializer(enemy_instance)
        return Response(serializer.data)
