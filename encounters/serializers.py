# encounters/serializers.py
from rest_framework import serializers
from .models import Encounter, EncounterEnemy
from bestiary.models import Enemy


class EncounterEnemySerializer(serializers.ModelSerializer):
    enemy_name = serializers.CharField(source='enemy.name', read_only=True)

    class Meta:
        model = EncounterEnemy
        fields = [
            'id', 'encounter', 'enemy', 'enemy_name',
            'name', 'initiative', 'current_hp', 'is_alive',
            'conditions', 'notes'
        ]


class EncounterSerializer(serializers.ModelSerializer):
    # Allow writing nested enemies
    enemies = EncounterEnemySerializer(many=True, required=False)

    class Meta:
        model = Encounter
        fields = ['id', 'name', 'description', 'location', 'created_at', 'enemies']

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
        instance.save()

        # optional: clear and re-add enemies
        if enemies_data:
            instance.enemies.all().delete()
            for enemy_data in enemies_data:
                EncounterEnemy.objects.create(encounter=instance, **enemy_data)

        return instance
