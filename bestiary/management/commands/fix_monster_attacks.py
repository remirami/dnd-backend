"""
Management command to fix monster attack data from the Open5e API.
Re-imports damage strings, attack bonuses, ability scores, speed, proficiency,
senses, and saving throws for all SRD monsters.

Only updates existing monsters — does not create new ones.
"""
import re
import time
import requests
from django.core.management.base import BaseCommand
from bestiary.models import Enemy, EnemyStats, EnemyAttack, EnemyAbility


def parse_damage_from_desc(desc):
    """
    Parse damage string from action description.
    Examples:
      "...Hit: 21 (4d8 + 3) necrotic damage..." -> "4d8+3 necrotic"
      "...Hit: 7 (2d6) slashing damage..." -> "2d6 slashing"
    """
    # Match: digits (dice_expr) damage_type damage
    match = re.search(
        r'Hit:\s*\d+\s*\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)\s*(\w+)\s+damage',
        desc, re.IGNORECASE
    )
    if match:
        dice = match.group(1).replace(' ', '')
        dmg_type = match.group(2).lower()
        return f"{dice} {dmg_type}"

    # Fallback: just dice without damage type
    match = re.search(r'Hit:\s*\d+\s*\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)', desc)
    if match:
        return match.group(1).replace(' ', '')

    return None


def calc_modifier(score):
    """Calculate ability modifier from score."""
    return (score - 10) // 2


class Command(BaseCommand):
    help = 'Fix monster attack data using the Open5e API (SRD monsters only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be changed without saving'
        )
        parser.add_argument(
            '--monster', type=str, default=None,
            help='Fix a specific monster by name (case-insensitive)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_monster = options.get('monster')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved'))

        # Fetch all SRD monsters from Open5e
        all_api_monsters = []
        url = 'https://api.open5e.com/v1/monsters/?document__slug=wotc-srd&limit=50&format=json'

        self.stdout.write('Fetching monsters from Open5e API...')
        while url:
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                all_api_monsters.extend(data.get('results', []))
                url = data.get('next')
                self.stdout.write(f'  Fetched {len(all_api_monsters)} so far...')
                time.sleep(0.3)  # Rate limiting
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'API error: {e}'))
                break

        self.stdout.write(f'Total API monsters: {len(all_api_monsters)}')

        # Build lookup by name
        api_lookup = {m['name'].lower(): m for m in all_api_monsters}

        # Get DB monsters to fix
        if specific_monster:
            db_monsters = Enemy.objects.filter(name__icontains=specific_monster)
        else:
            db_monsters = Enemy.objects.all()

        stats_fixed = 0
        attacks_fixed = 0
        attacks_removed = 0
        abilities_fixed = 0
        monsters_matched = 0

        for enemy in db_monsters:
            api_data = api_lookup.get(enemy.name.lower())
            if not api_data:
                continue

            monsters_matched += 1
            self.stdout.write(f'\n--- {enemy.name} ---')

            # === Fix Stats ===
            try:
                stats = enemy.stats
            except EnemyStats.DoesNotExist:
                self.stdout.write(f'  No stats record, skipping')
                continue

            changed = False

            # Ability scores
            for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                api_val = api_data.get(ability)
                db_val = getattr(stats, ability)
                if api_val and api_val != db_val:
                    self.stdout.write(f'  {ability}: {db_val} -> {api_val}')
                    if not dry_run:
                        setattr(stats, ability, api_val)
                    changed = True

            # Speed
            api_speed = api_data.get('speed', {})
            speed_parts = []
            if api_speed.get('walk'):
                speed_parts.append(f"{api_speed['walk']} ft.")
            elif api_speed.get('walk') == 0:
                speed_parts.append("0 ft.")
            if api_speed.get('fly'):
                fly_str = f"fly {api_speed['fly']} ft."
                if api_speed.get('hover'):
                    fly_str += " (hover)"
                speed_parts.append(fly_str)
            if api_speed.get('swim'):
                speed_parts.append(f"swim {api_speed['swim']} ft.")
            if api_speed.get('burrow'):
                speed_parts.append(f"burrow {api_speed['burrow']} ft.")
            if api_speed.get('climb'):
                speed_parts.append(f"climb {api_speed['climb']} ft.")

            speed_str = ', '.join(speed_parts) if speed_parts else None
            if speed_str and speed_str != stats.speed:
                self.stdout.write(f'  speed: "{stats.speed}" -> "{speed_str}"')
                if not dry_run:
                    stats.speed = speed_str
                changed = True

            # Proficiency bonus (derived from CR)
            cr = api_data.get('cr', 0)
            if cr is not None:
                prof = max(2, 2 + (int(cr) - 1) // 4) if cr >= 1 else 2
                if stats.proficiency_bonus != prof:
                    self.stdout.write(f'  proficiency: {stats.proficiency_bonus} -> {prof}')
                    if not dry_run:
                        stats.proficiency_bonus = prof
                    changed = True

            # Senses
            senses_str = api_data.get('senses', '')
            if senses_str:
                dv_match = re.search(r'darkvision\s+(\d+\s*ft\.?)', senses_str, re.I)
                if dv_match and stats.darkvision != dv_match.group(1):
                    self.stdout.write(f'  darkvision: {stats.darkvision} -> {dv_match.group(1)}')
                    if not dry_run:
                        stats.darkvision = dv_match.group(1)
                    changed = True

                bs_match = re.search(r'blindsight\s+(\d+\s*ft\.?)', senses_str, re.I)
                if bs_match and stats.blindsight != bs_match.group(1):
                    if not dry_run:
                        stats.blindsight = bs_match.group(1)
                    changed = True

                ts_match = re.search(r'tremorsense\s+(\d+\s*ft\.?)', senses_str, re.I)
                if ts_match and stats.tremorsense != ts_match.group(1):
                    if not dry_run:
                        stats.tremorsense = ts_match.group(1)
                    changed = True

                true_match = re.search(r'truesight\s+(\d+\s*ft\.?)', senses_str, re.I)
                if true_match and stats.truesight != true_match.group(1):
                    if not dry_run:
                        stats.truesight = true_match.group(1)
                    changed = True

                pp_match = re.search(r'passive Perception\s+(\d+)', senses_str, re.I)
                if pp_match:
                    pp_val = int(pp_match.group(1))
                    if stats.passive_perception != pp_val:
                        self.stdout.write(f'  passive_perception: {stats.passive_perception} -> {pp_val}')
                        if not dry_run:
                            stats.passive_perception = pp_val
                        changed = True

            # Saving throws
            for ability_short, save_field in [
                ('strength', 'str_save'), ('dexterity', 'dex_save'),
                ('constitution', 'con_save'), ('intelligence', 'int_save'),
                ('wisdom', 'wis_save'), ('charisma', 'cha_save'),
            ]:
                api_save = api_data.get(f'{ability_short}_save')
                if not dry_run:
                    setattr(stats, save_field, api_save)
                if api_save != getattr(stats, save_field):
                    changed = True

            if changed:
                if not dry_run:
                    stats.save()
                stats_fixed += 1

            # === Fix Attacks ===
            api_actions = api_data.get('actions', []) or []

            # Build set of real attacks from the API (actions that have attack_bonus)
            api_attacks = {}
            for action in api_actions:
                if action.get('attack_bonus') is not None or action.get('damage_dice'):
                    name = action['name']
                    bonus = action.get('attack_bonus', 0) or 0
                    damage = parse_damage_from_desc(action.get('desc', ''))
                    if not damage:
                        # Fallback: build from damage_dice + damage_bonus
                        dd = action.get('damage_dice', '')
                        db = action.get('damage_bonus', 0)
                        if dd:
                            damage = f"{dd}+{db}" if db else dd
                            # Try to get damage type from desc
                            type_match = re.search(r'(\w+)\s+damage', action.get('desc', ''), re.I)
                            if type_match:
                                damage += f" {type_match.group(1).lower()}"
                    if damage:
                        api_attacks[name.lower()] = {
                            'name': name,
                            'bonus': bonus,
                            'damage': damage,
                        }

            # Non-attack actions (Multiattack, breath weapons, etc.)
            api_non_attacks = {}
            for action in api_actions:
                name_lower = action['name'].lower()
                if name_lower not in api_attacks:
                    api_non_attacks[name_lower] = {
                        'name': action['name'],
                        'description': action.get('desc', ''),
                    }

            # Update existing DB attacks and remove fakes
            db_attacks = list(enemy.attacks.all())
            for db_atk in db_attacks:
                name_lower = db_atk.name.lower()

                if name_lower in api_attacks:
                    api_atk = api_attacks[name_lower]
                    if db_atk.damage == '1d4 bludgeoning' or db_atk.bonus != api_atk['bonus'] or db_atk.damage != api_atk['damage']:
                        self.stdout.write(
                            f'  Attack fix: {db_atk.name}: +{db_atk.bonus}/{db_atk.damage}'
                            f' -> +{api_atk["bonus"]}/{api_atk["damage"]}'
                        )
                        if not dry_run:
                            db_atk.bonus = api_atk['bonus']
                            db_atk.damage = api_atk['damage']
                            db_atk.save()
                        attacks_fixed += 1
                    del api_attacks[name_lower]  # Mark as processed

                elif name_lower in api_non_attacks:
                    # This is stored as an attack but should be an ability
                    self.stdout.write(f'  Remove fake attack: {db_atk.name} (not a weapon attack)')
                    if not dry_run:
                        # Move to abilities if not already there
                        if not enemy.abilities.filter(name__iexact=db_atk.name).exists():
                            non_atk = api_non_attacks[name_lower]
                            EnemyAbility.objects.create(
                                enemy=enemy,
                                name=non_atk['name'],
                                description=non_atk['description'],
                            )
                            abilities_fixed += 1
                        db_atk.delete()
                    attacks_removed += 1

                elif name_lower == 'multiattack' and 'multiattack' not in api_attacks:
                    # Multiattack incorrectly stored as an attack
                    self.stdout.write(f'  Remove fake attack: Multiattack')
                    if not dry_run:
                        # Check if there's already a Multiattack ability
                        if not enemy.abilities.filter(name__iexact='Multiattack').exists():
                            # Try to find multiattack description from API
                            ma_desc = api_non_attacks.get('multiattack', {}).get('description', '')
                            if ma_desc:
                                EnemyAbility.objects.create(
                                    enemy=enemy,
                                    name='Multiattack',
                                    description=ma_desc,
                                )
                                abilities_fixed += 1
                        db_atk.delete()
                    attacks_removed += 1

            # Add any attacks from API that don't exist in DB
            for name_lower, api_atk in api_attacks.items():
                if not enemy.attacks.filter(name__iexact=api_atk['name']).exists():
                    self.stdout.write(f'  Add new attack: {api_atk["name"]}: +{api_atk["bonus"]}/{api_atk["damage"]}')
                    if not dry_run:
                        EnemyAttack.objects.create(
                            enemy=enemy,
                            name=api_atk['name'],
                            bonus=api_atk['bonus'],
                            damage=api_atk['damage'],
                        )
                    attacks_fixed += 1

            # === Fix Special Abilities ===
            api_special = api_data.get('special_abilities', []) or []
            for sa in api_special:
                existing = enemy.abilities.filter(name__iexact=sa['name']).first()
                if existing:
                    # Update description if it's short/placeholder
                    if len(existing.description) < len(sa.get('desc', '')):
                        if not dry_run:
                            existing.description = sa['desc']
                            existing.save()
                elif sa.get('desc'):
                    if not dry_run:
                        EnemyAbility.objects.create(
                            enemy=enemy,
                            name=sa['name'],
                            description=sa['desc'],
                        )
                    abilities_fixed += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done! Matched {monsters_matched} monsters. '
            f'Stats fixed: {stats_fixed}, '
            f'Attacks fixed: {attacks_fixed}, '
            f'Fake attacks removed: {attacks_removed}, '
            f'Abilities fixed: {abilities_fixed}'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a dry run — no changes were saved'))
