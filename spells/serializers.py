from rest_framework import serializers
from .models import Spell, SpellDamage
from characters.serializers import CharacterClassSerializer
from characters.models import CharacterClass
from bestiary.serializers import DamageTypeSerializer


class SpellDamageSerializer(serializers.ModelSerializer):
    """Serializer for spell damage progression"""
    damage_type_name = serializers.CharField(source='damage_type.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SpellDamage
        fields = '__all__'


class SpellSerializer(serializers.ModelSerializer):
    """Serializer for spell data"""
    classes = CharacterClassSerializer(many=True, read_only=True)
    damage_progression = SpellDamageSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    school_display = serializers.CharField(source='get_school_display', read_only=True)
    
    class Meta:
        model = Spell
        fields = '__all__'


class SimpleClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterClass
        fields = ['id', 'name']

class SpellListSerializer(serializers.ModelSerializer):
    """Lighter serializer for spell lists"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    school_display = serializers.CharField(source='get_school_display', read_only=True)
    classes = SimpleClassSerializer(many=True, read_only=True)
    
    class Meta:
        model = Spell
        fields = ['id', 'name', 'slug', 'level', 'level_display', 'school', 'school_display', 
                  'casting_time', 'range', 'concentration', 'ritual', 'classes']
