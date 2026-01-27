"""
Spell selection endpoints for CharacterViewSet
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from characters.models import CharacterSpell
from spells.models import Spell
from spells.serializers import SpellSerializer


def add_spell_selection_endpoints(cls):
    """
    Decorator to add spell selection endpoints to CharacterViewSet
    """
    
    @action(detail=False, methods=['get'])
    def starting_spell_choices(self, request):
        """Get available spells for character creation based on class"""
        from characters.starting_spells import get_spell_selection_requirements, RECOMMENDED_SPELLS
        
        class_name = request.query_params.get('class_name')
        if not class_name:
            return Response(
                {"error": "class_name parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get spell selection requirements
        requirements = get_spell_selection_requirements(class_name)
        if not requirements:
            return Response(
                {"message": f"{class_name} is not a spellcasting class at level 1"},
                status=status.HTTP_200_OK
            )
        
        # Get available cantrips for this class
        cantrips = Spell.objects.filter(
            level=0,
            classes__name__iexact=class_name
        ).order_by('school', 'name')
        
        # Get available 1st level spells for this class
        level_1_spells = Spell.objects.filter(
            level=1,
            classes__name__iexact=class_name
        ).order_by('school', 'name')
        
        # Serialize spells
        cantrips_data = SpellSerializer(cantrips, many=True).data
        spells_data = SpellSerializer(level_1_spells, many=True).data
        
        # Mark recommended spells
        recommendations = RECOMMENDED_SPELLS.get(class_name.capitalize(), {})
        rec_cantrips = set(recommendations.get('cantrips', []))
        rec_spells = set(recommendations.get('spells_level_1', []))
        
        for spell in cantrips_data:
            spell['recommended'] = spell['name'] in rec_cantrips
            
        for spell in spells_data:
            spell['recommended'] = spell['name'] in rec_spells
        
        return Response({
            "class_name": requirements['class_name'],
            "cantrips_count": requirements['cantrips_count'],
            "spells_info": requirements['spells_info'],
            "description": requirements['description'],
            "available_cantrips": cantrips_data,
            "available_spells": spells_data,
        })
    
    @action(detail=True, methods=['post'])
    def apply_starting_spells(self, request, pk=None):
        """Apply selected starting spells to a character"""
        from characters.starting_spells import get_spell_selection_requirements, calculate_starting_cantrips
        
        character = self.get_object()
        cantrip_ids = request.data.get('cantrip_ids', [])
        spell_ids = request.data.get('spell_ids', [])
        
        # Get requirements for this class
        requirements = get_spell_selection_requirements(
            character.character_class.name,
            character.stats if hasattr(character, 'stats') else None
        )
        
        if not requirements:
            return Response(
                {"error": f"{character.character_class.name} cannot select spells at level 1"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate cantrip count
        expected_cantrips = requirements['cantrips_count']
        if len(cantrip_ids) != expected_cantrips:
            return Response(
                {"error": f"Expected {expected_cantrips} cantrips, got {len(cantrip_ids)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate spell count (only for classes that select specific spells)
        spells_info = requirements['spells_info']
        expected_spells = spells_info.get('count', 0)
        
        # Only validate spell count if they should be selecting spells
        if expected_spells > 0 and len(spell_ids) != expected_spells:
            return Response(
                {"error": f"Expected {expected_spells} spells, got {len(spell_ids)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        added_spells = []
        failed_spells = []
        
        # Process cantrips
        for spell_id in cantrip_ids:
            try:
                spell = Spell.objects.get(pk=spell_id, level=0)
                
                # Verify spell is available for this class
                if not spell.classes.filter(pk=character.character_class.pk).exists():
                    failed_spells.append(f"{spell.name}: Not available to {character.character_class.name}")
                    continue
                
                # Create CharacterSpell entry
                CharacterSpell.objects.create(
                    character=character,
                    spell=spell,
                    name=spell.name,
                    level=spell.level,
                    school=spell.school,
                    is_prepared=True,  # Cantrips are always prepared
                    is_ritual=spell.ritual,
                    in_spellbook=False,
                    description=spell.description
                )
                added_spells.append(spell.name)
                
            except Spell.DoesNotExist:
                failed_spells.append(f"Cantrip ID {spell_id}: Not found")
            except Exception as e:
                failed_spells.append(f"Cantrip ID {spell_id}: {str(e)}")
        
        # Process leveled spells
        is_wizard = character.character_class.name.lower() == 'wizard'
        is_known_caster = spells_info.get('type') == 'known'
        
        for spell_id in spell_ids:
            try:
                spell = Spell.objects.get(pk=spell_id, level=1)
                
                # Verify spell is available for this class
                if not spell.classes.filter(pk=character.character_class.pk).exists():
                    failed_spells.append(f"{spell.name}: Not available to {character.character_class.name}")
                    continue
                
                # Create CharacterSpell entry
                CharacterSpell.objects.create(
                    character=character,
                    spell=spell,
                    name=spell.name,
                    level=spell.level,
                    school=spell.school,
                    is_prepared=is_known_caster,  # Known casters have all spells prepared
                    is_ritual=spell.ritual,
                    in_spellbook=is_wizard,  # Wizards add to spellbook
                    description=spell.description
                )
                added_spells.append(spell.name)
                
            except Spell.DoesNotExist:
                failed_spells.append(f"Spell ID {spell_id}: Not found")
            except Exception as e:
                failed_spells.append(f"Spell ID {spell_id}: {str(e)}")
        
        # Prepare a success message
        message = f"Successfully added {len(added_spells)} spells to {character.name}"
        if is_wizard:
            message += "'s spellbook"
        
        return Response({
            "message": message,
            "added_spells": added_spells,
            "failed_spells": failed_spells,
            "cantrips_added": len([s_id for s_id in cantrip_ids if s_id]),
            "spells_added": len([s_id for s_id in spell_ids if s_id]),
        })
    
    # Add methods to class
    @action(detail=True, methods=['post'])
    def finalize_level_up_spells(self, request, pk=None):
        """Finalize spell selection after level up"""
        character = self.get_object()
        pending = character.pending_spell_choices
        
        if not pending:
             return Response(
                 {"error": "No pending spell choices found"},
                 status=status.HTTP_400_BAD_REQUEST
             )
             
        spell_ids = request.data.get('spell_ids', [])
        
        # Validate count
        expected_count = pending.get('count', 0)
        # Allow selecting fewer spells? Usually yes, but better to warn. We'll enforce max strict.
        if len(spell_ids) > expected_count:
             return Response(
                 {"error": f"Selected {len(spell_ids)} spells, but limit is {expected_count}"},
                 status=status.HTTP_400_BAD_REQUEST
             )
             
        # Process and Validate
        added = []
        errors = []
        max_level = pending.get('max_level', 9)
        selection_type = pending.get('type', 'new_spell') # 'spellbook' or 'new_spell'
        
        for spell_id in spell_ids:
            try:
                spell = Spell.objects.get(pk=spell_id)
                
                # Check level
                if spell.level > max_level:
                    errors.append(f"{spell.name} is too high level (max {max_level})")
                    continue
                    
                # Add to character
                is_wiz_spellbook = selection_type == 'spellbook'
                
                is_wiz_spellbook = selection_type == 'spellbook'
                
                # Use get_or_create to avoid errors if spell already exists
                obj, created = CharacterSpell.objects.get_or_create(
                    character=character,
                    spell=spell,
                    defaults={
                        'name': spell.name,
                        'level': spell.level,
                        'school': spell.school,
                        'is_prepared': not is_wiz_spellbook,
                        'in_spellbook': is_wiz_spellbook,
                        'is_ritual': spell.ritual,
                        'description': spell.description
                    }
                )
                
                # If spell already existed but we need to ensure it's in the spellbook (for wizards)
                # or prepared (for others), we might want to update it.
                # For now, just ensuring it exists is enough to proceed.
                if not created and is_wiz_spellbook and not obj.in_spellbook:
                    obj.in_spellbook = True
                    obj.save()
                    
                added.append(spell.name)
            except Spell.DoesNotExist:
                errors.append(f"Spell {spell_id} not found")
            except Exception as e:
                errors.append(f"Error adding spell {spell_id}: {str(e)}")
        
        if errors:
             return Response({
                 "error": "Some spells failed",
                 "details": errors,
                 "added": added
             }, status=status.HTTP_400_BAD_REQUEST)
             
        # Clear pending choices first to ensure clean state
        character.pending_spell_choices = {}
        
        # Recalculate pending choices (e.g. to see if we now need Cantrips after picking Spells)
        if hasattr(self, '_calculate_pending_spells'):
            dummy_gained = [] 
            self._calculate_pending_spells(character, character.character_class, character.level, dummy_gained)
             
        character.save()
        
        return Response({
            "message": f"Added {len(added)} spells",
            "added_spells": added
        })

    # Add methods to class
    cls.starting_spell_choices = starting_spell_choices
    cls.apply_starting_spells = apply_starting_spells
    cls.finalize_level_up_spells = finalize_level_up_spells
    
    return cls
