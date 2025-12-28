# 🌐 API Import Guide - Populate Your Database from Open D&D APIs

This guide shows you how to populate your D&D backend with real monsters and items from free, open-source APIs.

## 🎯 Overview

Your treasure system and encounter generation can now pull from a database populated with **real D&D 5e content** from:

- **Open5e API** - Free, no API key required, comprehensive SRD content
- **Custom JSON files** - Import your own custom content
- **D&D Beyond** - (via existing monster importer, requires API access)

## 📦 Available Importers

### 1. Monster Importer (Open5e)
Import hundreds of D&D 5e monsters with full stat blocks.

### 2. Item Importer (Open5e)
Import weapons, armor, magic items, and equipment.

## 🚀 Quick Start

### Step 1: Install Requirements

```bash
pip install requests
```

### Step 2: Import Monsters

```bash
# Import all SRD monsters (200+ monsters)
python manage.py import_monsters_from_api --source open5e

# Import only low-level monsters (CR 0-5)
python manage.py import_monsters_from_api --source open5e --cr-max 5

# Import specific CR range
python manage.py import_monsters_from_api --source open5e --cr-min 1 --cr-max 10

# Test with limited import
python manage.py import_monsters_from_api --source open5e --limit 10

# Preview without importing (dry run)
python manage.py import_monsters_from_api --source open5e --dry-run
```

### Step 3: Import Items

```bash
# Import all SRD items (weapons, armor, magic items)
python manage.py import_items_from_api --source open5e

# Test with limited import
python manage.py import_items_from_api --source open5e --limit 20

# Preview without importing (dry run)
python manage.py import_items_from_api --source open5e --dry-run
```

### Step 4: Verify Import

```bash
# Check how many monsters were imported
python manage.py shell
>>> from bestiary.models import Enemy
>>> Enemy.objects.count()
>>> Enemy.objects.all()[:5]

# Check how many items were imported
>>> from items.models import Item, Weapon, Armor, MagicItem
>>> Item.objects.count()
>>> Weapon.objects.count()
>>> Armor.objects.count()
>>> MagicItem.objects.count()
```

## 📚 Detailed Usage

### Monster Import Options

```bash
python manage.py import_monsters_from_api [OPTIONS]

Options:
  --source {open5e,json}    Source for import (default: open5e)
  --file PATH               Path to JSON file (if using json source)
  --dry-run                 Preview import without saving
  --update-existing         Update existing monsters instead of skipping
  --limit NUMBER            Limit number of monsters to import
  --cr-min CR               Minimum challenge rating (e.g., "1/4", "1", "5")
  --cr-max CR               Maximum challenge rating (e.g., "5", "10", "20")
```

### Item Import Options

```bash
python manage.py import_items_from_api [OPTIONS]

Options:
  --source {open5e,json}    Source for import (default: open5e)
  --file PATH               Path to JSON file (if using json source)
  --dry-run                 Preview import without saving
  --update-existing         Update existing items instead of skipping
  --limit NUMBER            Limit number of items to import
```

## 🎲 How It Integrates with Your System

### Treasure System Integration

Your `TreasureGenerator` class already pulls from the Item database:

```python
# From campaigns/utils.py - TreasureGenerator
equipment_items = Item.objects.filter(
    category__name__in=['Weapon', 'Armor', 'Shield']
).order_by('?')[:random.randint(1, 2)]

magic_items = Item.objects.filter(
    category__name='Magic Item'
).order_by('?')[:1]

consumables = Item.objects.filter(
    category__name='Consumable'
).order_by('?')[:random.randint(2, 4)]
```

**After importing items**, your treasure rooms will automatically include:
- Real D&D weapons (longswords, daggers, crossbows, etc.)
- Real D&D armor (leather armor, chain mail, plate armor, etc.)
- Real D&D magic items (potions, rings, wands, etc.)
- Consumables (healing potions, scrolls, etc.)

### Encounter Generation Integration

Your `CampaignGenerator` already pulls from the Enemy database:

```python
# From campaigns/utils.py - CampaignGenerator
enemies = Enemy.objects.filter(
    challenge_rating__in=valid_crs
).order_by('?')[:num_enemy_types]
```

**After importing monsters**, your encounters will automatically include:
- Real D&D monsters (goblins, orcs, dragons, etc.)
- Proper CR balancing
- Full stat blocks with abilities
- Resistances and immunities

## 📊 What Gets Imported

### Monster Data Includes:
- ✓ Name, HP, AC, Challenge Rating
- ✓ All ability scores (STR, DEX, CON, INT, WIS, CHA)
- ✓ Saving throws and skills
- ✓ Speed, senses (darkvision, etc.)
- ✓ Actions and attacks with damage
- ✓ Special abilities
- ✓ Legendary actions
- ✓ Damage resistances, immunities, vulnerabilities
- ✓ Languages

### Item Data Includes:
- ✓ Name, description, rarity
- ✓ Weight and value (in gold pieces)
- ✓ Category (weapon, armor, magic item, etc.)
- ✓ Weapon properties (damage dice, damage type, range)
- ✓ Armor properties (AC, armor type, stealth disadvantage)
- ✓ Magic item properties (attunement, bonuses)
- ✓ Item properties (versatile, finesse, two-handed, etc.)

## 🔧 Advanced Usage

### Import from Custom JSON

You can also import from your own JSON files:

**Monster JSON Format:**
```json
{
  "monsters": [
    {
      "name": "Custom Goblin",
      "hit_points": 10,
      "armor_class": 14,
      "challenge_rating": "1/2",
      "strength": 10,
      "dexterity": 16,
      "constitution": 12,
      "intelligence": 10,
      "wisdom": 8,
      "charisma": 8,
      "speed": {"walk": "30 ft."},
      "actions": [
        {
          "name": "Scimitar",
          "desc": "Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 1d6+3 slashing damage."
        }
      ],
      "special_abilities": [
        {
          "name": "Nimble Escape",
          "desc": "The goblin can take the Disengage or Hide action as a bonus action."
        }
      ]
    }
  ]
}
```

**Item JSON Format:**
```json
{
  "items": [
    {
      "name": "Custom Sword",
      "desc": "A magical sword that glows in the dark.",
      "rarity": "rare",
      "requires_attunement": true,
      "category": "Weapon",
      "damage_dice": "1d8",
      "damage_type": "Slashing",
      "cost": "500 gp",
      "weight": "3 lb"
    }
  ]
}
```

Then import:
```bash
python manage.py import_monsters_from_api --source json --file my_monsters.json
python manage.py import_items_from_api --source json --file my_items.json
```

### Update Existing Content

If you want to update monsters/items that are already in your database:

```bash
python manage.py import_monsters_from_api --source open5e --update-existing
python manage.py import_items_from_api --source open5e --update-existing
```

### Selective Imports

Import only what you need:

```bash
# Only import low-level monsters for starting campaigns
python manage.py import_monsters_from_api --source open5e --cr-max 3

# Only import mid-level monsters
python manage.py import_monsters_from_api --source open5e --cr-min 4 --cr-max 10

# Only import legendary creatures
python manage.py import_monsters_from_api --source open5e --cr-min 15
```

## 🎮 Testing Your Imports

### Test Monster Import
```bash
# Import a few monsters
python manage.py import_monsters_from_api --source open5e --limit 5

# Create a test campaign and see if monsters appear
python manage.py shell
>>> from campaigns.models import Campaign
>>> from campaigns.utils import CampaignGenerator
>>> campaign = Campaign.objects.create(name="Test", starting_level=1)
>>> CampaignGenerator.populate_campaign(campaign, num_encounters=3)
>>> campaign.campaign_encounters.first().encounter.encounter_enemies.all()
```

### Test Item Import
```bash
# Import a few items
python manage.py import_items_from_api --source open5e --limit 10

# Generate a treasure room and see what items appear
python manage.py shell
>>> from campaigns.models import Campaign, TreasureRoom
>>> from campaigns.utils import TreasureGenerator
>>> campaign = Campaign.objects.create(name="Test", starting_level=1)
>>> treasure = TreasureGenerator.generate_treasure_room(campaign, 1)
>>> treasure.rewards
```

## 📈 Recommended Import Strategy

### For a New Database:

1. **Import base data first:**
```bash
python manage.py populate_dnd_data  # Creates damage types, languages, etc.
python manage.py populate_items     # Creates basic item categories
```

2. **Import monsters by CR range:**
```bash
# Start with low-level monsters
python manage.py import_monsters_from_api --source open5e --cr-max 5

# Add mid-level monsters
python manage.py import_monsters_from_api --source open5e --cr-min 6 --cr-max 10

# Add high-level monsters
python manage.py import_monsters_from_api --source open5e --cr-min 11
```

3. **Import all items:**
```bash
python manage.py import_items_from_api --source open5e
```

### For Testing:

```bash
# Quick test import
python manage.py import_monsters_from_api --source open5e --limit 20
python manage.py import_items_from_api --source open5e --limit 30
```

## 🔍 Troubleshooting

### "Requests library not available"
```bash
pip install requests
```

### "Failed to fetch from API"
- Check your internet connection
- The Open5e API might be temporarily down
- Try again with `--limit 10` to test

### "Damage type not found"
```bash
# Run this first to create base damage types
python manage.py populate_dnd_data
```

### "Language not found"
```bash
# Run this first to create base languages
python manage.py populate_dnd_data
```

### Import is slow
- Use `--limit` to import in batches
- The API is rate-limited, so large imports take time
- Consider importing overnight for full database population

## 🌟 Benefits

### Before API Import:
- ❌ Limited test data
- ❌ Manual data entry required
- ❌ Inconsistent stat blocks
- ❌ Small item pool

### After API Import:
- ✅ 200+ real D&D monsters
- ✅ 100+ real D&D items
- ✅ Official SRD stat blocks
- ✅ Automatic treasure variety
- ✅ Balanced encounters
- ✅ No manual data entry

## 🎯 Next Steps

After importing:

1. **Test your treasure system:**
   - Create a campaign
   - Complete encounters
   - Check treasure rooms for variety

2. **Test your encounter generation:**
   - Use the campaign population system
   - Verify CR-appropriate monsters appear

3. **Customize as needed:**
   - Add custom monsters via JSON
   - Add custom items via JSON
   - Mix official and homebrew content

## 📚 API Resources

- **Open5e API:** https://api.open5e.com/
- **Open5e Documentation:** https://open5e.com/
- **D&D 5e SRD:** https://dnd.wizards.com/resources/systems-reference-document

## 🔐 Legal Note

All content imported from Open5e is from the D&D 5th Edition System Reference Document (SRD), which is released under the Open Game License (OGL). This content is free to use in your projects.

---

**Happy Importing!** 🎲⚔️🏆

