# 🚀 Quick Import Reference

## One-Line Commands

### Import Everything
```bash
# Install requirements
pip install requests

# Import all monsters and items (takes 5-10 minutes)
python manage.py import_monsters_from_api --source open5e && python manage.py import_items_from_api --source open5e
```

### Import for Testing
```bash
# Quick test import (takes ~30 seconds)
python manage.py import_monsters_from_api --source open5e --limit 20 && python manage.py import_items_from_api --source open5e --limit 30
```

### Import by Level Range
```bash
# Low-level content (CR 0-5)
python manage.py import_monsters_from_api --source open5e --cr-max 5

# Mid-level content (CR 6-10)
python manage.py import_monsters_from_api --source open5e --cr-min 6 --cr-max 10

# High-level content (CR 11+)
python manage.py import_monsters_from_api --source open5e --cr-min 11
```

## Verify Imports

```bash
python manage.py shell
```

```python
# Check monster count
from bestiary.models import Enemy
print(f"Monsters: {Enemy.objects.count()}")

# Check item count
from items.models import Item, Weapon, Armor, MagicItem
print(f"Total Items: {Item.objects.count()}")
print(f"Weapons: {Weapon.objects.count()}")
print(f"Armor: {Armor.objects.count()}")
print(f"Magic Items: {MagicItem.objects.count()}")

# Sample monsters by CR
for cr in ['1/4', '1', '5', '10']:
    count = Enemy.objects.filter(challenge_rating=cr).count()
    print(f"CR {cr}: {count} monsters")
```

## Test Integration

### Test Treasure System
```python
from campaigns.models import Campaign
from campaigns.utils import TreasureGenerator

# Create test campaign
campaign = Campaign.objects.create(name="Treasure Test", starting_level=1)

# Generate treasure room
treasure = TreasureGenerator.generate_treasure_room(campaign, 1)

# Check rewards
print(f"Room Type: {treasure.room_type}")
print(f"Rewards: {treasure.rewards}")

# Check individual rewards
for reward in treasure.treasureroomreward_set.all():
    if reward.item:
        print(f"- {reward.item.name} x{reward.quantity}")
    if reward.gold_amount:
        print(f"- {reward.gold_amount} gold")
```

### Test Encounter Generation
```python
from campaigns.models import Campaign
from campaigns.utils import CampaignGenerator

# Create test campaign
campaign = Campaign.objects.create(name="Encounter Test", starting_level=1)

# Populate with encounters
CampaignGenerator.populate_campaign(campaign, num_encounters=5)

# Check generated encounters
for ce in campaign.campaign_encounters.all():
    print(f"\nEncounter {ce.encounter_number}:")
    for ee in ce.encounter.encounter_enemies.all():
        print(f"  - {ee.quantity}x {ee.enemy.name} (CR {ee.enemy.challenge_rating})")
```

## Common Workflows

### Setup New Database
```bash
# 1. Base setup
python manage.py migrate
python manage.py populate_dnd_data
python manage.py populate_character_data
python manage.py populate_items

# 2. Import API content
python manage.py import_monsters_from_api --source open5e
python manage.py import_items_from_api --source open5e

# 3. Create superuser
python manage.py createsuperuser

# 4. Start server
python manage.py runserver
```

### Update Existing Database
```bash
# Update monsters
python manage.py import_monsters_from_api --source open5e --update-existing

# Update items
python manage.py import_items_from_api --source open5e --update-existing
```

### Selective Import
```bash
# Only import what you need
python manage.py import_monsters_from_api --source open5e --cr-max 3  # Starter monsters
python manage.py import_items_from_api --source open5e --limit 50      # Limited items
```

## Troubleshooting

### Connection Issues
```bash
# Test API connection
curl https://api.open5e.com/monsters/?limit=1

# If fails, check internet or try again later
```

### Missing Dependencies
```bash
# Install missing packages
pip install requests

# Verify installation
python -c "import requests; print('OK')"
```

### Database Issues
```bash
# Check migrations
python manage.py showmigrations

# Apply missing migrations
python manage.py migrate

# Check for errors
python manage.py check
```

## Performance Tips

- **Use --limit for testing**: Start with `--limit 10` to test
- **Import in batches**: Import by CR range for better control
- **Run overnight**: Full import takes 5-10 minutes
- **Check progress**: Use `--dry-run` first to preview

## Quick Stats

After full import, you should have approximately:

- **Monsters**: 200-300 creatures
- **Weapons**: 30-50 weapons
- **Armor**: 10-20 armor pieces
- **Magic Items**: 50-100 magic items
- **Total Items**: 100-200 items

---

**Need more details?** See [API Import Guide](api_import_guide.md)

