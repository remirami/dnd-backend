
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
