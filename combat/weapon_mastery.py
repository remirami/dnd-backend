"""
Weapon Mastery System (D&D 5e 2024 Rules).
Implements the 8 official 2024 Weapon Mastery properties:
- Cleave (Greataxe, Halberd)
- Graze (Glaive, Greatsword)
- Nick (Dagger, Light Hammer, Scimitar, Sickle)
- Push (Greatclub, Heavy Crossbow, Pike, Warhammer)
- Sap (Flail, Mace, Morningstar, War Pick)
- Slow (Club, Javelin, Light Crossbow, Longbow, Musket, Sling, Whip)
- Topple (Battleaxe, Lance, Maul, Quarterstaff, Trident)
- Vex (Blowgun, Dart, Hand Crossbow, Handaxe, Pistol, Rapier, Shortbow, Shortsword)
"""
import math


WEAPON_MASTERY_MAP = {
    'Cleave': ['Greataxe', 'Halberd'],
    'Graze': ['Glaive', 'Greatsword'],
    'Nick': ['Dagger', 'Light Hammer', 'Scimitar', 'Sickle'],
    'Push': ['Greatclub', 'Heavy Crossbow', 'Pike', 'Warhammer'],
    'Sap': ['Flail', 'Mace', 'Morningstar', 'War Pick'],
    'Slow': ['Club', 'Javelin', 'Light Crossbow', 'Longbow', 'Musket', 'Sling', 'Whip'],
    'Topple': ['Battleaxe', 'Lance', 'Maul', 'Quarterstaff', 'Trident'],
    'Vex': ['Blowgun', 'Dart', 'Hand Crossbow', 'Handaxe', 'Pistol', 'Rapier', 'Shortbow', 'Shortsword'],
}

WEAPON_TO_MASTERY = {}
for _prop, _weapons in WEAPON_MASTERY_MAP.items():
    for _w in _weapons:
        WEAPON_TO_MASTERY[_w.lower()] = _prop


def get_weapon_mastery_property(weapon_name: str, weapon_obj=None) -> str:
    """Return the 2024 Weapon Mastery property for a weapon."""
    if weapon_obj and getattr(weapon_obj, 'mastery_property', None):
        return weapon_obj.mastery_property

    if not weapon_name:
        return None

    clean_name = weapon_name.strip().lower()
    if clean_name in WEAPON_TO_MASTERY:
        return WEAPON_TO_MASTERY[clean_name]

    # Partial / substring match (e.g. "+1 Greatsword" or "Silvered Dagger")
    for w_name, prop in WEAPON_TO_MASTERY.items():
        if w_name in clean_name:
            return prop

    return None


def can_use_weapon_mastery(participant, weapon_name: str, weapon_obj=None, property_name: str = None) -> bool:
    """
    Check if a participant can use the mastery property of a weapon.
    Only 2024 rules characters (or participants with explicit mastery features) qualify.
    """
    if not participant:
        return False

    # Check participant feature_uses overrides (for tests, custom mobs, or explicit feats)
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        if participant.feature_uses.get('has_weapon_mastery') or participant.feature_uses.get('weapon_mastery'):
            mastered = participant.feature_uses.get('mastered_weapons')
            if mastered and weapon_name:
                if not any(w.lower() in weapon_name.lower() for w in mastered):
                    return False
            prop = get_weapon_mastery_property(weapon_name, weapon_obj)
            if property_name and prop:
                return prop.lower() == property_name.lower()
            return bool(prop)

    if not participant.character:
        return False

    character = participant.character
    # Weapon Masteries are a 2024 feature
    if getattr(character, 'ruleset_version', '2014') != '2024':
        return False

    # Check if character's class has Weapon Mastery in 2024
    cls_name = getattr(character.character_class, 'name', '').lower()
    mastery_classes = {'fighter', 'barbarian', 'paladin', 'ranger', 'rogue'}
    has_class_feature = cls_name in mastery_classes

    # Check character features/feats
    if not has_class_feature and hasattr(character, 'features'):
        has_class_feature = character.features.filter(name__icontains='Weapon Mastery').exists()

    if not has_class_feature:
        return False

    # Check if the weapon has a mastery property
    prop = get_weapon_mastery_property(weapon_name, weapon_obj)
    if not prop:
        return False

    if property_name and prop.lower() != property_name.lower():
        return False

    # Check mastered weapons list if restricted
    if participant.feature_uses and isinstance(participant.feature_uses, dict):
        mastered = participant.feature_uses.get('mastered_weapons')
        if mastered and weapon_name:
            return any(w.lower() in weapon_name.lower() for w in mastered)

    return True


def apply_mastery_on_hit(
    session,
    attacker,
    target,
    weapon_name: str,
    weapon_obj,
    damage_amount: int,
    damage_type: str,
    attack_total: int,
    ability_mod: int,
    proficiency_bonus: int,
    is_critical: bool = False,
    cleave_target_id: int = None
):
    """
    Resolve on-hit Weapon Mastery properties (Vex, Topple, Push, Sap, Slow, Cleave).
    Returns a dict with mastery event details and annotations.
    """
    if not can_use_weapon_mastery(attacker, weapon_name, weapon_obj):
        return None

    mastery = get_weapon_mastery_property(weapon_name, weapon_obj)
    if not mastery:
        return None

    from bestiary.models import Condition
    from combat.models import CombatAction

    result = {
        'mastery': mastery,
        'description': '',
        'annotation': '',
        'target_pushed': False,
        'target_sapped': False,
        'target_slowed': False,
        'target_toppled': False,
        'vex_applied': False,
        'cleave_action': None,
    }

    if mastery == 'Vex' and damage_amount > 0:
        if not isinstance(attacker.feature_uses, dict):
            attacker.feature_uses = {}
        attacker.feature_uses['vex_target_id'] = target.id
        attacker.save(update_fields=['feature_uses'])
        result['vex_applied'] = True
        result['annotation'] = "🎯 Vex: Advantage granted on next attack vs target!"

    elif mastery == 'Sap':
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['sapped'] = True
        target.save(update_fields=['feature_uses'])
        result['target_sapped'] = True
        result['annotation'] = "😵 Sap: Target has Disadvantage on their next attack!"

    elif mastery == 'Slow' and damage_amount > 0:
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}
        target.feature_uses['slowed_speed_reduction'] = 10
        target.save(update_fields=['feature_uses'])
        result['target_slowed'] = True
        result['annotation'] = "🐢 Slow: Target speed reduced by 10 ft!"

    elif mastery == 'Topple':
        topple_dc = 8 + proficiency_bonus + ability_mod
        con_mod = target.get_ability_modifier('CON')
        from combat.utils import roll_d20
        save_roll, _ = roll_d20(advantage=False, lucky=getattr(target, 'has_lucky_trait', lambda: False)())
        save_total = save_roll + con_mod
        if save_total < topple_dc:
            prone_cond = Condition.objects.filter(name__iexact='Prone').first()
            if prone_cond:
                target.conditions.add(prone_cond)
            result['target_toppled'] = True
            result['annotation'] = f"🤼 Topple: Target knocked PRONE (failed DC {topple_dc} CON save, rolled {save_total})!"
        else:
            result['annotation'] = f"🤼 Topple: Target resisted knock down (saved vs DC {topple_dc}, rolled {save_total})!"

    elif mastery == 'Push':
        # Push target up to 10 ft away if Large or smaller
        target_size = getattr(target, 'size', 'M')
        if hasattr(target, 'character') and target.character:
            target_size = target.character.size
        elif hasattr(target, 'encounter_enemy') and target.encounter_enemy and target.encounter_enemy.enemy:
            target_size = target.encounter_enemy.enemy.size

        if target_size in ['T', 'S', 'M', 'L']:
            dx = (target.position_x or 0) - (attacker.position_x or 0)
            dy = (target.position_y or 0) - (attacker.position_y or 0)
            dist = math.hypot(dx, dy)
            if dist == 0:
                dx, dy, dist = 1, 0, 1
            dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            if abs(dx) > abs(dy) * 1.5:
                step_x, step_y = dir_x * 10, 0
            elif abs(dy) > abs(dx) * 1.5:
                step_x, step_y = 0, dir_y * 10
            else:
                step_x, step_y = dir_x * 10, dir_y * 10

            new_x = max(0, min(45, (target.position_x or 0) + step_x))
            new_y = max(0, min(35, (target.position_y or 0) + step_y))
            occ = session.participants.filter(
                position_x=new_x, position_y=new_y, is_active=True, current_hp__gt=0
            ).exclude(id=target.id).first()
            if not occ and (new_x != target.position_x or new_y != target.position_y):
                target.position_x = new_x
                target.position_y = new_y
                target.save(update_fields=['position_x', 'position_y'])
                result['target_pushed'] = True
                result['annotation'] = f"💨 Push: Target pushed 10 ft away to ({new_x} ft, {new_y} ft)!"

    elif mastery == 'Cleave':
        second_target = None
        if cleave_target_id:
            second_target = session.participants.filter(pk=cleave_target_id, is_active=True, current_hp__gt=0).first()
        else:
            reach = attacker.get_reach() if hasattr(attacker, 'get_reach') else 5
            potentials = session.participants.filter(
                is_active=True, current_hp__gt=0
            ).exclude(id__in=[attacker.id, target.id])
            for p in potentials:
                if p.participant_type != attacker.participant_type:
                    if target.get_distance_to(p) <= 5 and attacker.get_distance_to(p) <= reach:
                        second_target = p
                        break

        if second_target:
            from combat.utils import roll_d20, calculate_attack_roll, calculate_damage
            c_roll, _ = roll_d20(advantage=False, lucky=getattr(attacker, 'has_lucky_trait', lambda: False)())
            c_total, _ = calculate_attack_roll(c_roll, ability_mod, proficiency_bonus, True, 0)
            sec_ac = second_target.calculate_effective_ac()
            if c_total >= sec_ac:
                mod_for_cleave = min(0, ability_mod)
                c_dmg, _ = calculate_damage(getattr(weapon_obj, 'damage_dice', '1d12') if weapon_obj else '1d12', mod_for_cleave, False)
                second_target.take_damage(c_dmg, damage_type=damage_type)
                result['annotation'] = f"⚔️ Cleave: Struck {second_target.get_name()} for {c_dmg} {damage_type or ''} damage (rolled {c_total} vs AC {sec_ac})!"
                cleave_act = CombatAction.objects.create(
                    combat_session=session,
                    actor=attacker,
                    target=second_target,
                    action_type='attack',
                    attack_name=f"{weapon_name} (Cleave)",
                    attack_roll=c_roll,
                    attack_total=c_total,
                    hit=True,
                    damage_amount=c_dmg,
                    round_number=session.current_round,
                    turn_number=session.current_turn_index,
                    description=f"⚔️ Cleave attack struck {second_target.get_name()} for {c_dmg} damage!"
                )
                result['cleave_action'] = cleave_act
            else:
                result['annotation'] = f"⚔️ Cleave: Missed second target {second_target.get_name()} (rolled {c_total} vs AC {sec_ac})!"

    return result


def apply_mastery_on_miss(
    session,
    attacker,
    target,
    weapon_name: str,
    weapon_obj,
    ability_mod: int,
    damage_type: str
):
    """
    Resolve on-miss Weapon Mastery properties (Graze).
    Returns a dict with graze damage dealt and annotation if applicable.
    """
    if not can_use_weapon_mastery(attacker, weapon_name, weapon_obj):
        return None

    mastery = get_weapon_mastery_property(weapon_name, weapon_obj)
    if mastery != 'Graze' or ability_mod <= 0:
        return None

    graze_damage = ability_mod
    _new_hp, concentration_broken = target.take_damage(graze_damage, damage_type=damage_type, is_critical=False)
    annotation = f"🛡️ Graze: Missed, but dealt {graze_damage} {damage_type or ''} damage (Ability Mod)!"

    return {
        'mastery': 'Graze',
        'damage_amount': graze_damage,
        'damage_type': damage_type,
        'annotation': annotation,
        'concentration_broken': concentration_broken
    }
