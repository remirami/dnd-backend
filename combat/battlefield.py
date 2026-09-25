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

    if start_col == target_col and start_row == target_row:
        return 0, [(start_col * 5, start_row * 5)]

    # If destination is solid obstacle, cannot move there
    if is_tile_solid(session_id, target_col, target_row):
        return float('inf'), []

    # Map hostile enemy positions that block pathing
    hostile_cells = set()
    if hasattr(session, 'participants'):
        opp_type = 'enemy' if participant.participant_type == 'character' else 'character'
        enemies = session.participants.filter(
            participant_type=opp_type,
            is_active=True,
            current_hp__gt=0
        )
        for e in enemies:
            ec = round(e.position_x / 5.0)
            er = round(e.position_y / 5.0)
            hostile_cells.add((ec, er))

    # Priority queue for Dijkstra: (cost, col, row, path)
    pq = [(0, start_col, start_row, [(start_col * 5, start_row * 5)])]
    best_costs = {(start_col, start_row): 0}

    # 8-directional movement: orthogonal + diagonal (5e grid)
    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    while pq:
        cost, col, row, path = heapq.heappop(pq)

        if col == target_col and row == target_row:
            return cost, path

        if cost > best_costs.get((col, row), float('inf')):
            continue

        for dc, dr in directions:
            ncol, nrow = col + dc, row + dr

            # Arena bounds check
            if ncol < 0 or ncol >= COLS or nrow < 0 or nrow >= ROWS:
                continue

            # Cannot move through solid obstacle
            if is_tile_solid(session_id, ncol, nrow):
                continue

            # Cannot cut diagonally through two adjacent solid blocks
            if dc != 0 and dr != 0:
                if is_tile_solid(session_id, col + dc, row) and is_tile_solid(session_id, col, row + dr):
                    continue

            # Cannot move through hostile creature square (unless destination is somehow allowed)
            if (ncol, nrow) in hostile_cells and (ncol != target_col or nrow != target_row):
                continue

            # Calculate step cost
            # 5e: Difficult terrain costs 1 extra foot per foot moved (10 ft per 5ft square)
            if is_tile_difficult(session, ncol, nrow):
                step_cost = 10
            else:
                step_cost = 5

            new_cost = cost + step_cost
            if new_cost < best_costs.get((ncol, nrow), float('inf')):
                best_costs[(ncol, nrow)] = new_cost
                new_path = path + [(ncol * 5, nrow * 5)]
                heapq.heappush(pq, (new_cost, ncol, nrow, new_path))

    return float('inf'), []
