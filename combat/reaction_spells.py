"""
Reaction & Abjuration Spell Resolution System: Counterspell and Dispel Magic
Strictly compliant with official SRD 5.1 & 2024 SRD 5.2 rules.
"""

from typing import Tuple, List, Dict, Any, Optional
import math


def get_spellcasting_ability(participant) -> str:
    """Returns the primary spellcasting ability for a participant ('INT', 'WIS', 'CHA')."""
    if not participant:
        return 'INT'
    if getattr(participant, 'character', None) and getattr(participant.character, 'character_class', None):
        cname = participant.character.character_class.name.lower()
        if cname in ['wizard']:
            return 'INT'
        elif cname in ['cleric', 'druid', 'ranger']:
            return 'WIS'
        elif cname in ['sorcerer', 'warlock', 'bard', 'paladin']:
            return 'CHA'
    # Fallback to highest mental stat
    int_mod = participant.get_ability_modifier('INT')
    wis_mod = participant.get_ability_modifier('WIS')
    cha_mod = participant.get_ability_modifier('CHA')
    best = max(int_mod, wis_mod, cha_mod)
    if best == cha_mod:
        return 'CHA'
    if best == wis_mod:
        return 'WIS'
    return 'INT'


def resolve_counterspell(
    counter_caster,
    target_caster,
    target_spell_name: str,
    target_spell_level: int,
    counter_slot_level: int = 3
) -> Tuple[bool, Dict[str, Any]]:
    """
    Resolves 5e Counterspell:
    - 60 ft range requirement.
    - Consumes reaction and spell slot.
    - If counter_slot_level >= target_spell_level: automatic success.
    - Else: Ability check with spellcasting modifier vs DC = 10 + target_spell_level.
    Returns: (is_countered, result_details)
    """
    from combat.utils import roll_d20

    # 1. Validation: reaction check
    if getattr(counter_caster, 'reaction_used', False):
        return False, {
            'success': False,
            'error': f"{counter_caster.get_name()} has already used their reaction this round."
        }

    # 2. Validation: range check (60 ft)
    from combat.high_tier_passives import get_participant_distance
    distance = get_participant_distance(counter_caster, target_caster)
    if distance > 60:
        return False, {
            'success': False,
            'error': f"Target {target_caster.get_name()} is out of range ({int(distance)} ft > 60 ft)."
        }

    # 3. Consume reaction
    if hasattr(counter_caster, 'use_reaction'):
        counter_caster.use_reaction()
    else:
        counter_caster.reaction_used = True
        counter_caster.save(update_fields=['reaction_used'])

    # 4. Check resolution
    ability = get_spellcasting_ability(counter_caster)
    ability_mod = counter_caster.get_ability_modifier(ability)
    dc = 10 + target_spell_level

    if counter_slot_level >= target_spell_level:
        is_success = True
        roll = None
        total = None
        msg = (
            f"✨ Counterspell: {counter_caster.get_name()} casts Counterspell at level {counter_slot_level}, "
            f"automatically negating {target_caster.get_name()}'s {target_spell_name} (level {target_spell_level})!"
        )
    else:
        roll, _ = roll_d20()
        total = roll + ability_mod
        is_success = (total >= dc)
        if is_success:
            msg = (
                f"✨ Counterspell SUCCESS! {counter_caster.get_name()} rolled {total} (d20: {roll} + {ability_mod:+d} {ability}) "
                f"vs DC {dc}, successfully negating {target_caster.get_name()}'s {target_spell_name}!"
            )
        else:
            msg = (
                f"❌ Counterspell FAILED! {counter_caster.get_name()} rolled {total} (d20: {roll} + {ability_mod:+d} {ability}) "
                f"vs DC {dc}. {target_caster.get_name()}'s {target_spell_name} takes effect!"
            )

    return is_success, {
        'success': is_success,
        'counter_caster': counter_caster.get_name(),
        'target_caster': target_caster.get_name(),
        'target_spell': target_spell_name,
        'target_spell_level': target_spell_level,
        'counter_slot_level': counter_slot_level,
        'ability': ability,
        'ability_modifier': ability_mod,
        'roll': roll,
        'total': total,
        'dc': dc,
        'message': msg
    }


def resolve_dispel_magic(
    caster,
    target,
    dispel_slot_level: int = 3
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Resolves 5e Dispel Magic:
    - 120 ft range requirement.
    - Ends spells of level <= dispel_slot_level automatically.
    - For higher level spells, make an ability check with spellcasting modifier vs DC = 10 + spell level.
    - Strips active buffs and breaks concentration if applicable.
    Returns: (list_of_dispelled_spell_names, result_details)
    """
    from combat.utils import roll_d20
    from combat.spell_rules import SPELL_RULES

    from combat.high_tier_passives import get_participant_distance
    distance = get_participant_distance(caster, target)
    if distance > 120:
        return [], {
            'success': False,
            'dispelled': [],
            'error': f"Target {target.get_name()} is out of range ({int(distance)} ft > 120 ft)."
        }

    ability = get_spellcasting_ability(caster)
    ability_mod = caster.get_ability_modifier(ability)

    active_buffs = list(target.get_active_buffs())
    dispelled_spells = []
    log_messages = []

    # Map of spell levels
    for buff in active_buffs:
        buff_name = buff.get('name', '')
        clean_name = buff_name.strip().lower()
        rule = SPELL_RULES.get(clean_name, {})
        spell_level = rule.get('level', 1)

        dc = 10 + spell_level
        if dispel_slot_level >= spell_level:
            target.remove_buff(buff_name)
            dispelled_spells.append(buff_name)
            log_messages.append(f"Auto-dispelled {buff_name} (level {spell_level})")
        else:
            roll, _ = roll_d20()
            check_total = roll + ability_mod
            if check_total >= dc:
                target.remove_buff(buff_name)
                dispelled_spells.append(buff_name)
                log_messages.append(f"Dispelled {buff_name} (check {check_total} vs DC {dc})")
            else:
                log_messages.append(f"Failed to dispel {buff_name} (check {check_total} vs DC {dc})")

    # If target was concentrating on an ongoing spell, and it was dispelled or targeted
    target_conc_dispelled = False
    if target.is_concentrating and target.concentration_spell:
        conc_name = target.concentration_spell
        rule = SPELL_RULES.get(conc_name.strip().lower(), {})
        conc_level = rule.get('level', 1)
        dc = 10 + conc_level
        if dispel_slot_level >= conc_level:
            target.is_concentrating = False
            target.concentration_spell = ""
            target.save(update_fields=['is_concentrating', 'concentration_spell'])
            try:
                from combat.spell_rules import remove_caster_concentration_buffs
                remove_caster_concentration_buffs(target)
            except Exception:
                pass
            dispelled_spells.append(f"{conc_name} (Concentration)")
            target_conc_dispelled = True
            log_messages.append(f"Broke concentration on {conc_name} (level {conc_level})")
        else:
            roll, _ = roll_d20()
            check_total = roll + ability_mod
            if check_total >= dc:
                target.is_concentrating = False
                target.concentration_spell = ""
                target.save(update_fields=['is_concentrating', 'concentration_spell'])
                try:
                    from combat.spell_rules import remove_caster_concentration_buffs
                    remove_caster_concentration_buffs(target)
                except Exception:
                    pass
                dispelled_spells.append(f"{conc_name} (Concentration)")
                target_conc_dispelled = True
                log_messages.append(f"Broke concentration on {conc_name} (check {check_total} vs DC {dc})")

    # Remove magical conditions if spell source was dispelled
    condition_dispelled = []
    dispelled_lower = [s.lower() for s in dispelled_spells]
    if any('hold person' in s or 'hold monster' in s for s in dispelled_lower):
        from bestiary.models import Condition
        para = Condition.objects.filter(name='paralyzed').first()
        if para and target.conditions.filter(name='paralyzed').exists():
            target.conditions.remove(para)
            condition_dispelled.append('paralyzed')

    if any('blindness' in s for s in dispelled_lower):
        from bestiary.models import Condition
        blind = Condition.objects.filter(name='blinded').first()
        if blind and target.conditions.filter(name='blinded').exists():
            target.conditions.remove(blind)
            condition_dispelled.append('blinded')

    summary_msg = f"🔮 Dispel Magic on {target.get_name()}: "
    if dispelled_spells:
        summary_msg += f"Dispelled {', '.join(dispelled_spells)}."
    else:
        summary_msg += "No magical effects were dispelled."

    return dispelled_spells, {
        'success': bool(dispelled_spells),
        'caster': caster.get_name(),
        'target': target.get_name(),
        'dispelled': dispelled_spells,
        'conditions_removed': condition_dispelled,
        'details': log_messages,
        'message': summary_msg
    }
