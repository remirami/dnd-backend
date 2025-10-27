from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import render
import json
import csv
import tempfile
import os
from .models import Enemy
from .serializers import EnemySerializer
from .management.commands.import_monsters import Command as ImportCommand


class EnemyViewSet(viewsets.ModelViewSet):
    queryset = Enemy.objects.all()
    serializer_class = EnemySerializer
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=['post'])
    def import_json(self, request):
        """Import monsters from JSON file"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        update_existing = request.data.get('update_existing', False)
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                content = file.read().decode('utf-8')
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Use the import command
            import_cmd = ImportCommand()
            import_cmd.handle(
                source='json',
                file=temp_file_path,
                dry_run=False,
                update_existing=update_existing
            )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            return Response(
                {'message': 'Monsters imported successfully'}, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """Import monsters from CSV file"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        update_existing = request.data.get('update_existing', False)
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as temp_file:
                content = file.read().decode('utf-8')
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Use the import command
            import_cmd = ImportCommand()
            import_cmd.handle(
                source='csv',
                file=temp_file_path,
                dry_run=False,
                update_existing=update_existing
            )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            return Response(
                {'message': 'Monsters imported successfully'}, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def import_srd(self, request):
        """Import monsters from D&D 5e SRD"""
        update_existing = request.data.get('update_existing', False)
        
        try:
            import_cmd = ImportCommand()
            import_cmd.handle(
                source='srd',
                dry_run=False,
                update_existing=update_existing
            )
            
            return Response(
                {'message': 'SRD monsters imported successfully'}, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def export_template(self, request):
        """Export a template file for monster imports"""
        format_type = request.query_params.get('format', 'json')
        
        if format_type == 'json':
            template_data = {
                "monsters": [
                    {
                        "name": "Example Monster",
                        "hit_points": 10,
                        "armor_class": 12,
                        "challenge_rating": "1/4",
                        "strength": 10,
                        "dexterity": 10,
                        "constitution": 10,
                        "intelligence": 10,
                        "wisdom": 10,
                        "charisma": 10,
                        "speed": "30 ft.",
                        "darkvision": "60 ft.",
                        "passive_perception": 10,
                        "attacks": [
                            {
                                "name": "Attack Name",
                                "bonus": 2,
                                "damage": "1d6+1 damage_type"
                            }
                        ],
                        "abilities": [
                            {
                                "name": "Ability Name",
                                "description": "Ability description"
                            }
                        ],
                        "resistances": [
                            {
                                "damage_type": "Fire",
                                "resistance_type": "resistance",
                                "notes": "Optional notes"
                            }
                        ],
                        "languages": ["Common", "Other Language"]
                    }
                ]
            }
            
            response = Response(template_data)
            response['Content-Disposition'] = 'attachment; filename="monster_template.json"'
            return response
            
        elif format_type == 'csv':
            template_data = [
                "name,hit_points,armor_class,challenge_rating,strength,dexterity,constitution,intelligence,wisdom,charisma,speed,darkvision,passive_perception,attacks,abilities,languages",
                "Example Monster,10,12,1/4,10,10,10,10,10,10,\"30 ft.\",\"60 ft.\",10,\"Attack Name (+2, 1d6+1 damage_type)\",\"Ability Name: Description\",\"Common, Other Language\""
            ]
            
            response = Response('\n'.join(template_data))
            response['Content-Type'] = 'text/csv'
            response['Content-Disposition'] = 'attachment; filename="monster_template.csv"'
            return response
        
        return Response(
            {'error': 'Invalid format. Use json or csv'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


def import_monsters_view(request):
    """Web interface for monster imports"""
    return render(request, 'bestiary/import_monsters.html')
