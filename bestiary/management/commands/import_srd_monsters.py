"""
Automated seeder command for D&D 5e SRD monsters from Open5e API v1.
Parses stats, actions, recharge mechanics, multiattack, traits, resistances, and saving throws
into relational models while ensuring full backwards compatibility.
"""
import re
import urllib.request
import json
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
    EnemyConditionImmunity,
    EnemyLanguage,
    EnemyLegendaryAction,
    EnemyMultiattack,
    EnemyResistance,
    EnemyStats,
    EnemyTrait,
    Language,
)
from bestiary.parsers.action_parser import (
    parse_action,
    parse_multiattack,
    parse_trait,
)


class Command(BaseCommand):
    help = 'Import and update official D&D 5e SRD monsters from Open5e API with structured actions'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Limit number of monsters to import')
        parser.add_argument('--search', type=str, default=None, help='Filter monsters by name search')

    def handle(self, *args, **options):
        limit = options.get('limit')
        search = options.get('search')

        self.stdout.write(self.style.NOTICE("Fetching SRD monsters from Open5e API v1..."))

        base_url = "https://api.open5e.com/v1/monsters/?document__slug=wotc-srd"
        if search:
            base_url += f"&search={urllib.parse.quote(search)}"

        monsters_data = []
        url = base_url
        page = 1

        headers = {'User-Agent': 'D&D-5e-Campaign-Manager/1.8'}

        while url:
            self.stdout.write(f"  Fetching page {page}...")
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    results = data.get('results', [])
                    monsters_data.extend(results)
                    url = data.get('next')
                    page += 1
                    if limit and len(monsters_data) >= limit:
                        monsters_data = monsters_data[:limit]
                        break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching page {page}: {e}"))
                break

        self.stdout.write(f"Downloaded {len(monsters_data)} monsters. Saving to database...")
        self.process_monsters(monsters_data)

    def process_monsters(self, monsters_data):
        damage_types = {dt.name.lower(): dt for dt in DamageType.objects.all()}
        conditions = {c.name.lower(): c for c in Condition.objects.all()}

        imported_count = 0

        with transaction.atomic():
            for m in monsters_data:
                name = m.get('name', '').strip()
                if not name:
                    continue

                size_raw = (m.get('size') or 'Medium').strip().upper()
                size_map = {'TINY': 'T', 'SMALL': 'S', 'MEDIUM': 'M', 'LARGE': 'L', 'HUGE': 'H', 'GARGANTUAN': 'G'}
                size = size_map.get(size_raw, 'M')

                creature_type = (m.get('type') or 'humanoid').lower().strip()
                valid_types = [
                    'aberration', 'beast', 'celestial', 'construct', 'dragon', 'elemental',
                    'fey', 'fiend', 'giant', 'humanoid', 'monstrosity', 'ooze', 'plant', 'undead'
                ]
                if creature_type not in valid_types:
                    creature_type = 'humanoid'

                align_raw = (m.get('alignment') or 'unaligned').lower()
                alignment = 'U'
                align_map = {
                    'lawful good': 'LG', 'neutral good': 'NG', 'chaotic good': 'CG',
                    'lawful neutral': 'LN', 'neutral': 'N', 'true neutral': 'N', 'chaotic neutral': 'CN',
                    'lawful evil': 'LE', 'neutral evil': 'NE', 'chaotic evil': 'CE',
                    'unaligned': 'U'
                }
                for k, v in align_map.items():
                    if k in align_raw:
                        alignment = v
                        break

                hp = m.get('hit_points') or 10
                ac = m.get('armor_class') or 10
                cr = str(m.get('challenge_rating') or '1')

                enemy, _ = Enemy.objects.update_or_create(
                    name=name,
                    defaults={
                        'hp': hp,
                        'ac': ac,
                        'challenge_rating': cr,
                        'size': size,
                        'creature_type': creature_type,
                        'alignment': alignment,
                    }
                )

                # Stats
                speed_str = ""
                if isinstance(m.get('speed'), dict):
                    speed_parts = [f"{k} {v} ft." if k != 'walk' else f"{v} ft." for k, v in m.get('speed').items() if v]
                    speed_str = ", ".join(speed_parts)
                elif m.get('speed'):
                    speed_str = str(m.get('speed'))

                EnemyStats.objects.update_or_create(
                    enemy=enemy,
                    defaults={
                        'strength': m.get('strength') or 10,
                        'dexterity': m.get('dexterity') or 10,
                        'constitution': m.get('constitution') or 10,
                        'intelligence': m.get('intelligence') or 10,
                        'wisdom': m.get('wisdom') or 10,
                        'charisma': m.get('charisma') or 10,
                        'hit_points': hp,
                        'armor_class': ac,
                        'speed': speed_str,
                        'str_save': m.get('strength_save'),
                        'dex_save': m.get('dexterity_save'),
                        'con_save': m.get('constitution_save'),
                        'int_save': m.get('intelligence_save'),
                        'wis_save': m.get('wisdom_save'),
                        'cha_save': m.get('charisma_save'),
                        'perception': m.get('skills', {}).get('perception') if isinstance(m.get('skills'), dict) else m.get('perception'),
                        'stealth': m.get('skills', {}).get('stealth') if isinstance(m.get('skills'), dict) else m.get('stealth'),
                        'athletics': m.get('skills', {}).get('athletics') if isinstance(m.get('skills'), dict) else m.get('athletics'),
                        'hit_dice': m.get('hit_dice'),
                    }
                )

                # Clear previous action items for fresh sync
                EnemyActionDamage.objects.filter(action__enemy=enemy).delete()
                EnemyAction.objects.filter(enemy=enemy).delete()
                EnemyMultiattack.objects.filter(enemy=enemy).delete()
                EnemyTrait.objects.filter(enemy=enemy).delete()
                EnemyAttack.objects.filter(enemy=enemy).delete()
                EnemyAbility.objects.filter(enemy=enemy).delete()

                # Process Actions
                actions = m.get('actions') or []
                for act in actions:
                    act_name = act.get('name', '')
                    act_desc = act.get('desc', '')

                    # Multiattack
                    if 'multiattack' in act_name.lower():
                        parsed_multi = parse_multiattack(act_name, act_desc)
                        EnemyMultiattack.objects.create(
                            enemy=enemy,
                            description=act_desc,
                            action_count=parsed_multi['action_count'],
                            sequence=parsed_multi['sequence'],
                        )
                        # Keep in abilities for backwards compatibility
                        EnemyAbility.objects.create(enemy=enemy, name=act_name, description=act_desc)
                        continue

                    # Parse action
                    parsed = parse_action(
                        act_name,
                        act_desc,
                        raw_attack_bonus=act.get('attack_bonus'),
                        raw_damage_dice=act.get('damage_dice')
                    )

                    action_obj = EnemyAction.objects.create(
                        enemy=enemy,
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

                    # Backwards compatibility: create EnemyAttack
                    if parsed['attack_bonus'] is not None or parsed['damage_rolls']:
                        dmg_str = ""
                        if parsed['damage_rolls']:
                            dmg_str = parsed['damage_rolls'][0].get('damage_type_name', '')
                            d0 = parsed['damage_rolls'][0]
                            b_str = f"+{d0['damage_bonus']}" if d0['damage_bonus'] > 0 else ""
                            dmg_str = f"{d0['dice_count']}d{d0['dice_sides']}{b_str} {dmg_str}".strip()
                        EnemyAttack.objects.create(
                            enemy=enemy,
                            name=parsed['name'],
                            bonus=parsed['attack_bonus'] or 0,
                            damage=dmg_str or '1d6 bludgeoning'
                        )

                # Special abilities -> Traits
                special_abilities = m.get('special_abilities') or []
                for sa in special_abilities:
                    sa_name = sa.get('name', '')
                    sa_desc = sa.get('desc', '')
                    t = parse_trait(sa_name, sa_desc)
                    EnemyTrait.objects.create(
                        enemy=enemy,
                        name=t['name'],
                        description=t['description'],
                        trait_type=t['trait_type'],
                    )
                    EnemyAbility.objects.create(enemy=enemy, name=sa_name, description=sa_desc)

                # Legendary actions
                legendary = m.get('legendary_actions') or []
                for leg in legendary:
                    leg_name = leg.get('name', '')
                    leg_desc = leg.get('desc', '')
                    parsed_leg = parse_action(leg_name, leg_desc, action_category='legendary_action')
                    leg_obj = EnemyAction.objects.create(
                        enemy=enemy,
                        name=parsed_leg['name'],
                        description=parsed_leg['description'],
                        action_type='legendary_action',
                        attack_type=parsed_leg['attack_type'],
                        attack_bonus=parsed_leg['attack_bonus'],
                        reach_or_range=parsed_leg['reach_or_range'],
                        saving_throw_dc=parsed_leg['saving_throw_dc'],
                        saving_throw_ability=parsed_leg['saving_throw_ability'],
                        half_damage_on_save=parsed_leg['half_damage_on_save'],
                        has_recharge=parsed_leg['has_recharge'],
                        recharge_min_roll=parsed_leg['recharge_min_roll'],
                        condition_save_end=parsed_leg['condition_save_end'],
                        legendary_cost=parsed_leg['legendary_cost'],
                    )
                    for dmg in parsed_leg['damage_rolls']:
                        dt_obj = None
                        if dmg.get('damage_type_name'):
                            dt_obj = damage_types.get(dmg['damage_type_name'].lower())
                        EnemyActionDamage.objects.create(
                            action=leg_obj,
                            dice_count=dmg['dice_count'],
                            dice_sides=dmg['dice_sides'],
                            damage_bonus=dmg['damage_bonus'],
                            damage_type=dt_obj,
                            is_secondary=dmg['is_secondary'],
                        )
                    EnemyLegendaryAction.objects.update_or_create(
                        enemy=enemy,
                        name=leg_name,
                        defaults={'description': leg_desc, 'cost': parsed_leg['legendary_cost']}
                    )

                imported_count += 1

        self.stdout.write(self.style.SUCCESS(f"Finished! Imported/updated {imported_count} SRD monsters with full structured actions."))
