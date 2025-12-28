"""
Condition Auto-Application and Effects System

Handles automatic condition application from spells/abilities and condition effects on stats.
"""

from bestiary.models import Condition


# Mapping of spells/abilities to conditions they apply
SPELL_CONDITION_MAP = {
    # Spells
    'Hold Person': 'paralyzed',
    'Hold Monster': 'paralyzed',
    'Sleep': 'unconscious',
    'Charm Person': 'charmed',
    'Charm Monster': 'charmed',
    'Frightful Presence': 'frightened',
    'Cause Fear': 'frightened',
    'Blindness/Deafness': 'blinded',
    'Blind': 'blinded',
    'Deaf': 'deafened',
    'Stunning Strike': 'stunned',
    'Stun': 'stunned',
    'Poison Spray': 'poisoned',
    'Poison': 'poisoned',
    'Ray of Enfeeblement': 'poisoned',
    'Grapple': 'grappled',
    'Restrain': 'restrained',
    'Prone': 'prone',
    'Invisibility': 'invisible',
    'Petrify': 'petrified',
    'Flesh to Stone': 'petrified',
    'Exhaustion': 'exhaustion',
    
    # Abilities
    'Uncanny Dodge': None,  # No condition, just damage reduction
    'Evasion': None,
    'Cunning Action': None,
}


# Condition effects on stats and abilities
CONDITION_EFFECTS = {
    'blinded': {
        'description': 'Cannot see and automatically fails any ability check that requires sight',
        'attack_disadvantage': True,
        'attack_advantage_against': True,  # Attacks against blinded creature have advantage
        'sight_checks_fail': True,
    },
    'charmed': {
        'description': 'Cannot attack the charmer or target the charmer with harmful abilities',
        'cannot_attack_charmer': True,
    },
    'deafened': {
        'description': 'Cannot hear and automatically fails any ability check that requires hearing',
        'hearing_checks_fail': True,
    },
    'frightened': {
        'description': 'Has disadvantage on ability checks and attack rolls while source is in line of sight',
        'ability_check_disadvantage': True,
        'attack_disadvantage': True,
        'cannot_move_closer': True,
    },
    'grappled': {
        'description': 'Speed becomes 0, cannot benefit from any bonus to speed',
        'speed': 0,
        'speed_bonus_ignored': True,
    },
    'incapacitated': {
        'description': 'Cannot take actions or reactions',
        'cannot_take_actions': True,
        'cannot_take_reactions': True,
    },
    'invisible': {
        'description': 'Cannot be seen without special senses',
        'attack_advantage': True,
        'attack_disadvantage_against': True,  # Attacks against invisible creature have disadvantage
    },
    'paralyzed': {
        'description': 'Cannot move or speak, automatically fails STR/DEX saves, attacks against have advantage',
        'speed': 0,
        'cannot_take_actions': True,
        'str_dex_saves_fail': True,
        'attack_advantage_against': True,
        'critical_hit_on_melee': True,
    },
    'petrified': {
        'description': 'Turned to stone, weight increases, cannot move or speak, resistant to all damage',
        'speed': 0,
        'cannot_take_actions': True,
        'damage_resistance': 'all',
        'attack_advantage_against': True,
    },
    'poisoned': {
        'description': 'Has disadvantage on attack rolls and ability checks',
        'attack_disadvantage': True,
        'ability_check_disadvantage': True,
    },
    'prone': {
        'description': 'Melee attacks have advantage, ranged attacks have disadvantage',
        'melee_attack_advantage_against': True,
        'ranged_attack_disadvantage_against': True,
        'standing_up_required': True,
    },
    'restrained': {
        'description': 'Speed becomes 0, attack rolls have disadvantage, attacks against have advantage',
        'speed': 0,
        'attack_disadvantage': True,
        'attack_advantage_against': True,
    },
    'stunned': {
        'description': 'Cannot take actions or reactions, automatically fails STR/DEX saves, attacks against have advantage',
        'cannot_take_actions': True,
        'cannot_take_reactions': True,
        'str_dex_saves_fail': True,
        'attack_advantage_against': True,
    },
    'unconscious': {
        'description': 'Cannot move or speak, automatically fails STR/DEX saves, attacks against have advantage, critical hit on melee',
        'speed': 0,
        'cannot_take_actions': True,
        'str_dex_saves_fail': True,
        'attack_advantage_against': True,
        'critical_hit_on_melee': True,
    },
    'exhaustion': {
        'description': 'Levels of exhaustion have cumulative effects',
        'levels': {
            1: {'ability_check_disadvantage': True},
            2: {'speed_multiplier': 0.5},
            3: {'attack_disadvantage': True, 'save_disadvantage': True},
            4: {'hp_max_multiplier': 0.5},
            5: {'speed': 0},
            6: {'death': True},
        }
    },
}


def get_condition_for_spell(spell_name):
    """Get the condition that a spell applies"""
    return SPELL_CONDITION_MAP.get(spell_name)


def get_condition_effects(condition_name):
    """Get the effects of a condition"""
    return CONDITION_EFFECTS.get(condition_name, {})


def apply_condition_effects(participant, condition_name):
    """
    Apply condition effects to a participant's stats.
    Returns a dict of stat modifications.
    """
    effects = get_condition_effects(condition_name)
    if not effects:
        return {}
    
    modifications = {}
    
    # Speed modifications
    if 'speed' in effects:
        modifications['speed'] = effects['speed']
    elif 'speed_multiplier' in effects:
        base_speed = getattr(participant, 'speed', 30)
        modifications['speed'] = int(base_speed * effects['speed_multiplier'])
    
    # Attack modifications
    if effects.get('attack_disadvantage'):
        modifications['attack_disadvantage'] = True
    if effects.get('attack_advantage'):
        modifications['attack_advantage'] = True
    
    # Ability check modifications
    if effects.get('ability_check_disadvantage'):
        modifications['ability_check_disadvantage'] = True
    
    # Save modifications
    if effects.get('save_disadvantage'):
        modifications['save_disadvantage'] = True
    if effects.get('str_dex_saves_fail'):
        modifications['str_dex_saves_fail'] = True
    
    # Action restrictions
    if effects.get('cannot_take_actions'):
        modifications['cannot_take_actions'] = True
    if effects.get('cannot_take_reactions'):
        modifications['cannot_take_reactions'] = True
    
    return modifications


def auto_apply_condition_from_spell(participant, spell_name):
    """
    Automatically apply condition from a spell.
    Returns the condition if applied, None otherwise.
    """
    condition_name = get_condition_for_spell(spell_name)
    if not condition_name:
        return None
    
    try:
        condition = Condition.objects.get(name=condition_name)
        participant.conditions.add(condition)
        participant.save()
        return condition
    except Condition.DoesNotExist:
        return None


def should_remove_condition(participant, condition_name, reason=''):
    """
    Check if a condition should be removed.
    Reasons: 'end_of_turn', 'end_of_spell', 'saving_throw_success', 'damage_taken'
    """
    # Some conditions are removed on specific triggers
    removal_triggers = {
        'charmed': ['end_of_spell', 'saving_throw_success'],
        'frightened': ['end_of_spell', 'saving_throw_success'],
        'stunned': ['end_of_turn', 'saving_throw_success'],
        'paralyzed': ['end_of_spell', 'saving_throw_success'],
        'unconscious': ['healed', 'damage_taken'],  # Healed = regain HP, damage = death saves
    }
    
    triggers = removal_triggers.get(condition_name, [])
    return reason in triggers


def calculate_effective_speed(participant, base_speed):
    """Calculate effective speed considering conditions"""
    speed = base_speed
    
    # Check for speed-affecting conditions
    if participant.conditions.filter(name='grappled').exists():
        speed = 0
    elif participant.conditions.filter(name='restrained').exists():
        speed = 0
    elif participant.conditions.filter(name='paralyzed').exists():
        speed = 0
    elif participant.conditions.filter(name='unconscious').exists():
        speed = 0
    elif participant.conditions.filter(name='petrified').exists():
        speed = 0
    
    # Exhaustion level 2: half speed
    exhaustion_level = participant.conditions.filter(name='exhaustion').count()
    if exhaustion_level >= 2:
        speed = int(speed * 0.5)
    
    # Exhaustion level 5: speed 0
    if exhaustion_level >= 5:
        speed = 0
    
    return speed


def has_attack_disadvantage(participant):
    """Check if participant has disadvantage on attacks due to conditions"""
    conditions = participant.conditions.all()
    condition_names = [c.name for c in conditions]
    
    disadvantage_conditions = ['blinded', 'frightened', 'poisoned', 'restrained']
    return any(name in condition_names for name in disadvantage_conditions)


def has_attack_advantage_against(participant):
    """Check if attacks against participant have advantage due to conditions"""
    conditions = participant.conditions.all()
    condition_names = [c.name for c in conditions]
    
    advantage_conditions = ['blinded', 'paralyzed', 'prone', 'restrained', 'stunned', 'unconscious']
    return any(name in condition_names for name in advantage_conditions)

