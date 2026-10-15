"""
Spell Rules Engine - Centralized 5e rules lookup and resolution for specific spells.

Provides declarative rules definitions for D&D 5e spells, including:
- Attack-roll vs saving-throw mechanics
- Range and target constraints (e.g., humanoid only, no undead healing)
- Post-cast riders (e.g., Shocking Grasp reaction denial, Ray of Frost speed reduction)
- Bonus action / Reaction classifications
"""

SPELL_RULES = {
    # Cantrips
    'fire bolt': {
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'fire',
        'damage': '1d10 fire',
    },
    'eldritch blast': {
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'force',
        'damage': '1d10 force',
    },
    'shocking grasp': {
        'range': 'Touch',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'lightning',
        'damage': '1d8 lightning',
        'prevents_reactions': True,
        'advantage_vs_metal': True,
    },
    'ray of frost': {
        'range': '60 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'cold',
        'damage': '1d8 cold',
        'speed_reduction': 10,
    },
    'sacred flame': {
        'range': '60 feet',
        'save_type': 'DEX',
        'half_on_save': False,
        'ignores_cover': True,
        'damage_type': 'radiant',
        'damage': '1d8 radiant',
    },
    'toll the dead': {
        'range': '60 feet',
        'save_type': 'WIS',
        'half_on_save': False,
        'damage_type': 'necrotic',
        'damage_full_hp': '1d8 necrotic',
        'damage_wounded': '1d12 necrotic',
    },
    'vicious mockery': {
        'range': '60 feet',
        'save_type': 'WIS',
        'half_on_save': False,
        'damage_type': 'psychic',
        'damage': '1d4 psychic',
        'disadvantage_on_next_attack': True,
    },
    'acid splash': {
        'range': '60 feet',
        'save_type': 'DEX',
        'half_on_save': False,
        'damage_type': 'acid',
        'damage': '1d6 acid',
    },
    'poison spray': {
        'range': '10 feet',
        'save_type': 'CON',
        'half_on_save': False,
        'damage_type': 'poison',
        'damage': '1d12 poison',
    },
    'chill touch': {
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'necrotic',
        'damage': '1d8 necrotic',
    },
    'produce flame': {
        'range': '30 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'fire',
        'damage': '1d8 fire',
    },
    'thorn whip': {
        'range': '30 feet',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'piercing',
        'damage': '1d6 piercing',
    },
    'primal savagery': {
        'range': 'Self',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'acid',
        'damage': '1d10 acid',
    },
    'thunderclap': {
        'range': 'Self (5-foot sphere)',
        'save_type': 'CON',
        'half_on_save': False,
        'damage_type': 'thunder',
        'damage': '1d6 thunder',
    },
    'word of radiance': {
        'range': 'Self (5-foot sphere)',
        'save_type': 'CON',
        'half_on_save': False,
        'damage_type': 'radiant',
        'damage': '1d6 radiant',
    },
    'mind sliver': {
        'range': '60 feet',
        'save_type': 'INT',
        'half_on_save': False,
        'damage_type': 'psychic',
        'damage': '1d6 psychic',
    },
    'frostbite': {
        'range': '60 feet',
        'save_type': 'CON',
        'half_on_save': False,
        'damage_type': 'cold',
        'damage': '1d6 cold',
    },
    'infestation': {
        'range': '30 feet',
        'save_type': 'CON',
        'half_on_save': False,
        'damage_type': 'poison',
        'damage': '1d6 poison',
    },
    'create bonfire': {
        'range': '60 feet',
        'save_type': 'DEX',
        'half_on_save': False,
        'damage_type': 'fire',
        'damage': '1d8 fire',
        'requires_concentration': True,
    },
    'lightning lure': {
        'range': '15 feet',
        'save_type': 'STR',
        'half_on_save': False,
        'damage_type': 'lightning',
        'damage': '1d8 lightning',
    },
    'sword burst': {
        'range': 'Self (5-foot sphere)',
        'save_type': 'DEX',
        'half_on_save': False,
        'damage_type': 'force',
        'damage': '1d6 force',
    },
    'shillelagh': {
        'range': 'Touch',
        'damage_type': 'bludgeoning',
        'damage': '1d8 bludgeoning',
    },
    'spare the dying': {
        'range': 'Touch',
        'stabilizes_dying': True,
        'requires_zero_hp': True,
    },
    'guidance': {
        'range': 'Touch',
        'requires_concentration': True,
    },

    # 1st Level Spells
    'cure wounds': {
        'base_level': 1,
        'range': 'Touch',
        'is_healing': True,
        'healing': '1d8',
        'no_undead_or_construct': True,
    },
    'healing word': {
        'base_level': 1,
        'range': '60 feet',
        'is_healing': True,
        'healing': '1d4',
        'is_bonus_action': True,
        'no_undead_or_construct': True,
    },
    'inflict wounds': {
        'base_level': 1,
        'range': 'Touch',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'necrotic',
        'damage': '3d10 necrotic',
    },
    'guiding bolt': {
        'base_level': 1,
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'radiant',
        'damage': '4d6 radiant',
        'grants_next_attack_advantage': True,
    },
    'magic missile': {
        'base_level': 1,
        'range': '120 feet',
        'auto_hit': True,
        'damage_type': 'force',
        'dart_count': 3,
        'dart_damage': '1d4+1 force',
    },
    'shield': {
        'base_level': 1,
        'range': 'Self',
        'is_reaction': True,
        'ac_bonus': 5,
        'negates_magic_missile': True,
    },
    'mage armor': {
        'base_level': 1,
        'range': 'Touch',
        'target_unarmored_only': True,
        'base_ac_override': 13,
    },
    'thunderwave': {
        'base_level': 1,
        'range': 'Self (15-foot cube)',
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'thunder',
        'damage': '2d8 thunder',
        'push_distance': 10,
    },
    'burning hands': {
        'base_level': 1,
        'range': 'Self (15-foot cone)',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '3d6 fire',
    },
    'grease': {
        'base_level': 1,
        'range': '60 feet (10-foot square)',
        'save_type': 'DEX',
        'condition': 'prone',
        'creates_difficult_terrain': True,
    },
    'fog cloud': {
        'base_level': 1,
        'range': '120 feet (20-foot radius)',
        'requires_concentration': True,
        'creates_heavily_obscured': True,
    },

    # Control & Status Spells
    'hold person': {
        'base_level': 2,
        'range': '60 feet',
        'save_type': 'WIS',
        'requires_concentration': True,
        'condition': 'paralyzed',
        'humanoid_only': True,
        'upcast_targets': True,
    },
    'sleep': {
        'base_level': 1,
        'range': '90 feet',
        'radius': 20,
        'condition': 'unconscious',
        'no_undead_or_immune': True,
        'damage': '5d8',
        'upcast_dice_count': 2,
    },

    # Mobility & Buffs
    'misty step': {
        'base_level': 2,
        'range': 'Self',
        'is_bonus_action': True,
        'teleport_distance': 30,
    },
    'color spray': {
        'base_level': 1,
        'range': 'Self (15-foot cone)',
        'condition': 'blinded',
        'damage': '6d10',
        'upcast_dice_count': 2,
    },
    'entangle': {
        'base_level': 1,
        'range': '90 feet',
        'save_type': 'STR',
        'condition': 'restrained',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'faerie fire': {
        'base_level': 1,
        'range': '60 feet',
        'save_type': 'DEX',
        'requires_concentration': True,
        'grants_next_attack_advantage': True,
    },
    'shatter': {
        'base_level': 2,
        'range': '60 feet',
        'radius': 10,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'thunder',
        'damage': '3d8 thunder',
    },
    'scorching ray': {
        'base_level': 2,
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'fire',
        'damage': '6d6 fire',
    },
    'spiritual weapon': {
        'base_level': 2,
        'range': '60 feet',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'force',
        'damage': '1d8 force',
    },
    'darkness': {
        'base_level': 2,
        'range': '60 feet',
        'radius': 15,
        'requires_concentration': True,
        'creates_magical_darkness': True,
    },
    'moonbeam': {
        'base_level': 2,
        'range': '120 feet',
        'radius': 5,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'radiant',
        'damage': '2d10 radiant',
        'requires_concentration': True,
    },
    'flaming sphere': {
        'base_level': 2,
        'range': '60 feet',
        'radius': 5,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '2d6 fire',
        'requires_concentration': True,
    },
    'gust of wind': {
        'base_level': 2,
        'range': 'Self (60-foot line)',
        'save_type': 'STR',
        'push_distance': 15,
        'requires_concentration': True,
    },
    'spike growth': {
        'base_level': 2,
        'range': '150 feet',
        'radius': 20,
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'web': {
        'base_level': 2,
        'range': '60 feet',
        'save_type': 'DEX',
        'condition': 'restrained',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'calm emotions': {
        'base_level': 2,
        'range': '60 feet',
        'radius': 20,
        'save_type': 'CHA',
        'requires_concentration': True,
    },
    'silence': {
        'base_level': 2,
        'range': '120 feet',
        'radius': 20,
        'requires_concentration': True,
    },
    'fireball': {
        'base_level': 3,
        'range': '150 feet',
        'radius': 20,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '8d6 fire',
    },
    'lightning bolt': {
        'base_level': 3,
        'range': 'Self (100-foot line)',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'lightning',
        'damage': '8d6 lightning',
    },
    'call lightning': {
        'base_level': 3,
        'range': '120 feet',
        'radius': 5,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'lightning',
        'damage': '3d10 lightning',
        'requires_concentration': True,
    },
    'sleet storm': {
        'base_level': 3,
        'range': '150 feet',
        'radius': 40,
        'save_type': 'DEX',
        'condition': 'prone',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
        'creates_heavily_obscured': True,
    },
    'stinking cloud': {
        'base_level': 3,
        'range': '90 feet',
        'radius': 20,
        'save_type': 'CON',
        'condition': 'poisoned',
        'requires_concentration': True,
        'creates_heavily_obscured': True,
    },
    'spirit guardians': {
        'base_level': 3,
        'range': 'Self (15-foot radius)',
        'radius': 15,
        'save_type': 'WIS',
        'half_on_save': True,
        'damage_type': 'radiant',
        'damage': '3d8 radiant',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'fear': {
        'base_level': 3,
        'range': 'Self (30-foot cone)',
        'save_type': 'WIS',
        'condition': 'frightened',
        'requires_concentration': True,
    },
    'hypnotic pattern': {
        'base_level': 3,
        'range': '120 feet',
        'save_type': 'WIS',
        'condition': 'incapacitated',
        'requires_concentration': True,
    },
    'slow': {
        'base_level': 3,
        'range': '120 feet',
        'save_type': 'WIS',
        'requires_concentration': True,
        'speed_reduction': 15,
    },
    'wind wall': {
        'base_level': 3,
        'range': '120 feet',
        'save_type': 'STR',
        'half_on_save': True,
        'damage_type': 'bludgeoning',
        'damage': '3d8 bludgeoning',
        'requires_concentration': True,
    },
    'ice storm': {
        'base_level': 4,
        'range': '300 feet',
        'radius': 20,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'cold',
        'damage': '2d8 bludgeoning + 4d6 cold',
        'creates_difficult_terrain': True,
    },
    'wall of fire': {
        'base_level': 4,
        'range': '120 feet',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '5d8 fire',
        'requires_concentration': True,
    },
    'black tentacles': {
        'base_level': 4,
        'range': '90 feet',
        'save_type': 'DEX',
        'condition': 'restrained',
        'half_on_save': False,
        'damage_type': 'bludgeoning',
        'damage': '3d6 bludgeoning',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'confusion': {
        'base_level': 4,
        'range': '90 feet',
        'radius': 10,
        'save_type': 'WIS',
        'requires_concentration': True,
    },
    'cone of cold': {
        'base_level': 5,
        'range': 'Self (60-foot cone)',
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'cold',
        'damage': '8d8 cold',
    },
    'cloudkill': {
        'base_level': 5,
        'range': '120 feet',
        'radius': 20,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'poison',
        'damage': '5d8 poison',
        'requires_concentration': True,
        'creates_heavily_obscured': True,
    },
    'flame strike': {
        'base_level': 5,
        'range': '60 feet',
        'radius': 10,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '4d6 fire + 4d6 radiant',
    },
    'destructive wave': {
        'base_level': 5,
        'range': 'Self (30-foot radius)',
        'radius': 30,
        'save_type': 'CON',
        'condition': 'prone',
        'half_on_save': True,
        'damage_type': 'thunder',
        'damage': '5d6 thunder + 5d6 radiant',
    },
    'insect plague': {
        'base_level': 5,
        'range': '300 feet',
        'radius': 20,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'piercing',
        'damage': '4d10 piercing',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'mass cure wounds': {
        'base_level': 5,
        'range': '60 feet',
        'radius': 30,
        'is_healing': True,
        'healing': '3d8',
        'no_undead_or_construct': True,
    },
    'circle of death': {
        'base_level': 6,
        'range': '150 feet',
        'radius': 60,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'necrotic',
        'damage': '8d6 necrotic',
    },
    'disintegrate': {
        'base_level': 6,
        'range': '60 feet',
        'save_type': 'DEX',
        'half_on_save': False,
        'damage_type': 'force',
        'damage': '10d6+40 force',
    },
    'sunbeam': {
        'base_level': 6,
        'range': 'Self (60-foot line)',
        'save_type': 'CON',
        'condition': 'blinded',
        'half_on_save': True,
        'damage_type': 'radiant',
        'damage': '6d8 radiant',
        'requires_concentration': True,
    },
    'freezing sphere': {
        'base_level': 6,
        'range': '300 feet',
        'radius': 60,
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'cold',
        'damage': '10d6 cold',
    },
    'delayed blast fireball': {
        'base_level': 7,
        'range': '150 feet',
        'radius': 20,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '12d6 fire',
        'requires_concentration': True,
    },
    'fire storm': {
        'base_level': 7,
        'range': '150 feet',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '7d10 fire',
    },
    'prismatic spray': {
        'base_level': 7,
        'range': 'Self (60-foot cone)',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'prismatic',
        'damage': '10d6',
    },
    'sunburst': {
        'base_level': 8,
        'range': '150 feet',
        'radius': 60,
        'save_type': 'CON',
        'condition': 'blinded',
        'half_on_save': True,
        'damage_type': 'radiant',
        'damage': '12d6 radiant',
    },
    'earthquake': {
        'base_level': 8,
        'range': '500 feet',
        'radius': 100,
        'save_type': 'DEX',
        'condition': 'prone',
        'requires_concentration': True,
        'creates_difficult_terrain': True,
    },
    'incendiary cloud': {
        'base_level': 8,
        'range': '150 feet',
        'radius': 20,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '10d8 fire',
        'requires_concentration': True,
        'creates_heavily_obscured': True,
    },
    'meteor swarm': {
        'base_level': 9,
        'range': '1 mile',
        'radius': 40,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '20d6 fire + 20d6 bludgeoning',
    },
}


def get_spell_rule(spell_name):
    """Retrieve rule definition for a spell by name (case-insensitive)."""
    if not spell_name:
        return {}
    clean = str(spell_name).strip().lower()
    return SPELL_RULES.get(clean, {})


def is_spell_attack_roll(spell_name):
    """Check if spell resolves with an attack roll instead of a saving throw."""
    rule = get_spell_rule(spell_name)
    return rule.get('requires_attack_roll', False)


CANTRIP_NAMES = {
    'fire bolt', 'eldritch blast', 'shocking grasp', 'ray of frost',
    'sacred flame', 'toll the dead', 'vicious mockery', 'acid splash',
    'poison spray', 'chill touch', 'primal savagery', 'thorn whip',
    'word of radiance', 'guidance', 'spare the dying', 'resistance',
    'mage hand', 'light', 'minor illusion', 'prestidigitation', 'true strike',
    'produce flame', 'shillelagh', 'thunderclap', 'mind sliver', 'frostbite',
    'infestation', 'create bonfire', 'lightning lure', 'sword burst',
    'mending', 'message', 'dancing lights', 'druidcraft', 'thaumaturgy'
}


def is_cantrip(spell_name):
    """Check if a spell is a cantrip (level 0)."""
    if not spell_name:
        return False
    clean = str(spell_name).strip().lower()
    if clean in CANTRIP_NAMES:
        return True
    try:
        from spells.models import Spell
        return Spell.objects.filter(name__iexact=clean, level=0).exists()
    except Exception:
        return False


def get_cantrip_multiplier(level):
    """
    D&D 5e Cantrip scaling multiplier based on character level / CR:
    - Levels 1-4: 1x (1 die)
    - Levels 5-10: 2x (2 dice)
    - Levels 11-16: 3x (3 dice)
    - Levels 17-20: 4x (4 dice)
    """
    try:
        lvl = int(level)
    except (ValueError, TypeError):
        lvl = 1
    if lvl >= 17:
        return 4
    elif lvl >= 11:
        return 3
    elif lvl >= 5:
        return 2
    return 1


def scale_cantrip_damage(formula, level):
    """
    Scales a cantrip damage formula (e.g., '1d10', '1d10 force', '1d8') based on caster level.
    e.g., for level 20: '1d10' -> '4d10', '1d10 force' -> '4d10 force'.
    """
    if not formula:
        return formula
    multiplier = get_cantrip_multiplier(level)
    if multiplier <= 1:
        return formula

    import re
    def _scale(m):
        base_count = int(m.group(1))
        if base_count == 1:
            return f"{multiplier}d{m.group(2)}"
        return m.group(0)

    return re.sub(r'(\d+)d(\d+)', _scale, formula, count=1)


def get_spell_base_level(spell_name, spell_obj=None, aoe_template=None):
    """
    Retrieve the base spell slot level for a spell (0 for cantrips, 1-9 for leveled spells).
    """
    if not spell_name:
        return 1
    clean = str(spell_name).strip().lower()
    if is_cantrip(clean):
        return 0
    rule = get_spell_rule(clean) or get_buff_rule(clean) or {}
    if 'base_level' in rule:
        return rule['base_level']
    if aoe_template and 'base_level' in aoe_template:
        return aoe_template['base_level']
    if spell_obj and hasattr(spell_obj, 'level') and spell_obj.level is not None:
        return spell_obj.level
    return 1


def scale_upcast_spell_damage(spell_name, formula, base_level, cast_slot_level):
    """
    Scales a leveled spell damage/healing formula when cast using a higher-level spell slot.
    D&D 5e Upcasting rules:
    - Standard additive: +1 die per slot level above base level (e.g. Fireball 8d6 @ lvl 3 -> 9d6 @ lvl 4, 10d6 @ lvl 5)
    - Scorching Ray: +2d6 (1 additional ray) per slot level above 2nd (6d6 @ lvl 2 -> 8d6 @ lvl 3, 10d6 @ lvl 4)
    - Sleep: +2d8 per slot level above 1st (5d8 @ lvl 1 -> 7d8 @ lvl 2, 9d8 @ lvl 3)
    - Color Spray: +2d10 per slot level above 1st (6d10 @ lvl 1 -> 8d10 @ lvl 2, 10d10 @ lvl 3)
    - Spiritual Weapon: +1d8 per 2 slot levels above 2nd (1d8 @ lvl 2-3, 2d8 @ lvl 4-5, 3d8 @ lvl 6-7)
    - Disintegrate: +3d6 per slot level above 6th (10d6+40 @ lvl 6 -> 13d6+40 @ lvl 7)
    """
    if not formula:
        return formula
    try:
        cast_lvl = int(cast_slot_level)
        base_lvl = int(base_level)
    except (ValueError, TypeError):
        return formula

    extra_levels = cast_lvl - base_lvl
    if extra_levels <= 0:
        return formula

    import re
    clean = str(spell_name).strip().lower()

    # Special stepped / multi-die scaling
    if clean == 'scorching ray':
        total_dice = 6 + (extra_levels * 2)
        return re.sub(r'^\d+d6', f"{total_dice}d6", formula)

    if clean == 'sleep':
        total_dice = 5 + (extra_levels * 2)
        return re.sub(r'^\d+d8', f"{total_dice}d8", formula)

    if clean == 'color spray':
        total_dice = 6 + (extra_levels * 2)
        return re.sub(r'^\d+d10', f"{total_dice}d10", formula)

    if clean == 'spiritual weapon':
        total_dice = 1 + (extra_levels // 2)
        return re.sub(r'^\d+d8', f"{total_dice}d8", formula)

    if clean == 'disintegrate':
        total_dice = 10 + (extra_levels * 3)
        return re.sub(r'^\d+d6', f"{total_dice}d6", formula)

    # General 5e additive upcasting (+1 die per slot level above base level)
    rule = get_spell_rule(clean)
    dice_per_level = rule.get('upcast_dice_count', 1)

    def _upcast_match(m):
        base_dice = int(m.group(1))
        new_dice = base_dice + (extra_levels * dice_per_level)
        return f"{new_dice}d{m.group(2)}"

    return re.sub(r'(\d+)d(\d+)', _upcast_match, formula, count=1)


def can_heal_target(target, spell_name):
    """
    Check if a target can receive healing from a given spell.
    Spells like Cure Wounds / Healing Word cannot heal undead or constructs.
    """
    rule = get_spell_rule(spell_name)
    if not rule.get('no_undead_or_construct'):
        return True
    
    # Check enemy creature type
    if target.encounter_enemy and target.encounter_enemy.enemy:
        enemy_type = (target.encounter_enemy.enemy.creature_type or '').lower()
        if enemy_type in ['undead', 'construct']:
            return False
    return True


def apply_spell_post_effects(caster, target, spell_name, hit_or_save_failed=True):
    """
    Apply special post-resolution riders from spells:
    - Shocking Grasp: target cannot take reactions until start of its next turn
    - Ray of Frost: target speed reduced by 10 ft
    - Guiding Bolt: next attack against target has advantage
    """
    if not hit_or_save_failed or not target:
        return []

    effects_applied = []
    rule = get_spell_rule(spell_name)

    if rule.get('prevents_reactions'):
        target.reaction_used = True
        target.save(update_fields=['reaction_used'])
        effects_applied.append(f"{target.get_name()} cannot take reactions until start of next turn.")

    if rule.get('speed_reduction'):
        reduction = rule['speed_reduction']
        if not target.feature_uses:
            target.feature_uses = {}
        target.feature_uses['speed_penalty'] = target.feature_uses.get('speed_penalty', 0) + reduction
        target.save(update_fields=['feature_uses'])
        effects_applied.append(f"{target.get_name()}'s speed is reduced by {reduction} ft.")

    if rule.get('grants_next_attack_advantage'):
        effects_applied.append(f"Mystical dim light glitters on {target.get_name()}, granting Advantage on the next attack roll against it.")

    return effects_applied


def has_active_shield(participant):
    """
    Check if a combat participant currently has an active Shield spell protecting them.
    Under 5e rules, the Shield spell completely negates all damage from Magic Missile.
    """
    if not participant:
        return False
    # Check feature_uses flag
    if participant.feature_uses and participant.feature_uses.get('shield_spell_active'):
        return True
    # Check notes
    if participant.notes and 'shield spell active' in str(participant.notes).lower():
        return True
    # Check if participant cast Shield reaction/spell in current round
    try:
        from combat.models import CombatAction
        if participant.combat_session:
            return CombatAction.objects.filter(
                combat_session=participant.combat_session,
                actor=participant,
                attack_name__iexact='shield',
                round_number=participant.combat_session.current_round
            ).exists()
    except Exception:
        pass
    return False


BUFF_SPELL_RULES = {
    'protection from evil and good': {
        'name': 'Protection from Evil and Good',
        'base_level': 1,
        'requires_concentration': True,
        'disadvantage_creature_types': ['aberration', 'celestial', 'elemental', 'fey', 'fiend', 'undead'],
        'immune_conditions': ['charmed', 'frightened'],
        'description': 'Protected against aberrations, celestials, elementals, fey, fiends, and undead. Their attacks have Disadvantage against the target, and target cannot be charmed, frightened, or possessed by them.',
    },
    'shield of faith': {
        'name': 'Shield of Faith',
        'base_level': 1,
        'requires_concentration': True,
        'ac_bonus': 2,
        'description': 'A shimmering divine field surrounds the target, granting a +2 bonus to AC.',
    },
    'bless': {
        'name': 'Bless',
        'base_level': 1,
        'requires_concentration': True,
        'bonus_dice': '1d4',
        'description': 'Divine favor grants +1d4 added to all attack rolls and saving throws.',
    },
    'mage armor': {
        'name': 'Mage Armor',
        'base_level': 1,
        'requires_concentration': False,
        'base_ac_override': 13,
        'description': 'Target’s base AC becomes 13 + Dex modifier while not wearing armor.',
    },
    'shield': {
        'name': 'Shield',
        'base_level': 1,
        'requires_concentration': False,
        'ac_bonus': 5,
        'duration_type': 'until_next_turn',
        'negates_magic_missile': True,
        'description': 'An invisible barrier of magical force grants a +5 bonus to AC and complete immunity to Magic Missile until the start of your next turn.',
    },
    'blur': {
        'name': 'Blur',
        'base_level': 2,
        'requires_concentration': True,
        'attacks_have_disadvantage': True,
        'description': 'Your body becomes blurred and shifting. Attack rolls against you have Disadvantage.',
    },
    'mirror image': {
        'name': 'Mirror Image',
        'base_level': 2,
        'requires_concentration': False,
        'duplicates': 3,
        'description': 'Three illusory duplicates appear, redirecting incoming attacks away from you.',
    },
    'false life': {
        'name': 'False Life',
        'base_level': 1,
        'requires_concentration': False,
        'temp_hp': 8,
        'description': 'Bolstering necromantic energy grants temporary hit points.',
    },
    'armor of agathys': {
        'name': 'Armor of Agathys',
        'base_level': 1,
        'requires_concentration': False,
        'temp_hp': 5,
        'retaliation_damage': 5,
        'retaliation_type': 'cold',
        'description': 'Spectral frost grants 5 temp HP. Melee attackers take 5 cold damage when hitting you.',
    },
    'aid': {
        'name': 'Aid',
        'base_level': 2,
        'requires_concentration': False,
        'hp_boost': 5,
        'description': 'Bolsters your allies with toughness and resolve, increasing current and maximum HP by 5 (+5 per level above 2nd).',
    },
    'expeditious retreat': {
        'name': 'Expeditious Retreat',
        'base_level': 1,
        'requires_concentration': True,
        'bonus_dash': True,
        'description': 'Allows taking the Dash action as a bonus action each turn.',
    },
    'fire shield': {
        'name': 'Fire Shield',
        'base_level': 4,
        'requires_concentration': False,
        'retaliation_damage': '2d8',
        'description': 'Thin flames wreathe your body. Melee attackers within 5 ft take 2d8 damage, and you gain damage resistance.',
    },
    'haste': {
        'name': 'Haste',
        'base_level': 3,
        'requires_concentration': True,
        'ac_bonus': 2,
        'speed_multiplier': 2.0,
        'advantage_dex_saves': True,
        'extra_action': True,
        'description': '+2 AC, double speed, advantage on Dex saves, and an extra action.',
    },
    'fly': {
        'name': 'Fly',
        'base_level': 3,
        'requires_concentration': True,
        'upcast_targets': True,
        'description': 'The target gains a flying speed of 60 feet. Can target +1 creature per slot level above 3rd.',
    },
    'heroism': {
        'name': 'Heroism',
        'base_level': 1,
        'requires_concentration': True,
        'immune_conditions': ['frightened'],
        'description': 'Target is immune to being frightened and gains temporary HP at the start of each turn.',
    },
    'barkskin': {
        'name': 'Barkskin',
        'base_level': 2,
        'requires_concentration': True,
        'min_ac': 16,
        'description': 'Target’s AC cannot be less than 16, regardless of armor.',
    },
    'guidance': {
        'name': 'Guidance',
        'base_level': 0,
        'requires_concentration': True,
        'bonus_dice': '1d4',
        'description': '+1d4 bonus to one ability check.',
    },
    'resistance': {
        'name': 'Resistance',
        'base_level': 0,
        'requires_concentration': True,
        'bonus_dice': '1d4',
        'description': '+1d4 bonus to one saving throw.',
    },
    'invisibility': {
        'name': 'Invisibility',
        'base_level': 2,
        'requires_concentration': True,
        'condition': 'invisible',
        'upcast_targets': True,
        'description': 'Target is invisible. Attacks have advantage, attacks against have disadvantage. Can target +1 creature per slot level above 2nd.',
    },
}

BUFF_SPELL_ALIASES = {
    'protection from undead': 'protection from evil and good',
    'protect from undead': 'protection from evil and good',
    'protect from evil and good': 'protection from evil and good',
    'protection from evil & good': 'protection from evil and good',
    'protect from evil & good': 'protection from evil and good',
}


def normalize_buff_spell_name(spell_name):
    """Normalize a spell name to a canonical buff key."""
    if not spell_name:
        return ''
    clean = str(spell_name).strip().lower()
    return BUFF_SPELL_ALIASES.get(clean, clean)


def is_buff_spell(spell_name):
    """Check if a spell provides a positive combat buff."""
    canon = normalize_buff_spell_name(spell_name)
    return canon in BUFF_SPELL_RULES


def get_buff_rule(spell_name):
    """Retrieve the buff rule dict for a given spell name."""
    canon = normalize_buff_spell_name(spell_name)
    return BUFF_SPELL_RULES.get(canon)


def apply_buff_to_target(caster, target, spell_name, spell_level=1):
    """
    Apply a buff effect to a combat participant.
    Records caster ID (for concentration expiration), AC bonuses, dice bonuses, etc.
    Scales upcastable buffs (Armor of Agathys, False Life, Aid).
    """
    rule = get_buff_rule(spell_name)
    if not rule or not target:
        return None

    buff_name = rule['name']
    ac_bonus = rule.get('ac_bonus', 0)
    bonus_dice = rule.get('bonus_dice')
    concentration = rule.get('requires_concentration', False)
    description = rule.get('description', '')

    applied = target.add_buff(
        name=buff_name,
        caster_id=caster.id if caster else None,
        source_spell=spell_name,
        ac_bonus=ac_bonus,
        bonus_dice=bonus_dice,
        concentration=concentration,
        description=description,
    )

    # 5e Upcast scaling for temporary HP and protective buffs
    temp_hp = rule.get('temp_hp', 0)
    slot_lvl = max(1, int(spell_level or 1))

    if buff_name.lower() == 'armor of agathys':
        temp_hp = 5 * slot_lvl
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['armor_of_agathys_damage'] = 5 * slot_lvl
        target.save(update_fields=['feature_uses'])
    elif buff_name.lower() == 'false life':
        import random
        temp_hp = random.randint(1, 4) + 4 + (5 * max(0, slot_lvl - 1))
    elif buff_name.lower() == 'aid':
        hp_boost = 5 + (5 * max(0, slot_lvl - 2))
        target.max_hp = (target.max_hp or 0) + hp_boost
        target.current_hp = min(target.max_hp, (target.current_hp or 0) + hp_boost)
        target.save(update_fields=['max_hp', 'current_hp'])

    if temp_hp > 0:
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        current_temp = target.feature_uses.get('temp_hp', 0)
        if current_temp < temp_hp:
            target.feature_uses['temp_hp'] = temp_hp
            target.save(update_fields=['feature_uses'])
            if getattr(target, 'character', None) and hasattr(target.character, 'stats'):
                target.character.stats.temp_hp = max(getattr(target.character.stats, 'temp_hp', 0), temp_hp)
                target.character.stats.save(update_fields=['temp_hp'])

    # Special handling for Shield spell reaction / flag
    if buff_name.lower() == 'shield':
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['shield_spell_active'] = True
        target.save(update_fields=['feature_uses'])

    # Special handling for Mirror Image duplicate tracking
    if buff_name.lower() == 'mirror image':
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['mirror_image_count'] = rule.get('duplicates', 3)
        target.save(update_fields=['feature_uses'])

    # Special handling for Haste spell extra action
    if buff_name.lower() == 'haste':
        target.attacks_remaining = (target.attacks_remaining or 0) + 1
        target.action_used = False
        target.save(update_fields=['attacks_remaining', 'action_used'])

    # If the buff also applies a condition (e.g. Invisibility -> invisible)
    cond_name = rule.get('condition')
    if cond_name:
        try:
            from bestiary.models import Condition
            cond_obj = Condition.objects.filter(name=cond_name).first()
            if cond_obj:
                target.conditions.add(cond_obj)
        except Exception:
            pass

    return applied


def remove_caster_concentration_buffs(caster):
    """
    When a caster's concentration ends or is broken, remove all concentration
    buffs originating from this caster across the entire combat session.
    """
    if not caster or not caster.combat_session:
        return []
    
    removed_from = []
    try:
        participants = caster.combat_session.participants.all()
        for p in participants:
            if hasattr(p, 'remove_buffs_by_caster'):
                had_buffs = bool((p.feature_uses or {}).get('active_buffs'))
                p.remove_buffs_by_caster(caster.id)
                has_buffs_now = bool((p.feature_uses or {}).get('active_buffs'))
                if had_buffs and not has_buffs_now:
                    removed_from.append(p)
    except Exception:
        pass
    return removed_from

