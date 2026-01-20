"""
Inventory Management Utilities

Handles equipment, weight tracking, and item effects.
"""

from .models import Character, CharacterItem
from items.models import Item, Weapon, Armor


# Encumbrance thresholds (in pounds)
ENCUMBRANCE_THRESHOLDS = {
    'light': 0,  # No penalty
    'medium': None,  # Calculated as STR * 5
    'heavy': None,  # Calculated as STR * 10
    'overloaded': None,  # Calculated as STR * 15
}


def calculate_carrying_capacity(character):
    """
    Calculate carrying capacity based on STR score.
    Returns dict with thresholds.
    """
    if not character.stats:
        return {}
    
    strength = character.stats.strength
    
    # Base capacity: STR * 15 pounds
    # Medium load: STR * 5
    # Heavy load: STR * 10
    # Maximum: STR * 15
    
    return {
        'light': 0,
        'medium': strength * 5,
        'heavy': strength * 10,
        'maximum': strength * 15,
    }


def calculate_total_weight(character):
    """Calculate total weight of all items in inventory"""
    items = CharacterItem.objects.filter(character=character)
    total_weight = 0
    
    for char_item in items:
        item_weight = char_item.item.weight or 0
        total_weight += float(item_weight) * char_item.quantity
    
    return total_weight


def get_encumbrance_level(character):
    """
    Get encumbrance level based on total weight.
    Returns: 'light', 'medium', 'heavy', 'overloaded'
    """
    total_weight = calculate_total_weight(character)
    capacity = calculate_carrying_capacity(character)
    
    if not capacity:
        return 'light'
    
    if total_weight <= capacity['medium']:
        return 'light'
    elif total_weight <= capacity['heavy']:
        return 'medium'
    elif total_weight <= capacity['maximum']:
        return 'heavy'
    else:
        return 'overloaded'


def get_encumbrance_effects(character):
    """
    Get effects of encumbrance on character stats.
    Returns dict of stat modifications.
    """
    encumbrance = get_encumbrance_level(character)
    
    effects = {
        'light': {
            'speed_modifier': 1.0,
            'ability_check_disadvantage': False,
        },
        'medium': {
            'speed_modifier': 1.0,
            'ability_check_disadvantage': False,
        },
        'heavy': {
            'speed_modifier': 0.8,  # 20% speed reduction
            'ability_check_disadvantage': False,
        },
        'overloaded': {
            'speed_modifier': 0.5,  # 50% speed reduction
            'ability_check_disadvantage': True,  # Disadvantage on STR/DEX checks
        },
    }
    
    return effects.get(encumbrance, effects['light'])


def can_equip_item(character, item, slot):
    """Check if character can equip an item in the given slot"""
    # Downcast item if needed
    if hasattr(item, 'weapon'):
        item = item.weapon
    elif hasattr(item, 'armor'):
        item = item.armor

    # Check if slot is valid for item type
    if hasattr(item, 'weapon_type'):  # It's a Weapon
        valid_slots = ['main_hand', 'off_hand']
        if item.two_handed:
            valid_slots = ['main_hand']  # Two-handed weapons must be in main hand
        if slot not in valid_slots:
            return False, f"Weapon must be equipped in main_hand or off_hand"
    
    elif hasattr(item, 'armor_type'):  # It's an Armor
        if slot != 'armor' and item.armor_type != 'shield':
             return False, f"Armor must be equipped in armor slot"
        if item.armor_type == 'shield' and slot != 'off_hand':
             return False, f"Shield must be equipped in off_hand"
    
    else:
        # Other items can go in various slots
        valid_slots = ['ring', 'amulet', 'boots', 'gloves', 'helmet', 'cloak']
        if slot not in valid_slots and slot != 'inventory':
            return False, f"Item cannot be equipped in {slot}"
    
    # Note: We don't check if slot is occupied here because equip_item() 
    # handles auto-unequipping the old item when equipping a new one
    
    # Check two-handed weapon conflicts
    if hasattr(item, 'weapon_type') and item.two_handed:
        # If equipping 2H to main_hand, off_hand must be empty
        off_hand_item = CharacterItem.objects.filter(
            character=character,
            equipment_slot='off_hand',
            is_equipped=True
        ).first()
        if off_hand_item:
            return False, "Cannot equip two-handed weapon while off-hand is occupied"
            
    # Check if equipping to off-hand (shield/weapon) while holding 2H weapon
    if slot == 'off_hand':
        main_hand_item = get_equipped_weapon(character, 'main_hand')
        if main_hand_item and main_hand_item.two_handed:
             return False, "Cannot equip to off-hand while holding two-handed weapon"
    
    return True, None


def equip_item(character, item, slot='main_hand'):
    """
    Equip an item to a character.
    Returns (success, message, character_item)
    """
    char_item, created = CharacterItem.objects.get_or_create(
        character=character,
        item=item,
        defaults={'equipment_slot': slot}
    )

    # Auto-detect slot for armor/shields (always, not just when slot='main_hand')
    # This is needed because shields might have been incorrectly set to 'armor' slot previously
    
    # Check if item is an Armor type (includes shields)
    if hasattr(item, 'armor_type'):
        # It's already an Armor object (shields are armor with armor_type='shield')
        if item.armor_type == 'shield':
            slot = 'off_hand'
        else:
            slot = 'armor'
    elif hasattr(item, 'armor'):
        # Item is a base Item with an armor relation
        armor_item = item.armor
        if armor_item.armor_type == 'shield':
            slot = 'off_hand'
        else:
            slot = 'armor'
    elif slot == 'main_hand':
        # Only do accessory detection if slot is still main_hand
            # Check for accessories based on item name
            item_name_lower = item.name.lower()
            if 'amulet' in item_name_lower or 'necklace' in item_name_lower or 'pendant' in item_name_lower:
                slot = 'amulet'
            elif 'ring' in item_name_lower:
                slot = 'ring'
            elif 'boot' in item_name_lower or 'shoe' in item_name_lower:
                slot = 'boots'
            elif 'glove' in item_name_lower or 'gauntlet' in item_name_lower:
                slot = 'gloves'
            elif 'helmet' in item_name_lower or 'helm' in item_name_lower or 'crown' in item_name_lower or 'circlet' in item_name_lower:
                slot = 'helmet'
            elif 'cloak' in item_name_lower or 'cape' in item_name_lower or 'mantle' in item_name_lower:
                slot = 'cloak'
    
    # Check if can equip
    can_equip, error_msg = can_equip_item(character, item, slot)
    if not can_equip:
        return False, error_msg, None
    
    # Unequip any item currently in this slot
    CharacterItem.objects.filter(
        character=character,
        equipment_slot=slot,
        is_equipped=True
    ).exclude(id=char_item.id).update(is_equipped=False)
    
    # Equip the item
    char_item.is_equipped = True
    char_item.equipment_slot = slot
    char_item.save()
    
    # Recalculate stats (AC)
    recalculate_armor_class(character)
    
    return True, f"Equipped {item.name} in {slot}", char_item


def unequip_item(character, item):
    """
    Unequip an item from a character.
    Returns (success, message)
    """
    try:
        char_item = CharacterItem.objects.get(character=character, item=item, is_equipped=True)
        char_item.is_equipped = False
        char_item.equipment_slot = 'inventory'
        char_item.save()
        
        # Recalculate stats (AC)
        recalculate_armor_class(character)
        
        return True, f"Unequipped {item.name}"
    except CharacterItem.DoesNotExist:
        return False, f"{item.name} is not equipped"


def get_equipped_items(character):
    """Get all equipped items for a character"""
    return CharacterItem.objects.filter(character=character, is_equipped=True)


def get_equipped_weapon(character, slot='main_hand'):
    """Get equipped weapon in specified slot"""
    try:
        char_item = CharacterItem.objects.get(
            character=character,
            equipment_slot=slot,
            is_equipped=True
        )
        if hasattr(char_item.item, 'weapon'):
            return char_item.item.weapon
    except CharacterItem.DoesNotExist:
        pass
    return None


def get_equipped_armor(character):
    """Get equipped armor"""
    try:
        char_item = CharacterItem.objects.get(
            character=character,
            equipment_slot='armor',
            is_equipped=True
        )
        if hasattr(char_item.item, 'armor'):
            return char_item.item.armor
    except CharacterItem.DoesNotExist:
        pass
    return None


def get_equipped_shield(character):
    """Get equipped shield"""
    try:
        char_item = CharacterItem.objects.get(
            character=character,
            equipment_slot='off_hand', # Shield uses off_hand slot
            is_equipped=True
        )
        if hasattr(char_item.item, 'armor') and char_item.item.armor.armor_type == 'shield':
            return char_item.item.armor
    except CharacterItem.DoesNotExist:
        pass
    return None


def apply_item_effects(character):
    """
    Apply effects from equipped magic items.
    Returns dict of stat modifications.
    """
    modifications = {}
    equipped_items = get_equipped_items(character)
    
    for char_item in equipped_items:
        item = char_item.item
        
        # Apply magic item bonuses
        if item.is_magical:
            # This would be expanded based on item properties
            # For now, just a placeholder structure
            pass
    
    return modifications


def recalculate_armor_class(character):
    """
    Recalculate and save character's Armor Class based on:
    - Base: 10 + DEX mod
    - Armor: Base AC + DEX mod (capped if medium, ignored if heavy)
    - Shield: +2 AC
    """
    if not character.stats:
        return
        
    stats = character.stats
    dex_mod = stats.dexterity_modifier
    
    
    # 1. Determine Base AC from Armor
    equipped_armor = get_equipped_armor(character)
    
    if equipped_armor:
        # Armor equipped
        ac = equipped_armor.base_ac
        
        # Apply DEX bonus based on armor type
        if equipped_armor.armor_type == 'light':
            ac += dex_mod
        elif equipped_armor.armor_type == 'medium':
            # Cap DEX bonus at +2, but allow negative
            bonus = min(dex_mod, 2)
            ac += bonus
        elif equipped_armor.armor_type == 'heavy':
            # No DEX bonus (neither positive nor negative usually, though strict 5e says no bonus)
            pass
    else:
        # Unarmored: 10 + DEX
        # TODO: Add Unarmored Defense (Monk/Barbarian) check here later
        ac = 10 + dex_mod
        
    # 2. Add Shield Bonus
    equipped_shield = get_equipped_shield(character)
    if equipped_shield:
        ac += 2  # Standard shield bonus
        
    # 3. Add Magic Item Bonuses (placeholder)
    # Check for Ring of Protection, etc.
    
    # Update stats
    if stats.armor_class != ac:
        stats.armor_class = ac
        stats.save(update_fields=['armor_class'])
    
    return ac

