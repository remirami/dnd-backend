# Testing Combat Logging System

This guide shows you how to test the enhanced combat logging system with mock data.

## Quick Start

### Step 1: Generate Test Data

Run the management command to create a test combat session with actions:

```bash
python manage.py test_combat_logging
```

This will:
- Create a character and enemy
- Create a combat session
- Simulate combat actions (attacks, spells)
- End the combat and generate a log
- Display the session ID and log ID

### Step 2: Test the Endpoints

Run the automated test script:

```bash
python test_combat_logging.py
```

Or test manually using curl or a REST client:

```bash
# Get statistics
curl http://127.0.0.1:8000/api/combat/sessions/{session_id}/stats/

# Get full report
curl http://127.0.0.1:8000/api/combat/sessions/{session_id}/report/

# Export as JSON
curl http://127.0.0.1:8000/api/combat/sessions/{session_id}/export/?format=json

# Export as CSV
curl http://127.0.0.1:8000/api/combat/sessions/{session_id}/export/?format=csv

# Get log analytics
curl http://127.0.0.1:8000/api/combat/logs/{log_id}/analytics/

# Get character stats
curl http://127.0.0.1:8000/api/characters/{character_id}/combat_stats/
```

## Manual Testing with Django Shell

You can also test interactively:

```python
python manage.py shell
```

```python
from combat.models import CombatSession, CombatLog

# Get a combat session
session = CombatSession.objects.filter(status='ended').first()

# Generate/update log
log = session.generate_log()

# View statistics
print(f"Rounds: {log.total_rounds}")
print(f"Turns: {log.total_turns}")
print(f"Damage Dealt: {log.total_damage_dealt}")
print(f"Damage Received: {log.total_damage_received}")

# Get report
report = session.get_combat_report()
print(f"Encounter: {report['encounter']['name']}")
print(f"Duration: {report['summary']['duration_formatted']}")
```

## Testing with Real Combat

1. **Create a combat session** via API or admin
2. **Add participants** (characters and enemies)
3. **Start combat**
4. **Perform actions** (attacks, spells, etc.)
5. **End combat** - log is automatically generated
6. **Test logging endpoints** using the session ID

## Example Workflow

```bash
# 1. Create test data
python manage.py test_combat_logging

# Output shows:
# Session ID: 9
# Log ID: 1

# 2. Test statistics
curl http://127.0.0.1:8000/api/combat/sessions/9/stats/

# 3. Test report
curl http://127.0.0.1:8000/api/combat/sessions/9/report/

# 4. Test analytics
curl http://127.0.0.1:8000/api/combat/logs/1/analytics/

# 5. Run automated tests
python test_combat_logging.py
```

## What Gets Tracked

The logging system automatically tracks:
- All combat actions (attacks, spells, moves, etc.)
- Damage dealt and received
- Hit/miss ratios
- Critical hits
- Spells cast
- Participant status changes
- Combat duration
- Victors and casualties

## Tips

- **Multiple Sessions**: Run `test_combat_logging` multiple times to create more test data
- **Character Stats**: Character lifetime stats aggregate across all sessions
- **Real-time**: Logs are generated when combat ends, but you can call `generate_log()` anytime
- **Export**: CSV exports are downloadable files, JSON is returned as API response

## Troubleshooting

**No sessions found:**
- Run `python manage.py test_combat_logging` first
- Check that sessions have `status='ended'`

**No logs found:**
- Logs are created when combat ends
- Call `session.generate_log()` to create/update manually

**Statistics seem wrong:**
- Call `log.calculate_statistics()` to recalculate
- Check that combat actions exist

