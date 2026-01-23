# 🎲 SRD5 Roguelike Gauntlet Backend

A comprehensive Django REST API backend for **SRD 5.1 (Fantasy RPG)** featuring a roguelike gauntlet campaign system, complete character progression, advanced combat mechanics, and full bestiary integration.

> **Legal Disclaimer**: This project is based on the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode. This project is not affiliated with or endorsed by Wizards of the Coast.

## 🚀 Features

### 🎮 Roguelike Gauntlet Campaign System
- **Campaign Management**: Create gauntlet-style campaigns with sequential encounters
- **Starting Level Selection**: Begin campaigns at any level (1-20)
- **XP Tracking**: Automatic experience point calculation and level-up
- **Treasure Rooms**: Procedurally generated loot with real D&D items and gold rewards
- **Merchant System**: Random merchant encounters with rarity-based item selection tied to gauntlet progress
- **Gold Economy**: Earn gold from treasure and encounters, spend at merchants
- **Rest Management**: Limited short and long rests for strategic resource management
- **Party Status**: Real-time HP, hit dice, resource, and gold tracking
- **Encounter Progression**: Sequential encounter completion with rewards

### 📖 Spell Library System
- **1,400+ Spells**: Comprehensive D&D 5e spell database imported from Open5e
- **Advanced Filtering**: Search by level, school, concentration, ritual, class availability
- **Complete Spell Data**: Casting time, range, components, duration, damage progression
- **API Endpoints**: RESTful API for spell queries and management
- **Open5e Integration**: Auto-import spells with management command


### 👤 Complete Character System
- **Character Creation**: Full D&D 5e character creation with all classes and races
- **Level Progression**: Automatic level-up with class features (levels 1-20)
- **Multiclassing**: Full multiclass support with spell slot calculation
- **Ability Score Increases**: ASI selection at appropriate levels
- **Subclass Selection**: All major subclasses with features
- **Racial Features**: Complete racial trait implementation
- **Background Features**: Background-specific abilities
- **Feat System**: 40+ feats with prerequisites

### 🎯 Advanced Combat System (Phases 1-3)
- **Phase 1 - Core Combat**: Initiative, attacks, damage, turn management
- **Phase 2 - Spellcasting**: Full spell system with saving throws and conditions
- **Phase 3 - Advanced Mechanics**:
  - Concentration checks and management
  - Opportunity attacks and reactions
  - Death saving throws
  - Legendary actions
  - **Enemy spell slot enforcement** (prevents infinite spell spam)
  - Environmental effects (terrain, cover, lighting, weather)
  - Hazards and position tracking
- **Combat Logging**: Detailed combat logs with analytics and export (JSON/CSV)

### � Spell Management
- **Prepared Casters**: Cleric, Druid, Paladin, Wizard spell preparation
- **Known Casters**: Bard, Ranger, Sorcerer, Warlock spell learning
- **Wizard Spellbook**: Spellbook management and spell copying
- **Ritual Casting**: Ritual spell mechanics
- **Spell Slots**: Automatic calculation including multiclass casters

### 📚 Complete Bestiary System
- **3,200+ Monsters**: Full creature database from Open5e with automatic spell import
- **Full D&D 5e Stat Blocks**: All ability scores, skills, saving throws, and combat stats
- **Spellcaster Support**: Automatic spell parsing from Open5e with usage limits
- **Creature Properties**: Size, type, alignment, challenge rating
- **Combat Mechanics**: Attacks, abilities, spells, legendary actions
- **Resistances & Immunities**: Damage types and condition immunities
- **Spell Slot Enforcement**: Enemies limited by stat blocks - no infinite spam
- **Senses**: Darkvision, blindsight, tremorsense, truesight
- **Environments**: Where creatures can be found
- **Treasure**: Loot tables and treasure information

### 🔄 Import System
- **Multiple Sources**: JSON, CSV, D&D Beyond API, official SRD, **Open5e API**
- **Auto-Population**: Import 3,200+ monsters with complete spell lists from Open5e
- **Automatic Spell Parsing**: Spellcasting abilities parsed into structured spell data
- **Web Interface**: User-friendly file upload interface
- **Command Line**: Bulk import capabilities (`python manage.py import_monsters_from_api`)
- **Templates**: Pre-formatted import templates
- **Validation**: Comprehensive error handling
- **Smart Integration**: Imported content automatically available in treasure and encounters

### 🔐 User Authentication
- **JWT Authentication**: Secure token-based authentication
- **User Registration**: Email-based registration system
- **Token Refresh**: Automatic token refresh mechanism
- **Data Isolation**: Users can only access their own characters and campaigns
- **Public Endpoints**: Bestiary and items accessible without authentication

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
dnd-backend/
├── dnd_backend/          # Core Django settings
├── authentication/       # User authentication (JWT)
├── bestiary/             # Monster and creature data
│   ├── models.py        # Complete D&D 5e models
│   ├── serializers.py   # API serialization
│   ├── views.py         # API endpoints
│   ├── admin.py         # Admin interface
│   └── management/      # Import commands
├── characters/           # Player characters
│   ├── models.py        # Character, stats, features
│   ├── multiclassing.py # Multiclass mechanics
│   ├── spell_management.py # Spell system
│   ├── feat_models.py   # Feat system
│   └── inventory_management.py # Equipment
├── campaigns/            # Campaign and gauntlet system
│   ├── models.py        # Campaign, XP, treasure
│   ├── views.py         # Campaign endpoints
│   ├── utils.py         # Treasure/encounter generation
│   ├── class_features_data.py # All class features
│   ├── racial_features_data.py # Racial traits
│   └── background_features_data.py # Backgrounds
├── combat/              # Combat mechanics (Phases 1-3)
│   ├── models.py        # Combat sessions, participants
│   ├── views.py         # Combat endpoints
│   ├── environmental_effects.py # Environmental system
│   └── condition_effects.py # Condition mechanics
├── spells/               # Spell library system
│   ├── models.py        # Spell and SpellDamage models
│   ├── views.py         # Spell API endpoints
│   ├── serializers.py   # Spell serialization
│   └── management/commands/import_spells_from_api.py # Open5e import
├── merchants/            # Merchant/shop system
│   ├── models.py        # Merchant, inventory, transactions
│   ├── views.py         # Merchant API endpoints
│   ├── serializers.py   # Merchant serialization
│   └── rarity_weights.py # Rarity algorithm for item selection
├── encounters/          # Encounter management
├── items/               # Equipment and items
├── logs/                # Combat logs and analytics
├── tests/               # Organized test suite
│   ├── test_authentication.py
│   ├── test_api_integration.py
│   ├── test_combat.py
│   ├── test_campaign_gauntlet.py
│   ├── test_spell_and_merchant.py # Tests for new systems
│   ├── test_subclass_and_racial_features.py
│   ├── test_multiclassing.py
│   ├── test_spell_management.py
│   └── ... (15+ test files total)
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

5. **Import monsters, items, and spells from Open5e API** (Optional but recommended)
   ```bash
   # Import real D&D 5e monsters (200+)
   python manage.py import_monsters_from_api --source open5e
   
   # Import real D&D 5e items (100+)
   python manage.py import_items_from_api --source open5e
   
   # Import real D&D 5e spells (1,400+)  🆕
   python manage.py import_spells_from_api --source open5e
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

## 🎲 SRD5 Data Models

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
# Run all Django tests
python manage.py test

# Run specific test file from tests/ directory
python tests/test_authentication.py
python tests/test_combat.py
python tests/test_campaign_gauntlet.py
python tests/test_multiclassing.py
python tests/test_spell_management.py

# Check for issues
python manage.py check
```

**Available Test Suites:**
- `test_authentication.py` - User authentication and JWT tokens
- `test_api_integration.py` - API integration tests
- `test_combat.py` - Combat system (Phases 1-3)
- `test_campaign_gauntlet.py` - Roguelike campaign system
- `test_subclass_and_racial_features.py` - Character features
- `test_multiclassing.py` - Multiclass mechanics
- `test_spell_management.py` - Spell system
- `test_level_up_features.py` - Level progression
- `test_asi_and_subclass.py` - ASI and subclass selection
- `test_background_feats_reactions.py` - Backgrounds, feats, reactions
- `test_environmental_effects.py` - Environmental combat mechanics
- `test_combat_logging.py` - Combat log analytics
- And more...

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Campaign Gauntlet Guide](docs/campaign_gauntlet_guide.md)
- [Combat System Phase 2](docs/combat_phase2_guide.md)
- [Combat System Phase 3](docs/combat_phase3_guide.md)
- [User Authentication Guide](docs/user_authentication_guide.md)
- [Character Tracking Guide](docs/CHARACTER_TRACKING_GUIDE.md)
- [Frontend Ready Summary](docs/FRONTEND_READY_SUMMARY.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Roadmap

### ✅ Completed Features
- [x] Complete bestiary system with 200+ monsters
- [x] Import/export functionality (JSON, CSV, Open5e API)
- [x] Web interface for imports
- [x] Full character management system
  - [x] Character creation with all classes and races
  - [x] Level progression (1-20) with automatic features
  - [x] Multiclassing with spell slot calculation
  - [x] Subclass selection and features
  - [x] Racial and background features
  - [x] Feat system (40+ feats)
  - [x] Ability Score Increases (ASI)
- [x] Advanced combat mechanics (Phases 1-3)
  - [x] Core combat (initiative, attacks, damage)
  - [x] Spellcasting system
  - [x] Concentration and reactions
  - [x] Opportunity attacks
  - [x] Death saving throws
  - [x] Legendary actions
  - [x] Environmental effects
- [x] Item/equipment system with 100+ items
- [x] Combat logging with analytics and export
- [x] Roguelike gauntlet campaign system
  - [x] Campaign management
  - [x] XP tracking and automatic level-up
  - [x] Treasure room generation
  - [x] Rest management (short/long rests)
  - [x] Party status tracking
- [x] Spell management system
  - [x] Prepared casters (Cleric, Druid, Paladin, Wizard)
  - [x] Known casters (Bard, Ranger, Sorcerer, Warlock)
  - [x] Wizard spellbook
  - [x] Ritual casting
- [x] User authentication (JWT)
  - [x] Registration and login
  - [x] Token refresh
  - [x] Data isolation

### 🔜 Upcoming Features
- [ ] Frontend interface (React/Vue)
- [ ] Campaign sharing and templates
- [ ] Custom content creation tools
- [ ] Mobile app

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
