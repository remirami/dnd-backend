"""
SRD 5.2 5e Rest Mechanics Engine (SRD 5.1 & 2024 SRD 5.2)

Provides comprehensive short rest and long rest execution:
- Hit Dice expenditure & HP recovery (with CON modifier)
- Warlock Pact Magic slot resets (independent from long-rest caster slots)
- Monk Ki / Focus points restoration
- Sorcerer Sorcerous Restoration (2024 level 5+ / 2014 level 20)
- Fighter Action Surge & Second Wind recovery
- Druid Wild Shape recovery
- Cleric & Paladin Channel Divinity recovery
- Bard Font of Inspiration (Level 5+) recovery
- Paladin Lay on Hands pool restoration (Long Rest)
- Barbarian Rage recovery (Long Rest)
- Fighter Indomitable recovery (Long Rest)
- Spell slots full restoration & hit dice recovery (Long Rest)
- Synchronization with active CombatParticipant instances
"""

import random
from typing import Dict, List, Tuple, Any, Optional
from django.db import transaction


# Standard Hit Dice mapping by class name
CLASS_HIT_DICE = {
    'barbarian': 12,
    'fighter': 10,
    'paladin': 10,
    'ranger': 10,
    'bard': 8,
    'cleric': 8,
    'druid': 8,
    'monk': 8,
    'rogue': 8,
    'warlock': 8,
    'sorcerer': 6,
    'wizard': 6,
}


def get_class_hit_die_size(class_name: str) -> int:
    """Return die size for given class (e.g. 'fighter' -> 10, 'wizard' -> 6)."""
    if not class_name:
        return 8
    clean = class_name.strip().lower()
    return CLASS_HIT_DICE.get(clean, 8)


def get_available_hit_dice(character) -> int:
    """Calculate total available hit dice remaining for a character."""
    total_level = getattr(character, 'level', 1) or 1
    stats = getattr(character, 'stats', None)
    if not stats:
        return total_level
    used = getattr(stats, 'hit_dice_used', 0) or 0
    return max(0, total_level - used)


def get_character_hit_dice_pool(character) -> Dict[str, int]:
    """
    Get available hit dice pool broken down by die type for single-class and multiclass characters.
    Returns: e.g. {'d10': 3, 'd6': 2}
    """
    pool = {}
    class_levels = []
    if hasattr(character, 'class_levels'):
        class_levels = list(character.class_levels.all())

    if class_levels:
        for cl in class_levels:
            c_name = cl.character_class.name.lower()
            die_size = get_class_hit_die_size(c_name)
            die_key = f"d{die_size}"
            pool[die_key] = pool.get(die_key, 0) + cl.level
    else:
        c_name = getattr(character.character_class, 'name', '').lower() if character.character_class else 'fighter'
        die_size = get_class_hit_die_size(c_name)
        die_key = f"d{die_size}"
        pool[die_key] = getattr(character, 'level', 1) or 1

    return pool


def calculate_pact_magic_slots(character) -> Tuple[int, int]:
    """
    Calculate Warlock Pact Magic slots and slot level based on Warlock level.
    Returns: (slot_count, slot_level)
    """
    from characters.multiclassing import get_class_level
    warlock_level = 0
    if character.character_class and character.character_class.name.lower() == 'warlock':
        warlock_level = character.level
    else:
        warlock_level = get_class_level(character, 'warlock')

    if warlock_level <= 0:
        return 0, 0

    if warlock_level >= 17:
        return 4, 5
    elif warlock_level >= 11:
        return 3, 5
    elif warlock_level >= 9:
        return 2, 5
    elif warlock_level >= 7:
        return 2, 4
    elif warlock_level >= 5:
        return 2, 3
    elif warlock_level >= 3:
        return 2, 2
    elif warlock_level >= 2:
        return 2, 1
    elif warlock_level >= 1:
        return 1, 1

    return 0, 0


def calculate_channel_divinity_max(character) -> int:
    """Calculate maximum Channel Divinity uses for Cleric or Paladin."""
    from characters.multiclassing import get_class_level
    cleric_lvl = get_class_level(character, 'cleric')
    if not cleric_lvl and character.character_class and character.character_class.name.lower() == 'cleric':
        cleric_lvl = character.level

    paladin_lvl = get_class_level(character, 'paladin')
    if not paladin_lvl and character.character_class and character.character_class.name.lower() == 'paladin':
        paladin_lvl = character.level

    if cleric_lvl >= 18:
        return 3
    elif cleric_lvl >= 6:
        return 2
    elif cleric_lvl >= 2:
        return 1
    elif paladin_lvl >= 3:
        return 1

    return 0


def calculate_lay_on_hands_max(character) -> int:
    """Calculate Paladin Lay on Hands pool (5 x Paladin level)."""
    from characters.multiclassing import get_class_level
    paladin_lvl = get_class_level(character, 'paladin')
    if not paladin_lvl and character.character_class and character.character_class.name.lower() == 'paladin':
        paladin_lvl = character.level
    return paladin_lvl * 5


def calculate_rage_max(character) -> int:
    """Calculate Barbarian maximum rages per long rest."""
    from characters.multiclassing import get_class_level
    barb_lvl = get_class_level(character, 'barbarian')
    if not barb_lvl and character.character_class and character.character_class.name.lower() == 'barbarian':
        barb_lvl = character.level

    if barb_lvl >= 20:
        return 999  # Unlimited
    elif barb_lvl >= 17:
        return 6
    elif barb_lvl >= 12:
        return 5
    elif barb_lvl >= 6:
        return 4
    elif barb_lvl >= 3:
        return 3
    elif barb_lvl >= 1:
        return 2
    return 0


def sync_participant_after_rest(character, is_long_rest: bool = False):
    """
    Synchronize active/recent combat participants with character's post-rest state.
    """
    from combat.models import CombatParticipant
    participants = CombatParticipant.objects.filter(character=character)
    for p in participants:
        stats = getattr(character, 'stats', None)
        if stats:
            p.current_hp = stats.hit_points
            p.temporary_hp = stats.temporary_hit_points
        if not isinstance(p.feature_uses, dict):
            p.feature_uses = {}

        # Reset short-rest combat tags
        p.feature_uses['action_surge_used'] = False
        p.feature_uses['second_wind_used'] = False
        p.feature_uses['wild_shaped'] = False
        p.feature_uses['wild_shape_uses'] = 2
        p.feature_uses['gwm_bonus_attack_available'] = False
        p.action_used = False
        p.bonus_action_used = False
        p.reaction_used = False

        cd_max = calculate_channel_divinity_max(character)
        if cd_max > 0:
            p.feature_uses['channel_divinity_uses_remaining'] = cd_max

        monk_lvl = character.level if character.character_class and character.character_class.name.lower() == 'monk' else 0
        if monk_lvl > 0:
            p.feature_uses['ki_pool_remaining'] = monk_lvl

        if is_long_rest:
            p.death_save_successes = 0
            p.death_save_failures = 0
            p.feature_uses['arcane_recovery_used'] = False
            p.feature_uses['indomitable_used'] = False
            if hasattr(p, 'set_exhaustion_level'):
                p.set_exhaustion_level(getattr(character.stats, 'exhaustion_level', 0) or 0)
            loh_max = calculate_lay_on_hands_max(character)
            if loh_max > 0:
                p.feature_uses['lay_on_hands_pool'] = loh_max
            rage_max = calculate_rage_max(character)
            if rage_max > 0:
                p.feature_uses['rages_remaining'] = rage_max
                p.feature_uses['rage_active'] = False

        p.save()


@transaction.atomic
def execute_short_rest(
    character,
    hit_dice_to_spend: int = 0,
    dice_choices: Optional[List[str]] = None,
    sync_combat: bool = True
) -> Dict[str, Any]:
    """
    Execute a full 5e Short Rest on a character:
    1. Spend Hit Dice & Roll for Healing (die + CON mod, min 0 per die).
    2. Reset Warlock Pact Magic slots.
    3. Reset Monk Ki points (`ki_points_used = 0`).
    4. Apply Sorcerous Restoration (2024 / 2014 level 20).
    5. Reset Short Rest class features (Action Surge, Second Wind, Wild Shape, Channel Divinity, Bardic Inspiration).
    6. Synchronize with active CombatParticipant if present.
    """
    if not hasattr(character, 'stats') or not character.stats:
        raise ValueError("Character has no stats record.")

    stats = character.stats
    if stats.hit_dice_used is None:
        stats.hit_dice_used = 0

    total_level = getattr(character, 'level', 1) or 1
    available_hd = max(0, total_level - stats.hit_dice_used)

    if hit_dice_to_spend > available_hd and hit_dice_to_spend > 0:
        raise ValueError(f"Not enough hit dice. Available: {available_hd}, requested: {hit_dice_to_spend}")

    # 1. Roll Hit Dice Healing
    hp_healed = 0
    dice_rolls = []
    con_mod = stats.constitution_modifier

    if hit_dice_to_spend > 0:
        # Determine default die size
        default_die = 8
        if character.character_class:
            default_die = get_class_hit_die_size(character.character_class.name)

        for i in range(hit_dice_to_spend):
            chosen_die = default_die
            if dice_choices and i < len(dice_choices):
                try:
                    chosen_die = int(str(dice_choices[i]).strip().lower().replace('d', ''))
                except (ValueError, TypeError):
                    chosen_die = default_die

            roll = random.randint(1, chosen_die)
            total = max(0, roll + con_mod)
            dice_rolls.append({
                'die': f"d{chosen_die}",
                'roll': roll,
                'con_modifier': con_mod,
                'healed': total
            })
            hp_healed += total

        old_hp = stats.hit_points
        stats.hit_points = min(stats.max_hit_points, stats.hit_points + hp_healed)
        actual_healed = stats.hit_points - old_hp
        stats.hit_dice_used += hit_dice_to_spend
    else:
        actual_healed = 0

    features_recovered = []

    # 2. Warlock Pact Magic Slot Reset
    pact_slots, pact_level = calculate_pact_magic_slots(character)
    if pact_slots > 0:
        from characters.multiclassing import _get_class_levels
        cls_levels = _get_class_levels(character)
        is_multiclass = len(cls_levels) > 1 or (hasattr(character, 'class_levels') and character.class_levels.count() > 1)
        other_slots_exist = any(str(k) != str(pact_level) for k in (stats.spell_slots or {}).keys())
        is_pure_warlock = (not is_multiclass and not other_slots_exist and character.character_class and character.character_class.name.lower() == 'warlock')

        if is_pure_warlock:
            stats.expended_spell_slots = {}
            features_recovered.append(f"Warlock Pact Magic slots fully restored ({pact_slots} slots @ Level {pact_level})")
        else:
            pact_level_str = str(pact_level)
            if stats.expended_spell_slots and pact_level_str in stats.expended_spell_slots:
                cur_exp = stats.expended_spell_slots[pact_level_str]
                new_exp = max(0, cur_exp - pact_slots)
                if new_exp == 0:
                    del stats.expended_spell_slots[pact_level_str]
                else:
                    stats.expended_spell_slots[pact_level_str] = new_exp
                features_recovered.append(f"Warlock Pact Magic slots restored ({pact_slots} slots @ Level {pact_level})")

    # 3. Monk Ki / Focus Points
    if getattr(stats, 'ki_points_used', 0) > 0:
        recovered_ki = stats.ki_points_used
        stats.ki_points_used = 0
        features_recovered.append(f"Monk Ki points restored ({recovered_ki} points)")

    # 4. Sorcerer Sorcerous Restoration
    c_name = getattr(character.character_class, 'name', '').lower() if character.character_class else ''
    is_2024 = getattr(character, 'ruleset_version', '') == '2024'
    if c_name == 'sorcerer' and getattr(stats, 'sorcery_points_used', 0) > 0:
        if is_2024 and total_level >= 5:
            restore_amount = min(stats.sorcery_points_used, max(1, total_level // 5))
            stats.sorcery_points_used = max(0, stats.sorcery_points_used - restore_amount)
            features_recovered.append(f"Sorcerous Restoration (+{restore_amount} Sorcery points)")
        elif total_level >= 20:
            restore_amount = min(stats.sorcery_points_used, 4)
            stats.sorcery_points_used = max(0, stats.sorcery_points_used - restore_amount)
            features_recovered.append(f"Sorcerous Restoration (+{restore_amount} Sorcery points)")

    # 5. Reset Class Features
    if c_name == 'fighter' or (hasattr(character, 'features') and character.features.filter(name__icontains='Action Surge').exists()):
        features_recovered.append("Action Surge & Second Wind restored")

    if c_name == 'druid' or (hasattr(character, 'features') and character.features.filter(name__icontains='Wild Shape').exists()):
        features_recovered.append("Wild Shape uses restored")

    if calculate_channel_divinity_max(character) > 0:
        features_recovered.append("Channel Divinity uses restored")

    if c_name == 'bard' and total_level >= 5:
        features_recovered.append("Bardic Inspiration uses restored (Font of Inspiration)")

    stats.save()

    # 6. Sync active combat participants
    if sync_combat:
        sync_participant_after_rest(character, is_long_rest=False)

    msg = f"Short rest completed. Recovered {actual_healed} HP."
    if features_recovered:
        msg += f" Features restored: {', '.join(features_recovered)}."

    return {
        "message": msg,
        "hp_gained": actual_healed,
        "hp_recovered": actual_healed,
        "hit_points": stats.hit_points,
        "current_hp": stats.hit_points,
        "max_hit_points": stats.max_hit_points,
        "hit_dice_spent": hit_dice_to_spend,
        "hit_dice_used": stats.hit_dice_used,
        "hit_dice_remaining": max(0, total_level - stats.hit_dice_used),
        "dice_rolls": dice_rolls,
        "features_recovered": features_recovered,
        "ki_points_used": stats.ki_points_used,
        "sorcery_points_used": stats.sorcery_points_used,
        "expended_spell_slots": stats.expended_spell_slots,
    }


@transaction.atomic
def execute_long_rest(character, sync_combat: bool = True) -> Dict[str, Any]:
    """
    Execute a full 5e Long Rest on a character:
    1. Restore HP to max & clear temporary HP.
    2. Regain Hit Dice up to half total level (min 1 die).
    3. Restore all Spell Slots (clear expended & created slots).
    4. Reset all class resources (Ki, Sorcery, Rages, Action Surge, Indomitable, Lay on Hands, Channel Divinity).
    5. Clear Exhaustion by 1 level if present.
    6. Reset Death Saves.
    7. Synchronize with active CombatParticipant if present.
    """
    if not hasattr(character, 'stats') or not character.stats:
        raise ValueError("Character has no stats record.")

    stats = character.stats
    if stats.hit_dice_used is None:
        stats.hit_dice_used = 0

    total_level = getattr(character, 'level', 1) or 1

    # 1. HP & Temp HP
    old_hp = stats.hit_points
    stats.hit_points = stats.max_hit_points
    actual_healed = stats.max_hit_points - old_hp
    stats.temporary_hit_points = 0
    stats.temp_hp = 0

    # 2. Hit Dice Recovery (Half total, min 1)
    recover_hd = max(1, total_level // 2)
    old_used = stats.hit_dice_used
    stats.hit_dice_used = max(0, stats.hit_dice_used - recover_hd)
    actual_hd_recovered = old_used - stats.hit_dice_used

    # 3. Spell Slots Full Reset
    from campaigns.utils import calculate_spell_slots
    from characters.multiclassing import calculate_multiclass_spell_slots
    from characters.models import CharacterClassLevel

    if hasattr(character, 'class_levels') and CharacterClassLevel.objects.filter(character=character).count() > 1:
        max_slots = calculate_multiclass_spell_slots(character)
    elif character.character_class:
        max_slots = calculate_spell_slots(character.character_class.name, total_level)
    else:
        max_slots = {}

    stats.spell_slots = max_slots
    stats.expended_spell_slots = {}
    stats.created_spell_slots = {}

    # 4. Reset Class Resources
    stats.ki_points_used = 0
    stats.sorcery_points_used = 0

    # 5. Clear Exhaustion by 1 level if present (2024 SRD 5.2 Rules)
    old_exhaustion = getattr(stats, 'exhaustion_level', 0) or 0
    stats.exhaustion_level = max(0, old_exhaustion - 1)
    exhaustion_recovered = 1 if old_exhaustion > stats.exhaustion_level else 0

    stats.save()

    # 6. Sync active combat participants & feature pools
    if sync_combat:
        sync_participant_after_rest(character, is_long_rest=True)

    msg = f"Long rest completed. HP and Spell Slots fully restored. Regained {actual_hd_recovered} Hit Dice."
    if exhaustion_recovered > 0:
        msg += f" Recovered 1 level of Exhaustion (Current: Level {stats.exhaustion_level})."

    return {
        "message": msg,
        "hp_gained": actual_healed,
        "hp_recovered": actual_healed,
        "hit_points": stats.hit_points,
        "current_hp": stats.hit_points,
        "max_hit_points": stats.max_hit_points,
        "hit_dice_recovered": actual_hd_recovered,
        "hit_dice_used": stats.hit_dice_used,
        "hit_dice_remaining": max(0, total_level - stats.hit_dice_used),
        "spell_slots": stats.spell_slots,
        "expended_spell_slots": stats.expended_spell_slots,
        "ki_points_used": stats.ki_points_used,
        "sorcery_points_used": stats.sorcery_points_used,
        "exhaustion_recovered": exhaustion_recovered,
        "exhaustion_level": stats.exhaustion_level,
    }
