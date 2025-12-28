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
    # Check if slot is valid for item type
    if isinstance(item, Weapon):
        valid_slots = ['main_hand', 'off_hand']
        if item.two_handed:
            valid_slots = ['main_hand']  # Two-handed weapons must be in main hand
        if slot not in valid_slots:
            return False, f"Weapon must be equipped in main_hand or off_hand"
    
    elif isinstance(item, Armor):
        if slot != 'armor':
            return False, f"Armor must be equipped in armor slot"
    
    else:
        # Other items can go in various slots
        valid_slots = ['ring', 'amulet', 'boots', 'gloves', 'helmet', 'cloak']
        if slot not in valid_slots and slot != 'inventory':
            return False, f"Item cannot be equipped in {slot}"
    
    # Check if slot is already occupied
    existing = CharacterItem.objects.filter(
        character=character,
        equipment_slot=slot,
        is_equipped=True
    ).exclude(item=item)
    
    if existing.exists():
        return False, f"Slot {slot} is already occupied"
    
    # Check two-handed weapon conflicts
    if isinstance(item, Weapon) and item.two_handed:
        # Check if off_hand has something equipped
        off_hand_item = CharacterItem.objects.filter(
            character=character,
            equipment_slot='off_hand',
            is_equipped=True
        ).first()
        if off_hand_item:
            return False, "Cannot equip two-handed weapon while off-hand is occupied"
    
    return True, None


def equip_item(character, item, slot='main_hand'):
    """
    Equip an item to a character.
    Returns (success, message, character_item)
    """
    # Get or create CharacterItem
    char_item, created = CharacterItem.objects.get_or_create(
        character=character,
        item=item,
        defaults={'equipment_slot': slot}
    )
    
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
        if isinstance(char_item.item, Weapon):
            return char_item.item
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
        if isinstance(char_item.item, Armor):
            return char_item.item
    except CharacterItem.DoesNotExist:
        pass
    return None


def get_equipped_shield(character):
    """Get equipped shield"""
    try:
        char_item = CharacterItem.objects.get(
            character=character,
            equipment_slot='shield',
            is_equipped=True
        )
        return char_item.item
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

