"""
Starting Equipment Data for D&D 5e Classes

This module defines the starting equipment choices for each class,
including equipment packs and individual item choices.
"""

# Equipment Packs (standard D&D 5e packs)
EQUIPMENT_PACKS = {
    "Explorer's Pack": {
        'cost': 10,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Bedroll', 'quantity': 1},
            {'name': 'Mess Kit', 'quantity': 1},
            {'name': 'Tinderbox', 'quantity': 1},
            {'name': 'Torch', 'quantity': 10},
            {'name': 'Rations', 'quantity': 10},
            {'name': 'Waterskin', 'quantity': 1},
            {'name': 'Rope, Hempen (50 feet)', 'quantity': 1}
        ]
    },
    "Dungeoneer's Pack": {
        'cost': 12,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Crowbar', 'quantity': 1},
            {'name': 'Hammer', 'quantity': 1},
            {'name': 'Piton', 'quantity': 10},
            {'name': 'Torch', 'quantity': 10},
            {'name': 'Tinderbox', 'quantity': 1},
            {'name': 'Rations', 'quantity': 10},
            {'name': 'Waterskin', 'quantity': 1},
            {'name': 'Rope, Hempen (50 feet)', 'quantity': 1}
        ]
    },
    "Scholar's Pack": {
        'cost': 40,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Book', 'quantity': 1},
            {'name': 'Ink', 'quantity': 1},
            {'name': 'Ink Pen', 'quantity': 1},
            {'name': 'Parchment', 'quantity': 10},
            {'name': 'Sand', 'quantity': 1},
            {'name': 'Knife', 'quantity': 1}
        ]
    },
    "Priest's Pack": {
        'cost': 19,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Blanket', 'quantity': 1},
            {'name': 'Candle', 'quantity': 10},
            {'name': 'Tinderbox', 'quantity': 1},
            {'name': 'Alms Box', 'quantity': 1},
            {'name': 'Incense', 'quantity': 2},
            {'name': 'Censer', 'quantity': 1},
            {'name': 'Vestments', 'quantity': 1},
            {'name': 'Rations', 'quantity': 2},
            {'name': 'Waterskin', 'quantity': 1}
        ]
    },
    "Entertainer's Pack": {
        'cost': 40,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Bedroll', 'quantity': 1},
            {'name': 'Costume', 'quantity': 2},
            {'name': 'Candle', 'quantity': 5},
            {'name': 'Rations', 'quantity': 5},
            {'name': 'Waterskin', 'quantity': 1},
            {'name': 'Disguise Kit', 'quantity': 1}
        ]
    },
    "Burglar's Pack": {
        'cost': 16,
        'items': [
            {'name': 'Backpack', 'quantity': 1},
            {'name': 'Ball Bearings', 'quantity': 1000},
            {'name': 'String', 'quantity': 1},
            {'name': 'Bell', 'quantity': 1},
            {'name': 'Candle', 'quantity': 5},
            {'name': 'Crowbar', 'quantity': 1},
            {'name': 'Hammer', 'quantity': 1},
            {'name': 'Piton', 'quantity': 10},
            {'name': 'Hooded Lantern', 'quantity': 1},
            {'name': 'Oil', 'quantity': 2},
            {'name': 'Rations', 'quantity': 5},
            {'name': 'Tinderbox', 'quantity': 1},
            {'name': 'Waterskin', 'quantity': 1},
            {'name': 'Rope, Hempen (50 feet)', 'quantity': 1}
        ]
    }
}

# Starting Equipment Choices for Each Class
STARTING_EQUIPMENT = {
    'fighter': {
        'class_name': 'Fighter',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your armor',
                'options': [
                    {
                        'label': '(a) Chain Mail',
                        'items': [{'name': 'Chain Mail', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Leather Armor, Longbow, and 20 Arrows',
                        'items': [
                            {'name': 'Leather', 'quantity': 1},
                            {'name': 'Longbow', 'quantity': 1},
                            {'name': 'Arrow', 'quantity': 20}
                        ]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your weapons',
                'options': [
                    {
                        'label': '(a) A Martial Weapon and a Shield',
                        'items': [
                            {'name': 'Shield', 'quantity': 1},
                            {'name': 'martial_weapon_choice', 'quantity': 1}  # Special marker for choice
                        ],
                        'additional_choice': {
                            'type': 'weapon',
                            'category': 'martial',
                            'prompt': 'Choose a martial weapon'
                        }
                    },
                    {
                        'label': '(b) Two Martial Weapons',
                        'items': [
                            {'name': 'martial_weapon_choice_1', 'quantity': 1},
                            {'name': 'martial_weapon_choice_2', 'quantity': 1}
                        ],
                        'additional_choice': {
                            'type': 'weapon',
                            'category': 'martial',
                            'count': 2,
                            'prompt': 'Choose two martial weapons'
                        }
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your ranged weapon',
                'options': [
                    {
                        'label': '(a) Light Crossbow and 20 Bolts',
                        'items': [
                            {'name': 'Light Crossbow', 'quantity': 1},
                            {'name': 'Crossbow Bolt', 'quantity': 20}
                        ]
                    },
                    {
                        'label': '(b) Two Handaxes',
                        'items': [{'name': 'Hand Axe', 'quantity': 2}]
                    }
                ]
            },
            {
                'choice_number': 4,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': []  # Items all fighters get automatically
    },
    
    'wizard': {
        'class_name': 'Wizard',
        'starting_gold': {'min': 40, 'max': 160},  # 4d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Quarterstaff',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    },
                    {
                        'label': '(b) A Dagger',
                        'items': [{'name': 'Dagger', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your arcane focus',
                'options': [
                    {
                        'label': '(a) A Component Pouch',
                        'items': [{'name': 'Component Pouch', 'quantity': 1}]
                    },
                    {
                        'label': '(b) An Arcane Focus',
                        'items': [{'name': 'Arcane Focus', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Scholar's Pack",
                        'pack': "Scholar's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Spellbook', 'quantity': 1}
        ]
    },
    
    'rogue': {
        'class_name': 'Rogue',
        'starting_gold': {'min': 40, 'max': 160},  # 4d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your primary weapon',
                'options': [
                    {
                        'label': '(a) A Rapier',
                        'items': [{'name': 'Rapier', 'quantity': 1}]
                    },
                    {
                        'label': '(b) A Shortsword',
                        'items': [{'name': 'Shortsword', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your ranged weapon',
                'options': [
                    {
                        'label': '(a) Shortbow and 20 Arrows',
                        'items': [
                            {'name': 'Shortbow', 'quantity': 1},
                            {'name': 'Arrow', 'quantity': 20}
                        ]
                    },
                    {
                        'label': '(b) A Shortsword',
                        'items': [{'name': 'Shortsword', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Burglar's Pack",
                        'pack': "Burglar's Pack"
                    },
                    {
                        'label': "(b) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    },
                    {
                        'label': "(c) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Leather', 'quantity': 1},
            {'name': 'Dagger', 'quantity': 2},
            {'name': "Thieves' Tools", 'quantity': 1}
        ]
    },
    
    'barbarian': {
        'class_name': 'Barbarian',
        'starting_gold': {'min': 50, 'max': 200},  # 2d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Greataxe',
                        'items': [{'name': 'Greataxe', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Any Martial Melee Weapon',
                        'items': [{'name': 'Battleaxe', 'quantity': 1}]  # Default to battleaxe
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your secondary weapon',
                'options': [
                    {
                        'label': '(a) Two Handaxes',
                        'items': [{'name': 'Handaxe', 'quantity': 2}]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Javelin', 'quantity': 1}]  # Default to javelin
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Javelin', 'quantity': 4}
        ]
    },
    
    'bard': {
        'class_name': 'Bard',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Rapier',
                        'items': [{'name': 'Rapier', 'quantity': 1}]
                    },
                    {
                        'label': '(b) A Longsword',
                        'items': [{'name': 'Longsword', 'quantity': 1}]
                    },
                    {
                        'label': '(c) Any Simple Weapon',
                        'items': [{'name': 'Dagger', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Diplomat's Pack",
                        'pack': "Explorer's Pack"  # Use Explorer's as substitute
                    },
                    {
                        'label': "(b) Entertainer's Pack",
                        'pack': "Entertainer's Pack"
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your instrument',
                'options': [
                    {
                        'label': '(a) A Lute',
                        'items': [{'name': 'Lute', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Any Musical Instrument',
                        'items': [{'name': 'Flute', 'quantity': 1}]
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Leather', 'quantity': 1},
            {'name': 'Dagger', 'quantity': 1}
        ]
    },
    
    'cleric': {
        'class_name': 'Cleric',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Mace',
                        'items': [{'name': 'Mace', 'quantity': 1}]
                    },
                    {
                        'label': '(b) A Warhammer',
                        'items': [{'name': 'Warhammer', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your armor',
                'options': [
                    {
                        'label': '(a) Scale Mail',
                        'items': [{'name': 'Scale Mail', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Leather Armor',
                        'items': [{'name': 'Leather', 'quantity': 1}]
                    },
                    {
                        'label': '(c) Chain Mail',
                        'items': [{'name': 'Chain Mail', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your ranged weapon',
                'options': [
                    {
                        'label': '(a) Light Crossbow and 20 Bolts',
                        'items': [
                            {'name': 'Light Crossbow', 'quantity': 1},
                            {'name': 'Crossbow Bolt', 'quantity': 20}
                        ]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Club', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 4,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Priest's Pack",
                        'pack': "Priest's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Shield', 'quantity': 1},
            {'name': 'Holy Symbol', 'quantity': 1}
        ]
    },
    
    'druid': {
        'class_name': 'Druid',
        'starting_gold': {'min': 50, 'max': 200},  # 2d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Wooden Shield',
                        'items': [{'name': 'Shield', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your melee weapon',
                'options': [
                    {
                        'label': '(a) A Scimitar',
                        'items': [{'name': 'Scimitar', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Any Simple Melee Weapon',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Leather', 'quantity': 1},
            {'name': 'Druidic Focus', 'quantity': 1}
        ]
    },
    
    'monk': {
        'class_name': 'Monk',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) A Shortsword',
                        'items': [{'name': 'Shortsword', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Dart', 'quantity': 10}
        ]
    },
    
    'paladin': {
        'class_name': 'Paladin',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon and shield',
                'options': [
                    {
                        'label': '(a) A Martial Weapon and Shield',
                        'items': [
                            {'name': 'Longsword', 'quantity': 1},
                            {'name': 'Shield', 'quantity': 1}
                        ]
                    },
                    {
                        'label': '(b) Two Martial Weapons',
                        'items': [{'name': 'Longsword', 'quantity': 2}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your ranged weapon',
                'options': [
                    {
                        'label': '(a) Five Javelins',
                        'items': [{'name': 'Javelin', 'quantity': 5}]
                    },
                    {
                        'label': '(b) Any Simple Melee Weapon',
                        'items': [{'name': 'Mace', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Priest's Pack",
                        'pack': "Priest's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Chain Mail', 'quantity': 1},
            {'name': 'Holy Symbol', 'quantity': 1}
        ]
    },
    
    'ranger': {
        'class_name': 'Ranger',
        'starting_gold': {'min': 125, 'max': 200},  # 5d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your armor',
                'options': [
                    {
                        'label': '(a) Scale Mail',
                        'items': [{'name': 'Scale Mail', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Leather Armor',
                        'items': [{'name': 'Leather', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your melee weapons',
                'options': [
                    {
                        'label': '(a) Two Shortswords',
                        'items': [{'name': 'Shortsword', 'quantity': 2}]
                    },
                    {
                        'label': '(b) Two Simple Melee Weapons',
                        'items': [{'name': 'Handaxe', 'quantity': 2}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Longbow', 'quantity': 1},
            {'name': 'Arrow', 'quantity': 20}
        ]
    },
    
    'sorcerer': {
        'class_name': 'Sorcerer',
        'starting_gold': {'min': 75, 'max': 300},  # 3d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) Light Crossbow and 20 Bolts',
                        'items': [
                            {'name': 'Light Crossbow', 'quantity': 1},
                            {'name': 'Crossbow Bolt', 'quantity': 20}
                        ]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your focus',
                'options': [
                    {
                        'label': '(a) Component Pouch',
                        'items': [{'name': 'Component Pouch', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Arcane Focus',
                        'items': [{'name': 'Arcane Focus', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    },
                    {
                        'label': "(b) Explorer's Pack",
                        'pack': "Explorer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Dagger', 'quantity': 2}
        ]
    },
    
    'warlock': {
        'class_name': 'Warlock',
        'starting_gold': {'min': 40, 'max': 160},  # 4d4 × 10 gp
        'choices': [
            {
                'choice_number': 1,
                'description': 'Choose your weapon',
                'options': [
                    {
                        'label': '(a) Light Crossbow and 20 Bolts',
                        'items': [
                            {'name': 'Light Crossbow', 'quantity': 1},
                            {'name': 'Crossbow Bolt', 'quantity': 20}
                        ]
                    },
                    {
                        'label': '(b) Any Simple Weapon',
                        'items': [{'name': 'Quarterstaff', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 2,
                'description': 'Choose your focus',
                'options': [
                    {
                        'label': '(a) Component Pouch',
                        'items': [{'name': 'Component Pouch', 'quantity': 1}]
                    },
                    {
                        'label': '(b) Arcane Focus',
                        'items': [{'name': 'Arcane Focus', 'quantity': 1}]
                    }
                ]
            },
            {
                'choice_number': 3,
                'description': 'Choose your pack',
                'options': [
                    {
                        'label': "(a) Scholar's Pack",
                        'pack': "Scholar's Pack"
                    },
                    {
                        'label': "(b) Dungeoneer's Pack",
                        'pack': "Dungeoneer's Pack"
                    }
                ]
            }
        ],
        'default_items': [
            {'name': 'Leather', 'quantity': 1},
            {'name': 'Dagger', 'quantity': 2}
        ]
    }
}


def get_starting_equipment_for_class(class_name):
    """
    Get starting equipment choices for a given class.
    
    Args:
        class_name (str): The class name (lowercase, e.g., 'fighter', 'wizard')
    
    Returns:
        dict: Starting equipment data or None if class not found
    """
    return STARTING_EQUIPMENT.get(class_name.lower())


def get_equipment_pack(pack_name):
    """
    Get items in an equipment pack.
    
    Args:
        pack_name (str): Pack name (e.g., "Explorer's Pack")
    
    Returns:
        dict: Pack data or None if pack not found
    """
    return EQUIPMENT_PACKS.get(pack_name)


def get_all_packs():
    """Get all available equipment packs."""
    return EQUIPMENT_PACKS
