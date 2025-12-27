# Testing the Roguelike Gauntlet Campaign System

## Quick Start

### 1. Start the Server

```bash
python manage.py runserver
```

### 2. Ensure You Have Test Data

Make sure you have:
- At least 2 characters with stats
- At least 3 encounters with enemies

If you don't have test data:

```bash
# Create test characters
python manage.py create_test_characters

# Create test encounters
python manage.py create_test_encounters
```

### 3. Run the Test Script

```bash
python test_campaign_gauntlet.py
```

## What the Test Script Does

The test script demonstrates the complete gauntlet campaign workflow:

1. **Gets existing characters and encounters**
2. **Creates a new campaign**
3. **Adds 2 characters to the campaign**
4. **Adds 3 encounters in sequence**
5. **Starts the campaign**
6. **Runs through all 3 encounters:**
   - Starts each encounter
   - Simulates completion
   - Tests rest mechanics between encounters
7. **Tests short rest** (spend hit dice to heal)
8. **Tests long rest** (full recovery, limited uses)
9. **Shows final campaign status**

## Expected Output

The script will show:
- Campaign creation
- Character addition
- Encounter progression
- Rest mechanics (short and long)
- Party status updates
- Final campaign completion

## Manual Testing

You can also test manually using the API endpoints:

### Create Campaign
```bash
POST http://127.0.0.1:8000/api/campaigns/
{
  "name": "My Gauntlet",
  "long_rests_available": 2
}
```

### Add Characters
```bash
POST http://127.0.0.1:8000/api/campaigns/{id}/add_character/
{
  "character_id": 1
}
```

### Add Encounters
```bash
POST http://127.0.0.1:8000/api/campaigns/{id}/add_encounter/
{
  "encounter_id": 1
}
```

### Start Campaign
```bash
POST http://127.0.0.1:8000/api/campaigns/{id}/start/
```

### Check Party Status
```bash
GET http://127.0.0.1:8000/api/campaigns/{id}/party_status/
```

### Take Short Rest
```bash
POST http://127.0.0.1:8000/api/campaigns/{id}/short_rest/
{
  "hit_dice_to_spend": {
    "1": 1,
    "2": 1
  }
}
```

### Take Long Rest
```bash
POST http://127.0.0.1:8000/api/campaigns/{id}/long_rest/
{
  "confirm": true
}
```

## Integration with Combat System

To test with real combat:

1. **Start an encounter:**
   ```bash
   POST /api/campaigns/{id}/start_encounter/
   ```

2. **Create a combat session:**
   ```bash
   POST /api/combat/sessions/
   {
     "encounter_id": {encounter_id}
   }
   ```

3. **Run combat** using the combat system endpoints

4. **After combat ends**, complete the encounter:
   ```bash
   POST /api/campaigns/{id}/complete_encounter/
   {
     "combat_session_id": {session_id},
     "rewards": {
       "gold": 100,
       "xp": 200
     }
   }
   ```

## Troubleshooting

**"Need at least 2 characters with stats"**
- Run: `python manage.py create_test_characters`

**"Need at least 3 encounters"**
- Run: `python manage.py create_test_encounters`

**"Could not connect to server"**
- Make sure Django server is running: `python manage.py runserver`

**"Character must have stats to join campaign"**
- Characters need CharacterStats created before joining campaigns

## Next Steps

After testing, you can:
- Create your own campaigns with custom encounters
- Experiment with rest strategies
- Test permadeath mechanics
- Build a frontend interface
- Add procedural encounter generation

