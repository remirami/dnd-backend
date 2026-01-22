from rest_framework import serializers
from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance, CharacterItem,
    CharacterClassLevel
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


from items.serializers import ItemSerializer

class CharacterSpellSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    spell_details = serializers.SerializerMethodField()
    spell_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CharacterSpell
        fields = "__all__"
        extra_kwargs = {
            'name': {'required': False},
            'level': {'required': False},
            'school': {'required': False},
            'spell': {'required': False},
        }

    def get_spell_details(self, obj):
        if not obj.spell:
            return None
        from spells.serializers import SpellListSerializer
        return SpellListSerializer(obj.spell).data
    
    def validate(self, data):
        # If spell_id is provided, populate name, level, school from it
        if 'spell_id' in data:
            from spells.models import Spell
            try:
                spell = Spell.objects.get(pk=data['spell_id'])
                data['spell'] = spell
                # Auto-populate legacy fields if they are missing
                if 'name' not in data:
                    data['name'] = spell.name
                if 'level' not in data:
                    data['level'] = spell.level
                if 'school' not in data:
                    data['school'] = spell.school
            except Spell.DoesNotExist:
                raise serializers.ValidationError({"spell_id": "Spell not found"})
        return data


class CharacterItemSerializer(serializers.ModelSerializer):
    item_details = serializers.SerializerMethodField()
    item_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CharacterItem
        fields = "__all__"
        read_only_fields = ('character',)

    def get_item_details(self, obj):
        if not obj.item:
            return None
        
        item = obj.item
        if hasattr(item, 'weapon'):
            from items.serializers import WeaponSerializer
            return WeaponSerializer(item.weapon).data
        elif hasattr(item, 'armor'):
            from items.serializers import ArmorSerializer
            return ArmorSerializer(item.armor).data
        elif hasattr(item, 'consumable'):
            from items.serializers import ConsumableSerializer
            return ConsumableSerializer(item.consumable).data
        
        return ItemSerializer(item).data


class CharacterResistanceSerializer(serializers.ModelSerializer):
    resistance_type_display = serializers.CharField(source='get_resistance_type_display', read_only=True)
    damage_type = DamageTypeSerializer(read_only=True)
    damage_type_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = CharacterResistance
        fields = "__all__"
        read_only_fields = ('character',)


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


class CharacterClassLevelSerializer(serializers.ModelSerializer):
    """Serializer for character class levels"""
    class_name = serializers.CharField(source='character_class.get_name_display', read_only=True)
    character_class_id = serializers.IntegerField(source='character_class.id', read_only=True)
    
    class Meta:
        model = CharacterClassLevel
        fields = ['id', 'character_class_id', 'class_name', 'level', 'subclass', 'created_at', 'updated_at']


class CharacterSerializer(serializers.ModelSerializer):
    stats = CharacterStatsSerializer(read_only=True)
    proficiencies = CharacterProficiencySerializer(many=True, read_only=True)
    features = CharacterFeatureSerializer(many=True, read_only=True)
    spells = CharacterSpellSerializer(many=True, read_only=True)
    character_items = CharacterItemSerializer(many=True, read_only=True)
    resistances = CharacterResistanceSerializer(many=True, read_only=True)
    class_levels = CharacterClassLevelSerializer(many=True, read_only=True)
    
    # Nested serializers for related objects
    character_class = CharacterClassSerializer(read_only=True)
    character_class_id = serializers.IntegerField(write_only=True)
    
    race = CharacterRaceSerializer(read_only=True)
    race_id = serializers.IntegerField(write_only=True)
    
    background = CharacterBackgroundSerializer(read_only=True, allow_null=True)
    background_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Ability Scores (Write Only - used for creation)
    strength = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    dexterity = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    constitution = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    intelligence = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    wisdom = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    charisma = serializers.IntegerField(write_only=True, min_value=1, max_value=30, required=False)
    
    # Display choices as readable text
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    alignment_display = serializers.CharField(source='get_alignment_display', read_only=True)
    
    # Computed fields
    proficiency_bonus = serializers.ReadOnlyField()
    
    # Multiclass info
    total_level = serializers.SerializerMethodField()
    multiclass_info = serializers.SerializerMethodField()
    
    def get_total_level(self, obj):
        """Get total character level (sum of all class levels)"""
        try:
            from .multiclassing import get_total_level
            return get_total_level(obj)
        except:
            return obj.level
    
    def get_multiclass_info(self, obj):
        """Get multiclass information"""
        try:
            from .multiclassing import (
                calculate_multiclass_spell_slots, get_multiclass_spellcasting_ability,
                get_multiclass_hit_dice
            )
            return {
                'spell_slots': calculate_multiclass_spell_slots(obj),
                'spellcasting_ability': get_multiclass_spellcasting_ability(obj),
                'hit_dice': get_multiclass_hit_dice(obj),
            }
        except:
            return {}
    
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
        """Create a character with proper foreign key handling and auto-create stats"""
        # Extract the _id fields and convert them to the actual foreign key fields
        character_class_id = validated_data.pop('character_class_id', None)
        race_id = validated_data.pop('race_id', None)
        background_id = validated_data.pop('background_id', None)
        
        # Extract ability scores if provided (for create)
        ability_scores = {
            'strength': validated_data.pop('strength', 10),
            'dexterity': validated_data.pop('dexterity', 10),
            'constitution': validated_data.pop('constitution', 10),
            'intelligence': validated_data.pop('intelligence', 10),
            'wisdom': validated_data.pop('wisdom', 10),
            'charisma': validated_data.pop('charisma', 10),
        }
        
        # Get the actual objects
        character_class = None
        race = None
        if character_class_id:
            character_class = CharacterClass.objects.get(pk=character_class_id)
            validated_data['character_class'] = character_class
        if race_id:
            race = CharacterRace.objects.get(pk=race_id)
            validated_data['race'] = race
        if background_id:
            validated_data['background'] = CharacterBackground.objects.get(pk=background_id)
        
        # Create the character
        character = super().create(validated_data)
        
        # Apply racial bonuses to stats
        if race:
            from .services.validators import RacialBonusCalculator
            # Map full names to short names for calculator
            short_scores = {
                'str': ability_scores['strength'],
                'dex': ability_scores['dexterity'],
                'con': ability_scores['constitution'],
                'int': ability_scores['intelligence'],
                'wis': ability_scores['wisdom'],
                'cha': ability_scores['charisma'],
            }
            
            # Apply bonuses
            final_scores_short = RacialBonusCalculator.apply_bonuses(short_scores, race)
            
            # Update ability_scores with results
            ability_scores['strength'] = final_scores_short['str']
            ability_scores['dexterity'] = final_scores_short['dex']
            ability_scores['constitution'] = final_scores_short['con']
            ability_scores['intelligence'] = final_scores_short['int']
            ability_scores['wisdom'] = final_scores_short['wis']
            ability_scores['charisma'] = final_scores_short['cha']
        
        # Auto-create CharacterStats
        con_mod = (ability_scores['constitution'] - 10) // 2
        dex_mod = (ability_scores['dexterity'] - 10) // 2
        
        # Calculate HP based on class hit dice
        hit_dice_map = {'d6': 6, 'd8': 8, 'd10': 10, 'd12': 12}
        die_size = hit_dice_map.get(character_class.hit_dice if character_class else 'd8', 8)
        max_hp = max(1, die_size + con_mod)  # Level 1: max die + CON mod
        
        # Calculate AC (base 10 + DEX mod)
        armor_class = 10 + dex_mod
        
        # Get race speed if available
        speed = race.speed if race else 30
        
        CharacterStats.objects.create(
            character=character,
            **ability_scores,
            hit_points=max_hp,
            max_hit_points=max_hp,
            armor_class=armor_class,
            speed=speed,
            initiative=dex_mod,
            passive_perception=10 + ((ability_scores['wisdom'] - 10) // 2),
            passive_investigation=10 + ((ability_scores['intelligence'] - 10) // 2),
            passive_insight=10 + ((ability_scores['wisdom'] - 10) // 2),
        )
        
        # Apply racial skills and traits
        if race:
            # Parse skill proficiencies (comma-separated)
            if race.skill_proficiencies:
                skill_names = [s.strip() for s in race.skill_proficiencies.split(',') if s.strip()]
                for skill_name in skill_names:
                    CharacterProficiency.objects.create(
                        character=character,
                        proficiency_type='skill',
                        skill_name=skill_name,
                        source='Race'
                    )
            
            # Parse traits (JSON list)
            if race.traits:
                for trait in race.traits:
                    CharacterFeature.objects.create(
                        character=character,
                        name=trait.get('name', 'Unknown Trait'),
                        feature_type='racial',
                        description=trait.get('description', ''),
                        source='Race'
                    )
            
            # Add Ability Score Increases as a feature
            if race.ability_score_increases:
                # Parse the increases (e.g., "+2 str, +1 con")
                increases_str = race.ability_score_increases
                # Format it nicely for display
                ability_map = {
                    'str': 'Strength',
                    'dex': 'Dexterity', 
                    'con': 'Constitution',
                    'int': 'Intelligence',
                    'wis': 'Wisdom',
                    'cha': 'Charisma'
                }
                
                # Parse and format the description
                parts = []
                for part in increases_str.split(','):
                    part = part.strip()
                    if part:
                        # Extract bonus (e.g., "+2") and ability (e.g., "str")
                        for abbr, full_name in ability_map.items():
                            if abbr in part.lower():
                                # Get the number
                                import re
                                match = re.search(r'[+-]?\d+', part)
                                if match:
                                    bonus = match.group()
                                    parts.append(f"{bonus} {full_name}")
                                break
                
                if parts:
                    description = "Your ability scores increase by: " + ", ".join(parts) + "."
                    CharacterFeature.objects.create(
                        character=character,
                        name='Ability Score Increase',
                        feature_type='racial',
                        description=description,
                        source='Race'
                    )
        
        # Apply background skills and features
        background = validated_data.get('background')
        if background:
            # Skills
            if background.skill_proficiencies:
                skill_names = [s.strip() for s in background.skill_proficiencies.split(',') if s.strip()]
                for skill_name in skill_names:
                    # Check for duplicates or handle gracefully? 
                    # For now just create, assuming unique_together handles or we ignore overlap
                    if not CharacterProficiency.objects.filter(character=character, proficiency_type='skill', skill_name=skill_name).exists():
                         CharacterProficiency.objects.create(
                            character=character,
                            proficiency_type='skill',
                            skill_name=skill_name,
                            source='Background'
                        )

            # Tools
            if background.tool_proficiencies:
                tool_names = [t.strip() for t in background.tool_proficiencies.split(',') if t.strip()]
                for tool_name in tool_names:
                     if not CharacterProficiency.objects.filter(character=character, proficiency_type='tool', item_name=tool_name).exists():
                        CharacterProficiency.objects.create(
                            character=character,
                            proficiency_type='tool',
                            item_name=tool_name,
                            source='Background'
                        )
            
            # Feature
            if background.feature_name:
                CharacterFeature.objects.create(
                    character=character,
                    name=background.feature_name,
                    feature_type='background',
                    description=background.feature_description or '',
                    source='Background'
                )

        return character

    def update(self, instance, validated_data):
        """Update character and check for ASI levels"""
        old_level = instance.level
        instance = super().update(instance, validated_data)
        new_level = instance.level
        
        # Check for ASI levels if level increased
        # Check for ASI levels if level increased
        if new_level > old_level:
            asi_levels = [4, 8, 12, 16, 19]
            pending = instance.pending_asi_levels or []
            
            # Check all levels reached in this update
            for level in range(old_level + 1, new_level + 1):
                if level in asi_levels and level not in pending:
                    pending.append(level)
            
            if pending != instance.pending_asi_levels:
                instance.pending_asi_levels = pending
                instance.save(update_fields=['pending_asi_levels'])
            
            # Check for Subclass Selection
            if not instance.subclass:
                subclass_levels = {
                    'Cleric': 1,
                    'Druid': 2,
                    'Wizard': 2,
                    'Sorcerer': 1,
                    'Warlock': 1,
                }
                default_subclass_level = 3
                # Get class name safely
                class_name = instance.character_class.name if instance.character_class else None
                if class_name:
                    required_level = subclass_levels.get(class_name, default_subclass_level)
                    if new_level >= required_level:
                        instance.pending_subclass_selection = True
                        instance.save(update_fields=['pending_subclass_selection'])
            
            # Apply Class Features for gained levels
            if instance.character_class:
                from campaigns.class_features_data import get_class_features
                from .models import CharacterFeature
                
                # We need to apply features for ALL levels gained in this jump
                for level in range(old_level + 1, new_level + 1):
                    # Handle case-insensitive class name lookup
                    features = get_class_features(instance.character_class.name.lower(), level)
                    for feature_data in features:
                        CharacterFeature.objects.get_or_create(
                            character=instance,
                            name=feature_data['name'],
                            defaults={
                                'feature_type': 'class',
                                'description': feature_data['description'],
                                'source': f"{instance.character_class.name} Level {level}"
                            }
                        )

        
        return instance
    
    class Meta:
        model = Character
        fields = "__all__"



class FeatSerializer(serializers.ModelSerializer):
    """Serializer for feats with optional eligibility checking"""
    is_eligible = serializers.SerializerMethodField()
    reason_if_not = serializers.SerializerMethodField()
    
    class Meta:
        from .models import Feat
        model = Feat
        fields = '__all__'
        extra_kwargs = {
            'is_eligible': {'read_only': True},
            'reason_if_not': {'read_only': True},
        }
    
    def get_is_eligible(self, obj):
        """Check if character (from context) is eligible for this feat"""
        character = self.context.get('character')
        if not character:
            return None
        is_eligible, _ = obj.check_prerequisites(character)
        return is_eligible
    
    def get_reason_if_not(self, obj):
        """Get reason why character is not eligible"""
        character = self.context.get('character')
        if not character:
            return None
        _, reason = obj.check_prerequisites(character)
        return reason


class CharacterFeatSerializer(serializers.ModelSerializer):
    """Serializer for character feats with nested feat details"""
    feat = FeatSerializer(read_only=True)
    feat_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        from .models import CharacterFeat
        model = CharacterFeat
        fields = '__all__'
        read_only_fields = ('character', 'taken_at')
