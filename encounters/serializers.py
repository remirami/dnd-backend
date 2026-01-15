# encounters/serializers.py
from rest_framework import serializers
from .models import (
    Encounter, EncounterEnemy, EncounterTheme,
    EnemyThemeAssociation, BiomeEncounterWeight, ThemeIncompatibility
)
from bestiary.serializers import EnemySerializer


class EncounterEnemySerializer(serializers.ModelSerializer):
    enemy_name = serializers.CharField(source='enemy.name', read_only=True)

    class Meta:
        model = EncounterEnemy
        fields = [
            'id', 'encounter', 'enemy', 'enemy_name',
            'name', 'initiative', 'current_hp', 'is_alive',
            'conditions', 'notes'
        ]


class EncounterThemeSerializer(serializers.ModelSerializer):
    """Serializer for EncounterTheme"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    enemy_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EncounterTheme
        fields = [
            'id', 'name', 'category', 'category_display',
            'description', 'min_cr', 'max_cr', 'weight',
            'flavor_text', 'enemy_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_enemy_count(self, obj):
        """Return number of enemies associated with this theme"""
        return obj.enemy_associations.count()


class EnemyThemeAssociationSerializer(serializers.ModelSerializer):
    """Serializer for EnemyThemeAssociation"""
    
    enemy_name = serializers.CharField(source='enemy.name', read_only=True)
    theme_name = serializers.CharField(source='theme.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = EnemyThemeAssociation
        fields = [
            'id', 'theme', 'theme_name', 'enemy', 'enemy_name',
            'role', 'role_display', 'weight', 'min_count', 'max_count'
        ]


class BiomeEncounterWeightSerializer(serializers.ModelSerializer):
    """Serializer for BiomeEncounterWeight"""
    
    biome_display = serializers.CharField(source='get_biome_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    theme_name = serializers.CharField(source='theme.name', read_only=True)
    
    class Meta:
        model = BiomeEncounterWeight
        fields = [
            'id', 'biome', 'biome_display', 'theme', 'theme_name',
            'category', 'category_display', 'weight', 'narrative_reason'
        ]


class EncounterSerializer(serializers.ModelSerializer):
    """Enhanced serializer for Encounter with theme/biome support"""
    
    # Allow writing nested enemies
    enemies = EncounterEnemySerializer(many=True, required=False)
    theme_name = serializers.CharField(source='theme.name', read_only=True, allow_null=True)
    biome_display = serializers.CharField(source='get_biome_display', read_only=True)

    class Meta:
        model = Encounter
        fields = [
            'id', 'name', 'description', 'location',
            'theme', 'theme_name', 'biome', 'biome_display',
            'is_chaotic', 'narrative_justification',
            'enemies', 'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        enemies_data = validated_data.pop('enemies', [])
        encounter = Encounter.objects.create(**validated_data)

        for enemy_data in enemies_data:
            EncounterEnemy.objects.create(encounter=encounter, **enemy_data)

        return encounter

    def update(self, instance, validated_data):
        enemies_data = validated_data.pop('enemies', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.location = validated_data.get('location', instance.location)
        instance.theme = validated_data.get('theme', instance.theme)
        instance.biome = validated_data.get('biome', instance.biome)
        instance.is_chaotic = validated_data.get('is_chaotic', instance.is_chaotic)
        instance.narrative_justification = validated_data.get('narrative_justification', instance.narrative_justification)
        instance.save()

        # optional: clear and re-add enemies
        if enemies_data:
            instance.enemies.all().delete()
            for enemy_data in enemies_data:
                EncounterEnemy.objects.create(encounter=instance, **enemy_data)

        return instance
