"""
Sorcery Points and Metamagic System (SRD 5.2 5e Rules).
Implements Font of Magic (Sorcerer Level 2+) and Metamagic (Sorcerer Level 3+):
- Font of Magic:
  - Converting Spell Slots to Sorcery Points (Bonus Action)
  - Creating Spell Slots from Sorcery Points (Bonus Action)
- Metamagic Options:
  - Quickened Spell (2 SP): Cast a 1-action spell as a Bonus Action
  - Twinned Spell (Spell Level SP, min 1): Target a second creature with a single-target spell
  - Subtle Spell (1 SP): Cast without verbal or somatic components
  - Empowered Spell (1 SP): Reroll up to CHA mod (min 1) damage dice
  - Heightened Spell (3 SP in 2014, 2 SP in 2024): Target has Disadvantage on the saving throw
  - Careful Spell (1 SP): Chosen creatures automatically succeed on saving throws
  - Extended Spell (1 SP): Double spell duration
  - Distant Spell (1 SP): Double spell range (or 30 ft if touch)
"""
import random
from typing import Optional, Dict, Any, Tuple, List


# 5e Font of Magic: Creating Spell Slots Cost Table (PHB p. 101)
SLOT_CREATION_COST = {
    1: 2,
    2: 3,
    3: 5,
    4: 6,
    5: 7,
}

# 5e Font of Magic: Converting Spell Slots to Points Gain Table
SLOT_CONVERSION_GAIN = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
}

METAMAGIC_NAMES = {
    'quickened': 'Quickened Spell',
    'twinned': 'Twinned Spell',
    'subtle': 'Subtle Spell',
    'empowered': 'Empowered Spell',
    'heightened': 'Heightened Spell',
    'careful': 'Careful Spell',
    'extended': 'Extended Spell',
    'distant': 'Distant Spell',
}


def is_sorcerer_participant(participant) -> bool:
    """Check if combat participant is a Sorcerer or has Font of Magic."""
    if not participant:
        return False
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        if participant.feature_uses.get('has_font_of_magic') or participant.feature_uses.get('has_metamagic'):
            return True
        if 'sorcery_points' in participant.feature_uses:
            return True

    if participant.character:
        cls_name = getattr(participant.character.character_class, 'name', '').lower()
        if cls_name == 'sorcerer':
            return True
        if hasattr(participant.character, 'features'):
            return participant.character.features.filter(name__icontains='font of magic').exists()

    return False


def get_sorcery_points_info(participant) -> Dict[str, int]:
    """Return dictionary with max, current, and used Sorcery Points."""
    if not participant:
        return {'max': 0, 'current': 0, 'used': 0}

    # Explicit override in feature_uses (e.g. for enemy/mock/custom participants)
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        if 'sorcery_points' in participant.feature_uses:
            cur = int(participant.feature_uses.get('sorcery_points', 0))
            max_sp = int(participant.feature_uses.get('sorcery_points_max', cur))
            return {'max': max_sp, 'current': cur, 'used': max(0, max_sp - cur)}

    if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
        stats = participant.character.stats
        return {
            'max': stats.sorcery_points_max,
            'current': stats.sorcery_points_current,
            'used': stats.sorcery_points_used or 0
        }

    return {'max': 0, 'current': 0, 'used': 0}


def spend_sorcery_points(participant, amount: int) -> bool:
    """Deduct sorcery points from participant. Returns True if successful."""
    if amount <= 0:
        return True

    info = get_sorcery_points_info(participant)
    if info['current'] < amount:
        return False

    # Check participant feature_uses override
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        if 'sorcery_points' in participant.feature_uses:
            participant.feature_uses['sorcery_points'] = max(0, int(participant.feature_uses['sorcery_points']) - amount)
            participant.save(update_fields=['feature_uses'])
            return True

    if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
        return participant.character.stats.spend_sorcery_points(amount)

    return False


def regain_sorcery_points(participant, amount: int) -> int:
    """Regain sorcery points up to maximum. Returns actual points regained."""
    if amount <= 0:
        return 0

    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        if 'sorcery_points' in participant.feature_uses:
            cur = int(participant.feature_uses['sorcery_points'])
            max_sp = int(participant.feature_uses.get('sorcery_points_max', cur + amount))
            gained = min(max_sp - cur, amount)
            participant.feature_uses['sorcery_points'] = cur + gained
            participant.save(update_fields=['feature_uses'])
            return gained

    if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
        return participant.character.stats.regain_sorcery_points(amount)

    return 0


def convert_slot_to_sorcery_points(participant, slot_level: int) -> Tuple[bool, int, str]:
    """
    Font of Magic: Converting a Spell Slot to Sorcery Points (Bonus Action).
    Points gained = slot_level. You can never have more points than your level allows.
    """
    if not is_sorcerer_participant(participant):
        return False, 0, f"{participant.get_name()} does not have the Font of Magic feature."

    if slot_level not in SLOT_CONVERSION_GAIN:
        return False, 0, f"Cannot convert slot level {slot_level}. Must be 1-9."

    info = get_sorcery_points_info(participant)
    if info['current'] >= info['max']:
        return False, 0, f"Sorcery Points are already at maximum ({info['max']}/{info['max']})."

    # Verify participant has an available spell slot of that level
    level_str = str(slot_level)
    if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
        stats = participant.character.stats
        slots = stats.spell_slots or {}
        expended = stats.expended_spell_slots or {}
        created = stats.created_spell_slots or {}
        
        max_available = int(slots.get(level_str, 0)) + int(created.get(level_str, 0))
        used = int(expended.get(level_str, 0))
        
        if used >= max_available:
            return False, 0, f"No level {slot_level} spell slots available to convert."

        # Expend the slot
        if not isinstance(stats.expended_spell_slots, dict):
            stats.expended_spell_slots = {}
        stats.expended_spell_slots[level_str] = used + 1
        stats.save(update_fields=['expended_spell_slots'])

    gain_potential = SLOT_CONVERSION_GAIN[slot_level]
    actual_gained = regain_sorcery_points(participant, gain_potential)
    return True, actual_gained, f"Converted a Level {slot_level} spell slot into {actual_gained} Sorcery Points."


def create_slot_from_sorcery_points(participant, slot_level: int) -> Tuple[bool, int, str]:
    """
    Font of Magic: Creating Spell Slots from Sorcery Points (Bonus Action).
    Only 1st through 5th-level slots can be created.
    """
    if not is_sorcerer_participant(participant):
        return False, 0, f"{participant.get_name()} does not have the Font of Magic feature."

    if slot_level not in SLOT_CREATION_COST:
        return False, 0, f"Cannot create slot of level {slot_level}. Font of Magic only creates 1st to 5th-level slots."

    cost = SLOT_CREATION_COST[slot_level]
    info = get_sorcery_points_info(participant)
    if info['current'] < cost:
        return False, 0, f"Insufficient Sorcery Points. Creating a Level {slot_level} slot costs {cost} points (have {info['current']})."

    spent = spend_sorcery_points(participant, cost)
    if not spent:
        return False, 0, "Failed to spend Sorcery Points."

    level_str = str(slot_level)
    if participant.character and hasattr(participant.character, 'stats') and participant.character.stats:
        stats = participant.character.stats
        # If there are expended slots of this level, replenish one
        expended = stats.expended_spell_slots or {}
        if int(expended.get(level_str, 0)) > 0:
            expended[level_str] = int(expended[level_str]) - 1
            stats.expended_spell_slots = expended
            stats.save(update_fields=['expended_spell_slots'])
        else:
            # Add bonus created slot
            if not stats.created_spell_slots or not isinstance(stats.created_spell_slots, dict):
                stats.created_spell_slots = {}
            stats.created_spell_slots[level_str] = int(stats.created_spell_slots.get(level_str, 0)) + 1
            stats.save(update_fields=['created_spell_slots'])

    return True, cost, f"Spent {cost} Sorcery Points to create a Level {slot_level} spell slot."


def get_metamagic_cost(metamagic_name: str, spell_level: Optional[int] = None, ruleset_version: str = '2014') -> Optional[int]:
    """Return the sorcery point cost for a given metamagic option."""
    if not metamagic_name:
        return None

    clean_meta = metamagic_name.strip().lower()

    if clean_meta == 'quickened':
        return 2
    elif clean_meta == 'twinned':
        lvl = 1 if (spell_level is None or spell_level == 0) else max(1, int(spell_level))
        return lvl
    elif clean_meta == 'subtle':
        return 1
    elif clean_meta == 'empowered':
        return 1
    elif clean_meta == 'careful':
        return 1
    elif clean_meta == 'heightened':
        return 2 if ruleset_version == '2024' else 3
    elif clean_meta == 'extended':
        return 1
    elif clean_meta == 'distant':
        return 1

    return None


def can_use_metamagic(participant, metamagic_name: str, spell_level: Optional[int] = None) -> Tuple[bool, Optional[int], str]:
    """
    Check if a participant can apply a specific Metamagic option.
    Returns (can_use: bool, cost: int, reason: str).
    """
    if not is_sorcerer_participant(participant):
        return False, None, f"{participant.get_name()} does not have Metamagic."

    # Minimum level 3 for Metamagic unless overridden
    lvl = 1
    if participant.character:
        lvl = participant.character.level or 1
    elif participant.feature_uses and 'level' in participant.feature_uses:
        lvl = participant.feature_uses['level']

    has_metamagic_feature = (lvl >= 3)
    if participant.feature_uses and participant.feature_uses.get('has_metamagic'):
        has_metamagic_feature = True

    if not has_metamagic_feature:
        return False, None, "Metamagic is unlocked at Sorcerer level 3."

    ruleset = '2014'
    if participant.character and getattr(participant.character, 'ruleset_version', None) == '2024':
        ruleset = '2024'

    cost = get_metamagic_cost(metamagic_name, spell_level, ruleset_version=ruleset)
    if cost is None:
        return False, None, f"Unknown Metamagic option: '{metamagic_name}'."

    info = get_sorcery_points_info(participant)
    if info['current'] < cost:
        return False, cost, f"Not enough Sorcery Points for {METAMAGIC_NAMES.get(metamagic_name.lower(), metamagic_name)}. Requires {cost} SP, currently have {info['current']} SP."

    return True, cost, "Ready to apply Metamagic."


def apply_empowered_spell_reroll(dice_count: int, dice_sides: int, cha_mod: int, initial_rolls: List[int]) -> Tuple[List[int], int, str]:
    """
    Empowered Spell: Reroll a number of damage dice up to Charisma modifier (min 1).
    Rerolls the lowest rolls and takes the new values if they are higher.
    """
    max_rerolls = max(1, cha_mod)
    sorted_indices = sorted(range(len(initial_rolls)), key=lambda i: initial_rolls[i])
    indices_to_reroll = sorted_indices[:max_rerolls]

    new_rolls = list(initial_rolls)
    reroll_notes = []

    for idx in indices_to_reroll:
        old_val = initial_rolls[idx]
        rerolled = random.randint(1, dice_sides)
        # 5e rules: "you must use the new rolls" - standard tactical usage rerolls strictly lowest
        new_rolls[idx] = rerolled
        reroll_notes.append(f"{old_val} -> {rerolled}")

    annotation = f"⚡ Empowered Spell rerolled {len(indices_to_reroll)} dice: {', '.join(reroll_notes)}"
    return new_rolls, sum(new_rolls), annotation
