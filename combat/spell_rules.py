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
        'range': 'Touch',
        'is_healing': True,
        'no_undead_or_construct': True,
    },
    'healing word': {
        'range': '60 feet',
        'is_healing': True,
        'is_bonus_action': True,
        'no_undead_or_construct': True,
    },
    'inflict wounds': {
        'range': 'Touch',
        'requires_attack_roll': True,
        'attack_type': 'melee_spell',
        'damage_type': 'necrotic',
        'damage': '3d10 necrotic',
    },
    'guiding bolt': {
        'range': '120 feet',
        'requires_attack_roll': True,
        'attack_type': 'ranged_spell',
        'damage_type': 'radiant',
        'damage': '4d6 radiant',
        'grants_next_attack_advantage': True,
    },
    'magic missile': {
        'range': '120 feet',
        'auto_hit': True,
        'damage_type': 'force',
        'dart_count': 3,
        'dart_damage': '1d4+1 force',
    },
    'shield': {
        'range': 'Self',
        'is_reaction': True,
        'ac_bonus': 5,
        'negates_magic_missile': True,
    },
    'mage armor': {
        'range': 'Touch',
        'target_unarmored_only': True,
        'base_ac_override': 13,
    },
    'thunderwave': {
        'range': 'Self (15-foot cube)',
        'save_type': 'CON',
        'half_on_save': True,
        'damage_type': 'thunder',
        'damage': '2d8 thunder',
        'push_distance': 10,
    },
    'burning hands': {
        'range': 'Self (15-foot cone)',
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '3d6 fire',
    },
    'grease': {
        'range': '60 feet (10-foot square)',
        'save_type': 'DEX',
        'condition': 'prone',
        'creates_difficult_terrain': True,
    },
    'fog cloud': {
        'range': '120 feet (20-foot radius)',
        'requires_concentration': True,
        'creates_heavily_obscured': True,
    },

    # Control & Status Spells
    'hold person': {
        'range': '60 feet',
        'save_type': 'WIS',
        'requires_concentration': True,
        'condition': 'paralyzed',
        'humanoid_only': True,
    },
    'sleep': {
        'range': '90 feet',
        'radius': 20,
        'condition': 'unconscious',
        'no_undead_or_immune': True,
    },

    # Mobility & Buffs
    'misty step': {
        'range': 'Self',
        'is_bonus_action': True,
        'teleport_distance': 30,
    },
    'fireball': {
        'range': '150 feet',
        'radius': 20,
        'save_type': 'DEX',
        'half_on_save': True,
        'damage_type': 'fire',
        'damage': '8d6 fire',
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
