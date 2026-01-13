"""
Rarity-based weighted random selection for merchant inventory.
Rarity chances increase as players progress deeper into the gauntlet.
"""
import random
from items.models import Item, Weapon, Armor, Consumable,MagicItem


# Rarity progression by encounter depth
RARITY_WEIGHTS = {
    # Encounters 1-3: Mostly common items
    'early': {
        'common': 70,
        'uncommon': 25,
        'rare': 5,
        'very_rare': 0,
        'legendary': 0,
        'artifact': 0,
    },
    # Encounters 4-6: More uncommon and some rare
    'mid': {
        'common': 40,
        'uncommon': 40,
        'rare': 15,
        'very_rare': 5,
        'legendary': 0,
        'artifact': 0,
    },
    # Encounters 7-9: Rare items become common
    'late': {
        'common': 15,
        'uncommon': 35,
        'rare': 35,
        'very_rare': 12,
        'legendary': 3,
        'artifact': 0,
    },
    # Encounters 10+: Legendary and artifact items appear
    'endgame': {
        'common': 5,
        'uncommon': 20,
        'rare': 30,
        'very_rare': 30,
        'legendary': 13,
        'artifact': 2,
    },
}


def get_rarity_weights(encounter_depth: int) -> dict:
    """
    Get rarity weights based on encounter depth in the gauntlet.
    
    Args:
        encounter_depth: Current encounter number (1-based)
    
    Returns:
        Dictionary of rarity -> weight percentage
    """
    if encounter_depth <= 3:
        return RARITY_WEIGHTS['early']
    elif encounter_depth <= 6:
        return RARITY_WEIGHTS['mid']
    elif encounter_depth <= 9:
        return RARITY_WEIGHTS['late']
    else:
        return RARITY_WEIGHTS['endgame']


def select_random_items(encounter_depth: int, count: int = 5) -> list:
    """
    Select random items weighted by rarity based on encounter depth.
    
    Args:
        encounter_depth: Current encounter number in gauntlet
        count: Number of items to select
    
    Returns:
        List of Item objects (or subclasses)
    """
    weights = get_rarity_weights(encounter_depth)
    selected_items = []
    
    # Get all items by rarity
    items_by_rarity = _get_items_by_rarity()
    
    # If no items available, return empty list
    if not any(items_by_rarity.values()):
        return []
    
    # Select items based on weighted probabilities
    for _ in range(count):
        # Randomly choose a rarity based on weights
        rarity = _weighted_random_choice(weights)
        
        # Get available items of this rarity
        available_items = items_by_rarity.get(rarity, [])
        
        if available_items:
            # Randomly select one item of this rarity
            item = random.choice(available_items)
            selected_items.append(item)
        else:
            # Fallback to any common item if this rarity has no items
            for fallback_rarity in ['common', 'uncommon', 'rare', 'very_rare', 'legendary', 'artifact']:
                fallback_items = items_by_rarity.get(fallback_rarity, [])
                if fallback_items:
                    item = random.choice(fallback_items)
                    selected_items.append(item)
                    break
    
    return selected_items


def _get_items_by_rarity() -> dict:
    """
    Get all items organized by rarity.
    
    Returns:
        Dictionary of rarity -> list of items
    """
    items_by_rarity = {
        'common': [],
        'uncommon': [],
        'rare': [],
        'very_rare': [],
        'legendary': [],
        'artifact': [],
    }
    
    # Collect all Item-based objects (Item, Weapon, Armor, Consumable, MagicItem)
    all_items = list(Item.objects.filter(rarity__in=items_by_rarity.keys()))
    
    # Organize by rarity
    for item in all_items:
        rarity = item.rarity
        if rarity in items_by_rarity:
            items_by_rarity[rarity].append(item)
    
    return items_by_rarity


def _weighted_random_choice(weights: dict) -> str:
    """
    Make a weighted random choice from a dictionary of weights.
    
    Args:
        weights: Dictionary of option -> weight percentage
    
    Returns:
        Selected option
    """
    # Filter out zero weights
    valid_weights = {k: v for k, v in weights.items() if v > 0}
    
    if not valid_weights:
        return 'common'  # Fallback
    
    # Create a list of (option, weight) pairs
    options = list(valid_weights.keys())
    weight_values = list(valid_weights.values())
    
    # Use random.choices for weighted selection
    selected = random.choices(options, weights=weight_values, k=1)[0]
    return selected


# Merchant name generation
MERCHANT_PREFIXES = [
    "Griswald", "Bartok", "Fenwick", "Aldric", "Oswald", "Mortimer", "Barnabas",
    "Thaddeus", "Percival", "Reginald", "Cornelius", "Balthazar", "Ignatius",
    "Tobias", "Ambrose", "Cedric", "Darius", "Erasmus", "Fabian", "Gideon"
]

MERCHANT_SUFFIXES = [
    "the Trader", "the Merchant", "the Wanderer", "the Collector", "the Vendor",
    "the Peddler", "the Supplier", "the Broker", "the Dealer", "the Shopkeeper",
    "the Purveyor", "the Hawker", "the Tradesman"
]


def generate_merchant_name() -> str:
    """Generate a random merchant name"""
    prefix = random.choice(MERCHANT_PREFIXES)
    suffix = random.choice(MERCHANT_SUFFIXES)
    return f"{prefix} {suffix}"
