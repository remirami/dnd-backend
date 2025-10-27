from rest_framework import serializers
from .models import (
    Enemy, EnemyAttack, EnemyAbility, EnemySpell, EnemySpellSlot,
    EnemyStats, DamageType, EnemyResistance, Language, EnemyLanguage,
    Condition, EnemyConditionImmunity, EnemyLegendaryAction,
    Environment, EnemyEnvironment, EnemyTreasure
)


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
