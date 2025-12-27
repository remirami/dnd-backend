# Roguelike Gauntlet Campaign System Design

## Overview

A roguelike gauntlet campaign where players must survive a series of encounters with strategic rest management and permadeath.

## Core Concepts

### 1. **Gauntlet Campaign**
- Sequential series of encounters
- Characters persist between encounters (with permadeath)
- Resource management (HP, spell slots, hit dice)
- Strategic rest decisions

### 2. **Roguelike Elements**
- **Permadeath**: Characters who die are permanently removed from the campaign
- **Resource Scarcity**: Limited healing, spell slots, hit dice
- **Procedural Encounters**: Can be pre-generated or random
- **Progression**: Rewards between encounters (items, gold, maybe XP)

### 3. **Rest System**
- **Short Rest** (1 hour):
  - Spend hit dice to heal
  - Recover some abilities (class-dependent)
  - Limited uses per day
  - No spell slot recovery
  
- **Long Rest** (8 hours):
  - Full HP recovery
  - All spell slots recovered
  - All hit dice recovered
  - All abilities refreshed
  - **BUT**: Limited uses (e.g., 1-2 per campaign)
  - May have consequences (enemies get stronger, time pressure)

## Data Models

### Campaign
- `name`: Campaign name
- `status`: 'active', 'completed', 'failed'
- `current_encounter_index`: Which encounter we're on
- `short_rests_used`: Number of short rests taken
- `long_rests_used`: Number of long rests taken
- `long_rests_available`: Max long rests (default: 2)
- `created_at`, `started_at`, `ended_at`
- `notes`: Campaign notes

### CampaignCharacter
- `campaign`: ForeignKey to Campaign
- `character`: ForeignKey to Character (base character)
- `current_hp`: Current HP in campaign
- `max_hp`: Max HP (may change with level ups)
- `hit_dice_remaining`: Array of available hit dice (e.g., [1, 1, 1] for 3d8)
- `spell_slots`: JSON field tracking spell slots by level
- `is_alive`: Boolean (permadeath)
- `died_in_encounter`: Which encounter they died in
- `notes`: Character-specific notes

### CampaignEncounter
- `campaign`: ForeignKey to Campaign
- `encounter`: ForeignKey to Encounter (the actual encounter)
- `encounter_number`: Sequential number (1, 2, 3...)
- `status`: 'pending', 'active', 'completed', 'failed'
- `combat_session`: ForeignKey to CombatSession (if combat happened)
- `completed_at`: When encounter was finished
- `rewards`: JSON field for rewards (gold, items, XP)

## Game Flow

1. **Start Campaign**
   - Create campaign
   - Add characters (from Character pool)
   - Initialize campaign characters with full resources

2. **Encounter Phase**
   - Load next encounter
   - Create combat session
   - Run combat
   - If all characters die → Campaign failed
   - If encounter won → Distribute rewards, continue

3. **Between Encounters**
   - Show party status
   - Offer rest options:
     - **Continue**: Go to next encounter (no rest)
     - **Short Rest**: Spend hit dice to heal
     - **Long Rest**: Full recovery (if available)
   - Distribute rewards
   - Maybe level up characters

4. **Campaign End**
   - **Victory**: Completed all encounters
   - **Failure**: All characters dead
   - Show final statistics

## API Endpoints

### Campaign Management
- `POST /api/campaigns/` - Create new campaign
- `GET /api/campaigns/` - List campaigns
- `GET /api/campaigns/{id}/` - Get campaign details
- `POST /api/campaigns/{id}/start/` - Start campaign
- `POST /api/campaigns/{id}/add_character/` - Add character to campaign
- `POST /api/campaigns/{id}/remove_character/` - Remove character

### Encounter Management
- `GET /api/campaigns/{id}/current_encounter/` - Get current encounter
- `POST /api/campaigns/{id}/start_encounter/` - Start next encounter
- `POST /api/campaigns/{id}/complete_encounter/` - Mark encounter complete
- `POST /api/campaigns/{id}/fail_encounter/` - Mark encounter failed

### Rest System
- `POST /api/campaigns/{id}/short_rest/` - Take short rest
- `POST /api/campaigns/{id}/long_rest/` - Take long rest
- `GET /api/campaigns/{id}/rest_status/` - Get rest availability

### Campaign State
- `GET /api/campaigns/{id}/status/` - Get full campaign status
- `GET /api/campaigns/{id}/party_status/` - Get party HP/resources
- `POST /api/campaigns/{id}/end/` - End campaign (victory/failure)

## Strategic Elements

### When to Rest?
- **Short Rest**: Good for recovering HP when you have hit dice, but need to save them
- **Long Rest**: Powerful but limited - use when party is very low or before boss fights
- **No Rest**: Risky but may be necessary if long rests are limited

### Resource Management
- Track hit dice carefully (recovered on long rest)
- Manage spell slots (especially for casters)
- Consider character death impact (lose that character permanently)

### Difficulty Scaling
- Encounters get harder as campaign progresses
- Long rests may make future encounters harder
- Rewards scale with difficulty

## Future Enhancements
- Procedural encounter generation
- Random events between encounters
- Character level-ups mid-campaign
- Item shops between encounters
- Multiple difficulty modes
- Leaderboards for completed campaigns

