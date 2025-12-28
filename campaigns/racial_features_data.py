"""
D&D 5e Racial Features

This module contains racial feature data for automatic application during character creation.
Features are organized by race name.
"""

# Racial features by race name
RACIAL_FEATURES = {
    'human': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your ability scores each increase by 1.'
        },
        {
            'name': 'Extra Language',
            'description': 'You can speak, read, and write one extra language of your choice.'
        }
    ],
    
    'elf': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Dexterity score increases by 2.'
        },
        {
            'name': 'Darkvision',
            'description': 'Accustomed to twilit forests and the night sky, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Keen Senses',
            'description': 'You have proficiency in the Perception skill.'
        },
        {
            'name': 'Fey Ancestry',
            'description': 'You have advantage on saving throws against being charmed, and magic can\'t put you to sleep.'
        },
        {
            'name': 'Trance',
            'description': 'Elves don\'t need to sleep. Instead, they meditate deeply, remaining semiconscious, for 4 hours a day. While meditating, you can dream after a fashion; such dreams are actually mental exercises that have become reflexive through years of practice. After resting in this way, you gain the same benefit that a human does from 8 hours of sleep.'
        },
        {
            'name': 'Elf Weapon Training',
            'description': 'You have proficiency with the longsword, shortsword, shortbow, and longbow.'
        }
    ],
    
    'dwarf': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Constitution score increases by 2.'
        },
        {
            'name': 'Darkvision',
            'description': 'Accustomed to life underground, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Dwarven Resilience',
            'description': 'You have advantage on saving throws against poison, and you have resistance against poison damage.'
        },
        {
            'name': 'Dwarven Combat Training',
            'description': 'You have proficiency with the battleaxe, handaxe, light hammer, and warhammer.'
        },
        {
            'name': 'Tool Proficiency',
            'description': 'You gain proficiency with the artisan\'s tools of your choice: smith\'s tools, brewer\'s supplies, or mason\'s tools.'
        },
        {
            'name': 'Stonecunning',
            'description': 'Whenever you make an Intelligence (History) check related to the origin of stonework, you are considered proficient in the History skill and add double your proficiency bonus to the check, instead of your normal proficiency bonus.'
        }
    ],
    
    'halfling': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Dexterity score increases by 2.'
        },
        {
            'name': 'Lucky',
            'description': 'When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and must use the new roll.'
        },
        {
            'name': 'Brave',
            'description': 'You have advantage on saving throws against being frightened.'
        },
        {
            'name': 'Halfling Nimbleness',
            'description': 'You can move through the space of any creature that is of a size larger than yours.'
        }
    ],
    
    'dragonborn': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Strength score increases by 2, and your Charisma score increases by 1.'
        },
        {
            'name': 'Draconic Ancestry',
            'description': 'You have draconic ancestry. Choose one type of dragon from the Draconic Ancestry table. Your breath weapon and damage resistance are determined by the dragon type.'
        },
        {
            'name': 'Breath Weapon',
            'description': 'You can use your action to exhale destructive energy. Your draconic ancestry determines the size, shape, and damage type of the exhalation. When you use your breath weapon, each creature in the area of the exhalation must make a saving throw, the type of which is determined by your draconic ancestry. The DC for this saving throw equals 8 + your Constitution modifier + your proficiency bonus. A creature takes 2d6 damage on a failed save, and half as much damage on a successful one. The damage increases to 3d6 at 6th level, 4d6 at 11th level, and 5d6 at 16th level. After you use your breath weapon, you can\'t use it again until you complete a short or long rest.'
        },
        {
            'name': 'Damage Resistance',
            'description': 'You have resistance to the damage type associated with your draconic ancestry.'
        }
    ],
    
    'gnome': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Intelligence score increases by 2.'
        },
        {
            'name': 'Darkvision',
            'description': 'Accustomed to life underground, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Gnome Cunning',
            'description': 'You have advantage on all Intelligence, Wisdom, and Charisma saving throws against magic.'
        }
    ],
    
    'half-elf': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Charisma score increases by 2, and two other ability scores of your choice increase by 1.'
        },
        {
            'name': 'Darkvision',
            'description': 'Thanks to your elf blood, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Fey Ancestry',
            'description': 'You have advantage on saving throws against being charmed, and magic can\'t put you to sleep.'
        },
        {
            'name': 'Skill Versatility',
            'description': 'You gain proficiency in two skills of your choice.'
        }
    ],
    
    'half-orc': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Strength score increases by 2, and your Constitution score increases by 1.'
        },
        {
            'name': 'Darkvision',
            'description': 'Thanks to your orc blood, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Menacing',
            'description': 'You gain proficiency in the Intimidation skill.'
        },
        {
            'name': 'Relentless Endurance',
            'description': 'When you are reduced to 0 hit points but not killed outright, you can drop to 1 hit point instead. You can\'t use this feature again until you finish a long rest.'
        },
        {
            'name': 'Savage Attacks',
            'description': 'When you score a critical hit with a melee weapon attack, you can roll one of the weapon\'s damage dice one additional time and add it to the extra damage of the critical hit.'
        }
    ],
    
    'tiefling': [
        {
            'name': 'Ability Score Increase',
            'description': 'Your Intelligence score increases by 1, and your Charisma score increases by 2.'
        },
        {
            'name': 'Darkvision',
            'description': 'Thanks to your infernal heritage, you have superior vision in dark and dim conditions. You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can\'t discern color in darkness, only shades of gray.'
        },
        {
            'name': 'Hellish Resistance',
            'description': 'You have resistance to fire damage.'
        },
        {
            'name': 'Infernal Legacy',
            'description': 'You know the thaumaturgy cantrip. When you reach 3rd level, you can cast the hellish rebuke spell as a 2nd-level spell once with this trait and regain the ability to do so when you finish a long rest. When you reach 5th level, you can cast the darkness spell once with this trait and regain the ability to do so when you finish a long rest. Charisma is your spellcasting ability for these spells.'
        }
    ]
}


def get_racial_features(race_name):
    """
    Get racial features for a specific race.
    
    Args:
        race_name: Name of the race (e.g., 'human', 'elf', 'dwarf')
    
    Returns:
        List of feature dictionaries with 'name' and 'description' keys
    """
    race_name_lower = race_name.lower()
    if race_name_lower not in RACIAL_FEATURES:
        return []
    
    return RACIAL_FEATURES[race_name_lower]


def apply_racial_features_to_character(character):
    """
    Apply racial features to a character.
    Creates CharacterFeature instances for all racial features.
    
    Args:
        character: Character instance
    
    Returns:
        List of created CharacterFeature instances
    """
    from characters.models import CharacterFeature
    
    race_name = character.race.name
    racial_features = get_racial_features(race_name)
    
    created_features = []
    for feature_data in racial_features:
        feature = CharacterFeature.objects.create(
            character=character,
            name=feature_data['name'],
            feature_type='racial',
            description=feature_data['description'],
            source=f"{character.race.get_name_display()} Race"
        )
        created_features.append(feature)
    
    return created_features

