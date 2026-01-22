"""
Character Builder API ViewSet

Provides REST endpoints for the character creation wizard
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from characters.builder_models import CharacterBuilderSession
from characters.services import CharacterBuilderService
from characters.serializers import CharacterSerializer
from characters.models import CharacterClass, CharacterRace, CharacterBackground


class CharacterBuilderViewSet(viewsets.GenericViewSet):
    """
    Character Builder API
    
    Provides step-by-step wizard for creating characters
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='start')
    def start_session(self, request):
        """
        Start a new character builder session
        
        POST /api/characters/builder/start/
        {
            "ability_score_method": "standard_array"  // or "point_buy", "manual"
        }
        """
        method = request.data.get('ability_score_method', 'standard_array')
        
        # Validate method
        valid_methods = ['standard_array', 'point_buy', 'manual']
        if method not in valid_methods:
            return Response(
                {"error": f"Invalid ability_score_method. Must be one of: {', '.join(valid_methods)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create session
        session = CharacterBuilderService.start_session(request.user, method)
        
        return Response({
            "message": "Character builder session started",
            "session_id": str(session.id),
            "current_step": session.current_step,
            "method": method,
            "expires_at": session.expires_at.isoformat()
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get', 'delete'], url_path='session/(?P<session_id>[^/.]+)', url_name='session-detail')
    def session_detail(self, request, session_id=None):
        """
        Get or delete a session
        
        GET/DELETE /api/characters/builder/session/{session_id}/
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if request.method == 'DELETE':
            session.delete()
            return Response({
                "message": "Session deleted"
            }, status=status.HTTP_200_OK)
        
        # GET request
        return Response({
            "session_id": str(session.id),
            "current_step": session.current_step,
            "data": session.data,
            "expires_at": session.expires_at.isoformat()
        })
    
    @action(detail=False, methods=['post'], url_path='(?P<session_id>[^/.]+)/assign-abilities')
    def assign_abilities(self, request, session_id=None):
        """
        Assign ability scores (Step 2)
        
        POST /api/characters/builder/{session_id}/assign-abilities/
        {
            "str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8
        }
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate we have all scores
        required = ['str', 'dex', 'con', 'int', 'wis', 'cha']
        for ability in required:
            if ability not in request.data:
                return Response(
                    {"error": f"Missing ability score: {ability}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Convert scores to integers (API sends as strings)
        try:
            scores = {
                ability: int(request.data[ability])
                for ability in required
            }
        except (ValueError, TypeError):
            return Response(
                {"error": "All ability scores must be valid integers"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Refresh session to get latest data
        session.refresh_from_db()
        
        # Assign abilities
        success, error, data = CharacterBuilderService.assign_abilities(session, scores)
        
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            "message": "Abilities assigned successfully",
            **data
        })
    
    @action(detail=False, methods=['post'], url_path='(?P<session_id>[^/.]+)/choose-race')
    def choose_race(self, request, session_id=None):
        """
        Choose race (Step 3)
        
        POST /api/characters/builder/{session_id}/choose-race/
        {
            "race_id": 1
        }
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        race_id = request.data.get('race_id')
        if not race_id:
            return Response(
                {"error": "race_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, error, data = CharacterBuilderService.choose_race(session, race_id)
        
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            "message": "Race chosen successfully",
            **data
        })
    
    @action(detail=False, methods=['post'], url_path='(?P<session_id>[^/.]+)/choose-class')
    def choose_class(self, request, session_id=None):
        """
        Choose class (Step 4)
        
        POST /api/characters/builder/{session_id}/choose-class/
        {
            "class_id": 2,
            "subclass": "champion"  // Optional
        }
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        class_id = request.data.get('class_id')
        if not class_id:
            return Response(
                {"error": "class_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subclass = request.data.get('subclass')
        
        success, error, data = CharacterBuilderService.choose_class(session, class_id, subclass)
        
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            "message": "Class chosen successfully",
            **data
        })
    
    @action(detail=False, methods=['post'], url_path='(?P<session_id>[^/.]+)/choose-background')
    def choose_background(self, request, session_id=None):
        """
        Choose background (Step 5)
        
        POST /api/characters/builder/{session_id}/choose-background/
        {
            "background_id": 3
        }
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        background_id = request.data.get('background_id')
        if not background_id:
            return Response(
                {"error": "background_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, error, data = CharacterBuilderService.choose_background(session, background_id)
        
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            "message": "Background chosen successfully",
            **data
        })
    
    @action(detail=False, methods=['post'], url_path='(?P<session_id>[^/.]+)/finalize')
    def finalize(self, request, session_id=None):
        """
        Finalize character creation (Step 7)
        
        POST /api/characters/builder/{session_id}/finalize/
        {
            "name": "Thorin Ironforge",
            "alignment": "LG"  // Optional, default "N"
        }
        """
        session = CharacterBuilderService.get_session(session_id, request.user)
        
        if not session:
            return Response(
                {"error": "Session not found or expired"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        name = request.data.get('name')
        if not name:
            return Response(
                {"error": "name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alignment = request.data.get('alignment', 'N')
        hp_method = request.data.get('hp_method', 'fixed')
        
        success, error, character = CharacterBuilderService.finalize_character(
            session, name, alignment, hp_method
        )
        
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize character
        serializer = CharacterSerializer(character)
        
        return Response({
            "message": "Character created successfully!",
            "character": serializer.data
        }, status=status.HTTP_201_CREATED)
