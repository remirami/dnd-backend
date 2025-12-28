# Practice Mode / Combat Simulation - Implementation Complete ✅

## Overview

A practice/simulation mode for quick combat testing where users can:
- Create characters/party
- Equip them with desired items
- Fight against desired monsters
- Run combat simulations without needing to create encounters first

---

## ✅ What Was Implemented

### 1. Practice Mode Combat Sessions

**CombatSession Model Updates:**
- `encounter` field is now **optional** (can be null)
- `is_practice` field added to mark practice sessions
- Practice sessions don't require an Encounter

### 2. Direct Enemy Addition

**Enhanced `add_participant` Endpoint:**
- Supports adding enemies directly by `enemy_id` (practice mode)
- Still supports `encounter_enemy_id` (campaign mode)
- Can customize enemy name and HP when adding

### 3. Quick Practice Session Creation

**New `practice_mode` Endpoint:**
- Creates a complete combat session in one call
- Adds multiple characters and enemies at once
- Returns next steps for running combat

---

## 🎯 API Endpoints

### Create Practice Session (Quick Setup)

**`POST /api/combat/sessions/practice_mode/`**

Create a complete practice combat session with characters and enemies.

**Request:**
```json
{
  "name": "Practice Combat",
  "character_ids": [1, 2, 3],
  "enemies": [
    {"enemy_id": 1, "name": "Goblin 1", "hp": 7},
    {"enemy_id": 1, "name": "Goblin 2", "hp": 7},
    {"enemy_id": 2, "name": "Orc Warrior", "hp": 15}
  ]
}
```

**Response:**
```json
{
  "message": "Practice combat session created: Practice Combat",
  "session": {
    "id": 1,
    "is_practice": true,
    "encounter": null,
    "status": "preparing",
    ...
  },
  "characters_added": [
    {"id": 1, "name": "Fighter", "participant_id": 1},
    {"id": 2, "name": "Wizard", "participant_id": 2}
  ],
  "enemies_added": [
    {"id": 1, "name": "Goblin 1", "participant_id": 3},
    {"id": 1, "name": "Goblin 2", "participant_id": 4}
  ],
  "next_steps": [
    "1. Roll initiative: POST /api/combat/sessions/1/roll_initiative/",
    "2. Start combat: POST /api/combat/sessions/1/start/",
    "3. Make attacks: POST /api/combat/sessions/1/attack/"
  ]
}
```

### Create Practice Session Manually

**`POST /api/combat/sessions/`**

Create a practice session without an encounter.

**Request:**
```json
{
  "is_practice": true,
  "notes": "Practice session"
}
```

**Response:**
```json
{
  "id": 1,
  "is_practice": true,
  "encounter": null,
  "status": "preparing",
  ...
}
```

### Add Enemy Directly (Practice Mode)

**`POST /api/combat/sessions/{id}/add_participant/`**

Add an enemy directly by enemy ID (for practice sessions).

**Request:**
```json
{
  "participant_type": "enemy",
  "enemy_id": 1,
  "enemy_name": "Goblin Warrior",
  "enemy_hp": 10
}
```

**Response:**
```json
{
  "message": "Goblin Warrior added to combat",
  "participant": {
    "id": 1,
    "participant_type": "enemy",
    "current_hp": 10,
    "max_hp": 7,
    ...
  }
}
```

---

## 📋 Complete Workflow Example

### Step 1: Create Characters and Equip Items

```bash
# Create character
POST /api/characters/
{
  "name": "Test Fighter",
  "character_class_id": 1,
  "race_id": 1,
  "level": 5
}

# Equip items
POST /api/characters/1/inventory/
{
  "item_id": 10,  // Longsword
  "quantity": 1,
  "is_equipped": true,
  "equipment_slot": "main_hand"
}

POST /api/characters/1/inventory/
{
  "item_id": 5,  // Chain Mail
  "quantity": 1,
  "is_equipped": true,
  "equipment_slot": "armor"
}
```

### Step 2: Create Practice Combat Session

```bash
# Quick method: Create everything at once
POST /api/combat/sessions/practice_mode/
{
  "name": "Fighter vs Goblins",
  "character_ids": [1],
  "enemies": [
    {"enemy_id": 1, "name": "Goblin 1", "hp": 7},
    {"enemy_id": 1, "name": "Goblin 2", "hp": 7}
  ]
}
```

**OR manually:**

```bash
# Create practice session
POST /api/combat/sessions/
{
  "is_practice": true
}

# Add character
POST /api/combat/sessions/1/add_participant/
{
  "participant_type": "character",
  "character_id": 1
}

# Add enemies
POST /api/combat/sessions/1/add_participant/
{
  "participant_type": "enemy",
  "enemy_id": 1,
  "enemy_name": "Goblin 1"
}

POST /api/combat/sessions/1/add_participant/
{
  "participant_type": "enemy",
  "enemy_id": 1,
  "enemy_name": "Goblin 2"
}
```

### Step 3: Run Combat

```bash
# Roll initiative
POST /api/combat/sessions/1/roll_initiative/

# Start combat
POST /api/combat/sessions/1/start/

# Make attacks
POST /api/combat/sessions/1/attack/
{
  "attacker_id": 1,
  "target_id": 2
}

# Advance turns
POST /api/combat/sessions/1/next_turn/
```

---

## 🎮 Use Cases

### 1. Character Testing
Test how a character performs against different enemies:
- "Can my level 5 Fighter beat 3 Goblins?"
- "How does my Wizard fare against an Orc?"

### 2. Equipment Testing
Test different equipment combinations:
- Equip different weapons/armor
- Test magic items
- Compare builds

### 3. Party Composition Testing
Test party synergy:
- "Can a Fighter + Cleric duo beat a Dragon?"
- Test different party combinations

### 4. Strategy Testing
Test combat strategies:
- Test positioning
- Test spell combinations
- Test environmental effects

---

## ✅ Features

- ✅ **No Encounter Required** - Practice sessions don't need encounters
- ✅ **Direct Enemy Addition** - Add enemies by ID, not just EncounterEnemy
- ✅ **Quick Setup** - Create complete sessions in one call
- ✅ **Custom Enemy Names** - Name enemies as you like
- ✅ **Custom HP** - Set custom HP for enemies
- ✅ **Full Combat System** - All combat features work in practice mode
- ✅ **Equipment Support** - Characters use their equipped items
- ✅ **Environmental Effects** - Can add terrain, cover, lighting, etc.

---

## 📁 Files Modified

**Modified:**
- `combat/models.py` - Made encounter optional, added is_practice field
- `combat/views.py` - Added practice_mode endpoint, enhanced add_participant
- `combat/serializers.py` - Made encounter optional in serializer
- `combat/migrations/0006_add_practice_mode.py` - Database migration

---

## 🎉 Status: Complete!

The practice/simulation mode is **fully functional**! Users can now:
- ✅ Create characters and equip them
- ✅ Create practice combat sessions quickly
- ✅ Add any monsters they want
- ✅ Run full combat simulations
- ✅ Test strategies and builds

**Campaign/Gauntlet features are also complete** - users can run sequential encounters with permadeath and resource management.

Both modes are ready to use! 🎲⚔️

