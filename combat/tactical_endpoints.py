"""
Tactical Combat Endpoints

Endpoints for AOE targeting, grappling, and cover systems.
"""
from rest_framework import status as http_status
from rest_framework.response import Response

from .aoe_utils import AOE_SPELL_TEMPLATES, get_aoe_targets
from .utils import calculate_damage, calculate_saving_throw, roll_d20


def cast_aoe_spell_endpoint(self, request, pk=None):
    """
    Cast an area of effect spell hitting multiple targets.
    
    POST /api/combat/sessions/{id}/cast_aoe_spell/
    
    Request body:
    {
        "caster_id": 1,
        "spell_name": "fireball",  # or custom params
        "save_dc": 15,
        
        # For sphere (like Fireball)
        "origin_x": 50,
        "origin_y": 50,
        "radius": 20,
        
        # OR for cone (like Burning Hands)
        "caster_x": 10,
        "caster_y": 10,
        "target_x": 30,
        "target_y": 30,
        "length": 15,
        
        # OR for line (like Lightning Bolt)
        "start_x": 10,
        "start_y": 10,
        "end_x": 110,
        "end_y": 10,
        "width": 5,
        
        # OR for cube (like Thunderwave)
        "origin_x": 10,
        "origin_y": 10,
        "size": 15,
        
        # Damage (optional if using template)
        "damage_dice": "8d6",
        "damage_type": "fire",
        "save_type": "dex"
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    caster_id = request.data.get('caster_id')
    spell_name = request.data.get('spell_name', '').lower()
    
    if not caster_id:
        return Response(
            {"error": "caster_id is required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        caster = session.participants.get(id=caster_id)
    except:
        return Response(
            {"error": "Caster not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    # Get spell template or use custom params
    if spell_name in AOE_SPELL_TEMPLATES:
        template = AOE_SPELL_TEMPLATES[spell_name]
        shape = template['shape']
        damage_dice = template['base_damage']
        damage_type = template['damage_type']
        save_type = template['save_type']
        save_dc = request.data.get('save_dc', 15)
    else:
        # Custom AOE spell
        shape = request.data.get('shape')
        damage_dice = request.data.get('damage_dice')
        damage_type = request.data.get('damage_type')
        save_type = request.data.get('save_type', 'dex')
        save_dc = request.data.get('save_dc', 15)
        
        if not all([shape, damage_dice, damage_type]):
            return Response(
                {"error": "For custom spells, shape, damage_dice, and damage_type are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
    
    # Get targets based on shape
    participants = session.participants.filter(is_active=True)
    
    try:
        if shape == 'sphere':
            targets = get_aoe_targets(participants, 'sphere',
                origin_x=request.data.get('origin_x', 0),
                origin_y=request.data.get('origin_y', 0),
                radius=request.data.get('radius', 20)
            )
        elif shape == 'cone':
            targets = get_aoe_targets(participants, 'cone',
                caster_x=request.data.get('caster_x', caster.position_x),
                caster_y=request.data.get('caster_y', caster.position_y),
                target_x=request.data.get('target_x', 0),
                target_y=request.data.get('target_y', 0),
                length=request.data.get('length', 15)
            )
        elif shape == 'line':
            targets = get_aoe_targets(participants, 'line',
                start_x=request.data.get('start_x', caster.position_x),
                start_y=request.data.get('start_y', caster.position_y),
                end_x=request.data.get('end_x', 0),
                end_y=request.data.get('end_y', 0),
                width=request.data.get('width', 5)
            )
        elif shape == 'cube':
            targets = get_aoe_targets(participants, 'cube',
                origin_x=request.data.get('origin_x', 0),
                origin_y=request.data.get('origin_y', 0),
                size=request.data.get('size', 15)
            )
        else:
            return Response(
                {"error": f"Unknown shape: {shape}"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            {"error": f"Error calculating targets: {e!s}"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Apply damage/saves to each target
    targets_affected = []
    
    for participant, distance in targets:
        # Roll save (accounting for Gnome Cunning and Halfling Lucky)
        save_adv = False
        if save_type.upper() in ['INT', 'WIS', 'CHA'] and getattr(participant, 'has_gnome_cunning', lambda: False)():
            save_adv = True
        save_roll, _ = roll_d20(advantage=save_adv, lucky=getattr(participant, 'has_lucky_trait', lambda: False)())
        save_modifier = participant.get_ability_modifier(save_type.upper())
        
        # Apply cover bonus to DEX saves
        cover_bonus = 0
        if save_type.lower() == 'dex' and participant.cover_type != 'none':
            cover_bonus = {'half': 2, 'three_quarters': 5}.get(participant.cover_type, 0)
        
        save_total, _ = calculate_saving_throw(save_roll, save_modifier, 0, False)
        save_total += cover_bonus
        
        save_success = save_total >= save_dc
        
        # Roll damage - calculate_damage returns (damage, breakdown) tuple
        base_damage, _ = calculate_damage(damage_dice)
        damage_taken = base_damage // 2 if save_success else base_damage
        
        # Apply damage
        participant.take_damage(damage_taken, damage_type, check_concentration=True)
        
        targets_affected.append({
            'participant_id': participant.id,
            'name': participant.get_name(),
            'distance': round(distance, 1),
            'save_roll': save_roll,
            'save_modifier': save_modifier,
            'cover_bonus': cover_bonus,
            'save_total': save_total,
            'save_dc': save_dc,
            'save_result': 'success' if save_success else 'failed',
            'damage_rolled': base_damage,
            'damage_taken': damage_taken,
            'current_hp': participant.current_hp,
            'max_hp': participant.max_hp
        })
    
    return Response({
        'spell_name': spell_name or 'Custom AOE',
        'caster': caster.get_name(),
        'shape': shape,
        'damage_type': damage_type,
        'save_type': save_type.upper(),
        'save_dc': save_dc,
        'targets_affected': targets_affected,
        'total_targets': len(targets_affected)
    })


def get_skill_modifier(participant, skill_name, default_ability):
    """Calculate skill modifier for character or monster."""
    ability_mod = participant.get_ability_modifier(default_ability)
    if participant.character:
        prof_bonus = participant.character.proficiency_bonus
        profs = participant.character.proficiencies.filter(skill_name__iexact=skill_name)
        if profs.exists():
            prof = profs.first()
            if getattr(prof, 'expertise', False):
                return ability_mod + (prof_bonus * 2)
            return ability_mod + prof_bonus
        return ability_mod
    elif participant.encounter_enemy and participant.encounter_enemy.enemy:
        enemy = participant.encounter_enemy.enemy
        stats = getattr(enemy, 'stats', None)
        if stats:
            skill_val = getattr(stats, skill_name.lower(), None)
            if skill_val is not None:
                return skill_val
    return ability_mod


def grapple_endpoint(self, request, pk=None):
    """
    Initiate a grapple.
    
    POST /api/combat/sessions/{id}/grapple/
    
    Request body:
    {
        "grappler_id": 1,
        "target_id": 2
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    grappler_id = request.data.get('grappler_id')
    target_id = request.data.get('target_id')
    
    if not grappler_id or not target_id:
        return Response(
            {"error": "grappler_id and target_id are required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        grappler = session.participants.get(id=grappler_id)
        target = session.participants.get(id=target_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    # Check if grappler has action / attack available
    if grappler.action_used and grappler.attacks_remaining <= 0:
        return Response(
            {"error": "Grappler has already used their action this turn"},
            status=http_status.HTTP_400_BAD_REQUEST
        )

    if grappler.is_incapacitated():
        return Response(
            {"error": f"{grappler.get_name()} is {grappler.get_incapacitating_condition()} and cannot grapple."},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already grappling
    if grappler.is_grappling:
        return Response(
            {"error": "Grappler is already grappling someone"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Check if target already grappled
    if target.grappled_by:
        return Response(
            {"error": f"{target.get_name()} is already grappled"},
            status=http_status.HTTP_400_BAD_REQUEST
        )

    # 5e Size Limitation: The target of your grapple must be no more than one size larger than you.
    size_rank = {'T': 0, 'S': 1, 'M': 2, 'L': 3, 'H': 4, 'G': 5}
    g_rank = size_rank.get(grappler.get_size(), 2)
    t_rank = size_rank.get(target.get_size(), 2)
    if t_rank > g_rank + 1:
        return Response(
            {"error": f"{target.get_name()} ({target.get_size_dimensions()['name']}) is too large for {grappler.get_name()} to grapple (maximum one size larger)."},
            status=http_status.HTTP_400_BAD_REQUEST
        )

    # Check melee reach if coordinates are present
    has_coords = (grappler.position_x != 0 or grappler.position_y != 0 or target.position_x != 0 or target.position_y != 0)
    if has_coords:
        reach = grappler.get_reach() if hasattr(grappler, 'get_reach') else 5
        dist = grappler.get_distance_to(target)
        if dist > reach:
            return Response(
                {"error": f"{target.get_name()} is out of melee reach ({dist} ft away, maximum reach is {reach} ft). Move closer first!"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
    
    # Contested check: Grappler's Athletics vs Target's Athletics or Acrobatics
    grappler_roll, _ = roll_d20(lucky=getattr(grappler, 'has_lucky_trait', lambda: False)())
    grappler_athletics = get_skill_modifier(grappler, 'Athletics', 'STR')
    grappler_total = grappler_roll + grappler_athletics
    
    if target.is_incapacitated():
        target_roll, target_modifier, target_total = 0, 0, 0
    else:
        target_roll, _ = roll_d20(lucky=getattr(target, 'has_lucky_trait', lambda: False)())
        target_athletics = get_skill_modifier(target, 'Athletics', 'STR')
        target_acrobatics = get_skill_modifier(target, 'Acrobatics', 'DEX')
        target_modifier = max(target_athletics, target_acrobatics)
        target_total = target_roll + target_modifier
    
    success = grappler_total > target_total
    
    from bestiary.models import Condition
    from combat.models import CombatAction
    from combat.serializers import CombatSessionSerializer

    if success:
        # Apply grapple state
        grappler.is_grappling = True
        target.grappled_by = grappler

        grappled_cond, _ = Condition.objects.get_or_create(name='Grappled')
        target.conditions.add(grappled_cond)

        # Consume action / attack
        if grappler.attacks_remaining > 1:
            grappler.attacks_remaining -= 1
        else:
            grappler.action_used = True
            grappler.attacks_remaining = 0
        grappler.save()

        # If airborne without hover, falls to ground
        if target.altitude > 0 and not getattr(target, 'has_hover', False):
            target.altitude = 0
            target.is_flying = False
            prone_cond, _ = Condition.objects.get_or_create(name='Prone')
            target.conditions.add(prone_cond)

        target.save()
        
        message = f"🤼 {grappler.get_name()} successfully grapples {target.get_name()}! (Athletics {grappler_total} vs {target_total}). {target.get_name()}'s speed is now 0."
    else:
        if grappler.attacks_remaining > 1:
            grappler.attacks_remaining -= 1
        else:
            grappler.action_used = True
            grappler.attacks_remaining = 0
        grappler.save()
        message = f"{grappler.get_name()} fails to grapple {target.get_name()} (Athletics {grappler_total} vs {target_total})."
    
    CombatAction.objects.create(
        combat_session=session,
        actor=grappler,
        target=target,
        action_type='grapple',
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=message
    )

    fresh_session = self.get_queryset().get(pk=session.pk)

    return Response({
        'success': success,
        'message': message,
        'grappler_roll': grappler_roll,
        'grappler_modifier': grappler_athletics,
        'grappler_total': grappler_total,
        'target_roll': target_roll,
        'target_modifier': target_modifier,
        'target_total': target_total,
        'target_speed': 0 if success else target.speed,
        'session': CombatSessionSerializer(fresh_session).data
    })


def escape_grapple_endpoint(self, request, pk=None):
    """
    Attempt to escape a grapple.
    
    POST /api/combat/sessions/{id}/escape_grapple/
    
    Request body:
    {
        "participant_id": 2
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    participant_id = request.data.get('participant_id')
    
    if not participant_id:
        return Response(
            {"error": "participant_id is required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        participant = session.participants.get(id=participant_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    if not participant.grappled_by:
        return Response(
            {"error": f"{participant.get_name()} is not grappled"},
            status=http_status.HTTP_400_BAD_REQUEST
        )

    if participant.action_used:
        return Response(
            {"error": f"{participant.get_name()} has already used their action this turn."},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    grappler = participant.grappled_by
    if not grappler:
        return Response({"error": "You are not currently grappled."}, status=http_status.HTTP_400_BAD_REQUEST)

    reach = grappler.get_reach() if hasattr(grappler, 'get_reach') else 5
    dist = participant.get_distance_to(grappler)
    if dist > reach:
        participant.release_grapple()
        return Response({
            "error": f"You are no longer within reach of {grappler.get_name()} ({dist} ft away). The grapple has already ended."
        }, status=http_status.HTTP_400_BAD_REQUEST)
    
    # Contested check: Grappled's Athletics or Acrobatics vs Grappler's Athletics
    participant_roll, _ = roll_d20(lucky=getattr(participant, 'has_lucky_trait', lambda: False)())
    participant_athletics = get_skill_modifier(participant, 'Athletics', 'STR')
    participant_acrobatics = get_skill_modifier(participant, 'Acrobatics', 'DEX')
    participant_modifier = max(participant_athletics, participant_acrobatics)
    participant_total = participant_roll + participant_modifier
    
    if grappler.is_incapacitated():
        grappler_roll, grappler_athletics, grappler_total = 0, 0, 0
    else:
        grappler_roll, _ = roll_d20(lucky=getattr(grappler, 'has_lucky_trait', lambda: False)())
        grappler_athletics = get_skill_modifier(grappler, 'Athletics', 'STR')
        grappler_total = grappler_roll + grappler_athletics
    
    success = participant_total > grappler_total

    participant.action_used = True
    participant.attacks_remaining = 0
    participant.save(update_fields=['action_used', 'attacks_remaining'])

    from combat.models import CombatAction
    from combat.serializers import CombatSessionSerializer

    if success:
        # Escape successful - release grapple & conditions
        participant.release_grapple()
        message = f"🔓 {participant.get_name()} escapes the grapple from {grappler.get_name()}! ({participant_total} vs {grappler_total})"
    else:
        message = f"{participant.get_name()} fails to escape {grappler.get_name()}'s grapple ({participant_total} vs {grappler_total})."

    CombatAction.objects.create(
        combat_session=session,
        actor=participant,
        target=grappler,
        action_type='escape_grapple',
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=message
    )

    fresh_session = self.get_queryset().get(pk=session.pk)
    
    return Response({
        'success': success,
        'message': message,
        'participant_roll': participant_roll,
        'participant_modifier': participant_modifier,
        'participant_total': participant_total,
        'grappler_roll': grappler_roll,
        'grappler_modifier': grappler_athletics,
        'grappler_total': grappler_total,
        'session': CombatSessionSerializer(fresh_session).data
    })


def release_grapple_endpoint(self, request, pk=None):
    """
    Release a grapple as a free action.
    POST /api/combat/sessions/{id}/release_grapple/
    Request body: { "grappler_id": 1 }
    """
    session = self.get_object()
    if session.status != 'active':
        return Response({"error": "Combat is not active"}, status=http_status.HTTP_400_BAD_REQUEST)

    grappler_id = request.data.get('grappler_id')
    if not grappler_id:
        return Response({"error": "grappler_id is required"}, status=http_status.HTTP_400_BAD_REQUEST)

    try:
        grappler = session.participants.get(id=grappler_id)
    except:
        return Response({"error": "Participant not found"}, status=http_status.HTTP_404_NOT_FOUND)

    if not grappler.is_grappling:
        return Response({"error": f"{grappler.get_name()} is not currently grappling anyone."}, status=http_status.HTTP_400_BAD_REQUEST)

    victim = grappler.grappling_targets.first()
    victim_name = victim.get_name() if victim else "the target"
    grappler.release_grapple()

    from combat.models import CombatAction
    from combat.serializers import CombatSessionSerializer
    desc = f"🫱 {grappler.get_name()} releases {victim_name} from the grapple."
    CombatAction.objects.create(
        combat_session=session,
        actor=grappler,
        target=victim,
        action_type='release_grapple',
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=desc
    )

    fresh_session = self.get_queryset().get(pk=session.pk)
    return Response({
        'success': True,
        'message': desc,
        'session': CombatSessionSerializer(fresh_session).data
    })


def pin_endpoint(self, request, pk=None):
    """
    Pin a grappled creature using the 5e Grappler feat.
    POST /api/combat/sessions/{id}/pin/
    Request body: { "grappler_id": 1, "target_id": 2 }
    """
    session = self.get_object()
    if session.status != 'active':
        return Response({"error": "Combat is not active"}, status=http_status.HTTP_400_BAD_REQUEST)

    grappler_id = request.data.get('grappler_id')
    if not grappler_id:
        return Response({"error": "grappler_id is required"}, status=http_status.HTTP_400_BAD_REQUEST)

    try:
        grappler = session.participants.get(id=grappler_id)
    except:
        return Response({"error": "Participant not found"}, status=http_status.HTTP_404_NOT_FOUND)

    if not grappler.has_grappler_feat():
        return Response({
            "error": f"{grappler.get_name()} does not have the Grappler feat. Pinning requires the Grappler feat."
        }, status=http_status.HTTP_400_BAD_REQUEST)

    if not grappler.is_grappling:
        return Response({
            "error": f"{grappler.get_name()} must be actively grappling a creature to pin it."
        }, status=http_status.HTTP_400_BAD_REQUEST)

    if grappler.action_used and grappler.attacks_remaining <= 0:
        return Response({
            "error": f"{grappler.get_name()} has already used their action this turn."
        }, status=http_status.HTTP_400_BAD_REQUEST)

    target_id = request.data.get('target_id')
    if target_id:
        target = session.participants.filter(id=target_id).first()
    else:
        target = grappler.grappling_targets.first()

    if not target or target.grappled_by_id != grappler.id:
        return Response({"error": "Target must be a creature currently grappled by you."}, status=http_status.HTTP_400_BAD_REQUEST)

    # 5e Reach check: Pinning requires the target to be within melee reach
    dist = grappler.get_distance_to(target)
    reach = grappler.get_reach() if hasattr(grappler, 'get_reach') else 5
    if dist > reach:
        grappler.release_grapple()
        return Response({
            "error": f"{target.get_name()} is out of melee reach ({dist} ft away, max reach is {reach} ft). The grapple has ended."
        }, status=http_status.HTTP_400_BAD_REQUEST)

    # Check if already pinned
    if grappler.feature_uses and grappler.feature_uses.get('is_pinning'):
        return Response({"error": f"{target.get_name()} is already pinned!"}, status=http_status.HTTP_400_BAD_REQUEST)

    # Contested grapple check: Grappler's Athletics vs Target's Athletics or Acrobatics
    grappler_roll, _ = roll_d20(lucky=getattr(grappler, 'has_lucky_trait', lambda: False)())
    grappler_athletics = get_skill_modifier(grappler, 'Athletics', 'STR')
    grappler_total = grappler_roll + grappler_athletics

    if target.is_incapacitated():
        target_roll, target_modifier, target_total = 0, 0, 0
    else:
        target_roll, _ = roll_d20(lucky=getattr(target, 'has_lucky_trait', lambda: False)())
        target_athletics = get_skill_modifier(target, 'Athletics', 'STR')
        target_acrobatics = get_skill_modifier(target, 'Acrobatics', 'DEX')
        target_modifier = max(target_athletics, target_acrobatics)
        target_total = target_roll + target_modifier

    # Action cost
    grappler.action_used = True
    grappler.attacks_remaining = 0

    from bestiary.models import Condition
    from combat.models import CombatAction
    from combat.serializers import CombatSessionSerializer

    success = grappler_total > target_total
    if success:
        restrained_cond, _ = Condition.objects.get_or_create(name='Restrained')
        grappler.conditions.add(restrained_cond)
        target.conditions.add(restrained_cond)

        if not isinstance(grappler.feature_uses, dict):
            grappler.feature_uses = {}
        if not isinstance(target.feature_uses, dict):
            target.feature_uses = {}

        grappler.feature_uses['is_pinning'] = target.id
        target.feature_uses['pinned_by'] = grappler.id
        grappler.save(update_fields=['action_used', 'attacks_remaining', 'feature_uses'])
        target.save(update_fields=['feature_uses'])

        desc = f"📌 Grappler Feat Pin! {grappler.get_name()} pins {target.get_name()} (Athletics {grappler_total} vs {target_total})! Both {grappler.get_name()} and {target.get_name()} are now RESTRAINED until the grapple ends."
    else:
        grappler.save(update_fields=['action_used', 'attacks_remaining'])
        desc = f"📌 {grappler.get_name()} attempts to pin {target.get_name()}, but fails! (Athletics {grappler_total} vs {target_total}). Grapple remains active."

    CombatAction.objects.create(
        combat_session=session,
        actor=grappler,
        target=target,
        action_type='pin',
        round_number=session.current_round,
        turn_number=session.current_turn_index,
        description=desc
    )

    fresh_session = self.get_queryset().get(pk=session.pk)
    return Response({
        'success': success,
        'message': desc,
        'grappler_roll': grappler_roll,
        'grappler_modifier': grappler_athletics,
        'grappler_total': grappler_total,
        'target_roll': target_roll,
        'target_modifier': target_modifier,
        'target_total': target_total,
        'session': CombatSessionSerializer(fresh_session).data
    })


def set_cover_endpoint(self, request, pk=None):
    """
    Set cover type for a participant.
    
    POST /api/combat/sessions/{id}/set_cover/
    
    Request body:
    {
        "participant_id": 1,
        "cover_type": "half"  // none, half, three_quarters, full
    }
    """
    session = self.get_object()
    
    if session.status != 'active':
        return Response(
            {"error": "Combat is not active"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    participant_id = request.data.get('participant_id')
    cover_type = request.data.get('cover_type')
    
    if not participant_id or not cover_type:
        return Response(
            {"error": "participant_id and cover_type are required"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    valid_cover_types = ['none', 'half', 'three_quarters', 'full']
    if cover_type not in valid_cover_types:
        return Response(
            {"error": f"Invalid cover_type. Must be one of: {', '.join(valid_cover_types)}"},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    try:
        participant = session.participants.get(id=participant_id)
    except:
        return Response(
            {"error": "Participant not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    
    old_cover = participant.cover_type
    participant.cover_type = cover_type
    participant.save()
    
    # Calculate bonuses
    cover_bonuses = {
        'none': {'ac': 0, 'dex_save': 0},
        'half': {'ac': 2, 'dex_save': 2},
        'three_quarters': {'ac': 5, 'dex_save': 5},
        'full': {'ac': float('inf'), 'dex_save': float('inf')}
    }
    
    bonus = cover_bonuses[cover_type]
    
    return Response({
        'participant': participant.get_name(),
        'old_cover': old_cover,
        'new_cover': cover_type,
        'ac_bonus': bonus['ac'] if bonus['ac'] != float('inf') else 'Cannot be targeted',
        'dex_save_bonus': bonus['dex_save'] if bonus['dex_save'] != float('inf') else 'Total protection',
        'message': f"{participant.get_name()} now has {cover_type.replace('_', ' ')} cover"
    })
