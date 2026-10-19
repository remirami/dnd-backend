"""
Environmental Effects System

Handles difficult terrain, cover, lighting, weather, and hazards in combat.
"""


# Difficult Terrain Types
DIFFICULT_TERRAIN_TYPES = {
    'rubble': {'movement_cost_multiplier': 2, 'description': 'Rubble and debris'},
    'mud': {'movement_cost_multiplier': 2, 'description': 'Muddy ground'},
    'snow': {'movement_cost_multiplier': 2, 'description': 'Deep snow'},
    'thick_vegetation': {'movement_cost_multiplier': 2, 'description': 'Thick vegetation'},
    'ice': {'movement_cost_multiplier': 2, 'difficult_balance': True, 'description': 'Icy surface'},
    'swamp': {'movement_cost_multiplier': 2, 'description': 'Swampy ground'},
    'quicksand': {'movement_cost_multiplier': 3, 'description': 'Quicksand'},
}


# Cover Types
COVER_TYPES = {
    'half': {'ac_bonus': 2, 'dex_save_bonus': 2, 'description': 'Half cover (+2 AC, +2 DEX saves)'},
    'three_quarters': {'ac_bonus': 5, 'dex_save_bonus': 5, 'description': 'Three-quarters cover (+5 AC, +5 DEX saves)'},
    'full': {'ac_bonus': None, 'dex_save_bonus': None, 'description': 'Full cover (cannot be targeted directly)'},
}


# Lighting Conditions
LIGHTING_CONDITIONS = {
    'bright_light': {
        'description': 'Bright light (normal vision)',
        'attack_modifier': 0,
        'perception_modifier': 0,
        'stealth_disadvantage': False,
    },
    'dim_light': {
        'description': 'Dim light (lightly obscured)',
        'attack_modifier': 0,
        'perception_modifier': -5,  # Disadvantage on Perception
        'stealth_disadvantage': False,
        'creates_heavily_obscured': False,
    },
    'darkness': {
        'description': 'Darkness (heavily obscured)',
        'attack_modifier': 'disadvantage',  # Disadvantage on attacks
        'perception_modifier': 'disadvantage',  # Disadvantage on Perception
        'stealth_disadvantage': False,
        'creates_heavily_obscured': True,
        'blinded_effect': True,  # Effectively blinded
    },
    'magical_darkness': {
        'description': 'Magical darkness (blocks darkvision)',
        'attack_modifier': 'disadvantage',
        'perception_modifier': 'disadvantage',
        'stealth_disadvantage': False,
        'creates_heavily_obscured': True,
        'blinded_effect': True,
        'blocks_darkvision': True,
    },
}


# Weather Effects
WEATHER_EFFECTS = {
    'clear': {
        'description': 'Clear weather',
        'visibility_modifier': 0,
        'movement_modifier': 0,
        'ranged_attack_modifier': 0,
    },
    'light_rain': {
        'description': 'Light rain',
        'visibility_modifier': -1,  # Slight reduction
        'movement_modifier': 0,
        'ranged_attack_modifier': 0,
    },
    'heavy_rain': {
        'description': 'Heavy rain',
        'visibility_modifier': -5,  # Disadvantage on Perception
        'movement_modifier': 0,
        'ranged_attack_modifier': -2,  # -2 to ranged attacks
        'fire_damage_reduction': 0.5,  # Fire damage reduced
    },
    'fog': {
        'description': 'Fog',
        'visibility_modifier': 'disadvantage',  # Disadvantage on Perception
        'visibility_range': 20,  # Can only see 20 feet
        'movement_modifier': 0,
        'ranged_attack_modifier': 0,
    },
    'heavy_fog': {
        'description': 'Heavy fog',
        'visibility_modifier': 'disadvantage',
        'visibility_range': 10,  # Can only see 10 feet
        'movement_modifier': 0,
        'ranged_attack_modifier': 'disadvantage',
    },
    'snow': {
        'description': 'Snow',
        'visibility_modifier': -2,
        'movement_modifier': 0.5,  # Half movement speed
        'ranged_attack_modifier': -2,
    },
    'strong_wind': {
        'description': 'Strong wind',
        'visibility_modifier': 0,
        'movement_modifier': 0,
        'ranged_attack_modifier': 'disadvantage',  # Disadvantage on ranged attacks
        'flying_difficulty': True,  # Difficult to fly
    },
}


# Hazards
HAZARD_TYPES = {
    'lava': {
        'description': 'Lava',
        'damage_per_round': '6d10',
        'damage_type': 'fire',
        'save_type': 'DEX',
        'save_dc': 15,
        'on_contact': True,
    },
    'acid': {
        'description': 'Acid',
        'damage_per_round': '4d6',
        'damage_type': 'acid',
        'save_type': 'DEX',
        'save_dc': 12,
        'on_contact': True,
    },
    'poison_gas': {
        'description': 'Poison gas',
        'damage_per_round': '2d6',
        'damage_type': 'poison',
        'save_type': 'CON',
        'save_dc': 13,
        'on_contact': True,
        'condition': 'poisoned',
    },
    'spike_pit': {
        'description': 'Spike pit',
        'damage_on_fall': '2d6',
        'damage_type': 'piercing',
        'save_type': 'DEX',
        'save_dc': 15,
        'on_contact': False,
    },
    'electrified_water': {
        'description': 'Electrified water',
        'damage_per_round': '3d6',
        'damage_type': 'lightning',
        'save_type': 'CON',
        'save_dc': 12,
        'on_contact': True,
    },
    'spike_growth': {
        'description': 'Spike Growth',
        'damage_per_5ft': '2d4',
        'damage_type': 'piercing',
        'save_type': None,
        'save_dc': None,
        'on_movement': True,
        'difficult_terrain': True,
    },
    'wall_of_fire': {
        'description': 'Wall of Fire',
        'damage_per_round': '5d8',
        'damage_type': 'fire',
        'save_type': 'DEX',
        'save_dc': 15,
        'on_contact': True,
    },
    'moonbeam': {
        'description': 'Moonbeam',
        'damage_per_round': '2d10',
        'damage_type': 'radiant',
        'save_type': 'CON',
        'save_dc': 15,
        'on_contact': True,
    },
    'cloudkill': {
        'description': 'Cloudkill',
        'damage_per_round': '5d8',
        'damage_type': 'poison',
        'save_type': 'CON',
        'save_dc': 15,
        'on_contact': True,
        'obscured': 'heavily',
    },
}


def calculate_movement_cost(base_movement, terrain_type=None, weather=None, participant=None, hazards=None):
    """
    Calculate movement cost considering terrain, hazards, and weather.
    Land's Stride (Circle of the Land Level 6+): Moving through nonmagical difficult terrain costs no extra movement.
    Spike Growth creates magical difficult terrain that doubles movement cost.
    Returns: (effective_movement, cost_multiplier)
    """
    cost_multiplier = 1.0
    
    # Difficult terrain doubles movement cost (unless participant has Land's Stride on nonmagical terrain)
    if terrain_type and terrain_type in DIFFICULT_TERRAIN_TYPES:
        if not (participant and getattr(participant, 'has_lands_stride', lambda: False)()):
            terrain = DIFFICULT_TERRAIN_TYPES[terrain_type]
            cost_multiplier *= terrain['movement_cost_multiplier']

    # Hazards creating difficult terrain (e.g. Spike Growth)
    if hazards:
        for h in hazards:
            if h in HAZARD_TYPES and HAZARD_TYPES[h].get('difficult_terrain'):
                cost_multiplier *= 2
                break

    # Weather effects
    if weather and weather in WEATHER_EFFECTS:
        weather_effect = WEATHER_EFFECTS[weather]
        if 'movement_modifier' in weather_effect:
            if isinstance(weather_effect['movement_modifier'], (int, float)):
                if weather_effect['movement_modifier'] < 1:
                    cost_multiplier /= weather_effect['movement_modifier']
    
    effective_movement = int(base_movement / cost_multiplier)
    
    return effective_movement, cost_multiplier


def resolve_movement_hazards(participant, distance_moved: int, hazards: list) -> tuple[int, list]:
    """
    Resolve damage and saving throws for hazards triggered during movement.
    - spike_growth: 2d4 piercing per 5 ft moved.
    - wall_of_fire, moonbeam, cloudkill, lava, acid: saving throw on contact.
    Returns: (total_damage, list_of_report_messages)
    """
    import random
    from combat.utils import calculate_saving_throw, roll_d20

    if not hazards or distance_moved <= 0:
        return 0, []

    total_damage = 0
    reports = []

    for hazard_name in hazards:
        if hazard_name not in HAZARD_TYPES:
            continue
        hazard = HAZARD_TYPES[hazard_name]

        # Spike Growth: 2d4 piercing for every 5 feet moved through it
        if hazard_name == 'spike_growth':
            five_foot_increments = max(1, distance_moved // 5)
            spike_dmg = sum(random.randint(1, 4) + random.randint(1, 4) for _ in range(five_foot_increments))
            if spike_dmg > 0:
                _new_hp, _ = participant.take_damage(spike_dmg, damage_type='piercing')
                total_damage += spike_dmg
                reports.append(
                    f"🌿 Spike Growth: Took {spike_dmg} piercing damage ({five_foot_increments}x 2d4 for {distance_moved} ft moved)!"
                )
            continue

        # Contact / area hazards
        damage_dice = hazard.get('damage_per_round')
        dtype = hazard.get('damage_type')
        save_type = hazard.get('save_type')
        save_dc = hazard.get('save_dc', 15)

        if damage_dice and dtype:
            from combat.utils import calculate_damage
            base_dmg, _ = calculate_damage(damage_dice, 0, False)
            if save_type:
                save_roll, _ = roll_d20()
                con_or_dex_mod = participant.get_ability_modifier(save_type)
                prof = False
                if participant.character and hasattr(participant.character, 'saving_throw_proficiencies') and participant.character.saving_throw_proficiencies:
                    prof = save_type.lower() in [s.lower() for s in participant.character.saving_throw_proficiencies]
                prof_bonus = participant.character.proficiency_bonus if participant.character else 2
                aura_bonus = getattr(participant, 'get_aura_of_protection_bonus', lambda: 0)()
                save_total, _ = calculate_saving_throw(save_roll, con_or_dex_mod, prof_bonus, prof, other_modifiers=aura_bonus)
                if save_total >= save_dc:
                    actual_dmg = base_dmg // 2
                    res_str = f"succeeded {save_type} save ({save_total} vs DC {save_dc}, half damage: {actual_dmg})"
                else:
                    actual_dmg = base_dmg
                    res_str = f"failed {save_type} save ({save_total} vs DC {save_dc}, full damage: {actual_dmg})"
            else:
                actual_dmg = base_dmg
                res_str = f"took {actual_dmg} damage"

            _new_hp, _ = participant.take_damage(actual_dmg, damage_type=dtype)
            total_damage += actual_dmg
            reports.append(f"⚠️ {hazard['description']}: {participant.get_name()} {res_str}!")

    return total_damage, reports


def calculate_cover_ac_bonus(cover_type):
    """Calculate AC bonus from cover"""
    if cover_type and cover_type in COVER_TYPES:
        return COVER_TYPES[cover_type].get('ac_bonus', 0)
    return 0


def calculate_cover_save_bonus(cover_type):
    """Calculate DEX save bonus from cover"""
    if cover_type and cover_type in COVER_TYPES:
        return COVER_TYPES[cover_type].get('dex_save_bonus', 0)
    return 0


def has_full_cover(cover_type):
    """Check if cover provides full cover (cannot be targeted)"""
    return cover_type == 'full'


def get_lighting_attack_modifier(lighting, has_darkvision=False, has_devils_sight=False):
    """
    Get attack modifier from lighting conditions.
    Returns: 'advantage', 'disadvantage', or 0
    Devil's Sight allows seeing normally in both nonmagical and magical darkness.
    """
    if not lighting or lighting not in LIGHTING_CONDITIONS:
        return 0

    if has_devils_sight and lighting in ['darkness', 'magical_darkness']:
        return 0

    lighting_effect = LIGHTING_CONDITIONS[lighting]
    
    # Darkvision can see in darkness (but not magical darkness)
    if lighting == 'darkness' and has_darkvision:
        return 0
    
    if lighting == 'magical_darkness':
        return 'disadvantage'  # Even darkvision doesn't help
    
    modifier = lighting_effect.get('attack_modifier', 0)
    
    if modifier == 'disadvantage':
        return 'disadvantage'
    elif modifier == 'advantage':
        return 'advantage'
    
    return 0


def get_lighting_perception_modifier(lighting, has_darkvision=False, has_devils_sight=False):
    """
    Get perception modifier from lighting conditions.
    Returns: modifier value or 'disadvantage'
    """
    if not lighting or lighting not in LIGHTING_CONDITIONS:
        return 0

    if has_devils_sight and lighting in ['darkness', 'magical_darkness']:
        return 0
    
    lighting_effect = LIGHTING_CONDITIONS[lighting]
    
    # Darkvision can see in darkness (but not magical darkness)
    if lighting == 'darkness' and has_darkvision:
        return 0
    
    if lighting == 'magical_darkness':
        return 'disadvantage'  # Even darkvision doesn't help
    
    modifier = lighting_effect.get('perception_modifier', 0)
    
    if modifier == 'disadvantage':
        return 'disadvantage'
    
    return modifier


def get_weather_ranged_modifier(weather):
    """Get ranged attack modifier from weather"""
    if not weather or weather not in WEATHER_EFFECTS:
        return 0
    
    weather_effect = WEATHER_EFFECTS[weather]
    modifier = weather_effect.get('ranged_attack_modifier', 0)
    
    if modifier == 'disadvantage':
        return 'disadvantage'
    elif modifier == 'advantage':
        return 'advantage'
    
    return modifier


def calculate_hazard_damage(hazard_type, rounds_exposed=1):
    """
    Calculate damage from hazard exposure.
    Returns: (damage_dice, damage_type, save_type, save_dc, condition)
    """
    if hazard_type not in HAZARD_TYPES:
        return None, None, None, None, None
    
    hazard = HAZARD_TYPES[hazard_type]
    
    damage_dice = hazard.get('damage_per_round', hazard.get('damage_on_fall'))
    damage_type = hazard.get('damage_type')
    save_type = hazard.get('save_type')
    save_dc = hazard.get('save_dc')
    condition = hazard.get('condition')
    
    return damage_dice, damage_type, save_type, save_dc, condition


def can_see_target(attacker_lighting, target_lighting, attacker_darkvision=False, target_distance=0, has_devils_sight=False):
    """
    Check if attacker can see target based on lighting and distance.
    Returns: (can_see, reason)
    """
    # Check for full cover (handled separately)
    
    # Check lighting
    if attacker_lighting == 'magical_darkness':
        if has_devils_sight and (target_distance <= 120):
            return True, None
        return False, "Magical darkness blocks vision"
    
    if attacker_lighting == 'darkness':
        if has_devils_sight and (target_distance <= 120):
            return True, None
        if not attacker_darkvision:
            return False, "Cannot see in darkness without darkvision"
    
    # Check weather visibility range
    # This would need weather context
    
    return True, None


def get_environmental_effects_summary(terrain=None, cover=None, lighting=None, weather=None, hazards=None):
    """Get a summary of all environmental effects"""
    effects = {
        'terrain': None,
        'cover': None,
        'lighting': None,
        'weather': None,
        'hazards': [],
    }
    
    if terrain and terrain in DIFFICULT_TERRAIN_TYPES:
        effects['terrain'] = {
            'type': terrain,
            'description': DIFFICULT_TERRAIN_TYPES[terrain]['description'],
            'movement_cost_multiplier': DIFFICULT_TERRAIN_TYPES[terrain]['movement_cost_multiplier'],
        }
    
    if cover and cover in COVER_TYPES:
        effects['cover'] = {
            'type': cover,
            'description': COVER_TYPES[cover]['description'],
            'ac_bonus': COVER_TYPES[cover].get('ac_bonus'),
            'dex_save_bonus': COVER_TYPES[cover].get('dex_save_bonus'),
        }
    
    if lighting and lighting in LIGHTING_CONDITIONS:
        effects['lighting'] = {
            'type': lighting,
            'description': LIGHTING_CONDITIONS[lighting]['description'],
            'attack_modifier': LIGHTING_CONDITIONS[lighting].get('attack_modifier', 0),
            'perception_modifier': LIGHTING_CONDITIONS[lighting].get('perception_modifier', 0),
        }
    
    if weather and weather in WEATHER_EFFECTS:
        effects['weather'] = {
            'type': weather,
            'description': WEATHER_EFFECTS[weather]['description'],
            'ranged_attack_modifier': WEATHER_EFFECTS[weather].get('ranged_attack_modifier', 0),
            'visibility_modifier': WEATHER_EFFECTS[weather].get('visibility_modifier', 0),
        }
    
    if hazards:
        for hazard in hazards:
            if hazard in HAZARD_TYPES:
                effects['hazards'].append({
                    'type': hazard,
                    'description': HAZARD_TYPES[hazard]['description'],
                    'damage': HAZARD_TYPES[hazard].get('damage_per_round') or HAZARD_TYPES[hazard].get('damage_on_fall'),
                })
    
    return effects

