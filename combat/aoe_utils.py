"""
AOE (Area of Effect) Spell Utilities

Handles targeting and damage calculation for spells that affect multiple targets.
"""
import math
from typing import List, Tuple, Dict


def calculate_distance(x1, y1, x2, y2):
    """Calculate distance between two points in feet"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_targets_in_sphere(participants, origin_x, origin_y, radius):
    """
    Get all participants within a spherical area.
    
    Args:
        participants: QuerySet of CombatParticipant
        origin_x: X coordinate of sphere center
        origin_y: Y coordinate of sphere center
        radius: Radius in feet
    
    Returns:
        List of (participant, distance) tuples
    """
    targets = []
    for participant in participants:
        if not participant.is_active:
            continue
            
        distance = calculate_distance(
            origin_x, origin_y,
            participant.position_x, participant.position_y
        )
        
        if distance <= radius:
            targets.append((participant, distance))
    
    return targets


def get_targets_in_cone(participants, caster_x, caster_y, target_x, target_y, length, width=None):
    """
    Get all participants within a cone area.
    
    Args:
        participants: QuerySet of CombatParticipant
        caster_x: X coordinate of caster
        caster_y: Y coordinate of caster
        target_x: X coordinate of cone direction
        target_y: Y coordinate of cone direction
        length: Length of cone in feet (15, 30, 60)
        width: Width at end (defaults to length for standard D&D cones)
    
    Returns:
        List of (participant, distance) tuples
    """
    if width is None:
        width = length
        
    targets = []
    
    # Calculate cone direction vector
    dx = target_x - caster_x
    dy = target_y - caster_y
    cone_length = math.sqrt(dx**2 + dy**2)
    
    if cone_length == 0:
        return targets
    
    # Normalize direction
    dir_x = dx / cone_length
    dir_y = dy / cone_length
    
    for participant in participants:
        if not participant.is_active:
            continue
        
        # Vector from caster to participant
        px = participant.position_x - caster_x
        py = participant.position_y - caster_y
        
        # Distance along cone direction
        distance_along = px * dir_x + py * dir_y
        
        if distance_along < 0 or distance_along > length:
            continue  # Not in cone length
        
        # Distance perpendicular to cone direction
        distance_perp = abs(px * (-dir_y) + py * dir_x)
        
        # Cone width at this distance
        cone_width_at_distance = (distance_along / length) * width
        
        if distance_perp <= cone_width_at_distance:
            actual_distance = math.sqrt(px**2 + py**2)
            targets.append((participant, actual_distance))
    
    return targets


def get_targets_in_line(participants, start_x, start_y, end_x, end_y, width=5):
    """
    Get all participants within a line area.
    
    Args:
        participants: QuerySet of CombatParticipant
        start_x: X coordinate of line start
        start_y: Y coordinate of line start
        end_x: X coordinate of line end
        end_y: Y coordinate of line end
        width: Width of line in feet (default 5)
    
    Returns:
        List of (participant, distance) tuples
    """
    targets = []
    
    # Line direction vector
    dx = end_x - start_x
    dy = end_y - start_y
    line_length = math.sqrt(dx**2 + dy**2)
    
    if line_length == 0:
        return targets
    
    # Normalize
    dir_x = dx / line_length
    dir_y = dy / line_length
    
    for participant in participants:
        if not participant.is_active:
            continue
        
        # Vector from start to participant
        px = participant.position_x - start_x
        py = participant.position_y - start_y
        
        # Project onto line
        distance_along = px * dir_x + py * dir_y
        
        if distance_along < 0 or distance_along > line_length:
            continue  # Not along the line
        
        # Perpendicular distance from line
        distance_perp = abs(px * (-dir_y) + py * dir_x)
        
        if distance_perp <= width / 2:
            actual_distance = distance_along  # Distance from caster
            targets.append((participant, actual_distance))
    
    return targets


def get_targets_in_cube(participants, origin_x, origin_y, size):
    """
    Get all participants within a cube/square area.
    
    Args:
        participants: QuerySet of CombatParticipant
        origin_x: X coordinate of cube corner
        origin_y: Y coordinate of cube corner
        size: Size of cube in feet (e.g., 15, 20)
    
    Returns:
        List of (participant, distance) tuples
    """
    targets = []
    
    for participant in participants:
        if not participant.is_active:
            continue
        
        # Check if within square bounds
        if (origin_x <= participant.position_x <= origin_x + size and
            origin_y <= participant.position_y <= origin_y + size):
            distance = calculate_distance(
                origin_x, origin_y,
                participant.position_x, participant.position_y
            )
            targets.append((participant, distance))
    
    return targets


# Common AOE spell templates
AOE_SPELL_TEMPLATES = {
    'fireball': {
        'name': 'Fireball',
        'shape': 'sphere',
        'size': 20,  # 20 ft radius
        'save_type': 'dex',
        'base_damage': '8d6',
        'damage_type': 'fire',
        'description': 'A bright streak flashes from your pointing finger to a point you choose, then blossoms with a low roar into an explosion of flame.'
    },
    'cone_of_cold': {
        'name': 'Cone of Cold',
        'shape': 'cone',
        'size': 60,  # 60 ft cone
        'save_type': 'con',
        'base_damage': '8d8',
        'damage_type': 'cold',
        'description': 'A blast of cold air erupts from your hands.'
    },
    'lightning_bolt': {
        'name': 'Lightning Bolt',
        'shape': 'line',
        'size': 100,  # 100 ft line
        'width': 5,
        'save_type': 'dex',
        'base_damage': '8d6',
        'damage_type': 'lightning',
        'description': 'A stroke of lightning forming a line 100 feet long and 5 feet wide.'
    },
    'thunderwave': {
        'name': 'Thunderwave',
        'shape': 'cube',
        'size': 15,  # 15 ft cube
        'save_type': 'con',
        'base_damage': '2d8',
        'damage_type': 'thunder',
        'description': 'A wave of thunderous force sweeps out from you.'
    },
    'burning_hands': {
        'name': 'Burning Hands',
        'shape': 'cone',
        'size': 15,  # 15 ft cone
        'save_type': 'dex',
        'base_damage': '3d6',
        'damage_type': 'fire',
        'description': 'A thin sheet of flames shoots forth from your outstretched fingertips.'
    },
}


def get_aoe_targets(participants, shape, **kwargs):
    """
    Get targets based on AOE shape.
    
    Args:
        participants: QuerySet of CombatParticipant
        shape: 'sphere', 'cone', 'line', or 'cube'
        **kwargs: Shape-specific parameters
    
    Returns:
        List of (participant, distance) tuples
    """
    if shape == 'sphere':
        return get_targets_in_sphere(
            participants,
            kwargs['origin_x'],
            kwargs['origin_y'],
            kwargs['radius']
        )
    elif shape == 'cone':
        return get_targets_in_cone(
            participants,
            kwargs['caster_x'],
            kwargs['caster_y'],
            kwargs['target_x'],
            kwargs['target_y'],
            kwargs['length'],
            kwargs.get('width')
        )
    elif shape == 'line':
        return get_targets_in_line(
            participants,
            kwargs['start_x'],
            kwargs['start_y'],
            kwargs['end_x'],
            kwargs['end_y'],
            kwargs.get('width', 5)
        )
    elif shape == 'cube':
        return get_targets_in_cube(
            participants,
            kwargs['origin_x'],
            kwargs['origin_y'],
            kwargs['size']
        )
    else:
        raise ValueError(f"Unknown AOE shape: {shape}")
