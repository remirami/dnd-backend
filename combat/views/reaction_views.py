"""
Reaction Views - Death saves, concentration, reactions, legendary actions.

Contains the CombatReactionMixin with special combat mechanic actions.
"""
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from combat.models import CombatAction, CombatParticipant, CombatSession
from combat.serializers import CombatActionSerializer
from combat.utils import calculate_attack_roll, calculate_damage, check_hit, roll_d20

logger = logging.getLogger('combat')


class CombatReactionMixin:
    """Mixin providing reaction-based combat actions: death saves, concentration, reactions, legendary."""

    @action(detail=True, methods=['post'])
    def death_save(self, request, pk=None):
        """Make a death saving throw"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        manual_roll = request.data.get('roll')
        if manual_roll is not None:
            try:
                manual_roll = int(manual_roll)
            except (ValueError, TypeError):
                manual_roll = None
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if participant.current_hp > 0:
            return Response(
                {"error": f"{participant.get_name()} is not at 0 HP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participant.is_dead():
            return Response(
                {"error": f"{participant.get_name()} is dead and cannot make death saves"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if participant.is_stable():
            return Response(
                {"error": f"{participant.get_name()} is already stable"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, stabilized, died, message, total_roll, natural_roll = participant.make_death_save(roll=manual_roll)
        
        # Create combat action
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='death_save',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=message
        )

        from combat.serializers import CombatSessionSerializer, CombatParticipantSerializer
        fresh_session = CombatSession.objects.prefetch_related('participants', 'actions').get(id=session.id)
        
        return Response({
            "message": message,
            "success": success,
            "is_stable": stabilized,
            "is_dead": died,
            "roll": total_roll,
            "natural_roll": natural_roll,
            "death_save_successes": participant.death_save_successes,
            "death_save_failures": participant.death_save_failures,
            "current_hp": participant.current_hp,
            "action": CombatActionSerializer(combat_action).data,
            "participant": CombatParticipantSerializer(participant).data,
            "session": CombatSessionSerializer(fresh_session).data
        })

    @action(detail=True, methods=['post'])
    def check_concentration(self, request, pk=None):
        """Check concentration"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        damage_amount = int(request.data.get('damage_amount', 0))
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        broken, save_total, save_dc, message = participant.check_concentration(damage_amount)
        
        # Create combat action
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='concentration_check',
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=message
        )
        
        return Response({
            "message": message,
            "concentration_broken": broken,
            "save_roll": save_total,
            "save_dc": save_dc,
            "is_concentrating": participant.is_concentrating,
            "concentration_spell": participant.concentration_spell,
            "action": CombatActionSerializer(combat_action).data
        })

    @action(detail=True, methods=['post'])
    def opportunity_attack(self, request, pk=None):
        """Make an opportunity attack"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attacker_id = request.data.get('attacker_id')
        target_id = request.data.get('target_id')
        
        if not attacker_id or not target_id:
            return Response(
                {"error": "Missing 'attacker_id' or 'target_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attacker = session.participants.get(pk=attacker_id)
            target = session.participants.get(pk=target_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Attacker or target not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if attacker.reaction_used:
            return Response(
                {"error": "Reaction already used this turn"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attacker.is_incapacitated():
            return Response(
                {"error": f"{attacker.get_name()} is {attacker.get_incapacitating_condition()} and cannot take reactions."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get attack details
        attack_name = request.data.get('attack_name', None)
        advantage = request.data.get('advantage', False)
        disadvantage = request.data.get('disadvantage', False)
        
        # Get equipped weapon for characters
        equipped_weapon = None
        damage_string = "1d4"  # Default unarmed
        use_ability = 'STR'  # Default to STR
        
        if attacker.character:
            # Try to get equipped weapon
            equipped_weapon = attacker.get_equipped_weapon('main_hand')
            if equipped_weapon:
                attack_name = attack_name or equipped_weapon.name
                damage_string = equipped_weapon.damage_dice
                
                # Use DEX for finesse weapons, otherwise STR
                if equipped_weapon.finesse:
                    str_mod = attacker.get_ability_modifier('STR')
                    dex_mod = attacker.get_ability_modifier('DEX')
                    use_ability = 'DEX' if dex_mod > str_mod else 'STR'
                else:
                    use_ability = 'STR'
            else:
                attack_name = attack_name or 'Opportunity Attack'
        elif attacker.encounter_enemy:
            # Try to find enemy attack
            enemy = attacker.encounter_enemy.enemy
            attacks = enemy.attacks.all()
            if attacks.exists():
                enemy_attack = attacks.first()
                attack_name = attack_name or enemy_attack.name
                damage_string = enemy_attack.damage
        
        # Roll attack
        roll, roll_breakdown = roll_d20(advantage=advantage, disadvantage=disadvantage)
        
        # Calculate attack modifier
        ability_mod = attacker.get_ability_modifier(use_ability)
        if attacker.character:
            proficiency_bonus = attacker.character.proficiency_bonus
            proficiency = True
        else:
            proficiency_bonus = 2
            proficiency = True
        
        # Get magic item bonuses
        magic_bonuses = attacker.get_magic_item_bonuses()
        
        attack_total, attack_breakdown = calculate_attack_roll(
            roll, ability_mod, proficiency_bonus, proficiency, magic_bonuses['to_hit']
        )
        
        # Get target's effective AC
        target_ac = target.calculate_effective_ac()
        
        # Check if hit
        hit = check_hit(attack_total, target_ac)
        critical = (roll == 20)
        
        # Calculate damage if hit
        damage_amount = 0
        damage_breakdown = ""
        if hit:
            # Add magic item damage bonus
            damage_modifier = ability_mod + magic_bonuses['to_damage']
            damage_amount, damage_breakdown = calculate_damage(
                damage_string, damage_modifier, critical
            )
            _new_hp, _concentration_broken = target.take_damage(damage_amount)
        
        # Mark reaction as used
        attacker.reaction_used = True
        attacker.save()
        
        # Create combat action
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=attacker,
            target=target,
            action_type='opportunity_attack',
            attack_name=attack_name,
            attack_roll=roll,
            attack_modifier=ability_mod + proficiency_bonus + magic_bonuses['to_hit'],
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage_amount if hit else None,
            critical=critical,
            is_opportunity_attack=True,
            is_reaction=True,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{attacker.get_name()} makes an opportunity attack"
        )
        
        return Response({
            "message": f"{attacker.get_name()} makes an opportunity attack on {target.get_name()}",
            "attack_roll": roll,
            "attack_total": attack_total,
            "target_ac": target_ac,
            "weapon_used": attack_name if equipped_weapon else None,
            "ability_used": use_ability,
            "hit": hit,
            "critical": critical,
            "damage": damage_amount if hit else 0,
            "target_hp": target.current_hp,
            "breakdown": {
                "roll": roll_breakdown,
                "attack": attack_breakdown,
                "damage": damage_breakdown if hit else None
            },
            "action": CombatActionSerializer(combat_action).data
        })

    @action(detail=True, methods=['post'])
    def use_reaction(self, request, pk=None):
        """
        Use a reaction (spell, ability, etc.)
        
        Request body:
        {
            "participant_id": 1,
            "reaction_type": "spell",  // or "ability"
            "spell_name": "Shield",  // if reaction_type is "spell"
            "ability_name": "Uncanny Dodge",  // if reaction_type is "ability"
            "target_id": 2,  // optional, for targeted reactions
            "description": "Uses Shield spell to block attack"  // optional
        }
        """
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        reaction_type = request.data.get('reaction_type')  # 'spell' or 'ability'
        
        if not participant_id or not reaction_type:
            return Response(
                {"error": "participant_id and reaction_type are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reaction_type not in ['spell', 'ability']:
            return Response(
                {"error": "reaction_type must be 'spell' or 'ability'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not participant.can_use_reaction():
            return Response(
                {"error": "Reaction already used this round"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target_id = request.data.get('target_id')
        target = None
        if target_id:
            try:
                target = session.participants.get(pk=target_id)
            except CombatParticipant.DoesNotExist:
                return Response(
                    {"error": "Target not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get reaction details
        counterspell_details = None
        if reaction_type == 'spell':
            spell_name = request.data.get('spell_name', 'Unknown Spell')
            description = request.data.get('description', f"{participant.get_name()} casts {spell_name} as a reaction")
            clean_spell = str(spell_name).strip().lower()
            if clean_spell == 'shield':
                participant.use_reaction()
                if not participant.feature_uses:
                    participant.feature_uses = {}
                participant.feature_uses['shield_spell_active'] = True
                participant.save(update_fields=['feature_uses'])
            elif clean_spell == 'counterspell' and target:
                from combat.reaction_spells import resolve_counterspell
                target_spell_name = request.data.get('target_spell_name', 'Spell')
                target_spell_lvl = int(request.data.get('target_spell_level', 3))
                slot_lvl = int(request.data.get('slot_level', 3))
                is_countered, counterspell_details = resolve_counterspell(
                    participant, target, target_spell_name, target_spell_lvl, slot_lvl
                )
                description = counterspell_details.get('message', description)
            else:
                participant.use_reaction()
                if hasattr(participant, 'has_war_caster') and participant.has_war_caster():
                    description = f"⚡ War Caster: {participant.get_name()} casts {spell_name} as a reaction!"
        elif reaction_type == 'sentinel' or (reaction_type == 'ability' and 'sentinel' in str(request.data.get('ability_name', '')).lower()):
            participant.use_reaction()
            ability_name = 'Sentinel Retaliation'
            if target:
                raw_d20, _ = roll_d20()
                eq_w = participant.get_equipped_weapon('main_hand') if hasattr(participant, 'get_equipped_weapon') else None
                atk_mod = participant.get_ability_modifier('STR')
                if eq_w and getattr(eq_w, 'finesse', False):
                    atk_mod = max(atk_mod, participant.get_ability_modifier('DEX'))
                pb = participant.character.proficiency_bonus if participant.character else 2
                tot_atk = raw_d20 + atk_mod + pb
                tgt_ac = target.calculate_effective_ac() if hasattr(target, 'calculate_effective_ac') else target.armor_class
                hit = (tot_atk >= tgt_ac or raw_d20 == 20) and raw_d20 != 1
                dmg_dealt = 0
                if hit:
                    dmg_str = eq_w.damage_dice if eq_w else "1d8"
                    dmg_dealt, _ = calculate_damage(dmg_str, atk_mod, critical=(raw_d20 == 20))
                    target.take_damage(dmg_dealt)
                description = f"🛡️ Sentinel Reaction! {participant.get_name()} lashes out at {target.get_name()} for attacking an ally: rolled {tot_atk} vs AC {tgt_ac} ({'HIT for ' + str(dmg_dealt) + ' dmg' if hit else 'MISSED'})."
            else:
                description = f"{participant.get_name()} prepares a Sentinel reaction."
        else:
            participant.use_reaction()
            ability_name = request.data.get('ability_name', 'Unknown Ability')
            description = request.data.get('description', f"{participant.get_name()} uses {ability_name} as a reaction")
        
        # Create reaction action
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            target=target,
            action_type='reaction',
            attack_name=spell_name if reaction_type == 'spell' else ability_name,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=description,
            is_reaction=True
        )
        
        resp_data = {
            "message": description,
            "reaction_type": reaction_type,
            "participant": participant.get_name(),
            "target": target.get_name() if target else None,
            "reaction_used": True,
            "action": CombatActionSerializer(combat_action).data
        }
        if counterspell_details:
            resp_data["counterspell"] = counterspell_details
        return Response(resp_data)

    @action(detail=True, methods=['post'])
    def legendary_action(self, request, pk=None):
        """Use a legendary action"""
        session = self.get_object()
        
        if session.status != 'active':
            return Response(
                {"error": "Combat is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_id = request.data.get('participant_id')
        action_cost = int(request.data.get('action_cost', 1))
        action_name = request.data.get('action_name', 'Legendary Action')
        
        if not participant_id:
            return Response(
                {"error": "Missing 'participant_id'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = session.participants.get(pk=participant_id)
        except CombatParticipant.DoesNotExist:
            return Response(
                {"error": "Participant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        success, message = participant.use_legendary_action(action_cost)
        
        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create combat action
        combat_action = CombatAction.objects.create(
            combat_session=session,
            actor=participant,
            action_type='legendary_action',
            attack_name=action_name,
            is_legendary_action=True,
            legendary_action_cost=action_cost,
            round_number=session.current_round,
            turn_number=session.current_turn_index,
            description=f"{participant.get_name()} uses {action_name}"
        )
        
        return Response({
            "message": message,
            "action_name": action_name,
            "action_cost": action_cost,
            "legendary_actions_remaining": participant.legendary_actions_remaining,
            "action": CombatActionSerializer(combat_action).data
        })
