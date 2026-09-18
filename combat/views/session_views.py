"""
Session Views - CombatSessionViewSet (main viewset).

This is the primary combat viewset that composes all mixin classes.
It handles session lifecycle: create, start, add_participant, roll_initiative,
next_turn, and end. All other actions are inherited from mixins.
"""
import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from characters.models import Character
from combat.models import CombatParticipant, CombatSession
from combat.serializers import (
    CombatParticipantSerializer,
    CombatSessionListSerializer,
    CombatSessionSerializer,
)
from combat.utils import roll_d20
from core.throttles import CombatActionThrottle
from encounters.models import Encounter, EncounterEnemy

from .combat_action_views import CombatActionMixin
from .environment_views import CombatEnvironmentMixin
from .practice_views import CombatPracticeMixin
from .reaction_views import CombatReactionMixin

# Combat logging
logger = logging.getLogger('combat')


# Hard limits for combat participants (Option 1: Balanced Tabletop Limits)
MAX_TOTAL_PARTICIPANTS = 16
MAX_PARTY_PARTICIPANTS = 6
MAX_ENEMY_PARTICIPANTS = 10


class CombatSessionViewSet(
    CombatActionMixin,
    CombatReactionMixin,
    CombatEnvironmentMixin,
    CombatPracticeMixin,
    viewsets.ModelViewSet,
):
    """API endpoint for managing combat sessions"""
    serializer_class = CombatSessionSerializer
    throttle_classes = [CombatActionThrottle]

    MAX_ACTIVE_COMBATS_PER_USER = 2
    MAX_TOTAL_COMBATS_PER_USER = 10

    def get_serializer_class(self):
        if self.action == 'list':
            return CombatSessionListSerializer
        return CombatSessionSerializer

    def get_queryset(self):
        qs = CombatSession.objects.all().select_related('encounter')
        if self.request.user and self.request.user.is_authenticated:
            if not self.request.user.is_staff:
                from django.db.models import Q
                qs = qs.filter(Q(created_by=self.request.user) | Q(created_by__isnull=True))
        if self.action == 'list':
            # Purge any abandoned empty preparing sessions for authenticated users
            if self.request.user and self.request.user.is_authenticated:
                CombatSession.objects.filter(
                    created_by=self.request.user,
                    status='preparing',
                    participants__isnull=True
                ).delete()
            return qs.exclude(
                status='preparing',
                participants__isnull=True
            ).prefetch_related(
                'participants'
            ).order_by('-started_at')
        return qs.select_related(
            'encounter'
        ).prefetch_related(
            'participants',
            'participants__conditions',
            'participants__character',
            'participants__character__stats',
            'participants__character__character_items__item__weapon',
            'participants__character__character_items__item__armor',
            'participants__encounter_enemy',
            'participants__encounter_enemy__enemy',
            'participants__encounter_enemy__enemy__stats',
            'participants__encounter_enemy__enemy__attacks',
            'participants__encounter_enemy__enemy__abilities',
            'participants__encounter_enemy__enemy__resistances__damage_type',
            'actions',
            'actions__actor',
            'actions__target',
            'actions__damage_type',
        ).order_by('-started_at')
    
    def perform_create(self, serializer):
        """Handle creation with optional encounter and per-user limits"""
        user = self.request.user if (self.request.user and self.request.user.is_authenticated) else None
        
        if user:
            from rest_framework.exceptions import ValidationError
            # Automatically delete any abandoned preparing sessions with no participants for this user
            CombatSession.objects.filter(
                created_by=user,
                status='preparing',
                participants__isnull=True
            ).delete()

            user_sessions = CombatSession.objects.filter(created_by=user)
            if user_sessions.count() >= self.MAX_TOTAL_COMBATS_PER_USER:
                raise ValidationError(
                    {"error": f"Combat limit reached. You can have a maximum of {self.MAX_TOTAL_COMBATS_PER_USER} saved combat sessions. Please delete an older session to create a new one."}
                )
            active_count = user_sessions.filter(
                status__in=['preparing', 'active']
            ).exclude(
                status='preparing',
                participants__isnull=True
            ).count()
            if active_count >= self.MAX_ACTIVE_COMBATS_PER_USER:
                raise ValidationError(
                    {"error": f"Active combat limit reached. You can have a maximum of {self.MAX_ACTIVE_COMBATS_PER_USER} active combat sessions. Please finish or delete an active combat session before starting a new one."}
                )

        encounter_id = self.request.data.get('encounter_id')
        is_practice = self.request.data.get('is_practice', False)
        
        if is_practice or not encounter_id:
            # Practice mode: no encounter needed
            serializer.save(created_by=user, encounter=None, is_practice=True)
        else:
            # Campaign mode: require encounter
            try:
                encounter = Encounter.objects.get(pk=encounter_id)
                serializer.save(created_by=user, encounter=encounter, is_practice=False)
            except Encounter.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"encounter_id": "Encounter not found"})
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a combat session"""
        session = self.get_object()
        logger.info(f"Combat start requested for session {pk} by user {request.user}")
        
        if session.status != 'preparing':
            logger.warning(f"Cannot start combat {pk}: status is '{session.status}', not 'preparing'")
            return Response(
                {"error": "Combat must be in 'preparing' status to start"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participants = session.participants.filter(is_active=True)
        if not participants.exists():
            logger.warning(f"Cannot start combat {pk}: no participants")
            return Response(
                {"error": "Cannot start combat without participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not participants.filter(participant_type='enemy').exists():
            logger.warning(f"Cannot start combat {pk}: no enemies")
            return Response(
                {"error": "Cannot start combat without at least one enemy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participants.count() > MAX_TOTAL_PARTICIPANTS:
            return Response(
                {"error": f"Cannot start combat: total participants ({participants.count()}) exceed limit of {MAX_TOTAL_PARTICIPANTS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participants.filter(participant_type='character').count() > MAX_PARTY_PARTICIPANTS:
            return Response(
                {"error": f"Cannot start combat: party size ({participants.filter(participant_type='character').count()}) exceeds limit of {MAX_PARTY_PARTICIPANTS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participants.filter(participant_type='enemy').count() > MAX_ENEMY_PARTICIPANTS:
            return Response(
                {"error": f"Cannot start combat: enemies ({participants.filter(participant_type='enemy').count()}) exceed limit of {MAX_ENEMY_PARTICIPANTS}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'active'
        session.current_round = 1
        session.current_turn_index = 0
        session.started_at = timezone.now()
        session.save()
        
        # Reset turn action economy for all active participants at combat start
        for participant in participants:
            participant.reset_turn()
        
        logger.info(f"Combat {pk} started with {participants.count()} participants")
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat started",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to combat"""
        session = self.get_object()
        participant_type = request.data.get('participant_type')
        
        # Enforce total participant limit
        if session.participants.count() >= MAX_TOTAL_PARTICIPANTS:
            return Response(
                {"error": f"Encounter participant limit reached (maximum {MAX_TOTAL_PARTICIPANTS} participants)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if participant_type == 'character':
            # Enforce party participant limit
            party_count = session.participants.filter(participant_type='character').count()
            if party_count >= MAX_PARTY_PARTICIPANTS:
                return Response(
                    {"error": f"Party roster is full (maximum {MAX_PARTY_PARTICIPANTS} characters)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            character_id = request.data.get('character_id')
            if not character_id:
                return Response(
                    {"error": "Missing 'character_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Prevent duplicate character
            if session.participants.filter(participant_type='character', character_id=character_id).exists():
                return Response(
                    {"error": "Character is already in this combat session"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                character = Character.objects.get(pk=character_id)
            except Character.DoesNotExist:
                return Response(
                    {"error": "Character not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not hasattr(character, 'stats'):
                return Response(
                    {"error": "Character must have stats"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            stats = character.stats
            participant = CombatParticipant.objects.create(
                combat_session=session,
                participant_type='character',
                character=character,
                initiative=0,
                current_hp=stats.hit_points,
                max_hp=stats.max_hit_points,
                armor_class=stats.armor_class
            )
            session.participants.add(participant)
            
            serializer = CombatParticipantSerializer(participant)
            return Response({
                "message": f"{character.name} added to combat",
                "participant": serializer.data
            })
        
        elif participant_type == 'enemy':
            # Enforce enemy participant limit
            enemy_count = session.participants.filter(participant_type='enemy').count()
            if enemy_count >= MAX_ENEMY_PARTICIPANTS:
                return Response(
                    {"error": f"Enemy roster is full (maximum {MAX_ENEMY_PARTICIPANTS} enemies)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            encounter_enemy_id = request.data.get('encounter_enemy_id')
            enemy_id = request.data.get('enemy_id')  # Direct enemy ID for practice mode
            
            # Support both EncounterEnemy (for campaigns) and direct Enemy (for practice)
            if enemy_id:
                # Practice mode: add enemy directly
                from bestiary.models import Enemy
                try:
                    enemy = Enemy.objects.get(pk=enemy_id)
                except Enemy.DoesNotExist:
                    return Response(
                        {"error": "Enemy not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if not hasattr(enemy, 'stats'):
                    return Response(
                        {"error": "Enemy must have stats"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                enemy_name = request.data.get('enemy_name', enemy.name)
                enemy_hp = request.data.get('enemy_hp', enemy.stats.hit_points if hasattr(enemy, 'stats') else 10)
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    name=enemy_name,  # Set the enemy name for practice mode
                    encounter_enemy=None,  # No EncounterEnemy for practice mode
                    initiative=0,
                    current_hp=enemy_hp,
                    max_hp=enemy.stats.hit_points if hasattr(enemy, 'stats') else enemy_hp,
                    armor_class=enemy.stats.armor_class if hasattr(enemy, 'stats') else 10
                )
                session.participants.add(participant)
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{enemy_name} added to combat",
                    "participant": serializer.data
                })
            
            elif encounter_enemy_id:
                # Campaign mode: use EncounterEnemy
                try:
                    encounter_enemy = EncounterEnemy.objects.get(pk=encounter_enemy_id)
                except EncounterEnemy.DoesNotExist:
                    return Response(
                        {"error": "Encounter enemy not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if session.encounter and encounter_enemy.encounter != session.encounter:
                    return Response(
                        {"error": "Enemy must be from the same encounter"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                participant = CombatParticipant.objects.create(
                    combat_session=session,
                    participant_type='enemy',
                    encounter_enemy=encounter_enemy,
                    initiative=0,
                    current_hp=encounter_enemy.current_hp,
                    max_hp=encounter_enemy.enemy.stats.hit_points if hasattr(encounter_enemy.enemy, 'stats') else encounter_enemy.current_hp,
                    armor_class=encounter_enemy.enemy.stats.armor_class if hasattr(encounter_enemy.enemy, 'stats') else 10
                )
                session.participants.add(participant)
                
                serializer = CombatParticipantSerializer(participant)
                return Response({
                    "message": f"{encounter_enemy.name} added to combat",
                    "participant": serializer.data
                })
            else:
                return Response(
                    {"error": "Missing 'encounter_enemy_id' or 'enemy_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        else:
            return Response(
                {"error": "Invalid participant_type. Must be 'character' or 'enemy'"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove a participant from combat (before or during combat setup)"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        character_id = request.data.get('character_id')
        
        participant = None
        if participant_id:
            participant = session.participants.filter(pk=participant_id).first()
        elif character_id:
            participant = session.participants.filter(character_id=character_id).first()
        
        if not participant:
            return Response(
                {"error": "Participant not found in this combat session"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        name = participant.get_name()
        participant.delete()
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"{name} removed from combat",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def roll_initiative(self, request, pk=None):
        """Roll initiative for participants.
        
        Accepts optional 'overrides' dict: {participant_id: initiative_value}
        for manually set values. Auto-rolls (d20 + DEX mod) only for
        participants whose initiative is still 0 after applying overrides.
        """
        session = self.get_object()
        participants = session.participants.filter(is_active=True)
        
        if not participants.exists():
            return Response(
                {"error": "No participants in combat"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply manual overrides first
        overrides = request.data.get('overrides', {})
        for pid_str, value in overrides.items():
            try:
                pid = int(pid_str)
                val = int(value)
                if val != 0:
                    participant = participants.get(pk=pid)
                    participant.initiative = val
                    participant.save()
            except (ValueError, participants.model.DoesNotExist):
                continue
        
        # Re-fetch to get updated values
        participants = session.participants.filter(is_active=True)
        
        results = []
        for participant in participants:
            if participant.initiative != 0:
                # Already set manually — keep it
                results.append({
                    'participant_id': participant.id,
                    'name': participant.get_name(),
                    'roll': None,
                    'modifier': None,
                    'initiative': participant.initiative,
                    'source': 'manual',
                })
                continue
            
            # Auto-roll for this participant
            roll, _ = roll_d20()
            modifier = participant.get_ability_modifier('DEX')
            initiative = roll + modifier
            # Ensure we don't land on exactly 0 (would look unset)
            if initiative == 0:
                initiative = 1
            participant.initiative = initiative
            participant.save()
            results.append({
                'participant_id': participant.id,
                'name': participant.get_name(),
                'roll': roll,
                'modifier': modifier,
                'initiative': initiative,
                'source': 'auto',
            })
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Initiative rolled",
            "results": results,
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def next_turn(self, request, pk=None):
        """Advance to the next turn"""
        session = self.get_object()
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        next_participant = session.next_turn()
        if not next_participant:
            return Response(
                {"error": "No active participants"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(session)
        return Response({
            "message": f"Turn advanced to {next_participant.get_name()}",
            "session": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End the combat session"""
        session = self.get_object()
        
        if session.status == 'ended':
            return Response(
                {"error": "Combat is already ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save()
        
        # Generate combat log
        log = session.generate_log()
        
        serializer = self.get_serializer(session)
        return Response({
            "message": "Combat ended",
            "session": serializer.data,
            "log_id": log.id
        })
