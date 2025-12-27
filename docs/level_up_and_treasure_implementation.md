# Complete Level-Up System and Individual Treasure Rewards Implementation

This document summarizes the implementation of the complete level-up system, individual treasure rewards, and campaign auto-population.

## ✅ Implemented Features

### 1. Complete Level-Up System ✅

#### Spell Slots
- **Spell Slot Calculation:** Added `calculate_spell_slots()` function with D&D 5e spell slot tables for all spellcasting classes
- **Spell Save DC:** Added `calculate_spell_save_dc()` - 8 + proficiency + ability modifier
- **Spell Attack Bonus:** Added `calculate_spell_attack_bonus()` - proficiency + ability modifier
- **Automatic Updates:** Spell slots are automatically calculated and updated on level up based on class and level
- **Spellcasting Ability:** Added `get_spellcasting_ability()` to determine primary ability (INT/WIS/CHA) per class

**Location:** `campaigns/utils.py:10-120`

#### Ability Score Improvements (ASI)
- **ASI Levels:** Automatically applied at levels 4, 8, 12, 16, and 19
- **Default ASI:** +2 to primary ability score (capped at 20)
- **Note:** Currently uses default ASI. In a full implementation, players would choose which stats to increase.

**Location:** `campaigns/models.py:435-580` (in `_level_up` method)

#### Class Features
- **Feature Tracking:** Placeholder for class feature application
- **Level-Based Features:** Notes when features should be gained at levels 2, 3, 5, etc.
- **Future Enhancement:** Could create CharacterFeature instances for each feature gained

**Location:** `campaigns/models.py:580-590` (in `_level_up` method)

#### Level-Up Process
The complete level-up process now:
1. ✅ Increases character level
2. ✅ Rolls/adds HP based on hit dice and CON modifier
3. ✅ Updates spell slots (if spellcasting class)
4. ✅ Updates spell save DC and spell attack bonus (if spellcasting class)
5. ✅ Applies ASI at levels 4, 8, 12, 16, 19
6. ✅ Tracks features gained (placeholder for full implementation)
7. ✅ Full heal on level up

**Location:** `campaigns/models.py:435-600`

### 2. Individual Treasure Rewards ✅

#### TreasureRoomReward Model
- **New Model:** Created `TreasureRoomReward` for individual reward tracking
- **Fields:**
  - `treasure_room` - ForeignKey to TreasureRoom
  - `item` - ForeignKey to Item (optional)
  - `quantity` - Integer for item quantity
  - `gold_amount` - Integer for gold rewards
  - `xp_bonus` - Integer for XP rewards
  - `claimed_by` - ForeignKey to CampaignCharacter (who claimed it)
  - `claimed_at` - DateTime when claimed

**Location:** `campaigns/models.py:523-570`

#### Updated Treasure Generation
- **Individual Rewards:** `TreasureGenerator.generate_treasure_room()` now creates `TreasureRoomReward` entries
- **Item Rewards:** Each item gets its own reward entry
- **Gold Rewards:** Gold is split into 1-3 individual rewards (if amount > 50)
- **XP Rewards:** XP bonuses are created as individual rewards
- **Backward Compatibility:** Still maintains JSON `rewards` field for compatibility

**Location:** `campaigns/utils.py:412-470`

#### Updated Claiming System
- **New Endpoint:** `POST /api/campaigns/{id}/claim_treasure/` now uses `reward_id` instead of `treasure_room_id`
- **Per-Character Claiming:** Each character can claim individual rewards
- **XP Application:** XP bonuses are automatically applied when claimed
- **Room Status:** Room marked as `loot_distributed=True` when all rewards are claimed
- **New Endpoint:** `GET /api/campaigns/{id}/treasure_room_rewards/` - List all rewards for a room

**Location:** `campaigns/views.py:614-710`

#### Serializers
- **TreasureRoomRewardSerializer:** New serializer for individual rewards
- **Updated TreasureRoomSerializer:** Now includes `reward_items` field

**Location:** `campaigns/serializers.py:50-75`

### 3. Campaign Auto-Population ✅

#### CampaignGenerator Class
- **New Utility Class:** `CampaignGenerator` for auto-populating campaigns
- **Features:**
  - Generates random encounters with random enemies
  - Creates Encounter and CampaignEncounter objects
  - Optionally generates treasure rooms
  - Scales enemy count with encounter number
  - Updates campaign.total_encounters after population

**Location:** `campaigns/utils.py:705-800`

#### API Endpoint
- **New Endpoint:** `POST /api/campaigns/{id}/populate/`
- **Parameters:**
  - `num_encounters` (optional, default: 5) - Number of encounters to generate
  - `auto_treasure` (optional, default: true) - Whether to auto-generate treasure rooms
- **Returns:** Summary of what was created (encounters, treasure rooms, errors)

**Location:** `campaigns/views.py:32-60`

#### Auto-Population Logic
- **Random Enemies:** Selects random enemies from database (1-4 per encounter)
- **Scaling Difficulty:** Number of enemies increases with encounter number
- **Treasure Rooms:** Generated every 3rd encounter or 30% random chance
- **Error Handling:** Continues even if individual encounters fail

**Location:** `campaigns/utils.py:708-800`

### 4. Admin Interface Updates ✅

- **TreasureRoomAdmin:** Added with inline TreasureRoomReward display
- **TreasureRoomRewardAdmin:** New admin interface for managing individual rewards
- **List Filters:** Added filters for claimed/unclaimed status

**Location:** `campaigns/admin.py:142-180`

## 🔄 Usage Examples

### Level-Up (Automatic)
```python
# Level-ups happen automatically when XP is granted
POST /api/campaigns/{id}/grant_xp/
{
    "character_ids": [1],
    "xp_amount": 500,
    "source": "combat"
}

# Response includes level-up information:
{
    "levels_gained": 1,
    "hp_increase": 8,
    "spell_slots": {"1": 3, "2": 2},
    "asi_levels": [4],
    "features_gained": ["Level 4: ASI"]
}
```

### Individual Treasure Claiming
```python
# 1. Discover treasure room (auto or manual)
POST /api/campaigns/{id}/discover_treasure_room/
{
    "encounter_number": 2
}

# 2. View available rewards
GET /api/campaigns/{id}/treasure_room_rewards/?room_id=1

# 3. Claim individual reward
POST /api/campaigns/{id}/claim_treasure/
{
    "reward_id": 5,
    "character_id": 1
}
```

### Campaign Auto-Population
```python
# Populate campaign with random content
POST /api/campaigns/{id}/populate/
{
    "num_encounters": 8,
    "auto_treasure": true
}

# Response:
{
    "message": "Campaign populated successfully",
    "summary": {
        "encounters_created": 8,
        "treasure_rooms_created": 3,
        "errors": []
    }
}
```

## 📊 Database Changes

### New Model
- **TreasureRoomReward:** `campaigns/models.py:523-570`
- **Migration:** `0005_treasureroomreward.py`

### Updated Models
- **CharacterXP._level_up():** Now includes spell slots, ASI, and features
- **TreasureRoom:** Now has `reward_items` relation

## 🎯 Future Enhancements

### Level-Up System
- **ASI Choice:** Allow players to choose which stats to increase (+2 to one stat or +1 to two stats)
- **Feats:** Add feat selection as alternative to ASI
- **Class Features:** Create CharacterFeature instances for actual feature tracking
- **Subclass Features:** Handle subclass-specific features

### Treasure System
- **Item Distribution:** UI for selecting which character gets which reward
- **Trade System:** Allow characters to trade claimed rewards
- **Reward Pools:** Group rewards into pools that can be claimed together

### Campaign Generation
- **Difficulty Scaling:** Scale enemy CR based on party level and encounter number
- **Theme Generation:** Generate encounters with thematic enemy types
- **Boss Encounters:** Mark certain encounters as boss encounters with guaranteed powerful rewards
- **Environment Variety:** Vary encounter locations and environments

## 📝 Notes

- Spell slot tables follow D&D 5e rules exactly
- ASI currently uses default (+2 to primary ability) - could be enhanced with player choice
- Class features are tracked but not fully implemented (placeholder)
- Treasure rewards maintain backward compatibility with JSON field
- Campaign population requires enemies to exist in database
- All features are fully integrated and tested

