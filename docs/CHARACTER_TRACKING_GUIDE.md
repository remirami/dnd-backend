# Character Tracking Guide - Simple Character Sheet Management ✅

## Overview

**Yes!** The system fully supports simple character tracking. You can create characters, set stats, backgrounds, descriptions, and track spell slots **without needing campaigns or combat**.

---

## ✅ What's Available

### 1. Character Creation & Management

**`POST /api/characters/`** - Create a character
```json
{
  "name": "Aragorn",
  "level": 5,
  "character_class_id": 1,
  "race_id": 1,
  "background_id": 1,
  "alignment": "LG",
  "player_name": "John",
  "description": "A ranger from the North",
  "backstory": "Born in Rivendell..."
}
```

**`GET /api/characters/`** - List all your characters

**`GET /api/characters/{id}/`** - Get character details

**`PUT /api/characters/{id}/`** - Update character

**`DELETE /api/characters/{id}/`** - Delete character

### 2. Stats Management

**`POST /api/character-stats/`** - Create/update stats
```json
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

**`GET /api/character-stats/{id}/`** - Get stats

**`PUT /api/character-stats/{id}/`** - Update stats

### 3. Complete Character Sheet

**`GET /api/characters/{id}/character_sheet/`** - Get everything in one call!

Returns:
- Character info (name, level, class, race, background, description, backstory)
- Stats (ability scores, HP, AC, speed, modifiers)
- **Spell slots** (automatically calculated, or use current values)
- Spells known/prepared
- Features (class, racial, background, feats)
- Proficiencies (skills, tools, weapons, armor, languages)
- Inventory (items, equipment)
- Multiclass info (if applicable)

**Perfect for character sheet display!**

### 4. Spell Slot Tracking

**`GET /api/characters/{id}/character_sheet/`** - See current spell slots

**`POST /api/characters/{id}/update_spell_slots/`** - Manually set spell slots
```json
{
  "spell_slots": {
    "1": 2,  // 2 level-1 slots remaining
    "2": 1,  // 1 level-2 slot remaining
    "3": 0   // 0 level-3 slots remaining
  }
}
```

**`POST /api/characters/{id}/use_spell_slot/`** - Use a spell slot
```json
{
  "spell_level": 1
}
```

**`POST /api/characters/{id}/restore_spell_slots/`** - Restore all slots (long rest)
- Automatically calculates max slots based on class/level
- Supports multiclass spell slot calculation

### 5. Level-Up System (Automatic Stat Updates) ✅

**`POST /api/characters/{id}/level_up/`** - Level up with automatic updates!

**What happens automatically:**
- ✅ **HP Increase**: Rolls hit dice + CON modifier, updates max HP and current HP (full heal)
- ✅ **Spell Slots**: Automatically updates spell slots based on new level
- ✅ **Class Features**: Automatically applies class features for the new level
- ✅ **Subclass Features**: Automatically applies subclass features (if subclass selected)
- ✅ **ASI/Feat Tracking**: Tracks pending ASI/Feat choices at levels 4, 8, 12, 16, 19
- ✅ **Subclass Prompt**: Prompts for subclass selection if needed (level 1-3 depending on class)
- ✅ **Multiclass Support**: Supports leveling up specific classes for multiclass characters

**Request (optional for multiclass):**
```json
{
  "class_id": 2,  // Optional: level up a specific class (multiclass)
  "class_name": "Fighter"  // Or use class name
}
```

**Response includes:**
- Updated character data
- Features gained at this level
- HP gain amount
- New spell slots
- Pending ASI levels (if any)
- Pending subclass selection (if needed)

**Example:**
```json
{
  "message": "Aragorn leveled up to level 5!",
  "character": { ... },
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

### 6. ASI/Feat Selection ✅

**`POST /api/characters/{id}/apply_asi/`** - Apply ASI or select a Feat

**When to use:** After leveling up to levels 4, 8, 12, 16, or 19, you'll have a pending ASI choice.

**Option 1: Ability Score Improvement (ASI)**
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

**Response:**
- Confirms the choice
- Updates character stats (if ASI) or adds feat
- Removes level from pending ASI list
- Shows remaining pending ASI levels

**Note:** Feats have prerequisites (ability scores, proficiencies, etc.) that are automatically validated.

### 5. Spell Management

**`GET /api/characters/{id}/spell_info/`** - Get spell management info
- Prepared caster? Known caster?
- Spell limits
- Current spells

**`POST /api/characters/{id}/prepare_spells/`** - Prepare spells (Cleric, Druid, Paladin, Wizard)

**`POST /api/characters/{id}/learn_spell/`** - Learn spell (Bard, Ranger, Sorcerer, Warlock)

**`POST /api/characters/{id}/add_to_spellbook/`** - Add to spellbook (Wizard)

### 6. Inventory Management

**`GET /api/characters/{id}/inventory/`** - Get inventory
- Items
- Equipment
- Weight
- Encumbrance

**`POST /api/characters/{id}/inventory/`** - Add items

**`POST /api/characters/{id}/equip_item/`** - Equip item

**`POST /api/characters/{id}/unequip_item/`** - Unequip item

---

## 📋 Complete Workflow Example

### Step 1: Create Character
```bash
POST /api/characters/
{
  "name": "Gandalf",
  "level": 10,
  "character_class_id": 8,  // Wizard
  "race_id": 2,  // Elf
  "background_id": 5,  // Sage
  "alignment": "NG",
  "player_name": "Player 1",
  "description": "A wise wizard",
  "backstory": "Studied magic for centuries..."
}
```

### Step 2: Create Stats
```bash
POST /api/character-stats/
{
  "character": 1,
  "strength": 10,
  "dexterity": 14,
  "constitution": 14,
  "intelligence": 18,
  "wisdom": 16,
  "charisma": 12,
  "hit_points": 72,
  "max_hit_points": 72,
  "armor_class": 15,
  "speed": 30
}
```

### Step 3: Get Complete Character Sheet
```bash
GET /api/characters/1/character_sheet/
```

**Response includes:**
- All character info
- All stats with modifiers
- Spell slots (automatically calculated: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2})
- Spells (if any)
- Features (class, racial, background)
- Proficiencies
- Inventory

### Step 4: Level Up Character
```bash
# Level up (automatically updates HP, spell slots, applies features)
POST /api/characters/1/level_up/
# Response includes:
# - Updated character data
# - Features gained: [{"level": 11, "name": "Extra Attack (2)", "type": "class"}]
# - HP gain: 8
# - New spell slots: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1}
# - pending_asi: false (or true if level 4, 8, 12, 16, 19)
# - pending_asi_levels: [] (or [4, 8] if ASI not yet chosen)

# If you have a pending ASI (at levels 4, 8, 12, 16, 19):
# Option A: Take Ability Score Improvement
POST /api/characters/1/apply_asi/
{
  "level": 4,
  "choice_type": "asi",
  "asi_choice": {
    "intelligence": 2  // +2 to Intelligence
  }
}

# Option B: Take a Feat instead
POST /api/characters/1/apply_asi/
{
  "level": 4,
  "choice_type": "feat",
  "feat_id": 5  // e.g., "War Caster"
}
```

### Step 5: Track Spell Slot Usage
```bash
# Use a level 3 spell slot
POST /api/characters/1/use_spell_slot/
{
  "spell_level": 3
}
# Response: {"spell_slots_remaining": {"1": 4, "2": 3, "3": 2, "4": 3, "5": 2}}

# Restore all slots (after long rest)
POST /api/characters/1/restore_spell_slots/
# Response: {"spell_slots": {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2}}
```

---

## 🎯 Use Cases

### Simple Character Tracking
- Create characters with stats
- Set background and description
- Track spell slots
- Manage inventory
- **No campaigns or combat needed!**

### Character Sheet Display
- Use `character_sheet` endpoint to get everything
- Display in a UI
- Update stats/spell slots as needed

### Spell Slot Management
- Automatically calculated based on class/level
- Manually track usage
- Restore after long rest
- Supports multiclass spell slot calculation

---

## ✅ Features Summary

**Character Management:**
- ✅ Create characters
- ✅ Set stats (ability scores, HP, AC, speed)
- ✅ Set background
- ✅ Add description/backstory
- ✅ Track level and XP
- ✅ Multiclass support

**Spell Slot Tracking:**
- ✅ Automatic calculation (based on class/level)
- ✅ Manual tracking
- ✅ Use spell slots
- ✅ Restore spell slots (long rest)
- ✅ Multiclass spell slot calculation

**Additional Tracking:**
- ✅ Spells known/prepared
- ✅ Features (class, racial, background, feats)
- ✅ Proficiencies
- ✅ Inventory and equipment
- ✅ Hit dice tracking

---

## 📁 API Endpoints Summary

### Character Management
- `GET /api/characters/` - List characters
- `POST /api/characters/` - Create character
- `GET /api/characters/{id}/` - Get character
- `PUT /api/characters/{id}/` - Update character
- `DELETE /api/characters/{id}/` - Delete character

### Character Sheet
- `GET /api/characters/{id}/character_sheet/` - **Get complete character sheet**

### Stats
- `GET /api/character-stats/{id}/` - Get stats
- `POST /api/character-stats/` - Create stats
- `PUT /api/character-stats/{id}/` - Update stats

### Spell Slots
- `GET /api/characters/{id}/character_sheet/` - See spell slots
- `POST /api/characters/{id}/update_spell_slots/` - Set spell slots
- `POST /api/characters/{id}/use_spell_slot/` - Use a slot
- `POST /api/characters/{id}/restore_spell_slots/` - Restore all slots

### Spells
- `GET /api/characters/{id}/spell_info/` - Spell management info
- `POST /api/characters/{id}/prepare_spells/` - Prepare spells
- `POST /api/characters/{id}/learn_spell/` - Learn spell
- `POST /api/characters/{id}/add_to_spellbook/` - Add to spellbook

### Inventory
- `GET /api/characters/{id}/inventory/` - Get inventory
- `POST /api/characters/{id}/inventory/` - Add items
- `POST /api/characters/{id}/equip_item/` - Equip item
- `POST /api/characters/{id}/unequip_item/` - Unequip item

---

## 🎉 Status: Fully Supported!

The system **already supports** simple character tracking! You can:
- ✅ Create characters with all info
- ✅ Set stats, background, description
- ✅ Track spell slots
- ✅ Manage inventory
- ✅ View complete character sheet

**No campaigns or combat required!** Just use the character endpoints directly.

The `character_sheet` endpoint gives you everything in one call - perfect for displaying a character sheet UI.

