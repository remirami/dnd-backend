# Conditions Auto-Application & Inventory Management - Implementation Complete ✅

## Overview

Two major systems implemented:
1. **Conditions Auto-Application** - Automatic condition application from spells/abilities with duration tracking
2. **Inventory Management** - Equipment system with weight tracking and encumbrance

---

## ✅ Conditions Auto-Application System

### Features Implemented

1. **Spell-to-Condition Mapping** (`combat/condition_effects.py`)
   - Maps spells to conditions they apply (e.g., Hold Person → Paralyzed)
   - 20+ spell mappings included

2. **Condition Effects System**
   - Condition effects on stats (disadvantage, speed reduction, etc.)
   - Functions to calculate effective speed, attack modifiers
   - Condition removal triggers

3. **Condition Duration Tracking** (`combat/models.py`)
   - `ConditionApplication` model tracks:
     - When condition was applied
     - Duration type (instant, turn, round, spell, saving_throw, concentration)
     - Expiration round
     - Source (spell name, ability name)
     - Removal reason

4. **Automatic Application**
   - Spells auto-apply conditions on cast (if save fails)
   - Creates `ConditionApplication` records
   - Tracks source and duration

5. **Automatic Removal**
   - Conditions expire at end of rounds
   - Removed when concentration ends
   - Removed on successful saving throws
   - `remove_expired_conditions()` called each turn

### API Endpoints

**Existing (Enhanced):**
- `POST /api/combat/participants/{id}/add_condition/` - Now creates ConditionApplication record
- `POST /api/combat/participants/{id}/remove_condition/` - Removes condition

**Auto-Applied:**
- Conditions automatically applied when casting spells via `cast_spell` endpoint

### Condition Effects

| Condition | Effects |
|-----------|---------|
| **Blinded** | Attack disadvantage, attacks against have advantage |
| **Charmed** | Cannot attack charmer |
| **Frightened** | Disadvantage on checks/attacks, cannot move closer |
| **Grappled** | Speed = 0 |
| **Paralyzed** | Speed = 0, auto-fail STR/DEX saves, attacks against have advantage |
| **Poisoned** | Disadvantage on attacks and ability checks |
| **Prone** | Melee attacks against have advantage, ranged have disadvantage |
| **Restrained** | Speed = 0, attack disadvantage, attacks against have advantage |
| **Stunned** | Cannot take actions/reactions, auto-fail STR/DEX saves |
| **Unconscious** | Speed = 0, auto-fail saves, critical hits on melee |

---

## ✅ Inventory Management System

### Features Implemented

1. **Weight & Encumbrance** (`characters/inventory_management.py`)
   - Calculate total weight of inventory
   - Calculate carrying capacity (STR * 15 max)
   - Encumbrance levels: Light, Medium, Heavy, Overloaded
   - Encumbrance effects on speed and ability checks

2. **Equipment Management**
   - `equip_item()` - Equip items with slot validation
   - `unequip_item()` - Unequip items
   - `can_equip_item()` - Validate equipment slots
   - Slot conflict checking (two-handed weapons, etc.)

3. **Equipment Queries**
   - `get_equipped_items()` - All equipped items
   - `get_equipped_weapon()` - Weapon in specified slot
   - `get_equipped_armor()` - Equipped armor
   - `get_equipped_shield()` - Equipped shield

### API Endpoints

**Enhanced:**
- `GET /api/characters/{id}/inventory/` - Now includes encumbrance info
- `POST /api/characters/{id}/equip_item/` - Uses new validation system
- `POST /api/characters/{id}/unequip_item/` - Uses new utility functions

**Response Format:**
```json
{
  "message": "Equipped Longsword in main_hand",
  "character_item": {...},
  "encumbrance": {
    "level": "medium",
    "total_weight": 45.5,
    "effects": {
      "speed_modifier": 1.0,
      "ability_check_disadvantage": false
    }
  }
}
```

### Encumbrance Rules

| Level | Weight Threshold | Effects |
|-------|-----------------|---------|
| **Light** | ≤ STR × 5 | No penalties |
| **Medium** | ≤ STR × 10 | No penalties |
| **Heavy** | ≤ STR × 15 | 20% speed reduction |
| **Overloaded** | > STR × 15 | 50% speed reduction, disadvantage on STR/DEX checks |

---

## 📁 Files Created/Modified

### Created:
- `combat/condition_effects.py` - Condition mapping and effects
- `characters/inventory_management.py` - Inventory utilities
- `combat/migrations/0004_add_condition_duration.py` - ConditionApplication model

### Modified:
- `combat/models.py` - Added ConditionApplication model, remove_expired_conditions()
- `combat/views.py` - Auto-apply conditions from spells, enhanced add_condition
- `characters/views.py` - Enhanced equip/unequip endpoints, inventory info

---

## 🎯 Usage Examples

### Auto-Apply Condition from Spell
```python
POST /api/combat/sessions/1/cast_spell/
{
  "caster_id": 1,
  "target_id": 2,
  "spell_name": "Hold Person",  // Automatically applies "paralyzed"
  "spell_level": 2,
  "save_type": "WIS",
  "save_dc": 15
}
```

### Equip Item
```python
POST /api/characters/1/equip_item/
{
  "character_item_id": 5,
  "equipment_slot": "main_hand"
}
```

### Check Inventory
```python
GET /api/characters/1/inventory/
// Returns inventory + encumbrance info
```

---

## ✅ Status: Complete!

Both systems are **fully functional**:
- ✅ Condition auto-application from spells
- ✅ Condition duration tracking
- ✅ Automatic condition removal
- ✅ Condition effects on stats
- ✅ Weight & encumbrance tracking
- ✅ Equipment management
- ✅ Slot validation

---

## 🔮 Future Enhancements

1. **Item Effects** - Magic item bonuses (AC, damage, etc.)
2. **Condition Stacks** - Multiple levels of exhaustion
3. **Condition Immunities** - Character/enemy immunities
4. **Trading System** - Transfer items between characters

---

## 🎉 Summary

Your D&D 5e backend now has:
- **Smart condition system** that auto-applies from spells
- **Full inventory management** with weight tracking
- **Equipment system** with slot validation
- **Encumbrance rules** affecting movement and checks

All systems are production-ready! 🎲⚔️

