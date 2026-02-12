# 🎲 SRD5 Roguelike Gauntlet

A comprehensive Django REST API backend with a **Next.js frontend** for **SRD 5.2 (Fantasy RPG)** featuring a roguelike gauntlet campaign system, complete character progression, advanced combat mechanics, and full bestiary integration.

> **Legal Disclaimer**: This project is based on the System Reference Document 5.2 ("SRD 5.2") by Wizards of the Coast LLC and available at https://www.dndbeyond.com/resources/1781-systems-reference-document-52. The SRD 5.2 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode. This project is not affiliated with or endorsed by Wizards of the Coast.

## 🚀 Features

### 🖥️ Next.js Frontend
- **Character Management**: Create, view, and manage characters with a full creation wizard
- **Combat Interface**: Real-time combat with WebSocket support
- **Authentication**: Login/registration with JWT token management
- **Modern UI**: Built with Radix UI, Tailwind CSS 4, and Lucide icons
- **State Management**: Zustand for client-side state

### 🎮 Roguelike Gauntlet Campaign System
- **Campaign Management**: Create gauntlet-style campaigns with sequential encounters
- **Starting Level Selection**: Begin campaigns at any level (1-20)
- **XP Tracking**: Automatic experience point calculation and level-up
- **Treasure Rooms**: Procedurally generated loot with SRD items and gold rewards
- **Merchant System**: Random merchant encounters with rarity-based item selection tied to gauntlet progress
- **Gold Economy**: Earn gold from treasure and encounters, spend at merchants
- **Rest Management**: Limited short and long rests for strategic resource management
- **Party Status**: Real-time HP, hit dice, resource, and gold tracking
- **Encounter Progression**: Sequential encounter completion with rewards

### 📖 Spell Library System
- **Advanced Filtering**: Search by level, school, concentration, ritual, class availability
- **Complete Spell Data**: Casting time, range, components, duration, damage progression
- **Open5e Integration**: Auto-import SRD spells with management command

### 👤 Complete Character System
- **Character Creation**: Full SRD 5.2 character creation with all classes and races
- **Level Progression**: Automatic level-up with class features (levels 1-20)
- **Multiclassing**: Full multiclass support with spell slot calculation
- **Ability Score Increases**: ASI selection at appropriate levels
- **Subclass Selection**: All major subclasses with features
- **Racial Features**: Complete racial trait implementation
- **Background Features**: Background-specific abilities
- **Feat System**: 5+ feats with prerequisites

### 🎯 Advanced Combat System (Phases 1-3)
- **Phase 1 - Core Combat**: Initiative, attacks, damage, turn management
- **Phase 2 - Spellcasting**: Full spell system with saving throws and conditions
- **Phase 3 - Advanced Mechanics**:
  - Concentration checks and management
  - Opportunity attacks and reactions
  - Death saving throws
  - Legendary actions
  - Enemy spell slot enforcement
  - Environmental effects (terrain, cover, lighting, weather)
  - Hazards and position tracking
- **WebSocket Support**: Real-time combat updates via Django Channels
- **Combat Logging**: Detailed combat logs with analytics and export (JSON/CSV)

### 🧙 Spell Management
- **Prepared Casters**: Cleric, Druid, Paladin, Wizard spell preparation
- **Known Casters**: Bard, Ranger, Sorcerer, Warlock spell learning
- **Wizard Spellbook**: Spellbook management and spell copying
- **Ritual Casting**: Ritual spell mechanics
- **Spell Slots**: Automatic calculation including multiclass casters

### 📚 Complete Bestiary System
- **3,200+ Monsters**: Full creature database from Open5e with automatic spell import
- **Full SRD Stat Blocks**: All ability scores, skills, saving throws, and combat stats
- **Spellcaster Support**: Automatic spell parsing from Open5e with usage limits
- **Combat Mechanics**: Attacks, abilities, spells, legendary actions
- **Resistances & Immunities**: Damage types and condition immunities
- **Spell Slot Enforcement**: Enemies limited by stat blocks

### 🗺️ Encounter System
- **Procedural Generation**: Biome-based encounter generation
- **Encounter Themes**: Themed encounter templates
- **Boss Encounters**: Special boss encounter mechanics
- **CR Balancing**: Challenge rating based encounter scaling

### 🔐 User Authentication
- **JWT Authentication**: Secure token-based authentication
- **User Registration**: Email-based registration system
- **Token Refresh**: Automatic token refresh mechanism
- **Data Isolation**: Users can only access their own characters and campaigns
- **Public Endpoints**: Bestiary and items accessible without authentication

## 🏗️ Tech Stack

### Backend
- **Framework**: Django 5.0.2 + Django REST Framework
- **Database**: SQLite (development) → PostgreSQL (production)
- **WebSockets**: Django Channels + Daphne (ASGI)
- **Caching**: Redis + django-redis
- **Auth**: JWT via djangorestframework-simplejwt
- **API**: RESTful JSON API + CORS support

### Frontend
- **Framework**: Next.js 16 (React 19)
- **Styling**: Tailwind CSS 4 + Radix UI components
- **State**: Zustand
- **Forms**: React Hook Form + Zod validation
- **HTTP**: Axios

## 📁 Project Structure

```
dnd-backend/
├── dnd-backend/              # Django backend
│   ├── dnd_backend/          # Core Django settings
│   ├── authentication/       # User authentication (JWT)
│   ├── bestiary/             # Monster and creature data (3,200+)
│   ├── characters/           # Player characters
│   │   ├── models.py         # Character, stats, features, feats
│   │   ├── views/            # Split view modules
│   │   ├── multiclassing.py  # Multiclass mechanics
│   │   ├── spell_management.py # Spell system
│   │   └── inventory_management.py # Equipment
│   ├── campaigns/            # Campaign and gauntlet system
│   │   ├── models.py         # Campaign, XP, treasure
│   │   ├── views.py          # Campaign endpoints
│   │   └── utils.py          # Treasure/encounter generation
│   ├── combat/               # Combat mechanics (Phases 1-3)
│   │   ├── models.py         # Combat sessions, participants
│   │   ├── views.py          # Combat endpoints
│   │   ├── consumers.py      # WebSocket consumers
│   │   ├── environmental_effects.py
│   │   └── condition_effects.py
│   ├── encounters/           # Encounter generation
│   │   ├── models.py         # Encounter, themes
│   │   └── services/         # Biome & encounter generators
│   ├── spells/               # Spell library (1,400+)
│   ├── items/                # Equipment and items (100+)
│   ├── merchants/            # Merchant/shop system
│   ├── logs/                 # Combat logs and analytics
│   ├── core/                 # Shared utilities
│   ├── tests/                # Test suite (40+ test files)
│   ├── scripts/              # Debug, seed, repair, and utility scripts
│   └── docs/                 # Documentation
│
└── dnd-frontend/             # Next.js frontend
    ├── app/
    │   ├── characters/       # Character list, detail, creation wizard
    │   ├── combat/           # Combat interface
    │   ├── login/            # Authentication
    │   └── register/
    ├── components/           # Reusable UI components (Radix-based)
    └── lib/
        ├── api/              # API client modules
        ├── stores/           # Zustand stores
        └── types/            # TypeScript type definitions
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd dnd-backend/dnd-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
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

5. **Import SRD content from Open5e API** (Optional but recommended)
   ```bash
   python manage.py import_monsters_from_api --source open5e
   python manage.py import_items_from_api --source open5e
   python manage.py import_spells_from_api --source open5e
   ```

6. **Start the backend server**
   ```bash
   python manage.py runserver
   ```

> **Tip**: You can also run `python setup.py` to automate steps 2-4.

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd dnd-frontend
   npm install
   ```

2. **Start the dev server**
   ```bash
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://127.0.0.1:8000/api/
   - Admin: http://127.0.0.1:8000/admin/

## 🔧 Development

### Management Commands

```bash
# Delete all characters
python manage.py delete_all_characters

# Populate feats
python manage.py populate_feats

# Seed encounter themes
python manage.py seed_encounter_themes

# Create test encounters
python manage.py create_test_encounters
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific test file
python manage.py test tests.test_combat
python manage.py test tests.test_authentication
python manage.py test tests.test_campaign_gauntlet
```

The test suite includes 40+ test files covering authentication, combat (all phases), campaigns, character creation, multiclassing, spell management, encounters, environmental effects, and more.

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Campaign Gauntlet Guide](docs/campaign_gauntlet_guide.md)
- [Combat System Phase 2](docs/combat_phase2_guide.md)
- [Combat System Phase 3](docs/combat_phase3_guide.md)
- [Character Tracking Guide](docs/CHARACTER_TRACKING_GUIDE.md)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Gaming!** 🎲⚔️🐉
