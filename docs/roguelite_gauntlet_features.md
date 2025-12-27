# Roguelite/Roguelike Gauntlet Features

## Overview

This document outlines features to transform the campaign gauntlet system into a true roguelite/roguelike experience with progression, treasure, party management, and character advancement.

---

## 1. Starting Level Selection

### Concept
Players choose their starting level at campaign creation, affecting initial difficulty and progression.

### Implementation

**Campaign Model Changes:**
```python
class Campaign(models.Model):
    # ... existing fields ...
    
    # Starting level (affects all characters)
    starting_level = models.IntegerField(
        default=1,
        choices=[(1, 'Level 1'), (3, 'Level 3'), (5, 'Level 5')],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
```

**Character Initialization:**
- Characters join at campaign's `starting_level`
- Initial HP, spell slots, proficiencies calculated for that level
- Starting equipment/gold based on level

**Starting Level Benefits:**

| Level | Benefits |
|-------|----------|
| **Level 1** | Classic start, full progression, more XP to gain |
| **Level 3** | Skip early levels, subclass unlocked, faster start |
| **Level 5** | Extra Attack/3rd level spells, strong start, less XP gain |

---

## 2. Experience Points & Leveling System

### Concept
Characters gain XP from defeating enemies. At XP thresholds, they level up, gaining new abilities and stats.

### XP Sources

**Defeating Enemies:**
```python
def calculate_xp_reward(enemy, character_level):
    """Calculate XP based on enemy CR and character level"""
    base_xp = CR_TO_XP[enemy.challenge_rating]
    
    # Level difference modifier
    level_diff = enemy.effective_level - character_level
    
    if level_diff > 0:
        # Higher CR = more XP
        multiplier = 1.0 + (level_diff * 0.1)
    elif level_diff < 0:
        # Lower CR = less XP (but never zero)
        multiplier = max(0.5, 1.0 + (level_diff * 0.05))
    else:
        multiplier = 1.0
    
    return int(base_xp * multiplier)
```

**Other XP Sources:**
- Completing encounters (bonus XP)
- Treasure rooms discovered (small XP bonus)
- Bonus objectives (optional)

### Level-Up System

**XP Thresholds:**
```python
XP_THRESHOLDS = {
    1: 0,      # Starting level
    2: 300,    # +300 XP
    3: 900,    # +600 XP (total)
    4: 2700,   # +1800 XP (total)
    5: 6500,   # +3800 XP (total)
    6: 14000,  # +7500 XP (total)
    7: 23000,  # +9000 XP (total)
    8: 34000,  # +11000 XP (total)
    9: 48000,  # +14000 XP (total)
    10: 64000, # +16000 XP (total)
    # ... up to level 20
}
```

**Level-Up Benefits:**
- Increased Max HP (rolled or average)
- New spell slots (if caster)
- Class features (at appropriate levels)
- Ability Score Improvement (at levels 4, 8, 12, 16, 19)
- Proficiency bonus increase

**Implementation:**
```python
class CharacterXP(models.Model):
    """Tracks XP and leveling for characters in campaign"""
    campaign_character = models.OneToOneField(
        CampaignCharacter,
        related_name='xp_tracking'
    )
    current_xp = models.IntegerField(default=0)
    total_xp_gained = models.IntegerField(default=0)
    level_ups_gained = models.IntegerField(default=0)  # Levels gained during campaign
    
    def add_xp(self, amount):
        """Add XP and check for level up"""
        self.current_xp += amount
        self.total_xp_gained += amount
        
        old_level = self.campaign_character.character.level
        new_level = self._calculate_level(self.current_xp)
        
        if new_level > old_level:
            self._level_up(old_level, new_level)
        
        self.save()
    
    def _level_up(self, old_level, new_level):
        """Handle level up"""
        character = self.campaign_character.character
        character.level = new_level
        
        # Increase max HP
        hp_increase = self._roll_hit_points(new_level, character.character_class)
        self.campaign_character.max_hp += hp_increase
        self.campaign_character.current_hp += hp_increase  # Full heal on level up
        
        # Update spell slots
        self._update_spell_slots(character, new_level)
        
        # Apply class features
        self._apply_class_features(character, old_level, new_level)
        
        character.save()
        self.campaign_character.save()
        self.level_ups_gained += (new_level - old_level)
```

---

## 3. Treasure Rooms & Items

### Concept
Special rooms between encounters that reward players with items, gold, or other benefits.

### Treasure Room Types

**1. Equipment Treasure Room:**
- Random weapons, armor, or accessories
- Quality varies (common → rare → legendary)
- May include cursed items (high risk, high reward)

**2. Consumables Treasure Room:**
- Healing potions
- Scrolls (one-time spells)
- Buff items (temporary bonuses)

**3. Gold Treasure Room:**
- Large gold reward
- Can be saved for shop encounters (if implemented)

**4. Magical Item Room:**
- Guaranteed magic item
- Scales with encounter number
- May include attunement items

**5. Mystery Room (Risk/Reward):**
- Random effect (good or bad)
- Could be: XP boost, temporary buff, trap, curse
- Adds uncertainty

### Implementation

**Model:**
```python
class TreasureRoom(models.Model):
    """A treasure room in the campaign"""
    ROOM_TYPES = [
        ('equipment', 'Equipment Room'),
        ('consumables', 'Consumables Room'),
        ('gold', 'Gold Room'),
        ('magical', 'Magic Item Room'),
        ('mystery', 'Mystery Room'),
        ('shop', 'Shop Room'),  # Optional: buy items
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='treasure_rooms')
    encounter_number = models.IntegerField()  # After which encounter
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    discovered = models.BooleanField(default=False)
    loot_distributed = models.BooleanField(default=False)
    
    # Loot stored as JSON
    rewards = models.JSONField(default=dict)  # {"items": [1,2,3], "gold": 100, "xp": 50}
    
    discovered_at = models.DateTimeField(blank=True, null=True)

class TreasureRoomReward(models.Model):
    """Individual rewards in a treasure room"""
    treasure_room = models.ForeignKey(TreasureRoom, on_delete=models.CASCADE, related_name='rewards')
    item = models.ForeignKey('items.Item', on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    gold_amount = models.IntegerField(default=0)
    xp_bonus = models.IntegerField(default=0)
    claimed_by = models.ForeignKey(
        CampaignCharacter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    claimed_at = models.DateTimeField(blank=True, null=True)
```

**Treasure Generation:**
```python
class TreasureGenerator:
    def generate_treasure_room(self, campaign, encounter_number):
        """Generate appropriate treasure for this point in campaign"""
        # Determine room type (weighted random)
        room_type = self._select_room_type(encounter_number)
        
        # Calculate treasure value based on progress
        treasure_value = self._calculate_treasure_value(campaign, encounter_number)
        
        if room_type == 'equipment':
            items = self._generate_equipment(treasure_value)
        elif room_type == 'magical':
            items = [self._generate_magic_item(treasure_value)]
        elif room_type == 'gold':
            gold = treasure_value * 10  # Convert to gold
        # ... etc
        
        return TreasureRoom.objects.create(
            campaign=campaign,
            encounter_number=encounter_number,
            room_type=room_type,
            rewards={
                'items': [item.id for item in items],
                'gold': gold,
                'xp': treasure_value // 2
            }
        )
    
    def _calculate_treasure_value(self, campaign, encounter_number):
        """Calculate appropriate treasure value"""
        base_value = encounter_number * 100
        level_multiplier = campaign.starting_level * 50
        return base_value + level_multiplier
```

**Treasure Room Placement:**
- Every 2-3 encounters (guaranteed treasure)
- Random chance after each encounter (10-20%)
- Before boss encounters (guaranteed powerful item)

---

## 4. Solo vs Party Start

### Concept
Players choose to start alone or with a party. Solo players can recruit companions during the gauntlet.

### Implementation

**Campaign Model:**
```python
class Campaign(models.Model):
    # ... existing fields ...
    
    START_MODE_CHOICES = [
        ('solo', 'Solo - Start alone, recruit during run'),
        ('party', 'Party - Start with selected characters'),
    ]
    
    start_mode = models.CharField(
        max_length=10,
        choices=START_MODE_CHOICES,
        default='party'
    )
    starting_party_size = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
```

**Solo Mode Features:**
- Start with 1 character (selected by player)
- Can recruit up to 3 additional party members
- Recruits found in special "Recruitment Rooms"
- Recruits start at current campaign level (not starting level)

**Recruitment Rooms:**
- Appear every 3-5 encounters (random)
- Offer 2-3 potential recruits
- Each recruit has different class/race combo
- Player chooses which to recruit (or skip)

---

## 5. Recruitable Party Members

### Concept
Random NPCs that can join the party during solo runs. Each has unique stats and abilities.

### Implementation

**Model:**
```python
class RecruitableCharacter(models.Model):
    """Templates for characters that can be recruited"""
    name = models.CharField(max_length=100)
    character_class = models.ForeignKey(CharacterClass, on_delete=models.PROTECT)
    race = models.ForeignKey(CharacterRace, on_delete=models.PROTECT)
    background = models.ForeignKey(CharacterBackground, on_delete=models.PROTECT, blank=True, null=True)
    
    # Personality/flavor
    personality_trait = models.TextField(blank=True)
    recruitment_description = models.TextField()
    
    # Starting stats (can be randomized or fixed)
    starting_stats = models.JSONField(default=dict)  # Override default stats
    
    # Rarity (affects when they appear)
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('legendary', 'Legendary'),
    ]
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')

class RecruitmentRoom(models.Model):
    """A room where players can recruit party members"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recruitment_rooms')
    encounter_number = models.IntegerField()
    available_recruits = models.ManyToManyField(RecruitableCharacter)
    discovered = models.BooleanField(default=False)
    recruit_selected = models.ForeignKey(
        CampaignCharacter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
```

**Recruitment System:**
```python
class RecruitmentGenerator:
    def generate_recruitment_room(self, campaign, encounter_number):
        """Generate recruitment options"""
        # Determine rarity based on progress
        rarity_weights = self._calculate_rarity_weights(encounter_number)
        
        # Select 2-3 recruits
        recruits = RecruitableCharacter.objects.filter(
            rarity__in=['common', 'uncommon']
        ).order_by('?')[:3]
        
        room = RecruitmentRoom.objects.create(
            campaign=campaign,
            encounter_number=encounter_number
        )
        room.available_recruits.set(recruits)
        return room
    
    def recruit_character(self, campaign, recruitment_room, recruit_template):
        """Recruit a character into the campaign"""
        # Create character from template
        character = Character.objects.create(
            name=recruit_template.name,
            level=campaign.current_encounter_index + campaign.starting_level,  # Scale to current level
            character_class=recruit_template.character_class,
            race=recruit_template.race,
            background=recruit_template.background,
            user=campaign.owner  # Recruited characters belong to campaign owner
        )
        
        # Initialize stats (from template or defaults)
        stats = CharacterStats.objects.create(
            character=character,
            **recruit_template.starting_stats
        )
        
        # Add to campaign
        campaign_char = CampaignCharacter.objects.create(
            campaign=campaign,
            character=character
        )
        campaign_char.initialize_from_character()
        
        # Track recruitment
        recruitment_room.recruit_selected = campaign_char
        recruitment_room.save()
        
        return campaign_char
```

**Recruit Variety:**
- Different class combinations
- Random races
- Unique starting equipment (sometimes)
- Personality traits (flavor only, no mechanical effect)
- Some may have special abilities or bonuses

---

## 6. Campaign Flow with New Features

### Example Campaign Flow

**Campaign Setup:**
```
1. Player creates campaign
   - Name: "Solo Adventure"
   - Starting Level: 3
   - Start Mode: Solo
   - Starting Character: "Thorin the Fighter"

2. Campaign starts
   - Thorin joins at Level 3
   - Initial equipment based on level
   - Party size: 1/4
```

**Encounter 1:**
```
Combat: 3 Goblins
- Thorin defeats them
- Gain 150 XP each (450 total)
- Thorin levels up! (Level 3 → 4)
- +HP, +Spell Slots (if applicable)
```

**Treasure Room 1:**
```
Type: Equipment Room
Rewards:
  - Longsword +1 (Magic Weapon)
  - Healing Potion x2
  - 50 Gold
Player distributes items
```

**Encounter 2:**
```
Combat: Orc War Band
- Thorin defeats them
- Gain 200 XP
- No level up yet (needs 600 more XP)
```

**Recruitment Room:**
```
Available Recruits:
  1. Elara (Elf Wizard) - "A scholarly mage seeking adventure"
  2. Dorn (Dwarf Cleric) - "A holy warrior looking for glory"
  3. Skip recruitment

Player chooses: Dorn the Cleric
- Dorn joins party at Level 4 (same as Thorin)
- Party size: 2/4
```

**Encounter 3:**
```
Combat: Ogre + Goblins
- Party defeats them
- Thorin gains 300 XP, Dorn gains 300 XP
- Both level up to Level 5
- New abilities unlocked (Extra Attack for Fighter, 3rd level spells for Cleric)
```

**Boss Encounter:**
```
Final Boss: Dragon Wyrmling
- Full party (2 characters)
- Both Level 5
- Using magic items from treasure rooms
- Close fight, party wins!
```

---

## 7. API Endpoints

### New Endpoints Needed

**XP & Leveling:**
```python
POST /api/campaigns/{id}/grant_xp/
{
    "character_ids": [1, 2],
    "xp_amount": 300,
    "source": "encounter_completion"
}

GET /api/campaigns/{id}/character_xp/
# Returns XP tracking for all characters
```

**Treasure Rooms:**
```python
POST /api/campaigns/{id}/discover_treasure_room/
{
    "encounter_number": 2
}
# Generates and reveals treasure room

GET /api/campaigns/{id}/treasure_rooms/
# List all treasure rooms

POST /api/campaigns/{id}/treasure_rooms/{room_id}/claim_reward/
{
    "reward_id": 1,
    "character_id": 1  # Who gets the reward
}
```

**Recruitment:**
```python
POST /api/campaigns/{id}/discover_recruitment_room/
{
    "encounter_number": 3
}
# Generates recruitment room

GET /api/campaigns/{id}/recruitment_rooms/{room_id}/available/
# Get available recruits

POST /api/campaigns/{id}/recruitment_rooms/{room_id}/recruit/
{
    "recruit_template_id": 2
}
# Recruit a character
```

**Level Up:**
```python
POST /api/campaigns/{id}/campaign_characters/{id}/level_up/
# Manually trigger level up (or automatic on XP threshold)
```

---

## 8. Database Schema Updates

### New Models Needed

1. `CharacterXP` - Track XP and leveling
2. `TreasureRoom` - Treasure room instances
3. `TreasureRoomReward` - Individual rewards
4. `RecruitableCharacter` - Templates for recruits
5. `RecruitmentRoom` - Recruitment opportunities

### Migration Strategy

- Add fields to `Campaign` model
- Create new models
- Migrate existing campaigns (default values)
- Create initial `RecruitableCharacter` templates

---

## 9. Game Balance Considerations

### XP Scaling
- Higher starting level = Less total XP to gain
- Boss encounters give bonus XP
- Treasure rooms give small XP bonuses

### Treasure Balance
- Early encounters: Common/Uncommon items
- Mid encounters: Uncommon/Rare items
- Late encounters: Rare/Legendary items
- Boss rewards: Guaranteed powerful item

### Recruitment Balance
- Solo mode: Can recruit up to 3 (4 total party)
- Party mode: Start with chosen party, no recruitment
- Recruits scale to current level (not starting level)
- Later recruits may have better stats/equipment

---

## 10. Implementation Priority

### Phase 1: Core Systems (MVP)
1. ✅ Starting level selection
2. ✅ Basic XP system
3. ✅ Level up functionality
4. ✅ Simple treasure rooms

### Phase 2: Party Management
5. ✅ Solo vs Party mode
6. ✅ Recruitment system
7. ✅ Recruitable character templates

### Phase 3: Enhanced Features
8. ✅ Multiple treasure room types
9. ✅ Advanced XP calculations
10. ✅ Recruitment rarity system
11. ✅ Shop rooms (optional)

---

## Summary

These features transform the gauntlet into a true roguelite experience:
- **Progression**: XP and leveling system
- **Rewards**: Treasure rooms with items and gold
- **Flexibility**: Solo or party starts
- **Variety**: Recruitable companions
- **Replayability**: Different runs = different recruits and treasures

The system maintains the core roguelite loop:
**Fight → Gain XP → Level Up → Find Treasure → Recruit Allies → Fight Harder Enemies → Repeat**

