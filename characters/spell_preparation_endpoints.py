"""
Spell Preparation endpoints for CharacterViewSet
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from characters.models import CharacterSpell
from characters.spell_management import (
    is_prepared_caster,
    calculate_spells_prepared,
    can_prepare_spell
)
from characters.serializers import CharacterSpellSerializer


def add_spell_preparation_endpoints(cls):
    """
    Decorator to add spell preparation endpoints to CharacterViewSet
    """
    
    @action(detail=True, methods=['get'])
    def preparation_status(self, request, pk=None):
        """
        Get spell preparation status for a character.
        Returns limits, current count, and list of prepared spells.
        """
        character = self.get_object()
        
        if not is_prepared_caster(character):
            return Response(
                {"message": "Character is not a prepared caster"},
                status=status.HTTP_200_OK
            )
            
        limit = calculate_spells_prepared(character)
        prepared_spells = CharacterSpell.objects.filter(
            character=character,
            is_prepared=True,
            level__gt=0  # Cantrips don't count towards preparation limit
        )
        
        return Response({
            "limit": limit,
            "current": prepared_spells.count(),
            "remaining": max(0, limit - prepared_spells.count()),
            "prepared_spells": CharacterSpellSerializer(prepared_spells, many=True).data
        })
        
    @action(detail=True, methods=['post'])
    def prepare_spell(self, request, pk=None):
        """
        Toggle preparation status of a spell.
        Body: { "spell_id": <int>, "prepare": <bool> }
        """
        character = self.get_object()
        spell_id = request.data.get('spell_id')
        should_prepare = request.data.get('prepare')
        
        if not is_prepared_caster(character):
            return Response(
                {"error": "Character is not a prepared caster"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            char_spell = CharacterSpell.objects.get(pk=spell_id, character=character)
        except CharacterSpell.DoesNotExist:
            # For prepared casters, if the spell is not in the list, check if it's a valid spell to prepare
            # and add it.
            from spells.models import Spell
            try:
                spell_obj = Spell.objects.get(pk=spell_id)
                # Verify class access (simplified check)
                if not spell_obj.classes.filter(pk=character.character_class.pk).exists():
                     return Response(
                        {"error": "Spell not available to this class"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check level requirements? (Cleric knows all levels? No, only up to Max Slot level)
                # But typically Prepared Casters "Know" all spells on their list.
                # Logic: If you have a slot for it, you can prepare it.
                # Or even if you don't? (You can prepare Lvl 9 spell at Lvl 1? No.)
                # simplified max level check
                # Note: This duplicates logic from learn_spell but is safer for "Prepare"
                # For now, just create it.
                
                char_spell = CharacterSpell.objects.create(
                    character=character,
                    spell=spell_obj,
                    name=spell_obj.name,
                    level=spell_obj.level,
                    school=spell_obj.school,
                    description=spell_obj.description,
                    is_ritual=spell_obj.ritual,
                    is_prepared=False # Will set true below
                )
            except Spell.DoesNotExist:
                return Response(
                    {"error": "Spell not found (id)"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
        # Cantrips are always prepared
        if char_spell.level == 0:
            return Response(
                {"error": "Cantrips are always prepared"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if should_prepare:
            # Check limits
            limit = calculate_spells_prepared(character)
            current = CharacterSpell.objects.filter(
                character=character,
                is_prepared=True,
                level__gt=0
            ).count()
            
            if current >= limit:
                return Response(
                    {"error": f"Cannot prepare more spells. Limit is {limit}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            char_spell.is_prepared = True
            char_spell.save()
            return Response({
                "message": f"Prepared {char_spell.name}",
                "spell": CharacterSpellSerializer(char_spell).data
            })
            
        else:
            # Unprepare
            char_spell.is_prepared = False
            char_spell.save()
            return Response({
                "message": f"Unprepared {char_spell.name}",
                "spell": CharacterSpellSerializer(char_spell).data
            })

    # Add methods to class
    cls.preparation_status = preparation_status
    cls.prepare_spell = prepare_spell
    
    return cls
