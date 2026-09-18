"""
Management command to parse and upgrade existing monsters in the database
to the new structured EnemyAction, EnemyActionDamage, EnemyMultiattack, and EnemyTrait models.
"""
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
)


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
        )
        if limit:
            enemies_qs = enemies_qs[:limit]

        total_enemies = enemies_qs.count()
        self.stdout.write(f"Processing {total_enemies} monsters...")

        actions_created = 0
        damage_rolls_created = 0
        multiattacks_created = 0
        traits_created = 0

        batch_size = 200
        processed = 0

        with transaction.atomic():
            for enemy in enemies_qs.iterator(chunk_size=batch_size):
                processed += 1
                if processed % 100 == 0 or processed == total_enemies:
                    self.stdout.write(f"  Processed {processed}/{total_enemies} monsters...")

                # 1. Process Abilities -> Multiattack or Trait or Special Action
                for ability in enemy.abilities.all():
                    ab_name = ability.name.strip()
                    ab_desc = ability.description.strip()

                    # Check for Multiattack
                    if 'multiattack' in ab_name.lower():
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

                    # Check if it's an action-like ability (e.g. Frightful Presence or Breath Weapon in abilities)
                    if 'recharge' in ab_name.lower() or 'breath' in ab_name.lower():
                        action_data = parse_action(ab_name, ab_desc)
                        action_obj = EnemyAction.objects.create(
                            enemy=enemy,
                            name=action_data['name'],
                            description=action_data['description'],
                            action_type=action_data['action_type'],
                            attack_type=action_data['attack_type'],
                            attack_bonus=action_data['attack_bonus'],
                            reach_or_range=action_data['reach_or_range'],
                            saving_throw_dc=action_data['saving_throw_dc'],
                            saving_throw_ability=action_data['saving_throw_ability'],
                            half_damage_on_save=action_data['half_damage_on_save'],
                            has_recharge=action_data['has_recharge'],
                            recharge_min_roll=action_data['recharge_min_roll'],
                            condition_save_end=action_data['condition_save_end'],
                            legendary_cost=action_data['legendary_cost'],
                        )
                        actions_created += 1

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

                    # Otherwise, it is a Trait
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
                    action_data = parse_action(
                        atk.name,
                        atk.damage,
                        raw_attack_bonus=atk.bonus,
                        raw_damage_dice=atk.damage
                    )
                    action_obj = EnemyAction.objects.create(
                        enemy=enemy,
                        name=action_data['name'],
                        description=action_data['description'],
                        action_type=action_data['action_type'],
                        attack_type=action_data['attack_type'],
                        attack_bonus=action_data['attack_bonus'] or atk.bonus,
                        reach_or_range=action_data['reach_or_range'],
                        saving_throw_dc=action_data['saving_throw_dc'],
                        saving_throw_ability=action_data['saving_throw_ability'],
                        half_damage_on_save=action_data['half_damage_on_save'],
                        has_recharge=action_data['has_recharge'],
                        recharge_min_roll=action_data['recharge_min_roll'],
                        condition_save_end=action_data['condition_save_end'],
                        legendary_cost=action_data['legendary_cost'],
                    )
                    actions_created += 1

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

                # 3. Process Legendary Actions -> EnemyAction (legendary_action)
                for leg in enemy.legendary_actions.all():
                    leg_data = parse_action(
                        leg.name,
                        leg.description,
                        action_category='legendary_action'
                    )
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
                        legendary_cost=leg.cost or leg_data['legendary_cost'],
                    )
                    actions_created += 1

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
            f"  Traits created: {traits_created}"
        ))
