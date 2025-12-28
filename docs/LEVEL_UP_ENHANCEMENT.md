# Level-Up System Enhancement ✅

## Overview

The standalone character tracking system now includes a **complete automatic level-up mechanism** that updates all relevant stats, applies class features, and handles ASI/Feat selection at breakpoint levels.

---

## ✅ What Was Added

### 1. Character Model Fields

Added to `Character` model:
- `pending_asi_levels` (JSONField): List of levels where ASI/Feat choice is pending (e.g., `[4, 8]`)
- `pending_subclass_selection` (BooleanField): True if character needs to select a subclass

### 2. Enhanced `level_up` Endpoint

**`POST /api/characters/{id}/level_up/`**

**Automatic Updates:**
- ✅ **HP Increase**: Rolls hit dice + CON modifier, updates max HP and current HP (full heal)
- ✅ **Spell Slots**: Automatically calculates and updates spell slots based on new level
- ✅ **Class Features**: Automatically applies class features for the new level
- ✅ **Subclass Features**: Automatically applies subclass features (if subclass selected)
- ✅ **ASI/Feat Tracking**: Tracks pending ASI/Feat choices at levels 4, 8, 12, 16, 19
- ✅ **Subclass Prompt**: Prompts for subclass selection if needed (level 1-3 depending on class)
- ✅ **Multiclass Support**: Supports leveling up specific classes for multiclass characters

**Request (optional for multiclass):**
```json
{
  "class_id": 2,  // Optional: level up a specific class
  "class_name": "Fighter"  // Or use class name
}
```

**Response:**
```json
{
  "message": "Aragorn leveled up to level 5!",
  "character": { ... },
  "class_levels": [...],
  "features_gained": [
    {"level": 5, "name": "Extra Attack", "type": "class"}
  ],
  "hp_gain": 8,
  "spell_slots": {"1": 4, "2": 3, "3": 2},
  "pending_asi": false,
  "pending_subclass": false,
  "pending_asi_levels": []
}
```

### 3. New `apply_asi` Endpoint

**`POST /api/characters/{id}/apply_asi/`**

Allows players to choose between Ability Score Improvement (ASI) or Feat at breakpoint levels (4, 8, 12, 16, 19).

**Option 1: Ability Score Improvement**
```json
{
  "level": 4,
  "choice_type": "asi",
  "asi_choice": {
    "strength": 2  // +2 to one stat
    // OR
    "strength": 1, "dexterity": 1  // +1 to two stats
  }
}
```

**Option 2: Feat Selection**
```json
{
  "level": 4,
  "choice_type": "feat",
  "feat_id": 5  // ID of the feat to take
}
```

**Features:**
- Validates ASI totals (+2 total)
- Validates feat prerequisites (ability scores, proficiencies, level)
- Prevents duplicate feats
- Applies ability score increases from feats (if any)
- Removes level from pending ASI list after selection

---

## 🎯 How It Works

### Level-Up Flow

1. **Player calls `level_up` endpoint**
   - Character level increases
   - HP is rolled and added (hit dice + CON mod)
   - Spell slots are recalculated
   - Class features are applied
   - Subclass features are applied (if applicable)

2. **At ASI Breakpoint Levels (4, 8, 12, 16, 19)**
   - Level is added to `pending_asi_levels` list
   - Response includes `pending_asi: true` and `pending_asi_levels: [4]`
   - Player must call `apply_asi` endpoint to make choice

3. **Player calls `apply_asi` endpoint**
   - Chooses ASI or Feat
   - Stats are updated (if ASI) or feat is added (if feat)
   - Level is removed from `pending_asi_levels`
   - Character can continue leveling

### Subclass Selection Flow

1. **At Subclass Selection Level** (varies by class)
   - Cleric, Sorcerer, Warlock: Level 1
   - Druid, Wizard: Level 2
   - Most others: Level 3
   
2. **If no subclass selected**
   - `pending_subclass_selection` is set to `true`
   - Player must select subclass via existing `select_subclass` endpoint
   - Subclass features are then applied retroactively

---

## 📋 Example Workflow

```bash
# 1. Character is level 3
GET /api/characters/1/character_sheet/
# Level: 3, HP: 24/24

# 2. Level up to 4
POST /api/characters/1/level_up/
# Response:
# - Level: 4
# - HP gain: 7 (rolled 5 + CON mod 2)
# - New HP: 31/31
# - pending_asi: true
# - pending_asi_levels: [4]

# 3. Apply ASI
POST /api/characters/1/apply_asi/
{
  "level": 4,
  "choice_type": "asi",
  "asi_choice": {"strength": 2}
}
# Response:
# - Strength increased from 16 to 18
# - pending_asi_levels: []

# 4. Continue leveling
POST /api/characters/1/level_up/
# Level: 5, HP: 39/39, Features gained: ["Extra Attack"]
```

---

## 🔧 Technical Details

### HP Calculation
- Rolls hit dice based on class (e.g., Fighter = d10, Wizard = d6)
- Adds CON modifier
- Minimum 1 HP per level
- Full heal on level up

### Spell Slot Calculation
- Uses `calculate_spell_slots()` from `campaigns.utils`
- Supports multiclass spell slot calculation via `calculate_multiclass_spell_slots()`
- Updates spell save DC and spell attack bonus automatically

### Class Feature Application
- Uses `get_class_features()` from `campaigns.class_features_data`
- Creates `CharacterFeature` instances automatically
- Prevents duplicates with `get_or_create()`

### Multiclass Support
- Can level up specific classes
- Tracks levels per class via `CharacterClassLevel`
- Calculates total level automatically
- Handles HP and spell slots per class level

---

## ✅ Migration

Created migration: `characters/migrations/0009_character_pending_asi_levels_and_more.py`

**Fields added:**
- `pending_asi_levels` (JSONField, default: `[]`)
- `pending_subclass_selection` (BooleanField, default: `False`)

---

## 📚 Documentation Updated

- `docs/CHARACTER_TRACKING_GUIDE.md` - Added level-up and ASI sections
- Complete workflow examples included

---

## 🎉 Summary

**Yes!** The character tracking system now has a complete level-up mechanism that:

1. ✅ Automatically updates HP (rolls hit dice + CON mod)
2. ✅ Automatically updates spell slots
3. ✅ Automatically applies class features
4. ✅ Tracks pending ASI/Feat choices at breakpoint levels
5. ✅ Provides endpoint to apply ASI or select Feats
6. ✅ Supports multiclass leveling
7. ✅ Handles subclass selection prompts

**The frontend just needs to:**
- Call `level_up` endpoint when player clicks "Level Up"
- Check `pending_asi` flag in response
- If true, show ASI/Feat selection UI
- Call `apply_asi` endpoint with player's choice
- Display updated character data

**Everything else is handled automatically!** 🚀

