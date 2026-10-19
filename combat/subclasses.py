"""
D&D 5e / SRD 5.2 Subclass Combat Specialization Engine

Implements the official SRD 5.2 mechanics for priority subclasses:
1. Fighter — Champion: Improved Critical (19-20), Superior Critical (18-20), Remarkable Athlete, Survivor.
2. Ranger — Hunter: Colossus Slayer (+1d8 extra damage against damaged targets once/turn).
3. Warlock — Fiend Patron: Dark One's Blessing (temporary HP upon reducing hostile to 0 HP).
4. Monk — Warrior of the Open Hand: Open Hand Technique on Flurry of Blows (Topple, 15ft Push, No Reactions), Wholeness of Body.
5. Rogue — Thief: Fast Hands (Bonus action item / Use an Object, Cunning Action options), Second-Story Work.
"""

import math
import random
from typing import Dict, Any, Optional, Tuple

from combat.utils import roll_d20


def _get_subclass_name(participant) -> str:
    """Retrieve lowercase subclass name from character or participant feature_uses."""
    if not participant:
        return ""
    if getattr(participant, 'character', None) and participant.character.subclass:
        return participant.character.subclass.strip().lower()
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        sub = participant.feature_uses.get('subclass')
        if sub and isinstance(sub, str):
            return sub.strip().lower()
    return ""


def _has_feature_named(participant, feature_name: str) -> bool:
    """Check if participant or character has a specific named feature or trait."""
    if not participant or not feature_name:
        return False
    target = feature_name.strip().lower()
    
    # 1. Check feature_uses direct flag or boolean
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        slug = target.replace(' ', '_').replace("'", "")
        if participant.feature_uses.get(f'has_{slug}') or participant.feature_uses.get(slug):
            return True
        feats = participant.feature_uses.get('features') or participant.feature_uses.get('traits')
        if isinstance(feats, list) and any(target in str(f).lower() for f in feats):
            return True

    # 2. Check Character.features
    if getattr(participant, 'character', None):
        try:
            for feat in participant.character.features.all():
                if target in (feat.name or '').lower():
                    return True
        except Exception:
            pass
        try:
            for cf in participant.character.character_feats.select_related('feat').all():
                if target in (cf.feat.name or '').lower():
                    return True
        except Exception:
            pass

    return False


# ---------------------------------------------------------------------------
# 1. Fighter — Champion
# ---------------------------------------------------------------------------

def is_champion(participant) -> bool:
    """Check if participant is a Champion Fighter."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'champion' in sub:
        return True
    return _has_feature_named(participant, 'improved critical') or _has_feature_named(participant, 'champion')


def get_critical_threshold(participant) -> int:
    """
    Get the minimum d20 attack roll required to score a critical hit.
    - Default: 20
    - Champion Fighter 3+: 19 (Improved Critical)
    - Champion Fighter 15+: 18 (Superior Critical)
    - Supports manual override via participant.feature_uses['crit_threshold']
    """
    if not participant:
        return 20

    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        override = participant.feature_uses.get('crit_threshold') or participant.feature_uses.get('critical_threshold')
        if override and isinstance(override, int):
            return override

    if is_champion(participant):
        char_lvl = 3
        if getattr(participant, 'character', None):
            char_lvl = participant.character.level
        elif participant.feature_uses and isinstance(participant.feature_uses, dict):
            char_lvl = int(participant.feature_uses.get('level', 3))

        if char_lvl >= 15 or _has_feature_named(participant, 'superior critical'):
            return 18
        if char_lvl >= 3 or _has_feature_named(participant, 'improved critical'):
            return 19

    return 20


def apply_champion_survivor(participant) -> int:
    """
    Champion 18th level: Survivor
    At the start of each of your turns, you regain 5 + CON modifier HP if HP <= max_hp / 2 and HP > 0.
    Returns amount healed (0 if not applicable).
    """
    if not is_champion(participant) or participant.current_hp <= 0:
        return 0

    char_lvl = 18
    if getattr(participant, 'character', None):
        char_lvl = participant.character.level
    elif participant.feature_uses and isinstance(participant.feature_uses, dict):
        char_lvl = int(participant.feature_uses.get('level', 1))

    if char_lvl < 18 and not _has_feature_named(participant, 'survivor'):
        return 0

    half_hp = participant.max_hp // 2
    if participant.current_hp > half_hp:
        return 0

    con_mod = participant.get_ability_modifier('CON') if hasattr(participant, 'get_ability_modifier') else 0
    heal_amount = max(1, 5 + con_mod)
    old_hp = participant.current_hp
    participant.current_hp = min(participant.max_hp, participant.current_hp + heal_amount)
    healed = participant.current_hp - old_hp
    if healed > 0:
        participant.save(update_fields=['current_hp'])
    return healed


# ---------------------------------------------------------------------------
# 2. Ranger — Hunter
# ---------------------------------------------------------------------------

def is_hunter(participant) -> bool:
    """Check if participant is a Hunter Ranger."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'hunter' in sub:
        return True
    return _has_feature_named(participant, 'colossus slayer') or _has_feature_named(participant, "hunter's prey")


def resolve_colossus_slayer(attacker, target, is_critical: bool = False) -> Tuple[int, str]:
    """
    Hunter's Prey: Colossus Slayer
    Once per turn, when you hit a creature with a weapon attack, the creature takes
    an extra 1d8 damage if it is below its hit point maximum.
    Critical hits double the damage dice (2d8).
    Returns (extra_damage_amount, annotation_string).
    """
    if not is_hunter(attacker) or not target:
        return 0, ""

    if attacker.feature_uses and attacker.feature_uses.get('colossus_slayer_used_this_turn'):
        return 0, ""

    if target.current_hp >= target.max_hp:
        return 0, ""

    dice_count = 2 if is_critical else 1
    rolls = [random.randint(1, 8) for _ in range(dice_count)]
    total = sum(rolls)

    if not isinstance(attacker.feature_uses, dict):
        attacker.feature_uses = {}
    attacker.feature_uses['colossus_slayer_used_this_turn'] = True
    attacker.save(update_fields=['feature_uses'])

    rolls_str = ', '.join(map(str, rolls))
    annotation = f"🏹 Colossus Slayer ({dice_count}d8): +{total} ({rolls_str})"
    return total, annotation


# ---------------------------------------------------------------------------
# 3. Warlock — Fiend Patron
# ---------------------------------------------------------------------------

def is_fiend_warlock(participant) -> bool:
    """Check if participant is a Fiend Patron Warlock."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'fiend' in sub:
        return True
    return _has_feature_named(participant, "dark one's blessing") or _has_feature_named(participant, 'fiend')


def trigger_dark_ones_blessing(attacker, target) -> int:
    """
    Dark One's Blessing
    When you reduce a hostile creature to 0 hit points, you gain temporary hit points
    equal to your Charisma modifier + your warlock level (minimum of 1).
    Does not stack with higher existing temporary HP.
    Returns amount of temporary HP assigned (0 if not triggered).
    """
    if not is_fiend_warlock(attacker) or not target:
        return 0

    if target.current_hp > 0:
        return 0

    # Hostile verification: not on the same party / ally team
    if attacker.participant_type == target.participant_type and attacker.participant_type != 'enemy':
        return 0

    cha_mod = attacker.get_ability_modifier('CHA') if hasattr(attacker, 'get_ability_modifier') else 0
    warlock_lvl = 1
    if getattr(attacker, 'character', None):
        warlock_lvl = max(1, getattr(attacker.character, 'level', 1))
    elif attacker.feature_uses and isinstance(attacker.feature_uses, dict):
        warlock_lvl = int(attacker.feature_uses.get('warlock_level', attacker.feature_uses.get('level', 1)))

    thp = max(1, cha_mod + warlock_lvl)
    cur_thp = attacker.temporary_hp or 0

    if thp > cur_thp:
        attacker.temporary_hp = thp
        attacker.save(update_fields=['feature_uses'])
        return thp

    return 0


# ---------------------------------------------------------------------------
# 4. Monk — Warrior of the Open Hand
# ---------------------------------------------------------------------------

def is_open_hand_monk(participant) -> bool:
    """Check if participant is a Warrior of the Open Hand Monk."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if any(alias in sub for alias in ['open hand', 'warrior of the open hand', 'way of the open hand']):
        return True
    return _has_feature_named(participant, 'open hand technique')


def resolve_open_hand_technique(
    session,
    attacker,
    target,
    technique: str
) -> Dict[str, Any]:
    """
    Open Hand Technique (3rd level)
    Whenever you hit a creature with one of the attacks granted by your Flurry of Blows:
    1. Topple: Target must make a DEX saving throw or be knocked Prone.
    2. Push: Target must make a STR saving throw or be pushed up to 15 feet away.
    3. No Reactions: Target cannot take reactions until the end of your next turn.

    Monk Ki save DC = 8 + proficiency_bonus + WIS modifier.
    """
    from bestiary.models import Condition

    prof_bonus = attacker.get_proficiency_bonus() if hasattr(attacker, 'get_proficiency_bonus') else 2
    wis_mod = attacker.get_ability_modifier('WIS') if hasattr(attacker, 'get_ability_modifier') else 0
    dc = 8 + prof_bonus + wis_mod

    tech = (technique or '').strip().lower().replace('_', ' ')
    result = {
        'technique': technique,
        'success': False,
        'annotation': '',
        'target_prone': False,
        'target_pushed': False,
        'target_no_reactions': False,
    }

    if 'topple' in tech or 'prone' in tech or 'knock' in tech:
        dex_mod = target.get_ability_modifier('DEX') if hasattr(target, 'get_ability_modifier') else 0
        save_roll, _ = roll_d20(advantage=False, lucky=getattr(target, 'has_lucky_trait', lambda: False)())
        save_total = save_roll + dex_mod
        if save_total < dc:
            prone_cond, _ = Condition.objects.get_or_create(name='Prone', defaults={'description': 'Prone condition'})
            target.conditions.add(prone_cond)
            result['success'] = True
            result['target_prone'] = True
            result['annotation'] = f"🥋 Open Hand Technique: Target knocked PRONE (failed DC {dc} DEX save, rolled {save_total})!"
        else:
            result['annotation'] = f"🥋 Open Hand Technique: Target resisted knockdown (saved vs DC {dc} DEX, rolled {save_total})!"

    elif 'push' in tech or 'shove' in tech:
        str_mod = target.get_ability_modifier('STR') if hasattr(target, 'get_ability_modifier') else 0
        save_roll, _ = roll_d20(advantage=False, lucky=getattr(target, 'has_lucky_trait', lambda: False)())
        save_total = save_roll + str_mod
        if save_total < dc:
            result['success'] = True
            result['target_pushed'] = True
            
            # 15 ft push away on tactical grid (3 tiles)
            dx = (target.position_x or 0) - (attacker.position_x or 0)
            dy = (target.position_y or 0) - (attacker.position_y or 0)
            if dx == 0 and dy == 0:
                dx = 1
            dist = math.hypot(dx, dy)
            dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            step_x = dir_x * 15
            step_y = dir_y * 15

            new_x = max(0, min(45, (target.position_x or 0) + step_x))
            new_y = max(0, min(35, (target.position_y or 0) + step_y))
            # Check collisions
            occupied = session.participants.filter(
                position_x=new_x, position_y=new_y, is_active=True, current_hp__gt=0
            ).exclude(id=target.id).first() if session else None

            if not occupied and (new_x != target.position_x or new_y != target.position_y):
                target.position_x = new_x
                target.position_y = new_y
                target.save(update_fields=['position_x', 'position_y'])

            result['annotation'] = f"🥋 Open Hand Technique: Target PUSHED 15 ft away (failed DC {dc} STR save, rolled {save_total})!"
        else:
            result['annotation'] = f"🥋 Open Hand Technique: Target resisted push (saved vs DC {dc} STR, rolled {save_total})!"

    elif 'reaction' in tech:
        # Target cannot take reactions until the end of monk's next turn
        target.use_reaction()
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        cur_round = session.current_round if session else 1
        target.feature_uses['no_reactions_until_round'] = cur_round + 2
        target.save(update_fields=['reaction_used', 'feature_uses'])
        result['success'] = True
        result['target_no_reactions'] = True
        result['annotation'] = "🥋 Open Hand Technique: Target DENIED reactions until the end of your next turn!"

    return result


def resolve_wholeness_of_body(actor) -> Tuple[int, str]:
    """
    Wholeness of Body (6th level)
    Regain HP equal to 3 x Monk level (2014) or roll Martial Arts die + WIS mod (2024).
    Consumes action (or bonus action for 2024).
    Returns (healed_amount, description).
    """
    if not is_open_hand_monk(actor):
        return 0, "Actor is not an Open Hand monk."

    char_lvl = 6
    if getattr(actor, 'character', None):
        char_lvl = actor.character.level
    elif actor.feature_uses and isinstance(actor.feature_uses, dict):
        char_lvl = int(actor.feature_uses.get('monk_level', actor.feature_uses.get('level', 6)))

    is_2024 = False
    if getattr(actor, 'character', None) and getattr(actor.character, 'ruleset_version', '') == '2024':
        is_2024 = True

    wis_mod = actor.get_ability_modifier('WIS') if hasattr(actor, 'get_ability_modifier') else 0

    if is_2024:
        # 1d8 + WIS modifier
        die_roll = random.randint(1, 8)
        heal_amt = max(1, die_roll + wis_mod)
        desc_formula = f"1d8 ({die_roll}) + {wis_mod} WIS"
    else:
        heal_amt = 3 * char_lvl
        desc_formula = f"3 x {char_lvl} Monk Level"

    old_hp = actor.current_hp
    actor.current_hp = min(actor.max_hp, actor.current_hp + heal_amt)
    healed = actor.current_hp - old_hp
    actor.save(update_fields=['current_hp'])

    return healed, f"🧘 {actor.get_name()} channels Wholeness of Body ({desc_formula}), restoring {healed} HP!"


# ---------------------------------------------------------------------------
# 5. Rogue — Thief
# ---------------------------------------------------------------------------

def is_thief(participant) -> bool:
    """Check if participant is a Thief Rogue."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'thief' in sub:
        return True
    return _has_feature_named(participant, 'fast hands') or _has_feature_named(participant, 'thief')


def can_use_fast_hands(participant) -> bool:
    """Check if participant can take the Fast Hands bonus action."""
    return is_thief(participant) and not participant.bonus_action_used


# ---------------------------------------------------------------------------
# 6. Bard — College of Lore
# ---------------------------------------------------------------------------

def is_lore_bard(participant) -> bool:
    """Check if participant is a College of Lore Bard."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'lore' in sub:
        return True
    return _has_feature_named(participant, 'cutting words') or _has_feature_named(participant, 'college of lore')


def get_bardic_inspiration_die(participant) -> int:
    """
    Get Bardic Inspiration die size (d6, d8, d10, d12) based on Bard level:
    - Levels 1–4: d6
    - Levels 5–9: d8
    - Levels 10–14: d10
    - Levels 15–20: d12
    """
    if not participant:
        return 6
    lvl = 1
    if getattr(participant, 'character', None):
        lvl = participant.character.level
    elif participant.feature_uses and isinstance(participant.feature_uses, dict):
        lvl = int(participant.feature_uses.get('bard_level', participant.feature_uses.get('level', 1)))

    if lvl >= 15:
        return 12
    elif lvl >= 10:
        return 10
    elif lvl >= 5:
        return 8
    return 6


def can_use_cutting_words(bard, target=None) -> Tuple[bool, str]:
    """
    Validate if bard can use Cutting Words reaction against a target creature:
    - Must be a Lore Bard (3rd level+)
    - Must have reaction available
    - Must have Bardic Inspiration uses available
    - Target must be within 60 feet
    - Target cannot be deafened or immune to charmed
    """
    if not is_lore_bard(bard):
        return False, "Actor is not a College of Lore Bard."
    if bard.reaction_used:
        return False, "Reaction already expended this round."
    if bard.is_incapacitated():
        return False, f"{bard.get_name()} is incapacitated and cannot take reactions."

    # Inspiration uses check
    uses = None
    if bard.feature_uses and isinstance(bard.feature_uses, dict):
        uses = bard.feature_uses.get('bardic_inspiration_remaining')
    if uses is None:
        cha_mod = bard.get_ability_modifier('CHA') if hasattr(bard, 'get_ability_modifier') else 3
        uses = max(1, cha_mod)
        if not isinstance(bard.feature_uses, dict):
            bard.feature_uses = {}
        bard.feature_uses['bardic_inspiration_remaining'] = uses

    if uses <= 0:
        return False, "No Bardic Inspiration uses remaining."

    if target:
        # Range check: 60 feet
        dist = bard.get_distance_to(target) if hasattr(bard, 'get_distance_to') else 30
        if dist > 60:
            return False, f"Target is out of range ({dist} ft > 60 ft limit)."

        # Condition checks: deafened or charm immune
        if hasattr(target, 'has_condition'):
            if target.has_condition('deafened'):
                return False, "Target is deafened and cannot hear your words."
        from combat.condition_effects import is_condition_immune
        if is_condition_immune(target, 'charmed'):
            return False, "Target is immune to being charmed and unaffected by Cutting Words."

    return True, ""


def resolve_cutting_words(
    session,
    bard,
    target,
    roll_type: str = 'attack',
    roll_value: int = 0
) -> Dict[str, Any]:
    """
    Cutting Words (3rd level)
    Use reaction to expend one Bardic Inspiration use, roll inspiration die,
    and subtract the number rolled from the target's attack roll, ability check, or damage roll.
    """
    can_use, reason = can_use_cutting_words(bard, target)
    if not can_use:
        return {'success': False, 'message': reason, 'reduction': 0}

    # Consume reaction and inspiration use
    bard.use_reaction()
    if not isinstance(bard.feature_uses, dict):
        bard.feature_uses = {}
    cur_uses = bard.feature_uses.get('bardic_inspiration_remaining', max(1, bard.get_ability_modifier('CHA')))
    bard.feature_uses['bardic_inspiration_remaining'] = max(0, cur_uses - 1)
    bard.save(update_fields=['reaction_used', 'feature_uses'])

    die_size = get_bardic_inspiration_die(bard)
    roll = random.randint(1, die_size)
    mod_value = max(0, roll_value - roll)

    annotation = f"🗣️ Cutting Words (1d{die_size}): -{roll} to {roll_type} roll (from {roll_value} to {mod_value})!"
    return {
        'success': True,
        'die_size': die_size,
        'reduction': roll,
        'original_value': roll_value,
        'modified_value': mod_value,
        'remaining_uses': bard.feature_uses['bardic_inspiration_remaining'],
        'annotation': annotation,
    }


def resolve_peerless_skill(bard, check_total: int) -> Tuple[int, str]:
    """
    Peerless Skill (14th level)
    Expend one Bardic Inspiration use to add the inspiration die to your own ability check.
    """
    if not is_lore_bard(bard):
        return check_total, "Actor is not a Lore Bard."

    char_lvl = 14
    if getattr(bard, 'character', None):
        char_lvl = bard.character.level
    elif bard.feature_uses and isinstance(bard.feature_uses, dict):
        char_lvl = int(bard.feature_uses.get('level', 14))

    if char_lvl < 14 and not _has_feature_named(bard, 'peerless skill'):
        return check_total, "Peerless Skill requires Level 14+."

    if not isinstance(bard.feature_uses, dict):
        bard.feature_uses = {}
    cur_uses = bard.feature_uses.get('bardic_inspiration_remaining', max(1, bard.get_ability_modifier('CHA')))
    if cur_uses <= 0:
        return check_total, "No Bardic Inspiration uses remaining."

    bard.feature_uses['bardic_inspiration_remaining'] = max(0, cur_uses - 1)
    bard.save(update_fields=['feature_uses'])

    die_size = get_bardic_inspiration_die(bard)
    roll = random.randint(1, die_size)
    new_total = check_total + roll
    annotation = f"🎭 Peerless Skill (1d{die_size}): +{roll} to ability check (total: {new_total})!"
    return new_total, annotation


# ---------------------------------------------------------------------------
# 7. Druid — Circle of the Land
# ---------------------------------------------------------------------------

def is_land_druid(participant) -> bool:
    """Check if participant is a Circle of the Land Druid."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'land' in sub:
        return True
    return (_has_feature_named(participant, 'natural recovery') or
            _has_feature_named(participant, 'circle of the land') or
            _has_feature_named(participant, "land's aid") or
            _has_feature_named(participant, 'lands aid'))


def get_natural_recovery_limit(druid) -> int:
    """
    Natural Recovery:
    Combined spell slot levels you can recover equals half druid level (rounded up).
    Slots must be 5th level or lower (no 6th+ level slots).
    """
    lvl = 2
    if getattr(druid, 'character', None):
        lvl = druid.character.level
    elif druid.feature_uses and isinstance(druid.feature_uses, dict):
        lvl = int(druid.feature_uses.get('druid_level', druid.feature_uses.get('level', 2)))
    return math.ceil(lvl / 2.0)


def resolve_natural_recovery(druid, slots_to_recover: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Natural Recovery (2nd level)
    Recover spell slots on short rest (once per long rest) up to half druid level (round up).
    """
    if not is_land_druid(druid):
        return {'success': False, 'message': 'Actor is not a Circle of the Land Druid.'}

    if not isinstance(druid.feature_uses, dict):
        druid.feature_uses = {}

    if druid.feature_uses.get('natural_recovery_used'):
        return {'success': False, 'message': 'Natural Recovery has already been used today (resets on Long Rest).'}

    max_levels = get_natural_recovery_limit(druid)
    recovered_details = []

    if getattr(druid, 'character', None) and hasattr(druid.character, 'stats') and druid.character.stats:
        stats = druid.character.stats
        expended = dict(stats.expended_spell_slots or {})

        if slots_to_recover:
            total_levels = 0
            for lvl_str, count in slots_to_recover.items():
                cnt = int(count)
                if cnt <= 0:
                    continue
                lvl = int(lvl_str)
                if lvl >= 6:
                    return {'success': False, 'message': 'Natural Recovery cannot recover spell slots of 6th level or higher.'}
                if lvl < 1:
                    continue
                exp_count = int(expended.get(lvl_str, 0))
                if cnt > exp_count:
                    return {'success': False, 'message': f'Cannot recover {cnt} level {lvl} slots (only {exp_count} currently expended).'}
                total_levels += lvl * cnt

            if total_levels == 0:
                return {'success': False, 'message': 'No spell slots chosen for recovery.'}
            if total_levels > max_levels:
                return {'success': False, 'message': f'Combined slot levels ({total_levels}) exceed Natural Recovery limit ({max_levels} levels).'}

            for lvl_str, count in slots_to_recover.items():
                cnt = int(count)
                if cnt > 0:
                    lvl = int(lvl_str)
                    expended[lvl_str] = max(0, int(expended.get(lvl_str, 0)) - cnt)
                    recovered_details.append(f"{cnt}x Level {lvl}")
        else:
            # Auto-recovery prioritizing highest eligible slots (1..5)
            rem = max_levels
            for lvl in range(5, 0, -1):
                lvl_str = str(lvl)
                exp_count = int(expended.get(lvl_str, 0))
                recovered_for_lvl = 0
                while exp_count > 0 and rem >= lvl:
                    exp_count -= 1
                    rem -= lvl
                    recovered_for_lvl += 1
                if recovered_for_lvl > 0:
                    expended[lvl_str] = exp_count
                    recovered_details.append(f"{recovered_for_lvl}x Level {lvl}")

            if not recovered_details:
                return {'success': False, 'message': 'All spell slots (levels 1-5) are already at full capacity.'}

        stats.expended_spell_slots = expended
        stats.save(update_fields=['expended_spell_slots'])

    druid.feature_uses['natural_recovery_used'] = True
    druid.save(update_fields=['feature_uses'])

    details_str = ", ".join(recovered_details) if recovered_details else "spell slots"
    annotation = f"🌿 {druid.get_name()} meditates with nature via Natural Recovery, restoring {details_str}! (Max: {max_levels} slot levels)"
    return {
        'success': True,
        'recovered': details_str,
        'max_levels': max_levels,
        'annotation': annotation,
    }


def resolve_lands_aid(
    session,
    druid,
    target_x: int,
    target_y: int,
    heal_target=None
) -> Dict[str, Any]:
    """
    Land's Aid (2024 / 3rd level)
    As a Magic action, expend one Wild Shape use.
    60 ft range, 10 ft radius sphere (2 tiles).
    Enemies make CON save vs Druid Spell Save DC.
    Fail: 2d6 necrotic damage (3d6 at lvl 10, 4d6 at lvl 14). Save: half damage.
    One chosen ally in the area or within range regains 2d6 (3d6/4d6) HP.
    """
    if not is_land_druid(druid):
        return {'success': False, 'message': 'Actor is not a Circle of the Land Druid.'}

    if druid.action_used or druid.attacks_remaining <= 0:
        return {'success': False, 'message': f'{druid.get_name()} has already used their action this turn.'}

    # Wild Shape uses check
    if not isinstance(druid.feature_uses, dict):
        druid.feature_uses = {}
    ws_uses = druid.feature_uses.get('wild_shape_uses', 2)
    if ws_uses <= 0:
        return {'success': False, 'message': 'No Wild Shape uses remaining to activate Land\'s Aid.'}

    druid.feature_uses['wild_shape_uses'] = ws_uses - 1
    druid.action_used = True
    druid.attacks_remaining = 0
    druid.save(update_fields=['feature_uses', 'action_used', 'attacks_remaining'])

    lvl = 3
    if getattr(druid, 'character', None):
        lvl = druid.character.level
    elif druid.feature_uses and isinstance(druid.feature_uses, dict):
        lvl = int(druid.feature_uses.get('level', 3))

    dice_count = 2
    if lvl >= 14:
        dice_count = 4
    elif lvl >= 10:
        dice_count = 3

    # Damage roll: dice_count x d6 necrotic
    dmg_rolls = [random.randint(1, 6) for _ in range(dice_count)]
    total_necrotic = sum(dmg_rolls)

    prof_bonus = druid.get_proficiency_bonus() if hasattr(druid, 'get_proficiency_bonus') else 2
    wis_mod = druid.get_ability_modifier('WIS') if hasattr(druid, 'get_ability_modifier') else 3
    dc = 8 + prof_bonus + wis_mod

    # Find targets in 10 ft radius of target_x, target_y
    targets_hit = []
    if session:
        for p in session.participants.filter(is_active=True, current_hp__gt=0):
            # Distance from target_x, target_y
            px = p.position_x or 0
            py = p.position_y or 0
            dist = math.hypot(px - target_x, py - target_y)
            if dist <= 12:  # 10 ft radius + tolerance
                # Hostile to druid: damage
                if p.participant_type != druid.participant_type or p.participant_type == 'enemy':
                    con_mod = p.get_ability_modifier('CON') if hasattr(p, 'get_ability_modifier') else 0
                    save_r, _ = roll_d20(advantage=False, lucky=getattr(p, 'has_lucky_trait', lambda: False)())
                    save_tot = save_r + con_mod
                    if save_tot >= dc:
                        dmg = max(1, total_necrotic // 2)
                        saved = True
                    else:
                        dmg = total_necrotic
                        saved = False
                    p.take_damage(dmg, damage_type='necrotic')
                    targets_hit.append({
                        'id': p.id,
                        'name': p.get_name(),
                        'saved': saved,
                        'damage': dmg
                    })

    # Heal ally
    healed_amount = 0
    healed_target_name = None
    if heal_target and heal_target.current_hp > 0:
        heal_rolls = [random.randint(1, 6) for _ in range(dice_count)]
        healed_amount = sum(heal_rolls)
        heal_target.heal(healed_amount)
        healed_target_name = heal_target.get_name()
    elif not heal_target and druid.current_hp > 0:
        # Default self heal
        heal_rolls = [random.randint(1, 6) for _ in range(dice_count)]
        healed_amount = sum(heal_rolls)
        druid.heal(healed_amount)
        healed_target_name = druid.get_name()

    annotation = (f"🌸 Land's Aid: Sprouted thorny vines at ({target_x}, {target_y})! "
                  f"{len(targets_hit)} creature(s) withered by necrotic energy ({total_necrotic} damage, DC {dc} CON save). "
                  f"{healed_target_name} restored +{healed_amount} HP!")

    return {
        'success': True,
        'damage_base': total_necrotic,
        'dc': dc,
        'targets_hit': targets_hit,
        'healed_amount': healed_amount,
        'healed_target': healed_target_name,
        'annotation': annotation,
    }


def has_lands_stride(participant) -> bool:
    """Check if participant has Land's Stride (Level 6+ Circle of the Land Druid)."""
    if not participant:
        return False
    if is_land_druid(participant):
        lvl = 6
        if getattr(participant, 'character', None):
            lvl = participant.character.level
        elif participant.feature_uses and isinstance(participant.feature_uses, dict):
            lvl = int(participant.feature_uses.get('level', 6))
        if lvl >= 6:
            return True
    return _has_feature_named(participant, "land's stride") or _has_feature_named(participant, 'lands stride')


def has_natures_ward(participant) -> bool:
    """Check if participant has Nature's Ward (Level 10+ Circle of the Land Druid)."""
    if not participant:
        return False
    if is_land_druid(participant):
        lvl = 10
        if getattr(participant, 'character', None):
            lvl = participant.character.level
        elif participant.feature_uses and isinstance(participant.feature_uses, dict):
            lvl = int(participant.feature_uses.get('level', 10))
        if lvl >= 10:
            return True
    return _has_feature_named(participant, "nature's ward") or _has_feature_named(participant, 'natures ward')


# ---------------------------------------------------------------------------
# 8. Sorcerer — Draconic Sorcery
# ---------------------------------------------------------------------------

DRACONIC_ANCESTOR_ELEMENTS = {
    'red': 'fire',
    'gold': 'fire',
    'brass': 'fire',
    'blue': 'lightning',
    'bronze': 'lightning',
    'white': 'cold',
    'silver': 'cold',
    'black': 'acid',
    'copper': 'acid',
    'green': 'poison',
}


def is_draconic_sorcerer(participant) -> bool:
    """Check if participant is a Draconic Sorcery / Draconic Bloodline Sorcerer."""
    if not participant:
        return False
    sub = _get_subclass_name(participant)
    if 'draconic' in sub:
        return True
    return (_has_feature_named(participant, 'draconic resilience') or
            _has_feature_named(participant, 'elemental affinity') or
            _has_feature_named(participant, 'draconic sorcery') or
            _has_feature_named(participant, 'draconic bloodline'))


def get_draconic_ancestor_element(participant) -> str:
    """Get the elemental damage type associated with this Draconic Sorcerer's ancestor."""
    if not participant:
        return 'fire'
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        ancestor = participant.feature_uses.get('dragon_ancestor') or participant.feature_uses.get('draconic_ancestor')
        if ancestor and isinstance(ancestor, str):
            clean = ancestor.strip().lower()
            for dragon_color, elem in DRACONIC_ANCESTOR_ELEMENTS.items():
                if dragon_color in clean:
                    return elem
            if clean in ['fire', 'lightning', 'cold', 'acid', 'poison']:
                return clean

    # Check Character.features or character background
    if getattr(participant, 'character', None):
        try:
            for feat in participant.character.features.all():
                desc = ((feat.name or '') + ' ' + (feat.description or '')).lower()
                for dragon_color, elem in DRACONIC_ANCESTOR_ELEMENTS.items():
                    if dragon_color in desc:
                        return elem
        except Exception:
            pass

    return 'fire'


def apply_elemental_affinity_damage(caster, damage_type: str, base_damage: int) -> Tuple[int, str]:
    """
    Elemental Affinity (6th level)
    When you cast a spell that deals damage of the type associated with your draconic ancestry,
    add your Charisma modifier to one damage roll of that spell.
    Returns (extra_damage_amount, annotation).
    """
    if not is_draconic_sorcerer(caster) or not damage_type:
        return 0, ""

    char_lvl = 6
    if getattr(caster, 'character', None):
        char_lvl = caster.character.level
    elif caster.feature_uses and isinstance(caster.feature_uses, dict):
        char_lvl = int(caster.feature_uses.get('level', 6))

    if char_lvl < 6 and not _has_feature_named(caster, 'elemental affinity'):
        return 0, ""

    ancestor_elem = get_draconic_ancestor_element(caster)
    if damage_type.strip().lower() != ancestor_elem:
        return 0, ""

    cha_mod = caster.get_ability_modifier('CHA') if hasattr(caster, 'get_ability_modifier') else 3
    bonus = max(1, cha_mod)
    annotation = f"🐉 Elemental Affinity: +{bonus} {ancestor_elem.title()} damage (CHA modifier)"
    return bonus, annotation


def activate_elemental_affinity_resistance(caster) -> Dict[str, Any]:
    """
    Elemental Affinity Resistance (6th level)
    Spend 1 Sorcery Point to gain resistance to your associated draconic damage type for 1 hour.
    """
    if not is_draconic_sorcerer(caster):
        return {'success': False, 'message': 'Actor is not a Draconic Sorcerer.'}

    char_lvl = 6
    if getattr(caster, 'character', None):
        char_lvl = caster.character.level
    elif caster.feature_uses and isinstance(caster.feature_uses, dict):
        char_lvl = int(caster.feature_uses.get('level', 6))

    if char_lvl < 6 and not _has_feature_named(caster, 'elemental affinity'):
        return {'success': False, 'message': 'Elemental Affinity requires Sorcerer Level 6+.'}

    # Sorcery Point cost: 1
    from combat.sorcery import get_sorcery_points_info, spend_sorcery_points
    sp_info = get_sorcery_points_info(caster)
    if sp_info['current'] < 1:
        return {'success': False, 'message': 'Not enough Sorcery Points (1 SP required).'}

    if not spend_sorcery_points(caster, 1):
        return {'success': False, 'message': 'Failed to deduct Sorcery Point.'}

    remaining_sp = get_sorcery_points_info(caster)['current']


    elem = get_draconic_ancestor_element(caster)
    if not isinstance(caster.feature_uses, dict):
        caster.feature_uses = {}
    caster.feature_uses['elemental_affinity_resistance'] = elem
    caster.save(update_fields=['feature_uses'])

    annotation = f"🐉 Elemental Affinity: Expended 1 Sorcery Point to gain resistance to {elem.upper()} damage for 1 hour!"
    return {
        'success': True,
        'damage_type': elem,
        'remaining_sorcery_points': remaining_sp,
        'annotation': annotation,
    }


def has_elemental_affinity_resistance(participant, damage_type: str) -> bool:
    """Check if participant currently has active Elemental Affinity damage resistance."""
    if not participant or not damage_type:
        return False
    if not participant.feature_uses or not isinstance(participant.feature_uses, dict):
        return False
    active_elem = participant.feature_uses.get('elemental_affinity_resistance')
    if not active_elem:
        return False
    return active_elem.strip().lower() == damage_type.strip().lower()


def toggle_dragon_wings(participant, manifest: bool = True) -> Dict[str, Any]:
    """
    Dragon Wings (14th level)
    Sprout or dismiss dragon wings as a bonus action, gaining flying speed equal to current walking speed.
    Cannot manifest while wearing medium or heavy armor.
    """
    if not is_draconic_sorcerer(participant):
        return {'success': False, 'message': 'Actor is not a Draconic Sorcerer.'}

    char_lvl = 14
    if getattr(participant, 'character', None):
        char_lvl = participant.character.level
    elif participant.feature_uses and isinstance(participant.feature_uses, dict):
        char_lvl = int(participant.feature_uses.get('level', 14))

    if char_lvl < 14 and not _has_feature_named(participant, 'dragon wings'):
        return {'success': False, 'message': 'Dragon Wings requires Sorcerer Level 14+.'}

    if manifest:
        # Check armor restrictions
        armor = participant.get_equipped_armor() if hasattr(participant, 'get_equipped_armor') else None
        if armor and getattr(armor, 'armor_type', '').lower() in ['medium', 'heavy']:
            return {'success': False, 'message': 'Cannot manifest Dragon Wings while wearing medium or heavy armor.'}

        if not isinstance(participant.feature_uses, dict):
            participant.feature_uses = {}
        participant.feature_uses['dragon_wings_active'] = True
        participant.is_flying = True
        participant.save(update_fields=['feature_uses', 'is_flying'])
        annotation = f"🦅 {participant.get_name()} manifests majestic dragon wings, gaining a fly speed of {participant.speed} ft!"
        return {'success': True, 'manifested': True, 'fly_speed': participant.speed, 'annotation': annotation}
    else:
        if not isinstance(participant.feature_uses, dict):
            participant.feature_uses = {}
        participant.feature_uses['dragon_wings_active'] = False
        participant.is_flying = False
        participant.altitude = 0
        participant.save(update_fields=['feature_uses', 'is_flying', 'altitude'])
        annotation = f"🦅 {participant.get_name()} dismisses their dragon wings and returns to the ground."
        return {'success': True, 'manifested': False, 'annotation': annotation}

