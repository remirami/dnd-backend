# Roguelite Recruitment System Implementation

This document summarizes the implementation of the missing roguelite features: Solo/Party Mode and Recruitment System.

## ✅ Implemented Features

### 1. Solo vs Party Start Mode

**Campaign Model Changes:**
- Added `start_mode` field with choices: 'solo' or 'party'
- Added `starting_party_size` field (1-4 characters)
- Updated `start()` method to enforce solo mode restrictions:
  - Solo mode: Requires exactly 1 character at start
  - Party mode: Requires 1-4 characters at start

**Location:** `campaigns/models.py:30-48`

### 2. RecruitableCharacter Model

**New Model:**
- Template for characters that can be recruited
- Fields:
  - `name`, `character_class`, `race`, `background`
  - `personality_trait`, `recruitment_description`
  - `starting_stats` (JSON field for stat overrides)
  - `starting_equipment` (JSON field for item IDs)
  - `rarity` (common, uncommon, rare, legendary)

**Location:** `campaigns/models.py:533-560`

### 3. RecruitmentRoom Model

**New Model:**
- Represents a recruitment opportunity in a campaign
- Fields:
  - `campaign`, `encounter_number`
  - `available_recruits` (ManyToMany to RecruitableCharacter)
  - `discovered`, `recruit_selected`
  - `discovered_at`

**Location:** `campaigns/models.py:563-603`

### 4. RecruitmentGenerator Utility Class

**Features:**
- `generate_recruitment_room()` - Creates recruitment rooms with weighted rarity based on campaign progress
- `recruit_character()` - Recruits a character from template, creates Character and CharacterStats, adds to campaign
- Level scaling: Recruits join at average party level (not starting level)
- Proper HP calculation based on class hit dice and level
- Rarity weights:
  - Early game: Mostly common/uncommon
  - Mid game: Mix of all rarities
  - Late game: Higher chance of rare/legendary

**Location:** `campaigns/utils.py:332-520`

### 5. API Endpoints

**New Endpoints:**
- `GET /api/campaigns/{id}/recruitment_rooms/` - List all recruitment rooms
- `POST /api/campaigns/{id}/discover_recruitment_room/` - Manually discover a recruitment room
- `GET /api/campaigns/{id}/recruitment_room_available/` - Get available recruits for a room
- `POST /api/campaigns/{id}/recruit_character/` - Recruit a character from a room

**Auto-Generation:**
- Recruitment rooms automatically generated after encounters in solo mode
- Appears every 4th encounter or 15% random chance after encounter 3
- Only generated if party size < 4

**Location:** `campaigns/views.py:724-862`

### 6. Serializers

**New Serializers:**
- `RecruitableCharacterSerializer` - Includes class, race, background details
- `RecruitmentRoomSerializer` - Includes available recruits and selected recruit
- Updated `CampaignSerializer` - Includes `recruitment_rooms` field

**Location:** `campaigns/serializers.py:57-75`

### 7. Admin Interface

**Updates:**
- Added `RecruitableCharacterAdmin` - Manage recruit templates
- Added `RecruitmentRoomAdmin` - View recruitment rooms
- Updated `CampaignAdmin` - Added start_mode and starting_level to list display and fieldsets

**Location:** `campaigns/admin.py`

### 8. Database Migration

**Migration:** `0004_campaign_start_mode_campaign_starting_party_size_and_more.py`
- Adds `start_mode` and `starting_party_size` fields to Campaign
- Creates `RecruitableCharacter` model
- Creates `RecruitmentRoom` model

## 🎮 Usage

### Creating a Solo Campaign

```python
# Create campaign with solo mode
campaign = Campaign.objects.create(
    name="Solo Adventure",
    start_mode='solo',
    starting_level=3
)

# Add exactly 1 character
campaign.add_character(character_id=1)

# Start campaign
campaign.start()  # Will enforce solo mode restrictions
```

### Recruiting a Character

```python
# After an encounter completes, a recruitment room may be auto-generated
# Or manually discover one:
POST /api/campaigns/{id}/discover_recruitment_room/
{
    "encounter_number": 3
}

# View available recruits:
GET /api/campaigns/{id}/recruitment_room_available/?room_id=1

# Recruit a character:
POST /api/campaigns/{id}/recruit_character/
{
    "room_id": 1,
    "recruit_template_id": 5
}
```

### Creating Recruitable Character Templates

```python
# Via admin or API
recruit = RecruitableCharacter.objects.create(
    name="Elara the Wizard",
    character_class=fighter_class,
    race=elf_race,
    background=sage_bg,
    recruitment_description="A scholarly mage seeking adventure",
    personality_trait="Curious and bookish",
    rarity='uncommon',
    starting_stats={
        'intelligence': 16,
        'dexterity': 14,
        'constitution': 12
    }
)
```

## 🔄 Game Flow

1. **Campaign Creation:**
   - Choose start_mode: 'solo' or 'party'
   - Set starting_level: 1, 3, or 5
   - Add characters (1 for solo, 1-4 for party)

2. **Solo Mode Play:**
   - Start with 1 character
   - After encounters, recruitment rooms may appear
   - Recruit up to 3 more characters (max 4 total)
   - Recruits join at current party level

3. **Recruitment Room:**
   - Appears every 4th encounter or randomly
   - Offers 2-3 recruit options
   - Rarity varies by campaign progress
   - Player selects one recruit (or skips)

## 📝 Notes

- Recruitment is only available in solo mode
- Party size is limited to 4 characters maximum
- Recruits scale to current party level, not starting level
- HP is calculated properly based on class hit dice and level
- Character stats can be customized via template's `starting_stats` field
- Rarity system affects when recruits appear but doesn't affect stats (can be enhanced later)

## 🚀 Future Enhancements

- Better stat generation for recruits (assign based on class)
- Rarity affecting starting equipment or stats
- Special abilities for legendary recruits
- Recruitment cost (gold or other resources)
- Recruit level scaling options
- More complex recruitment requirements

