# Combat System Phase 3 - Advanced Features

Phase 3 adds death saves automation, concentration checks, opportunity attacks, reactions, and legendary actions to the combat system.

## New Features

### 1. Death Saving Throws

Automated death saving throws for unconscious characters.

**Endpoint:** `POST /api/combat/sessions/{id}/death_save/`

**Request Body:**
```json
{
  "participant_id": 1,
  "roll": 15  // Optional: provide roll or auto-roll
}
```

**Response:**
```json
{
  "message": "Death save: 15 (Success)",
  "success": true,
  "is_stable": false,
  "is_dead": false,
  "death_save_successes": 1,
  "death_save_failures": 0,
  "current_hp": 0,
  "action": {...}
}
```

**Rules:**
- Natural 20: Instant success (2 successes) and regain 1 HP
- Natural 1: Two failures
- 10+: Success (1 success)
- 9-: Failure (1 failure)
- 3 successes: Character stabilizes
- 3 failures: Character dies

### 2. Concentration Checks

Automatic concentration checks when taking damage while concentrating on a spell.

**Endpoint:** `POST /api/combat/sessions/{id}/check_concentration/`

**Request Body:**
```json
{
  "participant_id": 1,
  "damage_amount": 15
}
```

**Response:**
```json
{
  "message": "Concentration maintained (DC 10, rolled 14)",
  "concentration_broken": false,
  "save_roll": 14,
  "save_dc": 10,
  "is_concentrating": true,
  "concentration_spell": "Haste",
  "action": {...}
}
```

**Rules:**
- DC = 10 or half damage (rounded down), whichever is higher
- Roll CON saving throw
- If failed, concentration is broken and spell ends
- Automatically checked when taking damage via `take_damage()` method

**Concentration Management:**
- `POST /api/combat/participants/{id}/start_concentration/` - Start concentrating
- `POST /api/combat/participants/{id}/end_concentration/` - End concentration

### 3. Opportunity Attacks

Make opportunity attacks when enemies leave melee range.

**Endpoint:** `POST /api/combat/sessions/{id}/opportunity_attack/`

**Request Body:**
```json
{
  "attacker_id": 1,
  "target_id": 2,
  "attack_name": "Opportunity Attack",
  "advantage": false,
  "disadvantage": false
}
```

**Response:**
```json
{
  "message": "Test Rogue makes an opportunity attack on Goblin Scout",
  "attack_roll": 18,
  "attack_total": 20,
  "target_ac": 12,
  "hit": true,
  "critical": false,
  "damage": 4,
  "target_hp": 8,
  "breakdown": {...},
  "action": {...}
}
```

**Rules:**
- Uses attacker's reaction
- Standard melee attack
- Can be made when enemy leaves reach
- Reaction is marked as used

### 4. Legendary Actions

Powerful enemies can take legendary actions at the end of other creatures' turns.

**Endpoint:** `POST /api/combat/sessions/{id}/legendary_action/`

**Request Body:**
```json
{
  "participant_id": 1,
  "action_cost": 1,
  "action_name": "Wing Attack",
  "action_description": "The dragon beats its wings..."
}
```

**Response:**
```json
{
  "message": "Used 1 legendary action(s). 2 remaining.",
  "action_name": "Wing Attack",
  "action_cost": 1,
  "legendary_actions_remaining": 2,
  "action": {...}
}
```

**Rules:**
- Legendary actions reset at the start of each round
- Can be used at the end of any other creature's turn
- Each action has a cost (typically 1-3)
- Total legendary actions per round is limited by `legendary_actions_max`

**Setting Up Legendary Actions:**
When creating a participant, set:
```python
participant.legendary_actions_max = 3
participant.legendary_actions_remaining = 3
```

### 5. Automatic Concentration Checks

When a participant takes damage while concentrating, concentration is automatically checked:

```python
new_hp, concentration_broken = participant.take_damage(15)
```

The `damage` endpoint now returns concentration status:
```json
{
  "message": "Test Wizard took 15 damage",
  "current_hp": 30,
  "concentration_broken": true,
  "concentration_message": "Lost concentration on Haste",
  "participant": {...}
}
```

### 6. Spell Concentration

When casting a spell, you can mark it as requiring concentration:

```json
{
  "caster_id": 1,
  "target_id": 2,
  "spell_name": "Haste",
  "spell_level": 3,
  "requires_concentration": true
}
```

The caster will automatically start concentrating on the spell.

## Example Workflow

### Complete Combat with Phase 3 Features

```bash
# 1. Create combat session
POST /api/combat/sessions/ {"encounter_id": 1}

# 2. Add participants (including legendary enemy)
POST /api/combat/sessions/1/add_participant/ {
  "participant_type": "enemy",
  "encounter_enemy_id": 1,
  "legendary_actions_max": 3
}

# 3. Roll initiative and start
POST /api/combat/sessions/1/roll_initiative/
POST /api/combat/sessions/1/start/

# 4. Cast concentration spell
POST /api/combat/sessions/1/cast_spell/ {
  "caster_id": 1,
  "target_id": 1,
  "spell_name": "Haste",
  "spell_level": 3,
  "requires_concentration": true
}

# 5. Take damage (triggers concentration check)
POST /api/combat/participants/1/damage/ {"amount": 15}
# Response includes concentration_broken status

# 6. Make opportunity attack
POST /api/combat/sessions/1/opportunity_attack/ {
  "attacker_id": 2,
  "target_id": 1
}

# 7. Use legendary action (at end of turn)
POST /api/combat/sessions/1/legendary_action/ {
  "participant_id": 3,
  "action_cost": 1,
  "action_name": "Tail Attack"
}

# 8. Character goes unconscious - make death save
POST /api/combat/participants/1/damage/ {"amount": 50}
POST /api/combat/sessions/1/death_save/ {"participant_id": 1}

# 9. End combat
POST /api/combat/sessions/1/end/
```

## Model Updates

### CombatParticipant
- `is_concentrating` - Boolean, is currently concentrating
- `concentration_spell` - String, name of spell being concentrated on
- `legendary_actions_max` - Integer, max legendary actions per round
- `legendary_actions_remaining` - Integer, remaining legendary actions

### CombatAction
- `is_opportunity_attack` - Boolean, is this an opportunity attack
- `is_reaction` - Boolean, is this a reaction
- `is_legendary_action` - Boolean, is this a legendary action
- `legendary_action_cost` - Integer, cost in legendary action points

## API Endpoints Summary

### Phase 3 (Advanced Features)
- `POST /api/combat/sessions/{id}/death_save/` - Make death saving throw
- `POST /api/combat/sessions/{id}/check_concentration/` - Check concentration
- `POST /api/combat/sessions/{id}/opportunity_attack/` - Make opportunity attack
- `POST /api/combat/sessions/{id}/legendary_action/` - Use legendary action
- `POST /api/combat/participants/{id}/start_concentration/` - Start concentrating
- `POST /api/combat/participants/{id}/end_concentration/` - End concentration

## Testing

Run the tests:
```bash
python manage.py test combat
```

All 18 tests should pass, including:
- Death save tests
- Concentration check tests
- Opportunity attack tests
- Legendary action tests

## Integration Notes

### Automatic Features
- Concentration checks happen automatically when taking damage
- Legendary actions reset at the start of each round
- Death saves track successes/failures automatically
- Reactions are marked as used after opportunity attacks

### Best Practices
1. Set `legendary_actions_max` when creating powerful enemies
2. Mark spells as `requires_concentration: true` when casting
3. Check `concentration_broken` in damage responses
4. Monitor `death_save_successes` and `death_save_failures` for unconscious characters
5. Use legendary actions at the end of other creatures' turns

## Next Steps

Potential future enhancements:
- Lair actions (similar to legendary actions)
- Environmental effects
- Grappling mechanics
- Mounted combat
- Underwater combat
- Cover mechanics
- Flanking rules

