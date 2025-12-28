# Missing Features from Level-Up Implementation

## Analysis Date
Based on comparison between `level_up_and_treasure_implementation.md` and current codebase.

## ✅ What's Already Implemented

### 1. Core Level-Up Mechanics ✅
- **XP Tracking**: `CharacterXP` model with `add_xp()` method
- **Level Calculation**: D&D 5e XP thresholds (300, 900, 2700, etc.)
- **HP Increases**: Roll hit dice + CON modifier per level
- **Spell Slots**: Full spell slot tables for all spellcasting classes
- **Spell Save DC**: 8 + proficiency + ability modifier
- **Spell Attack Bonus**: proficiency + ability modifier
- **ASI (Ability Score Improvements)**: Applied at levels 4, 8, 12, 16, 19
- **Full Heal on Level Up**: Characters get full HP when leveling

**Location**: `campaigns/models.py:367-556`, `campaigns/utils.py:10-120`

### 2. Individual Treasure Rewards ✅
- **TreasureRoomReward Model**: Individual reward tracking
- **Per-Character Claiming**: Each character can claim specific rewards
- **Item/Gold/XP Rewards**: All reward types supported
- **Claiming System**: `claim_treasure` API endpoint
- **Admin Interface**: Full admin support for rewards

**Location**: `campaigns/models.py:609-630`, `campaigns/views.py:614-710`

### 3. Campaign Auto-Population ✅
- **CampaignGenerator Class**: Auto-generates encounters
- **Random Enemies**: Pulls from database
- **Treasure Generation**: Auto-creates treasure rooms
- **API Endpoint**: `POST /api/campaigns/{id}/populate/`

**Location**: `campaigns/utils.py:705-800`, `campaigns/views.py:32-60`

## ❌ What's Missing

### 1. Class Feature Application (MAJOR GAP)

**Current State:**
- `CharacterFeature` model EXISTS in `characters/models.py:253-269`
- Level-up code has PLACEHOLDER for features (`campaigns/models.py:529-543`)
- Features are tracked in a simple list but NOT created as `CharacterFeature` instances

**What's Missing:**
```python
# Current code (campaigns/models.py:532-542):
features_gained = []
for level in range(old_level + 1, new_level + 1):
    if level == 2:
        features_gained.append(f"Level {level}: Class Feature")
    elif level == 3:
        features_gained.append(f"Level {level}: Subclass Feature")
    # ... just strings, not actual feature records
```

**What Should Be Implemented:**
1. **Feature Database/Lookup Table**
   - Store class features by class and level
   - Store subclass features
   - Store racial features

2. **Feature Application Logic**
   - Create `CharacterFeature` instances when leveling up
   - Link features to character via `character.features.create(...)`
   - Track feature source (e.g., "Fighter Level 2")

3. **Feature Types to Implement:**
   - **Level 1**: Starting class features
   - **Level 2**: Class-specific features (e.g., Action Surge, Cunning Action)
   - **Level 3**: Subclass selection and first subclass feature
   - **Level 5**: Extra Attack (martial classes) or 3rd level spells
   - **Level 6**: Ability score improvement or class feature
   - **Level 9**: Indomitable, etc.
   - **Level 11**: Improved features
   - **Level 20**: Capstone abilities

**Example Implementation Needed:**
```python
# In campaigns/models.py _level_up method:
from characters.models import CharacterFeature

# Get class features for this level
class_features = get_class_features(character.character_class.name, new_level)

for feature_data in class_features:
    CharacterFeature.objects.create(
        character=character,
        name=feature_data['name'],
        feature_type='class',
        description=feature_data['description'],
        source=f"{character.character_class.name} Level {new_level}"
    )
```

### 2. ASI Player Choice (MODERATE GAP)

**Current State:**
- ASI is automatically applied to primary ability
- +2 to primary ability (STR for Fighter, INT for Wizard, etc.)
- Capped at 20

**What's Missing:**
1. **Player Choice for ASI**
   - Allow +2 to one stat OR +1 to two stats
   - Allow choosing which stats to increase
   - UI/API for player selection

2. **Feat Selection**
   - Alternative to ASI at levels 4, 8, 12, 16, 19
   - Feat database/table
   - Feat application logic
   - Feat prerequisites checking

**Example API Needed:**
```python
POST /api/campaigns/{id}/apply_asi/
{
    "character_id": 1,
    "level": 4,
    "choice": "asi",  # or "feat"
    "asi_increases": {
        "strength": 2  # or {"strength": 1, "dexterity": 1}
    }
}

# OR

POST /api/campaigns/{id}/apply_asi/
{
    "character_id": 1,
    "level": 4,
    "choice": "feat",
    "feat_id": 5  # e.g., "Great Weapon Master"
}
```

### 3. Subclass Selection (MODERATE GAP)

**Current State:**
- Subclass features mentioned in placeholder
- No actual subclass selection system
- No subclass tracking

**What's Missing:**
1. **Subclass Model** (or field on Character)
   - Track which subclass is selected
   - Subclass selection at level 3 (most classes)
   - Subclass-specific features

2. **Subclass Selection API**
   ```python
   POST /api/characters/{id}/select_subclass/
   {
       "subclass_id": 2  # e.g., "Champion" for Fighter
   }
   ```

3. **Subclass Feature Application**
   - Apply subclass features at levels 3, 7, 10, 15, 18, 20

### 4. Proficiency Bonus Updates (MINOR GAP)

**Current State:**
- Proficiency bonus is calculated as property: `((level - 1) // 4) + 2`
- Automatically updates based on level
- ✅ This actually works correctly!

**Status**: ✅ **NOT MISSING** - Already implemented correctly

### 5. Hit Dice Restoration on Level Up (MINOR GAP)

**Current State:**
- Hit dice are tracked in `CampaignCharacter.hit_dice_remaining`
- Hit dice are spent during short rests
- Hit dice are restored on long rests

**What's Missing:**
- On level up, character should gain additional hit dice
- Currently only HP is increased, not hit dice pool

**Fix Needed:**
```python
# In campaigns/models.py _level_up method, add:
hit_dice_type = character.character_class.hit_dice
if hit_dice_type in self.campaign_character.hit_dice_remaining:
    self.campaign_character.hit_dice_remaining[hit_dice_type] += levels_gained
else:
    self.campaign_character.hit_dice_remaining[hit_dice_type] = levels_gained
```

### 6. Multiclassing Support (MAJOR GAP - Future)

**Current State:**
- Single class only
- No multiclass support

**What Would Be Needed:**
1. Multiple `CharacterClass` relationships
2. Level tracking per class
3. Multiclass prerequisites checking
4. Spell slot calculation for multiclass casters
5. Feature progression from multiple classes

**Status**: Not mentioned in document, likely out of scope for now

### 7. Death Saving Throws (MINOR GAP)

**Current State:**
- Characters have `is_alive` boolean
- Death is permanent (permadeath in campaigns)

**What's Missing:**
- Death saving throw tracking (0 HP → unconscious → death saves)
- Stabilization mechanics
- Resurrection/revival (if permadeath is disabled)

**Status**: May be intentionally simplified for roguelike mode

## 📊 Priority Assessment

### High Priority (Should Implement)
1. **✅ Class Feature Application** - Core D&D mechanic
   - Create feature lookup table
   - Apply features on level up
   - Create `CharacterFeature` instances

2. **✅ Hit Dice Increase on Level Up** - Simple fix
   - Add hit dice when leveling
   - One-line code change

### Medium Priority (Nice to Have)
3. **ASI Player Choice** - Improves player agency
   - Requires UI/API for selection
   - Feat system is complex

4. **Subclass Selection** - Important for character identity
   - Requires subclass database
   - Subclass feature tracking

### Low Priority (Future Enhancement)
5. **Multiclassing** - Complex, out of scope
6. **Death Saves** - May conflict with permadeath design

## 🔧 Recommended Implementation Order

### Phase 1: Quick Fixes (1-2 hours)
1. **Add hit dice increase on level up**
   ```python
   # In _level_up method
   hit_dice_type = character.character_class.hit_dice
   for _ in range(levels_gained):
       if hit_dice_type in self.campaign_character.hit_dice_remaining:
           self.campaign_character.hit_dice_remaining[hit_dice_type] += 1
       else:
           self.campaign_character.hit_dice_remaining[hit_dice_type] = 1
   ```

### Phase 2: Class Features (4-8 hours)
1. **Create class feature lookup data**
   - JSON file or database table with features by class/level
   - Include name, description, level requirement

2. **Create feature application function**
   ```python
   def apply_class_features(character, level):
       features = CLASS_FEATURES[character.character_class.name][level]
       for feature_data in features:
           CharacterFeature.objects.create(
               character=character,
               name=feature_data['name'],
               feature_type='class',
               description=feature_data['description'],
               source=f"{character.character_class.name} Level {level}"
           )
   ```

3. **Integrate into _level_up method**
   - Replace placeholder with actual feature creation

### Phase 3: ASI Choice (4-6 hours)
1. **Create ASI pending state**
   - Track when character has pending ASI
   - Prevent progression until ASI is applied

2. **Create ASI application API**
   - Endpoint for applying ASI
   - Validation for stat caps (20 max)
   - Support +2 to one or +1 to two

3. **Optional: Add feat system**
   - Feat database
   - Feat selection API
   - Feat prerequisites

### Phase 4: Subclass (6-8 hours)
1. **Add subclass field to Character model**
2. **Create subclass selection API**
3. **Add subclass feature data**
4. **Apply subclass features on level up**

## 📝 Code Locations for Changes

### Files to Modify:
1. **`campaigns/models.py`** - `CharacterXP._level_up()` method (lines 435-556)
   - Add hit dice increase
   - Replace feature placeholder with actual feature creation

2. **`campaigns/utils.py`** - Add feature lookup functions
   - `get_class_features(class_name, level)`
   - `get_subclass_features(subclass_name, level)`

3. **`campaigns/views.py`** - Add new API endpoints
   - `apply_asi` action
   - `select_subclass` action (or in characters app)

4. **`characters/models.py`** - May need subclass field
   - Add `subclass` ForeignKey or CharField

5. **`characters/admin.py`** - Update admin for features
   - Add `CharacterFeatureInline` to `CharacterAdmin`

## 🎯 Summary

### Fully Implemented ✅
- XP tracking and level calculation
- HP increases
- Spell slot updates
- Spell save DC and attack bonus
- ASI application (automatic)
- Individual treasure rewards
- Campaign auto-population

### Partially Implemented ⚠️
- Class features (placeholder only)
- ASI (automatic, no player choice)

### Not Implemented ❌
- Class feature database and application
- Hit dice increase on level up
- ASI player choice
- Feat system
- Subclass selection
- Subclass features
- Multiclassing

### Biggest Gap
**Class Features** - The `CharacterFeature` model exists but is never populated during level-up. This is the most significant missing piece for a complete D&D experience.

---

**Recommendation**: Start with Phase 1 (hit dice fix) and Phase 2 (class features) to get the core level-up experience complete. ASI choice and subclasses can be added later as enhancements.

