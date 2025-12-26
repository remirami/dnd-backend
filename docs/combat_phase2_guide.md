# Combat System Phase 2 - Advanced Features

Phase 2 adds spell casting, saving throws, and conditions management to the combat system.

## New Features

### 1. Spell Casting

Cast spells during combat with saving throws and damage calculation.

**Endpoint:** `POST /api/combat/sessions/{id}/cast_spell/`

**Request Body:**
```json
{
  "caster_id": 1,
  "target_id": 2,
  "spell_name": "Fireball",
  "spell_level": 3,
  "damage_string": "8d6",
  "damage_type": 2,  // DamageType ID (Fire)
  "save_type": "DEX",
  "save_dc": 15
}
```

**Response:**
```json
{
  "message": "Test Wizard casts Fireball",
  "spell_name": "Fireball",
  "spell_level": 3,
  "target": "Goblin Scout",
  "target_hp": 3,
  "save_type": "DEX",
  "save_dc": 15,
  "save_roll": 12,
  "save_success": false,
  "damage": 24,
  "damage_breakdown": "Rolling 8d6 | 4, 3, 5, 2, 6, 1, 2, 1 = 24 | Save failed: full damage = 24",
  "action": {...}
}
```

**Features:**
- Automatic saving throw calculation
- Half damage on successful save
- Full damage on failed save
- Damage type tracking
- Combat log entry

### 2. Saving Throws

Make saving throws with advantage/disadvantage support.

**Endpoint:** `POST /api/combat/sessions/{id}/saving_throw/`

**Request Body:**
```json
{
  "participant_id": 1,
  "save_type": "DEX",
  "save_dc": 15,
  "advantage": false,
  "disadvantage": false
}
```

**Response:**
```json
{
  "message": "Test Rogue makes a DEX saving throw",
  "save_type": "DEX",
  "roll": 14,
  "save_total": 17,
  "save_dc": 15,
  "save_success": true,
  "breakdown": {
    "roll": "d20: 14",
    "save": "Roll: 14 + Ability: +3 + Total: 17"
  },
  "action": {...}
}
```

**Features:**
- Advantage/disadvantage support
- Automatic ability modifier calculation
- Success/failure determination
- Combat log entry

### 3. Conditions Management

Add and remove conditions from participants.

**Add Condition:** `POST /api/combat/participants/{id}/add_condition/`

**Request Body:**
```json
{
  "condition_id": 1
}
```

**Response:**
```json
{
  "message": "Poisoned added to Test Rogue",
  "participant": {
    "id": 1,
    "conditions": [
      {
        "id": 1,
        "name": "poisoned",
        "description": "..."
      }
    ],
    ...
  }
}
```

**Remove Condition:** `POST /api/combat/participants/{id}/remove_condition/`

**Request Body:**
```json
{
  "condition_id": 1
}
```

**Available Conditions:**
- Blinded
- Charmed
- Deafened
- Frightened
- Grappled
- Incapacitated
- Invisible
- Paralyzed
- Petrified
- Poisoned
- Prone
- Restrained
- Stunned
- Unconscious
- Exhaustion

## Example Workflow

### Complete Combat with Phase 2 Features

```bash
# 1. Create combat session
POST /api/combat/sessions/ {"encounter_id": 1}

# 2. Add participants
POST /api/combat/sessions/1/add_participant/ {"participant_type": "character", "character_id": 1}
POST /api/combat/sessions/1/add_participant/ {"participant_type": "enemy", "encounter_enemy_id": 1}

# 3. Roll initiative
POST /api/combat/sessions/1/roll_initiative/

# 4. Start combat
POST /api/combat/sessions/1/start/

# 5. Cast a spell
POST /api/combat/sessions/1/cast_spell/ {
  "caster_id": 1,
  "target_id": 2,
  "spell_name": "Fireball",
  "spell_level": 3,
  "damage_string": "8d6",
  "save_type": "DEX",
  "save_dc": 15
}

# 6. Make a saving throw
POST /api/combat/sessions/1/saving_throw/ {
  "participant_id": 2,
  "save_type": "DEX",
  "save_dc": 15
}

# 7. Add a condition
POST /api/combat/participants/2/add_condition/ {"condition_id": 10}  // Poisoned

# 8. Make an attack with advantage (due to condition)
POST /api/combat/sessions/1/attack/ {
  "attacker_id": 1,
  "target_id": 2,
  "advantage": true  // Target is poisoned
}

# 9. Remove condition
POST /api/combat/participants/2/remove_condition/ {"condition_id": 10}

# 10. End combat
POST /api/combat/sessions/1/end/
```

## Integration with Existing Systems

### Conditions
- Uses `Condition` model from bestiary app
- Run `python manage.py populate_conditions_environments` to populate conditions

### Damage Types
- Uses `DamageType` model from bestiary app
- Spell damage can specify damage type for resistance calculations

### Character Spells
- Can reference spells from `CharacterSpell` model
- Spell level and details come from character's known spells

## Testing

Run the updated test script:
```bash
python test_combat.py
```

This will test both Phase 1 and Phase 2 features.

## API Endpoints Summary

### Phase 1 (Core Combat)
- `POST /api/combat/sessions/` - Create session
- `POST /api/combat/sessions/{id}/start/` - Start combat
- `POST /api/combat/sessions/{id}/roll_initiative/` - Roll initiative
- `POST /api/combat/sessions/{id}/add_participant/` - Add participant
- `POST /api/combat/sessions/{id}/attack/` - Make attack
- `POST /api/combat/sessions/{id}/next_turn/` - Advance turn
- `POST /api/combat/sessions/{id}/end/` - End combat

### Phase 2 (Advanced Features)
- `POST /api/combat/sessions/{id}/cast_spell/` - Cast spell
- `POST /api/combat/sessions/{id}/saving_throw/` - Make saving throw
- `POST /api/combat/participants/{id}/add_condition/` - Add condition
- `POST /api/combat/participants/{id}/remove_condition/` - Remove condition

## Next Steps (Phase 3)

Potential future enhancements:
- Death saves automation
- Concentration checks
- Opportunity attacks
- Reactions
- Legendary actions
- Lair actions
- Environmental effects

