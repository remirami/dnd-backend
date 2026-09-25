import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from characters.models import Character
from combat.models import CombatSession
from gauntlet.models import GauntletRun, GauntletSnapshotHero
from gauntlet.serializers import (
    GauntletRunCreateSerializer,
    GauntletRunSerializer,
    RespiteRequestSerializer,
)

logger = logging.getLogger('combat')


class GauntletViewSet(viewsets.ModelViewSet):
    """
    Pillar 1: Gauntlet API ViewSet.
    Manages procedural wave-survival runs, hero snapshots,
    respite rewards, and scoreboards.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GauntletRunSerializer

    def get_queryset(self):
        user = self.request.user
        qs = GauntletRun.objects.prefetch_related(
            'snapshot_heroes',
            'snapshot_heroes__character'
        ).select_related('current_combat_session').order_by('-started_at')

        if user and user.is_authenticated and not user.is_staff:
            return qs.filter(user=user)
        return qs

    def create(self, request, *args, **kwargs):
        """Create a new Gauntlet Run and stage snapshot heroes."""
        serializer = GauntletRunCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data.get('name', 'The Gauntlet')
        theme = serializer.validated_data.get('theme', 'colosseum')
        character_ids = serializer.validated_data.get('character_ids', [])
        auto_delete_oldest = serializer.validated_data.get('auto_delete_oldest', False)

        if request.user and request.user.is_authenticated:
            from django.db.models import Q
            GauntletRun.objects.filter(
                user=request.user,
                status__in=['preparing', 'active', 'respite'],
            ).filter(
                Q(current_combat_session__isnull=True) |
                Q(current_combat_session__status='ended')
            ).update(status='failed')

            from combat.utils import enforce_user_combat_limits
            enforce_user_combat_limits(request.user, auto_delete_oldest=bool(auto_delete_oldest))

        with transaction.atomic():
            run = GauntletRun.objects.create(
                user=request.user,
                name=name,
                theme=theme,
                status='preparing'
            )

            for char_id in character_ids:
                char = Character.objects.get(id=char_id)
                run.add_hero(char)

            # Auto-start Wave 1
            combat_session = run.start_run()

        output_serializer = GauntletRunSerializer(run)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def sync_wave(self, request, pk=None):
        """
        Syncs state from the current combat session, checking if wave is cleared
        or if party wiped.
        """
        run = self.get_object()
        session = run.current_combat_session

        if not session:
            return Response({"error": "No active combat session for this run."}, status=status.HTTP_400_BAD_REQUEST)

        # Idempotency guard: If run has already ended or is already in respite, return current tally without re-scoring
        if run.status in ['failed', 'completed', 'victory', 'respite']:
            return Response({
                "run_status": run.status,
                "message": f"Run is already in {run.status} status.",
                "run": GauntletRunSerializer(run).data
            })

        with transaction.atomic():
            # First, sync hero vitals
            for hero in run.snapshot_heroes.all():
                participant = session.participants.filter(character=hero.character).first()
                if participant:
                    hero.current_hp = max(0, participant.current_hp)
                    hero.is_alive = participant.is_active and participant.current_hp > 0
                    hero.save()

            alive_heroes = run.snapshot_heroes.filter(is_alive=True)
            if not alive_heroes.exists():
                session.status = 'ended'
                session.save(update_fields=['status'])

                run.status = 'failed'
                run.completed_at = timezone.now()

                # Tally enemies killed and turns in this final wave without wave-completion bonus
                enemies_in_session = session.participants.filter(participant_type='enemy')
                dead_enemies = enemies_in_session.filter(current_hp=0).count()
                run.enemies_killed += dead_enemies
                run.turns_elapsed += session.current_round
                run.score += (dead_enemies * 150)
                run.save()

                return Response({
                    "run_status": "failed",
                    "message": "All heroes have fallen in the Gauntlet!",
                    "run": GauntletRunSerializer(run).data
                })

            # Check if all enemies in combat session are dead
            active_enemies = session.participants.filter(participant_type='enemy', current_hp__gt=0, is_active=True)
            if not active_enemies.exists():
                # Wave cleared! Transition to respite
                session.status = 'ended'
                session.save(update_fields=['status'])

                run.sync_from_combat_session()
                run.status = 'respite'
                run.save()

                return Response({
                    "run_status": "respite",
                    "wave_cleared": run.current_wave,
                    "message": f"Wave {run.current_wave} cleared! Choose your respite reward.",
                    "run": GauntletRunSerializer(run).data
                })

        return Response({
            "run_status": run.status,
            "run": GauntletRunSerializer(run).data
        })

    @action(detail=True, methods=['post'])
    def respite(self, request, pk=None):
        """Apply a respite choice between waves."""
        run = self.get_object()
        if run.status != 'respite':
            return Response(
                {"error": f"Run must be in 'respite' status to choose rewards (current: {run.status})."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RespiteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        choice_type = serializer.validated_data['choice_type']
        details = serializer.validated_data.get('details', {})

        try:
            result = run.apply_respite(choice_type, details)
            return Response({
                "result": result,
                "run": GauntletRunSerializer(run).data
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def next_wave(self, request, pk=None):
        """Summon the next wave after completing respite."""
        run = self.get_object()
        if run.status not in ['respite', 'ready_for_wave']:
            return Response(
                {"error": f"Cannot start next wave while run status is '{run.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = run.advance_to_next_wave()
            if session is None:
                # Reached end of trial
                return Response({
                    "run_status": "completed",
                    "message": "Trial completed! Claim your victory.",
                    "run": GauntletRunSerializer(run).data
                })

            return Response({
                "run_status": "active",
                "current_wave": run.current_wave,
                "combat_session_id": session.id,
                "run": GauntletRunSerializer(run).data
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def claim_victory(self, request, pk=None):
        """Claim victory after Wave 10."""
        run = self.get_object()
        if run.current_wave < run.max_waves:
            return Response(
                {"error": f"Must clear all {run.max_waves} waves to claim victory."},
                status=status.HTTP_400_BAD_REQUEST
            )

        run.status = 'completed'
        run.completed_at = timezone.now()
        # Victory score bonus: +5,000 points
        run.score += 5000
        run.save()

        return Response({
            "message": "Victory claimed! High score recorded.",
            "run": GauntletRunSerializer(run).data
        })

    @action(detail=True, methods=['post'])
    def enter_endless(self, request, pk=None):
        """Transition from standard 10-wave run into endless overtime."""
        run = self.get_object()
        if run.current_wave < 10:
            return Response(
                {"error": "Must reach Wave 10 before entering Endless Overtime."},
                status=status.HTTP_400_BAD_REQUEST
            )

        run.is_endless = True
        run.status = 'ready_for_wave'
        run.save()

        return Response({
            "message": "Entered Endless Overtime! Push for the ultimate high score.",
            "run": GauntletRunSerializer(run).data
        })

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        """Abandon an active Gauntlet run."""
        run = self.get_object()
        if run.status in ['preparing', 'active', 'respite', 'ready_for_wave']:
            run.status = 'failed'
            run.completed_at = timezone.now()
            run.save(update_fields=['status', 'completed_at'])
            if run.current_combat_session and run.current_combat_session.status != 'ended':
                run.current_combat_session.status = 'ended'
                run.current_combat_session.save(update_fields=['status'])
        return Response({"message": "Run abandoned.", "run": GauntletRunSerializer(run).data})

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Public leaderboard of top Gauntlet runs."""
        top_runs = GauntletRun.objects.filter(
            status__in=['completed', 'failed', 'respite', 'active']
        ).order_by('-score')[:20]

        serializer = GauntletRunSerializer(top_runs, many=True)
        return Response(serializer.data)
