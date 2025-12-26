# Enhanced Combat Logging System

The enhanced combat logging system provides comprehensive statistics, analytics, and reporting for combat sessions.

## Features

### 1. Automatic Log Generation

When a combat session ends, a `CombatLog` is automatically created and populated with statistics.

### 2. Statistics Tracking

The system tracks:
- **Combat Duration**: Rounds, turns, and real-time duration
- **Damage Statistics**: Total damage dealt/received, by damage type
- **Action Statistics**: Count of actions by type
- **Spell Statistics**: Spells cast with counts
- **Participant Performance**: Individual stats for each participant
- **Combat Outcomes**: Victors and casualties

### 3. Combat Reports

Get comprehensive reports with:
- Session summary
- Participant statistics
- Turn-by-turn timeline
- Damage breakdowns
- Action summaries

### 4. Export Functionality

Export combat logs in multiple formats:
- **JSON**: Structured data for programmatic access
- **CSV**: Spreadsheet-compatible format

### 5. Analytics

Detailed analytics including:
- Performance metrics (hit rates, crit rates)
- Damage analysis
- Action frequency
- Spell usage
- Participant comparisons

### 6. Character Lifetime Statistics

Track character performance across all combat sessions:
- Total combats participated
- Win rate
- Damage dealt/received
- Favorite weapons/spells
- Combat trends

## API Endpoints

### Combat Session Endpoints

#### Get Statistics
`GET /api/combat/sessions/{id}/stats/`

Returns calculated statistics for the combat session.

**Response:**
```json
{
  "id": 1,
  "combat_session": 1,
  "total_rounds": 5,
  "total_turns": 12,
  "duration_seconds": 1800,
  "total_damage_dealt": 150,
  "total_damage_received": 80,
  "total_healing": 20,
  "actions_by_type": {
    "attack": 8,
    "spell": 2,
    "move": 2
  },
  "damage_by_type": {
    "Slashing": 100,
    "Fire": 50
  },
  "spells_cast": {
    "Fireball": 1,
    "Healing Word": 1
  },
  "participant_stats": {
    "1": {
      "name": "Test Fighter",
      "damage_dealt": 80,
      "damage_received": 30,
      "attacks_made": 5,
      "attacks_hit": 4,
      "attacks_missed": 1,
      "critical_hits": 1
    }
  },
  "victors": [1],
  "casualties": [2]
}
```

#### Get Combat Report
`GET /api/combat/sessions/{id}/report/`

Returns a comprehensive combat report with timeline and detailed statistics.

**Response:**
```json
{
  "session_id": 1,
  "encounter": {
    "name": "Goblin Ambush",
    "description": "...",
    "location": "Forest Path"
  },
  "summary": {
    "status": "Ended",
    "rounds": 5,
    "turns": 12,
    "duration_seconds": 1800,
    "duration_formatted": "30m 0s",
    "started_at": "2025-12-26T12:00:00Z",
    "ended_at": "2025-12-26T12:30:00Z"
  },
  "statistics": {
    "total_damage_dealt": 150,
    "total_damage_received": 80,
    "actions_by_type": {...},
    "damage_by_type": {...}
  },
  "participants": [...],
  "outcomes": {
    "victors": [...],
    "casualties": [...]
  },
  "timeline": [
    {
      "round": 1,
      "turn": 1,
      "timestamp": "2025-12-26T12:00:05Z",
      "actor": "Test Fighter",
      "action_type": "Attack",
      "target": "Goblin",
      "details": {
        "attack_name": "Longsword",
        "hit": true,
        "damage": 8,
        "critical": false
      }
    }
  ]
}
```

#### Export Combat Log
`GET /api/combat/sessions/{id}/export/?format=json`
`GET /api/combat/sessions/{id}/export/?format=csv`

Export combat log in various formats.

**CSV Export:**
- Round, Turn, Timestamp, Actor, Action Type, Target, Hit, Damage, Critical
- One row per action

### Combat Log Endpoints

#### List Logs
`GET /api/combat/logs/`

List all combat logs with filtering:
- `?session={id}` - Filter by session ID
- `?public=true` - Filter public logs

#### Get Log Analytics
`GET /api/combat/logs/{id}/analytics/`

Get detailed analytics for a specific log.

**Response:**
```json
{
  "log_id": 1,
  "session_id": 1,
  "encounter_name": "Goblin Ambush",
  "duration": {
    "seconds": 1800,
    "formatted": "30m 0s",
    "rounds": 5,
    "turns": 12,
    "average_turns_per_round": 2.4
  },
  "damage_analysis": {
    "total_dealt": 150,
    "total_received": 80,
    "net_damage": 70,
    "by_type": {...},
    "average_per_turn": 12.5
  },
  "action_analysis": {
    "total_actions": 12,
    "by_type": {...},
    "most_common_action": "attack"
  },
  "spell_analysis": {
    "total_spells_cast": 2,
    "spells_by_name": {...},
    "most_used_spell": "Fireball"
  },
  "participant_performance": {
    "1": {
      "name": "Test Fighter",
      "damage_dealt": 80,
      "damage_received": 30,
      "attacks_made": 5,
      "hit_rate": 80.0,
      "critical_hit_rate": 20.0,
      "hp_change": -30,
      "status": "alive"
    }
  },
  "outcomes": {
    "victors": 1,
    "casualties": 1,
    "victor_names": ["Test Fighter"],
    "casualty_names": ["Goblin"]
  }
}
```

### Character Endpoints

#### Get Character Combat Statistics
`GET /api/characters/{id}/combat_stats/`

Get lifetime combat statistics for a character.

**Response:**
```json
{
  "character": {
    "id": 1,
    "name": "Test Fighter",
    "level": 5
  },
  "summary": {
    "total_combats": 10,
    "victories": 8,
    "win_rate": 80.0
  },
  "combat_statistics": {
    "total_damage_dealt": 500,
    "total_damage_received": 200,
    "total_attacks": 50,
    "total_hits": 40,
    "hit_rate": 80.0,
    "total_critical_hits": 5,
    "critical_hit_rate": 10.0,
    "total_spells_cast": 10,
    "average_damage_per_combat": 50.0
  },
  "favorites": {
    "weapon": "Longsword",
    "spell": "Fireball"
  },
  "weapon_usage": {
    "Longsword": 30,
    "Dagger": 10
  },
  "spell_usage": {
    "Fireball": 5,
    "Magic Missile": 5
  }
}
```

## Usage Examples

### Get Combat Statistics
```bash
curl http://127.0.0.1:8000/api/combat/sessions/1/stats/
```

### Get Combat Report
```bash
curl http://127.0.0.1:8000/api/combat/sessions/1/report/
```

### Export to CSV
```bash
curl http://127.0.0.1:8000/api/combat/sessions/1/export/?format=csv -o combat_log.csv
```

### Get Log Analytics
```bash
curl http://127.0.0.1:8000/api/combat/logs/1/analytics/
```

### Get Character Stats
```bash
curl http://127.0.0.1:8000/api/characters/1/combat_stats/
```

## Model Details

### CombatLog Model

- **One-to-one** relationship with `CombatSession`
- Automatically created when combat ends
- Statistics calculated via `calculate_statistics()` method
- JSON fields for flexible data storage

### Statistics Calculation

The `calculate_statistics()` method:
1. Processes all combat actions
2. Aggregates damage, actions, and spells
3. Calculates participant performance
4. Determines victors and casualties
5. Stores results in JSON fields

## Integration

The logging system is automatically integrated:
- Logs are created when combat ends
- Statistics are calculated on-demand
- Reports can be generated at any time
- Character stats aggregate across all sessions

## Future Enhancements

Potential additions:
- PDF export with formatted reports
- Real-time log updates via WebSocket
- Combat replay functionality
- Advanced filtering and search
- Performance benchmarking
- Campaign-wide analytics

