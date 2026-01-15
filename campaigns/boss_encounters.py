"""
Boss Encounter Templates for Gauntlet System

Each biome has 2-3 boss variants for variety across runs
"""

# Boss encounters organized by biome
BOSS_ENCOUNTERS = {
    'forest': [
        {
            'name': 'The Ancient Guardian',
            'boss_enemy_name': 'Treant',
            'minions': ['Awakened Tree', 'Wolf'],
            'flavor_text': 'An ancient treant towers above, its bark scarred by centuries. "You dare defile my forest?"',
            'loot': {
                'guaranteed_items': ['Ironwood Staff'],
                'gold': 800,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Corrupted Druid',
            'boss_enemy_name': 'Druid',
            'minions': ['Dire Wolf', 'Giant Spider'],
            'flavor_text': 'Once a forest protector, now twisted by dark magic. Nature itself recoils from their presence.',
            'loot': {
                'guaranteed_items': ["Nature's Wrath Quarterstaff"],
                'gold': 750,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Green Dragon',
            'boss_enemy_name': 'Green Dragon',
            'minions': ['Vine Blight'],
            'flavor_text': 'Poisonous fumes fill the air as a green dragon emerges from the toxic undergrowth.',
            'loot': {
                'guaranteed_items': ['Dragon Scale Shield'],
                'gold': 900,
                'xp_multiplier': 2.5
            }
        }
    ],
    
    'desert': [
        {
            'name': 'The Sand Tyrant',
            'boss_enemy_name': 'Giant Scorpion',
            'minions': ['Giant Scorpion'],
            'flavor_text': 'The sands part as a massive scorpion emerges, its stinger dripping with venom.',
            'loot': {
                'guaranteed_items': ['Desert Wind Scimitar'],
                'gold': 850,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Blue Dragon Wyrmling',
            'boss_enemy_name': 'Blue Dragon',
            'minions': ['Kobold'],
            'flavor_text': 'Lightning crackles across the dunes as a young blue dragon descends from the storm.',
            'loot': {
                'guaranteed_items': ['Stormcaller Spear'],
                'gold': 900,
                'xp_multiplier': 2.5
            }
        },
        {
            'name': 'The Mummy Lord',
            'boss_enemy_name': 'Mummy',
            'minions': ['Skeleton', 'Zombie'],
            'flavor_text': 'Ancient wrappings stir in the tomb as an undead pharaoh rises to defend their treasure.',
            'loot': {
                'guaranteed_items': ['Sandwalker Boots'],
                'gold': 800,
                'xp_multiplier': 2.0
            }
        }
    ],
    
    'mountain': [
        {
            'name': 'The Peak Overlord',
            'boss_enemy_name': 'Stone Giant',
            'minions': ['Ogre'],
            'flavor_text': 'A massive stone giant hurls boulders down from the summit. The mountain itself seems to fight you.',
            'loot': {
                'guaranteed_items': ['Cloudstrike Hammer'],
                'gold': 850,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Young Roc',
            'boss_enemy_name': 'Roc',
            'minions': ['Giant Eagle'],
            'flavor_text': 'A shadow blots out the sun. The legendary roc has made this peak its hunting ground.',
            'loot': {
                'guaranteed_items': ['Wings of the Roc'],
                'gold': 900,
                'xp_multiplier': 2.5
            }
        }
    ],
    
    'swamp': [
        {
            'name': 'The Bog Horror',
            'boss_enemy_name': 'Shambling Mound',
            'minions': ['Zombie', 'Giant Frog'],
            'flavor_text': 'The stagnant waters churn as a massive shambling mound rises, festooned with rot.',
            'loot': {
                'guaranteed_items': ["Bog Queen's Crown"],
                'gold': 750,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Black Dragon',
            'boss_enemy_name': 'Black Dragon',
            'minions': ['Lizardfolk'],
            'flavor_text': 'Acid drips from fanged jaws as a black dragon emerges from the murky depths.',
            'loot': {
                'guaranteed_items': ['Pestilence Dagger'],
                'gold': 900,
                'xp_multiplier': 2.5
            }
        },
        {
            'name': 'The Hag Coven Leader',
            'boss_enemy_name': 'Hag',
            'minions': ['Scarecrow'],
            'flavor_text': 'Cackling echoes through the mist. A powerful hag has cursed these lands.',
            'loot': {
                'guaranteed_items': ['Hag Eye Amulet'],
                'gold': 800,
                'xp_multiplier': 2.0
            }
        }
    ],
    
    'plains': [
        {
            'name': 'The Warlord',
            'boss_enemy_name': 'Hobgoblin',
            'minions': ['Hobgoblin', 'Goblin'],
            'flavor_text': 'A battle-hardened hobgoblin warlord rallies their troops. "Form ranks! Show no mercy!"',
            'loot': {
                'guaranteed_items': ["Warlord's Banner"],
                'gold': 750,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Centaur Chieftain',
            'boss_enemy_name': 'Centaur',
            'minions': ['Centaur'],
            'flavor_text': 'Hoofbeats thunder across the plains. The centaur tribes have united under a fierce chief.',
            'loot': {
                'guaranteed_items': ["Tactical Commander's Helm"],
                'gold': 800,
                'xp_multiplier': 2.0
            }
        }
    ],
    
    'underdark': [
        {
            'name': 'The Mind Tyrant',
            'boss_enemy_name': 'Mind Flayer',
            'minions': ['Intellect Devourer'],
            'flavor_text': 'Psychic whispers assault your mind. An mind flayer reaches out with writhing tentacles.',
            'loot': {
                'guaranteed_items': ['Mind Shackle'],
                'gold': 950,
                'xp_multiplier': 2.5
            }
        },
        {
            'name': 'The Spectator',
            'boss_enemy_name': 'Spectator',
            'minions': ['Gazer'],
            'flavor_text': 'A lesser beholder hovers in the darkness, its eye stalks tracking your every move.',
            'loot': {
                'guaranteed_items': ['Tentacle Rod'],
                'gold': 850,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Drow Matron',
            'boss_enemy_name': 'Drow',
            'minions': ['Drow', 'Giant Spider'],
            'flavor_text': 'A drow priestess emerges from the shadows, blessed by the Spider Queen herself.',
            'loot': {
                'guaranteed_items': ['Shadowsilk Cloak'],
                'gold': 800,
                'xp_multiplier': 2.0
            }
        }
    ],
    
    'urban': [
        {
            'name': 'The Crime Lord',
            'boss_enemy_name': 'Assassin',
            'minions': ['Thug', 'Spy'],
            'flavor_text': 'Shadows move unnaturally. The city\'s most feared assassin has accepted a contract on you.',
            'loot': {
                'guaranteed_items': ["Assassin's Blade"],
                'gold': 850,
                'xp_multiplier': 2.0
            }
        },
        {
            'name': 'The Vampire Spawn',
            'boss_enemy_name': 'Vampire',
            'minions': ['Bat'],
            'flavor_text': 'A vampire lurks in the underbelly of the city, ruling the night with terror.',
            'loot': {
                'guaranteed_items': ['Shadow Cloak'],
                'gold': 900,
                'xp_multiplier': 2.5
            }
        }
    ],
    
    'arctic': [
        {
            'name': 'The Frozen Fury',
            'boss_enemy_name': 'White Dragon',
            'minions': ['Ice Mephit', 'Winter Wolf'],
            'flavor_text': 'A white dragon descends from the blizzard, frost crystallizing in its wake.',
            'loot': {
                'guaranteed_items': ['Frostbite'],
                'gold': 950,
                'xp_multiplier': 2.5
            }
        },
        {
            'name': 'The Frost Giant',
            'boss_enemy_name': 'Frost Giant',
            'minions': ['Yeti'],
            'flavor_text': 'A frost giant bellows a challenge, icicles forming in the air from its frigid breath.',
            'loot': {
                'guaranteed_items': ['Glacier Shield'],
                'gold': 850,
                'xp_multiplier': 2.0
            }
        }
    ],
}


def get_random_boss_for_biome(biome):
    """Get a random boss encounter for the specified biome"""
    import random
    
    if biome not in BOSS_ENCOUNTERS:
        raise ValueError(f"No boss encounters defined for biome: {biome}")
    
    bosses = BOSS_ENCOUNTERS[biome]
    return random.choice(bosses)


def get_all_bosses_for_biome(biome):
    """Get all boss encounters for a biome"""
    return BOSS_ENCOUNTERS.get(biome, [])


def get_biomes_with_bosses():
    """Get list of all biomes that have boss encounters"""
    return list(BOSS_ENCOUNTERS.keys())
