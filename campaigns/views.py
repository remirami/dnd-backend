from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from .models import Campaign, CampaignCharacter, CampaignEncounter, CharacterXP, TreasureRoom, TreasureRoomReward, RecruitableCharacter, RecruitmentRoom
from .serializers import (
    CampaignSerializer, CampaignCharacterSerializer, CampaignEncounterSerializer,
    ShortRestRequestSerializer, LongRestRequestSerializer, TreasureRoomSerializer,
    RecruitableCharacterSerializer, RecruitmentRoomSerializer
)
from .utils import grant_encounter_xp, TreasureGenerator, RecruitmentGenerator, CampaignGenerator
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
    def populate(self, request, pk=None):
        """Auto-populate campaign with random encounters and treasures"""
        campaign = self.get_object()
        
        if campaign.status != 'preparing':
            return Response(
                {"error": "Campaign must be in 'preparing' status to populate"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        num_encounters = request.data.get('num_encounters', 5)
        auto_treasure = request.data.get('auto_treasure', True)
        
        try:
            summary = CampaignGenerator.populate_campaign(
                campaign,
                num_encounters=int(num_encounters),
                auto_treasure=bool(auto_treasure)
            )
            
            return Response({
                "message": "Campaign populated successfully",
                "summary": summary
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to populate campaign: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
            
            # Grant XP to all characters
            characters = campaign.get_alive_characters()
            xp_results = grant_encounter_xp(encounter, characters)
            
            # Check if treasure room should be generated (every 2-3 encounters, or random 20% chance)
            treasure_room = None
            import random
            should_generate_treasure = (
                encounter.encounter_number % 3 == 0 or  # Every 3rd encounter
                random.random() < 0.2  # 20% random chance
            )
            
            if should_generate_treasure and encounter.encounter_number < campaign.total_encounters:
                treasure_room = TreasureGenerator.generate_treasure_room(
                    campaign,
                    encounter.encounter_number
                )
            
            # Check if recruitment room should be generated (solo mode only, every 3-5 encounters)
            recruitment_room = None
            if campaign.start_mode == 'solo' and campaign.get_alive_characters().count() < 4:
                should_generate_recruitment = (
                    encounter.encounter_number % 4 == 0 or  # Every 4th encounter
                    (random.random() < 0.15 and encounter.encounter_number >= 3)  # 15% chance after encounter 3
                )
                
                if should_generate_recruitment and encounter.encounter_number < campaign.total_encounters:
                    try:
                        recruitment_room = RecruitmentGenerator.generate_recruitment_room(
                            campaign,
                            encounter.encounter_number
                        )
                    except ValueError as e:
                        # Silently fail if recruitment can't be generated (e.g., party already full)
                        pass
            
            serializer = CampaignEncounterSerializer(encounter)
            response_data = {
                "message": f"Encounter {encounter.encounter_number} completed",
                "campaign_encounter": serializer.data,
                "campaign_status": campaign.status,
                "xp_rewards": xp_results
            }
            
            if treasure_room:
                response_data["treasure_room"] = TreasureRoomSerializer(treasure_room).data
                response_data["message"] += " - Treasure room discovered!"
            
            if recruitment_room:
                response_data["recruitment_room"] = RecruitmentRoomSerializer(recruitment_room).data
                response_data["message"] += " - Recruitment room discovered!"
            
            return Response(response_data)
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
            xp_info = {}
            if hasattr(char, 'xp_tracking'):
                xp_tracking = char.xp_tracking
                xp_info = {
                    "current_xp": xp_tracking.current_xp,
                    "total_xp_gained": xp_tracking.total_xp_gained,
                    "level_ups_gained": xp_tracking.level_ups_gained,
                }
            
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
                "is_alive": char.is_alive,
                **xp_info
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
    
    @action(detail=True, methods=['get'])
    def treasure_rooms(self, request, pk=None):
        """Get all treasure rooms for this campaign"""
        campaign = self.get_object()
        rooms = campaign.treasure_rooms.all()
        serializer = TreasureRoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def discover_treasure_room(self, request, pk=None):
        """Manually discover a treasure room (for testing or special cases)"""
        campaign = self.get_object()
        encounter_number = request.data.get('encounter_number')
        
        if not encounter_number:
            return Response(
                {"error": "encounter_number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if room already exists
        existing_room = TreasureRoom.objects.filter(
            campaign=campaign,
            encounter_number=encounter_number
        ).first()
        
        if existing_room:
            if existing_room.discovered:
                return Response(
                    {"error": "Treasure room already discovered"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            existing_room.discover()
            serializer = TreasureRoomSerializer(existing_room)
            return Response({
                "message": "Treasure room discovered",
                "treasure_room": serializer.data
            })
        else:
            # Generate new treasure room
            treasure_room = TreasureGenerator.generate_treasure_room(
                campaign,
                encounter_number
            )
            treasure_room.discover()
            serializer = TreasureRoomSerializer(treasure_room)
            return Response({
                "message": "Treasure room discovered",
                "treasure_room": serializer.data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def claim_treasure(self, request, pk=None):
        """Claim individual rewards from a treasure room"""
        campaign = self.get_object()
        reward_id = request.data.get('reward_id')  # Individual reward ID
        character_id = request.data.get('character_id')
        
        if not reward_id:
            return Response(
                {"error": "reward_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not character_id:
            return Response(
                {"error": "character_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reward = TreasureRoomReward.objects.get(
                pk=reward_id,
                treasure_room__campaign=campaign
            )
        except TreasureRoomReward.DoesNotExist:
            return Response(
                {"error": "Reward not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        treasure_room = reward.treasure_room
        
        if not treasure_room.discovered:
            return Response(
                {"error": "Treasure room not discovered yet"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reward.claimed_by:
            return Response(
                {"error": "This reward has already been claimed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            campaign_char = CampaignCharacter.objects.get(
                pk=character_id,
                campaign=campaign,
                is_alive=True
            )
        except CampaignCharacter.DoesNotExist:
            return Response(
                {"error": "Character not found or not alive in this campaign"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Claim the reward
        claim_result = reward.claim(campaign_char)
        
        # Handle XP bonus if applicable
        if reward.xp_bonus > 0:
            xp_tracking, created = CharacterXP.objects.get_or_create(
                campaign_character=campaign_char
            )
            xp_result = xp_tracking.add_xp(reward.xp_bonus, source="treasure_room")
            claim_result['xp_gained'] = reward.xp_bonus
            claim_result['xp_result'] = xp_result
        
        # Check if all rewards are claimed
        unclaimed_count = treasure_room.reward_items.filter(claimed_by__isnull=True).count()
        if unclaimed_count == 0:
            treasure_room.loot_distributed = True
            treasure_room.save()
        
        return Response({
            "message": "Reward claimed successfully",
            "reward": claim_result,
            "remaining_unclaimed": unclaimed_count - 1
        })
    
    @action(detail=True, methods=['get'])
    def treasure_room_rewards(self, request, pk=None):
        """Get all rewards (claimed and unclaimed) for a treasure room"""
        campaign = self.get_object()
        room_id = request.query_params.get('room_id')
        
        if not room_id:
            return Response(
                {"error": "room_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            treasure_room = TreasureRoom.objects.get(
                pk=room_id,
                campaign=campaign
            )
        except TreasureRoom.DoesNotExist:
            return Response(
                {"error": "Treasure room not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        rewards = treasure_room.reward_items.all()
        from .serializers import TreasureRoomRewardSerializer
        serializer = TreasureRoomRewardSerializer(rewards, many=True)
        
        return Response({
            "treasure_room_id": room_id,
            "rewards": serializer.data,
            "unclaimed_count": rewards.filter(claimed_by__isnull=True).count()
        })
    
    @action(detail=True, methods=['post'])
    def grant_xp(self, request, pk=None):
        """Manually grant XP to characters (for testing or special rewards)"""
        campaign = self.get_object()
        character_ids = request.data.get('character_ids', [])
        xp_amount = request.data.get('xp_amount', 0)
        source = request.data.get('source', 'manual')
        
        if not xp_amount or xp_amount <= 0:
            return Response(
                {"error": "xp_amount must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if character_ids:
            characters = campaign.campaign_characters.filter(
                id__in=character_ids,
                is_alive=True
            )
        else:
            characters = campaign.get_alive_characters()
        
        if not characters.exists():
            return Response(
                {"error": "No alive characters to grant XP to"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {
            'characters': [],
            'total_xp_granted': 0,
            'levels_gained': 0
        }
        
        xp_per_character = xp_amount // characters.count()
        
        for campaign_char in characters:
            xp_tracking, created = CharacterXP.objects.get_or_create(
                campaign_character=campaign_char
            )
            
            old_level = campaign_char.character.level
            result = xp_tracking.add_xp(xp_per_character, source=source)
            new_level = campaign_char.character.level
            
            level_gained = new_level > old_level
            if level_gained:
                results['levels_gained'] += (new_level - old_level)
            
            results['characters'].append({
                'character_id': campaign_char.id,
                'character_name': campaign_char.character.name,
                'xp_gained': xp_per_character,
                'total_xp': xp_tracking.current_xp,
                'level': new_level,
                'level_gained': level_gained,
            })
            
            results['total_xp_granted'] += xp_per_character
        
        return Response({
            "message": f"Granted {xp_amount} XP total",
            "results": results
        })
    
    @action(detail=True, methods=['get'])
    def recruitment_rooms(self, request, pk=None):
        """Get all recruitment rooms for this campaign"""
        campaign = self.get_object()
        rooms = campaign.recruitment_rooms.all()
        serializer = RecruitmentRoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def discover_recruitment_room(self, request, pk=None):
        """Manually discover a recruitment room (for testing or special cases)"""
        campaign = self.get_object()
        encounter_number = request.data.get('encounter_number')
        
        if campaign.start_mode != 'solo':
            return Response(
                {"error": "Recruitment rooms are only available in solo mode"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not encounter_number:
            return Response(
                {"error": "encounter_number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if room already exists
        existing_room = RecruitmentRoom.objects.filter(
            campaign=campaign,
            encounter_number=encounter_number
        ).first()
        
        if existing_room:
            if existing_room.discovered:
                return Response(
                    {"error": "Recruitment room already discovered"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            existing_room.discover()
            serializer = RecruitmentRoomSerializer(existing_room)
            return Response({
                "message": "Recruitment room discovered",
                "recruitment_room": serializer.data
            })
        else:
            # Generate new recruitment room
            try:
                recruitment_room = RecruitmentGenerator.generate_recruitment_room(
                    campaign,
                    encounter_number
                )
                recruitment_room.discover()
                serializer = RecruitmentRoomSerializer(recruitment_room)
                return Response({
                    "message": "Recruitment room discovered",
                    "recruitment_room": serializer.data
                }, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
    
    @action(detail=True, methods=['get'])
    def recruitment_room_available(self, request, pk=None):
        """Get available recruits for a recruitment room"""
        campaign = self.get_object()
        room_id = request.query_params.get('room_id')
        
        if not room_id:
            return Response(
                {"error": "room_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recruitment_room = RecruitmentRoom.objects.get(
                pk=room_id,
                campaign=campaign
            )
        except RecruitmentRoom.DoesNotExist:
            return Response(
                {"error": "Recruitment room not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RecruitmentRoomSerializer(recruitment_room)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def recruit_character(self, request, pk=None):
        """Recruit a character from a recruitment room"""
        campaign = self.get_object()
        room_id = request.data.get('room_id')
        recruit_template_id = request.data.get('recruit_template_id')
        
        if campaign.start_mode != 'solo':
            return Response(
                {"error": "Recruitment is only available in solo mode"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not room_id:
            return Response(
                {"error": "room_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not recruit_template_id:
            return Response(
                {"error": "recruit_template_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recruitment_room = RecruitmentRoom.objects.get(
                pk=room_id,
                campaign=campaign
            )
        except RecruitmentRoom.DoesNotExist:
            return Response(
                {"error": "Recruitment room not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not recruitment_room.discovered:
            return Response(
                {"error": "Recruitment room not discovered yet"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if recruitment_room.recruit_selected:
            return Response(
                {"error": "A recruit has already been selected from this room"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the recruit template is available in this room
        try:
            recruit_template = recruitment_room.available_recruits.get(pk=recruit_template_id)
        except RecruitableCharacter.DoesNotExist:
            return Response(
                {"error": "Recruit template not found in this recruitment room"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            campaign_char = RecruitmentGenerator.recruit_character(
                campaign,
                recruitment_room,
                recruit_template
            )
            
            serializer = CampaignCharacterSerializer(campaign_char)
            return Response({
                "message": f"{campaign_char.character.name} recruited successfully",
                "campaign_character": serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def apply_asi(self, request, pk=None):
        """
        Apply Ability Score Improvement (ASI) or Feat for a character
        
        Request body for ASI:
        {
            "character_id": 1,
            "level": 4,
            "choice_type": "asi",
            "asi_choice": {
                "strength": 2  // +2 to one stat
                // OR
                "strength": 1, "dexterity": 1  // +1 to two stats
            }
        }
        
        Request body for Feat:
        {
            "character_id": 1,
            "level": 4,
            "choice_type": "feat",
            "feat_id": 5  // ID of the feat to take
        }
        """
        campaign = self.get_object()
        character_id = request.data.get('character_id')
        level = request.data.get('level')
        choice_type = request.data.get('choice_type', 'asi')  # 'asi' or 'feat'
        
        if not character_id or not level:
            return Response(
                {"error": "character_id and level are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get campaign character
            campaign_char = CampaignCharacter.objects.get(
                campaign=campaign,
                id=character_id
            )
            
            # Get XP tracking
            xp_tracking = CharacterXP.objects.get(campaign_character=campaign_char)
            
            # Check if this level has pending ASI
            if level not in xp_tracking.pending_asi_levels:
                return Response(
                    {"error": f"No pending ASI/Feat choice for level {level}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            character = campaign_char.character
            
            if choice_type == 'feat':
                # Handle feat selection
                from characters.models import Feat, CharacterFeat, CharacterFeature
                
                feat_id = request.data.get('feat_id')
                if not feat_id:
                    return Response(
                        {"error": "feat_id is required when choice_type is 'feat'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    feat = Feat.objects.get(pk=feat_id)
                except Feat.DoesNotExist:
                    return Response(
                        {"error": f"Feat with id {feat_id} not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Check prerequisites
                is_eligible, reason = feat.check_prerequisites(character)
                if not is_eligible:
                    return Response(
                        {"error": f"Feat prerequisites not met: {reason}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if character already has this feat
                if CharacterFeat.objects.filter(character=character, feat=feat).exists():
                    return Response(
                        {"error": f"Character already has the feat: {feat.name}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Apply feat
                CharacterFeat.objects.create(
                    character=character,
                    feat=feat,
                    level_taken=level
                )
                
                # Create CharacterFeature instance
                CharacterFeature.objects.create(
                    character=character,
                    name=feat.name,
                    feature_type='feat',
                    description=feat.description,
                    source=f"Feat (Level {level})"
                )
                
                # Apply ability score increase if feat grants one
                if feat.ability_score_increase:
                    stats = character.stats
                    ability_lower = feat.ability_score_increase.lower()
                    current_value = getattr(stats, ability_lower)
                    new_value = min(20, current_value + 1)  # Cap at 20
                    setattr(stats, ability_lower, new_value)
                    stats.save()
                
                # Remove this level from pending ASI
                xp_tracking.pending_asi_levels.remove(level)
                xp_tracking.save()
                
                return Response({
                    "message": f"Feat '{feat.name}' applied successfully for level {level}",
                    "feat": {
                        "id": feat.id,
                        "name": feat.name,
                        "description": feat.description
                    },
                    "remaining_pending_asi": xp_tracking.pending_asi_levels,
                    "ability_score_increase": feat.ability_score_increase if feat.ability_score_increase else None
                })
            
            else:
                # Handle ASI selection
                asi_choice = request.data.get('asi_choice', {})
                
                if not asi_choice:
                    return Response(
                        {"error": "asi_choice is required when choice_type is 'asi'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate ASI choice
                total_increase = sum(asi_choice.values())
                if total_increase != 2:
                    return Response(
                        {"error": "ASI must total +2 (either +2 to one stat or +1 to two stats)"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if len(asi_choice) > 2:
                    return Response(
                        {"error": "Can only increase 1 or 2 different abilities"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                for ability, increase in asi_choice.items():
                    if ability.lower() not in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                        return Response(
                            {"error": f"Invalid ability: {ability}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    if increase not in [1, 2]:
                        return Response(
                            {"error": "Each ability can only increase by 1 or 2"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Apply ASI
                stats = character.stats
                
                for ability, increase in asi_choice.items():
                    ability_lower = ability.lower()
                    current_value = getattr(stats, ability_lower)
                    new_value = min(20, current_value + increase)  # Cap at 20
                    setattr(stats, ability_lower, new_value)
                
                stats.save()
                
                # Remove this level from pending ASI
                xp_tracking.pending_asi_levels.remove(level)
                xp_tracking.save()
                
                return Response({
                    "message": f"ASI applied successfully for level {level}",
                    "asi_applied": asi_choice,
                    "remaining_pending_asi": xp_tracking.pending_asi_levels,
                    "new_stats": {
                        "strength": stats.strength,
                        "dexterity": stats.dexterity,
                        "constitution": stats.constitution,
                        "intelligence": stats.intelligence,
                        "wisdom": stats.wisdom,
                        "charisma": stats.charisma
                    }
                })
            
        except CampaignCharacter.DoesNotExist:
            return Response(
                {"error": "Campaign character not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except CharacterXP.DoesNotExist:
            return Response(
                {"error": "XP tracking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to apply ASI/Feat: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def select_subclass(self, request, pk=None):
        """
        Select subclass for a character
        
        Request body:
        {
            "character_id": 1,
            "subclass": "Champion"  // or "Battle Master", "College of Lore", etc.
        }
        """
        campaign = self.get_object()
        character_id = request.data.get('character_id')
        subclass = request.data.get('subclass')
        
        if not character_id or not subclass:
            return Response(
                {"error": "character_id and subclass are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get campaign character
            campaign_char = CampaignCharacter.objects.get(
                campaign=campaign,
                id=character_id
            )
            
            # Get XP tracking
            xp_tracking = CharacterXP.objects.get(campaign_character=campaign_char)
            
            # Check if subclass selection is pending
            if not xp_tracking.pending_subclass_selection:
                return Response(
                    {"error": "No pending subclass selection"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if character already has a subclass
            character = campaign_char.character
            if character.subclass:
                return Response(
                    {"error": f"Character already has subclass: {character.subclass}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set subclass
            character.subclass = subclass
            character.save()
            
            # Clear pending flag
            xp_tracking.pending_subclass_selection = False
            xp_tracking.save()
            
            # Apply subclass features retroactively for current level
            from characters.models import CharacterFeature
            from .class_features_data import get_subclass_features
            
            features_applied = []
            current_level = character.level
            
            # Determine when subclass features start
            subclass_levels = {
                'cleric': 1,
                'druid': 2,
                'wizard': 2,
                'sorcerer': 1,
                'warlock': 1,
            }
            start_level = subclass_levels.get(character.character_class.name, 3)
            
            # Apply all subclass features from start_level to current level
            for level in range(start_level, current_level + 1):
                subclass_features = get_subclass_features(subclass, level)
                
                for feature_data in subclass_features:
                    CharacterFeature.objects.create(
                        character=character,
                        name=feature_data['name'],
                        feature_type='class',
                        description=feature_data['description'],
                        source=f"{subclass} Level {level}"
                    )
                    
                    features_applied.append({
                        'level': level,
                        'name': feature_data['name']
                    })
            
            return Response({
                "message": f"Subclass selected successfully: {subclass}",
                "character": {
                    "id": character.id,
                    "name": character.name,
                    "class": character.character_class.name,
                    "subclass": character.subclass,
                    "level": character.level
                },
                "features_applied": features_applied
            })
            
        except CampaignCharacter.DoesNotExist:
            return Response(
                {"error": "Campaign character not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except CharacterXP.DoesNotExist:
            return Response(
                {"error": "XP tracking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to select subclass: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
