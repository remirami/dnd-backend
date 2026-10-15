from rest_framework import serializers

from bestiary.serializers import ConditionSerializer, DamageTypeSerializer
from characters.serializers import CharacterSerializer
from encounters.serializers import EncounterEnemySerializer, EncounterSerializer

from .models import CombatAction, CombatLog, CombatParticipant, CombatSession, EnvironmentalEffect, ParticipantPosition


class CombatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for combat participants"""
    participant_type_display = serializers.CharField(source='get_participant_type_display', read_only=True)
    name = serializers.SerializerMethodField()
    character = CharacterSerializer(read_only=True, allow_null=True)
    encounter_enemy = EncounterEnemySerializer(read_only=True, allow_null=True)
    conditions = ConditionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CombatParticipant
        fields = "__all__"
    
    def get_name(self, obj):
        return obj.get_name()
    
    def to_representation(self, instance):
        """Add computed fields"""
        data = super().to_representation(instance)
        data['speed'] = instance.speed
        data['movement_remaining'] = instance.movement_remaining
        data['dashed_this_turn'] = bool(instance.feature_uses and instance.feature_uses.get('dash_active'))
        data['is_disengaged'] = bool(instance.feature_uses and instance.feature_uses.get('disengaged'))
        data['is_dodging'] = bool(instance.feature_uses and (instance.feature_uses.get('dodging') or instance.feature_uses.get('dodge_active')))
        # Add death save status
        if instance.current_hp <= 0:
            data['death_save_status'] = {
                'successes': instance.death_save_successes,
                'failures': instance.death_save_failures,
                'is_stable': instance.death_save_successes >= 3,
                'is_dead': instance.death_save_failures >= 3
            }
        
        # Effective AC including buffs, armor, magic items, and dynamic cover props
        data['effective_ac'] = instance.calculate_effective_ac()
        data['cover'] = instance.get_cover_details() if hasattr(instance, 'get_cover_details') else None

        # Active buffs representation
        active_buffs = instance.get_active_buffs() if hasattr(instance, 'get_active_buffs') else (instance.feature_uses or {}).get('active_buffs', [])
        data['active_buffs'] = active_buffs

        # Inject active buffs into data['conditions'] so all condition badges and clash cards display them!
        conds = list(data.get('conditions') or [])
        existing_cond_names = {c.get('name', '').lower() if isinstance(c, dict) else str(c).lower() for c in conds}
        for buff in active_buffs:
            b_name = buff.get('name', '')
            if b_name.lower() not in existing_cond_names:
                conds.append({
                    'name': b_name,
                    'description': buff.get('description', ''),
                    'is_buff': True,
                    'source': buff.get('source_spell', ''),
                    'caster_id': buff.get('caster_id'),
                })
                existing_cond_names.add(b_name.lower())
        data['conditions'] = conds

        # Creature size & 3D flying properties
        data['size'] = instance.get_size()
        size_dims = instance.get_size_dimensions()
        data['size_dimensions'] = size_dims
        data['size_display'] = size_dims.get('name', 'Medium')
        data['occupied_cells'] = instance.get_occupied_cells()
        data['altitude'] = instance.altitude or 0
        data['is_flying'] = bool(instance.is_flying)
        data['fly_speed'] = instance.get_fly_speed()
        data['has_hover'] = instance.has_hover()
        data['can_fly'] = instance.can_fly()

        # Grapple & Grappler feat mechanics
        data['is_grappling'] = bool(instance.is_grappling)
        data['grappled_by_id'] = instance.grappled_by_id
        data['grappled_by_name'] = instance.grappled_by.get_name() if instance.grappled_by else None
        data['grappling_target_id'] = instance.grappling_targets.filter(is_active=True).values_list('id', flat=True).first() if instance.is_grappling else None
        data['has_grappler_feat'] = instance.has_grappler_feat()
        data['is_pinned'] = bool(instance.feature_uses and instance.feature_uses.get('pinned_by_grappler'))
        if instance.character:
            data['race_name'] = instance.character.race.name.lower() if instance.character.race else ''
            data['has_lucky_trait'] = instance.has_lucky_trait()
            data['has_halfling_nimbleness'] = instance.has_halfling_nimbleness()
            data['has_relentless_endurance'] = instance.has_relentless_endurance()
            data['relentless_endurance_used'] = bool(instance.feature_uses and instance.feature_uses.get('relentless_endurance_used', False))
            data['has_fey_ancestry'] = instance.has_fey_ancestry()
            data['has_brave_trait'] = instance.has_brave_trait()
            data['has_gnome_cunning'] = instance.has_gnome_cunning()
            data['has_dwarven_resilience'] = instance.has_dwarven_resilience()
            data['has_hellish_resistance'] = instance.has_hellish_resistance()

        # Add equipped items info for characters
        if instance.character:
            equipped_weapon = instance.get_equipped_weapon('main_hand') or instance.get_equipped_weapon('off_hand') or instance.get_equipped_weapon(None)
            equipped_armor = instance.get_equipped_armor()
            equipped_shield = instance.get_equipped_shield()
            effective_ac = instance.calculate_effective_ac()
            
            shield_bonus = 2
            if equipped_shield:
                shield_bonus = getattr(equipped_shield, 'ac_bonus', None) or (equipped_shield.base_ac if equipped_shield.base_ac <= 5 else 2)

            data['equipped_items'] = {
                'weapon': {
                    'name': equipped_weapon.name,
                    'damage_dice': getattr(equipped_weapon, 'damage_dice', ''),
                } if equipped_weapon else None,
                'armor': {
                    'name': equipped_armor.name,
                    'base_ac': getattr(equipped_armor, 'base_ac', 10),
                } if equipped_armor else None,
                'shield': {
                    'name': equipped_shield.name,
                    'ac_bonus': shield_bonus,
                } if equipped_shield else None,
            }
            data['effective_ac'] = effective_ac

            # Full equipped gear list matching character sheet equipment slots
            equipped_gear = []
            for ci in instance.character.character_items.all():
                if ci.is_equipped and ci.equipment_slot and ci.equipment_slot != 'inventory':
                    item_obj = ci.item
                    is_shield = ci.equipment_slot in ('shield', 'off_hand') and (
                        'shield' in item_obj.name.lower() or
                        (hasattr(item_obj, 'armor') and getattr(item_obj.armor, 'armor_type', None) == 'shield')
                    )
                    gear_entry = {
                        'id': ci.id,
                        'name': item_obj.name,
                        'slot': ci.equipment_slot,
                        'is_shield': is_shield,
                        'rarity': getattr(item_obj, 'rarity', 'common'),
                        'description': item_obj.description or '',
                        'is_attuned': ci.is_attuned,
                    }
                    if hasattr(item_obj, 'weapon'):
                        w = item_obj.weapon
                        gear_entry['weapon_type_display'] = getattr(w, 'weapon_type_display', '')
                        gear_entry['damage_dice'] = w.damage_dice
                        gear_entry['damage_type'] = getattr(w.damage_type, 'name', '') if getattr(w, 'damage_type', None) else ''
                    elif hasattr(item_obj, 'armor'):
                        a = item_obj.armor
                        gear_entry['armor_type_display'] = getattr(a, 'armor_type_display', '') or a.armor_type
                        if is_shield:
                            gear_entry['ac_bonus'] = getattr(a, 'ac_bonus', None) or (a.base_ac if a.base_ac <= 5 else 2)
                        else:
                            gear_entry['base_ac'] = a.base_ac
                    equipped_gear.append(gear_entry)
            data['equipped_gear'] = equipped_gear

            # Class feature resources for characters
            feature_uses = instance.feature_uses or {}
            data['feature_uses'] = feature_uses
            class_name = getattr(instance.character.character_class, 'name', '').lower()
            char_features = instance.character.features.all()
            
            # Paladin features
            is_paladin = instance.is_paladin()
            data['is_paladin'] = is_paladin
            if is_paladin:
                data['lay_on_hands_pool'] = instance.get_lay_on_hands_pool()
                data['max_lay_on_hands_pool'] = (instance.character.level or 1) * 5

            # Barbarian features (Rage, Reckless Attack)
            is_barbarian = instance.is_barbarian()
            data['is_barbarian'] = is_barbarian
            if is_barbarian:
                data['is_raging'] = instance.is_raging()
                data['rage_uses_remaining'] = instance.get_rage_uses_remaining()
                data['max_rage_uses'] = instance.get_max_rage_uses()
                data['rage_damage_bonus'] = instance.get_rage_damage_bonus()
                data['reckless_attack_active'] = bool(feature_uses.get('reckless_attack_active', False))
                data['has_reckless_attack'] = (instance.character.level or 1) >= 2

            # Fighter features (Second Wind, Action Surge)
            is_fighter = class_name == 'fighter' or any('second wind' in f.name.lower() for f in char_features)
            data['is_fighter'] = is_fighter
            if is_fighter:
                fighter_level = instance.character.level or 1
                has_action_surge = fighter_level >= 2 or any('action surge' in f.name.lower() for f in char_features)
                data['has_action_surge'] = has_action_surge
                data['second_wind_used'] = bool(feature_uses.get('second_wind_used', False))
                if has_action_surge:
                    data['action_surge_used'] = bool(feature_uses.get('action_surge_used', False))
                    data['action_surge_available'] = not feature_uses.get('action_surge_used', False)
                else:
                    data['action_surge_used'] = False
                    data['action_surge_available'] = None

            # Rogue features (Cunning Action, Sneak Attack, Uncanny Dodge)
            is_rogue = class_name == 'rogue' or any('sneak attack' in f.name.lower() for f in char_features)
            data['is_rogue'] = is_rogue
            if is_rogue:
                rogue_level = instance.character.level or 1
                has_cunning_action = rogue_level >= 2 or any('cunning action' in f.name.lower() for f in char_features)
                data['has_cunning_action'] = has_cunning_action
                data['cunning_action_available'] = has_cunning_action
                data['has_sneak_attack'] = True
                sa_dice_count = max(1, (rogue_level + 1) // 2)
                data['sneak_attack_dice'] = f"{sa_dice_count}d6"
                data['sneak_attack_used_this_turn'] = bool(feature_uses.get('sneak_attack_used_this_turn', False))
                data['has_uncanny_dodge'] = rogue_level >= 5

            # Paladin features (Lay on Hands, Divine Smite, Channel Divinity)
            is_paladin = instance.is_paladin()
            data['is_paladin'] = is_paladin
            if is_paladin:
                paladin_level = instance.character.level or 1
                data['lay_on_hands_pool'] = instance.get_lay_on_hands_pool()
                data['max_lay_on_hands_pool'] = paladin_level * 5
                data['has_divine_smite'] = paladin_level >= 2
                data['channel_divinity_remaining'] = instance.get_channel_divinity_uses_remaining()
                data['channel_divinity_max'] = instance.get_channel_divinity_max_uses()

            # Cleric features (Channel Divinity: Turn Undead, Preserve Life, Destroy Undead)
            is_cleric = instance.is_cleric()
            data['is_cleric'] = is_cleric
            if is_cleric:
                cleric_level = instance.character.level or 1
                data['channel_divinity_remaining'] = instance.get_channel_divinity_uses_remaining()
                data['channel_divinity_max'] = instance.get_channel_divinity_max_uses()
                data['can_turn_undead'] = cleric_level >= 2
                if cleric_level >= 17:
                    data['destroy_undead_cr'] = 4.0
                elif cleric_level >= 14:
                    data['destroy_undead_cr'] = 3.0
                elif cleric_level >= 11:
                    data['destroy_undead_cr'] = 2.0
                elif cleric_level >= 8:
                    data['destroy_undead_cr'] = 1.0
                elif cleric_level >= 5:
                    data['destroy_undead_cr'] = 0.5
                else:
                    data['destroy_undead_cr'] = None

            # Monk features (Ki: Flurry of Blows, Patient Defense, Step of the Wind, Stunning Strike)
            is_monk = instance.is_monk()
            data['is_monk'] = is_monk
            if is_monk:
                monk_level = instance.character.level or 1
                data['ki_pool_remaining'] = instance.get_ki_pool_remaining()
                data['ki_pool_max'] = instance.get_ki_pool_max()
                data['martial_arts_die'] = instance.get_martial_arts_die()
                data['can_flurry_of_blows'] = monk_level >= 2
                data['can_patient_defense'] = monk_level >= 2
                data['can_step_of_the_wind'] = monk_level >= 2
                data['can_stunning_strike'] = monk_level >= 5

            # Bard features (Bardic Inspiration)
            is_bard = instance.is_bard()
            data['is_bard'] = is_bard
            if is_bard:
                data['bardic_inspiration_remaining'] = instance.get_bardic_inspiration_uses_remaining()
                data['bardic_inspiration_max'] = instance.get_bardic_inspiration_max_uses()
                data['bardic_inspiration_die'] = instance.get_bardic_inspiration_die_size()

            # Druid features (Wild Shape)
            is_druid = instance.is_druid()
            data['is_druid'] = is_druid
            if is_druid:
                data['wild_shape_remaining'] = instance.get_wild_shape_uses_remaining()
                data['wild_shape_max'] = instance.get_wild_shape_max_uses()
                data['is_wild_shaped'] = bool(feature_uses.get('wild_shaped', False))
                data['wild_shape_beast'] = feature_uses.get('wild_shape_beast', None)

            # Wizard features (Arcane Recovery)
            is_wizard = instance.is_wizard()
            data['is_wizard'] = is_wizard
            if is_wizard:
                data['has_arcane_recovery'] = instance.has_arcane_recovery()
                data['arcane_recovery_used'] = instance.is_arcane_recovery_used()
                data['arcane_recovery_max_levels'] = instance.get_arcane_recovery_max_levels()

        
        # Add enemy stat block for enemy participants
        enemy = None
        if instance.encounter_enemy:
            enemy = instance.encounter_enemy.enemy
        elif instance.participant_type == 'enemy' and instance.name:
            # Practice mode enemy — try to find by name
            from bestiary.models import Enemy as EnemyModel
            enemy = EnemyModel.objects.filter(name=instance.name).first()
        
        if enemy:
            data['creature_type'] = enemy.get_creature_type_display() if hasattr(enemy, 'get_creature_type_display') else getattr(enemy, 'creature_type', '')
            data['alignment'] = enemy.get_alignment_display() if hasattr(enemy, 'get_alignment_display') else getattr(enemy, 'alignment', '')
            data['challenge_rating'] = str(enemy.challenge_rating) if enemy.challenge_rating is not None else None
            if hasattr(enemy, 'get_size_display') and enemy.get_size_display():
                data['size_display'] = enemy.get_size_display()

            # Ability scores
            if hasattr(enemy, 'stats'):
                stats = enemy.stats
                data['enemy_stats'] = {
                    'size': enemy.size,
                    'size_display': enemy.get_size_display() if hasattr(enemy, 'get_size_display') else size_dims.get('name', 'Medium'),
                    'ability_scores': {
                        'strength': {'score': stats.strength, 'modifier': stats.strength_modifier},
                        'dexterity': {'score': stats.dexterity, 'modifier': stats.dexterity_modifier},
                        'constitution': {'score': stats.constitution, 'modifier': stats.constitution_modifier},
                        'intelligence': {'score': stats.intelligence, 'modifier': stats.intelligence_modifier},
                        'wisdom': {'score': stats.wisdom, 'modifier': stats.wisdom_modifier},
                        'charisma': {'score': stats.charisma, 'modifier': stats.charisma_modifier},
                    },
                    'saving_throws': {
                        'str': stats.str_save,
                        'dex': stats.dex_save,
                        'con': stats.con_save,
                        'int': stats.int_save,
                        'wis': stats.wis_save,
                        'cha': stats.cha_save,
                    },
                    'speed': stats.speed,
                    'proficiency_bonus': stats.proficiency_bonus,
                    'senses': {
                        'darkvision': stats.darkvision,
                        'blindsight': stats.blindsight,
                        'tremorsense': stats.tremorsense,
                        'truesight': stats.truesight,
                        'passive_perception': stats.passive_perception,
                    },
                }
            
            # Structured EnemyAction records (excluding Multiattack utility entries)
            raw_actions = list(enemy.actions.all().prefetch_related('damage_rolls', 'conditions_inflicted'))
            actions = [act for act in raw_actions if 'multiattack' not in act.name.lower()]
            
            # Attacks: Prefer structured weapon actions over legacy flat strings
            action_attacks = []
            for act in actions:
                if act.attack_type in ['melee_weapon', 'ranged_weapon', 'melee_spell', 'ranged_spell']:
                    dmg_rolls = list(act.damage_rolls.all())
                    dmg_str = " + ".join([d.formula for d in dmg_rolls]) if dmg_rolls else "1d6 bludgeoning"
                    action_attacks.append({
                        'name': act.name,
                        'bonus': act.attack_bonus if act.attack_bonus is not None else (stats.strength_modifier if stats else 2),
                        'damage': dmg_str,
                    })

            if action_attacks:
                data['enemy_attacks'] = action_attacks
            else:
                # Fallback to legacy attacks, strictly excluding any named Multiattack
                attacks = [atk for atk in enemy.attacks.all() if 'multiattack' not in atk.name.lower()]
                if attacks:
                    data['enemy_attacks'] = [
                        {
                            'name': atk.name,
                            'bonus': atk.bonus,
                            'damage': atk.damage,
                        }
                        for atk in attacks
                    ]
            
            # Abilities (use in-memory list to leverage prefetch_related)
            abilities = list(enemy.abilities.all())
            if abilities:
                data['enemy_abilities'] = [
                    {
                        'name': ab.name,
                        'description': ab.description,
                    }
                    for ab in abilities
                ]
            
            # Resistances/immunities (use in-memory list to leverage prefetch_related)
            resistances = list(enemy.resistances.all())
            if resistances:
                data['enemy_resistances'] = [
                    {
                        'damage_type': r.damage_type.name,
                        'type': r.resistance_type,
                    }
                    for r in resistances
                ]

            if actions:
                data['enemy_actions'] = [
                    {
                        'id': act.id,
                        'name': act.name,
                        'description': act.description,
                        'action_type': act.action_type,
                        'action_type_display': act.get_action_type_display(),
                        'attack_type': act.attack_type,
                        'attack_type_display': act.get_attack_type_display(),
                        'attack_bonus': act.attack_bonus,
                        'reach_or_range': act.reach_or_range,
                        'saving_throw_dc': act.saving_throw_dc,
                        'saving_throw_ability': act.saving_throw_ability,
                        'half_damage_on_save': act.half_damage_on_save,
                        'conditions_inflicted': [c.name for c in act.conditions_inflicted.all()],
                        'condition_save_end': act.condition_save_end,
                        'has_recharge': act.has_recharge,
                        'recharge_min_roll': act.recharge_min_roll,
                        'is_charged': instance.recharge_state.get(act.name, True) if act.has_recharge else True,
                        'damage_rolls': [
                            {
                                'formula': d.formula,
                                'dice_count': d.dice_count,
                                'dice_sides': d.dice_sides,
                                'damage_bonus': d.damage_bonus,
                                'damage_type': d.damage_type.name if d.damage_type else None,
                                'is_secondary': d.is_secondary,
                            }
                            for d in act.damage_rolls.all()
                        ]
                    }
                    for act in actions
                ]

            # Multiattack
            if hasattr(enemy, 'multiattack') and enemy.multiattack:
                data['multiattack'] = {
                    'description': enemy.multiattack.description,
                    'action_count': enemy.multiattack.action_count,
                    'sequence': enemy.multiattack.sequence,
                }

            # Traits
            traits = list(enemy.traits.all())
            if traits:
                data['enemy_traits'] = [
                    {
                        'name': t.name,
                        'description': t.description,
                        'trait_type': t.trait_type,
                    }
                    for t in traits
                ]

            data['recharge_state'] = instance.recharge_state
        
        return data


class CombatActionSerializer(serializers.ModelSerializer):
    """Serializer for combat actions"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    is_ai = serializers.SerializerMethodField()
    damage_type = DamageTypeSerializer(read_only=True, allow_null=True)
    damage_type_name = serializers.SerializerMethodField()
    is_advantage = serializers.SerializerMethodField()
    is_disadvantage = serializers.SerializerMethodField()
    
    class Meta:
        model = CombatAction
        fields = "__all__"
    
    def get_damage_type_name(self, obj):
        return obj.damage_type.name if obj.damage_type else None
    
    def get_actor_name(self, obj):
        return obj.actor.get_name() if obj.actor else None
    
    def get_target_name(self, obj):
        return obj.target.get_name() if obj.target else None
    
    def get_is_ai(self, obj):
        return obj.actor.participant_type == 'enemy' if obj.actor else False

    def get_is_advantage(self, obj):
        if getattr(obj, 'is_advantage', False):
            return True
        desc = (obj.description or "").lower()
        return ('advantage' in desc and 'disadvantage' not in desc) or ('[pack tactics]' in desc)

    def get_is_disadvantage(self, obj):
        if getattr(obj, 'is_disadvantage', False):
            return True
        desc = (obj.description or "").lower()
        return 'disadvantage' in desc


class CombatParticipantSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for combat participants in list views"""
    name = serializers.SerializerMethodField()

    class Meta:
        model = CombatParticipant
        fields = [
            'id', 'participant_type', 'name', 'initiative',
            'current_hp', 'max_hp', 'armor_class', 'is_active'
        ]

    def get_name(self, obj):
        return obj.get_name()


class CombatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for combat sessions list view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    encounter = EncounterSerializer(read_only=True, allow_null=True)
    participants = CombatParticipantSummarySerializer(many=True, read_only=True)
    gauntlet_run = serializers.SerializerMethodField()

    class Meta:
        model = CombatSession
        fields = [
            'id', 'status', 'status_display', 'is_active', 'current_round',
            'current_turn_index', 'started_at', 'ended_at', 'is_practice',
            'encounter', 'participants', 'gauntlet_run'
        ]

    def get_is_active(self, obj):
        return obj.status == 'active'

    def get_gauntlet_run(self, obj):
        gr = obj.gauntlet_runs.first() if hasattr(obj, 'gauntlet_runs') else None
        if gr:
            return {
                'id': gr.id,
                'name': gr.name,
                'theme': gr.theme,
                'current_wave': gr.current_wave,
                'max_waves': gr.max_waves,
                'status': gr.status,
                'score': gr.score,
                'is_endless': gr.is_endless,
            }
        return None


class EnvironmentalEffectSerializer(serializers.ModelSerializer):
    """Serializer for environmental effects"""
    effect_type_display = serializers.CharField(source='get_effect_type_display', read_only=True)
    terrain_type_display = serializers.CharField(source='get_terrain_type_display', read_only=True, allow_null=True)
    cover_type_display = serializers.CharField(source='get_cover_type_display', read_only=True, allow_null=True)
    lighting_type_display = serializers.CharField(source='get_lighting_type_display', read_only=True, allow_null=True)
    weather_type_display = serializers.CharField(source='get_weather_type_display', read_only=True, allow_null=True)
    hazard_type_display = serializers.CharField(source='get_hazard_type_display', read_only=True, allow_null=True)
    
    class Meta:
        model = EnvironmentalEffect
        fields = '__all__'


class CombatSessionSerializer(serializers.ModelSerializer):
    """Serializer for combat sessions"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    encounter = EncounterSerializer(read_only=True, allow_null=True)
    encounter_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    participants = CombatParticipantSerializer(many=True, read_only=True)
    current_participant = serializers.SerializerMethodField()
    initiative_order = serializers.SerializerMethodField()
    actions = CombatActionSerializer(many=True, read_only=True)
    gauntlet_run = serializers.SerializerMethodField()
    environmental_effects = EnvironmentalEffectSerializer(many=True, read_only=True)
    
    class Meta:
        model = CombatSession
        fields = "__all__"
        read_only_fields = ['created_by']
        
    def get_is_active(self, obj):
        return obj.status == 'active'
    
    def get_current_participant(self, obj):
        current = obj.get_current_participant()
        if current:
            return CombatParticipantSerializer(current).data
        return None
    
    def get_initiative_order(self, obj):
        order = obj.get_initiative_order()
        return CombatParticipantSerializer(order, many=True).data

    def get_gauntlet_run(self, obj):
        gr = obj.gauntlet_runs.first() if hasattr(obj, 'gauntlet_runs') else None
        if gr:
            return {
                'id': gr.id,
                'name': gr.name,
                'theme': gr.theme,
                'current_wave': gr.current_wave,
                'max_waves': gr.max_waves,
                'status': gr.status,
                'score': gr.score,
                'is_endless': gr.is_endless,
            }
        return None


class AttackRequestSerializer(serializers.Serializer):
    """Serializer for attack requests"""
    attacker_id = serializers.IntegerField()
    target_id = serializers.IntegerField(required=False, allow_null=True)
    target_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    attack_name = serializers.CharField(required=False, allow_blank=True)
    advantage = serializers.BooleanField(default=False)
    disadvantage = serializers.BooleanField(default=False)
    dm_override = serializers.BooleanField(default=False)
    inspiration = serializers.BooleanField(default=False)
    other_modifiers = serializers.IntegerField(default=0)
    is_ranged = serializers.BooleanField(required=False, default=None, allow_null=True)
    weapon_slot = serializers.CharField(required=False, default='main_hand', allow_blank=True)
    smite_slot_level = serializers.IntegerField(required=False, allow_null=True)
    use_divine_smite = serializers.BooleanField(required=False, default=False)
    use_sneak_attack = serializers.BooleanField(required=False, default=True)
    use_bardic_inspiration = serializers.BooleanField(required=False, default=False)


class SpellRequestSerializer(serializers.Serializer):
    """Serializer for spell casting requests"""
    caster_id = serializers.IntegerField()
    target_id = serializers.IntegerField(required=False, allow_null=True)
    target_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    spell_name = serializers.CharField()
    spell_level = serializers.IntegerField(required=False, allow_null=True)
    save_type = serializers.CharField(required=False, allow_blank=True)  # STR, DEX, etc.
    save_dc = serializers.IntegerField(required=False, allow_null=True)
    damage_string = serializers.CharField(required=False, allow_blank=True)
    damage_type = serializers.IntegerField(required=False, allow_null=True)  # DamageType ID
    is_healing = serializers.BooleanField(required=False, default=False)
    is_ritual = serializers.BooleanField(required=False, default=False)
    requires_concentration = serializers.BooleanField(required=False, default=False)
    is_bonus_action = serializers.BooleanField(required=False, default=False)
    casting_time = serializers.CharField(required=False, allow_blank=True, default='')
    half_on_save = serializers.BooleanField(required=False, default=True)


class CombatLogSerializer(serializers.ModelSerializer):
    """Serializer for combat logs"""
    combat_session = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = CombatLog
        fields = '__all__'



class ParticipantPositionSerializer(serializers.ModelSerializer):
    """Serializer for participant positions"""
    participant_name = serializers.CharField(source='participant.get_name', read_only=True)
    
    class Meta:
        model = ParticipantPosition
        fields = '__all__'

