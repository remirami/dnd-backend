from rest_framework import serializers

from bestiary.serializers import ConditionSerializer, DamageTypeSerializer
from characters.serializers import CharacterSerializer
from encounters.serializers import EncounterEnemySerializer, EncounterSerializer

from .models import CombatAction, CombatLog, CombatParticipant, CombatSession, EnvironmentalEffect, ParticipantPosition


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

            # Class feature resources for characters (e.g. Lay on Hands pool)
            data['feature_uses'] = instance.feature_uses or {}
            class_name = getattr(instance.character.character_class, 'name', '').lower()
            is_paladin = class_name == 'paladin' or instance.character.features.filter(name__iexact='Lay on Hands').exists()
            if is_paladin:
                data['lay_on_hands_pool'] = instance.get_lay_on_hands_pool()
                data['max_lay_on_hands_pool'] = (instance.character.level or 1) * 5
        
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
            
            # Structured EnemyAction records (excluding Multiattack utility entries)
            raw_actions = list(enemy.actions.all().prefetch_related('damage_rolls', 'conditions_inflicted'))
            actions = [act for act in raw_actions if 'multiattack' not in act.name.lower()]
            
            # Attacks: Prefer structured weapon actions over legacy flat strings
            action_attacks = []
            for act in actions:
                if act.attack_type in ['melee_weapon', 'ranged_weapon', 'melee_spell', 'ranged_spell']:
                    dmg_rolls = list(act.damage_rolls.all())
                    dmg_str = " + ".join([d.formula for d in dmg_rolls]) if dmg_rolls else "1d6 bludgeoning"
                    action_attacks.append({
                        'name': act.name,
                        'bonus': act.attack_bonus if act.attack_bonus is not None else (stats.strength_modifier if stats else 2),
                        'damage': dmg_str,
                    })

            if action_attacks:
                data['enemy_attacks'] = action_attacks
            else:
                # Fallback to legacy attacks, strictly excluding any named Multiattack
                attacks = [atk for atk in enemy.attacks.all() if 'multiattack' not in atk.name.lower()]
                if attacks:
                    data['enemy_attacks'] = [
                        {
                            'name': atk.name,
                            'bonus': atk.bonus,
                            'damage': atk.damage,
                        }
                        for atk in attacks
                    ]
            
            # Abilities (use in-memory list to leverage prefetch_related)
            abilities = list(enemy.abilities.all())
            if abilities:
                data['enemy_abilities'] = [
                    {
                        'name': ab.name,
                        'description': ab.description,
                    }
                    for ab in abilities
                ]
            
            # Resistances/immunities (use in-memory list to leverage prefetch_related)
            resistances = list(enemy.resistances.all())
            if resistances:
                data['enemy_resistances'] = [
                    {
                        'damage_type': r.damage_type.name,
                        'type': r.resistance_type,
                    }
                    for r in resistances
                ]

            if actions:
                data['enemy_actions'] = [
                    {
                        'id': act.id,
                        'name': act.name,
                        'description': act.description,
                        'action_type': act.action_type,
                        'action_type_display': act.get_action_type_display(),
                        'attack_type': act.attack_type,
                        'attack_type_display': act.get_attack_type_display(),
                        'attack_bonus': act.attack_bonus,
                        'reach_or_range': act.reach_or_range,
                        'saving_throw_dc': act.saving_throw_dc,
                        'saving_throw_ability': act.saving_throw_ability,
                        'half_damage_on_save': act.half_damage_on_save,
                        'conditions_inflicted': [c.name for c in act.conditions_inflicted.all()],
                        'condition_save_end': act.condition_save_end,
                        'has_recharge': act.has_recharge,
                        'recharge_min_roll': act.recharge_min_roll,
                        'is_charged': instance.recharge_state.get(act.name, True) if act.has_recharge else True,
                        'damage_rolls': [
                            {
                                'formula': d.formula,
                                'dice_count': d.dice_count,
                                'dice_sides': d.dice_sides,
                                'damage_bonus': d.damage_bonus,
                                'damage_type': d.damage_type.name if d.damage_type else None,
                                'is_secondary': d.is_secondary,
                            }
                            for d in act.damage_rolls.all()
                        ]
                    }
                    for act in actions
                ]

            # Multiattack
            if hasattr(enemy, 'multiattack') and enemy.multiattack:
                data['multiattack'] = {
                    'description': enemy.multiattack.description,
                    'action_count': enemy.multiattack.action_count,
                    'sequence': enemy.multiattack.sequence,
                }

            # Traits
            traits = list(enemy.traits.all())
            if traits:
                data['enemy_traits'] = [
                    {
                        'name': t.name,
                        'description': t.description,
                        'trait_type': t.trait_type,
                    }
                    for t in traits
                ]

            data['recharge_state'] = instance.recharge_state
        
        return data


class CombatActionSerializer(serializers.ModelSerializer):
    """Serializer for combat actions"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    is_ai = serializers.SerializerMethodField()
    damage_type = DamageTypeSerializer(read_only=True, allow_null=True)
    is_advantage = serializers.SerializerMethodField()
    is_disadvantage = serializers.SerializerMethodField()
    
    class Meta:
        model = CombatAction
        fields = "__all__"
    
    def get_actor_name(self, obj):
        return obj.actor.get_name() if obj.actor else None
    
    def get_target_name(self, obj):
        return obj.target.get_name() if obj.target else None
    
    def get_is_ai(self, obj):
        return obj.actor.participant_type == 'enemy' if obj.actor else False

    def get_is_advantage(self, obj):
        if getattr(obj, 'is_advantage', False):
            return True
        desc = (obj.description or "").lower()
        return ('advantage' in desc and 'disadvantage' not in desc) or ('[pack tactics]' in desc)

    def get_is_disadvantage(self, obj):
        if getattr(obj, 'is_disadvantage', False):
            return True
        desc = (obj.description or "").lower()
        return 'disadvantage' in desc


class CombatParticipantSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for combat participants in list views"""
    name = serializers.SerializerMethodField()

    class Meta:
        model = CombatParticipant
        fields = [
            'id', 'participant_type', 'name', 'initiative',
            'current_hp', 'max_hp', 'armor_class', 'is_active'
        ]

    def get_name(self, obj):
        return obj.get_name()


class CombatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for combat sessions list view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    encounter = EncounterSerializer(read_only=True, allow_null=True)
    participants = CombatParticipantSummarySerializer(many=True, read_only=True)

    class Meta:
        model = CombatSession
        fields = [
            'id', 'status', 'status_display', 'is_active', 'current_round',
            'current_turn_index', 'started_at', 'ended_at', 'is_practice',
            'encounter', 'participants'
        ]

    def get_is_active(self, obj):
        return obj.status == 'active'


class CombatSessionSerializer(serializers.ModelSerializer):
    """Serializer for combat sessions"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    encounter = EncounterSerializer(read_only=True, allow_null=True)
    encounter_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    participants = CombatParticipantSerializer(many=True, read_only=True)
    current_participant = serializers.SerializerMethodField()
    initiative_order = serializers.SerializerMethodField()
    actions = CombatActionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CombatSession
        fields = "__all__"
        read_only_fields = ['created_by']
        
    def get_is_active(self, obj):
        return obj.status == 'active'
    
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
    is_healing = serializers.BooleanField(required=False, default=False)
    is_ritual = serializers.BooleanField(required=False, default=False)
    requires_concentration = serializers.BooleanField(required=False, default=False)


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

