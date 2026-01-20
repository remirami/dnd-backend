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
    can_cast_spell
)
from .inventory_management import (
    equip_item, unequip_item, get_equipped_items,
    calculate_total_weight, get_encumbrance_level, get_encumbrance_effects,
    get_equipped_weapon, get_equipped_armor, get_equipped_shield
)


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
        """Automatically set the user when creating a character and apply racial and background features"""
        character = serializer.save(user=self.request.user)
        
        # Apply racial features automatically
        from campaigns.racial_features_data import apply_racial_features_to_character
        try:
            apply_racial_features_to_character(character)
        except Exception as e:
            # Log error but don't fail character creation
            print(f"Warning: Failed to apply racial features to {character.name}: {str(e)}")
        
        # Apply background features automatically
        from campaigns.background_features_data import apply_background_features_to_character
        try:
            apply_background_features_to_character(character)
        except Exception as e:
            # Log error but don't fail character creation
            print(f"Warning: Failed to apply background features to {character.name}: {str(e)}")
    
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
            # Check prerequisites if this is a new class
            can_multiclass, reason = can_multiclass_into(character, target_class.name)
            if not can_multiclass:
                # Check if already has this class
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
                    return Response(
                        {"error": reason},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # New class - create CharacterClassLevel
                class_level = CharacterClassLevel.objects.create(
                    character=character,
                    character_class=target_class,
                    level=1
                )
                old_class_level = 0
                new_class_level = 1
            
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
            class_features = get_class_features(target_class.name, new_class_level)
            for feature_data in class_features:
                CharacterFeature.objects.get_or_create(
                    character=character,
                    name=feature_data['name'],
                    defaults={
                        'feature_type': 'class',
                        'description': feature_data['description'],
                        'source': f"{target_class.get_name_display()} Level {new_class_level}"
                    }
                )
                features_gained.append({
                    'level': new_class_level,
                    'name': feature_data['name'],
                    'type': 'class'
                })
            
            # Apply subclass features if applicable
            if class_level.subclass:
                subclass_features = get_subclass_features(class_level.subclass, new_class_level)
                for feature_data in subclass_features:
                    CharacterFeature.objects.get_or_create(
                        character=character,
                        name=feature_data['name'],
                        defaults={
                            'feature_type': 'class',
                            'description': feature_data['description'],
                            'source': f"{class_level.subclass} Level {new_class_level}"
                        }
                    )
                    features_gained.append({
                        'level': new_class_level,
                        'name': feature_data['name'],
                        'type': 'subclass'
                    })
            
            # Update spell slots
            if new_slots and hasattr(character, 'stats'):
                character.stats.spell_slots = new_slots
                spellcasting_ability = get_multiclass_spellcasting_ability(character)
                if spellcasting_ability:
                    character.stats.spell_save_dc = calculate_spell_save_dc(character, spellcasting_ability)
                    character.stats.spell_attack_bonus = calculate_spell_attack_bonus(character, spellcasting_ability)
                character.stats.save()
            
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
        subclass_levels = {
            'cleric': 1,
            'druid': 2,
            'wizard': 2,
            'sorcerer': 1,
            'warlock': 1,
        }
        default_subclass_level = 3
        subclass_level = subclass_levels.get(primary_class.name, default_subclass_level)
        
        if new_level >= subclass_level and not character.subclass:
            character.pending_subclass_selection = True
        
        # Apply class features
        features_gained = []
        class_features = get_class_features(primary_class.name, new_level)
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
            subclass_features = get_subclass_features(character.subclass, new_level)
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
        
        character.save()
        
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
            
            # Check if character already has this feat
            if CharacterFeat.objects.filter(character=character, feat=feat).exists():
                return Response(
                    {"error": f"Character already has the feat: {feat.name}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply feat
            CharacterFeat.objects.create(
                character=character,
                feat=feat,
                level_taken=level
            )
            
            # Create CharacterFeature instance
            CharacterFeature.objects.get_or_create(
                character=character,
                name=feat.name,
                defaults={
                    'feature_type': 'feat',
                    'description': feat.description,
                    'source': f"Feat (Level {level})"
                }
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
                    stats.save()
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
                "message": f"ASI applied successfully for level {level}",
                "applied_changes": applied_changes,
                "remaining_pending_asi": character.pending_asi_levels
            })
    
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
        damage = request.data.get('damage', 0)
        
        if not isinstance(damage, int) or damage < 0:
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
        amount = request.data.get('amount', 0)
        
        if not isinstance(amount, int) or amount < 0:
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
                con_mod = (character.stats.constitution - 10) // 2
                # HP = (die_size + con_mod) per level
                new_max_hp = (die_size + con_mod) * character.level
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


class CharacterClassViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character classes."""
    queryset = CharacterClass.objects.all()
    serializer_class = CharacterClassSerializer


class CharacterRaceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character races."""
    queryset = CharacterRace.objects.all()
    serializer_class = CharacterRaceSerializer


class CharacterBackgroundViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing character backgrounds."""
    queryset = CharacterBackground.objects.all()
    serializer_class = CharacterBackgroundSerializer


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
