# 🎲 D&D Monster Import System

A comprehensive system for importing monsters from various sources into your D&D backend database.

## 🚀 Features

- **Multiple Import Sources**: JSON, CSV, D&D Beyond API, and official SRD data
- **Web Interface**: User-friendly web UI for file uploads
- **Command Line Interface**: Powerful CLI for bulk imports
- **Data Validation**: Comprehensive error handling and validation
- **Template Downloads**: Pre-formatted templates for easy data entry
- **Update Support**: Option to update existing monsters or skip duplicates

## 📁 Import Sources

### 1. JSON Files
Import monsters from structured JSON files with full stat blocks.

**Format:**
```json
{
  "monsters": [
    {
      "name": "Goblin",
      "hit_points": 7,
      "armor_class": 15,
      "challenge_rating": "1/4",
      "strength": 8,
      "dexterity": 14,
      "constitution": 10,
      "intelligence": 10,
      "wisdom": 8,
      "charisma": 8,
      "speed": "30 ft.",
      "darkvision": "60 ft.",
      "passive_perception": 9,
      "attacks": [
        {
          "name": "Scimitar",
          "bonus": 4,
          "damage": "1d6+2 slashing"
        }
      ],
      "abilities": [
        {
          "name": "Nimble Escape",
          "description": "The goblin can take the Disengage or Hide action as a bonus action."
        }
      ],
      "resistances": [
        {
          "damage_type": "Fire",
          "resistance_type": "immunity"
        }
      ],
      "languages": ["Common", "Goblin"]
    }
  ]
}
```

### 2. CSV Files
Import monsters from spreadsheet-compatible CSV files.

**Format:**
```csv
name,hit_points,armor_class,challenge_rating,strength,dexterity,constitution,intelligence,wisdom,charisma,speed,darkvision,passive_perception,attacks,abilities,languages
Goblin,7,15,1/4,8,14,10,10,8,8,"30 ft.","60 ft.",9,"Scimitar (+4, 1d6+2 slashing)","Nimble Escape","Common, Goblin"
```

### 3. D&D Beyond API
Import monsters directly from D&D Beyond (requires API key).

### 4. Official SRD Data
Import monsters from the official D&D 5e System Reference Document.

## 🖥️ Web Interface

Access the import interface at: `http://localhost:8000/api/enemies/import/`

**Features:**
- Drag-and-drop file uploads
- Real-time import status
- Template downloads
- Update existing monsters option

## 💻 Command Line Interface

### Basic Usage

```bash
# Import from JSON file
python manage.py import_monsters --source json --file monsters.json

# Import from CSV file
python manage.py import_monsters --source csv --file monsters.csv

# Import SRD monsters
python manage.py import_monsters --source srd

# Import from D&D Beyond API
python manage.py import_monsters --source dndbeyond --url "https://api.dndbeyond.com/monsters/123"
```

### Advanced Options

```bash
# Dry run (preview without importing)
python manage.py import_monsters --source json --file monsters.json --dry-run

# Update existing monsters
python manage.py import_monsters --source json --file monsters.json --update-existing
```

## 🔧 API Endpoints

### Import Endpoints

- `POST /api/enemies/import_json/` - Import from JSON file
- `POST /api/enemies/import_csv/` - Import from CSV file
- `POST /api/enemies/import_srd/` - Import SRD monsters

### Template Endpoints

- `GET /api/enemies/export_template/?format=json` - Download JSON template
- `GET /api/enemies/export_template/?format=csv` - Download CSV template

## 📋 Data Fields

### Core Monster Data
- `name` - Monster name
- `hit_points` - Hit points
- `armor_class` - Armor class
- `challenge_rating` - Challenge rating (e.g., "1/4", "1/2", "1", "2")

### Ability Scores
- `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma`

### Combat Stats
- `speed` - Movement speed (e.g., "30 ft.", "40 ft., fly 60 ft.")
- `darkvision`, `blindsight`, `tremorsense`, `truesight` - Special senses
- `passive_perception` - Passive perception score

### Saving Throws
- `str_save`, `dex_save`, `con_save`, `int_save`, `wis_save`, `cha_save`

### Skills
All 18 D&D 5e skills: `athletics`, `acrobatics`, `sleight_of_hand`, `stealth`, `arcana`, `history`, `investigation`, `nature`, `religion`, `animal_handling`, `insight`, `medicine`, `perception`, `survival`, `deception`, `intimidation`, `performance`, `persuasion`

### Spellcasting
- `spell_save_dc` - Spell save DC
- `spell_attack_bonus` - Spell attack bonus

### Attacks
Array of attack objects with:
- `name` - Attack name
- `bonus` - Attack bonus
- `damage` - Damage dice and type

### Abilities
Array of ability objects with:
- `name` - Ability name
- `description` - Ability description

### Spells
Array of spell objects with:
- `name` - Spell name
- `save_dc` - Spell save DC
- `slots` - Array of spell slot objects with `level` and `uses`

### Resistances
Array of resistance objects with:
- `damage_type` - Damage type name
- `resistance_type` - "resistance", "immunity", or "vulnerability"
- `notes` - Optional notes

### Languages
Array of language names

## 🛠️ Setup

### 1. Install Dependencies
```bash
pip install requests  # For D&D Beyond API integration
```

### 2. Configure Settings
Add to your `settings.py`:
```python
# Optional: D&D Beyond API key
DND_BEYOND_API_KEY = 'your_api_key_here'
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Populate Base Data
```bash
python manage.py populate_dnd_data
```

## 📝 Examples

### Sample JSON Import
```bash
python manage.py import_monsters --source json --file sample_monsters.json
```

### Sample CSV Import
```bash
python manage.py import_monsters --source csv --file sample_monsters.csv
```

### Import SRD Monsters
```bash
python manage.py import_monsters --source srd
```

## 🔍 Troubleshooting

### Common Issues

1. **"Requests library not available"**
   - Install: `pip install requests`

2. **"File not found"**
   - Check file path is correct
   - Ensure file exists and is readable

3. **"Invalid JSON"**
   - Validate JSON syntax
   - Use JSON validator online

4. **"Damage type not found"**
   - Run: `python manage.py populate_dnd_data`
   - Check damage type names match exactly

5. **"Language not found"**
   - Run: `python manage.py populate_dnd_data`
   - Check language names match exactly

### Validation Tips

- Use the `--dry-run` flag to preview imports
- Download templates to ensure correct format
- Check the web interface for user-friendly error messages
- Use the admin interface to verify imported data

## 🎯 Best Practices

1. **Always use dry-run first** to preview imports
2. **Backup your database** before bulk imports
3. **Use templates** to ensure correct data format
4. **Validate data** before importing large datasets
5. **Use update-existing** carefully to avoid overwriting custom data

## 🔗 Integration

The import system integrates seamlessly with:
- Django Admin interface
- REST API endpoints
- Existing monster models
- Combat system (when implemented)

## 📚 Additional Resources

- [D&D 5e SRD](https://dnd.wizards.com/resources/systems-reference-document)
- [D&D Beyond API Documentation](https://www.dndbeyond.com/api)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

**Happy Monster Importing!** 🎲⚔️
