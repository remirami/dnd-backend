"""
Combat Feats & Warlock Invocations System
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.

Implements:
- Feats: Sentinel, Sharpshooter, Great Weapon Master, Polearm Master, War Caster.
- Invocations: Agonizing Blast, Repelling Blast, Devil's Sight.
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import random


def has_feat(participant, feat_name: str) -> bool:
    """
    Check if participant has a specific 5e feat.
    Checks:
    1. participant.feature_uses (e.g. 'has_sentinel', 'sentinel_feat', 'sentinel')
    2. character.character_feats (Feat model match)
    3. character.features (CharacterFeature match)
    4. enemy traits
    """
    if not participant or not feat_name:
        return False

    clean = feat_name.strip().lower().replace('_', ' ')
    slug = clean.replace(' ', '_')
    aliases = {clean, slug, f"has_{slug}", f"{slug}_feat", f"has_{clean}"}

    # 1. Check feature_uses
    uses = getattr(participant, 'feature_uses', None)
    if isinstance(uses, dict):
        for alias in aliases:
            if uses.get(alias):
                return True
        feats_list = uses.get('feats', [])
        if isinstance(feats_list, list) and any(str(f).strip().lower() in aliases for f in feats_list):
            return True

    # 2. Check CharacterFeats
    char = getattr(participant, 'character', None)
    if char:
        if hasattr(char, 'character_feats') and char.character_feats.filter(feat__name__iexact=feat_name).exists():
            return True
        if hasattr(char, 'features') and char.features.filter(name__icontains=feat_name).exists():
            return True

    # 3. Check enemy traits
    if hasattr(participant, 'resolve_enemy'):
        enemy = participant.resolve_enemy()
        if enemy and hasattr(enemy, 'traits'):
            if enemy.traits.filter(name__icontains=feat_name).exists():
                return True

    return False


def has_eldritch_invocation(participant, invocation_name: str) -> bool:
    """
    Check if participant has a specific Warlock Eldritch Invocation.
    Supports Agonizing Blast, Repelling Blast, Devil's Sight, etc.
    """
    if not participant or not invocation_name:
        return False

    clean = invocation_name.strip().lower().replace('_', ' ')
    slug = clean.replace(' ', '_')
    aliases = {clean, slug, f"has_{slug}", f"has_{clean}"}

    uses = getattr(participant, 'feature_uses', None)
    if isinstance(uses, dict):
        for alias in aliases:
            if uses.get(alias):
                return True
        invoc_list = uses.get('eldritch_invocations', []) or uses.get('invocations', [])
        if isinstance(invoc_list, list) and any(str(inv).strip().lower() in aliases for inv in invoc_list):
            return True

    char = getattr(participant, 'character', None)
    if char and hasattr(char, 'features'):
        if char.features.filter(name__icontains=clean).exists():
            return True

    if hasattr(participant, 'resolve_enemy'):
        enemy = participant.resolve_enemy()
        if enemy and hasattr(enemy, 'traits'):
            if enemy.traits.filter(name__icontains=clean).exists():
                return True

    return False


# --- Sentinel Feat ---

def has_sentinel(participant) -> bool:
    return has_feat(participant, 'Sentinel')


def check_sentinel_provocation(mover, enemy, is_disengaged: bool) -> bool:
    """
    Sentinel (Rule 2): Creatures provoke opportunity attacks from you even if they take the Disengage action.
    Returns True if an opportunity attack is provoked despite Disengage.
    """
    if not is_disengaged:
        return True
    return has_sentinel(enemy)


def apply_sentinel_opportunity_hit(mover, attacker) -> Tuple[bool, str]:
    """
    Sentinel (Rule 1): When you hit a creature with an opportunity attack, the creature's speed becomes 0 for the rest of the turn.
    Returns: (applied, message)
    """
    if not has_sentinel(attacker):
        return False, ""

    if not isinstance(mover.feature_uses, dict):
        mover.feature_uses = {}
    mover.feature_uses['sentinel_halted'] = True
    mover.feature_uses['speed_zero'] = True
    # Consume remaining movement
    base_spd = 30
    if mover.character and hasattr(mover.character, 'stats') and mover.character.stats:
        base_spd = mover.character.stats.speed or 30
    mover.movement_used = max(mover.movement_used, base_spd * 2)
    mover.save(update_fields=['feature_uses', 'movement_used'])

    return True, f"🛡️ Sentinel: {mover.get_name()}'s speed becomes 0 for the remainder of the turn!"


def can_sentinel_retaliate(sentinel, attacker, target) -> bool:
    """
    Sentinel (Rule 3): When a creature within 5 ft attacks an ally (who does not have Sentinel),
    the Sentinel can use their reaction to make a melee weapon attack against the attacking creature.
    """
    if not has_sentinel(sentinel) or not sentinel.can_use_reaction() or sentinel.is_incapacitated():
        return False
    if attacker.id == sentinel.id or target.id == sentinel.id:
        return False
    if target.participant_type != sentinel.participant_type:
        return False
    # If the attacked ally also has Sentinel, this reaction does not trigger
    if has_sentinel(target):
        return False

    # Check distance between sentinel and attacker (within 5 ft melee reach)
    dist = sentinel.get_distance_to(attacker) if hasattr(sentinel, 'get_distance_to') else 5
    return dist <= 5


# --- Sharpshooter & Great Weapon Master Power Attack ---

def has_sharpshooter(participant) -> bool:
    return has_feat(participant, 'Sharpshooter')


def has_great_weapon_master(participant) -> bool:
    return has_feat(participant, 'Great Weapon Master')


def resolve_sharpshooter_cover(attacker, cover_type: str) -> str:
    """
    Sharpshooter: Ranged weapon attacks ignore half cover and three-quarters cover.
    """
    if not cover_type or cover_type == 'none':
        return 'none'
    if has_sharpshooter(attacker) and cover_type in ['half', 'three_quarters']:
        return 'none'
    return cover_type


def resolve_sharpshooter_range(attacker, distance: float, normal_range: int, long_range: int) -> bool:
    """
    Sharpshooter: Attacking at long range does not impose disadvantage on your ranged weapon attack rolls.
    Returns: has_disadvantage (False if Sharpshooter applies within long range)
    """
    if distance <= normal_range:
        return False
    if distance > long_range:
        return True  # Beyond long range cannot hit or has disadvantage
    if has_sharpshooter(attacker):
        return False  # No disadvantage within long range
    return True


def apply_power_attack_modifiers(
    attacker,
    is_ranged: bool,
    is_heavy: bool,
    power_attack_requested: bool
) -> Tuple[int, int, str]:
    """
    5e Power Attack (-5 to hit / +10 to damage):
    - Sharpshooter for ranged weapon attacks.
    - Great Weapon Master for melee attacks with heavy weapons.
    Returns: (attack_penalty, damage_bonus, note)
    """
    if not power_attack_requested:
        return 0, 0, ""

    if is_ranged and has_sharpshooter(attacker):
        return -5, 10, "🎯 Sharpshooter (-5 to hit, +10 damage)"

    if not is_ranged and is_heavy and has_great_weapon_master(attacker):
        return -5, 10, "⚔️ Great Weapon Master (-5 to hit, +10 damage)"

    return 0, 0, ""


def trigger_gwm_bonus_attack(attacker, is_critical: bool, target_dropped_to_zero: bool) -> bool:
    """
    Great Weapon Master: On a critical hit with a melee weapon, or when you reduce a creature to 0 HP
    with a melee weapon, you can make one melee weapon attack as a bonus action.
    """
    if not has_great_weapon_master(attacker):
        return False

    if is_critical or target_dropped_to_zero:
        if not isinstance(attacker.feature_uses, dict):
            attacker.feature_uses = {}
        attacker.feature_uses['gwm_bonus_attack_available'] = True
        attacker.save(update_fields=['feature_uses'])
        return True
    return False


# --- Polearm Master (PAM) ---

POLEARM_WEAPONS = {'glaive', 'halberd', 'pike', 'quarterstaff', 'spear'}


def has_polearm_master(participant) -> bool:
    return has_feat(participant, 'Polearm Master')


def is_polearm_weapon(weapon_name: str) -> bool:
    if not weapon_name:
        return False
    clean = str(weapon_name).strip().lower()
    return any(p in clean for p in POLEARM_WEAPONS)


def check_polearm_entry_provocation(mover, enemy, step_from: tuple, step_to: tuple) -> bool:
    """
    Polearm Master: While wielding a glaive, halberd, pike, quarterstaff, or spear,
    other creatures provoke an opportunity attack from you when they enter the reach you have with that weapon.
    Reach is 10 ft for glaive/halberd/pike, 5 ft for quarterstaff/spear.
    """
    if not has_polearm_master(enemy) or not enemy.can_use_reaction() or enemy.is_incapacitated():
        return False

    w_name = ""
    eq = None
    if hasattr(enemy, 'get_equipped_weapon'):
        eq = enemy.get_equipped_weapon('main_hand') or enemy.get_equipped_weapon('two_handed') or enemy.get_equipped_weapon(None)
    if eq:
        w_name = getattr(eq, 'name', '')
    if not w_name and isinstance(getattr(enemy, 'feature_uses', None), dict):
        w_name = enemy.feature_uses.get('equipped_weapon_name', '')

    if not is_polearm_weapon(w_name):
        # Fallback check on enemy attack names
        res_enemy = enemy.resolve_enemy() if hasattr(enemy, 'resolve_enemy') else None
        if res_enemy:
            acts = [a.name for a in res_enemy.actions.all()]
            polearm_act = next((a for a in acts if is_polearm_weapon(a)), None)
            if not polearm_act:
                return False
            w_name = polearm_act
        else:
            return False

    reach = 10 if any(p in str(w_name).lower() for p in ['glaive', 'halberd', 'pike']) else 5
    enemy_x = enemy.position_x
    enemy_y = enemy.position_y

    d_from = max(abs(step_from[0] - enemy_x), abs(step_from[1] - enemy_y))
    d_to = max(abs(step_to[0] - enemy_x), abs(step_to[1] - enemy_y))

    # Trigger when creature enters the reach (was outside reach, now inside)
    return (d_from > reach and d_to <= reach)


# --- War Caster ---

def has_war_caster(participant) -> bool:
    return has_feat(participant, 'War Caster')


def has_concentration_advantage(participant) -> bool:
    """
    War Caster: Advantage on Constitution saving throws that you make to maintain concentration on a spell.
    """
    return has_war_caster(participant)


# --- Warlock Eldritch Invocations ---

def has_devils_sight(participant) -> bool:
    """
    Devil's Sight: Can see normally in darkness, both magical and nonmagical, to a distance of 120 feet.
    """
    return has_eldritch_invocation(participant, 'devils_sight') or has_eldritch_invocation(participant, "devil's sight")


def apply_agonizing_blast_bonus(caster, spell_name: str, beam_count: int = 1) -> Tuple[int, str]:
    """
    Agonizing Blast: When you cast Eldritch Blast, add your Charisma modifier to the damage it deals on a hit.
    In 5e, this applies per beam that hits.
    Returns: (bonus_damage, annotation)
    """
    if not spell_name or 'eldritch blast' not in spell_name.lower():
        return 0, ""

    if not has_eldritch_invocation(caster, 'agonizing_blast'):
        return 0, ""

    cha_mod = caster.get_ability_modifier('CHA')
    if cha_mod <= 0:
        return 0, ""

    total_bonus = cha_mod * max(1, beam_count)
    return total_bonus, f"⚡ Agonizing Blast (+{total_bonus} CHA)"


def apply_repelling_blast_push(caster, target, spell_name: str, session) -> Tuple[bool, str]:
    """
    Repelling Blast: When you hit a creature with Eldritch Blast, you can push the creature up to 10 feet away
    in a straight line from you.
    Clamps push to battle grid [0, 45] x [0, 35] and validates destination occupancy.
    Returns: (pushed, description)
    """
    if not spell_name or 'eldritch blast' not in spell_name.lower():
        return False, ""

    if not has_eldritch_invocation(caster, 'repelling_blast'):
        return False, ""

    if not target or not target.is_active or target.current_hp <= 0:
        return False, ""

    dx = (target.position_x or 0) - (caster.position_x or 0)
    dy = (target.position_y or 0) - (caster.position_y or 0)
    dist = math.hypot(dx, dy)
    if dist == 0:
        dx, dy, dist = 1, 0, 1
    dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

    if abs(dx) > abs(dy) * 1.5:
        step_x = dir_x * 10
        step_y = 0
    elif abs(dy) > abs(dx) * 1.5:
        step_x = 0
        step_y = dir_y * 10
    else:
        step_x = dir_x * 10
        step_y = dir_y * 10

    new_x = max(0, min(45, (target.position_x or 0) + step_x))
    new_y = max(0, min(35, (target.position_y or 0) + step_y))

    # Check tile occupancy
    occ = session.participants.filter(
        position_x=new_x, position_y=new_y, is_active=True, current_hp__gt=0
    ).exclude(id=target.id).first()
    if occ:
        half_x = max(0, min(45, (target.position_x or 0) + (step_x // 2)))
        half_y = max(0, min(35, (target.position_y or 0) + (step_y // 2)))
        occ_half = session.participants.filter(
            position_x=half_x, position_y=half_y, is_active=True, current_hp__gt=0
        ).exclude(id=target.id).first()
        if not occ_half:
            new_x, new_y = half_x, half_y
        else:
            return False, f"{target.get_name()} could not be pushed: destination occupied."

    if new_x != target.position_x or new_y != target.position_y:
        target.position_x = new_x
        target.position_y = new_y
        target.save(update_fields=['position_x', 'position_y'])
        try:
            pos = target.position
            pos.x = new_x
            pos.y = new_y
            pos.save()
        except Exception:
            pass
        return True, f"💨 Repelling Blast: {target.get_name()} was pushed 10 ft away to ({new_x} ft, {new_y} ft)!"

    return False, ""
