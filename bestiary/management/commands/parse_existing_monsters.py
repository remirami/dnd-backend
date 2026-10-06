"""
Management command to parse and upgrade existing monsters in the database
to the new structured EnemyAction, EnemyActionDamage, EnemyMultiattack, and EnemyTrait models.
"""
import re
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
    EnemyLegendaryAction,
    EnemyMultiattack,
    EnemyTrait,
)
from bestiary.parsers.action_parser import (
    parse_action,
    parse_multiattack,
    parse_trait,
    parse_damage_formula,
    parse_recharge,
    DAMAGE_TYPES,
)


def is_reaction(name: str, desc: str) -> bool:
    n = name.lower()
    d = desc.lower()
    return '(reaction)' in n or n.endswith('reaction') or d.startswith('as a reaction')


def is_bonus_action(name: str, desc: str) -> bool:
    n = name.lower()
    d = desc.lower()
    return (
        'bonus action' in n or
        'as a bonus action' in d or
        n in ['nimble escape', 'aggressive', 'shadow stealth']
    )


def is_active_action(name: str, desc: str) -> bool:
    n = name.lower()
    d = desc.lower()
    keywords = [
        'breath', 'recharge', 'presence', 'spellcasting', 'gaze', 'roar',
        'howl', 'spores', 'web', 'swallow', 'cloud', 'burst', 'touch',
        'drain', 'spray', 'tentacle', 'slime', 'frightful'
    ]
    if any(k in n for k in keywords):
        return True
    if 'as an action' in d or 'costs 1 action' in d:
        return True
    if 'saving throw' in d and ('each creature' in d or 'target must succeed' in d or 'target takes' in d):
        return True
    return False


class Command(BaseCommand):
    help = 'Parse existing monsters into structured EnemyAction, Multiattack, and Trait models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of monsters to process'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing structured actions and traits before processing'
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        clear = options.get('clear_existing', False)

        self.stdout.write(self.style.NOTICE("Beginning monster parsing into structured models..."))

        if clear:
            self.stdout.write("Clearing existing structured actions, damages, multiattacks, and traits...")
            EnemyActionDamage.objects.all().delete()
            EnemyAction.objects.all().delete()
            EnemyMultiattack.objects.all().delete()
            EnemyTrait.objects.all().delete()

        # Cache damage types and conditions for fast lookups
        damage_types = {dt.name.lower(): dt for dt in DamageType.objects.all()}
        conditions = {c.name.lower(): c for c in Condition.objects.all()}

        enemies_qs = Enemy.objects.all().prefetch_related(
            'attacks', 'abilities', 'legendary_actions'
        ).select_related('stats')
        if limit:
            enemies_qs = enemies_qs[:limit]

        total_enemies = enemies_qs.count()
        self.stdout.write(f"Processing {total_enemies} monsters...")

        actions_created = 0
        damage_rolls_created = 0
        multiattacks_created = 0
        traits_created = 0
        legendary_created = 0

        batch_size = 100
        processed = 0

        with transaction.atomic():
            for enemy in enemies_qs.iterator(chunk_size=batch_size):
                processed += 1
                if processed % 50 == 0 or processed == total_enemies:
                    self.stdout.write(f"  Processed {processed}/{total_enemies} monsters...")

                # Clean up existing structured records for this enemy to guarantee idempotency
                EnemyActionDamage.objects.filter(action__enemy=enemy).delete()
                EnemyAction.objects.filter(enemy=enemy).delete()
                EnemyTrait.objects.filter(enemy=enemy).delete()

                stats = getattr(enemy, 'stats', None)
                prof = (stats.proficiency_bonus if stats and stats.proficiency_bonus else 2)
                con_mod = (stats.constitution_modifier if stats and stats.constitution_modifier is not None else 2)
                default_dc = 8 + prof + con_mod

                existing_action_names = set()

                # 1. Process Abilities -> Multiattack, Legendary Action, Special Action, or Trait
                for ability in enemy.abilities.all():
                    ab_name = ability.name.strip()
                    ab_desc = ability.description.strip()
                    ab_name_lower = ab_name.lower()

                    # 1A. Check for Multiattack
                    if 'multiattack' in ab_name_lower:
                        parsed_multi = parse_multiattack(ab_name, ab_desc)
                        EnemyMultiattack.objects.update_or_create(
                            enemy=enemy,
                            defaults={
                                'description': ab_desc,
                                'action_count': parsed_multi['action_count'],
                                'sequence': parsed_multi['sequence'],
                            }
                        )
                        multiattacks_created += 1
                        continue

                    # 1B. Check for Legendary Action [Legendary]
                    if ab_name_lower.startswith('[legendary]'):
                        clean_name = re.sub(r'^\[legendary\]\s*', '', ab_name, flags=re.IGNORECASE).strip()
                        cost_match = re.search(r'\(Costs\s+(\d+)\s+Actions?\)', clean_name, re.IGNORECASE)
                        cost = int(cost_match.group(1)) if cost_match else 1
                        clean_name = re.sub(r'\(Costs\s+\d+\s+Actions?\)', '', clean_name, flags=re.IGNORECASE).strip()

                        action_data = parse_action(
                            clean_name,
                            ab_desc,
                            action_category='legendary_action'
                        )
                        action_obj = EnemyAction.objects.create(
                            enemy=enemy,
                            name=action_data['name'],
                            description=action_data['description'],
                            action_type='legendary_action',
                            attack_type=action_data['attack_type'],
                            attack_bonus=action_data['attack_bonus'],
                            reach_or_range=action_data['reach_or_range'],
                            saving_throw_dc=action_data['saving_throw_dc'] or (default_dc if action_data['attack_type'] == 'saving_throw' else None),
                            saving_throw_ability=action_data['saving_throw_ability'] or ('DEX' if action_data['attack_type'] == 'saving_throw' else None),
                            half_damage_on_save=action_data['half_damage_on_save'],
                            has_recharge=action_data['has_recharge'],
                            recharge_min_roll=action_data['recharge_min_roll'],
                            condition_save_end=action_data['condition_save_end'],
                            legendary_cost=cost,
                        )
                        actions_created += 1
                        existing_action_names.add(action_data['name'].lower())

                        # Also sync to EnemyLegendaryAction model
                        EnemyLegendaryAction.objects.update_or_create(
                            enemy=enemy,
                            name=action_data['name'],
                            defaults={
                                'description': ab_desc,
                                'cost': cost,
                            }
                        )
                        legendary_created += 1

                        # Link conditions
                        for cond_name in action_data['conditions_inflicted']:
                            cond_obj = conditions.get(cond_name.lower())
                            if cond_obj:
                                action_obj.conditions_inflicted.add(cond_obj)

                        # Create damage rolls
                        for dmg_data in action_data['damage_rolls']:
                            dtype = None
                            if dmg_data.get('damage_type_name'):
                                dtype = damage_types.get(dmg_data['damage_type_name'].lower())
                                if not dtype:
                                    dtype, _ = DamageType.objects.get_or_create(name=dmg_data['damage_type_name'].lower())
                                    damage_types[dmg_data['damage_type_name'].lower()] = dtype

                            EnemyActionDamage.objects.create(
                                action=action_obj,
                                dice_count=dmg_data['dice_count'],
                                dice_sides=dmg_data['dice_sides'],
                                damage_bonus=dmg_data['damage_bonus'],
                                damage_type=dtype,
                                is_secondary=dmg_data['is_secondary'],
                            )
                            damage_rolls_created += 1
                        continue

                    # 1C. Check for Reaction
                    if is_reaction(ab_name, ab_desc):
                        action_data = parse_action(ab_name, ab_desc, action_category='reaction')
                        action_obj = EnemyAction.objects.create(
                            enemy=enemy,
                            name=action_data['name'],
                            description=action_data['description'],
                            action_type='reaction',
                            attack_type=action_data['attack_type'],
                            attack_bonus=action_data['attack_bonus'],
                            reach_or_range=action_data['reach_or_range'],
                            saving_throw_dc=action_data['saving_throw_dc'],
                            saving_throw_ability=action_data['saving_throw_ability'],
                            half_damage_on_save=action_data['half_damage_on_save'],
                            has_recharge=action_data['has_recharge'],
                            recharge_min_roll=action_data['recharge_min_roll'],
                            condition_save_end=action_data['condition_save_end'],
                            legendary_cost=1,
                        )
                        actions_created += 1
                        existing_action_names.add(action_data['name'].lower())
                        continue

                    # 1D. Check for Active Action Abilities (e.g. Frightful Presence, Breath Weapons, Spores)
                    if is_active_action(ab_name, ab_desc):
                        action_data = parse_action(ab_name, ab_desc, action_category='action')
                        # Infer saving throw DC if save action without explicit DC
                        is_st = action_data['attack_type'] == 'saving_throw' or action_data['has_recharge']
                        st_dc = action_data['saving_throw_dc'] or (default_dc if is_st else None)
                        st_ab = action_data['saving_throw_ability'] or ('DEX' if is_st else None)

                        action_obj = EnemyAction.objects.create(
                            enemy=enemy,
                            name=action_data['name'],
                            description=action_data['description'],
                            action_type='action',
                            attack_type='saving_throw' if is_st else action_data['attack_type'],
                            attack_bonus=action_data['attack_bonus'],
                            reach_or_range=action_data['reach_or_range'],
                            saving_throw_dc=st_dc,
                            saving_throw_ability=st_ab,
                            half_damage_on_save=action_data['half_damage_on_save'] or is_st,
                            has_recharge=action_data['has_recharge'],
                            recharge_min_roll=action_data['recharge_min_roll'],
                            condition_save_end=action_data['condition_save_end'],
                            legendary_cost=1,
                        )
                        actions_created += 1
                        existing_action_names.add(action_data['name'].lower())

                        for cond_name in action_data['conditions_inflicted']:
                            cond_obj = conditions.get(cond_name.lower())
                            if cond_obj:
                                action_obj.conditions_inflicted.add(cond_obj)

                        for dmg_data in action_data['damage_rolls']:
                            dtype = None
                            if dmg_data.get('damage_type_name'):
                                dtype = damage_types.get(dmg_data['damage_type_name'].lower())
                                if not dtype:
                                    dtype, _ = DamageType.objects.get_or_create(name=dmg_data['damage_type_name'].lower())
                                    damage_types[dmg_data['damage_type_name'].lower()] = dtype

                            EnemyActionDamage.objects.create(
                                action=action_obj,
                                dice_count=dmg_data['dice_count'],
                                dice_sides=dmg_data['dice_sides'],
                                damage_bonus=dmg_data['damage_bonus'],
                                damage_type=dtype,
                                is_secondary=dmg_data['is_secondary'],
                            )
                            damage_rolls_created += 1
                        continue

                    # 1E. Check for Bonus Action mobility / features
                    if is_bonus_action(ab_name, ab_desc):
                        action_data = parse_action(ab_name, ab_desc, action_category='bonus_action')
                        EnemyAction.objects.create(
                            enemy=enemy,
                            name=action_data['name'],
                            description=action_data['description'],
                            action_type='bonus_action',
                            attack_type='utility',
                            attack_bonus=None,
                            reach_or_range=action_data['reach_or_range'],
                            saving_throw_dc=None,
                            saving_throw_ability=None,
                            half_damage_on_save=False,
                            has_recharge=False,
                            recharge_min_roll=None,
                            condition_save_end=False,
                            legendary_cost=1,
                        )
                        actions_created += 1
                        existing_action_names.add(action_data['name'].lower())

                    # 1F. Special Trait (Pack Tactics, Magic Resistance, Nimble Escape, Undead Fortitude, etc.)
                    trait_data = parse_trait(ab_name, ab_desc)
                    EnemyTrait.objects.update_or_create(
                        enemy=enemy,
                        name=trait_data['name'],
                        defaults={
                            'description': trait_data['description'],
                            'trait_type': trait_data['trait_type'],
                        }
                    )
                    traits_created += 1

                # 2. Process Attacks -> EnemyAction + EnemyActionDamage
                for atk in enemy.attacks.all():
                    atk_name_clean = atk.name.strip()
                    if 'multiattack' in atk_name_clean.lower():
                        continue

                    # Check for breath weapon or recharge in attack name
                    has_recharge, recharge_min = parse_recharge(atk_name_clean, "")
                    is_breath = 'breath' in atk_name_clean.lower() or has_recharge

                    # Determine attack type
                    if is_breath:
                        attack_type = 'saving_throw'
                        reach_or_range = "30-foot cone" if 'cone' in atk_name_clean.lower() else "60-foot line"
                    elif any(rw in atk_name_clean.lower() for rw in ['bow', 'crossbow', 'javelin', 'dart', 'sling', 'spear', 'rock', 'bolt']):
                        attack_type = 'ranged_weapon'
                        reach_or_range = "range 60/120 ft."
                    else:
                        attack_type = 'melee_weapon'
                        reach_or_range = "reach 5 ft."

                    # Avoid exact duplicates if ability created it
                    clean_lookup_name = re.sub(r'\(Recharge\s+[\d\-–]+\)', '', atk_name_clean).strip().lower()
                    if clean_lookup_name in existing_action_names:
                        continue

                    action_obj = EnemyAction.objects.create(
                        enemy=enemy,
                        name=atk_name_clean,
                        description=f"{atk_name_clean} attack dealing {atk.damage}.",
                        action_type='action',
                        attack_type=attack_type,
                        attack_bonus=atk.bonus if attack_type != 'saving_throw' else None,
                        reach_or_range=reach_or_range,
                        saving_throw_dc=default_dc if attack_type == 'saving_throw' else None,
                        saving_throw_ability='DEX' if attack_type == 'saving_throw' else None,
                        half_damage_on_save=True if attack_type == 'saving_throw' else False,
                        has_recharge=has_recharge or ('breath' in atk_name_clean.lower()),
                        recharge_min_roll=recharge_min or (5 if is_breath else None),
                        condition_save_end=False,
                        legendary_cost=1,
                    )
                    actions_created += 1
                    existing_action_names.add(atk_name_clean.lower())

                    # Damage formula parsing from atk.damage (e.g. '12d8 acid', '2d10+6 piercing')
                    parsed_dmg = parse_damage_formula(atk.damage)
                    if parsed_dmg:
                        count, sides, bonus = parsed_dmg
                        dtype = None
                        for dt in DAMAGE_TYPES:
                            if dt in atk.damage.lower():
                                dtype = damage_types.get(dt)
                                if not dtype:
                                    dtype, _ = DamageType.objects.get_or_create(name=dt)
                                    damage_types[dt] = dtype
                                break

                        EnemyActionDamage.objects.create(
                            action=action_obj,
                            dice_count=count,
                            dice_sides=sides,
                            damage_bonus=bonus,
                            damage_type=dtype,
                            is_secondary=False,
                        )
                        damage_rolls_created += 1

                # 3. Process any existing EnemyLegendaryAction models
                for leg in enemy.legendary_actions.all():
                    if leg.name.lower() in existing_action_names:
                        continue
                    leg_data = parse_action(leg.name, leg.description, action_category='legendary_action')
                    leg_obj = EnemyAction.objects.create(
                        enemy=enemy,
                        name=leg_data['name'],
                        description=leg_data['description'],
                        action_type='legendary_action',
                        attack_type=leg_data['attack_type'],
                        attack_bonus=leg_data['attack_bonus'],
                        reach_or_range=leg_data['reach_or_range'],
                        saving_throw_dc=leg_data['saving_throw_dc'],
                        saving_throw_ability=leg_data['saving_throw_ability'],
                        half_damage_on_save=leg_data['half_damage_on_save'],
                        has_recharge=leg_data['has_recharge'],
                        recharge_min_roll=leg_data['recharge_min_roll'],
                        condition_save_end=leg_data['condition_save_end'],
                        legendary_cost=getattr(leg, 'cost', 1) or leg_data['legendary_cost'],
                    )
                    actions_created += 1
                    existing_action_names.add(leg_data['name'].lower())

                    for cond_name in leg_data['conditions_inflicted']:
                        cond_obj = conditions.get(cond_name.lower())
                        if cond_obj:
                            leg_obj.conditions_inflicted.add(cond_obj)

                    for dmg_data in leg_data['damage_rolls']:
                        dtype = None
                        if dmg_data.get('damage_type_name'):
                            dtype = damage_types.get(dmg_data['damage_type_name'].lower())
                            if not dtype:
                                dtype, _ = DamageType.objects.get_or_create(name=dmg_data['damage_type_name'].lower())
                                damage_types[dmg_data['damage_type_name'].lower()] = dtype

                        EnemyActionDamage.objects.create(
                            action=leg_obj,
                            dice_count=dmg_data['dice_count'],
                            dice_sides=dmg_data['dice_sides'],
                            damage_bonus=dmg_data['damage_bonus'],
                            damage_type=dtype,
                            is_secondary=dmg_data['is_secondary'],
                        )
                        damage_rolls_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully parsed monsters!\n"
            f"  Actions created: {actions_created}\n"
            f"  Damage rolls created: {damage_rolls_created}\n"
            f"  Multiattacks created: {multiattacks_created}\n"
            f"  Traits created: {traits_created}\n"
            f"  Legendary Actions created/synced: {legendary_created}"
        ))
