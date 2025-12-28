# ASI Player Choice & Subclass Selection - Implementation Complete!

## ✅ What Was Implemented

### 1. ASI Player Choice System ✅
Players can now choose how to apply their Ability Score Improvements instead of automatic application.

### 2. Subclass Selection System ✅
Players can select their subclass at the appropriate level (varies by class).

## 🎯 Features

### ASI System

**Before:**
- ASI automatically applied +2 to primary ability
- No player choice
- Inflexible

**After:**
- ✅ ASI marked as "pending" when level reached
- ✅ Player chooses which stats to increase
- ✅ Supports +2 to one stat OR +1 to two stats
- ✅ Stat cap at 20 enforced
- ✅ API endpoint for applying ASI
- ✅ Tracks pending ASI levels

### Subclass System

**Before:**
- No subclass tracking
- Subclass features mentioned but not applied

**After:**
- ✅ Subclass field added to Character model
- ✅ Automatic detection when subclass selection is needed
- ✅ Pending flag for subclass selection
- ✅ API endpoint for selecting subclass
- ✅ Class-specific subclass levels (level 1, 2, or 3)

## 📊 Database Changes

### Character Model
```python
# Added field:
subclass = models.CharField(max_length=100, blank=True, null=True)
```

### CharacterXP Model
```python
# Added fields:
pending_asi_levels = models.JSONField(default=list)
pending_subclass_selection = models.BooleanField(default=False)
```

**Migrations:**
- `campaigns/migrations/0006_characterxp_pending_asi_levels_and_more.py`
- `characters/migrations/0004_character_subclass.py`

## 🔧 API Endpoints

### 1. Apply ASI

**Endpoint:** `POST /api/campaigns/{campaign_id}/apply_asi/`

**Request Body:**
```json
{
    "character_id": 1,
    "level": 4,
    "asi_choice": {
        "strength": 2  // +2 to one stat
    }
}
```

**OR:**
```json
{
    "character_id": 1,
    "level": 4,
    "asi_choice": {
        "strength": 1,  // +1 to two stats
        "dexterity": 1
    }
}
```

**Response:**
```json
{
    "message": "ASI applied successfully for level 4",
    "asi_applied": {
        "strength": 2
    },
    "remaining_pending_asi": [],
    "new_stats": {
        "strength": 18,
        "dexterity": 14,
        "constitution": 13,
        "intelligence": 10,
        "wisdom": 12,
        "charisma": 8
    }
}
```

**Validation:**
- Total increase must equal 2
- Can only increase 1 or 2 different abilities
- Each ability can only increase by 1 or 2
- Stats capped at 20
- Level must have pending ASI

### 2. Select Subclass

**Endpoint:** `POST /api/campaigns/{campaign_id}/select_subclass/`

**Request Body:**
```json
{
    "character_id": 1,
    "subclass": "Champion"
}
```

**Response:**
```json
{
    "message": "Subclass selected successfully: Champion",
    "character": {
        "id": 1,
        "name": "Fighter Character",
        "class": "fighter",
        "subclass": "Champion",
        "level": 3
    }
}
```

**Validation:**
- Character must have pending subclass selection
- Character cannot already have a subclass
- Subclass selection must be at appropriate level

## 🎮 How It Works

### Level-Up Flow

**When character gains XP and levels up:**

1. **Level calculated** from XP thresholds
2. **HP increased** (roll hit dice + CON)
3. **Hit dice pool increased**
4. **Spell slots updated** (if spellcaster)
5. **ASI checked:**
   - If level is 4, 8, 12, 16, or 19
   - Level added to `pending_asi_levels`
   - Player must apply ASI via API
6. **Subclass checked:**
   - If level reaches subclass selection level
   - `pending_subclass_selection` set to True
   - Player must select subclass via API
7. **Class features granted** (automatic)

### Subclass Selection Levels

Different classes choose subclass at different levels:

| Class | Subclass Level | Feature Name |
|-------|----------------|--------------|
| Cleric | 1 | Divine Domain |
| Sorcerer | 1 | Sorcerous Origin |
| Warlock | 1 | Otherworldly Patron |
| Druid | 2 | Druid Circle |
| Wizard | 2 | Arcane Tradition |
| **All Others** | **3** | Various |

## 🧪 Test Results

Comprehensive test (`test_asi_and_subclass.py`) with **100% SUCCESS**:

```
[PASS] Subclass selection works
[PASS] First ASI applied correctly (+2 STR)
[PASS] Second ASI applied correctly (+1 DEX)
[PASS] Second ASI applied correctly (+1 CON)
[PASS] No pending ASI remaining

Tests Passed: 5/5
[SUCCESS] ALL TESTS PASSED!
```

### Test Scenario

**Character:** Fighter, Level 1 → 8
- **Initial Stats:** STR 15, DEX 14, CON 13

**Level 3:**
- ✅ Subclass selection pending
- ✅ Selected "Champion"

**Level 4:**
- ✅ ASI pending
- ✅ Applied +2 to Strength
- ✅ New STR: 17

**Level 8:**
- ✅ ASI pending
- ✅ Applied +1 to DEX, +1 to CON
- ✅ New DEX: 15, CON: 14

**Final Stats:** STR 17, DEX 15, CON 14

## 📝 Example Usage

### Frontend Flow

1. **Character levels up**
   ```javascript
   // XP is granted
   POST /api/campaigns/1/grant_xp/
   {
       "character_ids": [1],
       "xp_amount": 2700
   }
   
   // Response includes:
   {
       "characters": [{
           "level_gained": true,
           "new_level": 4,
           "pending_asi": [4],
           "pending_subclass": false
       }]
   }
   ```

2. **Player sees "ASI Available" notification**

3. **Player chooses ASI**
   ```javascript
   POST /api/campaigns/1/apply_asi/
   {
       "character_id": 1,
       "level": 4,
       "asi_choice": {
           "strength": 2
       }
   }
   ```

4. **Stats updated, ASI cleared**

### Subclass Flow

1. **Character reaches level 3**
   ```javascript
   // Response includes:
   {
       "pending_subclass": true
   }
   ```

2. **Player sees "Choose Subclass" dialog**

3. **Player selects subclass**
   ```javascript
   POST /api/campaigns/1/select_subclass/
   {
       "character_id": 1,
       "subclass": "Battle Master"
   }
   ```

4. **Subclass set, flag cleared**

## 🎯 Common Subclasses

### Fighter
- Champion
- Battle Master
- Eldritch Knight

### Wizard
- School of Evocation
- School of Abjuration
- School of Divination

### Rogue
- Thief
- Assassin
- Arcane Trickster

### Cleric
- Life Domain
- Light Domain
- War Domain

### Bard
- College of Lore
- College of Valor

### Barbarian
- Path of the Berserker
- Path of the Totem Warrior

### Paladin
- Oath of Devotion
- Oath of the Ancients
- Oath of Vengeance

### Ranger
- Hunter
- Beast Master

### Druid
- Circle of the Land
- Circle of the Moon

### Monk
- Way of the Open Hand
- Way of Shadow
- Way of the Four Elements

### Sorcerer
- Draconic Bloodline
- Wild Magic

### Warlock
- The Archfey
- The Fiend
- The Great Old One

## 📁 Files Modified/Created

### Modified:
1. **`characters/models.py`** - Added `subclass` field
2. **`campaigns/models.py`** - Added `pending_asi_levels` and `pending_subclass_selection` fields
3. **`campaigns/models.py`** - Updated `_level_up()` to mark ASI/subclass as pending
4. **`campaigns/views.py`** - Added `apply_asi` and `select_subclass` endpoints

### Created:
1. **`test_asi_and_subclass.py`** - Comprehensive test script
2. **`docs/ASI_AND_SUBCLASS_IMPLEMENTATION.md`** - This file

### Migrations:
1. **`campaigns/migrations/0006_characterxp_pending_asi_levels_and_more.py`**
2. **`characters/migrations/0004_character_subclass.py`**

## 🚀 What's Complete

✅ ASI player choice system  
✅ Subclass selection system  
✅ Pending state tracking  
✅ API endpoints for both  
✅ Validation and error handling  
✅ Stat cap enforcement (20 max)  
✅ Class-specific subclass levels  
✅ Database migrations  
✅ Comprehensive testing  
✅ Full documentation  

## 🎯 Future Enhancements

### Potential Additions:

1. **Feat System** (Alternative to ASI)
   - Feat database
   - Feat selection instead of ASI
   - Feat prerequisites
   - Feat effects

2. **Subclass Features**
   - Add subclass-specific features to `class_features_data.py`
   - Apply subclass features on level-up
   - Retroactive feature application when subclass selected

3. **ASI Recommendations**
   - Suggest optimal ASI based on class
   - Show stat breakpoints (e.g., modifier changes)
   - Highlight stats near cap

4. **Subclass Validation**
   - Validate subclass matches class
   - Provide list of valid subclasses per class
   - Subclass descriptions

## 📊 Summary

### Before This Implementation:
- ❌ ASI automatically applied
- ❌ No player choice
- ❌ No subclass tracking
- ❌ Inflexible character progression

### After This Implementation:
- ✅ Players choose ASI distribution
- ✅ Support for +2/+0 or +1/+1 splits
- ✅ Subclass selection at appropriate levels
- ✅ Pending state tracking
- ✅ Full API support
- ✅ Flexible character progression

**The level-up system now provides full player agency for ASI and subclass choices!** 🎲⚔️

## 🎮 Player Experience

Players now have meaningful choices during character progression:

1. **Level 3:** "Choose your subclass!"
   - Defines character specialization
   - Unlocks unique abilities

2. **Level 4:** "Ability Score Improvement!"
   - Boost primary stat (+2)
   - OR balance two stats (+1/+1)
   - Strategic choice based on playstyle

3. **Level 8, 12, 16, 19:** More ASI choices!
   - Build toward stat caps
   - Balance multiple abilities
   - Customize character strengths

This creates a more engaging and personalized D&D experience! 🎉

