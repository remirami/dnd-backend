# Roguelike Gauntlet Campaign System Guide

## Overview

The gauntlet campaign system allows you to run a series of sequential encounters where characters must survive with limited resources and strategic rest management. Characters have permadeath - if they die, they're gone from the campaign.

## Key Features

- **Sequential Encounters**: Fight through a series of encounters
- **Permadeath**: Dead characters are permanently removed
- **Resource Management**: Track HP, hit dice, and spell slots
- **Strategic Rests**: Choose when to short rest or long rest
- **Limited Long Rests**: Only 2 long rests per campaign (default)

## Quick Start

### 1. Create a Campaign

```bash
POST /api/campaigns/
{
  "name": "The Gauntlet of Doom",
  "description": "A challenging series of encounters",
  "long_rests_available": 2
}
```

### 2. Add Characters

```bash
POST /api/campaigns/{id}/add_character/
{
  "character_id": 1
}
```

Characters must have stats to join a campaign. They'll be initialized with:
- Full HP
- All hit dice (equal to character level)
- Empty spell slots (to be configured)

### 3. Add Encounters

```bash
POST /api/campaigns/{id}/add_encounter/
{
  "encounter_id": 1
}
```

Add encounters in the order you want them to appear. They'll be numbered sequentially (1, 2, 3...).

### 4. Start Campaign

```bash
POST /api/campaigns/{id}/start/
```

This will:
- Set campaign status to 'active'
- Initialize all characters
- Set current encounter to #1

### 5. Start an Encounter

```bash
POST /api/campaigns/{id}/start_encounter/
```

This marks the current encounter as 'active'. You can then:
- Create a combat session using the encounter
- Run combat as normal
- Track character HP during combat

### 6. Complete an Encounter

After combat ends:

```bash
POST /api/campaigns/{id}/complete_encounter/
{
  "combat_session_id": 5,
  "rewards": {
    "gold": 100,
    "xp": 200,
    "items": [1, 2]
  }
}
```

This will:
- Mark encounter as completed
- Advance to next encounter
- Check if campaign is complete (all encounters done)

### 7. Between Encounters - Rest Options

#### Short Rest (1 hour)
- Spend hit dice to heal
- Recover some class abilities
- No spell slot recovery
- Unlimited uses

```bash
POST /api/campaigns/{id}/short_rest/
{
  "character_ids": [1, 2],  # Optional: specific characters
  "hit_dice_to_spend": {     # Optional: specific dice counts
    "1": 2,  # Character 1 spends 2 hit dice
    "2": 1   # Character 2 spends 1 hit die
  }
}
```

If you don't specify `character_ids` or `hit_dice_to_spend`, all alive characters will spend 1 hit die each.

#### Long Rest (8 hours)
- Full HP recovery
- All hit dice restored
- All spell slots restored (when implemented)
- Limited uses (default: 2 per campaign)

```bash
POST /api/campaigns/{id}/long_rest/
{
  "confirm": true
}
```

**Warning**: Long rests are limited! Use them strategically.

### 8. Check Status

```bash
# Full campaign status
GET /api/campaigns/{id}/status/

# Party status (HP, resources)
GET /api/campaigns/{id}/party_status/

# Current encounter
GET /api/campaigns/{id}/current_encounter/
```

## Campaign Flow

```
1. Create Campaign
   ↓
2. Add Characters
   ↓
3. Add Encounters (in order)
   ↓
4. Start Campaign
   ↓
5. Start Encounter #1
   ↓
6. Run Combat (using combat system)
   ↓
7. Complete Encounter
   ↓
8. Choose: Continue, Short Rest, or Long Rest
   ↓
9. Repeat from step 5 for next encounter
   ↓
10. Campaign ends when:
    - All encounters completed (Victory!)
    - All characters dead (Failure)
```

## Permadeath

When a character dies in combat:
- `is_alive` is set to `False`
- `died_in_encounter` records which encounter they died in
- Character is removed from active party
- If all characters die, campaign automatically fails

## Resource Management

### Hit Dice
- Characters start with hit dice equal to their level
- Spend during short rests to heal
- Restored fully on long rest
- Tracked per character: `{"d8": 3}` means 3d8 available

### Spell Slots
- Currently stored as JSON: `{"1": 3, "2": 2}` means 3 level-1, 2 level-2 slots
- Restored on long rest (when implemented)
- Class-specific logic needed for full implementation

### HP
- Tracked per character in campaign
- Can be damaged/healed during encounters
- Full recovery on long rest
- Death at 0 HP (with death saves in combat)

## API Endpoints Summary

### Campaign Management
- `GET /api/campaigns/` - List campaigns
- `POST /api/campaigns/` - Create campaign
- `GET /api/campaigns/{id}/` - Get campaign details
- `POST /api/campaigns/{id}/start/` - Start campaign
- `POST /api/campaigns/{id}/end/` - End campaign manually

### Character Management
- `POST /api/campaigns/{id}/add_character/` - Add character
- `POST /api/campaigns/{id}/remove_character/` - Remove character
- `GET /api/campaign-characters/?campaign={id}` - List campaign characters

### Encounter Management
- `POST /api/campaigns/{id}/add_encounter/` - Add encounter
- `GET /api/campaigns/{id}/current_encounter/` - Get current encounter
- `POST /api/campaigns/{id}/start_encounter/` - Start encounter
- `POST /api/campaigns/{id}/complete_encounter/` - Complete encounter
- `POST /api/campaigns/{id}/fail_encounter/` - Fail encounter

### Rest System
- `POST /api/campaigns/{id}/short_rest/` - Take short rest
- `POST /api/campaigns/{id}/long_rest/` - Take long rest
- `GET /api/campaigns/{id}/status/` - Get full status
- `GET /api/campaigns/{id}/party_status/` - Get party status

## Example Workflow

```bash
# 1. Create campaign
POST /api/campaigns/
{"name": "Dungeon Crawl", "long_rests_available": 2}

# Response: {"id": 1, ...}

# 2. Add characters
POST /api/campaigns/1/add_character/
{"character_id": 1}

POST /api/campaigns/1/add_character/
{"character_id": 2}

# 3. Add encounters
POST /api/campaigns/1/add_encounter/
{"encounter_id": 1}

POST /api/campaigns/1/add_encounter/
{"encounter_id": 2}

POST /api/campaigns/1/add_encounter/
{"encounter_id": 3}

# 4. Start campaign
POST /api/campaigns/1/start/

# 5. Check status
GET /api/campaigns/1/party_status/
# Shows: Character 1 (50/50 HP, 5 hit dice), Character 2 (45/45 HP, 5 hit dice)

# 6. Start encounter 1
POST /api/campaigns/1/start_encounter/

# 7. Create and run combat session (using combat system)
POST /api/combat/sessions/
{"encounter_id": 1}
# ... run combat ...

# 8. After combat, characters might be at 30/50 HP, 20/45 HP

# 9. Take short rest
POST /api/campaigns/1/short_rest/
# Characters heal using hit dice

# 10. Complete encounter
POST /api/campaigns/1/complete_encounter/
{"combat_session_id": 5, "rewards": {"gold": 50}}

# 11. Continue to next encounter...
```

## Strategic Tips

1. **Save Long Rests**: Only 2 available - use before boss fights or when party is very low
2. **Manage Hit Dice**: Don't spend all hit dice early - you might need them later
3. **Character Death**: Losing a character is permanent - play carefully!
4. **Resource Tracking**: Check party status between encounters
5. **Encounter Order**: Plan encounter difficulty - start easier, get harder

## Future Enhancements

- Procedural encounter generation
- Random events between encounters
- Character level-ups mid-campaign
- Item shops between encounters
- Multiple difficulty modes
- Campaign leaderboards

