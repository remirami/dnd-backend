# API Reference

**Version**: 1.0  
**Base URL**: `/api/`  
**Authentication**: JWT Token (Bearer)

---

## 🔐 Authentication

All endpoints except public data require JWT authentication.

### Endpoints

#### Register User
```http
POST /api/auth/register/
```

**Request Body:**
```json
{
  "username": "player1",
  "email": "player1@example.com",
  "password": "secure_password"
}
```

**Response:** `201 Created`
```json
{
  "user": {
    "id": 1,
    "username": "player1",
    "email": "player1@example.com"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Login
```http
POST /api/auth/login/
```

**Request Body:**
```json
{
  "username": "player1",
  "password": "secure_password"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Refresh Token
```http
POST /api/auth/token/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 🎭 Characters

### List Characters
```http
GET /api/characters/
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `level` - Filter by level
- `character_class` - Filter by class name
- `search` - Search by name

**Response:** `200 OK`
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "name": "Thorin Ironforge",
      "level": 5,
      "character_class": "fighter",
      "race": "dwarf",
      "alignment": "LG",
      "experience_points": 6500
    }
  ]
}
```

### Create Character
```http
POST /api/characters/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Elara Moonwhisper",
  "character_class": 1,
  "race": 2,
  "background": 1,
  "alignment": "NG",
  "level": 1
}
```

### Get Character Details
```http
GET /api/characters/{id}/
Authorization: Bearer {access_token}
```

### Update Character
```http
PATCH /api/characters/{id}/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "level": 6,
  "experience_points": 14000
}
```

### Delete Character
```http
DELETE /api/characters/{id}/
Authorization: Bearer {access_token}
```

---

## ⚔️ Combat

### Combat Sessions

#### Create Combat Session
```http
POST /api/combat/sessions/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "encounter": 5,
  "name": "Goblin Ambush"
}
```

#### Start Combat
```http
POST /api/combat/sessions/{id}/start/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "message": "Combat started",
  "session": {
    "id": 1,
    "status": "active",
    "current_round": 1
  }
}
```

#### Add Participant
```http
POST /api/combat/sessions/{id}/add_participant/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "participant_type": "character",
  "character_id": 1,
  "initiative": 15
}
```

#### Roll Initiative
```http
POST /api/combat/sessions/{id}/roll_initiative/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "message": "Initiative rolled for all participants",
  "initiative_order": [
    {"name": "Thorin", "initiative": 18},
    {"name": "Goblin 1", "initiative": 12}
  ]
}
```

#### Next Turn
```http
POST /api/combat/sessions/{id}/next_turn/
Authorization: Bearer {access_token}
```

#### Attack
```http
POST /api/combat/sessions/{id}/attack/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "attacker_id": 1,
  "target_id": 2,
  "weapon": "Longsword",
  "attack_bonus": 7
}
```

**Response:** `200 OK`
```json
{
  "hit": true,
  "critical": false,
  "attack_roll": 15,
  "target_ac": 13,
  "damage": 8,
  "message": "Thorin hits Goblin 1 for 8 damage"
}
```

#### Cast Spell
```http
POST /api/combat/sessions/{id}/cast_spell/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "caster_id": 1,
  "spell_name": "Fireball",
  "spell_level": 3,
  "target_ids": [2, 3, 4],
  "save_dc": 15
}
```

#### Saving Throw
```http
POST /api/combat/sessions/{id}/saving_throw/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "participant_id": 2,
  "ability": "DEX",
  "dc": 15,
  "advantage": false
}
```

#### Check Concentration
```http
POST /api/combat/sessions/{id}/check_concentration/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "participant_id": 1,
  "damage_taken": 10
}
```

#### End Combat
```http
POST /api/combat/sessions/{id}/end/
Authorization: Bearer {access_token}
```

#### Get Combat Stats
```http
GET /api/combat/sessions/{id}/stats/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "total_rounds": 5,
  "duration_seconds": 120,
  "total_damage_dealt": 156,
  "critical_hits": 2,
  "participants": [...]
}
```

### Combat Participants

#### Damage Participant
```http
POST /api/combat/participants/{id}/damage/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "amount": 15,
  "damage_type": "slashing"
}
```

**Response:** `200 OK`
```json
{
  "message": "Thorin took 15 damage",
  "current_hp": 30,
  "concentration_broken": false
}
```

#### Heal Participant
```http
POST /api/combat/participants/{id}/heal/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "amount": 8
}
```

#### Add Condition
```http
POST /api/combat/participants/{id}/add_condition/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "condition_id": 1,
  "duration_type": "rounds",
  "duration_rounds": 3
}
```

#### Remove Condition
```http
POST /api/combat/participants/{id}/remove_condition/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "condition_id": 1
}
```

#### Start Concentration
```http
POST /api/combat/participants/{id}/start_concentration/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "spell": "Bless"
}
```

#### End Concentration
```http
POST /api/combat/participants/{id}/end_concentration/
Authorization: Bearer {access_token}
```

---

## 🏰 Campaigns

### List Campaigns
```http
GET /api/campaigns/
Authorization: Bearer {access_token}
```

### Create Campaign
```http
POST /api/campaigns/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "The Gauntlet of Doom",
  "starting_level": 3,
  "difficulty": "hard"
}
```

### Start Campaign
```http
POST /api/campaigns/{id}/start/
Authorization: Bearer {access_token}
```

### Add Character to Campaign
```http
POST /api/campaigns/{id}/add_character/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "character_id": 1
}
```

### Remove Character from Campaign
```http
POST /api/campaigns/{id}/remove_character/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "character_id": 1
}
```

### Short Rest
```http
POST /api/campaigns/{id}/short_rest/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "character_ids": [1, 2],
  "hit_dice_to_spend": {
    "1": {"d10": 1},
    "2": {"d8": 2}
  }
}
```

### Long Rest
```http
POST /api/campaigns/{id}/long_rest/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "message": "Party took a long rest",
  "characters_healed": [
    {"id": 1, "name": "Thorin", "hp_restored": 15}
  ]
}
```

### Claim Treasure
```http
POST /api/campaigns/{id}/claim_treasure/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "reward_id": 5,
  "character_id": 1
}
```

### Get Party Status
```http
GET /api/campaigns/{id}/party_status/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "campaign": "The Gauntlet of Doom",
  "status": "active",
  "current_encounter": 3,
  "gold": 450,
  "party": [
    {
      "name": "Thorin",
      "level": 5,
      "hp": "30/45",
      "is_alive": true
    }
  ]
}
```

---

## 📚 Spells

### List Spells
```http
GET /api/spells/
```

**Query Parameters:**
- `level` - Filter by spell level (0-9)
- `school` - Filter by school (evocation, abjuration, etc.)
- `concentration` - Filter by concentration requirement (true/false)
- `ritual` - Filter by ritual casting (true/false)
- `class_name` - Filter by class (wizard, cleric, etc.)
- `search` - Search by name

**Response:** `200 OK`
```json
{
  "count": 1400,
  "results": [
    {
      "id": 1,
      "name": "Fireball",
      "level": 3,
      "school": "evocation",
      "casting_time": "1 action",
      "range": "150 feet",
      "components": "V, S, M",
      "duration": "Instantaneous",
      "concentration": false,
      "ritual": false,
      "classes": ["sorcerer", "wizard"]
    }
  ]
}
```

### Get Spell Details
```http
GET /api/spells/{id}/
```

---

## 🛒 Merchants

### List Merchants
```http
GET /api/merchants/
Authorization: Bearer {access_token}
```

### Discover Merchant
```http
POST /api/merchants/discover/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "campaign_id": 1,
  "depth": 3
}
```

### Purchase Item
```http
POST /api/merchants/{id}/purchase/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "item_id": 5,
  "character_id": 1,
  "quantity": 1
}
```

---

## 👹 Bestiary

### List Enemies
```http
GET /api/enemies/
```

**Query Parameters:**
- `cr` - Filter by challenge rating
- `creature_type` - Filter by type (humanoid, dragon, etc.)
- `search` - Search by name

**Response:** `200 OK`
```json
{
  "count": 200,
  "results": [
    {
      "id": 1,
      "name": "Goblin",
      "hp": 7,
      "ac": 15,
      "challenge_rating": "1/4",
      "creature_type": "humanoid",
      "size": "S"
    }
  ]
}
```

### Import Monsters
```http
POST /api/enemies/import/
Authorization: Bearer {access_token}
```

---

## 🎒 Items

### List Items
```http
GET /api/items/
```

### List Weapons
```http
GET /api/weapons/
```

### List Armor
```http
GET /api/armor/
```

### List Magic Items
```http
GET /api/magic-items/
```

**Query Parameters:**
- `rarity` - Filter by rarity (common, uncommon, rare, very rare, legendary)
- `requires_attunement` - Filter by attunement requirement (true/false)

---

## 📖 Reference Data

### Character Classes
```http
GET /api/character-classes/
```

### Character Races
```http
GET /api/character-races/
```

### Character Backgrounds
```http
GET /api/character-backgrounds/
```

---

## 🔒 Authentication Headers

All authenticated requests require:
```http
Authorization: Bearer {access_token}
```

## 📝 Common Response Codes

- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Deletion successful
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Server Error` - Internal server error

---

**Need more details?** Check the [Models Reference](MODELS_REFERENCE.md) for data schemas.
