from rest_framework import serializers
from .models import Campaign, CampaignCharacter, CampaignEncounter
from characters.serializers import CharacterSerializer
from encounters.serializers import EncounterSerializer
from combat.serializers import CombatSessionSerializer


class CampaignCharacterSerializer(serializers.ModelSerializer):
    """Serializer for campaign character"""
    character = CharacterSerializer(read_only=True)
    character_id = serializers.IntegerField(write_only=True)
    hit_dice_remaining_display = serializers.SerializerMethodField()
    available_hit_dice = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignCharacter
        fields = '__all__'
    
    def get_hit_dice_remaining_display(self, obj):
        """Format hit dice as readable string"""
        if not obj.hit_dice_remaining:
            return "None"
        parts = [f"{count}{dice_type}" for dice_type, count in obj.hit_dice_remaining.items()]
        return ", ".join(parts)
    
    def get_available_hit_dice(self, obj):
        """Get total available hit dice"""
        return obj.get_available_hit_dice()


class CampaignEncounterSerializer(serializers.ModelSerializer):
    """Serializer for campaign encounter"""
    encounter = EncounterSerializer(read_only=True)
    encounter_id = serializers.IntegerField(write_only=True)
    combat_session = CombatSessionSerializer(read_only=True)
    
    class Meta:
        model = CampaignEncounter
        fields = '__all__'


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for campaign"""
    campaign_characters = CampaignCharacterSerializer(many=True, read_only=True)
    campaign_encounters = CampaignEncounterSerializer(many=True, read_only=True)
    current_encounter = serializers.SerializerMethodField()
    alive_characters_count = serializers.SerializerMethodField()
    can_short_rest = serializers.SerializerMethodField()
    can_long_rest = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = '__all__'
    
    def get_current_encounter(self, obj):
        """Get current encounter"""
        encounter = obj.get_current_encounter()
        if encounter:
            return CampaignEncounterSerializer(encounter).data
        return None
    
    def get_alive_characters_count(self, obj):
        """Get count of alive characters"""
        return obj.get_alive_characters().count()
    
    def get_can_short_rest(self, obj):
        """Check if can take short rest"""
        return obj.can_take_short_rest()
    
    def get_can_long_rest(self, obj):
        """Check if can take long rest"""
        return obj.can_take_long_rest()


class ShortRestRequestSerializer(serializers.Serializer):
    """Serializer for short rest request"""
    character_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of character IDs to use hit dice. If empty, all characters use available dice."
    )
    hit_dice_to_spend = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="Dict mapping character_id to number of hit dice to spend. If not provided, each character spends 1."
    )


class LongRestRequestSerializer(serializers.Serializer):
    """Serializer for long rest request"""
    confirm = serializers.BooleanField(
        required=True,
        help_text="Must be True to confirm long rest"
    )

