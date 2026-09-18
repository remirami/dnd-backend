"""
Action Parser for D&D 5e Monster Actions, Multiattacks, Traits, and Saving Throws.
Extracts structured game mechanics from SRD descriptive text.
"""
import re

WORD_NUMBERS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
    '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
}

DAMAGE_TYPES = [
    'slashing', 'piercing', 'bludgeoning', 'fire', 'cold',
    'lightning', 'poison', 'acid', 'psychic', 'necrotic',
    'radiant', 'force', 'thunder',
]

ABILITY_MAP = {
    'strength': 'STR', 'str': 'STR',
    'dexterity': 'DEX', 'dex': 'DEX',
    'constitution': 'CON', 'con': 'CON',
    'intelligence': 'INT', 'int': 'INT',
    'wisdom': 'WIS', 'wis': 'WIS',
    'charisma': 'CHA', 'cha': 'CHA',
}

CONDITION_KEYWORDS = [
    'blinded', 'charmed', 'deafened', 'frightened', 'grappled',
    'incapacitated', 'invisible', 'paralyzed', 'petrified',
    'poisoned', 'prone', 'restrained', 'stunned', 'unconscious',
    'exhaustion',
]


def parse_recharge(name: str, desc: str):
    """
    Extract recharge mechanic info.
    Examples:
        'Fire Breath (Recharge 5-6)' -> (True, 5)
        'Lightning Breath (Recharge 6)' -> (True, 6)
        'Breath Weapons (Recharge 5–6)' (en-dash) -> (True, 5)
    """
    combined = f"{name} {desc}"
    match = re.search(r'\(Recharge\s+(\d+)(?:[\-–](\d+))?\)', combined, re.IGNORECASE)
    if match:
        min_roll = int(match.group(1))
        return True, min_roll
    return False, None


def parse_multiattack(name: str, desc: str):
    """
    Parse a Multiattack action.
    Returns:
        dict with:
            is_multiattack: bool
            action_count: int
            sequence: list[dict] e.g. [{'action_name': 'Bite', 'count': 1}, {'action_name': 'Claw', 'count': 2}]
    """
    if 'multiattack' not in name.lower():
        return {'is_multiattack': False, 'action_count': 1, 'sequence': []}

    desc_clean = desc.strip()
    action_count = 2  # default if count unclear
    sequence = []

    # Try to find overall attack count
    # Patterns: "makes two attacks", "makes three melee attacks", "makes two weapon attacks"
    count_match = re.search(
        r'makes\s+(one|two|three|four|five|\d+)\s+(?:melee|ranged|weapon|spell)?\s*attacks',
        desc_clean,
        re.IGNORECASE
    )
    if count_match:
        word = count_match.group(1).lower()
        action_count = WORD_NUMBERS.get(word, 2)

    # Try to find specific attack breakdown
    # e.g. "one with its bite and two with its claws"
    # or "two with its scimitar or two with its shortbow"
    breakdown_parts = re.findall(
        r'(one|two|three|four|five|\d+)\s+(?:attacks?\s+)?with\s+its\s+([a-zA-Z\s]+?)(?:and|or|,|\.|$)',
        desc_clean,
        re.IGNORECASE
    )

    if breakdown_parts:
        for count_str, atk_name in breakdown_parts:
            cnt = WORD_NUMBERS.get(count_str.lower(), 1)
            clean_atk = atk_name.strip()
            # Clean trailing plurals if appropriate (e.g. claws -> Claw)
            clean_atk = re.sub(r's$', '', clean_atk).title()
            sequence.append({
                'action_name': clean_atk,
                'count': cnt,
            })

    return {
        'is_multiattack': True,
        'action_count': action_count,
        'sequence': sequence,
    }


def parse_damage_formula(formula_str: str):
    """
    Parse a dice string like '2d10 + 8', '1d6+3', or '2d8'.
    Returns:
        (dice_count, dice_sides, damage_bonus)
    """
    clean = formula_str.replace(' ', '')
    match = re.match(r'(\d+)d(\d+)(?:([+\-])(\d+))?', clean)
    if not match:
        return None
    
    count = int(match.group(1))
    sides = int(match.group(2))
    sign = match.group(3)
    bonus_val = int(match.group(4)) if match.group(4) else 0
    if sign == '-':
        bonus_val = -bonus_val
    return count, sides, bonus_val


def parse_action(name: str, desc: str, raw_attack_bonus=None, raw_damage_dice=None, action_category='action'):
    """
    Comprehensive action parser.
    Returns:
        dict with fields mapped directly to EnemyAction and EnemyActionDamage.
    """
    desc_clean = desc.strip() if desc else ""
    name_clean = name.strip()

    # Detect legendary action
    legendary_cost = 1
    if name_clean.startswith('[Legendary]') or action_category == 'legendary_action':
        action_type = 'legendary_action'
        name_clean = name_clean.replace('[Legendary]', '').strip()
        cost_match = re.search(r'\(Costs\s+(\d+)\s+Actions?\)', name_clean, re.IGNORECASE)
        if cost_match:
            legendary_cost = int(cost_match.group(1))
            name_clean = re.sub(r'\(Costs\s+\d+\s+Actions?\)', '', name_clean).strip()
    elif 'bonus action' in desc_clean.lower() or action_category == 'bonus_action':
        action_type = 'bonus_action'
    elif 'reaction' in desc_clean.lower() or action_category == 'reaction':
        action_type = 'reaction'
    else:
        action_type = 'action'

    # Detect recharge
    has_recharge, recharge_min_roll = parse_recharge(name_clean, desc_clean)

    # Detect attack type
    attack_type = 'melee_weapon'
    if re.search(r'melee weapon attack', desc_clean, re.IGNORECASE):
        attack_type = 'melee_weapon'
    elif re.search(r'ranged weapon attack', desc_clean, re.IGNORECASE):
        attack_type = 'ranged_weapon'
    elif re.search(r'melee spell attack', desc_clean, re.IGNORECASE):
        attack_type = 'melee_spell'
    elif re.search(r'ranged spell attack', desc_clean, re.IGNORECASE):
        attack_type = 'ranged_spell'
    elif 'saving throw' in desc_clean.lower() and not re.search(r'attack:', desc_clean, re.IGNORECASE):
        attack_type = 'saving_throw'
    elif 'saving throw' in desc_clean.lower() and ('breath' in name_clean.lower() or has_recharge):
        attack_type = 'saving_throw'
    elif not re.search(r'\+\d+\s+to hit', desc_clean, re.IGNORECASE) and not raw_attack_bonus:
        attack_type = 'utility'

    # Attack bonus
    attack_bonus = None
    if raw_attack_bonus is not None and int(raw_attack_bonus) > 0:
        attack_bonus = int(raw_attack_bonus)
    else:
        bonus_match = re.search(r'\+(\d+)\s+to hit', desc_clean, re.IGNORECASE)
        if bonus_match:
            attack_bonus = int(bonus_match.group(1))

    # Reach / Range / Area
    reach_or_range = ""
    reach_match = re.search(r'reach\s+(\d+\s*ft\.)', desc_clean, re.IGNORECASE)
    range_match = re.search(r'range\s+(\d+(?:/\d+)?\s*ft\.)', desc_clean, re.IGNORECASE)
    area_match = re.search(r'(\d+[\-–]foot\s+(?:cone|line|cube|sphere|radius))', desc_clean, re.IGNORECASE)

    if reach_match and range_match:
        reach_or_range = f"reach {reach_match.group(1)}, range {range_match.group(1)}"
    elif reach_match:
        reach_or_range = f"reach {reach_match.group(1)}"
    elif range_match:
        reach_or_range = f"range {range_match.group(1)}"
    elif area_match:
        reach_or_range = area_match.group(1)

    # Saving Throw details
    saving_throw_dc = None
    saving_throw_ability = None
    half_damage_on_save = False

    save_match = re.search(
        r'DC\s+(\d+)\s+(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma|STR|DEX|CON|INT|WIS|CHA)\s+saving throw',
        desc_clean,
        re.IGNORECASE
    )
    if save_match:
        saving_throw_dc = int(save_match.group(1))
        ability_str = save_match.group(2).lower()
        saving_throw_ability = ABILITY_MAP.get(ability_str)

        if re.search(r'half\s+(?:as\s+much\s+)?damage', desc_clean, re.IGNORECASE):
            half_damage_on_save = True

    # Conditions inflicted
    conditions_inflicted = []
    for cond in CONDITION_KEYWORDS:
        # Avoid false positives by requiring context
        pattern = rf'(?:become|be|knocked|is|target is|target must succeed|fall)\s+(?:\w+\s+)?{cond}'
        if re.search(pattern, desc_clean, re.IGNORECASE) or re.search(rf'\b{cond}\b', desc_clean, re.IGNORECASE) and ('condition' in desc_clean.lower() or 'saving throw' in desc_clean.lower()):
            conditions_inflicted.append(cond)

    condition_save_end = bool(
        re.search(r'repeat(?:ing)?\s+the\s+saving\s+throw\s+at\s+the\s+end\s+of', desc_clean, re.IGNORECASE)
    )

    # Damage rolls
    damage_rolls = []

    # Primary damage extraction
    # Patterns:
    # "Hit: 19 (2d10 + 8) piercing damage"
    # "taking 63 (18d6) fire damage"
    # "Hit: 7 (2d4 + 2) piercing damage"
    primary_found = False
    
    # Check for "Hit: X (NdM + B) type damage" or "taking X (NdM) type damage"
    hit_damage_matches = re.finditer(
        r'(?:Hit:\s*\d+\s*\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)|taking\s*\d+\s*\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\))\s*([a-zA-Z]+)?\s*damage',
        desc_clean,
        re.IGNORECASE
    )
    for m in hit_damage_matches:
        dice_str = m.group(1) or m.group(2)
        dtype = (m.group(3) or '').lower()
        if dtype not in DAMAGE_TYPES:
            dtype = None
        parsed = parse_damage_formula(dice_str)
        if parsed:
            count, sides, bonus = parsed
            damage_rolls.append({
                'dice_count': count,
                'dice_sides': sides,
                'damage_bonus': bonus,
                'damage_type_name': dtype,
                'is_secondary': primary_found,
            })
            primary_found = True

    # Secondary/rider damage: e.g. "plus 7 (2d6) poison damage"
    plus_matches = re.finditer(
        r'plus\s+\d+\s*\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)\s*([a-zA-Z]+)?\s*damage',
        desc_clean,
        re.IGNORECASE
    )
    for m in plus_matches:
        dice_str = m.group(1)
        dtype = (m.group(2) or '').lower()
        if dtype not in DAMAGE_TYPES:
            dtype = None
        parsed = parse_damage_formula(dice_str)
        if parsed:
            count, sides, bonus = parsed
            damage_rolls.append({
                'dice_count': count,
                'dice_sides': sides,
                'damage_bonus': bonus,
                'damage_type_name': dtype,
                'is_secondary': True,
            })

    # Fallback to raw_damage_dice if no damage parsed from text
    if not damage_rolls and raw_damage_dice:
        parsed = parse_damage_formula(raw_damage_dice)
        if parsed:
            count, sides, bonus = parsed
            # Try to find damage type in description
            dtype = None
            for dt in DAMAGE_TYPES:
                if dt in desc_clean.lower():
                    dtype = dt
                    break
            damage_rolls.append({
                'dice_count': count,
                'dice_sides': sides,
                'damage_bonus': bonus,
                'damage_type_name': dtype,
                'is_secondary': False,
            })

    return {
        'name': name_clean,
        'description': desc_clean,
        'action_type': action_type,
        'attack_type': attack_type,
        'attack_bonus': attack_bonus,
        'reach_or_range': reach_or_range,
        'saving_throw_dc': saving_throw_dc,
        'saving_throw_ability': saving_throw_ability,
        'half_damage_on_save': half_damage_on_save,
        'conditions_inflicted': list(set(conditions_inflicted)),
        'condition_save_end': condition_save_end,
        'has_recharge': has_recharge,
        'recharge_min_roll': recharge_min_roll,
        'legendary_cost': legendary_cost,
        'damage_rolls': damage_rolls,
    }


def parse_trait(name: str, desc: str):
    """
    Parse and classify an enemy special ability / trait.
    """
    name_clean = name.strip()
    desc_clean = desc.strip() if desc else ""
    name_lower = name_clean.lower()

    if 'pack tactics' in name_lower:
        trait_type = 'pack_tactics'
    elif 'magic resistance' in name_lower:
        trait_type = 'magic_resistance'
    elif 'undead fortitude' in name_lower:
        trait_type = 'undead_fortitude'
    elif 'spider climb' in name_lower:
        trait_type = 'spider_climb'
    elif any(k in name_lower for k in ['keen hearing', 'keen smell', 'keen sight', 'keen senses']):
        trait_type = 'keen_senses'
    elif 'regeneration' in name_lower:
        trait_type = 'regeneration'
    elif 'relentless' in name_lower:
        trait_type = 'relentless'
    elif 'amphibious' in name_lower:
        trait_type = 'amphibious'
    elif 'legendary resistance' in name_lower:
        trait_type = 'legendary_resistance'
    elif 'nimble escape' in name_lower:
        trait_type = 'nimble_escape'
    elif 'sneak attack' in name_lower:
        trait_type = 'sneak_attack'
    else:
        trait_type = 'general'

    return {
        'name': name_clean,
        'description': desc_clean,
        'trait_type': trait_type,
    }
