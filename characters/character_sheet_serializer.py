"""
Character Sheet Serializer

Provides a complete, comprehensive view of a character for display
on a character sheet. Includes all stats, abilities, features, spells,
equipment, and computed values.
"""
from rest_framework import serializers
from .models import Character, CharacterStats, CharacterFeat
from .multiclassing import get_total_level, get_class_level


class CharacterSheetSerializer(serializers.ModelSerializer):
    """
    Comprehensive character sheet data for frontend display.
    
    Includes:
    - Basic info (name, race, class, level, alignment)
    - Ability scores and modifiers
    - Combat stats (HP, AC, initiative, proficiency bonus)
    - Saving throws (with proficiency)
    - Skills (with proficiency and modifiers)
    - Features (racial, class, feats)
    - Spells (known, prepared, slots)
    - Equipment (with AC calculations)
    - Multiclass info
    """
    
    # Basic Info
    race_name = serializers.CharField(source='race.get_name_display', read_only=True)
    class_name = serializers.CharField(source='character_class.get_name_display', read_only=True)
    background_name = serializers.CharField(source='background.get_name_display', read_only=True)
    
    # Ability Scores (from stats)
    ability_scores = serializers.SerializerMethodField()
    
    # Combat Stats
    combat_stats = serializers.SerializerMethodField()
    
    # Proficiency Bonus
    proficiency_bonus = serializers.SerializerMethodField()
    
    # Saving Throws
    saving_throws = serializers.SerializerMethodField()
    
    # Skills
    skills = serializers.SerializerMethodField()
    
    # Features
    features = serializers.SerializerMethodField()
    
    # Feats
    feats = serializers.SerializerMethodField()
    
    # Spells
    spells = serializers.SerializerMethodField()
    
    # Equipment
    equipment = serializers.SerializerMethodField()
    
    # Multiclass Info
    multiclass_info = serializers.SerializerMethodField()
    
    # Proficiencies
    proficiencies = serializers.SerializerMethodField()
    
    class Meta:
        model = Character
        fields = [
            # Basic
            'id', 'name', 'race_name', 'class_name', 'background_name',
            'level', 'alignment', 'experience_points',
            # Derived
            'ability_scores', 'combat_stats', 'proficiency_bonus',
            'saving_throws', 'skills', 'features', 'feats', 'spells',
            'equipment', 'multiclass_info', 'proficiencies'
        ]
    
    def get_ability_scores(self, obj):
        """Get all ability scores with modifiers"""
        if not hasattr(obj, 'stats'):
            return None
        
        stats = obj.stats
        
        def calc_mod(score):
            return (score - 10) // 2
        
        return {
            'strength': {
                'score': stats.strength,
                'modifier': calc_mod(stats.strength)
            },
            'dexterity': {
                'score': stats.dexterity,
                'modifier': calc_mod(stats.dexterity)
            },
            'constitution': {
                'score': stats.constitution,
                'modifier': calc_mod(stats.constitution)
            },
            'intelligence': {
                'score': stats.intelligence,
                'modifier': calc_mod(stats.intelligence)
            },
            'wisdom': {
                'score': stats.wisdom,
                'modifier': calc_mod(stats.wisdom)
            },
            'charisma': {
                'score': stats.charisma,
                'modifier': calc_mod(stats.charisma)
            }
        }
    
    def get_combat_stats(self, obj):
        """Get combat-related stats"""
        if not hasattr(obj, 'stats'):
            return None
        
        stats = obj.stats
        dex_mod = (stats.dexterity - 10) // 2
        wis_mod = (stats.wisdom - 10) // 2
        
        return {
            'hit_points': {
                'current': stats.hit_points,
                'maximum': stats.max_hit_points,
                'temporary': 0  # TODO: Add temp HP field if needed
            },
            'armor_class': stats.armor_class,
            'initiative': dex_mod,
            'speed': stats.speed,
            'passive_perception': 10 + wis_mod,
            'passive_investigation': 10 + ((stats.intelligence - 10) // 2),
            'passive_insight': 10 + wis_mod
        }
    
    def get_proficiency_bonus(self, obj):
        """Calculate proficiency bonus based on level"""
        return 2 + ((obj.level - 1) // 4)
    
    def get_saving_throws(self, obj):
        """Get saving throw bonuses (with proficiency if applicable)"""
        if not hasattr(obj, 'stats'):
            return None
        
        stats = obj.stats
        prof_bonus = self.get_proficiency_bonus(obj)
        
        # Get proficient saves from class
        proficient_saves = []
        if obj.character_class and obj.character_class.saving_throw_proficiencies:
            proficient_saves = [s.strip().lower() for s in obj.character_class.saving_throw_proficiencies.split(',')]
        
        def calc_save(ability, ability_score):
            mod = (ability_score - 10) // 2
            is_proficient = ability.lower() in proficient_saves
            bonus = mod + (prof_bonus if is_proficient else 0)
            return {
                'modifier': bonus,
                'proficient': is_proficient
            }
        
        return {
            'strength': calc_save('STR', stats.strength),
            'dexterity': calc_save('DEX', stats.dexterity),
            'constitution': calc_save('CON', stats.constitution),
            'intelligence': calc_save('INT', stats.intelligence),
            'wisdom': calc_save('WIS', stats.wisdom),
            'charisma': calc_save('CHA', stats.charisma)
        }
    
    def get_skills(self, obj):
        """Get all skill modifiers with proficiency"""
        if not hasattr(obj, 'stats'):
            return None
        
        stats = obj.stats
        prof_bonus = self.get_proficiency_bonus(obj)
        
        # Get proficient skills from proficiencies table
        proficient_skills = set(
            obj.proficiencies.filter(proficiency_type='skill')
            .values_list('skill_name', flat=True)
        )
        
        # D&D 5e skill list with ability associations
        skills_list = {
            'Acrobatics': ('dexterity', stats.dexterity),
            'Animal Handling': ('wisdom', stats.wisdom),
            'Arcana': ('intelligence', stats.intelligence),
            'Athletics': ('strength', stats.strength),
            'Deception': ('charisma', stats.charisma),
            'History': ('intelligence', stats.intelligence),
            'Insight': ('wisdom', stats.wisdom),
            'Intimidation': ('charisma', stats.charisma),
            'Investigation': ('intelligence', stats.intelligence),
            'Medicine': ('wisdom', stats.wisdom),
            'Nature': ('intelligence', stats.intelligence),
            'Perception': ('wisdom', stats.wisdom),
            'Performance': ('charisma', stats.charisma),
            'Persuasion': ('charisma', stats.charisma),
            'Religion': ('intelligence', stats.intelligence),
            'Sleight of Hand': ('dexterity', stats.dexterity),
            'Stealth': ('dexterity', stats.dexterity),
            'Survival': ('wisdom', stats.wisdom)
        }
        
        result = {}
        for skill_name, (ability, ability_score) in skills_list.items():
            ability_mod = (ability_score - 10) // 2
            is_proficient = skill_name in proficient_skills
            modifier = ability_mod + (prof_bonus if is_proficient else 0)
            
            result[skill_name] = {
                'modifier': modifier,
                'proficient': is_proficient,
                'ability': ability
            }
        
        return result
    
    def get_features(self, obj):
        """Get racial and class features"""
        features = obj.features.all().order_by('feature_type', 'name')
        
        return [
            {
                'name': f.name,
                'type': f.get_feature_type_display() if hasattr(f, 'get_feature_type_display') else f.feature_type,
                'description': f.description,
                'source': f.source
            }
            for f in features
        ]
    
    def get_feats(self, obj):
        """Get character feats"""
        char_feats = CharacterFeat.objects.filter(character=obj).select_related('feat')
        
        return [
            {
                'name': cf.feat.name,
                'description': cf.feat.description,
                'level_taken': cf.level_taken
            }
            for cf in char_feats
        ]
    
    def get_spells(self, obj):
        """Get spell information"""
        if not hasattr(obj, 'stats'):
            return None
        
        stats = obj.stats
        spells_data = obj.spells.all().order_by('level', 'name')
        
        # Group by spell level
        by_level = {}
        for spell in spells_data:
            level = spell.level
            if level not in by_level:
                by_level[level] = []
            
            by_level[level].append({
                'name': spell.name,
                'level': spell.level,
                'school': spell.school,
                'is_prepared': spell.is_prepared,
                'is_ritual': spell.is_ritual,
                'description': spell.description
            })
        
        return {
            'spell_slots': stats.spell_slots if hasattr(stats, 'spell_slots') else {},
            'spell_save_dc': stats.spell_save_dc,
            'spell_attack_bonus': stats.spell_attack_bonus,
            'spells_by_level': by_level
        }
    
    def get_equipment(self, obj):
        """Get equipped and carried items"""
        items = obj.character_items.all().select_related('item')
        
        equipped = []
        carried = []
        
        for char_item in items:
            item_data = {
                'name': char_item.item.name,
                'quantity': char_item.quantity,
                'weight': char_item.item.weight,
                'description': char_item.item.description
            }
            
            if char_item.is_equipped:
                item_data['slot'] = char_item.equipment_slot
                equipped.append(item_data)
            else:
                carried.append(item_data)
        
        # Calculate total weight
        total_weight = sum(
            (ci.item.weight or 0) * ci.quantity 
            for ci in items
        )
        
        return {
            'equipped': equipped,
            'carried': carried,
            'total_weight': total_weight
        }
    
    def get_multiclass_info(self, obj):
        """Get multiclass information if applicable"""
        from .models import CharacterClassLevel
        
        class_levels = CharacterClassLevel.objects.filter(character=obj).select_related('character_class')
        
        if class_levels.count() <= 1:
            return None
        
        return {
            'total_level': get_total_level(obj),
            'classes': [
                {
                    'class_name': cl.character_class.get_name_display(),
                    'level': cl.level,
                    'subclass': cl.subclass
                }
                for cl in class_levels
            ]
        }
    
    def get_proficiencies(self, obj):
        """Get all proficiencies (weapons, armor, tools, languages)"""
        profs = obj.proficiencies.all()
        
        by_type = {}
        for prof in profs:
            prof_type = prof.get_proficiency_type_display() if hasattr(prof, 'get_proficiency_type_display') else prof.proficiency_type
            
            if prof_type not in by_type:
                by_type[prof_type] = []
            
            # Add the appropriate name field
            name = prof.skill_name or prof.item_name or prof.language or 'Unknown'
            if name and name not in by_type[prof_type]:
                by_type[prof_type].append(name)
        
        return by_type
