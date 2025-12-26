from rest_framework import serializers
from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance
)
from bestiary.serializers import LanguageSerializer, DamageTypeSerializer


class CharacterClassSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = CharacterClass
        fields = "__all__"


class CharacterRaceSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    
    class Meta:
        model = CharacterRace
        fields = "__all__"


class CharacterBackgroundSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = CharacterBackground
        fields = "__all__"


class CharacterProficiencySerializer(serializers.ModelSerializer):
    proficiency_type_display = serializers.CharField(source='get_proficiency_type_display', read_only=True)
    proficiency_level_display = serializers.CharField(source='get_proficiency_level_display', read_only=True)
    language = LanguageSerializer(read_only=True)
    language_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CharacterProficiency
        fields = "__all__"


class CharacterFeatureSerializer(serializers.ModelSerializer):
    feature_type_display = serializers.CharField(source='get_feature_type_display', read_only=True)
    
    class Meta:
        model = CharacterFeature
        fields = "__all__"


class CharacterSpellSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = CharacterSpell
        fields = "__all__"


class CharacterResistanceSerializer(serializers.ModelSerializer):
    resistance_type_display = serializers.CharField(source='get_resistance_type_display', read_only=True)
    damage_type = DamageTypeSerializer(read_only=True)
    damage_type_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = CharacterResistance
        fields = "__all__"


class CharacterStatsSerializer(serializers.ModelSerializer):
    # Include ability score modifiers as computed fields
    strength_modifier = serializers.ReadOnlyField()
    dexterity_modifier = serializers.ReadOnlyField()
    constitution_modifier = serializers.ReadOnlyField()
    intelligence_modifier = serializers.ReadOnlyField()
    wisdom_modifier = serializers.ReadOnlyField()
    charisma_modifier = serializers.ReadOnlyField()
    
    class Meta:
        model = CharacterStats
        fields = "__all__"


class CharacterSerializer(serializers.ModelSerializer):
    stats = CharacterStatsSerializer(read_only=True)
    proficiencies = CharacterProficiencySerializer(many=True, read_only=True)
    features = CharacterFeatureSerializer(many=True, read_only=True)
    spells = CharacterSpellSerializer(many=True, read_only=True)
    resistances = CharacterResistanceSerializer(many=True, read_only=True)
    
    # Nested serializers for related objects
    character_class = CharacterClassSerializer(read_only=True)
    character_class_id = serializers.IntegerField(write_only=True)
    
    race = CharacterRaceSerializer(read_only=True)
    race_id = serializers.IntegerField(write_only=True)
    
    background = CharacterBackgroundSerializer(read_only=True, allow_null=True)
    background_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Display choices as readable text
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    alignment_display = serializers.CharField(source='get_alignment_display', read_only=True)
    
    # Computed fields
    proficiency_bonus = serializers.ReadOnlyField()
    
    def validate_character_class_id(self, value):
        """Validate that the character class exists"""
        try:
            CharacterClass.objects.get(pk=value)
        except CharacterClass.DoesNotExist:
            raise serializers.ValidationError(f"Character class with id {value} does not exist. Run 'python manage.py populate_character_data' to create base data.")
        return value
    
    def validate_race_id(self, value):
        """Validate that the race exists"""
        try:
            CharacterRace.objects.get(pk=value)
        except CharacterRace.DoesNotExist:
            raise serializers.ValidationError(f"Character race with id {value} does not exist. Run 'python manage.py populate_character_data' to create base data.")
        return value
    
    def validate_background_id(self, value):
        """Validate that the background exists (if provided)"""
        if value is not None:
            try:
                CharacterBackground.objects.get(pk=value)
            except CharacterBackground.DoesNotExist:
                raise serializers.ValidationError(f"Character background with id {value} does not exist. Run 'python manage.py populate_character_data' to create base data.")
        return value
    
    def create(self, validated_data):
        """Create a character with proper foreign key handling"""
        # Extract the _id fields and convert them to the actual foreign key fields
        character_class_id = validated_data.pop('character_class_id', None)
        race_id = validated_data.pop('race_id', None)
        background_id = validated_data.pop('background_id', None)
        
        # Get the actual objects
        if character_class_id:
            validated_data['character_class'] = CharacterClass.objects.get(pk=character_class_id)
        if race_id:
            validated_data['race'] = CharacterRace.objects.get(pk=race_id)
        if background_id:
            validated_data['background'] = CharacterBackground.objects.get(pk=background_id)
        
        return super().create(validated_data)
    
    class Meta:
        model = Character
        fields = "__all__"

