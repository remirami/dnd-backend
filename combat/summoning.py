"""
SRD 5.2 5e / SRD 5.2 Summoning & Persistent Minion / Token Spells Engine

Supports:
- Persistent Spell Objects:
    * Spiritual Weapon (2nd level Evocation, bonus action attack/move, force damage)
    * Flaming Sphere (2nd level Conjuration, concentration, 2d6 fire DEX save ram/adjacent burn)
- Minion Summons:
    * Animate Dead (3rd level Necromancy, Skeleton/Zombie minion)
    * Find Familiar (1st level Conjuration, Owl/Cat/Bat/Raven helper)
    * Conjure Elemental (5th level Conjuration, Fire/Earth/Water/Air Elemental)
    * Conjure Minor Elementals / Conjure Fey / Conjure Animals (CR beasts & fey)
"""

import math
import random
import re
from bestiary.models import Condition
from combat.models import CombatAction, CombatParticipant
from combat.utils import calculate_damage, roll_d20


SUMMONABLE_SPELLS = {
    'spiritual weapon': {
        'spell_type': 'spell_object',
        'name': 'Spiritual Weapon',
        'range': 60,
        'speed': 20,
        'duration_rounds': 10,  # 1 minute
        'requires_concentration': False,
        'default_hp': 999,
        'default_ac': 999,
        'attack_type': 'melee_spell',
        'reach': 5,
        'damage_formula': '1d8',
        'damage_type': 'force',
        'is_bonus_action_command': True,
        'description': 'A floating, spectral weapon of faith that attacks with a bonus action dealing 1d8 + spellcasting mod force damage.',
    },
    'flaming sphere': {
        'spell_type': 'spell_object',
        'name': 'Flaming Sphere',
        'range': 60,
        'speed': 30,
        'duration_rounds': 10,  # 1 minute
        'requires_concentration': True,
        'default_hp': 999,
        'default_ac': 999,
        'damage_formula': '2d6',
        'damage_type': 'fire',
        'save_type': 'DEX',
        'half_on_save': True,
        'is_bonus_action_command': True,
        'description': 'A 5-ft sphere of fire that rams targets (2d6 fire, DEX save) and burns creatures ending their turn adjacent.',
    },
    'animate dead': {
        'spell_type': 'minion',
        'name': 'Animate Dead',
        'range': 10,
        'duration_rounds': 14400,  # 24 hours
        'requires_concentration': False,
        'default_creature': 'skeleton',
        'is_bonus_action_command': True,
        'choices': {
            'skeleton': {
                'name': 'Skeleton',
                'hp': 13,
                'ac': 13,
                'speed': 30,
                'creature_type': 'undead',
                'attacks': [
                    {'name': 'Shortsword', 'bonus': 4, 'damage': '1d6+2', 'damage_type': 'piercing', 'range': 5},
                    {'name': 'Shortbow', 'bonus': 4, 'damage': '1d6+2', 'damage_type': 'piercing', 'range': 80},
                ],
            },
            'zombie': {
                'name': 'Zombie',
                'hp': 22,
                'ac': 8,
                'speed': 20,
                'creature_type': 'undead',
                'undead_fortitude': True,
                'attacks': [
                    {'name': 'Slam', 'bonus': 3, 'damage': '1d6+1', 'damage_type': 'bludgeoning', 'range': 5},
                ],
            },
        },
    },
    'find familiar': {
        'spell_type': 'minion',
        'name': 'Find Familiar',
        'range': 10,
        'duration_rounds': 14400,
        'requires_concentration': False,
        'default_creature': 'owl',
        'is_bonus_action_command': False,
        'choices': {
            'owl': {
                'name': 'Familiar (Owl)',
                'hp': 1,
                'ac': 11,
                'speed': 60,
                'can_fly': True,
                'flyby': True,
                'creature_type': 'celestial',
            },
            'cat': {
                'name': 'Familiar (Cat)',
                'hp': 2,
                'ac': 12,
                'speed': 40,
                'creature_type': 'fey',
            },
            'bat': {
                'name': 'Familiar (Bat)',
                'hp': 1,
                'ac': 12,
                'speed': 30,
                'can_fly': True,
                'creature_type': 'fiend',
            },
            'raven': {
                'name': 'Familiar (Raven)',
                'hp': 1,
                'ac': 12,
                'speed': 50,
                'can_fly': True,
                'creature_type': 'fey',
            },
        },
    },
    'conjure elemental': {
        'spell_type': 'minion',
        'name': 'Conjure Elemental',
        'range': 90,
        'duration_rounds': 10,  # 1 hour
        'requires_concentration': True,
        'default_creature': 'fire elemental',
        'is_bonus_action_command': True,
        'choices': {
            'fire elemental': {
                'name': 'Fire Elemental',
                'hp': 102,
                'ac': 13,
                'speed': 50,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Touch', 'bonus': 6, 'damage': '2d6+3', 'damage_type': 'fire', 'range': 5},
                ],
            },
            'earth elemental': {
                'name': 'Earth Elemental',
                'hp': 126,
                'ac': 17,
                'speed': 30,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Slam', 'bonus': 8, 'damage': '2d8+5', 'damage_type': 'bludgeoning', 'range': 5},
                ],
            },
            'water elemental': {
                'name': 'Water Elemental',
                'hp': 114,
                'ac': 14,
                'speed': 30,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Slam', 'bonus': 7, 'damage': '2d8+4', 'damage_type': 'bludgeoning', 'range': 5},
                ],
            },
            'air elemental': {
                'name': 'Air Elemental',
                'hp': 90,
                'ac': 15,
                'speed': 90,
                'can_fly': True,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Slam', 'bonus': 8, 'damage': '2d8+5', 'damage_type': 'bludgeoning', 'range': 5},
                ],
            },
        },
    },
    'conjure minor elementals': {
        'spell_type': 'minion',
        'name': 'Conjure Minor Elementals',
        'range': 90,
        'duration_rounds': 10,
        'requires_concentration': True,
        'default_creature': 'steam mephit',
        'is_bonus_action_command': True,
        'choices': {
            'steam mephit': {
                'name': 'Steam Mephit',
                'hp': 21,
                'ac': 10,
                'speed': 30,
                'can_fly': True,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Claws', 'bonus': 2, 'damage': '1d4', 'damage_type': 'slashing', 'range': 5},
                ],
            },
            'magma mephit': {
                'name': 'Magma Mephit',
                'hp': 22,
                'ac': 11,
                'speed': 30,
                'can_fly': True,
                'creature_type': 'elemental',
                'attacks': [
                    {'name': 'Claws', 'bonus': 3, 'damage': '1d4+1', 'damage_type': 'slashing', 'range': 5},
                ],
            },
        },
    },
    'conjure fey': {
        'spell_type': 'minion',
        'name': 'Conjure Fey',
        'range': 90,
        'duration_rounds': 10,
        'requires_concentration': True,
        'default_creature': 'dryad',
        'is_bonus_action_command': True,
        'choices': {
            'dryad': {
                'name': 'Dryad',
                'hp': 22,
                'ac': 11,
                'speed': 30,
                'creature_type': 'fey',
                'attacks': [
                    {'name': 'Club', 'bonus': 2, 'damage': '1d4', 'damage_type': 'bludgeoning', 'range': 5},
                ],
            },
            'pixie': {
                'name': 'Pixie',
                'hp': 1,
                'ac': 15,
                'speed': 30,
                'can_fly': True,
                'creature_type': 'fey',
                'attacks': [],
            },
        },
    },
    'conjure animals': {
        'spell_type': 'minion',
        'name': 'Conjure Animals',
        'range': 60,
        'duration_rounds': 10,
        'requires_concentration': True,
        'default_creature': 'dire wolf',
        'is_bonus_action_command': True,
        'choices': {
            'dire wolf': {
                'name': 'Dire Wolf',
                'hp': 37,
                'ac': 14,
                'speed': 50,
                'creature_type': 'beast',
                'attacks': [
                    {'name': 'Bite', 'bonus': 5, 'damage': '2d6+3', 'damage_type': 'piercing', 'range': 5, 'prone_dc': 13},
                ],
            },
            'brown bear': {
                'name': 'Brown Bear',
                'hp': 34,
                'ac': 11,
                'speed': 40,
                'creature_type': 'beast',
                'attacks': [
                    {'name': 'Bite', 'bonus': 5, 'damage': '1d8+4', 'damage_type': 'piercing', 'range': 5},
                    {'name': 'Claws', 'bonus': 5, 'damage': '2d6+4', 'damage_type': 'slashing', 'range': 5},
                ],
            },
        },
    },
}


def is_summoning_spell(spell_name: str) -> bool:
    """Return True if spell name matches a recognized summoning or persistent minion/token spell."""
    if not spell_name:
        return False
    return spell_name.strip().lower() in SUMMONABLE_SPELLS


def get_summon_definition(spell_name: str) -> dict:
    """Retrieve the summon configuration dictionary for a spell."""
    if not spell_name:
        return {}
    return SUMMONABLE_SPELLS.get(spell_name.strip().lower(), {})


def spawn_summon(session, caster, spell_name: str, position_x=None, position_y=None, creature_choice=None, spell_level=None) -> CombatParticipant:
    """
    Spawns a summoned minion or persistent spell object on the combat grid.
    Registers the entity as a CombatParticipant linked to the caster.
    """
    clean_name = spell_name.strip().lower()
    spell_def = SUMMONABLE_SPELLS.get(clean_name)
    if not spell_def:
        raise ValueError(f"Unknown summoning spell: {spell_name}")

    spell_type = spell_def['spell_type']
    duration_rounds = spell_def.get('duration_rounds', 10)
    requires_concentration = spell_def.get('requires_concentration', False)

    # Resolve position (clamp to battlefield grid [0, 45] x [0, 35])
    caster_x = caster.position_x if caster.position_x is not None else 10
    caster_y = caster.position_y if caster.position_y is not None else 10

    if position_x is None:
        target_x = max(0, min(45, caster_x + 5))
    else:
        target_x = max(0, min(45, int(position_x)))

    if position_y is None:
        target_y = max(0, min(35, caster_y))
    else:
        target_y = max(0, min(35, int(position_y)))

    # Determine stats and token identity
    attacks = []
    can_fly = False
    speed = spell_def.get('speed', 30)

    if spell_type == 'spell_object':
        token_name = f"{spell_def['name']} ({caster.get_name()})"
        hp = spell_def['default_hp']
        ac = spell_def['default_ac']
        speed = spell_def.get('speed', 20)
    else:
        choices = spell_def.get('choices', {})
        choice_key = (creature_choice or spell_def.get('default_creature', '')).strip().lower()
        if choice_key not in choices and choices:
            choice_key = list(choices.keys())[0]

        creature_info = choices.get(choice_key, {})
        base_name = creature_info.get('name', 'Summoned Minion')
        token_name = f"{base_name} ({caster.get_name()})"
        hp = creature_info.get('hp', 10)
        ac = creature_info.get('ac', 10)
        speed = creature_info.get('speed', 30)
        can_fly = creature_info.get('can_fly', False)
        attacks = creature_info.get('attacks', [])

    # Calculate upcasting bonuses
    base_level = 2 if clean_name in ('spiritual weapon', 'flaming sphere') else (3 if clean_name == 'animate dead' else (5 if 'elemental' in clean_name else 1))
    cast_lvl = int(spell_level) if spell_level else base_level
    upcast_levels = max(0, cast_lvl - base_level)

    # Upcasting damage calculations
    damage_formula = spell_def.get('damage_formula', '1d8')
    if clean_name == 'spiritual weapon' and upcast_levels >= 2:
        extra_dice = upcast_levels // 2
        damage_formula = f"{1 + extra_dice}d8"
    elif clean_name == 'flaming sphere' and upcast_levels >= 1:
        damage_formula = f"{2 + upcast_levels}d6"

    # Initiative: Acts immediately after caster (or caster.initiative - 0.1)
    init_val = max(1, int(caster.initiative) - 1) if caster.initiative else 10

    # Build feature_uses dictionary
    feature_uses = {
        'is_summon': True,
        'summon_type': spell_type,
        'summoned_by': caster.id,
        'caster_id': caster.id,
        'caster_name': caster.get_name(),
        'spell_name': spell_def['name'],
        'spell_level': cast_lvl,
        'duration_rounds': duration_rounds,
        'remaining_rounds': duration_rounds,
        'requires_concentration': requires_concentration,
        'speed': speed,
        'attacks': attacks,
        'damage_formula': damage_formula,
        'damage_type': spell_def.get('damage_type', 'force'),
        'is_bonus_action_command': spell_def.get('is_bonus_action_command', True),
        'creature_type': spell_def.get('creature_type', 'construct' if spell_type == 'spell_object' else 'beast'),
    }

    summon_participant = CombatParticipant.objects.create(
        combat_session=session,
        participant_type=caster.participant_type,  # Ally of caster
        character=None,
        encounter_enemy=None,
        name=token_name,
        initiative=init_val,
        current_hp=hp,
        max_hp=hp,
        armor_class=ac,
        position_x=target_x,
        position_y=target_y,
        is_active=True,
        feature_uses=feature_uses,
    )

    if requires_concentration:
        caster.is_concentrating = True
        caster.concentration_spell = spell_def['name']
        caster.save(update_fields=['is_concentrating', 'concentration_spell'])

    # Create combat action log entry
    desc = f"✨ {caster.get_name()} summons {summon_participant.get_name()} at ({target_x} ft, {target_y} ft) using {spell_def['name']}."
    CombatAction.objects.create(
        combat_session=session,
        actor=caster,
        target=summon_participant,
        action_type='spell',
        attack_name=spell_def['name'],
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=desc,
    )

    return summon_participant


def command_summon_action(session, caster, summon: CombatParticipant, command_type: str, target: CombatParticipant = None, dest_x=None, dest_y=None, attack_index: int = 0, manual_roll=None, is_dm_override: bool = False) -> dict:
    """
    Executes a player command to move, attack, or trigger an ability on a summoned minion or spell object.
    Consumes the caster's Bonus Action (or Action if free command).
    """
    if not summon or not summon.is_active:
        return {'success': False, 'error': "Summon is inactive or not found."}

    feat_uses = summon.feature_uses or {}
    summoner_id = feat_uses.get('summoned_by') or feat_uses.get('caster_id')
    if not is_dm_override and summoner_id != caster.id:
        return {'success': False, 'error': f"{caster.get_name()} does not control this summon."}

    if not caster.is_active or caster.current_hp <= 0:
        return {'success': False, 'error': f"{caster.get_name()} is unconscious or defeated and cannot command summons."}

    if caster.is_incapacitated():
        return {'success': False, 'error': f"{caster.get_name()} is {caster.get_incapacitating_condition()} and cannot take actions."}

    current = session.get_current_participant()
    if not is_dm_override and current != caster:
        return {'success': False, 'error': f"It is not {caster.get_name()}'s turn."}

    is_ba = feat_uses.get('is_bonus_action_command', True)
    if is_ba and not is_dm_override:
        if caster.bonus_action_used:
            return {'success': False, 'error': f"{caster.get_name()} has already used their bonus action this turn."}

    clean_cmd = (command_type or '').strip().lower()
    spell_name = feat_uses.get('spell_name', 'Summon')
    summon_speed = feat_uses.get('speed', 30)

    # 1. DISMISS COMMAND
    if clean_cmd == 'dismiss':
        summon.is_active = False
        summon.current_hp = 0
        summon.save(update_fields=['is_active', 'current_hp'])

        if feat_uses.get('requires_concentration') and caster.is_concentrating and caster.concentration_spell.lower() == spell_name.lower():
            caster.is_concentrating = False
            caster.concentration_spell = ""
            caster.save(update_fields=['is_concentrating', 'concentration_spell'])

        if is_ba and not is_dm_override:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])

        desc = f"✨ {caster.get_name()} dismisses {summon.get_name()}."
        CombatAction.objects.create(
            combat_session=session,
            actor=caster,
            target=summon,
            action_type='special',
            attack_name='Dismiss Summon',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {'success': True, 'message': desc}

    # 2. MOVE COMMAND
    if clean_cmd == 'move':
        if dest_x is None or dest_y is None:
            return {'success': False, 'error': "Destination coordinates (dest_x, dest_y) are required to move."}

        nx = max(0, min(45, int(dest_x)))
        ny = max(0, min(35, int(dest_y)))

        cur_x = summon.position_x or 0
        cur_y = summon.position_y or 0
        dist = max(abs(nx - cur_x), abs(ny - cur_y))

        if dist > summon_speed:
            return {'success': False, 'error': f"{summon.get_name()} can only move up to {summon_speed} ft (attempted {dist} ft)."}

        summon.position_x = nx
        summon.position_y = ny
        summon.save(update_fields=['position_x', 'position_y'])

        if is_ba and not is_dm_override:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])

        desc = f"🏃 {caster.get_name()} commands {summon.get_name()} to move {dist} ft to ({nx} ft, {ny} ft)."
        CombatAction.objects.create(
            combat_session=session,
            actor=caster,
            target=summon,
            action_type='move',
            attack_name='Command Move',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {'success': True, 'message': desc, 'distance': dist, 'position': [nx, ny]}

    # 3. ATTACK COMMAND (e.g. Spiritual Weapon or Minion)
    if clean_cmd in ('attack', 'strike'):
        if not target:
            return {'success': False, 'error': "A target is required for an attack command."}
        if target.is_dead():
            return {'success': False, 'error': f"{target.get_name()} is dead and cannot be attacked."}

        # Check distance between summon and target
        dist = summon.get_distance_to(target)

        # Spiritual Weapon melee spell attack
        if 'spiritual weapon' in spell_name.lower():
            if dist > 5:
                return {'success': False, 'error': f"Spiritual Weapon must be within 5 ft of {target.get_name()} to attack (currently {dist} ft away). Move it closer first!"}

            # Spell attack roll: d20 + caster's spellcasting mod + proficiency
            ability = 'WIS'
            if caster.character and caster.character.character_class:
                primary = getattr(caster.character.character_class, 'primary_ability', 'WIS')
                if primary in ('INT', 'WIS', 'CHA'):
                    ability = primary
            ability_mod = caster.get_ability_modifier(ability)
            prof = caster.character.proficiency_bonus if (caster.character and caster.character.proficiency_bonus) else 2
            spell_atk_bonus = ability_mod + prof

            if manual_roll is not None:
                try:
                    d20 = int(manual_roll)
                except (ValueError, TypeError):
                    d20, _ = roll_d20()
            else:
                d20, _ = roll_d20()

            is_crit = (d20 == 20)
            is_fumble = (d20 == 1)
            total_atk = d20 + spell_atk_bonus
            effective_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else target.armor_class

            hit = (is_crit or (total_atk >= effective_ac)) and not is_fumble
            damage_str = feat_uses.get('damage_formula', '1d8')

            if hit:
                # Upcasting or standard dice roll
                dmg_val, _ = calculate_damage(damage_str, ability_mod, is_crit)
                dmg_val = max(1, dmg_val)
                target.take_damage(dmg_val, damage_type='force', is_critical=is_crit)
                desc = (
                    f"⚔️ {caster.get_name()}'s Spiritual Weapon strikes {target.get_name()}! "
                    f"(Attack: {d20}+{spell_atk_bonus} = {total_atk} vs AC {effective_ac}) - HIT! "
                    f"Deals {dmg_val} force damage."
                )
            else:
                dmg_val = 0
                desc = (
                    f"⚔️ {caster.get_name()}'s Spiritual Weapon attacks {target.get_name()} "
                    f"(Attack: {d20}+{spell_atk_bonus} = {total_atk} vs AC {effective_ac}) - MISSED."
                )

            if is_ba and not is_dm_override:
                caster.bonus_action_used = True
                caster.save(update_fields=['bonus_action_used'])

            CombatAction.objects.create(
                combat_session=session,
                actor=summon,
                target=target,
                action_type='attack',
                attack_name='Spiritual Weapon Strike',
                attack_roll=d20,
                attack_total=total_atk,
                damage_amount=dmg_val if hit else 0,
                hit=hit,
                critical=is_crit,
                round_number=session.current_round,
                turn_number=session.current_turn_index,
                description=desc,
            )
            return {'success': True, 'hit': hit, 'damage': dmg_val, 'message': desc}

        # Minion creature attack (Skeleton, Zombie, Elemental, Dire Wolf)
        attacks = feat_uses.get('attacks', [])
        if not attacks:
            return {'success': False, 'error': f"{summon.get_name()} has no attacks configured."}

        atk_idx = min(len(attacks) - 1, max(0, int(attack_index)))
        atk_data = attacks[atk_idx]
        atk_reach = atk_data.get('range', 5)

        if dist > atk_reach:
            return {'success': False, 'error': f"{summon.get_name()} is {dist} ft away from {target.get_name()} (reach/range is {atk_reach} ft)."}

        atk_bonus = atk_data.get('bonus', 4)
        if manual_roll is not None:
            try:
                d20 = int(manual_roll)
            except (ValueError, TypeError):
                d20, _ = roll_d20()
        else:
            d20, _ = roll_d20()

        is_crit = (d20 == 20)
        is_fumble = (d20 == 1)
        total_atk = d20 + atk_bonus
        effective_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else target.armor_class

        hit = (is_crit or (total_atk >= effective_ac)) and not is_fumble
        if hit:
            dmg_formula = atk_data.get('damage', '1d6+2')
            dtype = atk_data.get('damage_type', 'piercing')
            m_parts = re.match(r'(\d+d\d+)(?:([+-]\d+))?', dmg_formula.replace(" ", ""))
            dice_part = m_parts.group(1) if m_parts else '1d6'
            flat_part = int(m_parts.group(2)) if m_parts and m_parts.group(2) else 0

            dmg_val, _ = calculate_damage(dice_part, flat_part, is_crit)
            dmg_val = max(1, dmg_val)
            target.take_damage(dmg_val, damage_type=dtype, is_critical=is_crit)

            effect_str = ""
            prone_dc = atk_data.get('prone_dc')
            if prone_dc and not target.has_condition('prone'):
                target_str_mod = target.get_ability_modifier('STR')
                t_roll, _ = roll_d20()
                if (t_roll + target_str_mod) < prone_dc:
                    prone_cond, _ = Condition.objects.get_or_create(name='Prone')
                    target.conditions.add(prone_cond)
                    effect_str = f" [Knocked Prone! (DC {prone_dc} STR save failed)]"

            desc = (
                f"⚔️ {summon.get_name()} attacks {target.get_name()} with {atk_data.get('name', 'Attack')}! "
                f"(Attack: {d20}+{atk_bonus} = {total_atk} vs AC {effective_ac}) - HIT! "
                f"Deals {dmg_val} {dtype} damage.{effect_str}"
            )
        else:
            dmg_val = 0
            desc = (
                f"⚔️ {summon.get_name()} attacks {target.get_name()} with {atk_data.get('name', 'Attack')} "
                f"(Attack: {d20}+{atk_bonus} = {total_atk} vs AC {effective_ac}) - MISSED."
            )

        if is_ba and not is_dm_override:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])

        CombatAction.objects.create(
            combat_session=session,
            actor=summon,
            target=target,
            action_type='attack',
            attack_name=atk_data.get('name', 'Attack'),
            attack_roll=d20,
            attack_total=total_atk,
            damage_amount=dmg_val if hit else 0,
            hit=hit,
            critical=is_crit,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {'success': True, 'hit': hit, 'damage': dmg_val, 'message': desc}

    # 4. RAM / BURN COMMAND (Flaming Sphere)
    if clean_cmd in ('ram', 'burn'):
        if not target:
            return {'success': False, 'error': "A target is required for the Flaming Sphere ram command."}
        if target.is_dead():
            return {'success': False, 'error': f"{target.get_name()} is dead and cannot be rammed."}

        # Check distance between sphere and target (sphere can move up to 30 ft during ram)
        dist = summon.get_distance_to(target)
        if dist > summon_speed:
            return {'success': False, 'error': f"Flaming Sphere can only move up to {summon_speed} ft to ram (target is {dist} ft away)."}

        # Move sphere adjacent to target
        summon.position_x = target.position_x
        summon.position_y = target.position_y
        summon.save(update_fields=['position_x', 'position_y'])

        # Calculate Spell Save DC
        ability = 'WIS'
        if caster.character and caster.character.character_class:
            primary = getattr(caster.character.character_class, 'primary_ability', 'WIS')
            if primary in ('INT', 'WIS', 'CHA'):
                ability = primary
        ability_mod = caster.get_ability_modifier(ability)
        prof = caster.character.proficiency_bonus if (caster.character and caster.character.proficiency_bonus) else 2
        save_dc = 8 + ability_mod + prof

        # Target DEX Save
        dex_mod = target.get_ability_modifier('DEX')
        save_roll, _ = roll_d20()
        save_total = save_roll + dex_mod
        saved = (save_total >= save_dc)

        dmg_formula = feat_uses.get('damage_formula', '2d6')
        raw_damage, _ = calculate_damage(dmg_formula, 0, False)
        final_damage = (raw_damage // 2) if saved else raw_damage
        final_damage = max(1, final_damage)

        target.take_damage(final_damage, damage_type='fire')

        save_status = f"Saved (half damage) ({save_roll}+{dex_mod} = {save_total} vs DC {save_dc})" if saved else f"Failed Save ({save_roll}+{dex_mod} = {save_total} vs DC {save_dc})"
        desc = (
            f"☄️ {caster.get_name()} rams Flaming Sphere into {target.get_name()}! "
            f"DEX Save: {save_status}. Deals {final_damage} fire damage."
        )

        if is_ba and not is_dm_override:
            caster.bonus_action_used = True
            caster.save(update_fields=['bonus_action_used'])

        CombatAction.objects.create(
            combat_session=session,
            actor=summon,
            target=target,
            action_type='spell',
            attack_name='Flaming Sphere Ram',
            damage_amount=final_damage,
            save_type='DEX',
            save_dc=save_dc,
            save_roll=save_roll,
            save_success=saved,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {'success': True, 'saved': saved, 'damage': final_damage, 'message': desc}

    # 5. HELP COMMAND (Familiar)
    if clean_cmd == 'help':
        if not target:
            return {'success': False, 'error': "A target is required for the Help command."}

        # Familiar moves adjacent to target and distracts it
        summon.position_x = target.position_x
        summon.position_y = target.position_y
        summon.save(update_fields=['position_x', 'position_y'])

        # Mark target as distracted by familiar (granting advantage to next attack)
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['distracted_by_familiar'] = True
        target.save(update_fields=['feature_uses'])

        desc = f"🦉 {summon.get_name()} flits around {target.get_name()}, distracting them! The next attack against {target.get_name()} has Advantage."
        CombatAction.objects.create(
            combat_session=session,
            actor=summon,
            target=target,
            action_type='special',
            attack_name='Help Action',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=desc,
        )
        return {'success': True, 'message': desc}

    return {'success': False, 'error': f"Unknown command type: {command_type}"}


def dismiss_concentration_summons_by_caster(caster):
    """Dismisses any active summoned creatures or persistent tokens requiring concentration from this caster."""
    if not caster or not caster.combat_session_id:
        return
    summons = caster.combat_session.participants.filter(
        is_active=True
    ).exclude(id=caster.id)

    for p in summons:
        fu = p.feature_uses or {}
        if fu.get('is_summon') and fu.get('requires_concentration'):
            if fu.get('summoned_by') == caster.id or fu.get('caster_id') == caster.id:
                p.is_active = False
                p.current_hp = 0
                p.save(update_fields=['is_active', 'current_hp'])
                CombatAction.objects.create(
                    combat_session=caster.combat_session,
                    actor=caster,
                    target=p,
                    action_type='special',
                    attack_name='Dismiss Concentration Summon',
                    round_number=caster.combat_session.current_round,
                    turn_number=caster.combat_session.current_turn_index,
                    description=f"✨ Concentration ended: {p.get_name()} vanished from the battlefield.",
                )


def decrement_summon_durations(session):
    """
    Decrements duration on all active summons in the session at the start of each round.
    If remaining_rounds <= 0, summon expires and is marked inactive.
    """
    for p in session.participants.filter(is_active=True):
        fu = p.feature_uses or {}
        if fu.get('is_summon'):
            rem = fu.get('remaining_rounds', 10) - 1
            fu['remaining_rounds'] = rem
            if rem <= 0:
                p.is_active = False
                p.current_hp = 0
                p.save(update_fields=['is_active', 'current_hp', 'feature_uses'])
                CombatAction.objects.create(
                    combat_session=session,
                    actor=p,
                    action_type='special',
                    attack_name='Summon Expired',
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=f"⏳ {p.get_name()} duration has expired and it vanished from combat.",
                )
            else:
                p.save(update_fields=['feature_uses'])
