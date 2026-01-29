from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance, CharacterItem,
    CharacterClassLevel
)
from .multiclassing import (
    can_multiclass_into, calculate_multiclass_spell_slots, get_multiclass_spellcasting_ability,
    get_multiclass_hit_dice, get_total_level, get_class_level, get_primary_class,
    MULTICLASS_PREREQUISITES
)
from .serializers import (
    CharacterSerializer, CharacterStatsSerializer, CharacterClassSerializer,
    CharacterRaceSerializer, CharacterBackgroundSerializer, CharacterProficiencySerializer,
    CharacterFeatureSerializer, CharacterSpellSerializer, CharacterResistanceSerializer
)
from .spell_management import (
    is_prepared_caster, is_known_caster, can_cast_rituals,
    calculate_spells_prepared, calculate_spells_known,
    get_wizard_spellbook_size, can_learn_spell, can_add_to_spellbook,
    get_prepared_spells, get_known_spells, get_spellbook_spells,
    can_cast_spell, get_spellcasting_ability
)
from campaigns.utils import calculate_spell_slots
from .inventory_management import (
    equip_item, unequip_item, get_equipped_items,
    calculate_total_weight, get_encumbrance_level, get_encumbrance_effects,
    get_equipped_weapon, get_equipped_armor, get_equipped_shield
)
from .equipment_endpoints import add_equipment_endpoints_to_viewset
from .spell_selection_endpoints import add_spell_selection_endpoints
from .spell_preparation_endpoints import add_spell_preparation_endpoints
from .hp_endpoints import add_hp_endpoints
from .rest_endpoints import add_rest_endpoints


@add_equipment_endpoints_to_viewset
@add_spell_selection_endpoints
@add_spell_preparation_endpoints
@add_hp_endpoints
@add_rest_endpoints
class CharacterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing player characters."""
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter characters to only show those owned by the current user with optimized queries"""
        return Character.objects.filter(user=self.request.user).select_related(
            'character_class',
            'race',
            'background',
            'stats'
        ).prefetch_related(
            'features',
            'proficiencies'
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Automatically set the user when creating a character"""
        character = serializer.save(user=self.request.user)
        # Note: Racial and background features are already applied in CharacterSerializer.create
    
    @action(detail=True, methods=['post'])
    def apply_racial_features(self, request, pk=None):
        """Apply racial features to a character (for existing characters that don't have them)"""
        character = self.get_object()
        
        from campaigns.racial_features_data import apply_racial_features_to_character
        
        try:
            # Check if character already has racial features
            existing_racial_features = CharacterFeature.objects.filter(
                character=character,
                feature_type='racial'
            ).count()
            
            if existing_racial_features > 0:
                return Response({
                    "message": f"{character.name} already has {existing_racial_features} racial features",
                    "features_count": existing_racial_features
                })
            
            # Apply racial features
            features = apply_racial_features_to_character(character)
            
            return Response({
                "message": f"Applied {len(features)} racial features to {character.name}",
                "features": [
                    {
                        'name': f.name,
                        'description': f.description,
                        'source': f.source
                    } for f in features
                ]
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to apply racial features: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_pending_spells(self, character, character_class, level, features_gained):
        """Helper to calculate pending spell choices on level up"""
        # Calculate pending spell choices
        if character_class.name.lower() == 'wizard':
             # Wizards gain 2 spells per level into their spellbook
             # Base 6 at level 1, +2 for each level after
             expected_min_spells = 6 + (2 * (level - 1))
             
             current_spellbook_count = CharacterSpell.objects.filter(
                character=character,
                in_spellbook=True
             ).count()
             
             diff = expected_min_spells - current_spellbook_count
             
             if diff > 0:
                 # Find max spell level available
                 max_spell_level = 1
                 if hasattr(character, 'stats') and character.stats.spell_slots:
                     for lvl, slots in character.stats.spell_slots.items():
                         if slots > 0:
                             max_spell_level = max(max_spell_level, int(lvl))
                 
                 pending_choices = {
                     'count': diff,
                     'max_level': max_spell_level,
                     'source': 'level_up',
                     'type': 'spellbook'
                 }
        elif character_class.name.lower() in ['bard', 'sorcerer', 'warlock', 'ranger']:
             from characters.spell_management import calculate_spells_known
             spells_known_limit = calculate_spells_known(character)
             # Use current class-specific known spells? 
             # Currently system assumes global known list but filters by class usually.
             # CharacterSpell has 'class' FK? No.
             # But calculate_spells_known returns TOTAL known.
             # Simplified check:
             current_spells_count = CharacterSpell.objects.filter(
                character=character,
                level__gt=0
             ).count()
             
             diff = spells_known_limit - current_spells_count
             if diff > 0:
                 max_spell_level = 1
                 if hasattr(character, 'stats') and character.stats.spell_slots:
                     for lvl, slots in character.stats.spell_slots.items():
                         if slots > 0:
                             max_spell_level = max(max_spell_level, int(lvl))
                 
                 pending_choices = {
                     'count': diff,
                     'max_level': max_spell_level,
                     'source': 'level_up',
                     'type': 'new_spell'
                 }

        elif character_class.name.lower() in ['paladin', 'cleric', 'druid']:
             # Prepared Casters: Prompt to prepare spells if limit increases
             # Paladins must be at least level 2
             if character_class.name.lower() == 'paladin' and level < 2:
                 pass
             else:
                 from characters.spell_management import calculate_spells_prepared
                 prepared_limit = calculate_spells_prepared(character)
                 
                 current_prepared_count = CharacterSpell.objects.filter(
                    character=character,
                    is_prepared=True
                 ).count()
                 
                 diff = prepared_limit - current_prepared_count
                 
                 if diff > 0:
                     max_spell_level = 1
                     if hasattr(character, 'stats') and character.stats.spell_slots:
                         for lvl, slots in character.stats.spell_slots.items():
                             if slots > 0:
                                 max_spell_level = max(max_spell_level, int(lvl))
                     
                     pending_choices = {
                         'count': diff,
                         'max_level': max_spell_level,
                         'source': 'level_up',
                         'type': 'new_spell'
                     }

        
        # If no leveled spell choices, check for Cantrips
        if not pending_choices:
            from characters.spell_management import calculate_cantrips_known
            cantrips_known_limit = calculate_cantrips_known(character)
            if cantrips_known_limit > 0:
                current_cantrips_count = CharacterSpell.objects.filter(
                    character=character,
                    level=0
                ).count()
                
                diff = cantrips_known_limit - current_cantrips_count
                if diff > 0:
                    pending_choices = {
                        'count': diff,
                        'max_level': 0,
                        'source': 'level_up',
                        'type': 'cantrip'
                    }

        if pending_choices:
            # Merge with existing pending if strictly needed, but usually overwrite or append?
            # Current logic overwrites.
            character.pending_spell_choices = pending_choices
            features_gained.append({
                'level': level,
                'name': f"Select {pending_choices['count']} {'Cantrip(s)' if pending_choices['type'] == 'cantrip' else 'New Spell(s)'}",
                'type': 'choice'
            })

    @action(detail=True, methods=['post'])
    def level_up(self, request, pk=None):
        """
        Level up a character with automatic stat updates.
        For multiclass characters, specify which class to level up.
        
        Automatically:
        - Updates HP (rolls hit dice + CON modifier)
        - Updates spell slots
        - Applies class features
        - Tracks pending ASI/Feat choices at levels 4, 8, 12, 16, 19
        - Prompts for subclass selection if needed
        
        Request body (optional):
        {
            "class_id": 2,  // ID of class to level up (for multiclass)
            "class_name": "Fighter"  // Or name of class
        }
        """
        import random
        from campaigns.utils import calculate_spell_slots, get_spellcasting_ability, calculate_spell_save_dc, calculate_spell_attack_bonus
        from campaigns.class_features_data import get_class_features, get_subclass_features
        from characters.spell_management import calculate_spells_known
        
        def dlog(msg):
            print(f"[LEVEL_UP_DEBUG] {msg}")  # Console output
            try:
                import datetime
                import os
                log_path = os.path.join(os.getcwd(), 'debug_level_up.log')
                with open(log_path, 'a') as f:
                    f.write(f"{datetime.datetime.now()}: {msg}\n")
            except Exception as e:
                print(f"[DLOG_ERROR] {str(e)}")
        
        character = self.get_object()
        
        old_level = character.level
        
        # Check if multiclass level-up
        class_id = request.data.get('class_id')
        class_name = request.data.get('class_name')
        target_class = None
        
        if class_id:
            try:
                target_class = CharacterClass.objects.get(pk=class_id)
            except CharacterClass.DoesNotExist:
                return Response(
                    {"error": f"Class with id {class_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif class_name:
            try:
                target_class = CharacterClass.objects.get(name=class_name.lower())
            except CharacterClass.DoesNotExist:
                return Response(
                    {"error": f"Class '{class_name}' not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # If multiclassing, add level to that class
        if target_class:

            # First check if we already have this class
            try:
                class_level = CharacterClassLevel.objects.get(
                    character=character,
                    character_class=target_class
                )
                # Already has this class, just level it up
                if class_level.level >= 20:
                    return Response(
                        {"error": f"Cannot level up {target_class.get_name_display()} beyond level 20"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                old_class_level = class_level.level
                class_level.level += 1
                class_level.save()
                new_class_level = class_level.level
                
            except CharacterClassLevel.DoesNotExist:
                # New class (or missing primary class entry)
                
                # If this is the character's primary class, allowing leveling it up regardless of stats
                # This fixes issues where legacy characters might be missing the ClassLevel entry
                is_primary = (character.character_class and target_class.id == character.character_class.id)
                
                if not is_primary:
                    # Check prerequisites
                    can_multiclass, reason = can_multiclass_into(character, target_class.name)
                    if not can_multiclass:
                        return Response(
                            {"error": reason},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Create Level 1 (or restore primary class level)
                # If restoring primary, we should probably set it to current level?
                # But typically level_up is called to ADD a level.
                # If the user is Level 1 Fighter and calls this, they want to become Level 2.
                # If we create Level 1 now, they become Fighter 1 (again?).
                # Wait, if they are Fighter 1, and we create Fighter 1, then we increment?
                
                # Actually, if CharacterClassLevel was missing, they technically have 0 class levels registered.
                # So starting at 1 is correct for the object.
                # But wait, if character.level is 1, and we create level 1...
                # The total level calculation sums class levels.
                # If we create level 1, total level becomes 1.
                # Then we fall through... wait, do we fall through?
                
                # The code below:
                # class_level = CharacterClassLevel.objects.create(..., level=1)
                # old_class_level = 0
                # new_class_level = 1
                
                # Then later:
                # total_level = get_total_level(character)
                # character.level = total_level
                
                start_level = 1
                if is_primary and character.level > 0:
                     # If restoring mismatch, maybe we should respect current level?
                     # But level_up implies +1.
                     # If they were Level 1, we create Level 1.
                     # But the user wants to go to Level 2.
                     # If we just create Level 1, they "level up" to Level 1 (no change).
                     # So if is_primary, maybe we should init at character.level + 1?
                     # or init at character.level, then increment?
                     pass
                     
                class_level = CharacterClassLevel.objects.create(
                    character=character,
                    character_class=target_class,
                    level=1
                )
                old_class_level = 0
                new_class_level = 1
                
                # If this was a primary class restore, we might want to catch up?
                # But safe usage is just treating it as level 1 gain.
                # If they were Level 1 (stored on char), and we create Level 1 class level.
                # They are now Level 1.
                # They pressed "Level Up". They expect Level 2.
                # But since they had "0" class levels, they just gained their first class level.
                # It's a bit weird but safer than assuming.
                # Let's just allow the creation. Next click will take them to 2.
                # OR we could be smart:
                
                if is_primary and character.level >= 1:
                     # They are already level X, but missing class record.
                     # We should probably set the class record to current level + 1?
                     # No, because the rest of the logic assumes we just gained ONE level.
                     # "features_gained" will calculate for the new level.
                     pass
            
            # Update total level
            total_level = get_total_level(character)
            character.level = total_level
            
            # Use multiclass spell slot calculation
            from .multiclassing import calculate_multiclass_spell_slots
            new_slots = calculate_multiclass_spell_slots(character)
            
            # Calculate HP increase for this class level
            hp_gain = 0
            if hasattr(character, 'stats'):
                hit_dice_type = target_class.hit_dice
                if 'd' in hit_dice_type:
                    die_part = hit_dice_type.split('d')[-1]
                    die_size = int(die_part)
                else:
                    die_size = 8
                
                roll = random.randint(1, die_size)
                from core.dnd_utils import calculate_ability_modifier
                con_mod = calculate_ability_modifier(character.stats.constitution)
                hp_gain = max(1, roll + con_mod)
                
                character.stats.max_hit_points += hp_gain
                character.stats.hit_points += hp_gain  # Full heal on level up
                character.stats.save()
            
            # Apply class features for this class level
            features_gained = []
            class_features = get_class_features(target_class.name, new_class_level, ruleset=character.ruleset_version)
            for feature_data in class_features:
                CharacterFeature.objects.get_or_create(
                    character=character,
                    name=feature_data['name'],
                    defaults={
                        'feature_type': 'class',
                        'description': feature_data['description'],
                        'source': f"{target_class.get_name_display()} Level {new_class_level}",
                        'options': feature_data.get('options', []),
                        'choice_limit': feature_data.get('choice_limit', 1)
                    }
                )
                features_gained.append({
                    'level': new_class_level,
                    'name': feature_data['name'],
                    'type': 'class'
                })
            
            # Apply subclass features if applicable
            if class_level.subclass:
                subclass_features = get_subclass_features(class_level.subclass, new_class_level, ruleset=character.ruleset_version)
                for feature_data in subclass_features:
                    CharacterFeature.objects.get_or_create(
                        character=character,
                        name=feature_data['name'],
                        defaults={
                            'feature_type': 'class',
                            'description': feature_data['description'],
                            'source': f"{class_level.subclass} Level {new_class_level}",
                            'options': feature_data.get('options', []),
                            'choice_limit': feature_data.get('choice_limit', 1)
                        }
                    )
                    features_gained.append({
                        'level': new_class_level,
                        'name': feature_data['name'],
                        'type': 'subclass'
                    })
            
            # Handle Ability Score Improvements (ASI) based on CLASS level
            asi_levels = [4, 8, 12, 16, 19]
            # Fighter gets extra ASIs at 6 and 14
            if target_class.name.lower() == 'fighter':
                asi_levels.extend([6, 14])
            # Rogue gets extra ASI at 10
            elif target_class.name.lower() == 'rogue':
                asi_levels.append(10)
                
            if new_class_level in asi_levels:
                # We append the NEW level provided it triggers an ASI
                # We allow multiple same-level ASIs if from different sources (though list is simple ints)
                # But to avoid "already pending" check blocking legitimate 2nd ASI at same level, we just append.
                character.pending_asi_levels.append(new_class_level)
            
            # Check if subclass selection is needed
            subclass_levels_2014 = {
                'Cleric': 1,
                'Druid': 2,
                'Wizard': 2,
                'Sorcerer': 1,
                'Warlock': 1,
                'Fighter': 3,
                'Barbarian': 3,
                'Bard': 3,
                'Ranger': 3,
                'Rogue': 3,
                'Monk': 3,
                'Paladin': 3,
                'Artificer': 3,
                'Blood Hunter': 3,
                'Paladin (UA)': 3,
                'Ranger (UA)': 3
            }
            c_name = target_class.name
            
            if character.ruleset_version == '2024':
                 trigger_level = 3
            else:
                trigger_level = subclass_levels_2014.get(c_name, 3)
                # Handle casing fallback
                if c_name not in subclass_levels_2014 and c_name.title() in subclass_levels_2014:
                    trigger_level = subclass_levels_2014[c_name.title()]
                
            if new_class_level == trigger_level and not class_level.subclass:
                character.pending_subclass_selection = True
                
            # Explicitly save character validation flags
            character.save()
            
            # Update spell slots
            if new_slots and hasattr(character, 'stats'):
                character.stats.spell_slots = new_slots
                spellcasting_ability = get_multiclass_spellcasting_ability(character)
                if spellcasting_ability:
                    character.stats.spell_save_dc = calculate_spell_save_dc(character, spellcasting_ability)
                    character.stats.spell_attack_bonus = calculate_spell_attack_bonus(character, spellcasting_ability)
                character.stats.save()
            
            # Calculate pending spells for the leveled-up class
            try:
                self._calculate_pending_spells(character, target_class, new_class_level, features_gained)
            except Exception as e:
                print(f"Error calculating pending spells: {str(e)}")

            character.save()
            
            serializer = self.get_serializer(character)
            return Response({
                "message": f"{character.name} gained a level in {target_class.get_name_display()}! Total level: {total_level}",
                "character": serializer.data,
                "class_levels": self._get_class_levels_data(character),
                "features_gained": features_gained,
                "hp_gain": hp_gain if hasattr(character, 'stats') else None,
                "spell_slots": new_slots
            })
        
        # Single-class level-up
        if character.level >= 20:
            return Response(
                {"error": "Character is already at maximum level (20)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_level = character.level + 1
        
        # Ensure primary class has a CharacterClassLevel entry
        primary_class = character.character_class
        class_level, created = CharacterClassLevel.objects.get_or_create(
            character=character,
            character_class=primary_class,
            defaults={'level': new_level}
        )
        if not created:
            class_level.level = new_level
            class_level.save()
        
        # Calculate HP increase
        hp_gain = 0
        if hasattr(character, 'stats'):
            hit_dice_type = primary_class.hit_dice
            if 'd' in hit_dice_type:
                die_part = hit_dice_type.split('d')[-1]
                die_size = int(die_part)
            else:
                die_size = 8
            
            roll = random.randint(1, die_size)
            from core.dnd_utils import calculate_ability_modifier
            con_mod = calculate_ability_modifier(character.stats.constitution)
            hp_gain = max(1, roll + con_mod)
            
            character.stats.max_hit_points += hp_gain
            character.stats.hit_points += hp_gain  # Full heal on level up
            
            # Update spell slots
            class_name = primary_class.name
            new_slots = calculate_spell_slots(class_name, new_level)
            if new_slots:
                character.stats.spell_slots = new_slots
                
                # Update spell save DC and spell attack bonus
                spellcasting_ability = get_spellcasting_ability(class_name)
                if spellcasting_ability:
                    character.stats.spell_save_dc = calculate_spell_save_dc(character, spellcasting_ability)
                    character.stats.spell_attack_bonus = calculate_spell_attack_bonus(character, spellcasting_ability)
            
            character.stats.save()
        
        # Update character level
        character.level = new_level
        
        # Handle Ability Score Improvements (ASI) at levels 4, 8, 12, 16, 19
        asi_levels = [4, 8, 12, 16, 19]
        if new_level in asi_levels:
            if new_level not in character.pending_asi_levels:
                character.pending_asi_levels.append(new_level)
        
        # Check if subclass selection is needed
        subclass_levels_2014 = {
            'Cleric': 1,
            'Druid': 2,
            'Wizard': 2,
            'Sorcerer': 1,
            'Warlock': 1,
        }
        
        default_subclass_level = 3
        # Ensure we check against the actual class name casing or fallback to title case
        class_name = primary_class.name
        
        if character.ruleset_version == '2024':
            # In 2024 rules, all standard classes choose subclass at Level 3
            subclass_level = 3
        else:
            subclass_level = subclass_levels_2014.get(class_name, default_subclass_level)
            if class_name not in subclass_levels_2014 and class_name.title() in subclass_levels_2014:
                 subclass_level = subclass_levels_2014[class_name.title()]
        
        if new_level >= subclass_level and not character.subclass:
            character.pending_subclass_selection = True
        
        # Apply class features
        features_gained = []
        class_features = get_class_features(primary_class.name, new_level, ruleset=character.ruleset_version)
        for feature_data in class_features:
            CharacterFeature.objects.get_or_create(
                character=character,
                name=feature_data['name'],
                defaults={
                    'feature_type': 'class',
                    'description': feature_data['description'],
                    'source': f"{primary_class.get_name_display()} Level {new_level}"
                }
            )
            features_gained.append({
                'level': new_level,
                'name': feature_data['name'],
                'type': 'class'
            })
        
        # Apply subclass features if character has a subclass
        if character.subclass:
            subclass_features = get_subclass_features(character.subclass, new_level, ruleset=character.ruleset_version)
            for feature_data in subclass_features:
                CharacterFeature.objects.get_or_create(
                    character=character,
                    name=feature_data['name'],
                    defaults={
                        'feature_type': 'class',
                        'description': feature_data['description'],
                        'source': f"{character.subclass} Level {new_level}"
                    }
                )
                features_gained.append({
                    'level': new_level,
                    'name': feature_data['name'],
                    'type': 'subclass'
                })
        
        # Calculate pending spell choices using helper
        try:
            self._calculate_pending_spells(character, primary_class, new_level, features_gained)
        except Exception as e:
            print(f"Error calculating pending spells (Single Class): {str(e)}")
        
        character.save()
        dlog(f"DEBUG: Saved Character {character.id}. Pending field in DB: {character.pending_spell_choices}")
        
        serializer = self.get_serializer(character)
        return Response({
            "message": f"{character.name} leveled up to level {new_level}!",
            "character": serializer.data,
            "class_levels": self._get_class_levels_data(character),
            "features_gained": features_gained,
            "hp_gain": hp_gain,
            "spell_slots": new_slots if hasattr(character, 'stats') else None,
            "pending_asi": new_level in asi_levels,
            "pending_subclass": character.pending_subclass_selection,
            "pending_asi_levels": character.pending_asi_levels
        })
    
    def _get_class_levels_data(self, character):
        """Get class levels data for character"""
        class_levels = CharacterClassLevel.objects.filter(character=character)
        return [
            {
                'class_id': cl.character_class.id,
                'class_name': cl.character_class.get_name_display(),
                'level': cl.level,
                'subclass': cl.subclass
            }
            for cl in class_levels
        ]
    
    @action(detail=True, methods=['post'])
    def apply_asi(self, request, pk=None):
        """
        Apply Ability Score Improvement (ASI) or Feat for a standalone character.
        
        Request body for ASI:
        {
            "level": 4,
            "choice_type": "asi",
            "asi_choice": {
                "strength": 2  // +2 to one stat
                // OR
                "strength": 1, "dexterity": 1  // +1 to two stats
            }
        }
        
        Request body for Feat:
        {
            "level": 4,
            "choice_type": "feat",
            "feat_id": 5  // ID of the feat to take
        }
        """
        from .models import Feat, CharacterFeat
        
        character = self.get_object()
        level = request.data.get('level')
        choice_type = request.data.get('choice_type', 'asi')  # 'asi' or 'feat'
        
        if not level:
            return Response(
                {"error": "level is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if this level has pending ASI
        if level not in character.pending_asi_levels:
            return Response(
                {"error": f"No pending ASI/Feat choice for level {level}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if choice_type == 'feat':
            # Handle feat selection
            feat_id = request.data.get('feat_id')
            if not feat_id:
                return Response(
                    {"error": "feat_id is required when choice_type is 'feat'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                feat = Feat.objects.get(pk=feat_id)
            except Feat.DoesNotExist:
                return Response(
                    {"error": f"Feat with id {feat_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check prerequisites
            is_eligible, reason = feat.check_prerequisites(character)
            if not is_eligible:
                return Response(
                    {"error": f"Feat prerequisites not met: {reason}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get feat config (options/limits)
            from campaigns.feat_data import get_feat_config
            feat_config = get_feat_config(feat.name)
            
            # Check if character already has this feat (and it's not repeatable)
            if CharacterFeat.objects.filter(character=character, feat=feat).exists():
                if not feat_config.get('repeatable'):
                    return Response(
                        {"error": f"Character already has the feat: {feat.name}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Apply feat
            CharacterFeat.objects.create(
                character=character,
                feat=feat,
                level_taken=level,
                options=feat_config.get('options', []),
                choice_limit=feat_config.get('choice_limit', 1)
            )
            
            # Create CharacterFeature instance
            feature_name = feat.name
            if feat_config.get('repeatable'):
                # Find next available suffix if duplicates exist
                base_name = feat.name
                count = CharacterFeature.objects.filter(character=character, name__startswith=base_name).count()
                if count > 0:
                     feature_name = f"{base_name} ({count + 1})"
            
            CharacterFeature.objects.create(
                character=character,
                name=feature_name,
                feature_type='feat',
                description=feat.description,
                source=f"Feat (Level {level})",
                options=feat_config.get('options', []),
                choice_limit=feat_config.get('choice_limit', 1)
            )
            
            # Apply ability score increase if feat grants one
            if feat.ability_score_increase and hasattr(character, 'stats'):
                stats = character.stats
                ability_map = {
                    'STR': 'strength',
                    'DEX': 'dexterity',
                    'CON': 'constitution',
                    'INT': 'intelligence',
                    'WIS': 'wisdom',
                    'CHA': 'charisma',
                }
                ability_field = ability_map.get(feat.ability_score_increase.upper())
                if ability_field:
                    current_value = getattr(stats, ability_field)
                    new_value = min(20, current_value + 1)  # Cap at 20
                    setattr(stats, ability_field, new_value)
                    setattr(stats, ability_field, new_value)
                    stats.save()
            
            # Check for feats that grant languages
            # MVP: Hardcode check for 'Linguist'
            if feat.name.lower() == 'linguist':
                character.pending_language_choices += 3
                character.save(update_fields=['pending_language_choices'])
                
            # Remove this level from pending ASI
            character.pending_asi_levels.remove(level)
            character.save()
            
            return Response({
                "message": f"Feat '{feat.name}' applied successfully for level {level}",
                "feat": {
                    "id": feat.id,
                    "name": feat.name,
                    "description": feat.description
                },
                "remaining_pending_asi": character.pending_asi_levels,
                "ability_score_increase": feat.ability_score_increase if feat.ability_score_increase else None
            })
        
        else:
            # Handle ASI selection
            if not hasattr(character, 'stats'):
                return Response(
                    {"error": "Character must have stats"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            asi_choice = request.data.get('asi_choice', {})
            
            if not asi_choice:
                return Response(
                    {"error": "asi_choice is required when choice_type is 'asi'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate ASI choice
            total_increase = sum(asi_choice.values())
            if total_increase != 2:
                return Response(
                    {"error": "ASI must total +2 (either +2 to one stat or +1 to two stats)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(asi_choice) > 2:
                return Response(
                    {"error": "Can only increase 1 or 2 different abilities"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply ASI
            stats = character.stats
            ability_map = {
                'strength': 'strength',
                'dexterity': 'dexterity',
                'constitution': 'constitution',
                'intelligence': 'intelligence',
                'wisdom': 'wisdom',
                'charisma': 'charisma',
            }
            
            applied_changes = {}
            for ability_name, increase in asi_choice.items():
                ability_field = ability_map.get(ability_name.lower())
                if not ability_field:
                    return Response(
                        {"error": f"Invalid ability score: {ability_name}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if increase not in [1, 2]:
                    return Response(
                        {"error": f"Ability score increase must be 1 or 2, got {increase}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                current_value = getattr(stats, ability_field)
                new_value = min(20, current_value + increase)  # Cap at 20
                setattr(stats, ability_field, new_value)
                applied_changes[ability_name] = {
                    'old': current_value,
                    'new': new_value,
                    'increase': increase
                }
            
            stats.save()
            
            # Remove this level from pending ASI
            character.pending_asi_levels.remove(level)
            character.save()
            
            return Response({
                "message": "Ability scores improved!",
                "changes": applied_changes,
                "character": CharacterSerializer(character).data
            })
            
    @action(detail=True, methods=['get'])
    def eligible_subclasses(self, request, pk=None):
        """Get list of eligible subclasses for the character (handling multiclassing)"""
        character = self.get_object()
        from campaigns.class_features_data import AVAILABLE_SUBCLASSES_2014, AVAILABLE_SUBCLASSES_2024, SUBCLASS_FEATURES_2014, SUBCLASS_FEATURES_2024
        
        # Select ruleset data
        if character.ruleset_version == '2024':
            AVAILABLE_SUBCLASSES = AVAILABLE_SUBCLASSES_2024
            features_source = SUBCLASS_FEATURES_2024
        else:
            AVAILABLE_SUBCLASSES = AVAILABLE_SUBCLASSES_2014
            features_source = SUBCLASS_FEATURES_2014
        
        # Subclass selection levels
        subclass_levels = {
            'Cleric': 1,
            'Druid': 2,
            'Wizard': 2,
            'Sorcerer': 1,
            'Warlock': 1,
            'Fighter': 3,
            'Barbarian': 3,
            'Bard': 3,
            'Ranger': 3,
            'Rogue': 3,
            'Monk': 3,
            'Paladin': 3,
            'Artificer': 3, # Added Artificer
            'Blood Hunter': 3, # Added Blood Hunter
            'Paladin (UA)': 3, # Added Paladin (UA)
            'Ranger (UA)': 3, # Added Ranger (UA)
        }
        
        # Find which class needs a subclass
        target_class_name = None
        
        # Check all class levels
        for class_level in character.class_levels.all():
            c_name = class_level.character_class.name
            # Handle casing
            level_trigger = subclass_levels.get(c_name, 3)
            # Try title case if not found
            if c_name not in subclass_levels:
                c_title = c_name.title()
                if c_title in subclass_levels:
                    level_trigger = subclass_levels[c_title]
                    c_name = c_title # Use title case for lookup

            if class_level.level >= level_trigger and not class_level.subclass:
                target_class_name = c_name
                break
        
        if not target_class_name:
            # Fallback to primary if nothing specific found (though this shouldn't happen if pending_subclass_selection is true)
            # This case might occur if the character has no class levels yet, or if all classes already have subclasses
            # or if pending_subclass_selection is false.
            # If character.character_class is None (e.g., new character), this will fail.
            # Let's ensure we have a class to fall back on.
            if character.character_class:
                target_class_name = character.character_class.name.title()
            else:
                return Response({
                    "available_subclasses": [],
                    "class_name": None,
                    "message": "Character has no class to select a subclass for."
                }, status=status.HTTP_400_BAD_REQUEST)


        # Normalize lookup
        lookup_name = target_class_name
        if lookup_name not in AVAILABLE_SUBCLASSES and lookup_name.title() in AVAILABLE_SUBCLASSES:
            lookup_name = lookup_name.title()

        if lookup_name not in AVAILABLE_SUBCLASSES:
            return Response({
                "available_subclasses": [],
                "class_name": target_class_name,
                "message": f"No subclasses available for class '{target_class_name}'"
            })
            
        options = []
        options = []
        for sub_name in AVAILABLE_SUBCLASSES[lookup_name]:
            description = "No description available."
            if sub_name in features_source:
                # Try to get a description from the first feature at the earliest level
                levels = sorted(features_source[sub_name].keys())
                if levels and features_source[sub_name][levels[0]]:
                     for feature in features_source[sub_name][levels[0]]:
                         if 'description' in feature:
                             description = feature['description']
                             break
            
            
            options.append({
                "name": sub_name,
                "description": description
            })
            
        return Response({
            "is_eligible": character.pending_subclass_selection,
            "class_name": target_class_name,
            "available_subclasses": options
        })
        
    @action(detail=True, methods=['post'])
    def choose_subclass(self, request, pk=None):
        """Choose a subclass for the character"""
        try:
            character = self.get_object()
            subclass_name = request.data.get('subclass')
            
            if not subclass_name:
                 return Response({"error": "Subclass name is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not character.pending_subclass_selection and character.subclass:
                return Response({"error": "Character already has a subclass"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Verify eligibility
            from campaigns.class_features_data import AVAILABLE_SUBCLASSES_2014, AVAILABLE_SUBCLASSES_2024
    
            # Select ruleset data
            if character.ruleset_version == '2024':
                AVAILABLE_SUBCLASSES = AVAILABLE_SUBCLASSES_2024
            else:
                AVAILABLE_SUBCLASSES = AVAILABLE_SUBCLASSES_2014
            
            class_name = character.character_class.name
            # Handle case mismatch
            if class_name not in AVAILABLE_SUBCLASSES:
                if class_name.title() in AVAILABLE_SUBCLASSES:
                    class_name = class_name.title()
            
            if class_name not in AVAILABLE_SUBCLASSES or subclass_name not in AVAILABLE_SUBCLASSES[class_name]:
                return Response({"error": f"Invalid subclass '{subclass_name}' for class '{class_name}'"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Apply subclass to Character model
            character.subclass = subclass_name
            character.pending_subclass_selection = False
            character.save()
            
            # Sync subclass to CharacterClassLevel
            from .models import CharacterClassLevel
            if character.character_class:
                class_level = CharacterClassLevel.objects.filter(
                    character=character, 
                    character_class=character.character_class
                ).first()
                if class_level:
                    class_level.subclass = subclass_name
                    class_level.save()
    
            # Sync selection to the defining Class Feature
            selector_feature_map = {
                'Fighter': 'Martial Archetype',
                'Barbarian': 'Primal Path',
                'Rogue': 'Roguish Archetype',
                'Sorcerer': 'Sorcerous Origin',
                'Warlock': 'Otherworldly Patron',
                'Cleric': 'Divine Domain',
                'Druid': 'Druid Circle',
                'Bard': 'Bard College',
                'Monk': 'Monastic Tradition',
                'Paladin': 'Sacred Oath',
                'Ranger': 'Ranger Archetype',
                'Wizard': 'Arcane Tradition',
            }
            
            selector_name = selector_feature_map.get(character.character_class.name.title())
            if selector_name:
                feature = CharacterFeature.objects.filter(character=character, name=selector_name).first()
                if feature:
                    feature.selection = [subclass_name]
                    feature.save()
            
            # Apply subclass features immediately
            from campaigns.class_features_data import get_all_subclass_features_up_to_level
            features_by_level = get_all_subclass_features_up_to_level(
                subclass_name, 
                character.level, 
                ruleset=character.ruleset_version
            )
            
            for level, features in features_by_level.items():
                for feature_data in features:
                    CharacterFeature.objects.get_or_create(
                        character=character,
                        name=feature_data['name'],
                        defaults={
                            'feature_type': 'class',
                            'description': feature_data['description'],
                            'source': f"{subclass_name} Level {level}",
                            'options': feature_data.get('options', []),
                            'choice_limit': feature_data.get('choice_limit', 1)
                        }
                    )
            
            return Response({
                "message": f"Subclass '{subclass_name}' selected!",
                "character": CharacterSerializer(character).data
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def eligible_languages(self, request, pk=None):
        """Get languages the character does not already have"""
        character = self.get_object()
        from bestiary.models import Language
        from bestiary.serializers import LanguageSerializer
        
        # Get current languages
        known_language_ids = character.proficiencies.filter(
            proficiency_type='language',
            language__isnull=False
        ).values_list('language_id', flat=True)
        
        # Get available languages
        available = Language.objects.exclude(id__in=known_language_ids).order_by('name')
        
        return Response(LanguageSerializer(available, many=True).data)

    @action(detail=True, methods=['post'])
    def choose_languages(self, request, pk=None):
        """Choose languages for pending choices"""
        character = self.get_object()
        
        if character.pending_language_choices <= 0:
             return Response({"error": "No pending language choices"}, status=status.HTTP_400_BAD_REQUEST)
             
        language_ids = request.data.get('language_ids', [])
        
        if not language_ids:
            return Response({"error": "No languages selected"}, status=status.HTTP_400_BAD_REQUEST)
            
        if len(language_ids) > character.pending_language_choices:
            return Response({"error": f"You can only choose {character.pending_language_choices} languages"}, status=status.HTTP_400_BAD_REQUEST)
            
        from bestiary.models import Language
        from .models import CharacterProficiency
        
        languages = Language.objects.filter(id__in=language_ids)
        if len(languages) != len(language_ids):
             return Response({"error": "Invalid language IDs"}, status=status.HTTP_400_BAD_REQUEST)
             
        # Add languages
        for lang in languages:
            CharacterProficiency.objects.create(
                character=character,
                proficiency_type='language',
                language=lang,
                source='Feat Choice' # Could be more specific if tracked
            )
            
        # Decrement pending
        character.pending_language_choices -= len(languages)
        character.save(update_fields=['pending_language_choices'])
        
        return Response({
            "message": "Languages added successfully",
            "pending_language_choices": character.pending_language_choices,
            "character": CharacterSerializer(character).data
        })

    
    @action(detail=True, methods=['get'])
    def available_feats(self, request, pk=None):
        """List all available feats with eligibility checking for this character"""
        from .models import Feat
        from .serializers import FeatSerializer
        
        character = self.get_object()
        all_feats = Feat.objects.all().order_by('name')
        
        serializer = FeatSerializer(
            all_feats,
            many=True,
            context={'character': character}
        )
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def multiclass_info(self, request, pk=None):
        """Get multiclassing information for character"""
        character = self.get_object()
        
        # Get current class levels
        class_levels = CharacterClassLevel.objects.filter(character=character)
        current_classes = [
            {
                'class_id': cl.character_class.id,
                'class_name': cl.character_class.get_name_display(),
                'level': cl.level,
                'subclass': cl.subclass
            }
            for cl in class_levels
        ]
        
        # Get total level
        total_level = get_total_level(character)
        
        # Get spellcasting info
        spellcasting_ability = get_multiclass_spellcasting_ability(character)
        spell_slots = calculate_multiclass_spell_slots(character)
        
        # Get hit dice
        hit_dice = get_multiclass_hit_dice(character)
        
        # Get available classes for multiclassing
        all_classes = CharacterClass.objects.all()
        available_classes = []
        
        for char_class in all_classes:
            # Skip if already has this class
            if CharacterClassLevel.objects.filter(character=character, character_class=char_class).exists():
                continue
            
            can_multiclass, reason = can_multiclass_into(character, char_class.name)
            available_classes.append({
                'class_id': char_class.id,
                'class_name': char_class.get_name_display(),
                'can_multiclass': can_multiclass,
                'reason': reason if not can_multiclass else None,
                'prerequisites': MULTICLASS_PREREQUISITES.get(char_class.name, {})
            })
        
        return Response({
            'total_level': total_level,
            'current_classes': current_classes,
            'spellcasting': {
                'ability': spellcasting_ability,
                'spell_slots': spell_slots
            },
            'hit_dice': hit_dice,
            'available_classes': available_classes
        })
    
    @action(detail=True, methods=['post'])
    def check_multiclass(self, request, pk=None):
        """Check if character can multiclass into a specific class"""
        character = self.get_object()
        class_id = request.data.get('class_id')
        class_name = request.data.get('class_name')
        
        if not class_id and not class_name:
            return Response(
                {"error": "Either class_id or class_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if class_id:
                target_class = CharacterClass.objects.get(pk=class_id)
            else:
                target_class = CharacterClass.objects.get(name=class_name.lower())
        except CharacterClass.DoesNotExist:
            return Response(
                {"error": "Class not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        can_multiclass, reason = can_multiclass_into(character, target_class.name)
        
        return Response({
            'class_id': target_class.id,
            'class_name': target_class.get_name_display(),
            'can_multiclass': can_multiclass,
            'reason': reason,
            'prerequisites': MULTICLASS_PREREQUISITES.get(target_class.name, {})
        })
    
    @action(detail=True, methods=['post'])
    def take_damage(self, request, pk=None):
        """Apply damage to a character"""
        character = self.get_object()
        try:
            damage = int(request.data.get('damage', 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Damage must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if damage < 0:
            return Response(
                {"error": "Damage must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = character.stats
        stats.hit_points = max(0, stats.hit_points - damage)
        stats.save()
        
        serializer = CharacterStatsSerializer(stats)
        return Response({
            "message": f"{character.name} took {damage} damage. HP: {stats.hit_points}/{stats.max_hit_points}",
            "stats": serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def sheet(self, request, pk=None):
        """
        Get comprehensive character sheet data for display.
        
        GET /api/characters/{id}/sheet/
        
        Returns everything needed to display a complete character sheet.
        """
        from .character_sheet_serializer import CharacterSheetSerializer
        
        character = self.get_object()
        serializer = CharacterSheetSerializer(character)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def heal(self, request, pk=None):
        """Heal a character"""
        character = self.get_object()
        try:
            amount = int(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Heal amount must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount < 0:
            return Response(
                {"error": "Heal amount must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = character.stats
        stats.hit_points = min(stats.max_hit_points, stats.hit_points + amount)
        stats.save()
        
        serializer = CharacterStatsSerializer(stats)
        return Response({
            "message": f"{character.name} healed {amount} HP. HP: {stats.hit_points}/{stats.max_hit_points}",
            "stats": serializer.data
        })
    
    @action(detail=True, methods=['get', 'post'])
    def inventory(self, request, pk=None):
        """Get or add items to character inventory"""
        character = self.get_object()
        
        if request.method == 'GET':
            # Get inventory
            items = CharacterItem.objects.filter(character=character)
            inventory_data = []
            for item in items:
                inventory_data.append({
                    'id': item.id,
                    'item': {
                        'id': item.item.id,
                        'name': item.item.name,
                        'category': item.item.category.name if item.item.category else None,
                        'weight': float(item.item.weight) if item.item.weight else 0,
                    },
                    'quantity': item.quantity,
                    'is_equipped': item.is_equipped,
                    'equipment_slot': item.equipment_slot,
                    'equipment_slot_display': item.get_equipment_slot_display(),
                })
            
            # Get encumbrance info
            total_weight = calculate_total_weight(character)
            encumbrance = get_encumbrance_level(character)
            encumbrance_effects = get_encumbrance_effects(character)
            capacity = calculate_carrying_capacity(character)
            
            return Response({
                'inventory': inventory_data,
                'encumbrance': {
                    'total_weight': total_weight,
                    'level': encumbrance,
                    'capacity': capacity,
                    'effects': encumbrance_effects
                },
                'equipped_items': {
                    'weapon': get_equipped_weapon(character).name if get_equipped_weapon(character) else None,
                    'armor': get_equipped_armor(character).name if get_equipped_armor(character) else None,
                    'shield': get_equipped_shield(character).name if get_equipped_shield(character) else None,
                }
            })
        
        elif request.method == 'POST':
            # Add item to inventory
            item_id = request.data.get('item_id')
            quantity = int(request.data.get('quantity', 1))
            equipment_slot = request.data.get('equipment_slot', 'inventory')
            
            if not item_id:
                return Response(
                    {"error": "Missing 'item_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from items.models import Item
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                return Response(
                    {"error": "Item not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if character already has this item in this slot
            character_item, created = CharacterItem.objects.get_or_create(
                character=character,
                item=item,
                equipment_slot=equipment_slot,
                defaults={'quantity': quantity}
            )
            
            if not created:
                character_item.quantity += quantity
                character_item.save()
            
            return Response({
                "message": f"Added {quantity}x {item.name} to {character.name}'s inventory",
                "character_item": {
                    'id': character_item.id,
                    'item': item.name,
                    'quantity': character_item.quantity,
                    'equipment_slot': character_item.equipment_slot,
                }
            })
    
    @action(detail=True, methods=['post'])
    def equip_item(self, request, pk=None):
        """
        Equip an item to a character.
        
        Request body:
        {
            "item_id": 1,
            "slot": "main_hand"  // Optional, defaults based on item type
        }
        """
        character = self.get_object()
        character_item_id = request.data.get('character_item_id')
        equipment_slot = request.data.get('equipment_slot')
        
        if not character_item_id:
            return Response(
                {"error": "Missing 'character_item_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_item = CharacterItem.objects.get(pk=character_item_id, character=character)
        except CharacterItem.DoesNotExist:
            return Response(
                {"error": "Item not found in character's inventory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use inventory management utility
        # If equipment_slot is not provided in request, we check the item's current slot
        # But if current slot is 'inventory', we default to 'main_hand' which triggers auto-detection
        slot = equipment_slot
        if not slot:
            if character_item.equipment_slot and character_item.equipment_slot != 'inventory':
                slot = character_item.equipment_slot
            else:
                slot = 'main_hand'
                
        success, message, char_item = equip_item(character, character_item.item, slot)
        
        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get encumbrance info
        total_weight = calculate_total_weight(character)
        encumbrance = get_encumbrance_level(character)
        encumbrance_effects = get_encumbrance_effects(character)
        
        return Response({
            "message": message,
            "character_item": {
                'id': char_item.id,
                'item': char_item.item.name,
                'equipment_slot': char_item.equipment_slot,
                'is_equipped': char_item.is_equipped,
            },
            "encumbrance": {
                'level': encumbrance,
                'total_weight': total_weight,
                'effects': encumbrance_effects
            }
        })
    
    @action(detail=True, methods=['post'])
    def unequip_item(self, request, pk=None):
        """Unequip an item"""
        character = self.get_object()
        character_item_id = request.data.get('character_item_id')
        
        if not character_item_id:
            return Response(
                {"error": "Missing 'character_item_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_item = CharacterItem.objects.get(pk=character_item_id, character=character)
        except CharacterItem.DoesNotExist:
            return Response(
                {"error": "Item not found in character's inventory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use inventory management utility
        success, message = unequip_item(character, character_item.item)
        
        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        character_item.refresh_from_db()
        
        # Get encumbrance info
        total_weight = calculate_total_weight(character)
        encumbrance = get_encumbrance_level(character)
        encumbrance_effects = get_encumbrance_effects(character)
        
        return Response({
            "message": message,
            "character_item": {
                'id': character_item.id,
                'item': character_item.item.name,
                'equipment_slot': character_item.equipment_slot,
                'is_equipped': character_item.is_equipped,
            },
            "encumbrance": {
                'level': encumbrance,
                'total_weight': total_weight,
                'effects': encumbrance_effects
            }
        })
    
    @action(detail=True, methods=['post'], url_path='remove_item')
    def remove_item(self, request, pk=None):
        """Remove an item from character's inventory"""
        character = self.get_object()
        
        character_item_id = request.data.get('character_item_id')
        if not character_item_id:
            return Response(
                {"error": "Missing 'character_item_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_item = CharacterItem.objects.get(pk=character_item_id, character=character)
        except CharacterItem.DoesNotExist:
            return Response(
                {"error": "Item not found in character's inventory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        item_name = character_item.item.name
        character_item.delete()
        
        # Get updated encumbrance info
        total_weight = calculate_total_weight(character)
        encumbrance = get_encumbrance_level(character)
        encumbrance_effects = get_encumbrance_effects(character)
        
        return Response({
            "message": f"Removed {item_name} from inventory",
            "encumbrance": {
                'level': encumbrance,
                'total_weight': total_weight,
                'effects': encumbrance_effects
            }
        })
    @action(detail=True, methods=['post'], url_path='update_stats')
    def update_stats(self, request, pk=None):
        """Update character's ability scores"""
        character = self.get_object()
        
        # Get the stats data
        stats_data = request.data
        
        # Update the character's stats
        if character.stats:
            old_con = character.stats.constitution
            
            # Update existing stats
            for stat_name in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                if stat_name in stats_data:
                    value = int(stats_data[stat_name])
                    # Validate range (1-30)
                    if 1 <= value <= 30:
                        setattr(character.stats, stat_name, value)
            character.stats.save()
            
            # Recalculate max HP based on new Constitution
            if character.character_class:
                hit_dice = character.character_class.hit_dice  # e.g., "d8", "1d10"
                # Extract die size (handle both "d8" and "1d8" formats)
                die_size = int(hit_dice.split('d')[-1])
                new_con_mod = (character.stats.constitution - 10) // 2
                
                method = getattr(character, 'hp_method', 'fixed')
                new_max_hp = character.stats.max_hit_points
                
                if method == 'fixed':
                    # Max HP at every level
                    new_max_hp = (die_size + new_con_mod) * character.level
                    
                elif method == 'average':
                    # Max at level 1, Average after
                    # Average of dX is (X/2) + 1. e.g. d10 -> 6.
                    avg_val = (die_size // 2) + 1
                    base = die_size + new_con_mod
                    
                    if character.level > 1:
                        new_max_hp = base + ((avg_val + new_con_mod) * (character.level - 1))
                    else:
                        new_max_hp = base
                        
                elif method == 'manual':
                    # Start from existing max HP and adjust for CON change
                    old_con_mod = (old_con - 10) // 2
                    diff = new_con_mod - old_con_mod
                    if diff != 0:
                        # HP changes by diff * level
                        new_max_hp = character.stats.max_hit_points + (diff * character.level)

                new_max_hp = max(1, new_max_hp)  # Minimum 1 HP
                
                # Update max HP
                old_max_hp = character.stats.max_hit_points
                character.stats.max_hit_points = new_max_hp
                
                # Adjust current HP proportionally to maintain HP percentage
                if old_max_hp > 0:
                    hp_percentage = character.stats.hit_points / old_max_hp
                    character.stats.hit_points = int(new_max_hp * hp_percentage)
                else:
                    character.stats.hit_points = new_max_hp
                    
                character.stats.save()
        else:
            # Create new stats if they don't exist
            from .models import CharacterStats
            stats = CharacterStats.objects.create(
                strength=int(stats_data.get('strength', 10)),
                dexterity=int(stats_data.get('dexterity', 10)),
                constitution=int(stats_data.get('constitution', 10)),
                intelligence=int(stats_data.get('intelligence', 10)),
                wisdom=int(stats_data.get('wisdom', 10)),
                charisma=int(stats_data.get('charisma', 10))
            )
            character.stats = stats
            character.save()
        
        # Recalculate derived stats
        from .inventory_management import recalculate_armor_class
        recalculate_armor_class(character)
        
        # Return updated character
        serializer = self.get_serializer(character)
        return Response(serializer.data)
    

    
    @action(detail=True, methods=['get'])
    def combat_stats(self, request, pk=None):
        """Get character's lifetime combat statistics"""
        character = self.get_object()
        
        from combat.models import CombatParticipant, CombatLog
        
        # Get all combat participations
        participations = CombatParticipant.objects.filter(character=character)
        sessions = [p.combat_session for p in participations]
        
        # Aggregate statistics
        total_combats = len(sessions)
        total_damage_dealt = 0
        total_damage_received = 0
        total_attacks = 0
        total_hits = 0
        total_crits = 0
        total_spells_cast = 0
        favorite_weapon = {}
        favorite_spell = {}
        victories = 0
        
        for participation in participations:
            session = participation.combat_session
            log = session.get_or_create_log()
            log.calculate_statistics()
            
            # Get participant stats from log
            participant_stats = log.participant_stats.get(participation.id, {})
            total_damage_dealt += participant_stats.get('damage_dealt', 0)
            total_damage_received += participant_stats.get('damage_received', 0)
            total_attacks += participant_stats.get('attacks_made', 0)
            total_hits += participant_stats.get('attacks_hit', 0)
            total_crits += participant_stats.get('critical_hits', 0)
            total_spells_cast += participant_stats.get('spells_cast', 0)
            
            # Track favorite weapons and spells
            for action in session.actions.filter(actor=participation):
                if action.action_type == 'attack' and action.attack_name:
                    favorite_weapon[action.attack_name] = favorite_weapon.get(action.attack_name, 0) + 1
                elif action.action_type == 'spell' and action.attack_name:
                    favorite_spell[action.attack_name] = favorite_spell.get(action.attack_name, 0) + 1
            
            # Check if character was a victor
            if participation.id in log.victors:
                victories += 1
        
        # Calculate averages
        hit_rate = (total_hits / total_attacks * 100) if total_attacks > 0 else 0
        crit_rate = (total_crits / total_attacks * 100) if total_attacks > 0 else 0
        win_rate = (victories / total_combats * 100) if total_combats > 0 else 0
        
        return Response({
            'character': {
                'id': character.id,
                'name': character.name,
                'level': character.level,
            },
            'summary': {
                'total_combats': total_combats,
                'victories': victories,
                'win_rate': round(win_rate, 2),
            },
            'combat_statistics': {
                'total_damage_dealt': total_damage_dealt,
                'total_damage_received': total_damage_received,
                'total_attacks': total_attacks,
                'total_hits': total_hits,
                'hit_rate': round(hit_rate, 2),
                'total_critical_hits': total_crits,
                'critical_hit_rate': round(crit_rate, 2),
                'total_spells_cast': total_spells_cast,
                'average_damage_per_combat': round(total_damage_dealt / total_combats, 2) if total_combats > 0 else 0,
            },
            'favorites': {
                'weapon': max(favorite_weapon.items(), key=lambda x: x[1])[0] if favorite_weapon else None,
                'spell': max(favorite_spell.items(), key=lambda x: x[1])[0] if favorite_spell else None,
            },
            'weapon_usage': favorite_weapon,
            'spell_usage': favorite_spell,
        })
    
    @action(detail=True, methods=['get'])
    def character_sheet(self, request, pk=None):
        """
        Get complete character sheet information.
        Perfect for simple character tracking without campaigns/combat.
        """
        character = self.get_object()
        
        # Get stats
        stats_data = None
        if hasattr(character, 'stats'):
            stats = character.stats
            stats_data = CharacterStatsSerializer(stats).data
        
        # Get spell slots (calculate if not set)
        spell_slots = {}
        if hasattr(character, 'stats') and character.stats.spell_slots:
            spell_slots = character.stats.spell_slots
        else:
            # Calculate spell slots based on class and level
            from campaigns.utils import calculate_spell_slots
            from .multiclassing import calculate_multiclass_spell_slots
            
            # Check if multiclass
            if CharacterClassLevel.objects.filter(character=character).count() > 1:
                spell_slots = calculate_multiclass_spell_slots(character)
            else:
                spell_slots = calculate_spell_slots(character.character_class.name, character.level)
            
            # Store calculated slots if stats exist
            if hasattr(character, 'stats'):
                character.stats.spell_slots = spell_slots
                character.stats.save()
        
        # Get spells
        spells = CharacterSpell.objects.filter(character=character)
        spells_data = CharacterSpellSerializer(spells, many=True).data
        
        # Get features
        features = CharacterFeature.objects.filter(character=character)
        features_data = CharacterFeatureSerializer(features, many=True).data
        
        # Get proficiencies
        proficiencies = CharacterProficiency.objects.filter(character=character)
        proficiencies_data = CharacterProficiencySerializer(proficiencies, many=True).data
        
        # Get inventory
        items = CharacterItem.objects.filter(character=character)
        inventory_data = []
        for item in items:
            inventory_data.append({
                'id': item.id,
                'item': {
                    'id': item.item.id,
                    'name': item.item.name,
                    'category': item.item.category.name if item.item.category else None,
                },
                'quantity': item.quantity,
                'is_equipped': item.is_equipped,
                'equipment_slot': item.equipment_slot,
            })
        
        # Get multiclass info
        class_levels = CharacterClassLevel.objects.filter(character=character)
        class_levels_data = [
            {
                'class_id': cl.character_class.id,
                'class_name': cl.character_class.get_name_display(),
                'level': cl.level,
                'subclass': cl.subclass
            }
            for cl in class_levels
        ]
        
        return Response({
            'character': {
                'id': character.id,
                'name': character.name,
                'level': character.level,
                'total_level': get_total_level(character),
                'character_class': character.character_class.get_name_display(),
                'race': character.race.get_name_display(),
                'background': character.background.get_name_display() if character.background else None,
                'subclass': character.subclass,
                'alignment': character.get_alignment_display(),
                'size': character.get_size_display(),
                'player_name': character.player_name,
                'description': character.description,
                'backstory': character.backstory,
                'experience_points': character.experience_points,
                'proficiency_bonus': character.proficiency_bonus,
            },
            'stats': stats_data,
            'spell_slots': spell_slots,
            'spells': spells_data,
            'features': features_data,
            'proficiencies': proficiencies_data,
            'inventory': inventory_data,
            'class_levels': class_levels_data,
            'multiclass_info': {
                'is_multiclass': class_levels.count() > 1,
                'spellcasting_ability': get_multiclass_spellcasting_ability(character) if class_levels.count() > 1 else None,
            }
        })
    
    @action(detail=True, methods=['post'])
    def update_spell_slots(self, request, pk=None):
        """
        Update spell slots for a character.
        Useful for tracking spell slot usage outside of campaigns.
        
        Request body:
        {
            "spell_slots": {"1": 2, "2": 1, "3": 0}  // Slots remaining by level
        }
        """
        character = self.get_object()
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character must have stats"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_slots = request.data.get('spell_slots', {})
        
        # Validate spell slots format
        if not isinstance(spell_slots, dict):
            return Response(
                {"error": "spell_slots must be a dictionary"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update spell slots
        character.stats.spell_slots = spell_slots
        character.stats.save()
        
        return Response({
            "message": f"Spell slots updated for {character.name}",
            "spell_slots": spell_slots
        })
    
    @action(detail=True, methods=['post'])
    def use_spell_slot(self, request, pk=None):
        """
        Use a spell slot of a specific level.
        
        Request body:
        {
            "spell_level": 1  // Level of spell slot to use
        }
        """
        character = self.get_object()
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character must have stats"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_level = request.data.get('spell_level')
        if spell_level is None:
            return Response(
                {"error": "spell_level is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_level_str = str(spell_level)
        current_slots = character.stats.spell_slots or {}
        
        # Check if slot available
        if current_slots.get(spell_level_str, 0) <= 0:
            return Response(
                {"error": f"No level {spell_level} spell slots remaining"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use slot
        current_slots[spell_level_str] = current_slots.get(spell_level_str, 0) - 1
        character.stats.spell_slots = current_slots
        character.stats.save()
        
        return Response({
            "message": f"Used 1 level {spell_level} spell slot",
            "spell_slots_remaining": current_slots
        })
    
    @action(detail=True, methods=['post'])
    def restore_spell_slots(self, request, pk=None):
        """
        Restore spell slots (e.g., after long rest).
        Restores to maximum based on class and level.
        """
        character = self.get_object()
        
        if not hasattr(character, 'stats'):
            return Response(
                {"error": "Character must have stats"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate max spell slots
        from campaigns.utils import calculate_spell_slots
        from .multiclassing import calculate_multiclass_spell_slots
        
        if CharacterClassLevel.objects.filter(character=character).count() > 1:
            max_slots = calculate_multiclass_spell_slots(character)
        else:
            max_slots = calculate_spell_slots(character.character_class.name, character.level)
        
        # Restore slots
        character.stats.spell_slots = max_slots.copy()
        character.stats.save()
        
        return Response({
            "message": f"Spell slots restored for {character.name}",
            "spell_slots": max_slots
        })
    
    @action(detail=True, methods=['get'])
    def spell_info(self, request, pk=None):
        """Get spell management information for a character"""
        character = self.get_object()
        
        info = {
            'is_prepared_caster': is_prepared_caster(character),
            'is_known_caster': is_known_caster(character),
            'can_cast_rituals': can_cast_rituals(character),
        }
        
        if is_prepared_caster(character):
            spells_prepared_limit = calculate_spells_prepared(character)
            prepared_spells = get_prepared_spells(character)
            info['spells_prepared'] = {
                'limit': spells_prepared_limit,
                'current': prepared_spells.count(),
                'spells': CharacterSpellSerializer(prepared_spells, many=True).data
            }
            
            # For Wizards, also show spellbook info
            if character.character_class.name == 'Wizard':
                spellbook_size = get_wizard_spellbook_size(character)
                spellbook_spells = get_spellbook_spells(character)
                info['spellbook'] = {
                    'size': spellbook_size,
                    'current': spellbook_spells.count(),
                    'spells': CharacterSpellSerializer(spellbook_spells, many=True).data
                }
        
        elif is_known_caster(character):
            spells_known_limit = calculate_spells_known(character)
            known_spells = get_known_spells(character)
            info['spells_known'] = {
                'limit': spells_known_limit,
                'current': known_spells.count(),
                'spells': CharacterSpellSerializer(known_spells, many=True).data
            }
        
        return Response(info)
    
    @action(detail=True, methods=['post'])
    def prepare_spells(self, request, pk=None):
        """
        Prepare spells for a prepared caster (Cleric, Druid, Paladin, Wizard)
        
        Request body:
        {
            "spell_ids": [1, 2, 3]  // List of CharacterSpell IDs to prepare
        }
        """
        character = self.get_object()
        
        if not is_prepared_caster(character):
            return Response(
                {"error": f"{character.character_class.name} is not a prepared caster"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_ids = request.data.get('spell_ids', [])
        if not isinstance(spell_ids, list):
            return Response(
                {"error": "spell_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get spells that belong to this character
        spells = CharacterSpell.objects.filter(
            character=character,
            id__in=spell_ids
        )
        
        if spells.count() != len(spell_ids):
            return Response(
                {"error": "Some spells not found or don't belong to this character"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check limit
        spells_prepared_limit = calculate_spells_prepared(character)
        if len(spell_ids) > spells_prepared_limit:
            return Response(
                {"error": f"Can only prepare {spells_prepared_limit} spells"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Unprepare all spells first
        CharacterSpell.objects.filter(character=character).update(is_prepared=False)
        
        # Prepare selected spells
        spells.update(is_prepared=True)
        
        return Response({
            "message": f"Prepared {len(spell_ids)} spell(s)",
            "spells_prepared": CharacterSpellSerializer(spells, many=True).data,
            "limit": spells_prepared_limit
        })
    
    @action(detail=True, methods=['post'])
    def learn_spell(self, request, pk=None):
        """
        Learn a new spell (for known casters: Bard, Ranger, Sorcerer, Warlock)
        
        Request body:
        {
            "spell_name": "Fireball",
            "spell_level": 3,
            "school": "Evocation",
            "description": "...",
            "is_ritual": false
        }
        """
        character = self.get_object()
        
        if not is_known_caster(character) and not is_prepared_caster(character):
            return Response(
                {"error": f"{character.character_class.name} is not a known or prepared caster"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_id = request.data.get('spell_id')
        spell_name = request.data.get('spell_name')
        spell_level = request.data.get('spell_level')
        
        # If spell_id provided, fetch details from Spell model
        spell_obj = None
        if spell_id:
            from spells.models import Spell
            try:
                spell_obj = Spell.objects.get(pk=spell_id)
                spell_name = spell_obj.name
                spell_level = spell_obj.level
                # Use provided values as overrides if needed, otherwise defaults
                school = request.data.get('school', spell_obj.school)
                description = request.data.get('description', spell_obj.description)
                is_ritual = request.data.get('is_ritual', spell_obj.ritual)
            except Spell.DoesNotExist:
                return Response(
                    {"error": "Spell not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            school = request.data.get('school', '')
            description = request.data.get('description', '')
            is_ritual = request.data.get('is_ritual', False)

        if not spell_name or spell_level is None:
            return Response(
                {"error": "spell_name and spell_level are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate spell level based on character's spellcasting ability
        from .multiclassing import get_total_level
        total_level = get_total_level(character)
        
        # Determine max spell level based on character level
        # This follows the standard D&D 5e spell slot progression
        max_spell_level = 0
        if total_level >= 17:
            max_spell_level = 9
        elif total_level >= 15:
            max_spell_level = 8
        elif total_level >= 13:
            max_spell_level = 7
        elif total_level >= 11:
            max_spell_level = 6
        elif total_level >= 9:
            max_spell_level = 5
        elif total_level >= 7:
            max_spell_level = 4
        elif total_level >= 5:
            max_spell_level = 3
        elif total_level >= 3:
            max_spell_level = 2
        elif total_level >= 1:
            max_spell_level = 1
        
        # Cantrips (level 0) are always allowed
        if spell_level > 0 and spell_level > max_spell_level:
            return Response(
                {"error": f"Character level {total_level} can only learn spells up to level {max_spell_level}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already known
        if CharacterSpell.objects.filter(character=character, name=spell_name).exists():
            return Response(
                {"error": f"Already know {spell_name}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check limit (only for Known Casters)
        if is_known_caster(character):
            if not can_learn_spell(character, spell_level):
                spells_known_limit = calculate_spells_known(character)
                return Response(
                    {"error": f"Cannot learn more spells (limit: {spells_known_limit})"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create spell
        spell = CharacterSpell.objects.create(
            character=character,
            spell=spell_obj,
            name=spell_name,
            level=spell_level,
            school=school,
            description=description,
            is_ritual=is_ritual
        )
        
        return Response({
            "message": f"Learned {spell_name}",
            "spell": CharacterSpellSerializer(spell).data
        })
    
    @action(detail=True, methods=['post'], url_path='remove_spell')
    def remove_spell(self, request, pk=None):
        """Remove a spell from character's spell list"""
        character = self.get_object()
        
        character_spell_id = request.data.get('character_spell_id')
        if not character_spell_id:
            return Response(
                {"error": "Missing 'character_spell_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_spell = CharacterSpell.objects.get(pk=character_spell_id, character=character)
        except CharacterSpell.DoesNotExist:
            return Response(
                {"error": "Spell not found in character's spell list"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        spell_name = character_spell.name
        character_spell.delete()
        
        return Response({
            "message": f"Removed {spell_name} from spell list"
        })
    
    @action(detail=True, methods=['post'])
    def add_to_spellbook(self, request, pk=None):
        """
        Add a spell to Wizard's spellbook
        
        Request body:
        {
            "spell_name": "Fireball",
            "spell_level": 3,
            "school": "Evocation",
            "description": "...",
            "is_ritual": false
        }
        """
        character = self.get_object()
        
        if character.character_class.name != 'Wizard':
            return Response(
                {"error": "Only Wizards have spellbooks"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_id = request.data.get('spell_id')
        spell_name = request.data.get('spell_name')
        spell_level = request.data.get('spell_level')
        
        spell_obj = None
        if spell_id:
            from spells.models import Spell
            try:
                spell_obj = Spell.objects.get(pk=spell_id)
                spell_name = spell_obj.name
                spell_level = spell_obj.level
                school = request.data.get('school', spell_obj.school)
                description = request.data.get('description', spell_obj.description)
                is_ritual = request.data.get('is_ritual', spell_obj.ritual)
            except Spell.DoesNotExist:
                return Response(
                    {"error": "Spell not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            school = request.data.get('school', '')
            description = request.data.get('description', '')
            is_ritual = request.data.get('is_ritual', False)

        if not spell_name or spell_level is None:
            return Response(
                {"error": "spell_name and spell_level are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already in spellbook
        if CharacterSpell.objects.filter(character=character, name=spell_name, in_spellbook=True).exists():
            return Response(
                {"error": f"{spell_name} is already in spellbook"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check limit
        if not can_add_to_spellbook(character, spell_level):
            spellbook_size = get_wizard_spellbook_size(character)
            return Response(
                {"error": f"Spellbook is full (limit: {spellbook_size})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update spell
        spell, created = CharacterSpell.objects.get_or_create(
            character=character,
            name=spell_name,
            defaults={
                'spell': spell_obj,
                'level': spell_level,
                'school': school,
                'description': description,
                'is_ritual': is_ritual,
                'in_spellbook': True
            }
        )
        
        if not created:
            spell.in_spellbook = True
            if spell_obj and not spell.spell:
                spell.spell = spell_obj
            spell.save()
        
        return Response({
            "message": f"Added {spell_name} to spellbook",
            "spell": CharacterSpellSerializer(spell).data
        })
    
    @action(detail=True, methods=['post'])
    def learn_from_scroll(self, request, pk=None):
        """
        Learn a spell from a scroll (Wizards only)
        
        Request body:
        {
            "spell_name": "Fireball",
            "spell_level": 3,
            "school": "Evocation",
            "description": "...",
            "is_ritual": false
        }
        """
        character = self.get_object()
        
        if character.character_class.name != 'Wizard':
            return Response(
                {"error": "Only Wizards can learn spells from scrolls"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Same as add_to_spellbook, but this is for learning from scrolls
        return self.add_to_spellbook(request, pk)


    @action(detail=True, methods=['post'])
    def short_rest(self, request, pk=None):
        """
        Perform a Short Rest.
        - Spend Hit Dice to heal
        - Recover Warlock spell slots
        - Reset Short Rest features (Action Surge, etc. - future impl)
        """
        character = self.get_object()
        
        if not hasattr(character, 'stats'):
             return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            hit_dice_to_spend = int(request.data.get('hit_dice_to_spend', 0))
        except (ValueError, TypeError):
             return Response(
                {"error": "hit_dice_to_spend must be an integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        stats = character.stats
        
        # 1. Spend Hit Dice & Heal
        hp_recovered = 0
        dice_spent = 0
        
        if hit_dice_to_spend > 0:
            current_level = character.level
            # Check availability
            # "hit_dice_used" tracks how many have been SPENT. 
            # Available = Total - Used
            available = current_level - stats.hit_dice_used
            
            if hit_dice_to_spend > available:
                 return Response(
                    {"error": f"Not enough Hit Dice. Available: {available}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Roll for healing
            # Determine die size from class
            hit_die_size = 8 # Default
            if character.character_class:
                # "d10" -> 10
                try:
                    hit_die_size = int(character.character_class.hit_dice.strip('d'))
                except:
                    pass
            
            import random
            con_mod = stats.constitution_modifier
            
            for _ in range(hit_dice_to_spend):
                roll = random.randint(1, hit_die_size)
                heal_amt = max(0, roll + con_mod) # Minimum 0? PHB says minimum 0.
                hp_recovered += heal_amt
                stats.hit_points = min(stats.max_hit_points, stats.hit_points + heal_amt)
                
            stats.hit_dice_used += hit_dice_to_spend
            dice_spent = hit_dice_to_spend

        # 2. Recover Pact Magic slots (Warlock)
        slots_recovered = {}
        if character.character_class.name == 'Warlock':
             # Calculate max slots
            from campaigns.utils import calculate_spell_slots
            max_slots = calculate_spell_slots('Warlock', character.level)
            stats.spell_slots = max_slots
            slots_recovered = max_slots

        stats.save()
        
        return Response({
            "message": f"Short Rest complete. Regained {hp_recovered} HP using {dice_spent} Hit Dice.",
            "hp_recovered": hp_recovered,
            "hit_dice_spent": dice_spent,
            "current_hp": stats.hit_points,
            "hit_dice_remaining": character.level - stats.hit_dice_used,
            "slots_recovered": slots_recovered
        })

    @action(detail=True, methods=['post'])
    def long_rest(self, request, pk=None):
        """
        Perform a Long Rest.
        - Restore HP to max
        - Regain Hit Dice (half max)
        - Restore all Spell Slots
        - Reduce Exhaustion (future)
        """
        character = self.get_object()
        
        if not hasattr(character, 'stats'):
             return Response(
                {"error": "Character stats not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        stats = character.stats
        
        # 1. Restore HP
        hp_gained = stats.max_hit_points - stats.hit_points
        stats.hit_points = stats.max_hit_points
        
        # 2. Regain Hit Dice
        # Regain up to half of total hit dice (min 1)
        total_hit_dice = character.level
        regain_amount = max(1, total_hit_dice // 2)
        
        # Reduce "used" count
        # if used is 5, regain 2 -> used becomes 3
        stats.hit_dice_used = max(0, stats.hit_dice_used - regain_amount)
        
        # 3. Restore Spell Slots
        from campaigns.utils import calculate_spell_slots
        from .multiclassing import calculate_multiclass_spell_slots
        
        if CharacterClassLevel.objects.filter(character=character).count() > 1:
            max_slots = calculate_multiclass_spell_slots(character)
        else:
            max_slots = calculate_spell_slots(character.character_class.name, character.level)
            
        stats.spell_slots = max_slots
        stats.save()
        
        return Response({
            "message": f"Long Rest complete. HP and Spell Slots fully restored. Regained {regain_amount} Hit Dice.",
            "hp_gained": hp_gained,
            "hit_dice_regained": regain_amount,
            "current_hp": stats.hit_points,
            "hit_dice_remaining": total_hit_dice - stats.hit_dice_used,
            "spell_slots": max_slots
        })

class CharacterClassViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character classes."""
    @action(detail=True, methods=['get'])
    def subclasses(self, request, pk=None):
        """Get available subclasses for this class"""
        character_class = self.get_object()
        ruleset = request.query_params.get('ruleset', '2014')
        
        from campaigns.class_features_data import AVAILABLE_SUBCLASSES_2014, AVAILABLE_SUBCLASSES_2024
        
        if ruleset == '2024':
            subclasses = AVAILABLE_SUBCLASSES_2024.get(character_class.name, [])
        else:
            subclasses = AVAILABLE_SUBCLASSES_2014.get(character_class.name, [])
            
        data = []
        for sc_name in subclasses:
            # TODO: Add real descriptions from data
            data.append({
                'name': sc_name,
                'id': sc_name,
                'description': f"A valid subclass for {character_class.name}"
            })
            
        return Response(data)

    queryset = CharacterClass.objects.all()
    serializer_class = CharacterClassSerializer


class CharacterRaceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character races."""
    queryset = CharacterRace.objects.all()
    serializer_class = CharacterRaceSerializer

    def get_queryset(self):
        queryset = CharacterRace.objects.all()
        ruleset = self.request.query_params.get('ruleset', '2014')
        
        if ruleset == '2024':
            return queryset.filter(source_ruleset__in=['2024', 'all'])
        else:
            # Default to 2014 (Legacy) behavior
            return queryset.filter(source_ruleset__in=['2014', 'all'])


class CharacterBackgroundViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character backgrounds."""
    queryset = CharacterBackground.objects.all()
    serializer_class = CharacterBackgroundSerializer

    def get_queryset(self):
        queryset = CharacterBackground.objects.all()
        ruleset = self.request.query_params.get('ruleset', '2014')
        
        if ruleset == '2024':
            return queryset.filter(source_ruleset__in=['2024', 'all'])
        else:
            return queryset.filter(source_ruleset__in=['2014', 'all'])


class CharacterStatsViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character stats."""
    serializer_class = CharacterStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character stats to only show those for characters owned by the current user"""
        return CharacterStats.objects.filter(character__user=self.request.user)


class CharacterProficiencyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character proficiencies."""
    serializer_class = CharacterProficiencySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character proficiencies to only show those for characters owned by the current user"""
        return CharacterProficiency.objects.filter(character__user=self.request.user)


class CharacterFeatureViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character features."""
    serializer_class = CharacterFeatureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character features to only show those for characters owned by the current user"""
        return CharacterFeature.objects.filter(character__user=self.request.user)


class CharacterSpellViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character spells."""
    serializer_class = CharacterSpellSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character spells to only show those for characters owned by the current user"""
        return CharacterSpell.objects.filter(character__user=self.request.user)


class CharacterResistanceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing character resistances."""
    serializer_class = CharacterResistanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter character resistances to only show those for characters owned by the current user"""
        return CharacterResistance.objects.filter(character__user=self.request.user)
