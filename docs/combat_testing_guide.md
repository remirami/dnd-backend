# Combat System Testing Guide - Phase 1

This guide will walk you through testing the combat mechanics system step by step.

## Prerequisites

1. Make sure the server is running:
   ```bash
   python manage.py runserver
   ```

2. Ensure you have:
   - At least one Character with stats
   - At least one Enemy with stats
   - An Encounter with at least one EncounterEnemy

## Step-by-Step Testing

### Step 1: Set Up Test Data

First, let's create the necessary data if you don't have it yet.

#### 1.1 Create a Character (if needed)

```bash
POST http://127.0.0.1:8000/api/characters/
Content-Type: application/json

{
  "name": "Aragorn",
  "level": 5,
  "character_class_id": 5,
  "race_id": 1,
  "background_id": 6,
  "alignment": "LG",
  "experience_points": 6500
}
```

Then create stats for the character:

```bash
POST http://127.0.0.1:8000/api/character-stats/
Content-Type: application/json

{
  "character": 1,
  "strength": 18,
  "dexterity": 14,
  "constitution": 16,
  "intelligence": 10,
  "wisdom": 12,
  "charisma": 10,
  "hit_points": 45,
  "max_hit_points": 45,
  "armor_class": 18,
  "speed": 30
}
```

#### 1.2 Create an Encounter (if needed)

```bash
POST http://127.0.0.1:8000/api/encounters/
Content-Type: application/json

{
  "name": "Goblin Ambush",
  "description": "A group of goblins ambushes the party",
  "location": "Forest Road"
}
```

#### 1.3 Add Enemies to Encounter (if needed)

First, get an enemy ID from the bestiary, then:

```bash
POST http://127.0.0.1:8000/api/encounter-enemies/
Content-Type: application/json

{
  "encounter": 1,
  "enemy": 1,
  "name": "Goblin 1",
  "current_hp": 7,
  "initiative": 0
}
```

### Step 2: Create a Combat Session

```bash
POST http://127.0.0.1:8000/api/combat/sessions/
Content-Type: application/json

{
  "encounter_id": 1,
  "status": "preparing"
}
```

**Expected Response:**
```json
{
  "id": 1,
  "encounter": {...},
  "status": "preparing",
  "current_round": 0,
  ...
}
```

**Save the `id` from the response - you'll need it for subsequent calls!**

### Step 3: Add Participants to Combat

#### 3.1 Add a Character

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/add_participant/
Content-Type: application/json

{
  "participant_type": "character",
  "character_id": 1
}
```

**Expected Response:**
```json
{
  "message": "Aragorn added to combat",
  "participant": {
    "id": 1,
    "name": "Aragorn",
    "current_hp": 45,
    "max_hp": 45,
    "armor_class": 18,
    ...
  }
}
```

#### 3.2 Add an Enemy

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/add_participant/
Content-Type: application/json

{
  "participant_type": "enemy",
  "encounter_enemy_id": 1
}
```

### Step 4: Roll Initiative

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/roll_initiative/
```

**Expected Response:**
```json
{
  "message": "Initiative rolled for all participants",
  "results": [
    {
      "participant": "Aragorn",
      "roll": 15,
      "dex_modifier": 2,
      "initiative": 17
    },
    {
      "participant": "Goblin 1",
      "roll": 12,
      "dex_modifier": 2,
      "initiative": 14
    }
  ],
  "session": {...}
}
```

### Step 5: Start Combat

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/start/
```

**Expected Response:**
```json
{
  "message": "Combat started!",
  "session": {
    "status": "active",
    "current_round": 1,
    "current_turn_index": 0,
    ...
  }
}
```

### Step 6: Check Current Turn

```bash
GET http://127.0.0.1:8000/api/combat/sessions/1/
```

Look at the `current_participant` field to see whose turn it is.

### Step 7: Make an Attack

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/attack/
Content-Type: application/json

{
  "attacker_id": 1,
  "target_id": 2,
  "attack_name": "Longsword",
  "advantage": false,
  "disadvantage": false,
  "other_modifiers": 0
}
```

**Expected Response:**
```json
{
  "message": "Aragorn attacks Goblin 1",
  "attack_roll": 18,
  "attack_total": 22,
  "target_ac": 15,
  "hit": true,
  "critical": false,
  "damage": 8,
  "target_hp": -1,
  "breakdown": {
    "roll": "d20: 18",
    "attack": "Roll: 18 + Ability: +4 + Proficiency: +3 + Other: +0 = Total: 25",
    "damage": "Rolling 1d4 | 3 = 3"
  },
  "action": {...}
}
```

### Step 8: Advance to Next Turn

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/next_turn/
```

**Expected Response:**
```json
{
  "message": "Round 1, Goblin 1's turn",
  "session": {
    "current_round": 1,
    "current_turn_index": 1,
    ...
  }
}
```

### Step 9: Apply Damage Directly (Alternative)

You can also apply damage directly to a participant:

```bash
POST http://127.0.0.1:8000/api/combat/participants/1/damage/
Content-Type: application/json

{
  "amount": 10
}
```

### Step 10: Heal a Participant

```bash
POST http://127.0.0.1:8000/api/combat/participants/1/heal/
Content-Type: application/json

{
  "amount": 5
}
```

### Step 11: View Combat Log

```bash
GET http://127.0.0.1:8000/api/combat/actions/?combat_session=1
```

### Step 12: End Combat

```bash
POST http://127.0.0.1:8000/api/combat/sessions/1/end/
```

## Using cURL (Command Line)

If you prefer command line, here are the cURL equivalents:

```bash
# Create combat session
curl -X POST http://127.0.0.1:8000/api/combat/sessions/ \
  -H "Content-Type: application/json" \
  -d '{"encounter_id": 1, "status": "preparing"}'

# Add character
curl -X POST http://127.0.0.1:8000/api/combat/sessions/1/add_participant/ \
  -H "Content-Type: application/json" \
  -d '{"participant_type": "character", "character_id": 1}'

# Roll initiative
curl -X POST http://127.0.0.1:8000/api/combat/sessions/1/roll_initiative/

# Start combat
curl -X POST http://127.0.0.1:8000/api/combat/sessions/1/start/

# Make attack
curl -X POST http://127.0.0.1:8000/api/combat/sessions/1/attack/ \
  -H "Content-Type: application/json" \
  -d '{"attacker_id": 1, "target_id": 2}'

# Next turn
curl -X POST http://127.0.0.1:8000/api/combat/sessions/1/next_turn/
```

## Using Django Admin

You can also test via Django Admin:

1. Go to `http://127.0.0.1:8000/admin/`
2. Navigate to **Combat** section
3. Create a **Combat Session**
4. Add **Combat Participants**
5. View **Combat Actions** to see the log

## Common Issues

### "Cannot start combat without participants"
- Make sure you've added at least one participant before starting

### "It is not X's turn"
- Make sure you're making the attack with the current participant
- Check the `current_participant` field in the session

### "Character must have stats"
- Make sure your character has CharacterStats created

### "Enemy must be from the same encounter"
- Make sure the EncounterEnemy belongs to the same Encounter as the CombatSession

## Testing Checklist

- [ ] Create combat session
- [ ] Add character participant
- [ ] Add enemy participant
- [ ] Roll initiative
- [ ] Start combat
- [ ] Make an attack
- [ ] Check hit/miss calculation
- [ ] Check damage application
- [ ] Advance to next turn
- [ ] View combat log
- [ ] Apply direct damage
- [ ] Heal participant
- [ ] End combat

## Next Steps

Once Phase 1 is working, you can test:
- Multiple participants
- Multiple rounds
- Critical hits (natural 20)
- Advantage/disadvantage (Phase 2)
- Spell casting (Phase 2)
- Saving throws (Phase 2)

