"""
Utility functions for campaign roguelite features
"""
import random
from django.db import transaction


# D&D 5e Spell Slot Tables
# Format: {class_name: {level: {slot_level: count}}}
SPELL_SLOT_TABLES = {
    # Full Casters (Cleric, Druid, Wizard, Sorcerer, Bard)
    'cleric': {
        1: {'1': 2}, 2: {'1': 3}, 3: {'1': 4, '2': 2}, 4: {'1': 4, '2': 3},
        5: {'1': 4, '2': 3, '3': 2}, 6: {'1': 4, '2': 3, '3': 3}, 7: {'1': 4, '2': 3, '3': 3, '4': 1},
        8: {'1': 4, '2': 3, '3': 3, '4': 2}, 9: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 1},
        10: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2}, 11: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1},
        12: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1}, 13: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1},
        14: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1}, 15: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1, '8': 1},
        16: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1, '8': 1}, 17: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2, '6': 1, '7': 1, '8': 1, '9': 1},
        18: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 3, '6': 1, '7': 1, '8': 1, '9': 1}, 19: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 3, '6': 2, '7': 1, '8': 1, '9': 1},
        20: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 3, '6': 2, '7': 2, '8': 1, '9': 1},
    },
    'druid': {},  # Same as cleric
    'wizard': {},  # Same as cleric
    'sorcerer': {},  # Same as cleric
    'bard': {},  # Same as cleric
    
    # Paladin (Half Caster)
    'paladin': {
        1: {}, 2: {'1': 2}, 3: {'1': 3}, 4: {'1': 3}, 5: {'1': 4, '2': 2},
        6: {'1': 4, '2': 2}, 7: {'1': 4, '2': 3}, 8: {'1': 4, '2': 3}, 9: {'1': 4, '2': 3, '3': 2},
        10: {'1': 4, '2': 3, '3': 2}, 11: {'1': 4, '2': 3, '3': 3}, 12: {'1': 4, '2': 3, '3': 3}, 13: {'1': 4, '2': 3, '3': 3, '4': 1},
        14: {'1': 4, '2': 3, '3': 3, '4': 1}, 15: {'1': 4, '2': 3, '3': 3, '4': 2}, 16: {'1': 4, '2': 3, '3': 3, '4': 2}, 17: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 1},
        18: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 1}, 19: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2}, 20: {'1': 4, '2': 3, '3': 3, '4': 3, '5': 2},
    },
    'ranger': {},  # Same as paladin
}

# Fill in missing classes with cleric table (full casters) or paladin table (half casters)
for cls in ['druid', 'wizard', 'sorcerer', 'bard']:
    SPELL_SLOT_TABLES[cls] = SPELL_SLOT_TABLES['cleric'].copy()
SPELL_SLOT_TABLES['ranger'] = SPELL_SLOT_TABLES['paladin'].copy()

# Warlock has different spell slot system (patron slots)
# For simplicity, we'll use a modified version
SPELL_SLOT_TABLES['warlock'] = {
    1: {'1': 1}, 2: {'1': 2}, 3: {'2': 2}, 4: {'2': 2}, 5: {'3': 2},
    6: {'3': 2}, 7: {'4': 2}, 8: {'4': 2}, 9: {'5': 2}, 10: {'5': 2},
    11: {'5': 3}, 12: {'5': 3}, 13: {'5': 3}, 14: {'5': 3}, 15: {'5': 3},
    16: {'5': 3}, 17: {'5': 4}, 18: {'5': 4}, 19: {'5': 4}, 20: {'5': 4},
}


def calculate_spell_slots(character_class_name, level):
    """
    Calculate spell slots for a character based on class and level
    
    Args:
        character_class_name: Name of the character class (e.g., 'wizard', 'fighter')
        level: Character level
        
    Returns:
        dict: Spell slots by level (e.g., {'1': 2, '2': 1})
    """
    # Non-spellcasting classes
    non_casters = ['fighter', 'rogue', 'barbarian', 'monk']
    
    if character_class_name in non_casters:
        return {}
    
    # Get spell slot table for this class
    table = SPELL_SLOT_TABLES.get(character_class_name, {})
    
    # Find the appropriate level (cap at 20)
    level = min(level, 20)
    
    # Get slots for this level, or closest lower level
    slots = {}
    for lvl in range(level, 0, -1):
        if lvl in table:
            slots = table[lvl].copy()
            break
    
    return slots


def calculate_spell_save_dc(character, ability_score):
    """Calculate spell save DC: 8 + proficiency bonus + ability modifier"""
    proficiency_bonus = character.proficiency_bonus
    
    # Get ability modifier
    if hasattr(character, 'stats'):
        stats = character.stats
        if ability_score.lower() == 'int':
            ability_mod = stats.intelligence_modifier
        elif ability_score.lower() == 'wis':
            ability_mod = stats.wisdom_modifier
        elif ability_score.lower() == 'cha':
            ability_mod = stats.charisma_modifier
        else:
            ability_mod = 0
    else:
        ability_mod = 0
    
    return 8 + proficiency_bonus + ability_mod


def calculate_spell_attack_bonus(character, ability_score):
    """Calculate spell attack bonus: proficiency bonus + ability modifier"""
    proficiency_bonus = character.proficiency_bonus
    
    # Get ability modifier
    if hasattr(character, 'stats'):
        stats = character.stats
        if ability_score.lower() == 'int':
            ability_mod = stats.intelligence_modifier
        elif ability_score.lower() == 'wis':
            ability_mod = stats.wisdom_modifier
        elif ability_score.lower() == 'cha':
            ability_mod = stats.charisma_modifier
        else:
            ability_mod = 0
    else:
        ability_mod = 0
    
    return proficiency_bonus + ability_mod


def get_spellcasting_ability(character_class_name):
    """Get the spellcasting ability for a class"""
    spellcasting_abilities = {
        'wizard': 'INT',
        'sorcerer': 'CHA',
        'warlock': 'CHA',
        'cleric': 'WIS',
        'druid': 'WIS',
        'ranger': 'WIS',
        'paladin': 'CHA',
        'bard': 'CHA',
    }
    return spellcasting_abilities.get(character_class_name, None)


# XP values by Challenge Rating (D&D 5e)
CR_TO_XP = {
    "0": 0,
    "1/8": 25,
    "1/4": 50,
    "1/2": 100,
    "1": 200,
    "2": 450,
    "3": 700,
    "4": 1100,
    "5": 1800,
    "6": 2300,
    "7": 2900,
    "8": 3900,
    "9": 5000,
    "10": 5900,
    "11": 7200,
    "12": 8400,
    "13": 10000,
    "14": 11500,
    "15": 13000,
    "16": 15000,
    "17": 18000,
    "18": 20000,
    "19": 22000,
    "20": 25000,
    "21": 33000,
    "22": 41000,
    "23": 50000,
    "24": 62000,
    "30": 155000,
}


def calculate_xp_reward(enemy, character_level):
    """
    Calculate XP reward for defeating an enemy
    
    Args:
        enemy: Enemy object with challenge_rating
        character_level: Level of the character gaining XP
    
    Returns:
        int: XP amount
    """
    # Handle None or blank challenge_rating
    if not enemy.challenge_rating:
        # Default to CR 1/2 if no CR specified
        cr = "1/2"
    else:
        cr = str(enemy.challenge_rating).strip()
    
    base_xp = CR_TO_XP.get(cr, 0)
    
    if base_xp == 0:
        # Fallback: estimate based on HP (very rough)
        # 10 HP ≈ CR 1/4, 20 HP ≈ CR 1/2, etc.
        if hasattr(enemy, 'hp') and enemy.hp:
            estimated_cr = max(1, enemy.hp // 10)
            base_xp = CR_TO_XP.get(str(estimated_cr), 50)  # Default to 50 XP
        else:
            return 50  # Default minimum XP
    
    # Convert CR to effective level for comparison
    # Simple mapping for common CRs
    cr_to_level_map = {
        "1/8": 1, "1/4": 1, "1/2": 1,
        "1": 2, "2": 3, "3": 4, "4": 5,
        "5": 6, "6": 7, "7": 8, "8": 9,
        "9": 10, "10": 11, "11": 12, "12": 13,
    }
    
    effective_enemy_level = cr_to_level_map.get(cr, 5)
    level_diff = effective_enemy_level - character_level
    
    # Adjust XP based on level difference
    if level_diff > 0:
        # Higher CR = more XP
        multiplier = 1.0 + (level_diff * 0.1)
    elif level_diff < 0:
        # Lower CR = less XP (but never zero)
        multiplier = max(0.5, 1.0 + (level_diff * 0.05))
    else:
        multiplier = 1.0
    
    return int(base_xp * multiplier)


def grant_encounter_xp(campaign_encounter, campaign_characters):
    """
    Grant XP to all characters in an encounter
    
    Args:
        campaign_encounter: CampaignEncounter object
        campaign_characters: QuerySet of CampaignCharacter objects
    
    Returns:
        dict: Results of XP granting
    """
    from .models import CharacterXP
    from encounters.models import EncounterEnemy
    
    results = {
        'characters': [],
        'total_xp_granted': 0,
        'levels_gained': 0
    }
    
    # Get all enemies from the encounter
    encounter_enemies = EncounterEnemy.objects.filter(
        encounter=campaign_encounter.encounter
    )
    
    if not encounter_enemies.exists():
        return results
    
    # Calculate total XP pool from all enemies
    total_xp_pool = 0
    for encounter_enemy in encounter_enemies:
        enemy = encounter_enemy.enemy
        # Use average party level for XP calculation
        avg_party_level = sum([cc.character.level for cc in campaign_characters]) // max(1, campaign_characters.count())
        xp_per_enemy = calculate_xp_reward(enemy, avg_party_level)
        total_xp_pool += xp_per_enemy * encounter_enemy.quantity
    
    # Distribute XP evenly among alive characters
    alive_characters = [cc for cc in campaign_characters if cc.is_alive]
    
    if not alive_characters:
        return results
    
    xp_per_character = total_xp_pool // len(alive_characters)
    
    # Grant XP to each character
    with transaction.atomic():
        for campaign_char in alive_characters:
            xp_tracking, created = CharacterXP.objects.get_or_create(
                campaign_character=campaign_char
            )
            
            old_level = campaign_char.character.level
            result = xp_tracking.add_xp(xp_per_character, source="encounter_completion")
            new_level = campaign_char.character.level
            
            level_gained = new_level > old_level
            if level_gained:
                results['levels_gained'] += (new_level - old_level)
            
            results['characters'].append({
                'character_id': campaign_char.id,
                'character_name': campaign_char.character.name,
                'xp_gained': xp_per_character,
                'total_xp': xp_tracking.current_xp,
                'level': new_level,
                'level_gained': level_gained,
            })
            
            results['total_xp_granted'] += xp_per_character
    
    return results


class TreasureGenerator:
    """Generates treasure rooms for campaigns"""
    
    @staticmethod
    def generate_treasure_room(campaign, encounter_number):
        """
        Generate a treasure room after an encounter
        
        Args:
            campaign: Campaign object
            encounter_number: After which encounter this appears
        
        Returns:
            TreasureRoom object
        """
        from .models import TreasureRoom
        from items.models import Item, ItemCategory
        
        # Determine room type (weighted random)
        room_type = TreasureGenerator._select_room_type(encounter_number, campaign.total_encounters)
        
        # Calculate treasure value based on progress
        treasure_value = TreasureGenerator._calculate_treasure_value(campaign, encounter_number)
        
        rewards = {
            'items': [],
            'gold': 0,
            'xp_bonus': 0
        }
        
        if room_type == 'equipment':
            # Generate equipment items
            equipment_items = list(Item.objects.filter(
                category__name__in=['Weapon', 'Armor', 'Shield']
            ).order_by('?')[:random.randint(1, 2)])
            
            if equipment_items:
                rewards['items'] = [
                    {'item_id': item.id, 'quantity': 1, 'name': item.name}
                    for item in equipment_items
                ]
            rewards['gold'] = random.randint(10, 50)
            
        elif room_type == 'consumables':
            # Generate consumable items
            consumables = list(Item.objects.filter(
                category__name='Consumable'
            ).order_by('?')[:random.randint(2, 4)])
            
            if consumables:
                rewards['items'] = [
                    {'item_id': item.id, 'quantity': random.randint(1, 3), 'name': item.name}
                    for item in consumables
                ]
            rewards['gold'] = random.randint(5, 30)
            
        elif room_type == 'gold':
            # Large gold reward
            base_gold = treasure_value * 10
            rewards['gold'] = random.randint(int(base_gold * 0.8), int(base_gold * 1.2))
            
        elif room_type == 'magical':
            # Guaranteed magic item (if available)
            magic_items = list(Item.objects.filter(
                category__name='Magic Item'
            ).order_by('?')[:1])
            
            if magic_items:
                item = magic_items[0]
                rewards['items'] = [
                    {'item_id': item.id, 'quantity': 1, 'name': item.name}
                ]
            else:
                # Fallback to equipment if no magic items
                equipment_fallback = list(Item.objects.filter(
                    category__name__in=['Weapon', 'Armor']
                ).order_by('?')[:1])
                if equipment_fallback:
                    rewards['items'] = [
                        {'item_id': item.id, 'quantity': 1, 'name': item.name}
                        for item in equipment_fallback
                    ]
            
            rewards['gold'] = random.randint(50, 100)
            
        elif room_type == 'mystery':
            # Random mix
            mystery_type = random.choice(['items', 'gold', 'xp'])
            
            if mystery_type == 'items':
                all_items = list(Item.objects.all().order_by('?')[:random.randint(1, 3)])
                if all_items:
                    rewards['items'] = [
                        {'item_id': item.id, 'quantity': random.randint(1, 2), 'name': item.name}
                        for item in all_items
                    ]
            elif mystery_type == 'gold':
                rewards['gold'] = random.randint(30, 150)
            else:  # xp
                rewards['xp_bonus'] = random.randint(50, 200)
                rewards['gold'] = random.randint(20, 60)
        
        # Always give a small XP bonus
        if rewards['xp_bonus'] == 0:
            rewards['xp_bonus'] = random.randint(10, 50)
        
        treasure_room = TreasureRoom.objects.create(
            campaign=campaign,
            encounter_number=encounter_number,
            room_type=room_type,
            rewards=rewards  # Keep JSON for backward compatibility
        )
        
        # Create individual reward entries for per-character claiming
        from .models import TreasureRoomReward
        from items.models import Item
        
        # Create item rewards
        for item_data in rewards.get('items', []):
            try:
                item = Item.objects.get(pk=item_data['item_id'])
                TreasureRoomReward.objects.create(
                    treasure_room=treasure_room,
                    item=item,
                    quantity=item_data.get('quantity', 1)
                )
            except Item.DoesNotExist:
                pass  # Skip if item doesn't exist
        
        # Create gold rewards (split into individual rewards if multiple, or single if small)
        gold_total = rewards.get('gold', 0)
        if gold_total > 0:
            # Split gold into 1-3 rewards
            num_gold_rewards = min(3, max(1, gold_total // 50))
            gold_per_reward = gold_total // num_gold_rewards
            remainder = gold_total % num_gold_rewards
            
            for i in range(num_gold_rewards):
                gold_amount = gold_per_reward + (remainder if i == num_gold_rewards - 1 else 0)
                if gold_amount > 0:
                    TreasureRoomReward.objects.create(
                        treasure_room=treasure_room,
                        gold_amount=gold_amount
                    )
        
        # Create XP bonus rewards (one per character or split)
        xp_bonus = rewards.get('xp_bonus', 0)
        if xp_bonus > 0:
            TreasureRoomReward.objects.create(
                treasure_room=treasure_room,
                xp_bonus=xp_bonus
            )
        
        return treasure_room
    
    @staticmethod
    def _select_room_type(encounter_number, total_encounters):
        """Select treasure room type with weighted probabilities"""
        # Early encounters: more consumables and gold
        # Late encounters: more equipment and magic items
        
        progress = encounter_number / max(1, total_encounters)
        
        if progress < 0.3:  # Early game
            weights = {
                'consumables': 0.4,
                'gold': 0.3,
                'equipment': 0.2,
                'magical': 0.05,
                'mystery': 0.05,
            }
        elif progress < 0.7:  # Mid game
            weights = {
                'equipment': 0.3,
                'consumables': 0.25,
                'gold': 0.25,
                'magical': 0.1,
                'mystery': 0.1,
            }
        else:  # Late game
            weights = {
                'magical': 0.35,
                'equipment': 0.3,
                'gold': 0.15,
                'consumables': 0.1,
                'mystery': 0.1,
            }
        
        # Select based on weights
        room_types = list(weights.keys())
        probabilities = list(weights.values())
        return random.choices(room_types, weights=probabilities)[0]
    
    @staticmethod
    def _calculate_treasure_value(campaign, encounter_number):
        """Calculate appropriate treasure value"""
        base_value = encounter_number * 50
        level_multiplier = campaign.starting_level * 25
        return base_value + level_multiplier


class RecruitmentGenerator:
    """Generates recruitment rooms and recruits characters for solo campaigns"""
    
    @staticmethod
    def generate_recruitment_room(campaign, encounter_number):
        """
        Generate a recruitment room after an encounter (solo mode only)
        
        Args:
            campaign: Campaign object (must be in solo mode)
            encounter_number: After which encounter this appears
        
        Returns:
            RecruitmentRoom object
        """
        from .models import RecruitmentRoom, RecruitableCharacter
        
        if campaign.start_mode != 'solo':
            raise ValueError("Recruitment rooms are only available in solo mode")
        
        # Check current party size (max 4 total in solo mode)
        current_party_size = campaign.get_alive_characters().count()
        if current_party_size >= 4:
            raise ValueError("Party is already at maximum size (4). Cannot recruit more characters.")
        
        # Determine rarity weights based on progress
        rarity_weights = RecruitmentGenerator._calculate_rarity_weights(encounter_number, campaign.total_encounters)
        
        # Select 2-3 recruits based on rarity weights
        # Start with common/uncommon for early game, allow rare/legendary later
        available_rarities = []
        if random.random() < rarity_weights.get('legendary', 0):
            available_rarities.append('legendary')
        if random.random() < rarity_weights.get('rare', 0):
            available_rarities.append('rare')
        if random.random() < rarity_weights.get('uncommon', 0.5):
            available_rarities.append('uncommon')
        available_rarities.append('common')  # Always include common as fallback
        
        # Get recruits from available rarities
        recruits = RecruitableCharacter.objects.filter(
            rarity__in=available_rarities
        ).order_by('?')[:3]
        
        # If we don't have enough recruits, fill with any available
        if recruits.count() < 2:
            additional = RecruitableCharacter.objects.exclude(
                id__in=[r.id for r in recruits]
            ).order_by('?')[:2]
            recruits = list(recruits) + list(additional)
        
        # Create recruitment room
        room = RecruitmentRoom.objects.create(
            campaign=campaign,
            encounter_number=encounter_number
        )
        room.available_recruits.set(recruits[:3])  # Limit to 3 options
        
        return room
    
    @staticmethod
    def _calculate_rarity_weights(encounter_number, total_encounters):
        """Calculate rarity weights based on campaign progress"""
        progress = encounter_number / max(1, total_encounters)
        
        if progress < 0.3:  # Early game
            return {
                'common': 0.6,
                'uncommon': 0.35,
                'rare': 0.05,
                'legendary': 0.0,
            }
        elif progress < 0.7:  # Mid game
            return {
                'common': 0.4,
                'uncommon': 0.4,
                'rare': 0.15,
                'legendary': 0.05,
            }
        else:  # Late game
            return {
                'common': 0.2,
                'uncommon': 0.4,
                'rare': 0.3,
                'legendary': 0.1,
            }
    
    @staticmethod
    def recruit_character(campaign, recruitment_room, recruit_template):
        """
        Recruit a character into the campaign from a recruitment room
        
        Args:
            campaign: Campaign object
            recruitment_room: RecruitmentRoom object
            recruit_template: RecruitableCharacter object
        
        Returns:
            CampaignCharacter object
        """
        from characters.models import Character, CharacterStats
        
        if campaign.start_mode != 'solo':
            raise ValueError("Recruitment is only available in solo mode")
        
        # Check party size limit
        current_party_size = campaign.get_alive_characters().count()
        if current_party_size >= 4:
            raise ValueError("Party is already at maximum size (4). Cannot recruit more characters.")
        
        # Calculate recruit level (scale to current campaign level, not starting level)
        # Use average party level if party exists, otherwise use campaign starting level
        if current_party_size > 0:
            party_levels = [cc.character.level for cc in campaign.get_alive_characters()]
            recruit_level = sum(party_levels) // len(party_levels)
        else:
            recruit_level = campaign.starting_level
        
        # Create character from template
        character = Character.objects.create(
            name=recruit_template.name,
            level=recruit_level,
            character_class=recruit_template.character_class,
            race=recruit_template.race,
            background=recruit_template.background,
            user=campaign.owner  # Recruited characters belong to campaign owner
        )
        
        # Initialize stats
        # Use starting_stats from template if provided, otherwise use defaults
        if recruit_template.starting_stats:
            stats_data = recruit_template.starting_stats.copy()
        else:
            # Default stats: 15, 14, 13, 12, 10, 8 distributed based on class
            default_stats = {
                'strength': 10,
                'dexterity': 10,
                'constitution': 10,
                'intelligence': 10,
                'wisdom': 10,
                'charisma': 10,
            }
            # This is simplified - in a full implementation, you'd assign stats based on class
            # For now, we'll use basic defaults
            stats_data = default_stats
        
        # Create CharacterStats with proper HP calculation
        con_score = stats_data.get('constitution', 10)
        from core.dnd_utils import calculate_ability_modifier
        con_mod = calculate_ability_modifier(con_score)
        
        # Calculate HP based on level and hit dice type
        # Get hit dice type (e.g., "d8" or "1d8")
        hit_dice_type = recruit_template.character_class.hit_dice
        if 'd' in hit_dice_type:
            die_part = hit_dice_type.split('d')[-1]
            die_size = int(die_part)
        else:
            die_size = 8  # Default fallback
        
        # Calculate HP: first level gets max die + CON, subsequent levels get average + CON
        first_level_hp = die_size + con_mod
        additional_levels_hp = (recruit_level - 1) * (die_size // 2 + 1 + con_mod)  # Average rounded up + CON
        total_hp = max(1, first_level_hp + additional_levels_hp)
        
        # Calculate AC (10 + DEX mod, simplified - no armor)
        dex_score = stats_data.get('dexterity', 10)
        from core.dnd_utils import calculate_ability_modifier
        dex_mod = calculate_ability_modifier(dex_score)
        base_ac = 10 + dex_mod
        
        stats = CharacterStats.objects.create(
            character=character,
            strength=stats_data.get('strength', 10),
            dexterity=dex_score,
            constitution=con_score,
            intelligence=stats_data.get('intelligence', 10),
            wisdom=stats_data.get('wisdom', 10),
            charisma=stats_data.get('charisma', 10),
            hit_points=total_hp,
            max_hit_points=total_hp,
            armor_class=base_ac,
            speed=character.race.speed,
        )
        
        # Create CampaignCharacter
        from .models import CampaignCharacter, CharacterXP
        campaign_char = CampaignCharacter.objects.create(
            campaign=campaign,
            character=character
        )
        campaign_char.initialize_from_character()
        
        # Track recruitment
        recruitment_room.recruit_selected = campaign_char
        recruitment_room.save()
        
        return campaign_char


class CampaignGenerator:
    """Generates random encounters and treasures for campaign auto-population"""
    
    @staticmethod
    def populate_campaign(campaign, num_encounters=5, auto_treasure=True):
        """
        Populate a campaign with random encounters and treasure rooms
        
        Args:
            campaign: Campaign object
            num_encounters: Number of encounters to generate (default: 5)
            auto_treasure: Whether to auto-generate treasure rooms (default: True)
        
        Returns:
            dict: Summary of what was created
        """
        from .models import CampaignEncounter, TreasureRoom
        from encounters.models import Encounter, EncounterEnemy
        from bestiary.models import Enemy, EnemyStats
        
        summary = {
            'encounters_created': 0,
            'treasure_rooms_created': 0,
            'errors': []
        }
        
        # Get available enemies
        enemies = Enemy.objects.all()
        if not enemies.exists():
            summary['errors'].append("No enemies found in database. Please import enemies first.")
            return summary
        
        # Generate encounters
        for i in range(1, num_encounters + 1):
            try:
                # Create encounter
                encounter = Encounter.objects.create(
                    name=f"Random Encounter {i}",
                    description=f"Auto-generated encounter {i} for {campaign.name}",
                    location="Random Location"
                )
                
                # Select random enemies (1-4 enemies per encounter, scaling with encounter number)
                num_enemies = random.randint(1, min(4, 1 + (i // 2)))
                selected_enemies = list(enemies.order_by('?')[:num_enemies])
                
                # If we have fewer enemies than needed, use what we have
                if len(selected_enemies) < num_enemies:
                    selected_enemies = list(enemies.order_by('?'))
                
                # Add enemies to encounter
                for j, enemy in enumerate(selected_enemies[:num_enemies]):
                    # Get enemy HP from stats if available
                    hp = 10  # Default
                    if hasattr(enemy, 'stats') and enemy.stats.hit_points:
                        hp = enemy.stats.hit_points
                    elif enemy.hp:
                        hp = enemy.hp
                    
                    EncounterEnemy.objects.create(
                        encounter=encounter,
                        enemy=enemy,
                        name=f"{enemy.name} {j+1}",
                        current_hp=hp,
                        initiative=0,
                        is_alive=True
                    )
                
                # Create campaign encounter
                CampaignEncounter.objects.create(
                    campaign=campaign,
                    encounter=encounter,
                    encounter_number=i
                )
                
                summary['encounters_created'] += 1
                
                # Generate treasure room (every 2-3 encounters or random 30% chance)
                if auto_treasure and (i % 3 == 0 or random.random() < 0.3):
                    try:
                        treasure_room = TreasureGenerator.generate_treasure_room(
                            campaign,
                            i
                        )
                        summary['treasure_rooms_created'] += 1
                    except Exception as e:
                        summary['errors'].append(f"Failed to create treasure room for encounter {i}: {str(e)}")
                
            except Exception as e:
                summary['errors'].append(f"Failed to create encounter {i}: {str(e)}")
        
        # Update campaign total_encounters
        campaign.total_encounters = campaign.campaign_encounters.count()
        campaign.save()
        
        return summary