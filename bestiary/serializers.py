from rest_framework import serializers

from .models import (
    Condition,
    DamageType,
    Enemy,
    EnemyAbility,
    EnemyAction,
    EnemyActionDamage,
    EnemyAttack,
    EnemyConditionImmunity,
    EnemyEnvironment,
    EnemyLanguage,
    EnemyLegendaryAction,
    EnemyMultiattack,
    EnemyResistance,
    EnemySpell,
    EnemySpellSlot,
    EnemyStats,
    EnemyTrait,
    EnemyTreasure,
    Environment,
    Language,
)


class EnemyActionDamageSerializer(serializers.ModelSerializer):
    damage_type_name = serializers.CharField(source='damage_type.name', read_only=True, allow_null=True)
    formula = serializers.ReadOnlyField()

    class Meta:
        model = EnemyActionDamage
        fields = ('id', 'dice_count', 'dice_sides', 'damage_bonus', 'damage_type_name', 'is_secondary', 'formula')


class EnemyActionSerializer(serializers.ModelSerializer):
    damage_rolls = EnemyActionDamageSerializer(many=True, read_only=True)
    conditions_inflicted_names = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name', source='conditions_inflicted'
    )
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    attack_type_display = serializers.CharField(source='get_attack_type_display', read_only=True)

    class Meta:
        model = EnemyAction
        fields = (
            'id', 'name', 'description', 'action_type', 'action_type_display',
            'attack_type', 'attack_type_display', 'attack_bonus', 'reach_or_range',
            'saving_throw_dc', 'saving_throw_ability', 'half_damage_on_save',
            'conditions_inflicted_names', 'condition_save_end',
            'has_recharge', 'recharge_min_roll', 'target_count_or_area',
            'legendary_cost', 'damage_rolls'
        )


class EnemyMultiattackSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyMultiattack
        fields = ('id', 'description', 'action_count', 'sequence')


class EnemyTraitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyTrait
        fields = ('id', 'name', 'description', 'trait_type')


class EnemyAttackSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyAttack
        fields = "__all__"


class EnemyAbilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyAbility
        fields = "__all__"


class EnemySpellSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemySpellSlot
        fields = "__all__"


class EnemySpellSerializer(serializers.ModelSerializer):
    slots = EnemySpellSlotSerializer(many=True, read_only=True)

    class Meta:
        model = EnemySpell
        fields = "__all__"


class DamageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DamageType
        fields = "__all__"


class EnemyResistanceSerializer(serializers.ModelSerializer):
    damage_type = DamageTypeSerializer(read_only=True)
    damage_type_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = EnemyResistance
        fields = "__all__"


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"


class EnemyLanguageSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)
    language_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = EnemyLanguage
        fields = "__all__"


class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = "__all__"


class EnemyConditionImmunitySerializer(serializers.ModelSerializer):
    condition = ConditionSerializer(read_only=True)
    condition_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = EnemyConditionImmunity
        fields = "__all__"


class EnemyLegendaryActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyLegendaryAction
        fields = "__all__"


class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = "__all__"


class EnemyEnvironmentSerializer(serializers.ModelSerializer):
    environment = EnvironmentSerializer(read_only=True)
    environment_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = EnemyEnvironment
        fields = "__all__"


class EnemyTreasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnemyTreasure
        fields = "__all__"


class EnemyStatsSerializer(serializers.ModelSerializer):
    # Include ability score modifiers as computed fields
    strength_modifier = serializers.ReadOnlyField()
    dexterity_modifier = serializers.ReadOnlyField()
    constitution_modifier = serializers.ReadOnlyField()
    intelligence_modifier = serializers.ReadOnlyField()
    wisdom_modifier = serializers.ReadOnlyField()
    charisma_modifier = serializers.ReadOnlyField()
    
    class Meta:
        model = EnemyStats
        fields = "__all__"


class EnemySerializer(serializers.ModelSerializer):
    actions = EnemyActionSerializer(many=True, read_only=True)
    multiattack = EnemyMultiattackSerializer(read_only=True)
    traits = EnemyTraitSerializer(many=True, read_only=True)
    attacks = EnemyAttackSerializer(many=True, read_only=True)
    abilities = EnemyAbilitySerializer(many=True, read_only=True)
    spells = EnemySpellSerializer(many=True, read_only=True)
    stats = EnemyStatsSerializer(read_only=True)
    resistances = EnemyResistanceSerializer(many=True, read_only=True)
    languages = EnemyLanguageSerializer(many=True, read_only=True)
    condition_immunities = EnemyConditionImmunitySerializer(many=True, read_only=True)
    legendary_actions = EnemyLegendaryActionSerializer(many=True, read_only=True)
    environments = EnemyEnvironmentSerializer(many=True, read_only=True)
    treasure = EnemyTreasureSerializer(many=True, read_only=True)
    
    # Display choices as readable text
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    creature_type_display = serializers.CharField(source='get_creature_type_display', read_only=True)
    alignment_display = serializers.CharField(source='get_alignment_display', read_only=True)

    class Meta:
        model = Enemy
        fields = "__all__"
