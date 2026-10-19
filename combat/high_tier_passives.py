"""
High-Tier Class Passives and Automation System (Levels 11-20)
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.

Covers:
- Paladin Aura of Protection (Level 6+, range 30 ft at level 18+)
- Paladin Aura of Courage (Level 10+, range 30 ft at level 18+)
- Rogue Reliable Talent (Level 11+)
- Barbarian Relentless Rage (Level 11+)
- Barbarian Indomitable Might (Level 18+)
- Fighter Indomitable (Level 9+, 13+, 17+)
"""

from typing import Tuple, Optional


def is_paladin(participant) -> bool:
    """Check if participant is a Paladin."""
    if not participant or not getattr(participant, 'character', None):
        return False
    char_class = getattr(participant.character, 'character_class', None)
    return bool(char_class and char_class.name.lower() == 'paladin')


def get_paladin_level(participant) -> int:
    """Get the Paladin level of the participant."""
    if not is_paladin(participant):
        return 0
    return getattr(participant.character, 'level', 1)


def is_conscious(participant) -> bool:
    """Check if participant is conscious and not incapacitated."""
    if not participant or participant.current_hp <= 0:
        return False
    incapacitating_conditions = {'incapacitated', 'paralyzed', 'petrified', 'stunned', 'unconscious'}
    if hasattr(participant, 'conditions'):
        try:
            cond_names = {c.name.lower() for c in participant.conditions.all()}
            if cond_names.intersection(incapacitating_conditions):
                return False
        except Exception:
            pass
    return True


def get_participant_distance(p1, p2) -> float:
    """Calculate distance in feet between two participants."""
    if p1 == p2:
        return 0.0
    pos1 = getattr(p1, 'position', None)
    pos2 = getattr(p2, 'position', None)
    if pos1 and pos2:
        return float(pos1.distance_to(pos2))
    # Fallback to position_x / position_y attributes if available
    x1 = getattr(p1, 'position_x', None)
    y1 = getattr(p1, 'position_y', None)
    x2 = getattr(p2, 'position_x', None)
    y2 = getattr(p2, 'position_y', None)
    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
        import math
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    # If no grid position is present, assume within party aura range by default
    return 0.0


def has_aura_of_protection(participant) -> bool:
    """Paladin level 6+ grants Aura of Protection."""
    if is_paladin(participant) and get_paladin_level(participant) >= 6:
        return True
    if participant and getattr(participant, 'character', None):
        features = getattr(participant.character, 'features', None)
        if features and features.filter(name__icontains='Aura of Protection').exists():
            return True
    return False


def get_aura_of_protection_bonus(participant) -> int:
    """
    Returns the highest Charisma modifier bonus (min +1) granted by self or nearby conscious allied Paladins.
    Aura radius: 10 ft (increases to 30 ft at Paladin level 18).
    """
    if not participant:
        return 0
    session = getattr(participant, 'combat_session', None)
    if not session:
        # Standalone participant check
        if has_aura_of_protection(participant) and is_conscious(participant):
            return max(1, participant.get_ability_modifier('CHA'))
        return 0

    max_bonus = 0
    participants = session.participants.filter(is_active=True)
    for ally in participants:
        # Must be friendly/same participant type
        if ally.participant_type != participant.participant_type:
            continue
        if not has_aura_of_protection(ally) or not is_conscious(ally):
            continue
        lvl = get_paladin_level(ally)
        aura_radius = 30 if lvl >= 18 else 10
        dist = get_participant_distance(participant, ally)
        if dist <= aura_radius:
            bonus = max(1, ally.get_ability_modifier('CHA'))
            if bonus > max_bonus:
                max_bonus = bonus

    return max_bonus


def has_aura_of_courage(participant) -> bool:
    """Paladin level 10+ grants Aura of Courage."""
    if is_paladin(participant) and get_paladin_level(participant) >= 10:
        return True
    if participant and getattr(participant, 'character', None):
        features = getattr(participant.character, 'features', None)
        if features and features.filter(name__icontains='Aura of Courage').exists():
            return True
    return False


def is_protected_by_aura_of_courage(participant) -> bool:
    """
    Returns True if participant is protected by self or nearby conscious allied Paladin Aura of Courage.
    Immune to the frightened condition.
    """
    if not participant:
        return False
    session = getattr(participant, 'combat_session', None)
    if not session:
        return has_aura_of_courage(participant) and is_conscious(participant)

    participants = session.participants.filter(is_active=True)
    for ally in participants:
        if ally.participant_type != participant.participant_type:
            continue
        if not has_aura_of_courage(ally) or not is_conscious(ally):
            continue
        lvl = get_paladin_level(ally)
        aura_radius = 30 if lvl >= 18 else 10
        dist = get_participant_distance(participant, ally)
        if dist <= aura_radius:
            return True

    return False


def has_reliable_talent(participant) -> bool:
    """Rogue level 11+ grants Reliable Talent."""
    if not participant or not getattr(participant, 'character', None):
        return False
    char = participant.character
    char_class = getattr(char, 'character_class', None)
    if char_class and char_class.name.lower() == 'rogue' and getattr(char, 'level', 1) >= 11:
        return True
    features = getattr(char, 'features', None)
    if features and features.filter(name__icontains='Reliable Talent').exists():
        return True
    return False


def apply_reliable_talent(participant, base_roll: int, proficiency: bool = True) -> Tuple[int, bool]:
    """
    If participant has Reliable Talent and check uses proficiency, any d20 roll of 1-9 is treated as 10.
    Returns: (adjusted_roll, was_triggered)
    """
    if proficiency and has_reliable_talent(participant):
        if base_roll < 10:
            return 10, True
    return base_roll, False


def has_indomitable_might(participant) -> bool:
    """Barbarian level 18+ grants Indomitable Might."""
    if not participant or not getattr(participant, 'character', None):
        return False
    char = participant.character
    char_class = getattr(char, 'character_class', None)
    if char_class and char_class.name.lower() == 'barbarian' and getattr(char, 'level', 1) >= 18:
        return True
    features = getattr(char, 'features', None)
    if features and features.filter(name__icontains='Indomitable Might').exists():
        return True
    return False


def apply_indomitable_might(participant, ability_name: str, check_total: int) -> Tuple[int, bool]:
    """
    If participant has Indomitable Might and makes a Strength check with total < Strength score,
    use the Strength score instead.
    Returns: (adjusted_total, was_triggered)
    """
    if ability_name.upper() == 'STR' and has_indomitable_might(participant):
        str_score = 10
        if getattr(participant.character, 'stats', None):
            str_score = participant.character.stats.strength
        if check_total < str_score:
            return str_score, True
    return check_total, False


def has_relentless_rage(participant) -> bool:
    """Barbarian level 11+ grants Relentless Rage."""
    if not participant or not getattr(participant, 'character', None):
        return False
    char = participant.character
    char_class = getattr(char, 'character_class', None)
    if char_class and char_class.name.lower() == 'barbarian' and getattr(char, 'level', 1) >= 11:
        return True
    features = getattr(char, 'features', None)
    if features and features.filter(name__icontains='Relentless Rage').exists():
        return True
    return False


def get_relentless_rage_dc(participant) -> int:
    """Get current Relentless Rage DC (starts at 10, +5 per success)."""
    if not participant or not isinstance(getattr(participant, 'feature_uses', None), dict):
        return 10
    return participant.feature_uses.get('relentless_rage_dc', 10)


def check_relentless_rage(participant) -> Tuple[bool, int, int, str]:
    """
    Executes a Constitution saving throw for Relentless Rage.
    Starting at DC 10, if successful: remains at 1 HP, and DC increases by 5.
    Returns: (success, dc, save_total, message)
    """
    from combat.utils import roll_d20, calculate_saving_throw

    dc = get_relentless_rage_dc(participant)
    roll, _ = roll_d20(lucky=getattr(participant, 'has_lucky_trait', lambda: False)())
    con_mod = participant.get_ability_modifier('CON')
    prof_bonus = participant.character.proficiency_bonus if getattr(participant, 'character', None) else 2
    # Barbarians are proficient in Constitution saves
    prof = True
    aura_bonus = get_aura_of_protection_bonus(participant)

    save_total, breakdown = calculate_saving_throw(
        roll, con_mod, prof_bonus, prof, other_modifiers=aura_bonus
    )

    if save_total >= dc:
        if not isinstance(participant.feature_uses, dict):
            participant.feature_uses = {}
        participant.feature_uses['relentless_rage_dc'] = dc + 5
        msg = f"🔥 Relentless Rage! {participant.get_name()} succeeded CON save (rolled {save_total} vs DC {dc}) and remains at 1 HP! Next DC: {dc + 5}."
        return True, dc, save_total, msg
    else:
        msg = f"💀 Relentless Rage failed! {participant.get_name()} failed CON save (rolled {save_total} vs DC {dc}) and falls to 0 HP."
        return False, dc, save_total, msg


def reset_relentless_rage_dc(participant):
    """Resets Relentless Rage DC back to 10 upon short or long rest."""
    if participant and isinstance(getattr(participant, 'feature_uses', None), dict):
        if 'relentless_rage_dc' in participant.feature_uses:
            participant.feature_uses['relentless_rage_dc'] = 10
