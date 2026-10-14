"""
Battlefield Grid & Tactical Pathfinding Engine for D&D 5e Combat.

Handles:
- Procedural battlefield terrain layouts (identical seed matching frontend)
- Impassable obstacle collisions (pillars, trees, stalagmites, walls)
- 5e Difficult terrain cost calculations (10 ft per 5-ft square)
- Tile-by-tile Dijkstra pathfinding (prevents 'skipping' difficult terrain or obstacles)
- Opportunity attack trigger tracking along the actual movement path
"""
import heapq
from typing import Any

COLS = 10  # 0..45 ft in 5 ft steps
ROWS = 8   # 0..35 ft in 5 ft steps

BATTLEFIELD_LAYOUTS = [
    {
        "id": 0,
        "name": "Forgotten Crypt",
        "features": [
            {"col": 4, "row": 2, "name": "Ancient Pillar", "blocks_movement": True, "cover": "total"},
            {"col": 4, "row": 5, "name": "Ancient Pillar", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 2, "name": "Ancient Pillar", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 5, "name": "Ancient Pillar", "blocks_movement": True, "cover": "total"},
            {"col": 3, "row": 1, "name": "Stone Sarcophagus", "blocks_movement": False, "cover": "half"},
            {"col": 6, "row": 6, "name": "Crumbled Masonry", "blocks_movement": False, "cover": "half"},
        ],
    },
    {
        "id": 1,
        "name": "Ruined Watchtower",
        "features": [
            {"col": 3, "row": 5, "name": "Watchtower Pylon", "blocks_movement": True, "cover": "total"},
            {"col": 4, "row": 3, "name": "Timber Barricade", "blocks_movement": False, "cover": "half"},
            {"col": 4, "row": 4, "name": "Timber Barricade", "blocks_movement": False, "cover": "half"},
            {"col": 5, "row": 1, "name": "Spiked Palisade", "blocks_movement": False, "cover": "half"},
            {"col": 5, "row": 6, "name": "Spiked Palisade", "blocks_movement": False, "cover": "half"},
        ],
    },
    {
        "id": 2,
        "name": "Sunken Cavern",
        "features": [
            {"col": 5, "row": 3, "name": "Great Stalagmite", "blocks_movement": True, "cover": "total"},
            {"col": 3, "row": 4, "name": "Sunken Boulder", "blocks_movement": False, "cover": "half"},
            {"col": 6, "row": 3, "name": "Sunken Boulder", "blocks_movement": False, "cover": "half"},
            {"col": 4, "row": 1, "name": "Deep Bog", "blocks_movement": False, "difficult_terrain": True},
            {"col": 4, "row": 2, "name": "Deep Bog", "blocks_movement": False, "difficult_terrain": True},
            {"col": 5, "row": 5, "name": "Deep Bog", "blocks_movement": False, "difficult_terrain": True},
            {"col": 5, "row": 6, "name": "Deep Bog", "blocks_movement": False, "difficult_terrain": True},
        ],
    },
    {
        "id": 3,
        "name": "Mountain Chokepoint",
        "features": [
            {"col": 4, "row": 0, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 4, "row": 1, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 0, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 4, "row": 6, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 4, "row": 7, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 7, "name": "Cliff Face", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 3, "name": "Crag Outcrop", "blocks_movement": False, "cover": "half"},
        ],
    },
    {
        "id": 4,
        "name": "Overgrown Glade",
        "features": [
            {"col": 4, "row": 1, "name": "Ancient Oak", "blocks_movement": True, "cover": "total"},
            {"col": 5, "row": 6, "name": "Ancient Oak", "blocks_movement": True, "cover": "total"},
            {"col": 3, "row": 3, "name": "Trade Crates", "blocks_movement": False, "cover": "half"},
            {"col": 4, "row": 5, "name": "Dense Brambles", "blocks_movement": False, "difficult_terrain": True},
            {"col": 5, "row": 2, "name": "Dense Brambles", "blocks_movement": False, "difficult_terrain": True},
        ],
    },
]


def get_battlefield_layout(session_id: int = 0) -> dict[str, Any]:
    """Retrieve battlefield layout deterministically based on session id."""
    idx = abs(int(session_id or 0)) % len(BATTLEFIELD_LAYOUTS)
    return BATTLEFIELD_LAYOUTS[idx]


def is_tile_solid(session_id: int, col: int, row: int) -> bool:
    """Check if a tile contains an impassable obstacle (e.g. wall, pillar, cliff)."""
    layout = get_battlefield_layout(session_id)
    for feat in layout.get("features", []):
        if feat.get("col") == col and feat.get("row") == row and feat.get("blocks_movement"):
            return True
    return False


def is_tile_difficult(session, col: int, row: int) -> bool:
    """
    Check if a tile is difficult terrain.
    Combines layout natural hazards (bog, brambles) and active spells (Grease).
    """
    layout = get_battlefield_layout(session.id if hasattr(session, 'id') else 0)
    for feat in layout.get("features", []):
        if feat.get("col") == col and feat.get("row") == row and feat.get("difficult_terrain"):
            return True

    # Check active environmental effects on session
    if hasattr(session, 'environmental_effects'):
        tile_x = col * 5
        tile_y = row * 5
        active_effects = session.environmental_effects.filter(is_active=True)
        for eff in active_effects:
            if eff.effect_type == 'terrain':
                # If effect has a centered area (e.g. Grease spell)
                if eff.cover_area_x is not None and eff.cover_area_y is not None:
                    rad = eff.cover_area_radius if eff.cover_area_radius is not None else 5
                    if max(abs(tile_x - eff.cover_area_x), abs(tile_y - eff.cover_area_y)) <= rad:
                        return True
                else:
                    # Global terrain effect on the encounter
                    return True
    return False


def calculate_tile_path(
    session,
    participant,
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int
) -> tuple[int, list[tuple[int, int]]]:
    """
    Compute shortest movement cost and path from start to target on the tactical 5e grid.
    
    5e Rules:
    - Normal terrain: 5 ft per square.
    - Difficult terrain: 10 ft per square (+5 ft extra per square).
    - Solid obstacles: Cannot be traversed.
    - Enemy occupied squares: Cannot be moved through (5e hostile space block).
    - Corner cutting: Cannot cut diagonally between two adjacent solid walls.
    
    Returns:
        (total_cost_ft, path_of_coords_list)
        If unreachable, returns (float('inf'), [])
    """
    session_id = session.id if hasattr(session, 'id') else 0
    start_col = max(0, min(COLS - 1, round(start_x / 5.0)))
    start_row = max(0, min(ROWS - 1, round(start_y / 5.0)))
    target_col = max(0, min(COLS - 1, round(target_x / 5.0)))
    target_row = max(0, min(ROWS - 1, round(target_y / 5.0)))

    mover_tiles = 1
    if hasattr(participant, 'get_size_dimensions'):
        mover_tiles = participant.get_size_dimensions().get('tiles', 1)

    def is_footprint_clear(c: int, r: int) -> bool:
        """Check if all squares of this creature's footprint fit inside arena and avoid solid obstacles."""
        for ox in range(mover_tiles):
            for oy in range(mover_tiles):
                fc = c + ox
                fr = r + oy
                if fc < 0 or fc >= COLS or fr < 0 or fr >= ROWS:
                    return False
                if is_tile_solid(session_id, fc, fr):
                    return False
        return True

    if start_col == target_col and start_row == target_row:
        return 0, [(start_col * 5, start_row * 5)]

    # If destination footprint is out of bounds or overlaps solid obstacle, cannot move there
    if not is_footprint_clear(target_col, target_row):
        return float('inf'), []

    # Map hostile enemy positions that block pathing
    hostile_cells = set()
    creature_cells = set()
    has_nimbleness = getattr(participant, 'has_halfling_nimbleness', lambda: False)()
    SIZE_RANKS = {'T': 1, 'S': 2, 'M': 3, 'L': 4, 'H': 5, 'G': 6}
    mover_rank = SIZE_RANKS.get(getattr(participant, 'get_size', lambda: 'M')(), 2 if has_nimbleness else 3)

    if hasattr(session, 'participants'):
        opp_type = 'enemy' if participant.participant_type == 'character' else 'character'
        all_living = session.participants.filter(
            is_active=True,
            current_hp__gt=0
        ).exclude(id=participant.id)
        
        for c in all_living:
            c_tiles = c.get_size_dimensions()['tiles'] if hasattr(c, 'get_size_dimensions') else 1
            cc_base = round(c.position_x / 5.0)
            cr_base = round(c.position_y / 5.0)
            for ox in range(c_tiles):
                for oy in range(c_tiles):
                    cell = (cc_base + ox, cr_base + oy)
                    creature_cells.add(cell)
                    if c.participant_type == opp_type:
                        # Halfling Nimbleness: Can move through space of creature larger than yours
                        if has_nimbleness:
                            e_rank = SIZE_RANKS.get(getattr(c, 'get_size', lambda: 'M')(), 3)
                            if e_rank > mover_rank:
                                continue  # Nimble halfling can traverse through!
                        hostile_cells.add(cell)

    # Priority queue for Dijkstra: (cost, col, row, path)
    pq = [(0, start_col, start_row, [(start_col * 5, start_row * 5)])]
    best_costs = {(start_col, start_row): 0}

    # 8-directional movement: orthogonal + diagonal (5e grid)
    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    target_footprint = {(target_col + ox, target_row + oy) for ox in range(mover_tiles) for oy in range(mover_tiles)}

    while pq:
        cost, col, row, path = heapq.heappop(pq)

        if col == target_col and row == target_row:
            return cost, path

        if cost > best_costs.get((col, row), float('inf')):
            continue

        for dc, dr in directions:
            ncol, nrow = col + dc, row + dr

            # All squares of the footprint must remain within bounds and not overlap solid blocks
            if not is_footprint_clear(ncol, nrow):
                continue

            # Corner cutting check for 1x1 creatures between two solid blocks
            if mover_tiles == 1 and dc != 0 and dr != 0:
                if is_tile_solid(session_id, col + dc, row) and is_tile_solid(session_id, col, row + dr):
                    continue

            # Cannot move through hostile creature square (unless destination is allowed)
            candidate_footprint = {(ncol + ox, nrow + oy) for ox in range(mover_tiles) for oy in range(mover_tiles)}
            if (candidate_footprint & hostile_cells) and (candidate_footprint != target_footprint):
                continue

            # Calculate step cost
            # 5e: Difficult terrain (or moving through another creature's space) costs 10 ft per 5ft square
            is_step_difficult = any(
                is_tile_difficult(session, fc, fr) or ((fc, fr) in creature_cells and (fc, fr) not in target_footprint)
                for fc, fr in candidate_footprint
            )
            step_cost = 10 if is_step_difficult else 5

            new_cost = cost + step_cost
            if new_cost < best_costs.get((ncol, nrow), float('inf')):
                best_costs[(ncol, nrow)] = new_cost
                new_path = path + [(ncol * 5, nrow * 5)]
                heapq.heappush(pq, (new_cost, ncol, nrow, new_path))

    return float('inf'), []


def get_participant_cover(session_id: int, pos_x: int, pos_y: int, altitude: int = 0, size_tiles: int = 1) -> dict[str, Any] | None:
    """
    Check if a unit is taking cover behind low obstacles (half cover, +2 AC)
    on the active battlefield layout.
    
    5e Rules:
    - Low barricades, crates, sarcophagi, rubble provide half cover (+2 AC, +2 DEX saves).
    - Solid impassable obstacles (pillars, cliffs, pylons) provide Total Cover (blocking line of sight)
      rather than an ambient +5 AC aura to creatures standing nearby.
    """
    layout = get_battlefield_layout(session_id)
    features = layout.get("features", [])

    p_col = round((pos_x or 0) / 5.0)
    p_row = round((pos_y or 0) / 5.0)

    # All tiles in creature's footprint
    footprint = [
        (p_col + ox, p_row + oy)
        for ox in range(max(1, size_tiles))
        for oy in range(max(1, size_tiles))
    ]

    best_cover = None

    for feat in features:
        feat_cover = feat.get("cover")
        # Solid impassable obstacles do NOT grant passive AC aura to adjacent creatures
        if not feat_cover or feat_cover == "none" or feat.get("blocks_movement"):
            continue

        if feat_cover != "half":
            continue

        f_col = feat.get("col", 0)
        f_row = feat.get("row", 0)

        dist_tiles = min(max(abs(fc - f_col), abs(fr - f_row)) for fc, fr in footprint)
        if dist_tiles <= 1:
            if altitude > 5:
                continue

            prop_name = feat.get("name", "Low Cover")
            best_cover = {
                "type": "half",
                "bonus": 2,
                "source": prop_name,
                "col": f_col,
                "row": f_row,
            }
            break

    return best_cover


def get_line_tiles(start_col: int, start_row: int, target_col: int, target_row: int) -> list[tuple[int, int]]:
    """Returns intermediate (col, row) tiles along the raycast strictly between start and target."""
    tiles = []
    dx = abs(target_col - start_col)
    dy = abs(target_row - start_row)
    x = start_col
    y = start_row
    n = 1 + dx + dy
    x_inc = 1 if target_col > start_col else -1
    y_inc = 1 if target_row > start_row else -1
    error = dx - dy
    dx *= 2
    dy *= 2

    for _ in range(n):
        if (x, y) != (start_col, start_row) and (x, y) != (target_col, target_row):
            tiles.append((x, y))

        if error > 0:
            x += x_inc
            error -= dy
        elif error < 0:
            y += y_inc
            error += dx
        else:
            x += x_inc
            y += y_inc
            error += dx - dy

    return tiles


def check_line_of_sight(session_id: int, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
    """
    Check if there is an unblocked line of sight between two coordinates on the battlefield.
    Uses Bresenham raycast across the 5ft grid tiles.
    Returns True if clear, False if an impassable solid obstacle blocks the path.
    """
    start_col = round((from_x or 0) / 5.0)
    start_row = round((from_y or 0) / 5.0)
    target_col = round((to_x or 0) / 5.0)
    target_row = round((to_y or 0) / 5.0)

    # Adjacent or same tile always has direct line of sight
    if max(abs(start_col - target_col), abs(start_row - target_row)) <= 1:
        return True

    inter_tiles = get_line_tiles(start_col, start_row, target_col, target_row)
    for ix, iy in inter_tiles:
        if is_tile_solid(session_id, ix, iy):
            return False

    return True


def get_attack_cover(
    session_id: int,
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    is_melee: bool = False,
    target_size_tiles: int = 1,
) -> dict[str, Any]:
    """
    Determines directional cover between an attacker and a target.
    5e Rules:
    - Melee attacks within reach (adjacent) suffer NO cover from terrain props.
    - Ranged attacks & targeted spells suffer Total Cover (cannot be targeted)
      if an impassable solid obstacle (pillar, pylon, cliff, tree) blocks line of sight.
    - Ranged attacks & targeted spells suffer Half Cover (+2 AC) if a low obstacle
      (barricade, crate, boulder) intervenes along the trajectory.
    """
    if is_melee:
        return {"has_total_cover": False, "cover_bonus": 0, "cover_type": "none", "source": None}

    start_col = max(0, min(COLS - 1, round((from_x or 0) / 5.0)))
    start_row = max(0, min(ROWS - 1, round((from_y or 0) / 5.0)))
    t_base_col = max(0, min(COLS - 1, round((to_x or 0) / 5.0)))
    t_base_row = max(0, min(ROWS - 1, round((to_y or 0) / 5.0)))

    # If adjacent, no intervening cover for ranged attacks either
    if max(abs(start_col - t_base_col), abs(start_row - t_base_row)) <= 1 and target_size_tiles <= 1:
        return {"has_total_cover": False, "cover_bonus": 0, "cover_type": "none", "source": None}

    layout = get_battlefield_layout(session_id)
    features = layout.get("features", [])

    target_tiles = [
        (t_base_col + ox, t_base_row + oy)
        for ox in range(max(1, target_size_tiles))
        for oy in range(max(1, target_size_tiles))
    ]

    blocked_by_solid: list[str] = []
    intervening_half_covers: list[str] = []
    clear_lines = 0

    for tc, tr in target_tiles:
        if (start_col, start_row) == (tc, tr):
            clear_lines += 1
            continue

        ray_tiles = get_line_tiles(start_col, start_row, tc, tr)
        line_blocked = False

        for rx, ry in ray_tiles:
            for feat in features:
                if feat.get("col") == rx and feat.get("row") == ry:
                    if feat.get("blocks_movement"):
                        line_blocked = True
                        blocked_by_solid.append(feat.get("name", "Solid Obstacle"))
                        break
                    elif feat.get("cover") == "half":
                        intervening_half_covers.append(feat.get("name", "Low Obstacle"))
            if line_blocked:
                break

        if not line_blocked:
            clear_lines += 1

    # If ALL lines of sight to target footprint are blocked by solid obstacles
    if clear_lines == 0:
        source = blocked_by_solid[0] if blocked_by_solid else "Solid Obstacle"
        return {
            "has_total_cover": True,
            "cover_bonus": 0,
            "cover_type": "total",
            "source": source,
        }

    # If any intervening low obstacle was crossed, or partially obstructed multi-tile target
    if intervening_half_covers or clear_lines < len(target_tiles):
        source = intervening_half_covers[0] if intervening_half_covers else (blocked_by_solid[0] if blocked_by_solid else "Terrain Cover")
        return {
            "has_total_cover": False,
            "cover_bonus": 2,
            "cover_type": "half",
            "source": source,
        }

    return {
        "has_total_cover": False,
        "cover_bonus": 0,
        "cover_type": "none",
        "source": None,
    }

