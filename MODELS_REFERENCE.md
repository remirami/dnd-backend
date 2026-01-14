# Models Reference

**Version**: 1.0  
**ORM**: Django 5.0.2

---

## 📋 Table of Contents

1. [Characters](#-characters)
2. [Campaigns](#-campaigns)
3. [Combat](#️-combat)
4. [Bestiary](#-bestiary)
5. [Spells](#-spells)
6. [Items](#-items)
7. [Merchants](#-merchants)

---

## 🎭 Characters

### Character

**Location**: `characters/models.py`

**Description**: Represents a player character with full D&D 5e stats.

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | Primary Key | Auto-generated ID |
| `user` | ForeignKey | User, on_delete=CASCADE | Owner of the character |
| `name` | CharField | max_length=100 | Character name |
| `level` | IntegerField | default=1, validators=[1-20] | Character level |
| `character_class` | ForeignKey | CharacterClass | Character's class |
| `race` | ForeignKey | CharacterRace | Character's race |
| `background` | ForeignKey | CharacterBackground, nullable | Character background |
| `alignment` | CharField | max_length=2, choices | Alignment (LG, NG, CG, etc.) |
| `experience_points` | IntegerField | default=0 | Total XP |
| `size` | CharField | max_length=1, choices | Size (S, M) |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last update timestamp |

**Methods:**
- `proficiency_bonus()` → int - Calculate proficiency bonus based on level

**Relationships:**
- One-to-One: `CharacterStats`
- One-to-Many: `CharacterProficiency`, `CharacterFeature`, `CharacterSpell`
- Many-to-Many: `Campaign` (through `CampaignCharacter`)

---

### CharacterClass

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Class name (barbarian, bard, cleric, etc.) |
| `hit_dice` | CharField | Hit die type (d6, d8, d10, d12) |
| `primary_ability` | CharField | Primary ability (STR, DEX, INT, etc.) |
| `saving_throw_proficiencies` | CharField | Saving throw proficiencies |
| `spellcasting_ability` | CharField | Spellcasting ability (nullable) |
| `description` | TextField | Class description |

**Choices:**
```python
CLASS_CHOICES = [
    ('barbarian', 'Barbarian'),
    ('bard', 'Bard'),
    ('cleric', 'Cleric'),
    ('druid', 'Druid'),
    ('fighter', 'Fighter'),
    ('monk', 'Monk'),
    ('paladin', 'Paladin'),
    ('ranger', 'Ranger'),
    ('rogue', 'Rogue'),
    ('sorcerer', 'Sorcerer'),
    ('warlock', 'Warlock'),
    ('wizard', 'Wizard'),
]
```

---

### CharacterRace

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Race name (human, elf, dwarf, etc.) |
| `size` | CharField | Size (S, M) |
| `speed` | IntegerField | Base movement speed |
| `ability_score_increases` | CharField | ASI bonuses (e.g., "STR+2,CON+1") |
| `description` | TextField | Race description |

**Choices:**
```python
RACE_CHOICES = [
    ('human', 'Human'),
    ('elf', 'Elf'),
    ('dwarf', 'Dwarf'),
    ('halfling', 'Halfling'),
    ('dragonborn', 'Dragonborn'),
    ('gnome', 'Gnome'),
    ('half-elf', 'Half-Elf'),
    ('half-orc', 'Half-Orc'),
    ('tiefling', 'Tiefling'),
]
```

---

### CharacterStats

**Description**: Complete D&D 5e stat block for a character.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `character` | OneToOneField | - | Related character |
| `strength` | IntegerField | 10 | Strength score |
| `dexterity` | IntegerField | 10 | Dexterity score |
| `constitution` | IntegerField | 10 | Constitution score |
| `intelligence` | IntegerField | 10 | Intelligence score |
| `wisdom` | IntegerField | 10 | Wisdom score |
| `charisma` | IntegerField | 10 | Charisma score |
| `hit_points` | IntegerField | 0 | Current HP |
| `max_hit_points` | IntegerField | 0 | Maximum HP |
| `armor_class` | IntegerField | 10 | Armor class |
| `initiative` | IntegerField | 0 | Initiative bonus |
| `speed` | IntegerField | 30 | Movement speed |

**Methods:**
- `strength_modifier()` → int
- `dexterity_modifier()` → int
- `constitution_modifier()` → int
- `intelligence_modifier()` → int
- `wisdom_modifier()` → int
- `charisma_modifier()` → int

**Formula**: `(ability_score - 10) // 2`

---

### CharacterSpell

**Description**: Spells known or prepared by a character.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `character` | ForeignKey | Character who knows the spell |
| `name` | CharField | Spell name |
| `level` | IntegerField | Spell level (0-9) |
| `school` | CharField | School of magic |
| `is_prepared` | BooleanField | Whether spell is prepared |
| `source` | CharField | Source (class, item, feat) |

---

### CharacterFeature

**Description**: Class features, racial traits, and feats.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `character` | ForeignKey | Character with the feature |
| `name` | CharField | Feature name |
| `feature_type` | CharField | Type (class, racial, feat) |
| `description` | TextField | Feature description |
| `source` | CharField | Source (class level, race, etc.) |

**Choices:**
```python
FEATURE_TYPES = [
    ('class', 'Class Feature'),
    ('racial', 'Racial Feature'),
    ('background', 'Background Feature'),
    ('feat', 'Feat'),
]
```

---

## 🏰 Campaigns

### Campaign

**Location**: `campaigns/models.py`

**Description**: Roguelike gauntlet campaign with sequential encounters.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `user` | ForeignKey | - | Campaign owner |
| `name` | CharField | - | Campaign name |
| `status` | CharField | 'preparing' | Status (preparing, active, completed, failed) |
| `current_encounter_number` | IntegerField | 1 | Current encounter number |
| `gold` | IntegerField | 0 | Party gold |
| `short_rests_used` | IntegerField | 0 | Short rests used |
| `long_rests_used` | IntegerField | 0 | Long rests used |
| `long_rests_available` | IntegerField | 2 | Long rests allowed |
| `starting_level` | IntegerField | 1 | Starting level for characters |
| `difficulty` | CharField | 'normal' | Difficulty setting |
| `started_at` | DateTimeField | nullable | Campaign start time |
| `completed_at` | DateTimeField | nullable | Campaign completion time |

**Methods:**
- `start()` - Start the campaign
- `can_take_short_rest()` → bool
- `can_take_long_rest()` → bool
- `get_current_encounter()` → CampaignEncounter
- `get_alive_characters()` → QuerySet

**Relationships:**
- One-to-Many: `CampaignCharacter`, `CampaignEncounter`

---

### CampaignCharacter

**Description**: Character participating in a campaign with permadeath.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `campaign` | ForeignKey | Campaign |
| `character` | ForeignKey | Base character |
| `is_alive` | BooleanField | Alive status |
| `current_hp` | IntegerField | Current HP |
| `max_hp` | IntegerField | Maximum HP |
| `temporary_hp` | IntegerField | Temporary HP |
| `hit_dice_used` | JSONField | Hit dice spent |
| `death_saves_successes` | IntegerField | Death save successes |
| `death_saves_failures` | IntegerField | Death save failures |
| `joined_at` | DateTimeField | When joined campaign |

**Methods:**
- `take_damage(amount)` → new_hp
- `heal(amount)` → new_hp
- `spend_hit_die(dice_type=None)` → healing_amount
- `restore_all_hit_dice()`

**Unique Together**: `['campaign', 'character']`

---

### CampaignEncounter

**Description**: An encounter in the campaign progression.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `campaign` | ForeignKey | Parent campaign |
| `encounter` | ForeignKey | Base encounter data |
| `encounter_number` | IntegerField | Sequential number |
| `status` | CharField | Status (pending, active, completed, failed) |
| `combat_session` | ForeignKey | Associated combat session |
| `xp_awarded` | IntegerField | XP given |
| `gold_awarded` | IntegerField | Gold given |
| `started_at` | DateTimeField | When started |
| `completed_at` | DateTimeField | When completed |

**Methods:**
- `start()` - Begin encounter
- `complete(combat_session, rewards)` - Mark as complete
- `fail()` - Mark as failed

**Unique Together**: `['campaign', 'encounter_number']`

---

## ⚔️ Combat

### CombatSession

**Location**: `combat/models.py`

**Description**: Represents an active combat encounter.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `encounter` | ForeignKey | Related encounter (nullable) |
| `status` | CharField | Status (preparing, active, ended) |
| `current_round` | IntegerField | Current round number |
| `current_turn_index` | IntegerField | Current turn index |
| `current_participant` | ForeignKey | Participant whose turn it is |
| `started_at` | DateTimeField | Combat start time |
| `ended_at` | DateTimeField | Combat end time |

**Methods:**
- `get_current_participant()` → CombatParticipant
- `get_initiative_order()` → QuerySet
- `next_turn()` - Advance to next turn
- `remove_expired_conditions()` - Clean up conditions

**Relationships:**
- One-to-Many: `CombatParticipant`, `EnvironmentalEffect`

---

### CombatParticipant

**Description**: Character or enemy participating in combat.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `combat_session` | ForeignKey | Parent combat session |
| `participant_type` | CharField | Type (character, enemy) |
| `character` | ForeignKey | Character (if type=character) |
| `encounter_enemy` | ForeignKey | Enemy (if type=enemy) |
| `initiative` | IntegerField | Initiative roll |
| `current_hp` | IntegerField | Current HP |
| `max_hp` | IntegerField | Maximum HP |
| `armor_class` | IntegerField | AC |
| `temporary_hp` | IntegerField | Temporary HP |
| `is_active` | BooleanField | Still in combat |
| `is_concentrating` | BooleanField | Concentrating on a spell |
| `concentration_spell` | CharField | Spell being concentrated on |
| `has_reaction` | BooleanField | Reaction available |
| `conditions` | ManyToManyField | Active conditions |
| `spell_uses_remaining` | JSONField | Enemy spell slot tracking |

**Methods:**
- `take_damage(amount, damage_type, check_concentration)` → (new_hp, concentration_broken)
- `heal(amount)` → new_hp
- `get_name()` → str
- `get_ability_modifier(ability)` → int
- `check_concentration(damage)` → (success, roll, dc, modifier)
- `can_cast_enemy_spell(spell_name)` → bool - Check if enemy can cast spell
- `use_enemy_spell(spell_name)` - Decrement enemy spell uses
- `reset_enemy_spell_slots()` - Reset enemy spell slots (long rest)

**Enemy Spell Slot System:**

The `spell_uses_remaining` field tracks runtime spell usage for enemy spellcasters:

```python
# Format: {"Fireball": 2, "Power Word Kill": 0}
# Initialized from EnemySpellSlot on first cast
# Prevents infinite spell spam in combat
```

**Ordering**: `['-initiative', 'id']`

---

### ConditionApplication

**Description**: Tracks conditions applied to participants.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `participant` | ForeignKey | Affected participant |
| `condition` | ForeignKey | Condition type |
| `applied_round` | IntegerField | Round applied |
| `applied_turn` | IntegerField | Turn applied |
| `duration_type` | CharField | Type (instant, rounds, minutes) |
| `duration_rounds` | IntegerField | Duration in rounds |
| `expires_at_round` | IntegerField | Expiration round |
| `source_type` | CharField | Source (spell, ability) |
| `source_name` | CharField | Name of source |

---

## 👹 Bestiary

### Enemy

**Location**: `bestiary/models.py`

**Description**: Monster/enemy definition.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Enemy name |
| `hp` | IntegerField | Base HP |
| `ac` | IntegerField | Armor class |
| `challenge_rating` | CharField | CR (e.g., "1/4", "1", "5") |
| `size` | CharField | Size (T, S, M, L, H, G) |
| `creature_type` | CharField | Type (humanoid, dragon, etc.) |
| `alignment` | CharField | Alignment |

**Important**: Field is named `creature_type`, not `type`

**Relationships:**
- One-to-One: `EnemyStats`
- One-to-Many: `EnemyResistance`, `EnemyLanguage`, `EnemyAttack`, `EnemySpell`

**Data Source**: Automatically imported from Open5e API with complete spell data

---

### EnemyStats

**Description**: Complete stat block for enemies.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `enemy` | OneToOneField | Related enemy |
| `strength` | IntegerField | STR score |
| `dexterity` | IntegerField | DEX score |
| `constitution` | IntegerField | CON score |
| `intelligence` | IntegerField | INT score |
| `wisdom` | IntegerField | WIS score |
| `charisma` | IntegerField | CHA score |
| `proficiency_bonus` | IntegerField | Proficiency bonus |

**Methods**: Same as CharacterStats (modifier calculators)

---

### EnemySpell

**Description**: Spells that enemies can cast.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `enemy` | ForeignKey | Enemy that knows the spell |
| `name` | CharField | Spell name |
| `save_dc` | IntegerField | Spell save DC (nullable) |

**Note**: Automatically imported from Open5e spellcasting descriptions

---

### EnemySpellSlot

**Description**: Tracks spell usage limits for enemy spellcasters.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `spell` | ForeignKey | Related EnemySpell |
| `level` | IntegerField | Spell level (0 for X/day spells) |
| `uses` | IntegerField | Maximum uses (per day or combat) |

**Usage Examples:**
- At-will spells: No EnemySpellSlot record (unlimited)
- 3/day Fireball: `level=0, uses=3`
- 1st level (4 slots): `level=1, uses=4`

**Enforcement**: Tracked in combat via `CombatParticipant.spell_uses_remaining`

---

## 📚 Spells

### Spell

**Location**: `spells/models.py`

**Description**: D&D 5e spell from Open5e API.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Spell name |
| `level` | IntegerField | Spell level (0-9) |
| `school` | CharField | School of magic |
| `casting_time` | CharField | Casting time |
| `range` | CharField | Range |
| `components` | CharField | Components (V, S, M) |
| `material` | TextField | Material components |
| `duration` | CharField | Duration |
| `concentration` | BooleanField | Requires concentration |
| `ritual` | BooleanField | Can be cast as ritual |
| `description` | TextField | Full description |
| `higher_level` | TextField | Higher level effects |
| `classes` | JSONField | Classes that can cast |

---

## 🎒 Items

### Item

**Location**: `items/models.py`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Item name |
| `item_type` | CharField | Type (weapon, armor, consumable, magic) |
| `rarity` | CharField | Rarity (common, uncommon, etc.) |
| `cost_gold` | IntegerField | Cost in gold |
| `weight` | DecimalField | Weight in pounds |
| `description` | TextField | Description |
| `requires_attunement` | BooleanField | Requires attunement |

---

## 🛒 Merchants

### Merchant

**Location**: `merchants/models.py`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `campaign` | ForeignKey | Associated campaign |
| `name` | CharField | Merchant name |
| `merchant_type` | CharField | Type (general, magic, armor) |
| `discovered` | BooleanField | Has been discovered |
| `depth` | IntegerField | Gauntlet depth when discovered |

**Relationships:**
- One-to-Many: `MerchantInventory`

---

### MerchantInventory

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `merchant` | ForeignKey | Parent merchant |
| `item` | ForeignKey | Item for sale |
| `quantity` | IntegerField | Quantity available |
| `price_modifier` | DecimalField | Price adjustment multiplier |

---

## 🔗 Relationships Diagram

```
User
 ├── Character (1:N)
 │    ├── CharacterStats (1:1)
 │    ├── CharacterSpell (1:N)
 │    ├── CharacterFeature (1:N)
 │    └── CharacterProficiency (1:N)
 │
 └── Campaign (1:N)
      ├── CampaignCharacter (1:N) → Character
      ├── CampaignEncounter (1:N) → Encounter
      │    └── CombatSession (1:1)
      │         └── CombatParticipant (1:N)
      │              ├── Character (N:1)
      │              └── EncounterEnemy (N:1) → Enemy
      │
      └── Merchant (1:N)
           └── MerchantInventory (1:N) → Item
```

---

**Need API examples?** Check the [API Reference](API_REFERENCE.md).
