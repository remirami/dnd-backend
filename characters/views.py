from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance, CharacterItem
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
        """Filter characters to only show those owned by the current user"""
        return Character.objects.filter(user=self.request.user).order_by('-created_at')
    
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
        """Level up a character"""
        character = self.get_object()
        character.level += 1
        character.save()
        
        serializer = self.get_serializer(character)
        return Response({
            "message": f"{character.name} leveled up to level {character.level}!",
            "character": serializer.data
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
        slot = equipment_slot or character_item.equipment_slot or 'main_hand'
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
        
        if not is_known_caster(character):
            return Response(
                {"error": f"{character.character_class.name} is not a known caster"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spell_name = request.data.get('spell_name')
        spell_level = request.data.get('spell_level')
        
        if not spell_name or spell_level is None:
            return Response(
                {"error": "spell_name and spell_level are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already known
        if CharacterSpell.objects.filter(character=character, name=spell_name).exists():
            return Response(
                {"error": f"Already know {spell_name}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check limit
        if not can_learn_spell(character, spell_level):
            spells_known_limit = calculate_spells_known(character)
            return Response(
                {"error": f"Cannot learn more spells (limit: {spells_known_limit})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create spell
        spell = CharacterSpell.objects.create(
            character=character,
            name=spell_name,
            level=spell_level,
            school=request.data.get('school', ''),
            description=request.data.get('description', ''),
            is_ritual=request.data.get('is_ritual', False)
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
        
        spell_name = request.data.get('spell_name')
        spell_level = request.data.get('spell_level')
        
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
                'level': spell_level,
                'school': request.data.get('school', ''),
                'description': request.data.get('description', ''),
                'is_ritual': request.data.get('is_ritual', False),
                'in_spellbook': True
            }
        )
        
        if not created:
            spell.in_spellbook = True
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
