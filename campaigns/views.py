from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from .models import Campaign, CampaignCharacter, CampaignEncounter
from .serializers import (
    CampaignSerializer, CampaignCharacterSerializer, CampaignEncounterSerializer,
    ShortRestRequestSerializer, LongRestRequestSerializer
)
from encounters.models import Encounter
from characters.models import Character
from combat.models import CombatSession


class CampaignViewSet(viewsets.ModelViewSet):
    """API endpoint for managing campaigns"""
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter campaigns to only show those owned by the current user"""
        return Campaign.objects.filter(owner=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Automatically set the owner when creating a campaign"""
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start the campaign"""
        campaign = self.get_object()
        try:
            campaign.start()
            serializer = self.get_serializer(campaign)
            return Response({
                "message": "Campaign started",
                "campaign": serializer.data
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def add_character(self, request, pk=None):
        """Add a character to the campaign"""
        campaign = self.get_object()
        character_id = request.data.get('character_id')
        
        if not character_id:
            return Response(
                {"error": "character_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user can only add their own characters to campaigns
        try:
            character = Character.objects.get(pk=character_id, user=request.user)
        except Character.DoesNotExist:
            return Response(
                {"error": "Character not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character must have stats to join campaign"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already in campaign
        if CampaignCharacter.objects.filter(campaign=campaign, character=character).exists():
            return Response(
                {"error": "Character is already in this campaign"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate character has required attributes before creating
        if not hasattr(character, 'character_class'):
            return Response(
                {"error": "Character must have a character class to join campaign"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(character, 'stats') or not hasattr(character.stats, 'max_hit_points'):
            return Response(
                {"error": "Character must have stats with max_hit_points to join campaign"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create campaign character with initial values
        # We need to provide required fields, so we'll initialize first
        stats = character.stats
        campaign_char = CampaignCharacter(
            campaign=campaign,
            character=character,
            current_hp=stats.max_hit_points,  # Temporary, will be set properly in initialize_from_character
            max_hp=stats.max_hit_points  # Temporary, will be set properly in initialize_from_character
        )
        # Now initialize properly (this will set all fields correctly)
        campaign_char.initialize_from_character()
        
        serializer = CampaignCharacterSerializer(campaign_char)
        return Response({
            "message": f"{character.name} added to campaign",
            "campaign_character": serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def remove_character(self, request, pk=None):
        """Remove a character from the campaign"""
        campaign = self.get_object()
        character_id = request.data.get('character_id')
        
        if not character_id:
            return Response(
                {"error": "character_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            campaign_char = CampaignCharacter.objects.get(
                campaign=campaign,
                character_id=character_id
            )
            character_name = campaign_char.character.name
            campaign_char.delete()
            return Response({
                "message": f"{character_name} removed from campaign"
            })
        except CampaignCharacter.DoesNotExist:
            return Response(
                {"error": "Character not found in campaign"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def add_encounter(self, request, pk=None):
        """Add an encounter to the campaign"""
        campaign = self.get_object()
        encounter_id = request.data.get('encounter_id')
        
        if not encounter_id:
            return Response(
                {"error": "encounter_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            encounter = Encounter.objects.get(pk=encounter_id)
        except Encounter.DoesNotExist:
            return Response(
                {"error": "Encounter not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get next encounter number
        next_number = campaign.campaign_encounters.count() + 1
        
        campaign_encounter = CampaignEncounter.objects.create(
            campaign=campaign,
            encounter=encounter,
            encounter_number=next_number
        )
        
        serializer = CampaignEncounterSerializer(campaign_encounter)
        return Response({
            "message": f"Encounter {next_number} added to campaign",
            "campaign_encounter": serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def current_encounter(self, request, pk=None):
        """Get the current encounter"""
        campaign = self.get_object()
        encounter = campaign.get_current_encounter()
        
        if not encounter:
            return Response(
                {"error": "No current encounter. Campaign may be completed or have no encounters."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CampaignEncounterSerializer(encounter)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_encounter(self, request, pk=None):
        """Start the current encounter"""
        campaign = self.get_object()
        
        if campaign.status != 'active':
            return Response(
                {"error": "Campaign must be active to start encounters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        encounter = campaign.get_current_encounter()
        if not encounter:
            return Response(
                {"error": "No current encounter available"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            encounter.start()
            serializer = CampaignEncounterSerializer(encounter)
            return Response({
                "message": f"Encounter {encounter.encounter_number} started",
                "campaign_encounter": serializer.data
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete_encounter(self, request, pk=None):
        """Complete the current encounter"""
        campaign = self.get_object()
        encounter = campaign.get_current_encounter()
        
        if not encounter:
            return Response(
                {"error": "No current encounter"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if encounter.status != 'active':
            return Response(
                {"error": "Encounter must be active to complete"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        combat_session_id = request.data.get('combat_session_id')
        rewards = request.data.get('rewards', {})
        
        combat_session = None
        if combat_session_id:
            try:
                combat_session = CombatSession.objects.get(pk=combat_session_id)
            except CombatSession.DoesNotExist:
                return Response(
                    {"error": "Combat session not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        try:
            encounter.complete(combat_session=combat_session, rewards=rewards)
            serializer = CampaignEncounterSerializer(encounter)
            return Response({
                "message": f"Encounter {encounter.encounter_number} completed",
                "campaign_encounter": serializer.data,
                "campaign_status": campaign.status
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def fail_encounter(self, request, pk=None):
        """Mark encounter as failed (all characters died)"""
        campaign = self.get_object()
        encounter = campaign.get_current_encounter()
        
        if not encounter:
            return Response(
                {"error": "No current encounter"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        encounter.fail()
        serializer = self.get_serializer(campaign)
        return Response({
            "message": "Encounter failed. Campaign ended.",
            "campaign": serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def short_rest(self, request, pk=None):
        """Take a short rest"""
        campaign = self.get_object()
        
        if not campaign.can_take_short_rest():
            return Response(
                {"error": "Cannot take short rest at this time"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ShortRestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        character_ids = data.get('character_ids', [])
        hit_dice_to_spend = data.get('hit_dice_to_spend', {})
        
        # Get characters to rest
        if character_ids:
            characters = campaign.campaign_characters.filter(
                id__in=character_ids,
                is_alive=True
            )
        else:
            characters = campaign.get_alive_characters()
        
        if not characters.exists():
            return Response(
                {"error": "No alive characters to rest"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        total_healing = 0
        
        with transaction.atomic():
            for char in characters:
                # Determine how many hit dice to spend
                if char.id in hit_dice_to_spend:
                    dice_to_spend = hit_dice_to_spend[char.id]
                else:
                    dice_to_spend = 1  # Default: spend 1 hit die
                
                # Spend hit dice
                healing_done = 0
                messages = []
                for _ in range(min(dice_to_spend, char.get_available_hit_dice())):
                    healing, message = char.spend_hit_die()
                    healing_done += healing
                    messages.append(message)
                
                results.append({
                    "character_id": char.id,
                    "character_name": char.character.name,
                    "healing": healing_done,
                    "hit_dice_spent": min(dice_to_spend, char.get_available_hit_dice()),
                    "messages": messages,
                    "current_hp": char.current_hp,
                    "max_hp": char.max_hp,
                    "remaining_hit_dice": char.get_available_hit_dice()
                })
                total_healing += healing_done
            
            campaign.short_rests_used += 1
            campaign.save()
        
        return Response({
            "message": "Short rest completed",
            "total_healing": total_healing,
            "short_rests_used": campaign.short_rests_used,
            "characters": results
        })
    
    @action(detail=True, methods=['post'])
    def long_rest(self, request, pk=None):
        """Take a long rest"""
        campaign = self.get_object()
        
        if not campaign.can_take_long_rest():
            return Response(
                {"error": "Cannot take long rest. Either campaign is not active, no alive characters, or no long rests remaining."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LongRestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if not serializer.validated_data.get('confirm'):
            return Response(
                {"error": "Must confirm long rest"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        characters = campaign.get_alive_characters()
        if not characters.exists():
            return Response(
                {"error": "No alive characters to rest"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        
        with transaction.atomic():
            for char in characters:
                # Full HP recovery
                old_hp = char.current_hp
                char.current_hp = char.max_hp
                
                # Restore all hit dice
                char.restore_all_hit_dice()
                
                # TODO: Restore spell slots (would need class-specific logic)
                # For now, we'll leave spell slots as-is
                
                char.save()
                
                results.append({
                    "character_id": char.id,
                    "character_name": char.character.name,
                    "hp_restored": char.max_hp - old_hp,
                    "current_hp": char.current_hp,
                    "max_hp": char.max_hp,
                    "hit_dice_restored": char.get_available_hit_dice()
                })
            
            campaign.long_rests_used += 1
            campaign.save()
        
        return Response({
            "message": "Long rest completed",
            "long_rests_used": campaign.long_rests_used,
            "long_rests_remaining": campaign.long_rests_available - campaign.long_rests_used,
            "characters": results
        })
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get full campaign status"""
        campaign = self.get_object()
        serializer = self.get_serializer(campaign)
        
        # Add detailed party status
        party_status = []
        for char in campaign.get_alive_characters():
            party_status.append({
                "id": char.id,
                "character": char.character.name,
                "current_hp": char.current_hp,
                "max_hp": char.max_hp,
                "hp_percentage": round((char.current_hp / char.max_hp) * 100, 1) if char.max_hp > 0 else 0,
                "hit_dice_remaining": char.hit_dice_remaining,
                "available_hit_dice": char.get_available_hit_dice(),
                "spell_slots": char.spell_slots,
                "is_alive": char.is_alive
            })
        
        return Response({
            "campaign": serializer.data,
            "party_status": party_status,
            "can_short_rest": campaign.can_take_short_rest(),
            "can_long_rest": campaign.can_take_long_rest()
        })
    
    @action(detail=True, methods=['get'])
    def party_status(self, request, pk=None):
        """Get party status (HP, resources)"""
        campaign = self.get_object()
        party_status = []
        
        for char in campaign.get_alive_characters():
            party_status.append({
                "id": char.id,
                "character": char.character.name,
                "level": char.character.level,
                "class": char.character.character_class.get_name_display(),
                "current_hp": char.current_hp,
                "max_hp": char.max_hp,
                "hp_percentage": round((char.current_hp / char.max_hp) * 100, 1) if char.max_hp > 0 else 0,
                "hit_dice_remaining": char.hit_dice_remaining,
                "available_hit_dice": char.get_available_hit_dice(),
                "spell_slots": char.spell_slots,
                "is_alive": char.is_alive
            })
        
        return Response({
            "party": party_status,
            "total_characters": len(party_status),
            "short_rests_used": campaign.short_rests_used,
            "long_rests_used": campaign.long_rests_used,
            "long_rests_remaining": campaign.long_rests_available - campaign.long_rests_used
        })
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End the campaign (manually)"""
        campaign = self.get_object()
        
        if campaign.status not in ['active', 'preparing']:
            return Response(
                {"error": "Campaign is already ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'manual')
        campaign.status = 'completed' if reason == 'victory' else 'failed'
        campaign.ended_at = timezone.now()
        campaign.save()
        
        serializer = self.get_serializer(campaign)
        return Response({
            "message": f"Campaign ended: {reason}",
            "campaign": serializer.data
        })


class CampaignCharacterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing campaign characters"""
    serializer_class = CampaignCharacterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter to only show campaign characters from campaigns owned by the user"""
        queryset = CampaignCharacter.objects.filter(campaign__owner=self.request.user)
        campaign_id = self.request.query_params.get('campaign', None)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id, campaign__owner=self.request.user)
        return queryset


class CampaignEncounterViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing campaign encounters"""
    serializer_class = CampaignEncounterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter to only show campaign encounters from campaigns owned by the user"""
        queryset = CampaignEncounter.objects.filter(campaign__owner=self.request.user)
        campaign_id = self.request.query_params.get('campaign', None)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id, campaign__owner=self.request.user)
        return queryset
