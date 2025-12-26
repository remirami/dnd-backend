from rest_framework import serializers
from .models import CombatSession, CombatParticipant, CombatAction
from encounters.serializers import EncounterSerializer, EncounterEnemySerializer
from characters.serializers import CharacterSerializer
from bestiary.serializers import ConditionSerializer, DamageTypeSerializer


class CombatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for combat participants"""
    participant_type_display = serializers.CharField(source='get_participant_type_display', read_only=True)
    name = serializers.SerializerMethodField()
    character = CharacterSerializer(read_only=True, allow_null=True)
    encounter_enemy = EncounterEnemySerializer(read_only=True, allow_null=True)
    conditions = ConditionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CombatParticipant
        fields = "__all__"
    
    def get_name(self, obj):
        return obj.get_name()
    
    def to_representation(self, instance):
        """Add computed fields"""
        data = super().to_representation(instance)
        # Add death save status
        if instance.current_hp <= 0:
            data['death_save_status'] = {
                'successes': instance.death_save_successes,
                'failures': instance.death_save_failures,
                'is_stable': instance.death_save_successes >= 3,
                'is_dead': instance.death_save_failures >= 3
            }
        return data


class CombatActionSerializer(serializers.ModelSerializer):
    """Serializer for combat actions"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    damage_type = DamageTypeSerializer(read_only=True, allow_null=True)
    
    class Meta:
        model = CombatAction
        fields = "__all__"
    
    def get_actor_name(self, obj):
        return obj.actor.get_name() if obj.actor else None
    
    def get_target_name(self, obj):
        return obj.target.get_name() if obj.target else None


class CombatSessionSerializer(serializers.ModelSerializer):
    """Serializer for combat sessions"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    encounter = EncounterSerializer(read_only=True)
    encounter_id = serializers.IntegerField(write_only=True)
    participants = CombatParticipantSerializer(many=True, read_only=True)
    current_participant = serializers.SerializerMethodField()
    initiative_order = serializers.SerializerMethodField()
    actions = CombatActionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CombatSession
        fields = "__all__"
    
    def get_current_participant(self, obj):
        current = obj.get_current_participant()
        if current:
            return CombatParticipantSerializer(current).data
        return None
    
    def get_initiative_order(self, obj):
        order = obj.get_initiative_order()
        return CombatParticipantSerializer(order, many=True).data


class AttackRequestSerializer(serializers.Serializer):
    """Serializer for attack requests"""
    attacker_id = serializers.IntegerField()
    target_id = serializers.IntegerField()
    attack_name = serializers.CharField(required=False, allow_blank=True)
    advantage = serializers.BooleanField(default=False)
    disadvantage = serializers.BooleanField(default=False)
    other_modifiers = serializers.IntegerField(default=0)


class SpellRequestSerializer(serializers.Serializer):
    """Serializer for spell casting requests"""
    caster_id = serializers.IntegerField()
    target_id = serializers.IntegerField(required=False, allow_null=True)
    spell_name = serializers.CharField()
    spell_level = serializers.IntegerField(required=False, allow_null=True)
    save_type = serializers.CharField(required=False, allow_blank=True)  # STR, DEX, etc.
    save_dc = serializers.IntegerField(required=False, allow_null=True)
    damage_string = serializers.CharField(required=False, allow_blank=True)
    damage_type = serializers.IntegerField(required=False, allow_null=True)  # DamageType ID

