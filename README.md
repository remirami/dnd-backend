# 🎲 D&D 5e Combat Simulator Backend

A comprehensive Django REST API backend for D&D 5e combat simulation, featuring a complete bestiary system with full monster stat blocks, import capabilities, and combat mechanics.

## 🚀 Features

### 📚 Complete Bestiary System
- **Full D&D 5e Stat Blocks**: All ability scores, skills, saving throws, and combat stats
- **Creature Properties**: Size, type, alignment, challenge rating
- **Combat Mechanics**: Attacks, abilities, spells, legendary actions
- **Resistances & Immunities**: Damage types and condition immunities
- **Senses**: Darkvision, blindsight, tremorsense, truesight
- **Environments**: Where creatures can be found
- **Treasure**: Loot tables and treasure information

### 🔄 Import System
- **Multiple Sources**: JSON, CSV, D&D Beyond API, official SRD, **Open5e API**
- **Auto-Population**: Import 200+ monsters and 100+ items from free APIs
- **Web Interface**: User-friendly file upload interface
- **Command Line**: Bulk import capabilities
- **Templates**: Pre-formatted import templates
- **Validation**: Comprehensive error handling
- **Smart Integration**: Imported content automatically available in treasure and encounters

### 🎯 API Endpoints
- **RESTful API**: Complete CRUD operations for all entities
- **Nested Serialization**: Full monster data with related objects
- **Filtering & Search**: Advanced query capabilities
- **Admin Interface**: Django admin for data management

## 🏗️ Tech Stack

- **Backend**: Django 5.0.2 + Django REST Framework
- **Database**: SQLite (development) → PostgreSQL (production)
- **API**: RESTful JSON API
- **Admin**: Django Admin Interface

## 📁 Project Structure

```
dnd_backend/
├── dnd_backend/          # Core Django settings
├── bestiary/             # Monster and creature data
│   ├── models.py        # Complete D&D 5e models
│   ├── serializers.py   # API serialization
│   ├── views.py         # API endpoints
│   ├── admin.py         # Admin interface
│   └── management/      # Import commands
├── characters/           # Player characters
├── combat/              # Combat mechanics
├── items/               # Equipment and items
├── logs/                # Combat logs (planned)
├── templates/           # Web interface templates
└── docs/                # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Django 5.0.2
- Django REST Framework

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd dnd_backend
   ```

2. **Install dependencies**
   ```bash
   pip install django djangorestframework requests
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Populate base data**
   ```bash
   python manage.py populate_dnd_data
   python manage.py populate_conditions_environments
   ```

5. **Import monsters and items from Open5e API** (Optional but recommended)
   ```bash
   # Import real D&D 5e monsters (200+)
   python manage.py import_monsters_from_api --source open5e
   
   # Import real D&D 5e items (100+)
   python manage.py import_items_from_api --source open5e
   ```
   
   See [API Import Guide](docs/api_import_guide.md) for detailed instructions.

6. **Start the server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - API: http://127.0.0.1:8000/api/
   - Admin: http://127.0.0.1:8000/admin/
   - Import Interface: http://127.0.0.1:8000/api/enemies/import/

## 📖 Usage

### Import Monsters and Items

#### From Open5e API (Recommended - Free, No API Key Required)
```bash
# Import all SRD monsters (200+)
python manage.py import_monsters_from_api --source open5e

# Import only low-level monsters (CR 0-5)
python manage.py import_monsters_from_api --source open5e --cr-max 5

# Import all SRD items (weapons, armor, magic items)
python manage.py import_items_from_api --source open5e

# Preview before importing
python manage.py import_monsters_from_api --source open5e --dry-run --limit 10
```

**Benefits:**
- ✅ Real D&D 5e content from official SRD
- ✅ Automatically populates treasure system
- ✅ Automatically populates encounter generation
- ✅ No manual data entry required
- ✅ Free and legal to use

See [API Import Guide](docs/api_import_guide.md) for complete documentation.

#### Web Interface
Visit `http://127.0.0.1:8000/api/enemies/import/` for the user-friendly import interface.

#### From JSON/CSV Files
```bash
# Import from JSON file
python manage.py import_monsters --source json --file monsters.json

# Import from CSV file
python manage.py import_monsters --source csv --file monsters.csv

# Dry run (preview)
python manage.py import_monsters --source json --file monsters.json --dry-run
```

### API Usage

#### Get All Monsters
```bash
curl http://127.0.0.1:8000/api/enemies/
```

#### Get Specific Monster
```bash
curl http://127.0.0.1:8000/api/enemies/1/
```

#### Create Monster
```bash
curl -X POST http://127.0.0.1:8000/api/enemies/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Monster", "hp": 10, "ac": 12, "challenge_rating": "1/4"}'
```

## 🎲 D&D 5e Data Models

### Core Models
- **Enemy**: Basic creature information
- **EnemyStats**: Complete stat block
- **EnemyAttack**: Combat attacks
- **EnemyAbility**: Special abilities
- **EnemySpell**: Spellcasting
- **EnemyResistance**: Damage resistances/immunities
- **EnemyConditionImmunity**: Condition immunities
- **EnemyLegendaryAction**: Legendary actions
- **EnemyEnvironment**: Creature habitats
- **EnemyTreasure**: Loot information

### Supporting Models
- **DamageType**: D&D 5e damage types
- **Language**: D&D 5e languages
- **Condition**: D&D 5e conditions
- **Environment**: Creature environments

## 📋 Data Format

### JSON Import Format
```json
{
  "monsters": [
    {
      "name": "Goblin",
      "hit_points": 7,
      "armor_class": 15,
      "challenge_rating": "1/4",
      "size": "S",
      "creature_type": "humanoid",
      "alignment": "NE",
      "strength": 8,
      "dexterity": 14,
      "constitution": 10,
      "intelligence": 10,
      "wisdom": 8,
      "charisma": 8,
      "speed": "30 ft.",
      "darkvision": "60 ft.",
      "passive_perception": 9,
      "hit_dice": "2d6",
      "proficiency_bonus": 2,
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
      "resistances": [],
      "condition_immunities": [],
      "legendary_actions": [],
      "environments": ["forest", "hill", "underdark"],
      "languages": ["Common", "Goblin"]
    }
  ]
}
```

## 🔧 Development

### Adding New Features
1. Create models in `bestiary/models.py`
2. Add serializers in `bestiary/serializers.py`
3. Update admin in `bestiary/admin.py`
4. Create and run migrations
5. Update import system if needed

### Testing
```bash
# Run tests
python manage.py test

# Check for issues
python manage.py check
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Monster Import Guide](docs/monster_import_guide.md)
- **[API Import Guide](docs/api_import_guide.md)** - Import from Open5e API
- [Campaign Gauntlet Design](docs/campaign_gauntlet_design.md)
- [Combat System Guide](docs/combat_phase3_guide.md)
- [User Authentication Guide](docs/user_authentication_guide.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Roadmap

- [x] Complete bestiary system
- [x] Import/export functionality
- [x] Web interface
- [x] Character management system
- [x] Combat mechanics (Phase 1, 2, 3)
- [x] Item/equipment system
- [x] Combat logging
- [x] Campaign management (Roguelike Gauntlet)
- [ ] Frontend interface
- [ ] User authentication

## 🐛 Issues

If you encounter any issues, please create a GitHub issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details

## 📞 Support

For questions or support, please open a GitHub issue or contact the maintainers.

---

**Happy Gaming!** 🎲⚔️🐉
