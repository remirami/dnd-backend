"""
Tactical Combat Endpoints

Endpoints for AOE targeting, grappling, and cover systems.
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status
from .aoe_utils import get_aoe_targets, AOE_SPELL_TEMPLATES
from .utils import calculate_damage, calculate_saving_throw, roll_d20


def cast_aoe_spell_endpoint(self, request, pk=None):
    """
    Cast an area of effect spell hitting multiple targets.
    
    POST /api/combat/sessions/{id}/cast_aoe_spell/
    
    Request body:
    {
        "caster_id": 1,
        "spell_name": "fireball",  # or custom params
        "save_dc": 15,
        
        # For sphere (like Fireball)
        "origin_x": 50,
        "origin_y": 50,
        "radius": 20,
        
        # OR for cone (like Burning Hands)
        "caster_x": 10,
        "caster_y": 10,
        "target_x": 30,
        "target_y": 30,
        "length": 15,
        
        # OR for line (like Lightning Bolt)
        "start_x": 10,
        "start_y": 10,
        "end_x": 110,
        "end_y": 10,
        "width": 5,
        
        # OR for cube (like Thunderwave)
        "origin_x": 10,
        "origin_y": 10,
        "size": 15,
        
        # Damage (optional if using template)
        "damage_dice": "8d6",
        "damage_type": "fire",
        "save_type": "dex"
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    caster_id = request.data.get('caster_id')
    spell_name = request.data.get('spell_name', '').lower()
    
    if not caster_id:
        return Response(
            {"error": "caster_id is required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        caster = session.participants.get(id=caster_id)
    except:
        return Response(
            {"error": "Caster not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    # Get spell template or use custom params
    if spell_name in AOE_SPELL_TEMPLATES:
        template = AOE_SPELL_TEMPLATES[spell_name]
        shape = template['shape']
        damage_dice = template['base_damage']
        damage_type = template['damage_type']
        save_type = template['save_type']
        save_dc = request.data.get('save_dc', 15)
    else:
        # Custom AOE spell
        shape = request.data.get('shape')
        damage_dice = request.data.get('damage_dice')
        damage_type = request.data.get('damage_type')
        save_type = request.data.get('save_type', 'dex')
        save_dc = request.data.get('save_dc', 15)
        
        if not all([shape, damage_dice, damage_type]):
            return Response(
                {"error": "For custom spells, shape, damage_dice, and damage_type are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
    
    # Get targets based on shape
    participants = session.participants.filter(is_active=True)
    
    try:
        if shape == 'sphere':
            targets = get_aoe_targets(participants, 'sphere',
                origin_x=request.data.get('origin_x', 0),
                origin_y=request.data.get('origin_y', 0),
                radius=request.data.get('radius', 20)
            )
        elif shape == 'cone':
            targets = get_aoe_targets(participants, 'cone',
                caster_x=request.data.get('caster_x', caster.position_x),
                caster_y=request.data.get('caster_y', caster.position_y),
                target_x=request.data.get('target_x', 0),
                target_y=request.data.get('target_y', 0),
                length=request.data.get('length', 15)
            )
        elif shape == 'line':
            targets = get_aoe_targets(participants, 'line',
                start_x=request.data.get('start_x', caster.position_x),
                start_y=request.data.get('start_y', caster.position_y),
                end_x=request.data.get('end_x', 0),
                end_y=request.data.get('end_y', 0),
                width=request.data.get('width', 5)
            )
        elif shape == 'cube':
            targets = get_aoe_targets(participants, 'cube',
                origin_x=request.data.get('origin_x', 0),
                origin_y=request.data.get('origin_y', 0),
                size=request.data.get('size', 15)
            )
        else:
            return Response(
                {"error": f"Unknown shape: {shape}"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            {"error": f"Error calculating targets: {str(e)}"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Apply damage/saves to each target
    targets_affected = []
    
    for participant, distance in targets:
        # Roll save
        save_roll, _ = roll_d20()
        save_modifier = participant.get_ability_modifier(save_type.upper())
        
        # Apply cover bonus to DEX saves
        cover_bonus = 0
        if save_type.lower() == 'dex' and participant.cover_type != 'none':
            cover_bonus = {'half': 2, 'three_quarters': 5}.get(participant.cover_type, 0)
        
        save_total, _ = calculate_saving_throw(save_roll, save_modifier, 0, False)
        save_total += cover_bonus
        
        save_success = save_total >= save_dc
        
        # Roll damage - calculate_damage returns (damage, breakdown) tuple
        base_damage, _ = calculate_damage(damage_dice)
        damage_taken = base_damage // 2 if save_success else base_damage
        
        # Apply damage
        participant.take_damage(damage_taken, damage_type, check_concentration=True)
        
        targets_affected.append({
            'participant_id': participant.id,
            'name': participant.get_name(),
            'distance': round(distance, 1),
            'save_roll': save_roll,
            'save_modifier': save_modifier,
            'cover_bonus': cover_bonus,
            'save_total': save_total,
            'save_dc': save_dc,
            'save_result': 'success' if save_success else 'failed',
            'damage_rolled': base_damage,
            'damage_taken': damage_taken,
            'current_hp': participant.current_hp,
            'max_hp': participant.max_hp
        })
    
    return Response({
        'spell_name': spell_name or 'Custom AOE',
        'caster': caster.get_name(),
        'shape': shape,
        'damage_type': damage_type,
        'save_type': save_type.upper(),
        'save_dc': save_dc,
        'targets_affected': targets_affected,
        'total_targets': len(targets_affected)
    })


def grapple_endpoint(self, request, pk=None):
    """
    Initiate a grapple.
    
    POST /api/combat/sessions/{id}/grapple/
    
    Request body:
    {
        "grappler_id": 1,
        "target_id": 2
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    grappler_id = request.data.get('grappler_id')
    target_id = request.data.get('target_id')
    
    if not grappler_id or not target_id:
        return Response(
            {"error": "grappler_id and target_id are required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        grappler = session.participants.get(id=grappler_id)
        target = session.participants.get(id=target_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    # Check if grappler has action available
    if grappler.action_used:
        return Response(
            {"error": "Grappler has already used their action this turn"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already grappling
    if grappler.is_grappling:
        return Response(
            {"error": "Grappler is already grappling someone"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Check if target already grappled
    if target.grappled_by:
        return Response(
            {"error": f"{target.get_name()} is already grappled"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Contested check: Grappler's Athletics vs Target's Athletics or Acrobatics
    grappler_roll, _ = roll_d20()
    grappler_athletics = grappler.get_ability_modifier('STR')  # Simplified
    grappler_total = grappler_roll + grappler_athletics
    
    target_roll, _ = roll_d20()
    # Target can use either Athletics (STR) or Acrobatics (DEX)
    target_athletics = target.get_ability_modifier('STR')
    target_acrobatics = target.get_ability_modifier('DEX')
    target_modifier = max(target_athletics, target_acrobatics)
    target_total = target_roll + target_modifier
    
    success = grappler_total > target_total
    
    if success:
        # Apply grapple
        grappler.is_grappling = True
        grappler.action_used = True
        grappler.save()
        
        target.grappled_by = grappler
        target.save()
        
        message = f"{grappler.get_name()} successfully grapples {target.get_name()}! {target.get_name()}'s speed is now 0."
    else:
        grappler.action_used = True
        grappler.save()
        message = f"{grappler.get_name()} fails to grapple {target.get_name()}."
    
    return Response({
        'success': success,
        'message': message,
        'grappler_roll': grappler_roll,
        'grappler_modifier': grappler_athletics,
        'grappler_total': grappler_total,
        'target_roll': target_roll,
        'target_modifier': target_modifier,
        'target_total': target_total,
        'target_speed': 0 if success else target.character.stats.speed if target.character else 30
    })


def escape_grapple_endpoint(self, request, pk=None):
    """
    Attempt to escape a grapple.
    
    POST /api/combat/sessions/{id}/escape_grapple/
    
    Request body:
    {
        "participant_id": 2
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    participant_id = request.data.get('participant_id')
    
    if not participant_id:
        return Response(
            {"error": "participant_id is required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        participant = session.participants.get(id=participant_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    if not participant.grappled_by:
        return Response(
            {"error": f"{participant.get_name()} is not grappled"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    grappler = participant.grappled_by
    
    # Contested check: Grappled's Athletics or Acrobatics vs Grappler's Athletics
    participant_roll, _ = roll_d20()
    participant_athletics = participant.get_ability_modifier('STR')
    participant_acrobatics = participant.get_ability_modifier('DEX')
    participant_modifier = max(participant_athletics, participant_acrobatics)
    participant_total = participant_roll + participant_modifier
    
    grappler_roll, _ = roll_d20()
    grappler_athletics = grappler.get_ability_modifier('STR')
    grappler_total = grappler_roll + grappler_athletics
    
    success = participant_total > grappler_total
    
    if success:
        # Escape successful
        participant.grappled_by = None
        participant.action_used = True
        participant.save()
        
        grappler.is_grappling = False
        grappler.save()
        
        message = f"{participant.get_name()} escapes the grapple!"
    else:
        participant.action_used = True
        participant.save()
        message = f"{participant.get_name()} fails to escape the grapple."
    
    return Response({
        'success': success,
        'message': message,
        'participant_roll': participant_roll,
        'participant_modifier': participant_modifier,
        'participant_total': participant_total,
        'grappler_roll': grappler_roll,
        'grappler_modifier': grappler_athletics,
        'grappler_total': grappler_total
    })


def set_cover_endpoint(self, request, pk=None):
    """
    Set cover type for a participant.
    
    POST /api/combat/sessions/{id}/set_cover/
    
    Request body:
    {
        "participant_id": 1,
        "cover_type": "half"  // none, half, three_quarters, full
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    participant_id = request.data.get('participant_id')
    cover_type = request.data.get('cover_type')
    
    if not participant_id or not cover_type:
        return Response(
            {"error": "participant_id and cover_type are required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    valid_cover_types = ['none', 'half', 'three_quarters', 'full']
    if cover_type not in valid_cover_types:
        return Response(
            {"error": f"Invalid cover_type. Must be one of: {', '.join(valid_cover_types)}"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        participant = session.participants.get(id=participant_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    old_cover = participant.cover_type
    participant.cover_type = cover_type
    participant.save()
    
    # Calculate bonuses
    cover_bonuses = {
        'none': {'ac': 0, 'dex_save': 0},
        'half': {'ac': 2, 'dex_save': 2},
        'three_quarters': {'ac': 5, 'dex_save': 5},
        'full': {'ac': float('inf'), 'dex_save': float('inf')}
    }
    
    bonus = cover_bonuses[cover_type]
    
    return Response({
        'participant': participant.get_name(),
        'old_cover': old_cover,
        'new_cover': cover_type,
        'ac_bonus': bonus['ac'] if bonus['ac'] != float('inf') else 'Cannot be targeted',
        'dex_save_bonus': bonus['dex_save'] if bonus['dex_save'] != float('inf') else 'Total protection',
        'message': f"{participant.get_name()} now has {cover_type.replace('_', ' ')} cover"
    })
