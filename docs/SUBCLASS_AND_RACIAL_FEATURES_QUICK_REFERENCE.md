# Subclass and Racial Features - Quick Reference

## Available Subclasses

### Fighter
- **Champion** - Critical hit specialist (3, 7, 10, 15, 18)
- **Battle Master** - Tactical maneuvers (3, 7, 10, 15, 18)
- **Eldritch Knight** - Spellcasting warrior (3, 7, 10, 15, 18)

### Wizard
- **School of Evocation** - Damage spell specialist (2, 6, 10, 14)
- **School of Abjuration** - Protective magic (2, 6, 10, 14)

### Rogue
- **Assassin** - Deadly striker (3, 9, 13, 17)
- **Thief** - Skilled infiltrator (3, 9, 13, 17)
- **Arcane Trickster** - Magical rogue (3, 9, 13, 17)

### Cleric
- **Life Domain** - Master healer (1, 2, 6, 8, 17)
- **War Domain** - Combat cleric (1, 2, 6, 8, 17)

### Barbarian
- **Path of the Berserker** - Frenzied warrior (3, 6, 10, 14)
- **Path of the Totem Warrior** - Nature-bonded (3, 6, 10, 14)

### Bard
- **College of Lore** - Knowledge seeker (3, 6, 14)
- **College of Valor** - Combat bard (3, 6, 14)

### Druid
- **Circle of the Land** - Nature magic (2, 6, 10, 14)
- **Circle of the Moon** - Wild shape master (2, 6, 10, 14)

### Monk
- **Way of the Open Hand** - Unarmed master (3, 6, 11, 17)
- **Way of Shadow** - Stealth ninja (3, 6, 11, 17)

### Paladin
- **Oath of Devotion** - Holy knight (3, 7, 15, 20)
- **Oath of Vengeance** - Avenger (3, 7, 15, 20)

### Ranger
- **Hunter** - Versatile combatant (3, 7, 11, 15)
- **Beast Master** - Animal companion (3, 7, 11, 15)

### Sorcerer
- **Draconic Bloodline** - Dragon-touched (1, 6, 14, 18)
- **Wild Magic** - Chaos caster (1, 6, 14, 18)

### Warlock
- **The Fiend** - Infernal pact (1, 6, 10, 14)
- **The Archfey** - Fey pact (1, 6, 10, 14)

## Racial Features Summary

### Human
- +1 to all ability scores
- Extra language

### Elf
- DEX +2
- Darkvision 60 ft
- Perception proficiency
- Advantage vs charm, immune to sleep
- 4-hour rest
- Weapon proficiencies

### Dwarf
- CON +2
- Darkvision 60 ft
- Advantage vs poison, poison resistance
- Weapon proficiencies
- Tool proficiency
- Stonecunning

### Halfling
- DEX +2
- Lucky (reroll 1s)
- Advantage vs frightened
- Move through larger creatures

### Dragonborn
- STR +2, CHA +1
- Breath weapon
- Damage resistance (based on ancestry)

### Gnome
- INT +2
- Darkvision 60 ft
- Advantage on INT/WIS/CHA saves vs magic

### Half-Elf
- CHA +2, two others +1
- Darkvision 60 ft
- Advantage vs charm, immune to sleep
- Two skill proficiencies

### Half-Orc
- STR +2, CON +1
- Darkvision 60 ft
- Intimidation proficiency
- Relentless Endurance (1/long rest)
- Extra crit damage

### Tiefling
- INT +1, CHA +2
- Darkvision 60 ft
- Fire resistance
- Thaumaturgy, Hellish Rebuke, Darkness

## API Endpoints

### Select Subclass
```
POST /api/campaigns/{campaign_id}/select_subclass/
Body: {
    "character_id": 1,
    "subclass": "Champion"
}
```

### Apply Racial Features (for existing characters)
```
POST /api/characters/{character_id}/apply_racial_features/
```

### View Character Features
```
GET /api/characters/{character_id}/
# Features are included in the response under "features" array
```

## When Features Are Applied

### Racial Features
- ✅ Automatically on character creation
- ✅ Manually via API for existing characters

### Class Features
- ✅ Automatically during level-up
- ✅ Stored with source like "Fighter Level 2"

### Subclass Features
- ✅ Automatically during level-up (if subclass is set)
- ✅ Retroactively when subclass is selected
- ✅ Stored with source like "Champion Level 3"

## Subclass Selection Timing

| Class | Subclass Level |
|-------|----------------|
| Cleric | 1 |
| Sorcerer | 1 |
| Warlock | 1 |
| Druid | 2 |
| Wizard | 2 |
| All Others | 3 |

## Example: Creating a Character

```python
# 1. Create character (racial features auto-applied)
POST /api/characters/
{
    "name": "Aragorn",
    "level": 1,
    "character_class_id": 1,  # Ranger
    "race_id": 1,  # Human
    "background_id": 1
}

# 2. Level up to 3 in a campaign
# (class features auto-applied)

# 3. Select subclass
POST /api/campaigns/1/select_subclass/
{
    "character_id": 5,
    "subclass": "Hunter"
}
# (subclass features auto-applied retroactively)

# 4. Continue leveling
# (both class and subclass features auto-applied)
```

## Testing

Run the test suite:
```bash
python test_subclass_and_racial_features.py
```

## Notes

- All features are stored in the `CharacterFeature` model
- Features have a `feature_type` field: 'class', 'racial', 'background', or 'feat'
- Features have a `source` field indicating where they came from
- Subclass selection clears the `pending_subclass_selection` flag
- Features are automatically applied - no manual work needed!

