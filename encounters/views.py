from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Encounter, EncounterEnemy
from .serializers import EncounterSerializer, EncounterEnemySerializer


class EncounterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing encounters."""
    queryset = Encounter.objects.all().order_by('-created_at')
    serializer_class = EncounterSerializer

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

        # Apply damage using the model’s built-in logic
        encounter_enemy.take_damage(damage)

        serializer = EncounterEnemySerializer(encounter_enemy)
        return Response({
            "message": f"{encounter_enemy.name} took {damage} damage.",
            "enemy": serializer.data
        })


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

        # ✅ Correct variable name here:
        enemy_instance.heal(amount)

        serializer = self.get_serializer(enemy_instance)
        return Response(serializer.data)
