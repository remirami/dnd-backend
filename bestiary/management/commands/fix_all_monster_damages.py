"""
Management command to fix all monster attack damages, action parsing, and multiattack definitions
across the entire bestiary database.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from django.core.management.base import BaseCommand
from django.db import transaction

from bestiary.models import (
    Condition,
    DamageType,
    Enemy,
    EnemyAbility,
    EnemyAction,
    EnemyActionDamage,
    EnemyAttack,
    EnemyMultiattack,
    EnemyStats,
    EnemyTrait,
)
from bestiary.parsers.action_parser import (
    parse_action,
    parse_multiattack,
    parse_trait,
)


class Command(BaseCommand):
    help = 'Fix all monster attack damages from Open5e and synthesize sensible stats for remaining monsters'

    def add_arguments(self, parser):
        parser.add_argument('--limit-pages', type=int, default=None, help='Limit number of Open5e pages to fetch')
        parser.add_argument('--offline-only', action='store_true', help='Do not fetch from API; only fix DB heuristics')

    def handle(self, *args, **options):
        limit_pages = options.get('limit_pages')
        offline_only = options.get('offline_only')

        self.stdout.write(self.style.NOTICE("=== Step 1: Cleaning up bogus 'Multiattack' attacks and actions ==="))
        deleted_atks = EnemyAttack.objects.filter(name__icontains='multiattack').delete()
        deleted_acts = EnemyAction.objects.filter(name__icontains='multiattack').delete()
        self.stdout.write(f"Deleted {deleted_atks[0]} Multiattack attacks and {deleted_acts[0]} Multiattack actions.")

        damage_types = {dt.name.lower(): dt for dt in DamageType.objects.all()}
        conditions = {c.name.lower(): c for c in Condition.objects.all()}

        if not offline_only:
            self.stdout.write(self.style.NOTICE("\n=== Step 2: Fetching full Open5e monster dataset to fix damage formulas ==="))
            url = "https://api.open5e.com/v1/monsters/?limit=100"
            page = 1
            headers = {'User-Agent': 'D&D-Campaign-Engine/1.9'}
            updated_monsters = 0

            while url:
                self.stdout.write(f"  Fetching Open5e page {page}...")
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        results = data.get('results', [])
                        url = data.get('next')

                        # Update matching monsters in DB
                        with transaction.atomic():
                            for m in results:
                                name = m.get('name', '').strip()
                                if not name:
                                    continue

                                # Match by name (case-insensitive)
                                db_enemy = Enemy.objects.filter(name__iexact=name).first()
                                if not db_enemy:
                                    continue

                                actions = m.get('actions') or []
                                if not actions:
                                    continue

                                # Wipe existing structured actions to prevent duplicates
                                EnemyActionDamage.objects.filter(action__enemy=db_enemy).delete()
                                EnemyAction.objects.filter(enemy=db_enemy).delete()
                                EnemyAttack.objects.filter(enemy=db_enemy).delete()

                                for act in actions:
                                    act_name = act.get('name', '').strip()
                                    act_desc = act.get('desc', '').strip()
                                    if not act_name:
                                        continue

                                    # Multiattack handling
                                    if 'multiattack' in act_name.lower():
                                        parsed_multi = parse_multiattack(act_name, act_desc)
                                        EnemyMultiattack.objects.update_or_create(
                                            enemy=db_enemy,
                                            defaults={
                                                'description': act_desc,
                                                'action_count': parsed_multi['action_count'],
                                                'sequence': [
                                                    item for item in parsed_multi['sequence']
                                                    if 'multiattack' not in item.get('action_name', '').lower()
                                                ],
                                            }
                                        )
                                        continue

                                    parsed = parse_action(
                                        act_name,
                                        act_desc,
                                        raw_attack_bonus=act.get('attack_bonus'),
                                        raw_damage_dice=act.get('damage_dice')
                                    )

                                    action_obj = EnemyAction.objects.create(
                                        enemy=db_enemy,
                                        name=parsed['name'],
                                        description=parsed['description'],
                                        action_type=parsed['action_type'],
                                        attack_type=parsed['attack_type'],
                                        attack_bonus=parsed['attack_bonus'],
                                        reach_or_range=parsed['reach_or_range'],
                                        saving_throw_dc=parsed['saving_throw_dc'],
                                        saving_throw_ability=parsed['saving_throw_ability'],
                                        half_damage_on_save=parsed['half_damage_on_save'],
                                        has_recharge=parsed['has_recharge'],
                                        recharge_min_roll=parsed['recharge_min_roll'],
                                        condition_save_end=parsed['condition_save_end'],
                                        legendary_cost=parsed['legendary_cost'],
                                    )

                                    for cname in parsed['conditions_inflicted']:
                                        cobj = conditions.get(cname.lower())
                                        if cobj:
                                            action_obj.conditions_inflicted.add(cobj)

                                    for dmg in parsed['damage_rolls']:
                                        dt_obj = None
                                        if dmg.get('damage_type_name'):
                                            dt_obj = damage_types.get(dmg['damage_type_name'].lower())
                                            if not dt_obj:
                                                dt_obj, _ = DamageType.objects.get_or_create(name=dmg['damage_type_name'].lower())
                                                damage_types[dmg['damage_type_name'].lower()] = dt_obj

                                        EnemyActionDamage.objects.create(
                                            action=action_obj,
                                            dice_count=dmg['dice_count'],
                                            dice_sides=dmg['dice_sides'],
                                            damage_bonus=dmg['damage_bonus'],
                                            damage_type=dt_obj,
                                            is_secondary=dmg['is_secondary'],
                                        )

                                    # Also maintain updated EnemyAttack for backwards compatibility
                                    if parsed['attack_type'] in ['melee_weapon', 'ranged_weapon', 'melee_spell', 'ranged_spell']:
                                        dmg_str = ""
                                        if parsed['damage_rolls']:
                                            dmg_str = parsed['damage_rolls'][0].get('damage_type_name', '')
                                            d0 = parsed['damage_rolls'][0]
                                            b_str = f"+{d0['damage_bonus']}" if d0['damage_bonus'] > 0 else (f"{d0['damage_bonus']}" if d0['damage_bonus'] < 0 else "")
                                            dmg_str = f"{d0['dice_count']}d{d0['dice_sides']}{b_str} {dmg_str}".strip()
                                        EnemyAttack.objects.create(
                                            enemy=db_enemy,
                                            name=parsed['name'],
                                            bonus=parsed['attack_bonus'] or 0,
                                            damage=dmg_str or '1d6 bludgeoning'
                                        )

                                updated_monsters += 1

                        page += 1
                        if limit_pages and page > limit_pages:
                            break
                        time.sleep(0.2)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching page {page}: {e}"))
                    break

            self.stdout.write(self.style.SUCCESS(f"Finished Open5e sync! Updated {updated_monsters} monsters with real action data."))

        # Step 3: Fix any remaining 1d4 bludgeoning attacks using monster ability modifiers
        self.stdout.write(self.style.NOTICE("\n=== Step 3: Auditing remaining monsters for placeholder 1d4 bludgeoning ==="))
        flawed_attacks = EnemyAttack.objects.filter(damage__iexact='1d4 bludgeoning').select_related('enemy', 'enemy__stats')
        fixed_heuristics = 0

        with transaction.atomic():
            for atk in flawed_attacks:
                enemy = atk.enemy
                stats = getattr(enemy, 'stats', None)
                if not stats:
                    continue

                str_mod = stats.strength_modifier
                dex_mod = stats.dexterity_modifier
                mod = max(str_mod, dex_mod)
                mod_str = f"+{mod}" if mod > 0 else (f"{mod}" if mod < 0 else "")

                name_lower = atk.name.lower()
                dtype = 'bludgeoning'
                dice = '1d8'

                if any(w in name_lower for w in ['bite', 'beak', 'pierce', 'spear', 'javelin', 'arrow', 'bolt', 'rapier', 'dagger', 'shortsword']):
                    dtype = 'piercing'
                    dice = '1d6' if enemy.size in ['T', 'S', 'M'] else '2d6'
                elif any(w in name_lower for w in ['claw', 'slash', 'scimitar', 'greatsword', 'greataxe', 'halberd', 'talon']):
                    dtype = 'slashing'
                    dice = '1d8' if enemy.size in ['T', 'S', 'M'] else '2d8'
                elif any(w in name_lower for w in ['slam', 'club', 'greatclub', 'hammer', 'tail', 'fist', 'tentacle']):
                    dtype = 'bludgeoning'
                    dice = '1d8' if enemy.size in ['T', 'S', 'M'] else '2d8'

                if enemy.size in ['H', 'G']:
                    dice = '3d8' if '8' in dice else '3d6'

                new_dmg = f"{dice}{mod_str} {dtype}".strip()
                atk.damage = new_dmg
                if atk.bonus == 0 and (mod + 2) > 0:
                    atk.bonus = mod + (stats.proficiency_bonus or 2)
                atk.save(update_fields=['damage', 'bonus'])

                # Synchronize with EnemyAction if exists
                action_obj = EnemyAction.objects.filter(enemy=enemy, name__iexact=atk.name).first()
                if action_obj:
                    if action_obj.attack_bonus == 0 or action_obj.attack_bonus is None:
                        action_obj.attack_bonus = atk.bonus
                        action_obj.save(update_fields=['attack_bonus'])
                    
                    dt_obj = damage_types.get(dtype)
                    # Update damage rolls
                    dmgs = action_obj.damage_rolls.all()
                    if dmgs.count() == 1 and dmgs[0].dice_count == 1 and dmgs[0].dice_sides == 4:
                        m_dice = re.match(r'(\d+)d(\d+)', dice)
                        if m_dice:
                            d_roll = dmgs[0]
                            d_roll.dice_count = int(m_dice.group(1))
                            d_roll.dice_sides = int(m_dice.group(2))
                            d_roll.damage_bonus = max(0, mod)
                            d_roll.damage_type = dt_obj
                            d_roll.save()

                fixed_heuristics += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully repaired {fixed_heuristics} placeholder attacks with authentic ability-scaled dice!"))
