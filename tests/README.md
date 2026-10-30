# Test Suite Organization

## 📂 Test Directory Structure

All test files have been organized into the `tests/` directory for better project structure and maintainability.

```
tests/
├── __init__.py
├── test_all_classes.py
├── test_api_integration.py
├── test_asi_and_subclass.py
├── test_authentication.py
├── test_background_feats_reactions.py
├── test_campaign_gauntlet.py
├── test_combat.py
├── test_combat_logging.py
├── test_environmental_effects.py
├── test_import_simple.py
├── test_level_up_features.py
├── test_multiclassing.py
├── test_roguelite_features.py
├── test_spell_management.py
└── test_subclass_and_racial_features.py
```

## 🧪 Test Suite Descriptions

### Authentication & API
- **test_authentication.py** - Complete authentication system testing
  - User registration and login
  - JWT token generation and refresh
  - Protected endpoint access
  - Data isolation between users
  
- **test_api_integration.py** - Full API integration tests
  - Treasure system integration
  - Encounter generation
  - Database content verification

### Character System
- **test_all_classes.py** - Verifies all 12 SRD 5.2 classes have features defined
  
- **test_subclass_and_racial_features.py** - Character features testing
  - Racial feature application
  - Subclass feature application
  - Feature application during level-up
  
- **test_level_up_features.py** - Level progression system
  - Class features at each level
  - Hit dice tracking
  - Feature application
  
- **test_asi_and_subclass.py** - ASI and subclass mechanics
  - Ability Score Increase selection
  - Subclass selection at appropriate levels
  - Feature tracking

- **test_background_feats_reactions.py** - Additional character features
  - Background feature application
  - Feat system with prerequisites
  - Reaction mechanics in combat

### Advanced Character Features
- **test_multiclassing.py** - Multiclass system
  - Multiclass prerequisites
  - Level tracking across classes
  - Spell slot calculation for multiclass casters
  - Hit dice calculation
  - Spellcasting ability determination
  
- **test_spell_management.py** - Spell system
  - Prepared vs. known caster mechanics
  - Spell preparation limits
  - Spell learning limits
  - Wizard spellbook management
  - Ritual casting

### Combat System
- **test_combat.py** - Complete combat system (Phases 1-3)
  - Core combat mechanics
  - Spell casting in combat
  - Saving throws
  - Conditions
  - Concentration spells
  - Opportunity attacks
  - Death saving throws
  - Legendary actions
  
- **test_environmental_effects.py** - Environmental combat mechanics
  - Difficult terrain movement costs
  - Cover AC bonuses
  - Lighting effects on attacks
  - Weather effects on ranged attacks
  - Hazard damage
  - Position tracking
  
- **test_combat_logging.py** - Combat log system
  - Combat statistics
  - Full combat reports
  - JSON/CSV export
  - Log analytics
  - Character combat statistics

### Campaign System
- **test_campaign_gauntlet.py** - Roguelike gauntlet campaign
  - Campaign creation and management
  - Character addition to campaigns
  - Encounter progression
  - Party status tracking
  - Short and long rests
  
- **test_roguelite_features.py** - Roguelite features
  - Starting level selection
  - XP tracking and automatic level-up
  - Treasure room generation
  - Manual XP granting
  - Level progression through encounters

### Data Import
- **test_import_simple.py** - Data import verification
  - Monster import verification
  - Item import verification
  - Treasure generation testing
  - Encounter generation testing

## 🚀 Running Tests

### Run All Tests
```bash
python manage.py test
```

### Run Specific Test File
```bash
# From project root
python tests/test_authentication.py
python tests/test_combat.py
python tests/test_campaign_gauntlet.py
python tests/test_multiclassing.py
python tests/test_spell_management.py
```

### Run Category of Tests
```bash
# Character system tests
python tests/test_subclass_and_racial_features.py
python tests/test_level_up_features.py
python tests/test_multiclassing.py
python tests/test_spell_management.py

# Combat system tests
python tests/test_combat.py
python tests/test_environmental_effects.py
python tests/test_combat_logging.py

# Campaign system tests
python tests/test_campaign_gauntlet.py
python tests/test_roguelite_features.py
```

## ✅ Test Coverage

All major systems have comprehensive test coverage:

- ✅ **Authentication** - User registration, login, JWT tokens, data isolation
- ✅ **Character Creation** - All classes, races, backgrounds
- ✅ **Character Progression** - Level-up, features, ASI, subclasses
- ✅ **Multiclassing** - Prerequisites, spell slots, hit dice
- ✅ **Spell System** - Preparation, learning, spellbook, rituals
- ✅ **Combat (Phase 1)** - Initiative, attacks, damage, turns
- ✅ **Combat (Phase 2)** - Spells, saving throws, conditions
- ✅ **Combat (Phase 3)** - Concentration, reactions, death saves, legendary actions
- ✅ **Environmental Effects** - Terrain, cover, lighting, weather
- ✅ **Combat Logging** - Statistics, reports, analytics, export
- ✅ **Campaign System** - Gauntlet progression, XP, treasure, rests
- ✅ **Data Import** - Monsters, items, validation

## 📊 Test Statistics

- **Total Test Files**: 15
- **Test Categories**: 5 (Auth/API, Character, Combat, Campaign, Import)
- **Systems Tested**: 12+ major systems
- **Test Lines of Code**: 5,000+ lines
- **Coverage**: All critical paths tested

## 🔧 Test Maintenance

All tests have been updated to work from the `tests/` directory:
- ✅ Import paths corrected with `sys.path.append()`
- ✅ Django settings properly configured
- ✅ Database cleanup implemented where needed
- ✅ Tests are idempotent (can be run multiple times)

## 📝 Notes

- Tests use SQLite database (created automatically)
- Some tests require Django server to be running (API tests)
- Tests create and clean up their own test data
- All tests include detailed output for debugging

---

**Last Updated**: December 31, 2025
**Status**: All tests passing ✅
