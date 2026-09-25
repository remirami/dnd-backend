"""
Equipment endpoints for CharacterViewSet
This file adds starting equipment endpoints that should be imported in views.py
"""
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from characters.models import CharacterItem


def add_equipment_endpoints_to_viewset(cls):
    """
    Decorator to add equipment endpoints to CharacterViewSet
    Usage: Add @add_equipment_endpoints_to_viewset before CharacterViewSet class
    """
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def starting_equipment_choices(self, request):
        """Get starting equipment choices for a specific class"""
        from characters.starting_equipment import get_all_packs, get_starting_equipment_for_class
        
        class_name = request.query_params.get('class_name')
        if not class_name:
            return Response(
                {"error": "class_name parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        clean_class_name = class_name.split('(')[0].strip()
        equipment_data = get_starting_equipment_for_class(clean_class_name)
        if not equipment_data:
            return Response(
                {"error": f"No starting equipment data for class '{class_name}'"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            "class_name": equipment_data['class_name'],
            "choices": equipment_data['choices'],
            "default_items": equipment_data['default_items'],
            "starting_gold": equipment_data['starting_gold'],
            "available_packs": list(get_all_packs().keys()),
            "pack_definitions": get_all_packs()
        })
    
    @action(detail=True, methods=['post'])
    def apply_starting_equipment(self, request, pk=None):
        """Apply selected starting equipment to a character"""
        from characters.starting_equipment import get_equipment_pack, get_starting_equipment_for_class
        
        character = self.get_object()
        selections = request.data.get('selections', {})
        selected_weapons = request.data.get('selected_weapons', [])
        include_shield = request.data.get('include_shield', False)
        
        if not selections and not selected_weapons:
            return Response(
                {"error": "selections or selected_weapons are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get class equipment data
        class_name = character.character_class.name.lower()
        equipment_data = get_starting_equipment_for_class(class_name)
        
        if not equipment_data:
            return Response(
                {"error": f"No equipment data for class {class_name}"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        items_to_add = []
        
        # Add custom selected starting weapons
        if selected_weapons:
            for w in selected_weapons:
                w_name = w if isinstance(w, str) else w.get('name')
                w_qty = 1 if isinstance(w, str) else w.get('quantity', 1)
                if w_name:
                    items_to_add.append({'name': w_name, 'quantity': w_qty})
                    w_lower = w_name.lower()
                    if 'crossbow' in w_lower:
                        items_to_add.append({'name': 'Crossbow Bolt', 'quantity': 20})
                    elif 'bow' in w_lower and 'crossbow' not in w_lower:
                        items_to_add.append({'name': 'Arrow', 'quantity': 20})
                    elif 'sling' in w_lower:
                        items_to_add.append({'name': 'Sling Bullet', 'quantity': 20})
                    elif 'blowgun' in w_lower:
                        items_to_add.append({'name': 'Blowgun Needle', 'quantity': 50})
        
        if include_shield:
            items_to_add.append({'name': 'Shield', 'quantity': 1})
        
        # Process each choice
        for choice in equipment_data['choices']:
            choice_num = choice['choice_number']
            selected_option = selections.get(str(choice_num))
            is_weapon_choice = 'weapon' in choice.get('description', '').lower()
            
            if not selected_option:
                # If custom weapons were selected and this is a weapon choice, skip validation
                if selected_weapons and is_weapon_choice:
                    continue
                return Response(
                    {"error": f"Missing selection for choice {choice_num}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find the selected option
            option_data = None
            for opt in choice['options']:
                if opt['label'] == selected_option:
                    option_data = opt
                    break
            
            if not option_data:
                return Response(
                    {"error": f"Invalid option '{selected_option}' for choice {choice_num}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add items from this option
            if 'items' in option_data:
                # Track how many choice items we've encountered to map to _sub_0, _sub_1, etc.
                choice_item_index = 0
                
                for item_ref in option_data['items']:
                    item_name = item_ref['name']
                    quantity = item_ref.get('quantity', 1)
                    
                    # Check if this is a placeholder choice
                    if 'choice' in item_name.lower():
                        # Try to find the sub-selection
                        # Key format: "{choice_num}_sub_{index}"
                        sub_key = f"{choice_num}_sub_{choice_item_index}"
                        selected_sub = selections.get(sub_key)
                        
                        if selected_sub:
                            items_to_add.append({'name': selected_sub, 'quantity': quantity})
                        else:
                            # Fallback: maybe singular "_sub" was sent (old format/frontend)
                            short_key = f"{choice_num}_sub"
                            selected_sub_short = selections.get(short_key)
                            if selected_sub_short and choice_item_index == 0:
                                items_to_add.append({'name': selected_sub_short, 'quantity': quantity})
                            else:
                                # Start logging but don't fail hard, maybe user didn't select?
                                # But we should probably error if required choices missing.
                                # For now, skip adding placeholder.
                                pass
                        
                        choice_item_index += 1
                    else:
                        items_to_add.append(item_ref)

            # Add pack if specified
            if 'pack' in option_data:
                pack_name = option_data['pack']
                pack_data = get_equipment_pack(pack_name)
                
                if pack_data:
                    items_to_add.extend(pack_data['items'])
                    
                    # Create the Pack Item itself so it shows on character sheet
                    try:
                        # Calculate value/weight estimates or just create placeholder
                        # Format contents for description
                        contents_desc = "Contains:\n" + "\n".join([f"- {item['name']} (x{item.get('quantity', 1)})" for item in pack_data['items']])
                        
                        from items.models import Item, ItemCategory
                        
                        # Ensure category exists
                        gear_cat, _ = ItemCategory.objects.get_or_create(name="Adventuring Gear")
                        
                        _pack_item, _created = Item.objects.get_or_create(
                            name=pack_name,
                            defaults={
                                'description': contents_desc,
                                'category': gear_cat,
                                'weight': 0, # Bundle weight is sum of parts usually
                                'value': pack_data.get('cost', 0),
                                'rarity': 'common'
                            }
                        )
                        
                        # Add the pack container itself to the list (quantity 1)
                        items_to_add.append({'name': pack_name, 'quantity': 1})
                        
                    except Exception as e:
                        print(f"Error creating pack item: {e}")
        
        # Add default items
        items_to_add.extend(equipment_data.get('default_items', []))
        
        # Now add all items to character's inventory
        added_items = []
        failed_items = []
        
        for item_spec in items_to_add:
            item_name = item_spec['name']
            quantity = item_spec.get('quantity', 1)
            
            # Skip ANY remaining special markers (just in case)
            if 'choice' in item_name.lower():
                continue
            
            try:
                # Try to find the item
                item = Item.objects.filter(name__iexact=item_name).first()
                if not item:
                    # If this is ammunition, auto-create under Adventuring Gear
                    if any(ammo_kw in item_name.lower() for ammo_kw in ['arrow', 'bolt', 'bullet', 'needle']):
                        from items.models import ItemCategory
                        gear_cat, _ = ItemCategory.objects.get_or_create(name="Adventuring Gear")
                        item, _ = Item.objects.get_or_create(
                            name=item_name,
                            defaults={
                                'description': f"Ammunition ({item_name})",
                                'category': gear_cat,
                                'weight': 0.05,
                                'value': 1,
                                'rarity': 'common',
                            }
                        )
                    else:
                        failed_items.append(item_name)
                        continue
                
                # Add to character inventory
                CharacterItem.objects.create(
                    character=character,
                    item=item,
                    quantity=quantity,
                    is_equipped=False
                )
                added_items.append(f"{item_name} x{quantity}")
                
            except Exception as e:
                failed_items.append(f"{item_name}: {e!s}")
        
        # Add starting gold
        import random
        gold_min = equipment_data['starting_gold']['min']
        gold_max = equipment_data['starting_gold']['max']
        starting_gold = random.randint(gold_min, gold_max)
        character.gold_pieces = starting_gold
        character.save()
        
        return Response({
            "message": "Starting equipment applied successfully",
            "added_items": added_items,
            "failed_items": failed_items,
            "starting_gold": starting_gold
        })
    
    # Add methods to class
    cls.starting_equipment_choices = starting_equipment_choices
    cls.apply_starting_equipment = apply_starting_equipment
    
    return cls
