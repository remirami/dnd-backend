from rest_framework import serializers
from .models import CombatSession, CombatParticipant, CombatAction, CombatLog, EnvironmentalEffect, ParticipantPosition
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
        
        # Add equipped items info for characters
        if instance.character:
            equipped_weapon = instance.get_equipped_weapon()
            equipped_armor = instance.get_equipped_armor()
            equipped_shield = instance.get_equipped_shield()
            effective_ac = instance.calculate_effective_ac()
            
            data['equipped_items'] = {
                'weapon': {
                    'name': equipped_weapon.name,
                    'damage_dice': equipped_weapon.damage_dice,
                } if equipped_weapon else None,
                'armor': {
                    'name': equipped_armor.name,
                    'base_ac': equipped_armor.base_ac,
                } if equipped_armor else None,
                'shield': {
                    'name': equipped_shield.name,
                    'ac_bonus': equipped_shield.base_ac,
                } if equipped_shield else None,
            }
            data['effective_ac'] = effective_ac
        
        # Add enemy stat block for enemy participants
        enemy = None
        if instance.encounter_enemy:
            enemy = instance.encounter_enemy.enemy
        elif instance.participant_type == 'enemy' and instance.name:
            # Practice mode enemy — try to find by name
            from bestiary.models import Enemy as EnemyModel
            enemy = EnemyModel.objects.filter(name=instance.name).first()
        
        if enemy:
            # Ability scores
            if hasattr(enemy, 'stats'):
                stats = enemy.stats
                data['enemy_stats'] = {
                    'ability_scores': {
                        'strength': {'score': stats.strength, 'modifier': stats.strength_modifier},
                        'dexterity': {'score': stats.dexterity, 'modifier': stats.dexterity_modifier},
                        'constitution': {'score': stats.constitution, 'modifier': stats.constitution_modifier},
                        'intelligence': {'score': stats.intelligence, 'modifier': stats.intelligence_modifier},
                        'wisdom': {'score': stats.wisdom, 'modifier': stats.wisdom_modifier},
                        'charisma': {'score': stats.charisma, 'modifier': stats.charisma_modifier},
                    },
                    'saving_throws': {
                        'str': stats.str_save,
                        'dex': stats.dex_save,
                        'con': stats.con_save,
                        'int': stats.int_save,
                        'wis': stats.wis_save,
                        'cha': stats.cha_save,
                    },
                    'speed': stats.speed,
                    'proficiency_bonus': stats.proficiency_bonus,
                    'senses': {
                        'darkvision': stats.darkvision,
                        'blindsight': stats.blindsight,
                        'tremorsense': stats.tremorsense,
                        'truesight': stats.truesight,
                        'passive_perception': stats.passive_perception,
                    },
                }
            
            # Attacks
            attacks = enemy.attacks.all()
            if attacks.exists():
                data['enemy_attacks'] = [
                    {
                        'name': atk.name,
                        'bonus': atk.bonus,
                        'damage': atk.damage,
                    }
                    for atk in attacks
                ]
            
            # Abilities (Multiattack, special traits, etc.)
            abilities = enemy.abilities.all()
            if abilities.exists():
                data['enemy_abilities'] = [
                    {
                        'name': ab.name,
                        'description': ab.description,
                    }
                    for ab in abilities
                ]
            
            # Resistances/immunities
            resistances = enemy.resistances.all()
            if resistances.exists():
                data['enemy_resistances'] = [
                    {
                        'damage_type': r.damage_type.name,
                        'type': r.resistance_type,
                    }
                    for r in resistances
                ]
        
        return data


class CombatActionSerializer(serializers.ModelSerializer):
    """Serializer for combat actions"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    is_ai = serializers.SerializerMethodField()
    damage_type = DamageTypeSerializer(read_only=True, allow_null=True)
    
    class Meta:
        model = CombatAction
        fields = "__all__"
    
    def get_actor_name(self, obj):
        return obj.actor.get_name() if obj.actor else None
    
    def get_target_name(self, obj):
        return obj.target.get_name() if obj.target else None
    
    def get_is_ai(self, obj):
        return obj.actor.participant_type == 'enemy' if obj.actor else False


class CombatSessionSerializer(serializers.ModelSerializer):
    """Serializer for combat sessions"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    encounter = EncounterSerializer(read_only=True, allow_null=True)
    encounter_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
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


class CombatLogSerializer(serializers.ModelSerializer):
    """Serializer for combat logs"""
    combat_session = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = CombatLog
        fields = '__all__'


class EnvironmentalEffectSerializer(serializers.ModelSerializer):
    """Serializer for environmental effects"""
    effect_type_display = serializers.CharField(source='get_effect_type_display', read_only=True)
    terrain_type_display = serializers.CharField(source='get_terrain_type_display', read_only=True, allow_null=True)
    cover_type_display = serializers.CharField(source='get_cover_type_display', read_only=True, allow_null=True)
    lighting_type_display = serializers.CharField(source='get_lighting_type_display', read_only=True, allow_null=True)
    weather_type_display = serializers.CharField(source='get_weather_type_display', read_only=True, allow_null=True)
    hazard_type_display = serializers.CharField(source='get_hazard_type_display', read_only=True, allow_null=True)
    
    class Meta:
        model = EnvironmentalEffect
        fields = '__all__'


class ParticipantPositionSerializer(serializers.ModelSerializer):
    """Serializer for participant positions"""
    participant_name = serializers.CharField(source='participant.get_name', read_only=True)
    
    class Meta:
        model = ParticipantPosition
        fields = '__all__'

