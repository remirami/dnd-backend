# Spell Management System - Implementation Complete ✅

## Overview

A comprehensive spell management system for D&D 5e characters, supporting:
- **Prepared Casters** (Cleric, Druid, Paladin, Wizard)
- **Known Casters** (Bard, Ranger, Sorcerer, Warlock)
- **Wizard Spellbook** management
- **Ritual Casting**
- **Combat Spell Validation**

---

## ✅ What Was Implemented

### 1. Database Changes
- Added `in_spellbook` field to `CharacterSpell` model
- Migration: `characters/migrations/0006_add_spellbook_field.py`

### 2. Spell Management Utilities (`characters/spell_management.py`)

**Spellcasting Type Detection:**
- `is_prepared_caster(character)` - Check if character prepares spells
- `is_known_caster(character)` - Check if character knows spells
- `can_cast_rituals(character)` - Check if character can cast rituals

**Spell Limits:**
- `calculate_spells_prepared(character)` - Calculate prepared spell limit (Level + Ability Modifier)
- `calculate_spells_known(character)` - Calculate known spell limit (by class/level)
- `get_wizard_spellbook_size(character)` - Calculate Wizard spellbook size (6 + (level-1)*2)

**Spell Validation:**
- `can_cast_spell(character, spell_name, allow_ritual=True)` - Check if character can cast a spell
- `can_learn_spell(character, spell_level)` - Check if known caster can learn more spells
- `can_add_to_spellbook(character, spell_level)` - Check if Wizard can add to spellbook

**Spell Queries:**
- `get_prepared_spells(character)` - Get all prepared spells
- `get_known_spells(character)` - Get all known spells
- `get_spellbook_spells(character)` - Get all spells in Wizard's spellbook

### 3. API Endpoints (`characters/views.py`)

#### `GET /api/characters/{id}/spell_info/`
Get spell management information for a character.

**Response:**
```json
{
  "is_prepared_caster": true,
  "is_known_caster": false,
  "can_cast_rituals": true,
  "spells_prepared": {
    "limit": 9,
    "current": 5,
    "spells": [...]
  },
  "spellbook": {  // For Wizards only
    "size": 14,
    "current": 8,
    "spells": [...]
  }
}
```

#### `POST /api/characters/{id}/prepare_spells/`
Prepare spells for a prepared caster.

**Request:**
```json
{
  "spell_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "message": "Prepared 5 spell(s)",
  "spells_prepared": [...],
  "limit": 9
}
```

#### `POST /api/characters/{id}/learn_spell/`
Learn a new spell (for known casters).

**Request:**
```json
{
  "spell_name": "Fireball",
  "spell_level": 3,
  "school": "Evocation",
  "description": "A bright streak flashes...",
  "is_ritual": false
}
```

**Response:**
```json
{
  "message": "Learned Fireball",
  "spell": {...}
}
```

#### `POST /api/characters/{id}/add_to_spellbook/`
Add a spell to Wizard's spellbook.

**Request:**
```json
{
  "spell_name": "Magic Missile",
  "spell_level": 1,
  "school": "Evocation",
  "description": "...",
  "is_ritual": false
}
```

#### `POST /api/characters/{id}/learn_from_scroll/`
Learn a spell from a scroll (Wizards only).

**Request:** Same as `add_to_spellbook`

### 4. Combat Integration (`combat/views.py`)

Updated `cast_spell` endpoint to validate spells:
- Checks if spell is prepared (for prepared casters)
- Checks if spell is known (for known casters)
- Allows ritual casting for ritual casters
- Returns error if spell cannot be cast

---

## 📊 Spellcasting Rules

### Prepared Casters
- **Cleric, Druid, Paladin, Wizard**
- Prepare spells each day
- **Formula:** Level + Spellcasting Ability Modifier
- Minimum: 1 spell

### Known Casters
- **Bard, Ranger, Sorcerer, Warlock**
- Know fixed number of spells
- **Bard:** 4 at level 1, up to 22 at level 20
- **Sorcerer:** 2 at level 1, up to 15 at level 20
- **Warlock:** 2 at level 1, up to 15 at level 20
- **Ranger:** 0 at level 1, up to 11 at level 20

### Wizard Spellbook
- Starts with 6 spells at level 1
- Gains 2 spells per level
- Can learn from scrolls
- Must prepare spells from spellbook to cast them

### Ritual Casting
- **Cleric, Druid, Wizard** can cast ritual spells without preparing them
- Ritual spells take 10 minutes longer to cast
- Must have spell in spellbook (Wizards) or spell list (Cleric/Druid)

---

## 🎯 Usage Examples

### Preparing Spells (Cleric)
```python
POST /api/characters/1/prepare_spells/
{
  "spell_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9]
}
```

### Learning Spells (Bard)
```python
POST /api/characters/2/learn_spell/
{
  "spell_name": "Vicious Mockery",
  "spell_level": 0,
  "school": "Enchantment",
  "description": "You unleash a string of insults..."
}
```

### Adding to Spellbook (Wizard)
```python
POST /api/characters/3/add_to_spellbook/
{
  "spell_name": "Magic Missile",
  "spell_level": 1,
  "school": "Evocation",
  "description": "You create three glowing darts..."
}
```

### Casting in Combat
```python
POST /api/combat/sessions/1/cast_spell/
{
  "caster_id": 1,
  "target_id": 2,
  "spell_name": "Fireball",  // Must be prepared/known
  "spell_level": 3,
  "is_ritual": false
}
```

---

## ✅ Test Results

All tests pass:
- ✅ Spellcasting type detection
- ✅ Spells prepared calculation
- ✅ Spells known calculation
- ✅ Wizard spellbook size
- ✅ Spell preparation
- ✅ Spell learning
- ✅ Wizard spellbook management
- ✅ Ritual casting

---

## 📁 Files Created/Modified

**Created:**
- `characters/spell_management.py` - Spell management utilities
- `characters/migrations/0006_add_spellbook_field.py` - Database migration
- `test_spell_management.py` - Comprehensive test suite
- `docs/SPELL_MANAGEMENT_IMPLEMENTATION.md` - This document

**Modified:**
- `characters/models.py` - Added `in_spellbook` field
- `characters/views.py` - Added spell management endpoints
- `combat/views.py` - Added spell validation to `cast_spell`

---

## 🎉 Status: Complete!

The spell management system is **fully functional** and ready to use! 🎲✨

All core features are implemented:
- ✅ Prepared spellcasting
- ✅ Known spellcasting
- ✅ Wizard spellbook
- ✅ Ritual casting
- ✅ Combat validation

