# Environmental Effects System - Implementation Complete ✅

## Overview

A comprehensive environmental effects system for D&D 5e combat, including:
- **Difficult Terrain** - Movement cost multipliers
- **Cover** - AC and DEX save bonuses
- **Lighting** - Attack and perception modifiers
- **Weather** - Ranged attack and visibility modifiers
- **Hazards** - Area damage effects

---

## ✅ What Was Implemented

### 1. Database Models (`combat/models.py`)

**EnvironmentalEffect Model:**
- Tracks all environmental effects in combat
- Supports terrain, cover, lighting, weather, and hazards
- Area-based effects (cover, lighting, hazards) with coordinates
- Weather applies to entire combat session

**ParticipantPosition Model:**
- Tracks participant positions (x, y, z coordinates)
- Stores current environmental effects at position
- Methods for distance calculation and area checking

### 2. Environmental Effects Utilities (`combat/environmental_effects.py`)

**Difficult Terrain:**
- 7 terrain types (rubble, mud, snow, ice, swamp, quicksand, thick vegetation)
- Movement cost multipliers (2x for most, 3x for quicksand)
- Integration with weather effects

**Cover:**
- Half cover (+2 AC, +2 DEX saves)
- Three-quarters cover (+5 AC, +5 DEX saves)
- Full cover (cannot be targeted)

**Lighting:**
- Bright light (normal)
- Dim light (disadvantage on Perception)
- Darkness (disadvantage on attacks, blocks vision)
- Magical darkness (blocks darkvision)

**Weather:**
- Clear, light rain, heavy rain, fog, heavy fog, snow, strong wind
- Effects on visibility, movement, and ranged attacks

**Hazards:**
- Lava, acid, poison gas, spike pit, electrified water
- Damage per round with saving throws
- Condition application (e.g., poisoned)

### 3. API Endpoints (`combat/views.py`)

#### `GET/POST /api/combat/sessions/{id}/environmental_effects/`
Get or add environmental effects to combat.

**GET Response:**
```json
{
  "environmental_effects": [...],
  "summary": {
    "terrain": {...},
    "cover": {...},
    "lighting": {...},
    "weather": {...},
    "hazards": [...]
  }
}
```

**POST Request:**
```json
{
  "effect_type": "terrain",
  "terrain_type": "rubble",
  "description": "Rubble covers the battlefield"
}
```

#### `POST /api/combat/sessions/{id}/set_participant_position/`
Set participant position and update environmental effects.

**Request:**
```json
{
  "participant_id": 1,
  "x": 10,
  "y": 10,
  "z": 0
}
```

#### `POST /api/combat/participants/{id}/move/`
Move participant considering difficult terrain.

**Request:**
```json
{
  "distance": 30,
  "x": 15,
  "y": 15
}
```

**Response:**
```json
{
  "message": "Test Fighter moved 30 feet (cost: 60 feet)",
  "movement_used": 60,
  "movement_remaining": 0,
  "terrain_multiplier": 2.0,
  "position": {...}
}
```

#### `POST /api/combat/participants/{id}/apply_hazard_damage/`
Apply damage from hazards at participant's position.

### 4. Combat Integration

**Attack Calculations:**
- Cover bonuses added to target AC
- Full cover prevents targeting
- Lighting affects attack rolls (disadvantage in darkness)
- Weather affects ranged attacks (disadvantage in strong wind)

**Movement:**
- Difficult terrain doubles/triples movement cost
- Weather can reduce movement speed
- Movement endpoint validates available movement

**AC Calculation:**
- `calculate_effective_ac()` now accepts `cover_bonus` parameter
- Cover bonuses stack with armor and shield

---

## 📊 Environmental Effects Reference

### Difficult Terrain

| Terrain | Movement Cost | Description |
|---------|--------------|-------------|
| Rubble | 2x | Debris and rubble |
| Mud | 2x | Muddy ground |
| Snow | 2x | Deep snow |
| Ice | 2x | Icy surface (difficult balance) |
| Swamp | 2x | Swampy ground |
| Thick Vegetation | 2x | Dense vegetation |
| Quicksand | 3x | Quicksand |

### Cover

| Cover Type | AC Bonus | DEX Save Bonus | Effect |
|------------|----------|----------------|--------|
| Half | +2 | +2 | Partial protection |
| Three-Quarters | +5 | +5 | Strong protection |
| Full | N/A | N/A | Cannot be targeted |

### Lighting

| Lighting | Attack Modifier | Perception | Darkvision |
|----------|----------------|------------|------------|
| Bright Light | 0 | Normal | N/A |
| Dim Light | 0 | Disadvantage | N/A |
| Darkness | Disadvantage | Disadvantage | Can see |
| Magical Darkness | Disadvantage | Disadvantage | Cannot see |

### Weather

| Weather | Visibility | Movement | Ranged Attacks |
|---------|------------|----------|----------------|
| Clear | Normal | Normal | Normal |
| Light Rain | -1 | Normal | Normal |
| Heavy Rain | -5 | Normal | -2 |
| Fog | Disadvantage (20ft) | Normal | Normal |
| Heavy Fog | Disadvantage (10ft) | Normal | Disadvantage |
| Snow | -2 | Half | -2 |
| Strong Wind | Normal | Normal | Disadvantage |

### Hazards

| Hazard | Damage | Type | Save | DC |
|--------|--------|------|------|-----|
| Lava | 6d10 | Fire | DEX | 15 |
| Acid | 4d6 | Acid | DEX | 12 |
| Poison Gas | 2d6 | Poison | CON | 13 |
| Spike Pit | 2d6 | Piercing | DEX | 15 |
| Electrified Water | 3d6 | Lightning | CON | 12 |

---

## 🎯 Usage Examples

### Add Difficult Terrain
```python
POST /api/combat/sessions/1/environmental_effects/
{
  "effect_type": "terrain",
  "terrain_type": "rubble",
  "description": "Rubble from collapsed wall"
}
```

### Add Cover
```python
POST /api/combat/sessions/1/environmental_effects/
{
  "effect_type": "cover",
  "cover_type": "half",
  "cover_area_x": 10,
  "cover_area_y": 10,
  "cover_area_radius": 5
}
```

### Set Weather
```python
POST /api/combat/sessions/1/environmental_effects/
{
  "effect_type": "weather",
  "weather_type": "heavy_rain",
  "description": "Torrential downpour"
}
```

### Move Participant
```python
POST /api/combat/participants/1/move/
{
  "distance": 30,
  "x": 15,
  "y": 15
}
// Returns movement cost considering terrain
```

### Attack with Environmental Effects
```python
POST /api/combat/sessions/1/attack/
{
  "attacker_id": 1,
  "target_id": 2
}
// Automatically applies:
// - Cover bonuses to target AC
// - Lighting modifiers to attack
// - Weather modifiers for ranged attacks
```

---

## ✅ Test Results

All tests pass:
- ✅ Difficult terrain movement costs
- ✅ Cover AC bonuses
- ✅ Lighting effects
- ✅ Weather effects
- ✅ Hazard damage
- ✅ Integration with combat

---

## 📁 Files Created/Modified

**Created:**
- `combat/environmental_effects.py` - Environmental effects utilities
- `combat/migrations/0005_add_environmental_effects.py` - Database migration
- `test_environmental_effects.py` - Test suite
- `docs/ENVIRONMENTAL_EFFECTS_IMPLEMENTATION.md` - This document

**Modified:**
- `combat/models.py` - Added EnvironmentalEffect and ParticipantPosition models
- `combat/views.py` - Added environmental effects endpoints, integrated into attacks
- `combat/serializers.py` - Added serializers for environmental effects

---

## 🎉 Status: Complete!

The environmental effects system is **fully functional** and ready to use! 🎲⚔️

All features are implemented:
- ✅ Difficult terrain
- ✅ Cover system
- ✅ Lighting conditions
- ✅ Weather effects
- ✅ Hazards
- ✅ Position tracking
- ✅ Combat integration

