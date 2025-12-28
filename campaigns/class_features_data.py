"""
D&D 5e Class Features by Level

This module contains class feature data for automatic application during level-up.
Features are organized by class and level.
"""

# Class features by class name and level
CLASS_FEATURES = {
    'fighter': {
        1: [
            {
                'name': 'Fighting Style',
                'description': 'You adopt a particular style of fighting as your specialty. Choose one: Archery, Defense, Dueling, Great Weapon Fighting, Protection, or Two-Weapon Fighting.'
            },
            {
                'name': 'Second Wind',
                'description': 'You have a limited well of stamina that you can draw on to protect yourself from harm. On your turn, you can use a bonus action to regain hit points equal to 1d10 + your fighter level. Once you use this feature, you must finish a short or long rest before you can use it again.'
            }
        ],
        2: [
            {
                'name': 'Action Surge',
                'description': 'You can push yourself beyond your normal limits for a moment. On your turn, you can take one additional action. Once you use this feature, you must finish a short or long rest before you can use it again. Starting at 17th level, you can use it twice before a rest, but only once on the same turn.'
            }
        ],
        3: [
            {
                'name': 'Martial Archetype',
                'description': 'You choose an archetype that you strive to emulate in your combat styles and techniques (Champion, Battle Master, or Eldritch Knight). Your choice grants you features at 3rd level and again at 7th, 10th, 15th, and 18th level.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn. The number of attacks increases to three when you reach 11th level in this class and to four when you reach 20th level.'
            }
        ],
        6: [],  # ASI only
        7: [],  # Martial Archetype feature
        8: [],  # ASI only
        9: [
            {
                'name': 'Indomitable',
                'description': 'You can reroll a saving throw that you fail. If you do so, you must use the new roll, and you can\'t use this feature again until you finish a long rest. You can use this feature twice between long rests starting at 13th level and three times between long rests starting at 17th level.'
            }
        ],
        10: [],  # Martial Archetype feature
        11: [
            {
                'name': 'Extra Attack (2)',
                'description': 'You can attack three times whenever you take the Attack action on your turn.'
            }
        ],
        12: [],  # ASI only
        13: [
            {
                'name': 'Indomitable (2 uses)',
                'description': 'You can use Indomitable twice between long rests.'
            }
        ],
        14: [],  # ASI only
        15: [],  # Martial Archetype feature
        16: [],  # ASI only
        17: [
            {
                'name': 'Action Surge (2 uses)',
                'description': 'You can use Action Surge twice before a rest.'
            },
            {
                'name': 'Indomitable (3 uses)',
                'description': 'You can use Indomitable three times between long rests.'
            }
        ],
        18: [],  # Martial Archetype feature
        19: [],  # ASI only
        20: [
            {
                'name': 'Extra Attack (3)',
                'description': 'You can attack four times whenever you take the Attack action on your turn.'
            }
        ]
    },
    
    'wizard': {
        1: [
            {
                'name': 'Spellcasting',
                'description': 'As a student of arcane magic, you have a spellbook containing spells that show the first glimmerings of your true power.'
            },
            {
                'name': 'Arcane Recovery',
                'description': 'You have learned to regain some of your magical energy by studying your spellbook. Once per day when you finish a short rest, you can choose expended spell slots to recover. The spell slots can have a combined level that is equal to or less than half your wizard level (rounded up), and none of the slots can be 6th level or higher.'
            }
        ],
        2: [
            {
                'name': 'Arcane Tradition',
                'description': 'You choose an arcane tradition, shaping your practice of magic through one of eight schools (Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, or Transmutation). Your choice grants you features at 2nd level and again at 6th, 10th, and 14th level.'
            }
        ],
        3: [],  # Spell progression
        4: [],  # ASI only
        5: [],  # Spell progression
        6: [],  # Arcane Tradition feature
        7: [],  # Spell progression
        8: [],  # ASI only
        9: [],  # Spell progression
        10: [],  # Arcane Tradition feature
        11: [],  # Spell progression
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [],  # Arcane Tradition feature
        15: [],  # Spell progression
        16: [],  # ASI only
        17: [],  # Spell progression
        18: [
            {
                'name': 'Spell Mastery',
                'description': 'You have achieved such mastery over certain spells that you can cast them at will. Choose a 1st-level wizard spell and a 2nd-level wizard spell that are in your spellbook. You can cast those spells at their lowest level without expending a spell slot when you have them prepared.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Signature Spells',
                'description': 'You gain mastery over two powerful spells and can cast them with little effort. Choose two 3rd-level wizard spells in your spellbook as your signature spells. You always have these spells prepared, they don\'t count against the number of spells you have prepared, and you can cast each of them once at 3rd level without expending a spell slot. When you do so, you can\'t do so again until you finish a short or long rest.'
            }
        ]
    },
    
    'cleric': {
        1: [
            {
                'name': 'Spellcasting',
                'description': 'As a conduit for divine power, you can cast cleric spells.'
            },
            {
                'name': 'Divine Domain',
                'description': 'Choose one domain related to your deity (Life, Light, Knowledge, Nature, Tempest, Trickery, or War). Your choice grants you domain spells and other features when you choose it at 1st level. It also grants you additional ways to use Channel Divinity when you gain that feature at 2nd level, and additional benefits at 6th, 8th, and 17th levels.'
            }
        ],
        2: [
            {
                'name': 'Channel Divinity',
                'description': 'You gain the ability to channel divine energy directly from your deity, using that energy to fuel magical effects. You start with two such effects: Turn Undead and an effect determined by your domain. You can use your Channel Divinity once between rests. Beginning at 6th level, you can use it twice, and at 18th level, you can use it three times.'
            },
            {
                'name': 'Turn Undead',
                'description': 'As an action, you present your holy symbol and speak a prayer censuring the undead. Each undead that can see or hear you within 30 feet of you must make a Wisdom saving throw. If the creature fails its saving throw, it is turned for 1 minute or until it takes any damage.'
            }
        ],
        3: [],  # Spell progression
        4: [],  # ASI only
        5: [
            {
                'name': 'Destroy Undead (CR 1/2)',
                'description': 'When an undead fails its saving throw against your Turn Undead feature, the creature is instantly destroyed if its challenge rating is at or below 1/2.'
            }
        ],
        6: [
            {
                'name': 'Channel Divinity (2/rest)',
                'description': 'You can use Channel Divinity twice between rests.'
            }
        ],
        7: [],  # Spell progression
        8: [
            {
                'name': 'Destroy Undead (CR 1)',
                'description': 'Your Destroy Undead feature now destroys undead of CR 1 or lower.'
            }
        ],
        9: [],  # Spell progression
        10: [
            {
                'name': 'Divine Intervention',
                'description': 'You can call on your deity to intervene on your behalf when your need is great. Describe the assistance you seek, and roll percentile dice. If you roll a number equal to or lower than your cleric level, your deity intervenes. If your deity intervenes, you can\'t use this feature again for 7 days. Otherwise, you can use it again after you finish a long rest. At 20th level, your call for intervention succeeds automatically.'
            }
        ],
        11: [
            {
                'name': 'Destroy Undead (CR 2)',
                'description': 'Your Destroy Undead feature now destroys undead of CR 2 or lower.'
            }
        ],
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [
            {
                'name': 'Destroy Undead (CR 3)',
                'description': 'Your Destroy Undead feature now destroys undead of CR 3 or lower.'
            }
        ],
        15: [],  # Spell progression
        16: [],  # ASI only
        17: [
            {
                'name': 'Destroy Undead (CR 4)',
                'description': 'Your Destroy Undead feature now destroys undead of CR 4 or lower.'
            }
        ],
        18: [
            {
                'name': 'Channel Divinity (3/rest)',
                'description': 'You can use Channel Divinity three times between rests.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Divine Intervention Improvement',
                'description': 'Your call for Divine Intervention succeeds automatically, no roll required.'
            }
        ]
    },
    
    'rogue': {
        1: [
            {
                'name': 'Expertise',
                'description': 'Choose two of your skill proficiencies, or one of your skill proficiencies and your proficiency with thieves\' tools. Your proficiency bonus is doubled for any ability check you make that uses either of the chosen proficiencies. At 6th level, you can choose two more of your proficiencies to gain this benefit.'
            },
            {
                'name': 'Sneak Attack',
                'description': 'You know how to strike subtly and exploit a foe\'s distraction. Once per turn, you can deal an extra 1d6 damage to one creature you hit with an attack if you have advantage on the attack roll. The attack must use a finesse or a ranged weapon. The amount of the extra damage increases as you gain levels in this class.'
            },
            {
                'name': 'Thieves\' Cant',
                'description': 'You know thieves\' cant, a secret mix of dialect, jargon, and code that allows you to hide messages in seemingly normal conversation.'
            }
        ],
        2: [
            {
                'name': 'Cunning Action',
                'description': 'You can take a bonus action on each of your turns in combat. This action can be used only to take the Dash, Disengage, or Hide action.'
            }
        ],
        3: [
            {
                'name': 'Roguish Archetype',
                'description': 'You choose an archetype that you emulate in the exercise of your rogue abilities (Thief, Assassin, or Arcane Trickster). Your choice grants you features at 3rd level and then again at 9th, 13th, and 17th level.'
            },
            {
                'name': 'Sneak Attack (2d6)',
                'description': 'Your Sneak Attack damage increases to 2d6.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Uncanny Dodge',
                'description': 'When an attacker that you can see hits you with an attack, you can use your reaction to halve the attack\'s damage against you.'
            },
            {
                'name': 'Sneak Attack (3d6)',
                'description': 'Your Sneak Attack damage increases to 3d6.'
            }
        ],
        6: [
            {
                'name': 'Expertise (Additional)',
                'description': 'Choose two more of your proficiencies to gain the Expertise benefit.'
            }
        ],
        7: [
            {
                'name': 'Evasion',
                'description': 'When you are subjected to an effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail.'
            },
            {
                'name': 'Sneak Attack (4d6)',
                'description': 'Your Sneak Attack damage increases to 4d6.'
            }
        ],
        8: [],  # ASI only
        9: [
            {
                'name': 'Sneak Attack (5d6)',
                'description': 'Your Sneak Attack damage increases to 5d6.'
            }
        ],
        10: [],  # ASI only
        11: [
            {
                'name': 'Reliable Talent',
                'description': 'Whenever you make an ability check that lets you add your proficiency bonus, you can treat a d20 roll of 9 or lower as a 10.'
            },
            {
                'name': 'Sneak Attack (6d6)',
                'description': 'Your Sneak Attack damage increases to 6d6.'
            }
        ],
        12: [],  # ASI only
        13: [
            {
                'name': 'Sneak Attack (7d6)',
                'description': 'Your Sneak Attack damage increases to 7d6.'
            }
        ],
        14: [
            {
                'name': 'Blindsense',
                'description': 'If you are able to hear, you are aware of the location of any hidden or invisible creature within 10 feet of you.'
            }
        ],
        15: [
            {
                'name': 'Slippery Mind',
                'description': 'You have acquired greater mental strength. You gain proficiency in Wisdom saving throws.'
            },
            {
                'name': 'Sneak Attack (8d6)',
                'description': 'Your Sneak Attack damage increases to 8d6.'
            }
        ],
        16: [],  # ASI only
        17: [
            {
                'name': 'Sneak Attack (9d6)',
                'description': 'Your Sneak Attack damage increases to 9d6.'
            }
        ],
        18: [
            {
                'name': 'Elusive',
                'description': 'No attack roll has advantage against you while you aren\'t incapacitated.'
            }
        ],
        19: [
            {
                'name': 'Sneak Attack (10d6)',
                'description': 'Your Sneak Attack damage increases to 10d6.'
            }
        ],
        20: [
            {
                'name': 'Stroke of Luck',
                'description': 'If your attack misses a target within range, you can turn the miss into a hit. Alternatively, if you fail an ability check, you can treat the d20 roll as a 20. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            }
        ]
    },
    
    'barbarian': {
        1: [
            {
                'name': 'Rage',
                'description': 'In battle, you fight with primal ferocity. On your turn, you can enter a rage as a bonus action. While raging, you gain advantage on Strength checks and saving throws, +2 bonus to melee damage rolls using Strength, and resistance to bludgeoning, piercing, and slashing damage. You can rage 2 times. You regain all expended uses when you finish a long rest.'
            },
            {
                'name': 'Unarmored Defense',
                'description': 'While you are not wearing any armor, your Armor Class equals 10 + your Dexterity modifier + your Constitution modifier. You can use a shield and still gain this benefit.'
            }
        ],
        2: [
            {
                'name': 'Reckless Attack',
                'description': 'You can throw aside all concern for defense to attack with fierce desperation. When you make your first attack on your turn, you can decide to attack recklessly. Doing so gives you advantage on melee weapon attack rolls using Strength during this turn, but attack rolls against you have advantage until your next turn.'
            },
            {
                'name': 'Danger Sense',
                'description': 'You have advantage on Dexterity saving throws against effects that you can see, such as traps and spells. To gain this benefit, you can\'t be blinded, deafened, or incapacitated.'
            }
        ],
        3: [
            {
                'name': 'Primal Path',
                'description': 'You choose a path that shapes the nature of your rage (Path of the Berserker or Path of the Totem Warrior). Your choice grants you features at 3rd level and again at 6th, 10th, and 14th levels.'
            },
            {
                'name': 'Rage (3/day)',
                'description': 'You can now rage 3 times between long rests.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn.'
            },
            {
                'name': 'Fast Movement',
                'description': 'Your speed increases by 10 feet while you aren\'t wearing heavy armor.'
            }
        ],
        6: [],  # Primal Path feature
        7: [
            {
                'name': 'Feral Instinct',
                'description': 'Your instincts are so honed that you have advantage on initiative rolls. Additionally, if you are surprised at the beginning of combat and aren\'t incapacitated, you can act normally on your first turn, but only if you enter your rage before doing anything else on that turn.'
            }
        ],
        8: [],  # ASI only
        9: [
            {
                'name': 'Brutal Critical (1 die)',
                'description': 'You can roll one additional weapon damage die when determining the extra damage for a critical hit with a melee attack.'
            },
            {
                'name': 'Rage Damage (+3)',
                'description': 'Your rage damage bonus increases to +3.'
            }
        ],
        10: [],  # Primal Path feature
        11: [
            {
                'name': 'Relentless Rage',
                'description': 'Your rage can keep you fighting despite grievous wounds. If you drop to 0 hit points while you\'re raging and don\'t die outright, you can make a DC 10 Constitution saving throw. If you succeed, you drop to 1 hit point instead. Each time you use this feature after the first, the DC increases by 5. When you finish a short or long rest, the DC resets to 10.'
            }
        ],
        12: [
            {
                'name': 'Rage (5/day)',
                'description': 'You can now rage 5 times between long rests.'
            }
        ],
        13: [
            {
                'name': 'Brutal Critical (2 dice)',
                'description': 'You can roll two additional weapon damage dice when determining the extra damage for a critical hit with a melee attack.'
            }
        ],
        14: [],  # Primal Path feature
        15: [
            {
                'name': 'Persistent Rage',
                'description': 'Your rage is so fierce that it ends early only if you fall unconscious or if you choose to end it.'
            }
        ],
        16: [
            {
                'name': 'Rage Damage (+4)',
                'description': 'Your rage damage bonus increases to +4.'
            },
            {
                'name': 'Rage (6/day)',
                'description': 'You can now rage 6 times between long rests.'
            }
        ],
        17: [
            {
                'name': 'Brutal Critical (3 dice)',
                'description': 'You can roll three additional weapon damage dice when determining the extra damage for a critical hit with a melee attack.'
            },
            {
                'name': 'Rage (Unlimited)',
                'description': 'You can rage an unlimited number of times.'
            }
        ],
        18: [
            {
                'name': 'Indomitable Might',
                'description': 'If your total for a Strength check is less than your Strength score, you can use that score in place of the total.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Primal Champion',
                'description': 'You embody the power of the wilds. Your Strength and Constitution scores increase by 4. Your maximum for those scores is now 24.'
            }
        ]
    },
    
    'bard': {
        1: [
            {
                'name': 'Spellcasting',
                'description': 'You have learned to untangle and reshape the fabric of reality in harmony with your wishes and music. Your spells are part of your vast repertoire, magic that you can tune to different situations.'
            },
            {
                'name': 'Bardic Inspiration (d6)',
                'description': 'You can inspire others through stirring words or music. As a bonus action, choose one creature other than yourself within 60 feet who can hear you. That creature gains one Bardic Inspiration die, a d6. Once within the next 10 minutes, the creature can roll the die and add the number rolled to one ability check, attack roll, or saving throw it makes. You can use this feature a number of times equal to your Charisma modifier (minimum of once). You regain any expended uses when you finish a long rest.'
            }
        ],
        2: [
            {
                'name': 'Jack of All Trades',
                'description': 'You can add half your proficiency bonus, rounded down, to any ability check you make that doesn\'t already include your proficiency bonus.'
            },
            {
                'name': 'Song of Rest (d6)',
                'description': 'You can use soothing music or oration to help revitalize your wounded allies during a short rest. If you or any friendly creatures who can hear your performance regain hit points at the end of the short rest by spending one or more Hit Dice, each of those creatures regains an extra 1d6 hit points.'
            }
        ],
        3: [
            {
                'name': 'Bard College',
                'description': 'You delve into the advanced techniques of a bard college of your choice (College of Lore or College of Valor). Your choice grants you features at 3rd level and again at 6th and 14th level.'
            },
            {
                'name': 'Expertise',
                'description': 'Choose two of your skill proficiencies. Your proficiency bonus is doubled for any ability check you make that uses either of the chosen proficiencies. At 10th level, you can choose another two skill proficiencies to gain this benefit.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Bardic Inspiration (d8)',
                'description': 'Your Bardic Inspiration die becomes a d8.'
            },
            {
                'name': 'Font of Inspiration',
                'description': 'You regain all of your expended uses of Bardic Inspiration when you finish a short or long rest.'
            }
        ],
        6: [
            {
                'name': 'Countercharm',
                'description': 'You gain the ability to use musical notes or words of power to disrupt mind-influencing effects. As an action, you can start a performance that lasts until the end of your next turn. During that time, you and any friendly creatures within 30 feet of you have advantage on saving throws against being frightened or charmed.'
            }
        ],
        7: [],  # Spell progression
        8: [],  # ASI only
        9: [
            {
                'name': 'Song of Rest (d8)',
                'description': 'Your Song of Rest die becomes a d8.'
            }
        ],
        10: [
            {
                'name': 'Bardic Inspiration (d10)',
                'description': 'Your Bardic Inspiration die becomes a d10.'
            },
            {
                'name': 'Expertise (Additional)',
                'description': 'Choose two more of your skill proficiencies to gain the Expertise benefit.'
            },
            {
                'name': 'Magical Secrets',
                'description': 'You have plundered magical knowledge from a wide spectrum of disciplines. Choose two spells from any classes, including this one. A spell you choose must be of a level you can cast, as shown on the Bard table, or a cantrip. The chosen spells count as bard spells for you and are included in the number in the Spells Known column of the Bard table.'
            }
        ],
        11: [],  # Spell progression
        12: [],  # ASI only
        13: [
            {
                'name': 'Song of Rest (d10)',
                'description': 'Your Song of Rest die becomes a d10.'
            }
        ],
        14: [
            {
                'name': 'Magical Secrets (Additional)',
                'description': 'You learn two additional spells from any class.'
            }
        ],
        15: [
            {
                'name': 'Bardic Inspiration (d12)',
                'description': 'Your Bardic Inspiration die becomes a d12.'
            }
        ],
        16: [],  # ASI only
        17: [
            {
                'name': 'Song of Rest (d12)',
                'description': 'Your Song of Rest die becomes a d12.'
            }
        ],
        18: [
            {
                'name': 'Magical Secrets (Additional)',
                'description': 'You learn two additional spells from any class.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Superior Inspiration',
                'description': 'When you roll initiative and have no uses of Bardic Inspiration left, you regain one use.'
            }
        ]
    },
    
    'druid': {
        1: [
            {
                'name': 'Druidic',
                'description': 'You know Druidic, the secret language of druids. You can speak the language and use it to leave hidden messages. You and others who know this language automatically spot such a message. Others spot the message\'s presence with a successful DC 15 Wisdom (Perception) check but can\'t decipher it without magic.'
            },
            {
                'name': 'Spellcasting',
                'description': 'Drawing on the divine essence of nature itself, you can cast spells to shape that essence to your will.'
            }
        ],
        2: [
            {
                'name': 'Wild Shape',
                'description': 'You can use your action to magically assume the shape of a beast that you have seen before. You can use this feature twice. You regain expended uses when you finish a short or long rest. You can stay in a beast shape for a number of hours equal to half your druid level (rounded down). You then revert to your normal form.'
            },
            {
                'name': 'Druid Circle',
                'description': 'You choose to identify with a circle of druids (Circle of the Land or Circle of the Moon). Your choice grants you features at 2nd level and again at 6th, 10th, and 14th level.'
            }
        ],
        3: [],  # Spell progression
        4: [
            {
                'name': 'Wild Shape Improvement',
                'description': 'You can use your Wild Shape to transform into a beast with a challenge rating as high as 1/2. You ignore the Max. CR column of the Beast Shapes table, but must abide by the other limitations there.'
            }
        ],
        5: [],  # Spell progression
        6: [],  # Druid Circle feature
        7: [],  # Spell progression
        8: [
            {
                'name': 'Wild Shape Improvement',
                'description': 'You can use your Wild Shape to transform into a beast with a challenge rating as high as 1.'
            }
        ],
        9: [],  # Spell progression
        10: [],  # Druid Circle feature
        11: [],  # Spell progression
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [],  # Druid Circle feature
        15: [],  # Spell progression
        16: [],  # ASI only
        17: [],  # Spell progression
        18: [
            {
                'name': 'Timeless Body',
                'description': 'The primal magic that you wield causes you to age more slowly. For every 10 years that pass, your body ages only 1 year.'
            },
            {
                'name': 'Beast Spells',
                'description': 'You can cast many of your druid spells in any shape you assume using Wild Shape. You can perform the somatic and verbal components of a druid spell while in a beast shape, but you aren\'t able to provide material components.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Archdruid',
                'description': 'You can use your Wild Shape an unlimited number of times. Additionally, you can ignore the verbal and somatic components of your druid spells, as well as any material components that lack a cost and aren\'t consumed by a spell. You gain this benefit in both your normal shape and your beast shape from Wild Shape.'
            }
        ]
    },
    
    'monk': {
        1: [
            {
                'name': 'Unarmored Defense',
                'description': 'While you are wearing no armor and not wielding a shield, your AC equals 10 + your Dexterity modifier + your Wisdom modifier.'
            },
            {
                'name': 'Martial Arts',
                'description': 'Your practice of martial arts gives you mastery of combat styles that use unarmed strikes and monk weapons. You gain the following benefits while you are unarmed or wielding only monk weapons and you aren\'t wearing armor or wielding a shield: You can use Dexterity instead of Strength for the attack and damage rolls. You can roll a d4 in place of the normal damage of your unarmed strike or monk weapon. When you use the Attack action with an unarmed strike or a monk weapon on your turn, you can make one unarmed strike as a bonus action.'
            }
        ],
        2: [
            {
                'name': 'Ki',
                'description': 'Your training allows you to harness the mystic energy of ki. Your access to this energy is represented by a number of ki points. Your monk level determines the number of points you have. You can spend these points to fuel various ki features. You start knowing three such features: Flurry of Blows, Patient Defense, and Step of the Wind. You regain all expended ki points when you finish a short or long rest.'
            },
            {
                'name': 'Flurry of Blows',
                'description': 'Immediately after you take the Attack action on your turn, you can spend 1 ki point to make two unarmed strikes as a bonus action.'
            },
            {
                'name': 'Patient Defense',
                'description': 'You can spend 1 ki point to take the Dodge action as a bonus action on your turn.'
            },
            {
                'name': 'Step of the Wind',
                'description': 'You can spend 1 ki point to take the Disengage or Dash action as a bonus action on your turn, and your jump distance is doubled for the turn.'
            },
            {
                'name': 'Unarmored Movement',
                'description': 'Your speed increases by 10 feet while you are not wearing armor or wielding a shield. This bonus increases when you reach certain monk levels.'
            }
        ],
        3: [
            {
                'name': 'Monastic Tradition',
                'description': 'You commit yourself to a monastic tradition (Way of the Open Hand, Way of Shadow, or Way of the Four Elements). Your tradition grants you features at 3rd level and again at 6th, 11th, and 17th level.'
            },
            {
                'name': 'Deflect Missiles',
                'description': 'You can use your reaction to deflect or catch the missile when you are hit by a ranged weapon attack. When you do so, the damage you take from the attack is reduced by 1d10 + your Dexterity modifier + your monk level. If you reduce the damage to 0, you can catch the missile if it is small enough for you to hold in one hand and you have at least one hand free. If you catch a missile in this way, you can spend 1 ki point to make a ranged attack with the weapon or piece of ammunition you just caught.'
            }
        ],
        4: [
            {
                'name': 'Slow Fall',
                'description': 'You can use your reaction when you fall to reduce any falling damage you take by an amount equal to five times your monk level.'
            }
        ],
        5: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn.'
            },
            {
                'name': 'Stunning Strike',
                'description': 'You can interfere with the flow of ki in an opponent\'s body. When you hit another creature with a melee weapon attack, you can spend 1 ki point to attempt a stunning strike. The target must succeed on a Constitution saving throw or be stunned until the end of your next turn.'
            }
        ],
        6: [
            {
                'name': 'Ki-Empowered Strikes',
                'description': 'Your unarmed strikes count as magical for the purpose of overcoming resistance and immunity to nonmagical attacks and damage.'
            }
        ],
        7: [
            {
                'name': 'Evasion',
                'description': 'Your instinctive agility lets you dodge out of the way of certain area effects. When you are subjected to an effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail.'
            },
            {
                'name': 'Stillness of Mind',
                'description': 'You can use your action to end one effect on yourself that is causing you to be charmed or frightened.'
            }
        ],
        8: [],  # ASI only
        9: [
            {
                'name': 'Unarmored Movement Improvement',
                'description': 'You gain the ability to move along vertical surfaces and across liquids on your turn without falling during the move.'
            }
        ],
        10: [
            {
                'name': 'Purity of Body',
                'description': 'Your mastery of the ki flowing through you makes you immune to disease and poison.'
            }
        ],
        11: [],  # Monastic Tradition feature
        12: [],  # ASI only
        13: [
            {
                'name': 'Tongue of the Sun and Moon',
                'description': 'You learn to touch the ki of other minds so that you understand all spoken languages. Moreover, any creature that can understand a language can understand what you say.'
            }
        ],
        14: [
            {
                'name': 'Diamond Soul',
                'description': 'Your mastery of ki grants you proficiency in all saving throws. Additionally, whenever you make a saving throw and fail, you can spend 1 ki point to reroll it and take the second result.'
            }
        ],
        15: [
            {
                'name': 'Timeless Body',
                'description': 'Your ki sustains you so that you suffer none of the frailty of old age, and you can\'t be aged magically. You can still die of old age, however. In addition, you no longer need food or water.'
            }
        ],
        16: [],  # ASI only
        17: [],  # Monastic Tradition feature
        18: [
            {
                'name': 'Empty Body',
                'description': 'You can use your action to spend 4 ki points to become invisible for 1 minute. During that time, you also have resistance to all damage but force damage. Additionally, you can spend 8 ki points to cast the astral projection spell, without needing material components. When you do so, you can\'t take any other creatures with you.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Perfect Self',
                'description': 'When you roll for initiative and have no ki points remaining, you regain 4 ki points.'
            }
        ]
    },
    
    'paladin': {
        1: [
            {
                'name': 'Divine Sense',
                'description': 'The presence of strong evil registers on your senses like a noxious odor, and powerful good rings like heavenly music in your ears. As an action, you can open your awareness to detect such forces. Until the end of your next turn, you know the location of any celestial, fiend, or undead within 60 feet of you that is not behind total cover. You can use this feature a number of times equal to 1 + your Charisma modifier. When you finish a long rest, you regain all expended uses.'
            },
            {
                'name': 'Lay on Hands',
                'description': 'Your blessed touch can heal wounds. You have a pool of healing power that replenishes when you take a long rest. With that pool, you can restore a total number of hit points equal to your paladin level × 5. As an action, you can touch a creature and draw power from the pool to restore a number of hit points to that creature, up to the maximum amount remaining in your pool. Alternatively, you can expend 5 hit points from your pool of healing to cure the target of one disease or neutralize one poison affecting it.'
            }
        ],
        2: [
            {
                'name': 'Fighting Style',
                'description': 'You adopt a particular style of fighting as your specialty. Choose one: Defense, Dueling, Great Weapon Fighting, or Protection.'
            },
            {
                'name': 'Spellcasting',
                'description': 'You have learned to draw on divine magic through meditation and prayer to cast spells as a cleric does.'
            },
            {
                'name': 'Divine Smite',
                'description': 'When you hit a creature with a melee weapon attack, you can expend one spell slot to deal radiant damage to the target, in addition to the weapon\'s damage. The extra damage is 2d8 for a 1st-level spell slot, plus 1d8 for each spell level higher than 1st, to a maximum of 5d8. The damage increases by 1d8 if the target is an undead or a fiend, to a maximum of 6d8.'
            }
        ],
        3: [
            {
                'name': 'Divine Health',
                'description': 'The divine magic flowing through you makes you immune to disease.'
            },
            {
                'name': 'Sacred Oath',
                'description': 'You swear the oath that binds you as a paladin forever (Oath of Devotion, Oath of the Ancients, or Oath of Vengeance). Your choice grants you features at 3rd level and again at 7th, 15th, and 20th level. Those features include oath spells and the Channel Divinity feature.'
            },
            {
                'name': 'Channel Divinity',
                'description': 'You gain the ability to channel divine energy directly from your deity, using that energy to fuel magical effects. Each Sacred Oath provides two Channel Divinity effects. You can use your Channel Divinity once between rests. Beginning at 7th level, you can use it twice, and at 15th level, you can use it three times.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn.'
            }
        ],
        6: [
            {
                'name': 'Aura of Protection',
                'description': 'Whenever you or a friendly creature within 10 feet of you must make a saving throw, the creature gains a bonus to the saving throw equal to your Charisma modifier (with a minimum bonus of +1). You must be conscious to grant this bonus. At 18th level, the range of this aura increases to 30 feet.'
            }
        ],
        7: [],  # Sacred Oath feature
        8: [],  # ASI only
        9: [],  # Spell progression
        10: [
            {
                'name': 'Aura of Courage',
                'description': 'You and friendly creatures within 10 feet of you can\'t be frightened while you are conscious. At 18th level, the range of this aura increases to 30 feet.'
            }
        ],
        11: [
            {
                'name': 'Improved Divine Smite',
                'description': 'You are so suffused with righteous might that all your melee weapon strikes carry divine power with them. Whenever you hit a creature with a melee weapon, the creature takes an extra 1d8 radiant damage.'
            }
        ],
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [
            {
                'name': 'Cleansing Touch',
                'description': 'You can use your action to end one spell on yourself or on one willing creature that you touch. You can use this feature a number of times equal to your Charisma modifier (a minimum of once). You regain expended uses when you finish a long rest.'
            }
        ],
        15: [],  # Sacred Oath feature
        16: [],  # ASI only
        17: [],  # Spell progression
        18: [
            {
                'name': 'Aura Improvements',
                'description': 'The range of your Aura of Protection and Aura of Courage increases to 30 feet.'
            }
        ],
        19: [],  # ASI only
        20: []  # Sacred Oath feature
    },
    
    'ranger': {
        1: [
            {
                'name': 'Favored Enemy',
                'description': 'You have significant experience studying, tracking, hunting, and even talking to a certain type of enemy. Choose a type of favored enemy: aberrations, beasts, celestials, constructs, dragons, elementals, fey, fiends, giants, monstrosities, oozes, plants, or undead. Alternatively, you can select two races of humanoid as favored enemies. You have advantage on Wisdom (Survival) checks to track your favored enemies, as well as on Intelligence checks to recall information about them.'
            },
            {
                'name': 'Natural Explorer',
                'description': 'You are particularly familiar with one type of natural environment and are adept at traveling and surviving in such regions. Choose one type of favored terrain: arctic, coast, desert, forest, grassland, mountain, swamp, or the Underdark. When you make an Intelligence or Wisdom check related to your favored terrain, your proficiency bonus is doubled if you are using a skill that you\'re proficient in.'
            }
        ],
        2: [
            {
                'name': 'Fighting Style',
                'description': 'You adopt a particular style of fighting as your specialty. Choose one: Archery, Defense, Dueling, or Two-Weapon Fighting.'
            },
            {
                'name': 'Spellcasting',
                'description': 'You have learned to use the magical essence of nature to cast spells, much as a druid does.'
            }
        ],
        3: [
            {
                'name': 'Ranger Archetype',
                'description': 'You choose an archetype that you strive to emulate (Hunter or Beast Master). Your choice grants you features at 3rd level and again at 7th, 11th, and 15th level.'
            },
            {
                'name': 'Primeval Awareness',
                'description': 'You can use your action and expend one ranger spell slot to focus your awareness on the region around you. For 1 minute per level of the spell slot you expend, you can sense whether the following types of creatures are present within 1 mile of you (or within up to 6 miles if you are in your favored terrain): aberrations, celestials, dragons, elementals, fey, fiends, and undead.'
            }
        ],
        4: [],  # ASI only
        5: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn.'
            }
        ],
        6: [
            {
                'name': 'Favored Enemy (Additional)',
                'description': 'You choose one additional favored enemy, as well as an associated language.'
            },
            {
                'name': 'Natural Explorer (Additional)',
                'description': 'You choose one additional favored terrain.'
            }
        ],
        7: [],  # Ranger Archetype feature
        8: [
            {
                'name': 'Land\'s Stride',
                'description': 'Moving through nonmagical difficult terrain costs you no extra movement. You can also pass through nonmagical plants without being slowed by them and without taking damage from them if they have thorns, spines, or a similar hazard. In addition, you have advantage on saving throws against plants that are magically created or manipulated to impede movement.'
            }
        ],
        9: [],  # Spell progression
        10: [
            {
                'name': 'Natural Explorer (Additional)',
                'description': 'You choose one additional favored terrain.'
            },
            {
                'name': 'Hide in Plain Sight',
                'description': 'You can spend 1 minute creating camouflage for yourself. You must have access to fresh mud, dirt, plants, soot, and other naturally occurring materials with which to create your camouflage. Once you are camouflaged in this way, you can try to hide by pressing yourself up against a solid surface, such as a tree or wall, that is at least as tall and wide as you are. You gain a +10 bonus to Dexterity (Stealth) checks as long as you remain there without moving or taking actions.'
            }
        ],
        11: [],  # Ranger Archetype feature
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [
            {
                'name': 'Favored Enemy (Additional)',
                'description': 'You choose one additional favored enemy, as well as an associated language.'
            },
            {
                'name': 'Vanish',
                'description': 'You can use the Hide action as a bonus action on your turn. Also, you can\'t be tracked by nonmagical means, unless you choose to leave a trail.'
            }
        ],
        15: [],  # Ranger Archetype feature
        16: [],  # ASI only
        17: [],  # Spell progression
        18: [
            {
                'name': 'Feral Senses',
                'description': 'You gain preternatural senses that help you fight creatures you can\'t see. When you attack a creature you can\'t see, your inability to see it doesn\'t impose disadvantage on your attack rolls against it. You are also aware of the location of any invisible creature within 30 feet of you, provided that the creature isn\'t hidden from you and you aren\'t blinded or deafened.'
            }
        ],
        19: [],  # ASI only
        20: [
            {
                'name': 'Foe Slayer',
                'description': 'You become an unparalleled hunter of your enemies. Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll of an attack you make against one of your favored enemies. You can choose to use this feature before or after the roll, but before any effects of the roll are applied.'
            }
        ]
    },
    
    'sorcerer': {
        1: [
            {
                'name': 'Spellcasting',
                'description': 'An event in your past, or in the life of a parent or ancestor, left an indelible mark on you, infusing you with arcane magic. This font of magic, whatever its origin, fuels your spells.'
            },
            {
                'name': 'Sorcerous Origin',
                'description': 'Choose a sorcerous origin, which describes the source of your innate magical power (Draconic Bloodline or Wild Magic). Your choice grants you features when you choose it at 1st level and again at 6th, 14th, and 18th level.'
            }
        ],
        2: [
            {
                'name': 'Font of Magic',
                'description': 'You tap into a deep wellspring of magic within yourself. This wellspring is represented by sorcery points, which allow you to create a variety of magical effects. You have 2 sorcery points, and you gain more as you reach higher levels. You can never have more sorcery points than shown on the table for your level. You regain all spent sorcery points when you finish a long rest.'
            },
            {
                'name': 'Flexible Casting',
                'description': 'You can use your sorcery points to gain additional spell slots, or sacrifice spell slots to gain additional sorcery points.'
            }
        ],
        3: [
            {
                'name': 'Metamagic',
                'description': 'You gain the ability to twist your spells to suit your needs. You gain two Metamagic options of your choice (Careful Spell, Distant Spell, Empowered Spell, Extended Spell, Heightened Spell, Quickened Spell, Subtle Spell, or Twinned Spell). You gain another one at 10th and 17th level. You can use only one Metamagic option on a spell when you cast it, unless otherwise noted.'
            }
        ],
        4: [],  # ASI only
        5: [],  # Spell progression
        6: [],  # Sorcerous Origin feature
        7: [],  # Spell progression
        8: [],  # ASI only
        9: [],  # Spell progression
        10: [
            {
                'name': 'Metamagic (Additional)',
                'description': 'You gain one additional Metamagic option.'
            }
        ],
        11: [],  # Spell progression
        12: [],  # ASI only
        13: [],  # Spell progression
        14: [],  # Sorcerous Origin feature
        15: [],  # Spell progression
        16: [],  # ASI only
        17: [
            {
                'name': 'Metamagic (Additional)',
                'description': 'You gain one additional Metamagic option.'
            }
        ],
        18: [],  # Sorcerous Origin feature
        19: [],  # ASI only
        20: [
            {
                'name': 'Sorcerous Restoration',
                'description': 'You regain 4 expended sorcery points whenever you finish a short rest.'
            }
        ]
    },
    
    'warlock': {
        1: [
            {
                'name': 'Otherworldly Patron',
                'description': 'You have struck a bargain with an otherworldly being of your choice (The Archfey, The Fiend, or The Great Old One). Your choice grants you features at 1st level and again at 6th, 10th, and 14th level.'
            },
            {
                'name': 'Pact Magic',
                'description': 'Your arcane research and the magic bestowed on you by your patron have given you facility with spells. Unlike other spellcasters, warlocks regain all spell slots on a short rest.'
            }
        ],
        2: [
            {
                'name': 'Eldritch Invocations',
                'description': 'In your study of occult lore, you have unearthed eldritch invocations, fragments of forbidden knowledge that imbue you with an abiding magical ability. You gain two eldritch invocations of your choice. When you gain certain warlock levels, you gain additional invocations of your choice. Additionally, when you gain a level in this class, you can choose one of the invocations you know and replace it with another invocation that you could learn at that level.'
            }
        ],
        3: [
            {
                'name': 'Pact Boon',
                'description': 'Your otherworldly patron bestows a gift upon you for your loyal service. You gain one of the following features of your choice: Pact of the Chain (familiar), Pact of the Blade (weapon), or Pact of the Tome (cantrips).'
            }
        ],
        4: [],  # ASI only
        5: [],  # Spell progression
        6: [],  # Otherworldly Patron feature
        7: [],  # Spell progression
        8: [],  # ASI only
        9: [],  # Spell progression
        10: [],  # Otherworldly Patron feature
        11: [
            {
                'name': 'Mystic Arcanum (6th level)',
                'description': 'Your patron bestows upon you a magical secret called an arcanum. Choose one 6th-level spell from the warlock spell list as this arcanum. You can cast your arcanum spell once without expending a spell slot. You must finish a long rest before you can do so again.'
            }
        ],
        12: [],  # ASI only
        13: [
            {
                'name': 'Mystic Arcanum (7th level)',
                'description': 'You gain a 7th-level spell as your Mystic Arcanum.'
            }
        ],
        14: [],  # Otherworldly Patron feature
        15: [
            {
                'name': 'Mystic Arcanum (8th level)',
                'description': 'You gain an 8th-level spell as your Mystic Arcanum.'
            }
        ],
        16: [],  # ASI only
        17: [
            {
                'name': 'Mystic Arcanum (9th level)',
                'description': 'You gain a 9th-level spell as your Mystic Arcanum.'
            }
        ],
        18: [],  # Spell progression
        19: [],  # ASI only
        20: [
            {
                'name': 'Eldritch Master',
                'description': 'You can draw on your inner reserve of mystical power while entreating your patron to regain expended spell slots. You can spend 1 minute entreating your patron for aid to regain all your expended spell slots from your Pact Magic feature. Once you regain spell slots with this feature, you must finish a long rest before you can do so again.'
            }
        ]
    }
}


def get_class_features(class_name, level):
    """
    Get class features for a specific class at a specific level.
    
    Args:
        class_name: Name of the class (e.g., 'Fighter', 'Wizard')
        level: Character level (1-20)
    
    Returns:
        List of feature dictionaries with 'name' and 'description' keys
    """
    if class_name not in CLASS_FEATURES:
        return []
    
    if level not in CLASS_FEATURES[class_name]:
        return []
    
    return CLASS_FEATURES[class_name][level]


def get_all_features_up_to_level(class_name, level):
    """
    Get all class features from level 1 up to the specified level.
    Useful for creating a new character at a higher level.
    
    Args:
        class_name: Name of the class
        level: Character level
    
    Returns:
        Dictionary mapping level to list of features
    """
    if class_name not in CLASS_FEATURES:
        return {}
    
    features_by_level = {}
    for lvl in range(1, level + 1):
        if lvl in CLASS_FEATURES[class_name]:
            features = CLASS_FEATURES[class_name][lvl]
            if features:  # Only include levels with features
                features_by_level[lvl] = features
    
    return features_by_level


# Subclass features by subclass name and level
SUBCLASS_FEATURES = {
    # Fighter Subclasses
    'Champion': {
        3: [
            {
                'name': 'Improved Critical',
                'description': 'Your weapon attacks score a critical hit on a roll of 19 or 20.'
            }
        ],
        7: [
            {
                'name': 'Remarkable Athlete',
                'description': 'You can add half your proficiency bonus (rounded up) to any Strength, Dexterity, or Constitution check you make that doesn\'t already use your proficiency bonus. In addition, when you make a running long jump, the distance you can cover increases by a number of feet equal to your Strength modifier.'
            }
        ],
        10: [
            {
                'name': 'Additional Fighting Style',
                'description': 'You can choose a second option from the Fighting Style class feature.'
            }
        ],
        15: [
            {
                'name': 'Superior Critical',
                'description': 'Your weapon attacks score a critical hit on a roll of 18-20.'
            }
        ],
        18: [
            {
                'name': 'Survivor',
                'description': 'At the start of each of your turns, you regain hit points equal to 5 + your Constitution modifier if you have no more than half of your hit points left. You don\'t gain this benefit if you have 0 hit points.'
            }
        ]
    },
    
    'Battle Master': {
        3: [
            {
                'name': 'Combat Superiority',
                'description': 'You learn maneuvers that are fueled by special dice called superiority dice. You learn three maneuvers of your choice. You have four superiority dice, which are d8s. A superiority die is expended when you use it. You regain all of your expended superiority dice when you finish a short or long rest.'
            },
            {
                'name': 'Student of War',
                'description': 'You gain proficiency with one type of artisan\'s tools of your choice.'
            }
        ],
        7: [
            {
                'name': 'Know Your Enemy',
                'description': 'If you spend at least 1 minute observing or interacting with another creature outside combat, you can learn certain information about its capabilities compared to your own.'
            },
            {
                'name': 'Additional Maneuvers',
                'description': 'You learn two additional maneuvers of your choice. You also gain one additional superiority die.'
            }
        ],
        10: [
            {
                'name': 'Improved Combat Superiority',
                'description': 'Your superiority dice turn into d10s.'
            },
            {
                'name': 'Additional Maneuvers',
                'description': 'You learn two additional maneuvers of your choice.'
            }
        ],
        15: [
            {
                'name': 'Relentless',
                'description': 'When you roll initiative and have no superiority dice remaining, you regain 1 superiority die.'
            },
            {
                'name': 'Additional Maneuvers',
                'description': 'You learn two additional maneuvers of your choice. You also gain one additional superiority die.'
            }
        ],
        18: [
            {
                'name': 'Improved Combat Superiority',
                'description': 'Your superiority dice turn into d12s.'
            }
        ]
    },
    
    'Eldritch Knight': {
        3: [
            {
                'name': 'Spellcasting',
                'description': 'You augment your martial prowess with the ability to cast spells. You learn two cantrips of your choice from the wizard spell list. You also learn three 1st-level wizard spells of your choice, two of which you must choose from the abjuration and evocation schools.'
            },
            {
                'name': 'Weapon Bond',
                'description': 'You learn a ritual that creates a magical bond between yourself and one weapon. Once you have bonded a weapon to yourself, you can\'t be disarmed of that weapon unless you are incapacitated. You can summon that weapon as a bonus action on your turn, causing it to teleport instantly to your hand.'
            }
        ],
        7: [
            {
                'name': 'War Magic',
                'description': 'When you use your action to cast a cantrip, you can make one weapon attack as a bonus action.'
            }
        ],
        10: [
            {
                'name': 'Eldritch Strike',
                'description': 'When you hit a creature with a weapon attack, that creature has disadvantage on the next saving throw it makes against a spell you cast before the end of your next turn.'
            }
        ],
        15: [
            {
                'name': 'Arcane Charge',
                'description': 'When you use your Action Surge, you can teleport up to 30 feet to an unoccupied space you can see. You can teleport before or after the additional action.'
            }
        ],
        18: [
            {
                'name': 'Improved War Magic',
                'description': 'When you use your action to cast a spell, you can make one weapon attack as a bonus action.'
            }
        ]
    },
    
    # Wizard Subclasses
    'School of Evocation': {
        2: [
            {
                'name': 'Evocation Savant',
                'description': 'The gold and time you must spend to copy an evocation spell into your spellbook is halved.'
            },
            {
                'name': 'Sculpt Spells',
                'description': 'When you cast an evocation spell that affects other creatures that you can see, you can choose a number of them equal to 1 + the spell\'s level. The chosen creatures automatically succeed on their saving throws against the spell, and they take no damage if they would normally take half damage on a successful save.'
            }
        ],
        6: [
            {
                'name': 'Potent Cantrip',
                'description': 'Your damaging cantrips affect even creatures that avoid the brunt of the effect. When a creature succeeds on a saving throw against your cantrip, the creature takes half the cantrip\'s damage (if any) but suffers no additional effect from the cantrip.'
            }
        ],
        10: [
            {
                'name': 'Empowered Evocation',
                'description': 'You can add your Intelligence modifier to the damage roll of any wizard evocation spell you cast.'
            }
        ],
        14: [
            {
                'name': 'Overchannel',
                'description': 'When you cast a wizard spell of 5th level or lower that deals damage, you can deal maximum damage with that spell. The first time you do so, you suffer no adverse effect. If you use this feature again before you finish a long rest, you take 2d12 necrotic damage for each level of the spell, immediately after you cast it.'
            }
        ]
    },
    
    'School of Abjuration': {
        2: [
            {
                'name': 'Abjuration Savant',
                'description': 'The gold and time you must spend to copy an abjuration spell into your spellbook is halved.'
            },
            {
                'name': 'Arcane Ward',
                'description': 'You can weave magic around yourself for protection. When you cast an abjuration spell of 1st level or higher, you can simultaneously use a strand of the spell\'s magic to create a magical ward on yourself that lasts until you finish a long rest. The ward has hit points equal to twice your wizard level + your Intelligence modifier. Whenever you take damage, the ward takes the damage instead.'
            }
        ],
        6: [
            {
                'name': 'Projected Ward',
                'description': 'When a creature that you can see within 30 feet of you takes damage, you can use your reaction to cause your Arcane Ward to absorb that damage.'
            }
        ],
        10: [
            {
                'name': 'Improved Abjuration',
                'description': 'When you cast an abjuration spell that requires you to make an ability check as a part of casting that spell, you add your proficiency bonus to that ability check.'
            }
        ],
        14: [
            {
                'name': 'Spell Resistance',
                'description': 'You have advantage on saving throws against spells. Furthermore, you have resistance against the damage of spells.'
            }
        ]
    },
    
    # Rogue Subclasses
    'Assassin': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'You gain proficiency with the disguise kit and the poisoner\'s kit.'
            },
            {
                'name': 'Assassinate',
                'description': 'You have advantage on attack rolls against any creature that hasn\'t taken a turn in the combat yet. In addition, any hit you score against a creature that is surprised is a critical hit.'
            }
        ],
        9: [
            {
                'name': 'Infiltration Expertise',
                'description': 'You can unfailingly create false identities for yourself. You must spend seven days and 25 gp to establish the history, profession, and affiliations for an identity.'
            }
        ],
        13: [
            {
                'name': 'Impostor',
                'description': 'You gain the ability to unerringly mimic another person\'s speech, writing, and behavior. You must spend at least three hours studying these three components of the person\'s behavior, listening to speech, examining handwriting, and observing mannerisms.'
            }
        ],
        17: [
            {
                'name': 'Death Strike',
                'description': 'When you attack and hit a creature that is surprised, it must make a Constitution saving throw (DC 8 + your Dexterity modifier + your proficiency bonus). On a failed save, double the damage of your attack against the creature.'
            }
        ]
    },
    
    'Thief': {
        3: [
            {
                'name': 'Fast Hands',
                'description': 'You can use the bonus action granted by your Cunning Action to make a Dexterity (Sleight of Hand) check, use your thieves\' tools to disarm a trap or open a lock, or take the Use an Object action.'
            },
            {
                'name': 'Second-Story Work',
                'description': 'You gain the ability to climb faster than normal; climbing no longer costs you extra movement. In addition, when you make a running jump, the distance you cover increases by a number of feet equal to your Dexterity modifier.'
            }
        ],
        9: [
            {
                'name': 'Supreme Sneak',
                'description': 'You have advantage on a Dexterity (Stealth) check if you move no more than half your speed on the same turn.'
            }
        ],
        13: [
            {
                'name': 'Use Magic Device',
                'description': 'You have learned enough about the workings of magic that you can improvise the use of items even when they are not intended for you. You ignore all class, race, and level requirements on the use of magic items.'
            }
        ],
        17: [
            {
                'name': 'Thief\'s Reflexes',
                'description': 'You have become adept at laying ambushes and quickly escaping danger. You can take two turns during the first round of any combat. You take your first turn at your normal initiative and your second turn at your initiative minus 10.'
            }
        ]
    },
    
    'Arcane Trickster': {
        3: [
            {
                'name': 'Spellcasting',
                'description': 'You gain the ability to cast spells. You learn three cantrips: mage hand and two other cantrips of your choice from the wizard spell list. You also learn three 1st-level wizard spells of your choice, two of which you must choose from the enchantment and illusion schools.'
            },
            {
                'name': 'Mage Hand Legerdemain',
                'description': 'When you cast mage hand, you can make the spectral hand invisible, and you can perform additional tasks with it: stow or retrieve an object, pick locks and disarm traps, or use thieves\' tools.'
            }
        ],
        9: [
            {
                'name': 'Magical Ambush',
                'description': 'If you are hidden from a creature when you cast a spell on it, the creature has disadvantage on any saving throw it makes against the spell this turn.'
            }
        ],
        13: [
            {
                'name': 'Versatile Trickster',
                'description': 'You gain the ability to distract targets with your mage hand. As a bonus action on your turn, you can designate a creature within 5 feet of the spectral hand created by the spell. Doing so gives you advantage on attack rolls against that creature until the end of the turn.'
            }
        ],
        17: [
            {
                'name': 'Spell Thief',
                'description': 'You gain the ability to magically steal the knowledge of how to cast a spell from another spellcaster. Immediately after a creature casts a spell that targets you or includes you in its area of effect, you can use your reaction to force the creature to make a saving throw with its spellcasting ability modifier. On a failed save, you negate the spell\'s effect against you, and you steal the knowledge of the spell if it is at least 1st level and of a level you can cast.'
            }
        ]
    },
    
    # Cleric Subclasses
    'Life Domain': {
        1: [
            {
                'name': 'Bonus Proficiency',
                'description': 'You gain proficiency with heavy armor.'
            },
            {
                'name': 'Disciple of Life',
                'description': 'Your healing spells are more effective. Whenever you use a spell of 1st level or higher to restore hit points to a creature, the creature regains additional hit points equal to 2 + the spell\'s level.'
            }
        ],
        2: [
            {
                'name': 'Channel Divinity: Preserve Life',
                'description': 'You can use your Channel Divinity to heal the badly injured. As an action, you present your holy symbol and evoke healing energy that can restore a number of hit points equal to five times your cleric level. Choose any creatures within 30 feet of you, and divide those hit points among them. This feature can restore a creature to no more than half of its hit point maximum.'
            }
        ],
        6: [
            {
                'name': 'Blessed Healer',
                'description': 'The healing spells you cast on others heal you as well. When you cast a spell of 1st level or higher that restores hit points to a creature other than you, you regain hit points equal to 2 + the spell\'s level.'
            }
        ],
        8: [
            {
                'name': 'Divine Strike',
                'description': 'You gain the ability to infuse your weapon strikes with divine energy. Once on each of your turns when you hit a creature with a weapon attack, you can cause the attack to deal an extra 1d8 radiant damage to the target. When you reach 14th level, the extra damage increases to 2d8.'
            }
        ],
        17: [
            {
                'name': 'Supreme Healing',
                'description': 'When you would normally roll one or more dice to restore hit points with a spell, you instead use the highest number possible for each die.'
            }
        ]
    },
    
    'War Domain': {
        1: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'You gain proficiency with martial weapons and heavy armor.'
            },
            {
                'name': 'War Priest',
                'description': 'When you use the Attack action, you can make one weapon attack as a bonus action. You can use this feature a number of times equal to your Wisdom modifier (minimum of once). You regain all expended uses when you finish a long rest.'
            }
        ],
        2: [
            {
                'name': 'Channel Divinity: Guided Strike',
                'description': 'You can use your Channel Divinity to strike with supernatural accuracy. When you make an attack roll, you can use your Channel Divinity to gain a +10 bonus to the roll. You make this choice after you see the roll, but before the DM says whether the attack hits or misses.'
            }
        ],
        6: [
            {
                'name': 'Channel Divinity: War God\'s Blessing',
                'description': 'When a creature within 30 feet of you makes an attack roll, you can use your reaction to grant that creature a +10 bonus to the roll, using your Channel Divinity. You make this choice after you see the roll, but before the DM says whether the attack hits or misses.'
            }
        ],
        8: [
            {
                'name': 'Divine Strike',
                'description': 'You gain the ability to infuse your weapon strikes with divine energy. Once on each of your turns when you hit a creature with a weapon attack, you can cause the attack to deal an extra 1d8 damage of the same type dealt by the weapon to the target. When you reach 14th level, the extra damage increases to 2d8.'
            }
        ],
        17: [
            {
                'name': 'Avatar of Battle',
                'description': 'You gain resistance to bludgeoning, piercing, and slashing damage from nonmagical weapons.'
            }
        ]
    },
    
    # Barbarian Subclasses
    'Path of the Berserker': {
        3: [
            {
                'name': 'Frenzy',
                'description': 'You can go into a frenzy when you rage. If you do so, for the duration of your rage you can make a single melee weapon attack as a bonus action on each of your turns after this one. When your rage ends, you suffer one level of exhaustion.'
            }
        ],
        6: [
            {
                'name': 'Mindless Rage',
                'description': 'You can\'t be charmed or frightened while raging. If you are charmed or frightened when you enter your rage, the effect is suspended for the duration of the rage.'
            }
        ],
        10: [
            {
                'name': 'Intimidating Presence',
                'description': 'You can use your action to frighten someone with your menacing presence. When you do so, choose one creature that you can see within 30 feet of you. If the creature can see or hear you, it must succeed on a Wisdom saving throw (DC equal to 8 + your proficiency bonus + your Charisma modifier) or be frightened of you until the end of your next turn.'
            }
        ],
        14: [
            {
                'name': 'Retaliation',
                'description': 'When you take damage from a creature that is within 5 feet of you, you can use your reaction to make a melee weapon attack against that creature.'
            }
        ]
    },
    
    'Path of the Totem Warrior': {
        3: [
            {
                'name': 'Spirit Seeker',
                'description': 'Yours is a path that seeks attunement with the natural world, giving you a kinship with beasts. You gain the ability to cast the beast sense and speak with animals spells, but only as rituals.'
            },
            {
                'name': 'Totem Spirit',
                'description': 'You choose a totem spirit and gain its feature. You must make or acquire a physical totem object that incorporates fur or feathers, claws, teeth, or bones of the totem animal. Choose from Bear (resistance to all damage except psychic while raging), Eagle (enemies have disadvantage on opportunity attacks, you can Dash as bonus action), or Wolf (allies have advantage on melee attacks against enemies within 5 feet of you while you\'re raging).'
            }
        ],
        6: [
            {
                'name': 'Aspect of the Beast',
                'description': 'You gain a magical benefit based on the totem animal of your choice. Choose from Bear (double carrying capacity, advantage on Strength checks to push/pull/lift/break), Eagle (you can see up to 1 mile away with no difficulty, dim light doesn\'t impose disadvantage on Perception checks), or Wolf (you can track creatures while traveling at a fast pace, you can move stealthily while traveling at a normal pace).'
            }
        ],
        10: [
            {
                'name': 'Spirit Walker',
                'description': 'You can cast the commune with nature spell, but only as a ritual. When you do so, a spiritual version of one of the animals you chose for Totem Spirit or Aspect of the Beast appears to you to convey the information you seek.'
            }
        ],
        14: [
            {
                'name': 'Totemic Attunement',
                'description': 'You gain a magical benefit based on a totem animal of your choice. Choose from Bear (while raging, any creature within 5 feet that\'s hostile to you has disadvantage on attack rolls against targets other than you or another Totemic Attunement barbarian), Eagle (while raging, you have a flying speed equal to your current walking speed), or Wolf (while raging, you can use a bonus action to knock a Large or smaller creature prone when you hit it with a melee weapon attack).'
            }
        ]
    },
    
    # Bard Subclasses
    'College of Lore': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'You gain proficiency with three skills of your choice.'
            },
            {
                'name': 'Cutting Words',
                'description': 'You learn how to use your wit to distract, confuse, and otherwise sap the confidence and competence of others. When a creature that you can see within 60 feet of you makes an attack roll, an ability check, or a damage roll, you can use your reaction to expend one of your uses of Bardic Inspiration, rolling a Bardic Inspiration die and subtracting the number rolled from the creature\'s roll.'
            }
        ],
        6: [
            {
                'name': 'Additional Magical Secrets',
                'description': 'You learn two spells of your choice from any class. A spell you choose must be of a level you can cast, as shown on the Bard table, or a cantrip. The chosen spells count as bard spells for you but don\'t count against the number of bard spells you know.'
            }
        ],
        14: [
            {
                'name': 'Peerless Skill',
                'description': 'When you make an ability check, you can expend one use of Bardic Inspiration. Roll a Bardic Inspiration die and add the number rolled to your ability check. You can choose to do so after you roll the die for the ability check, but before the DM tells you whether you succeed or fail.'
            }
        ]
    },
    
    'College of Valor': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'You gain proficiency with medium armor, shields, and martial weapons.'
            },
            {
                'name': 'Combat Inspiration',
                'description': 'You learn to inspire others in battle. A creature that has a Bardic Inspiration die from you can roll that die and add the number rolled to a weapon damage roll it just made. Alternatively, when an attack roll is made against the creature, it can use its reaction to roll the Bardic Inspiration die and add the number rolled to its AC against that attack, after seeing the roll but before knowing whether it hits or misses.'
            }
        ],
        6: [
            {
                'name': 'Extra Attack',
                'description': 'You can attack twice, instead of once, whenever you take the Attack action on your turn.'
            }
        ],
        14: [
            {
                'name': 'Battle Magic',
                'description': 'You have mastered the art of weaving spellcasting and weapon use into a single harmonious act. When you use your action to cast a bard spell, you can make one weapon attack as a bonus action.'
            }
        ]
    },
    
    # Druid Subclasses
    'Circle of the Land': {
        2: [
            {
                'name': 'Bonus Cantrip',
                'description': 'You learn one additional druid cantrip of your choice.'
            },
            {
                'name': 'Natural Recovery',
                'description': 'You can regain some of your magical energy by sitting in meditation and communing with nature. During a short rest, you choose expended spell slots to recover. The spell slots can have a combined level that is equal to or less than half your druid level (rounded up), and none of the slots can be 6th level or higher. You can\'t use this feature again until you finish a long rest.'
            },
            {
                'name': 'Circle Spells',
                'description': 'Your mystical connection to the land infuses you with the ability to cast certain spells. You gain access to circle spells connected to the land where you became a druid (Arctic, Coast, Desert, Forest, Grassland, Mountain, Swamp, or Underdark). Once you gain access to a circle spell, you always have it prepared, and it doesn\'t count against the number of spells you can prepare each day.'
            }
        ],
        6: [
            {
                'name': 'Land\'s Stride',
                'description': 'Moving through nonmagical difficult terrain costs you no extra movement. You can also pass through nonmagical plants without being slowed by them and without taking damage from them if they have thorns, spines, or a similar hazard. In addition, you have advantage on saving throws against plants that are magically created or manipulated to impede movement.'
            }
        ],
        10: [
            {
                'name': 'Nature\'s Ward',
                'description': 'You can\'t be charmed or frightened by elementals or fey, and you are immune to poison and disease.'
            }
        ],
        14: [
            {
                'name': 'Nature\'s Sanctuary',
                'description': 'Creatures of the natural world sense your connection to nature and become hesitant to attack you. When a beast or plant creature attacks you, that creature must make a Wisdom saving throw against your druid spell save DC. On a failed save, the creature must choose a different target, or the attack automatically misses.'
            }
        ]
    },
    
    'Circle of the Moon': {
        2: [
            {
                'name': 'Combat Wild Shape',
                'description': 'You gain the ability to use Wild Shape on your turn as a bonus action, rather than as an action. Additionally, while you are transformed by Wild Shape, you can use a bonus action to expend one spell slot to regain 1d8 hit points per level of the spell slot expended.'
            },
            {
                'name': 'Circle Forms',
                'description': 'The rites of your circle grant you the ability to transform into more dangerous animal forms. You can transform into a beast with a challenge rating as high as 1 (you ignore the Max. CR column of the Beast Shapes table, but must abide by the other limitations there). Starting at 6th level, you can transform into a beast with a challenge rating as high as your druid level divided by 3, rounded down.'
            }
        ],
        6: [
            {
                'name': 'Primal Strike',
                'description': 'Your attacks in beast form count as magical for the purpose of overcoming resistance and immunity to nonmagical attacks and damage.'
            }
        ],
        10: [
            {
                'name': 'Elemental Wild Shape',
                'description': 'You can expend two uses of Wild Shape at the same time to transform into an air elemental, an earth elemental, a fire elemental, or a water elemental.'
            }
        ],
        14: [
            {
                'name': 'Thousand Forms',
                'description': 'You have learned to use magic to alter your physical form in more subtle ways. You can cast the alter self spell at will.'
            }
        ]
    },
    
    # Monk Subclasses
    'Way of the Open Hand': {
        3: [
            {
                'name': 'Open Hand Technique',
                'description': 'You can manipulate your enemy\'s ki when you harness your own. Whenever you hit a creature with one of the attacks granted by your Flurry of Blows, you can impose one of the following effects on that target: it must succeed on a Dexterity saving throw or be knocked prone, it must make a Strength saving throw or be pushed up to 15 feet away from you, or it can\'t take reactions until the end of your next turn.'
            }
        ],
        6: [
            {
                'name': 'Wholeness of Body',
                'description': 'You gain the ability to heal yourself. As an action, you can regain hit points equal to three times your monk level. You must finish a long rest before you can use this feature again.'
            }
        ],
        11: [
            {
                'name': 'Tranquility',
                'description': 'At the end of a long rest, you gain the effect of a sanctuary spell that lasts until the start of your next long rest (the spell can end early as normal). The saving throw DC for the spell equals 8 + your Wisdom modifier + your proficiency bonus.'
            }
        ],
        17: [
            {
                'name': 'Quivering Palm',
                'description': 'You gain the ability to set up lethal vibrations in someone\'s body. When you hit a creature with an unarmed strike, you can spend 3 ki points to start these imperceptible vibrations, which last for a number of days equal to your monk level. The vibrations are harmless unless you use your action to end them. To do so, you and the target must be on the same plane of existence. When you use this action, the creature must make a Constitution saving throw. If it fails, it is reduced to 0 hit points. If it succeeds, it takes 10d10 necrotic damage.'
            }
        ]
    },
    
    'Way of Shadow': {
        3: [
            {
                'name': 'Shadow Arts',
                'description': 'You can use your ki to duplicate the effects of certain spells. As an action, you can spend 2 ki points to cast darkness, darkvision, pass without trace, or silence, without providing material components. Additionally, you gain the minor illusion cantrip if you don\'t already know it.'
            }
        ],
        6: [
            {
                'name': 'Shadow Step',
                'description': 'You gain the ability to step from one shadow into another. When you are in dim light or darkness, as a bonus action you can teleport up to 60 feet to an unoccupied space you can see that is also in dim light or darkness. You then have advantage on the first melee attack you make before the end of the turn.'
            }
        ],
        11: [
            {
                'name': 'Cloak of Shadows',
                'description': 'You have learned to become one with the shadows. When you are in an area of dim light or darkness, you can use your action to become invisible. You remain invisible until you make an attack, cast a spell, or are in an area of bright light.'
            }
        ],
        17: [
            {
                'name': 'Opportunist',
                'description': 'You can exploit a creature\'s momentary distraction when it is hit by an attack. Whenever a creature within 5 feet of you is hit by an attack made by a creature other than you, you can use your reaction to make a melee attack against that creature.'
            }
        ]
    },
    
    # Paladin Subclasses
    'Oath of Devotion': {
        3: [
            {
                'name': 'Channel Divinity: Sacred Weapon',
                'description': 'As an action, you can imbue one weapon that you are holding with positive energy, using your Channel Divinity. For 1 minute, you add your Charisma modifier to attack rolls made with that weapon (with a minimum bonus of +1). The weapon also emits bright light in a 20-foot radius and dim light 20 feet beyond that. If the weapon is not already magical, it becomes magical for the duration.'
            },
            {
                'name': 'Channel Divinity: Turn the Unholy',
                'description': 'As an action, you present your holy symbol and speak a prayer censuring fiends and undead, using your Channel Divinity. Each fiend or undead that can see or hear you within 30 feet of you must make a Wisdom saving throw. If the creature fails its saving throw, it is turned for 1 minute or until it takes damage.'
            }
        ],
        7: [
            {
                'name': 'Aura of Devotion',
                'description': 'You and friendly creatures within 10 feet of you can\'t be charmed while you are conscious. At 18th level, the range of this aura increases to 30 feet.'
            }
        ],
        15: [
            {
                'name': 'Purity of Spirit',
                'description': 'You are always under the effects of a protection from evil and good spell.'
            }
        ],
        20: [
            {
                'name': 'Holy Nimbus',
                'description': 'As an action, you can emanate an aura of sunlight. For 1 minute, bright light shines from you in a 30-foot radius, and dim light shines 30 feet beyond that. Whenever an enemy creature starts its turn in the bright light, the creature takes 10 radiant damage. In addition, for the duration, you have advantage on saving throws against spells cast by fiends or undead. Once you use this feature, you can\'t use it again until you finish a long rest.'
            }
        ]
    },
    
    'Oath of Vengeance': {
        3: [
            {
                'name': 'Channel Divinity: Abjure Enemy',
                'description': 'As an action, you present your holy symbol and speak a prayer of denunciation, using your Channel Divinity. Choose one creature within 60 feet of you that you can see. That creature must make a Wisdom saving throw, unless it is immune to being frightened. Fiends and undead have disadvantage on this saving throw. On a failed save, the creature is frightened for 1 minute or until it takes any damage. While frightened, the creature\'s speed is 0, and it can\'t benefit from any bonus to its speed.'
            },
            {
                'name': 'Channel Divinity: Vow of Enmity',
                'description': 'As a bonus action, you can utter a vow of enmity against a creature you can see within 10 feet of you, using your Channel Divinity. You gain advantage on attack rolls against the creature for 1 minute or until it drops to 0 hit points or falls unconscious.'
            }
        ],
        7: [
            {
                'name': 'Relentless Avenger',
                'description': 'Your supernatural focus helps you close off a foe\'s retreat. When you hit a creature with an opportunity attack, you can move up to half your speed immediately after the attack and as part of the same reaction. This movement doesn\'t provoke opportunity attacks.'
            }
        ],
        15: [
            {
                'name': 'Soul of Vengeance',
                'description': 'The authority with which you speak your Vow of Enmity gives you greater power over your foe. When a creature under the effect of your Vow of Enmity makes an attack, you can use your reaction to make a melee weapon attack against that creature if it is within range.'
            }
        ],
        20: [
            {
                'name': 'Avenging Angel',
                'description': 'You can assume the form of an angelic avenger. Using your action, you undergo a transformation. For 1 hour, you gain the following benefits: you have a flying speed of 60 feet, you emanate an aura of menace in a 30-foot radius (the first time any enemy creature enters the aura or starts its turn there during a battle, the creature must succeed on a Wisdom saving throw or become frightened of you for 1 minute or until it takes any damage), and when you take the Attack action, you can make one additional attack as part of that action. Once you use this feature, you can\'t use it again until you finish a long rest.'
            }
        ]
    },
    
    # Ranger Subclasses
    'Hunter': {
        3: [
            {
                'name': 'Hunter\'s Prey',
                'description': 'You gain one of the following features of your choice: Colossus Slayer (once per turn when you hit with a weapon attack, you can deal an extra 1d8 damage if the target is below its hit point maximum), Giant Killer (when a Large or larger creature within 5 feet hits or misses you with an attack, you can use your reaction to attack that creature immediately after its attack), or Horde Breaker (once on each of your turns when you make a weapon attack, you can make another attack with the same weapon against a different creature within 5 feet of the original target).'
            }
        ],
        7: [
            {
                'name': 'Defensive Tactics',
                'description': 'You gain one of the following features of your choice: Escape the Horde (opportunity attacks against you are made with disadvantage), Multiattack Defense (when a creature hits you with an attack, you gain a +4 bonus to AC against all subsequent attacks made by that creature for the rest of the turn), or Steel Will (you have advantage on saving throws against being frightened).'
            }
        ],
        11: [
            {
                'name': 'Multiattack',
                'description': 'You gain one of the following features of your choice: Volley (you can use your action to make a ranged attack against any number of creatures within 10 feet of a point you can see within your weapon\'s range), or Whirlwind Attack (you can use your action to make a melee attack against any number of creatures within 5 feet of you, with a separate attack roll for each target).'
            }
        ],
        15: [
            {
                'name': 'Superior Hunter\'s Defense',
                'description': 'You gain one of the following features of your choice: Evasion (when you are subjected to an effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail), Stand Against the Tide (when a hostile creature misses you with a melee attack, you can use your reaction to force that creature to repeat the same attack against another creature of your choice), or Uncanny Dodge (when an attacker that you can see hits you with an attack, you can use your reaction to halve the attack\'s damage against you).'
            }
        ]
    },
    
    'Beast Master': {
        3: [
            {
                'name': 'Ranger\'s Companion',
                'description': 'You gain a beast companion that accompanies you on your adventures and is trained to fight alongside you. Choose a beast that is no larger than Medium and that has a challenge rating of 1/4 or lower. Add your proficiency bonus to the beast\'s AC, attack rolls, and damage rolls, as well as to any saving throws and skills it is proficient in. Its hit point maximum equals its normal maximum or four times your ranger level, whichever is higher. The beast obeys your commands as best as it can. It takes its turn on your initiative. On your turn, you can verbally command the beast where to move (no action required by you). You can use your action to verbally command it to take the Attack, Dash, Disengage, or Help action.'
            }
        ],
        7: [
            {
                'name': 'Exceptional Training',
                'description': 'On any of your turns when your beast companion doesn\'t attack, you can use a bonus action to command the beast to take the Dash, Disengage, or Help action on its turn. In addition, the beast\'s attacks now count as magical for the purpose of overcoming resistance and immunity to nonmagical attacks and damage.'
            }
        ],
        11: [
            {
                'name': 'Bestial Fury',
                'description': 'When you command your beast companion to take the Attack action, the beast can make two attacks, or it can take the Multiattack action if it has that action.'
            }
        ],
        15: [
            {
                'name': 'Share Spells',
                'description': 'When you cast a spell targeting yourself, you can also affect your beast companion with the spell if the beast is within 30 feet of you.'
            }
        ]
    },
    
    # Sorcerer Subclasses
    'Draconic Bloodline': {
        1: [
            {
                'name': 'Dragon Ancestor',
                'description': 'You choose one type of dragon as your ancestor. The damage type associated with each dragon is used by features you gain later. You can speak, read, and write Draconic. Additionally, whenever you make a Charisma check when interacting with dragons, your proficiency bonus is doubled if it applies to the check.'
            },
            {
                'name': 'Draconic Resilience',
                'description': 'Your hit point maximum increases by 1 and increases by 1 again whenever you gain a level in this class. Additionally, parts of your skin are covered by a thin sheen of dragon-like scales. When you aren\'t wearing armor, your AC equals 13 + your Dexterity modifier.'
            }
        ],
        6: [
            {
                'name': 'Elemental Affinity',
                'description': 'When you cast a spell that deals damage of the type associated with your draconic ancestry, you can add your Charisma modifier to one damage roll of that spell. At the same time, you can spend 1 sorcery point to gain resistance to that damage type for 1 hour.'
            }
        ],
        14: [
            {
                'name': 'Dragon Wings',
                'description': 'You gain the ability to sprout a pair of dragon wings from your back, gaining a flying speed equal to your current speed. You can create these wings as a bonus action on your turn. They last until you dismiss them as a bonus action on your turn. You can\'t manifest your wings while wearing armor unless the armor is made to accommodate them.'
            }
        ],
        18: [
            {
                'name': 'Draconic Presence',
                'description': 'You can channel the dread presence of your dragon ancestor, causing those around you to become awestruck or frightened. As an action, you can spend 5 sorcery points to draw on this power and exude an aura of awe or fear (your choice) to a distance of 60 feet. For 1 minute or until you lose your concentration, each hostile creature that starts its turn in this aura must succeed on a Wisdom saving throw or be charmed (if you chose awe) or frightened (if you chose fear) until the aura ends. A creature that succeeds on this saving throw is immune to your aura for 24 hours.'
            }
        ]
    },
    
    'Wild Magic': {
        1: [
            {
                'name': 'Wild Magic Surge',
                'description': 'Your spellcasting can unleash surges of untamed magic. Immediately after you cast a sorcerer spell of 1st level or higher, the DM can have you roll a d20. If you roll a 1, roll on the Wild Magic Surge table to create a random magical effect.'
            },
            {
                'name': 'Tides of Chaos',
                'description': 'You can manipulate the forces of chance and chaos to gain advantage on one attack roll, ability check, or saving throw. Once you do so, you must finish a long rest before you can use this feature again. Any time before you regain the use of this feature, the DM can have you roll on the Wild Magic Surge table immediately after you cast a sorcerer spell of 1st level or higher. You then regain the use of this feature.'
            }
        ],
        6: [
            {
                'name': 'Bend Luck',
                'description': 'You have the ability to twist fate using your wild magic. When another creature you can see makes an attack roll, an ability check, or a saving throw, you can use your reaction and spend 2 sorcery points to roll 1d4 and apply the number rolled as a bonus or penalty (your choice) to the creature\'s roll. You can do so after the creature rolls but before any effects of the roll occur.'
            }
        ],
        14: [
            {
                'name': 'Controlled Chaos',
                'description': 'You gain a modicum of control over the surges of your wild magic. Whenever you roll on the Wild Magic Surge table, you can roll twice and use either number.'
            }
        ],
        18: [
            {
                'name': 'Spell Bombardment',
                'description': 'The harmful energy of your spells intensifies. When you roll damage for a spell and roll the highest number possible on any of the dice, choose one of those dice, roll it again and add that roll to the damage. You can use the feature only once per turn.'
            }
        ]
    },
    
    # Warlock Subclasses
    'The Fiend': {
        1: [
            {
                'name': 'Dark One\'s Blessing',
                'description': 'When you reduce a hostile creature to 0 hit points, you gain temporary hit points equal to your Charisma modifier + your warlock level (minimum of 1).'
            }
        ],
        6: [
            {
                'name': 'Dark One\'s Own Luck',
                'description': 'You can call on your patron to alter fate in your favor. When you make an ability check or a saving throw, you can use this feature to add a d10 to your roll. You can do so after seeing the initial roll but before any of the roll\'s effects occur. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            }
        ],
        10: [
            {
                'name': 'Fiendish Resilience',
                'description': 'You can choose one damage type when you finish a short or long rest. You gain resistance to that damage type until you choose a different one with this feature. Damage from magical weapons or silver weapons ignores this resistance.'
            }
        ],
        14: [
            {
                'name': 'Hurl Through Hell',
                'description': 'When you hit a creature with an attack, you can use this feature to instantly transport the target through the lower planes. The creature disappears and hurtles through a nightmare landscape. At the end of your next turn, the target returns to the space it previously occupied, or the nearest unoccupied space. If the target is not a fiend, it takes 10d10 psychic damage as it reels from its horrific experience. Once you use this feature, you can\'t use it again until you finish a long rest.'
            }
        ]
    },
    
    'The Archfey': {
        1: [
            {
                'name': 'Fey Presence',
                'description': 'Your patron bestows upon you the ability to project the beguiling and fearsome presence of the fey. As an action, you can cause each creature in a 10-foot cube originating from you to make a Wisdom saving throw against your warlock spell save DC. The creatures that fail their saving throws are all charmed or frightened by you (your choice) until the end of your next turn. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            }
        ],
        6: [
            {
                'name': 'Misty Escape',
                'description': 'You can vanish in a puff of mist in response to harm. When you take damage, you can use your reaction to turn invisible and teleport up to 60 feet to an unoccupied space you can see. You remain invisible until the start of your next turn or until you attack or cast a spell. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            }
        ],
        10: [
            {
                'name': 'Beguiling Defenses',
                'description': 'Your patron teaches you how to turn the mind-affecting magic of your enemies against them. You are immune to being charmed, and when another creature attempts to charm you, you can use your reaction to attempt to turn the charm back on that creature. The creature must succeed on a Wisdom saving throw against your warlock spell save DC or be charmed by you for 1 minute or until the creature takes any damage.'
            }
        ],
        14: [
            {
                'name': 'Dark Delirium',
                'description': 'You can plunge a creature into an illusory realm. As an action, choose a creature that you can see within 60 feet of you. It must make a Wisdom saving throw against your warlock spell save DC. On a failed save, it is charmed or frightened by you (your choice) for 1 minute or until your concentration is broken. This effect ends early if the creature takes any damage. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            }
        ]
    }

    'Ancient Dragons': {
        1: [
            {
                'name': 'Dragon Tongue',
                'description': 'Starting at 1st level, you can speak, read, and write Draconic.'
            },

    'Animal Lords': {
        1: [
            {
                'name': 'Natural Blessing',
                'description': 'Starting at 1st level, you learn the *druidcraft* cantrip, and you gain proficiency in the Animal Handling skill.'
            },

    'Arcane Warrior': {
        3: [
            {
                'name': 'Spellcasting',
                'description': 'Beginning at 3rd level, you can cast spells from the wizard spell list.  **_Cantrips._** Choose two cantrips from the wizard spell list to learn. At 10th level, you learn one additional cantrip from the same list.  **_Spell Slots._** You use spell slots to cast 1st level and higher spells, expending a spell slot equal to or higher than the level of the spell you wish to cast. When you complete a long rest, you regain any spell slots you have used. The number of spell slots of different levels av...'
            },

    'Beast Trainer': {
        3: [
            {
                'name': 'Beast Whisperer',
                'description': 'Starting at 3rd level, you gain proficiency in Animal Handling. If you already have proficiency in this skill, your proficiency bonus is doubled for any ability check you make with it.'
            },

    'Blood Domain': {
        1: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'At 1st Level, you gain proficiency with martial weapons.'
            },

    'Cantrip Adept': {
        2: [
            {
                'name': 'Cantrip Polymath',
                'description': 'At 2nd level, you gain two cantrips of your choice from any spell list. For you, these cantrips count as wizard cantrips and don\'t count against the number of cantrips you know. In addition, any cantrip you learn or can cast from any other source, such as from a racial trait or feat, counts as a wizard cantrip for you.'
            },

    'Cat Burglar': {
        3: [
            {
                'name': 'Up, Over, and In',
                'description': 'Beginning when you choose this archetype at 3rd level, you have a climbing speed equal to your walking speed. If you already have a climbing speed equal to or greater than your walking speed, it increases by 5 feet. In addition, when you are falling, you can use your reaction to soften the fall. You reduce the falling damage you take by an amount equal to your proficiency bonus + your rogue level. You don\'t land prone, unless the damage you take from the fall would reduce you to less than half y...'
            },

    'Chaplain': {
        3: [
            {
                'name': 'Student of Faith',
                'description': 'When you choose this archetype at 3rd level, you gain proficiency in the Insight, Medicine, or Religion skill (your choice).'
            },

    'Circle of Ash': {
        2: [
            {
                'name': 'Ash Cloud',
                'description': 'At 2nd level, you can expend one use of your Wild Shape and, rather than assuming a beast form, create a small, brief volcanic eruption beneath the ground, causing it to spew out an ash cloud. As an action, choose a point within 30 feet of you that you can see. Each creature within 5 feet of that point must make a Dexterity saving throw against your spell save DC, taking 2d8 bludgeoning damage on a failed save, or half as much damage on a successful one.   This eruption creates a 20-foot-radius ...'
            },

    'Circle of Bees': {
        2: [
            {
                'name': 'Circle Spells',
                'description': 'Your bond with bees and other stinging beasts grants you knowledge of certain spells. At 2nd level, you learn the true strike cantrip. At 3rd, 5th, 7th, and 9th levels, you gain access to the spells listed for those levels in the Circle of Bees Spells table.   Once you gain access to a circle spell, you always have it prepared, and it doesn\'t count against the number of spells you can prepare each day. If you gain access to a spell that doesn\'t appear on the druid spell list, the spell is noneth...'
            },

    'Circle of Crystals': {
        2: [
            {
                'name': 'Resonant Crystal',
                'description': 'When you choose this circle at 2nd level, you learn to create a special crystal that can take on different harmonic frequencies and properties. It is a Tiny object and can serve as a spellcasting focus for your druid spells. As a bonus action, you can cause the crystal to shed bright light in a 10-foot radius and dim light for an additional 10 feet. You can end the light as a bonus action.   Whenever you finish a long rest, you can attune your crystal to one of the following harmonic frequencies...'
            },

    'Circle of Sand': {
        2: [
            {
                'name': 'Sand Form',
                'description': 'When you join this circle at 2nd level, you learn to adopt a sandy form. You can use a bonus action to expend one use of your Wild Shape feature and transform yourself into a form made of animated sand rather than transforming into a beast form. While in your sand form, you retain your game statistics. Because your body is mostly sand, you can move through a space as narrow as 1 inch wide without squeezing, and you have advantage on ability checks and saving throws to escape a grapple or the res...'
            },

    'Circle of Wind': {
        2: [
            {
                'name': 'Bonus Cantrip',
                'description': 'At 2nd level when you choose this circle, you learn the *message* cantrip.'
            },

    'Circle of the Green': {
        2: [
            {
                'name': 'Circle Spells',
                'description': 'When you join this circle at 2nd level, you form a bond with a plant spirit, a creature of the Green. Your link with this spirit grants you access to some spells when you reach certain levels in this class, as shown on the Circle of the Green Spells table.   Once you gain access to one of these spells, you always have it prepared, and it doesn\'t count against the number of spells you can prepare each day. If you gain access to a spell that doesn\'t appear on the druid spell list, the spell is non...'
            },

    'Circle of the Many': {
        2: [
            {
                'name': 'Resilient Transformation',
                'description': 'When you choose this circle at 2nd level, you gain more control over your Wild Shape ability and can use it more effectively in combat. On your turn, you can use the Wild Shape ability as a bonus action instead of as an action. While you are in beast form, you can also expend a spell slot as a bonus action in order to heal the beast shape’s hit points. You can heal 1d8 hit points for each level of the spell slot that you expended in this way.'
            },

    'Circle of the Shapeless': {
        2: [
            {
                'name': 'Circle Spells',
                'description': 'When you join this circle at 2nd level, your connection with oozes grants you access to certain spells. At 2nd level, you learn the *acid splash* cantrip. At 3rd, 5th, 7th, and 9th level you gain access to the spells listed for that level in the Circle of the Shapeless Spells table. Once you gain access to one of these spells, you always have it prepared, and it doesn\'t count against the number of spells you can prepare each day. If you gain access to a spell that doesn\'t appear on the druid spe...'
            },

    'Cold-Blooded': {
        1: [
            {
                'name': 'Ophidian Metabolism',
                'description': 'At 1st level, your affinity with serpents grants you a measure of their hardiness. You can go without food for a number of days equal to 3 + your Constitution modifier (minimum 1) + your proficiency bonus before you suffer the effects of starvation. You also have advantage on saving throws against poison and disease.'
            },

    'College of Echoes': {
        3: [
            {
                'name': 'Echolocation',
                'description': 'When you join the College of Echoes at 3rd level, you learn how to see with your ears as well as your eyes. As long as you can hear, you have blindsight out to a range of 10 feet, and you have disadvantage on saving throws against effects that would deafen you. At 14th level, your blindsight is now out to a range of 15 feet, and you no longer have disadvantage on saving throws against effects that would deafen you.'
            },

    'College of Investigation': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you join the College of Investigation at 3rd level, you gain proficiency in the Insight skill and in two of the following skills of your choice: Acrobatics, Deception, Investigation, Performance, Sleight of Hand, or Stealth.'
            },

    'College of Shadows': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you join the College of Shadows at 3rd level, you gain proficiency in Stealth and in two other skills of your choice.'
            },

    'College of Sincerity': {
        3: [
            {
                'name': 'Entourage',
                'description': 'When you join the College of Sincerity at 3rd level, you gain the service of two commoners. Your entourage is considered charmed by you and travels with you to see to your mundane needs, such as making your meals and doing your laundry. If you are in an urban area, they act as your messengers and gofers. When you put on a performance, they speak your praises and rouse the crowd to applause. In exchange for their service, you must provide your entourage a place to live and pay the costs for them ...'
            },

    'College of Skalds': {
        3: [
            {
                'name': 'Combat Aptitude',
                'description': 'When you choose the College of Skalds at 3rd level, you become proficient in all martial weapons, as well as in the use of medium armor and shields.'
            },

    'College of Tactics': {
        3: [
            {
                'name': 'Combat Tactician',
                'description': 'When you join the College of Tactics at 3rd level, you gain proficiency with medium armor, shields, and one martial weapon of your choice. In addition, you can use Bardic Inspiration a number of times equal to your Charisma modifier (a minimum of 1) + your proficiency bonus. You regain expended uses when you finish a long rest (or short rest if you have the Font of Inspiration feature), as normal.'
            },

    'College of the Cat': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you join the College of the Cat at 3rd level, you gain proficiency with the Acrobatics and Stealth skills and with thieves\' tools if you don\'t already have them. In addition, if you\'re proficient with a simple or martial melee weapon, you can use it as a spellcasting focus for your bard spells.'
            },

    'Courser Mage': {
        2: [
            {
                'name': 'Stalking Savant',
                'description': 'At 2nd level, you gain proficiency with longbows and shortbows, and you gain proficiency in the Stealth skill. In addition, you can still perform the somatic components of wizard spells even when you have a longbow or shortbow in one or both hands.'
            },

    'Dawn Blade': {
        3: [
            {
                'name': 'Eyes of the Dawn',
                'description': 'At 3rd level, you gain darkvision out to a range of 60 feet. If you already have darkvision, the range increases by 30 feet.'
            },

    'Demise Domain': {
        1: [
            {
                'name': 'Bonus Proficiency',
                'description': 'When you choose this domain at 1st level, you gain the martial weapon proficiency.'
            },

    'Eldritch Trickster': {
        3: [
            {
                'name': 'Spellcasting',
                'description': 'Beginning at 3rd level, you can cast spells from the wizard spell list.  **_Cantrips._** You learn the cantrip _mage hand_ and two additional cantrips of your choice, picking from the wizard spell list. At 10th level, you learn one additional cantrip from the same list.  **_Spell Slots._** You use spell slots to cast 1st level and higher spells, expending a spell slot equal to or higher than the level of the spell you wish to cast. When you complete a long rest, you regain any spell slots you ha...'
            },

    'Familiar Master': {
        2: [
            {
                'name': 'Familiar Savant',
                'description': 'Beginning when you select this arcane tradition at 2nd level, you learn the *find familiar* spell if you don\'t know it already. You innately know this spell and don\'t need to have it scribed in your spellbook or prepared in order to cast it. When you cast *find familiar*, the casting time is 1 action, and it requires no material components.   You can cast *find familiar* without expending a spell slot. You can do so a number of times equal to your proficiency bonus. You regain all expended uses ...'
            },

    'Gravebinding': {
        2: [
            {
                'name': 'Gravebinder Lore',
                'description': 'At 2nd level, you can use an action to inscribe a small rune on a corpse. While this rune remains, the corpse can\'t become undead. You can use this feature a number of times equal to your Intelligence modifier (a minimum of once). You regain all expended uses when you finish a long rest.   In addition, you have proficiency in the Religion skill if you don\'t already have it, and you have advantage on Intelligence (Religion) checks made to recall lore about deities of death, burial practices, and ...'
            },

    'Grove Warden': {
        3: [
            {
                'name': 'Grove Warden Magic',
                'description': 'Starting at 3rd level, you learn an additional spell when you reach certain levels in this class, as shown in the Grove Warden Spells table. The spell counts as a ranger spell for you, but it doesn\'t count against the number of ranger spells you know.  **Grove Warden Spells** | Ranger Level  | Spells                  |  |---------------|-------------------------|  | 3rd           | *entangle*              |  | 5th           | *branding smite*        |  | 9th           | *speak with plants*     |...'
            },

    'Haunted Warden': {
        3: [
            {
                'name': 'Beyond the Pale',
                'description': 'Starting when you choose this archetype at 3rd level, you can use a bonus action to see into the Ethereal Plane for 1 minute. Ethereal creatures and objects appear ghostly and translucent.   You can use this feature a number of times equal to your proficiency bonus. You regain all expended uses when you finish a long rest.'
            },

    'Hungering': {
        1: [
            {
                'name': 'Hungry Eyes',
                'description': 'At 1st level, you can sense when a creature is nearing death. You know if a creature you can see that isn\'t undead or a construct within 30 feet of you is below half its hit point maximum. Your spell attacks ignore half cover and three-quarters cover when targeting creatures you sense with this feature.'
            },

    'Hunt Domain': {
        1: [
            {
                'name': 'Blessing of the Hunter',
                'description': 'At 1st level, you gain proficiency in Survival. You can use your action to touch a willing creature other than yourself to give it advantage on Wisdom (Survival) checks. This blessing lasts for 1 hour or until you use this feature again.'
            },

    'Hunter in Darkness': {
        1: [
            {
                'name': 'Savage Hunter',
                'description': 'Starting at 1st level, when you reduce a hostile creature to 0 hp, its nearest ally within 30 feet of you must succeed on a Wisdom saving throw against your warlock spell save DC or be frightened of you until the end of its next turn.'
            },

    'Legionary': {
        3: [
            {
                'name': 'Coordinated Fighting',
                'description': 'Starting at 3rd level, you learn techniques and strategies for close-quarter combat. On your first attack each round, you gain a +1 bonus to the attack and damage rolls if at least one friendly creature is within 5 feet of you.'
            },

    'Mercy Domain': {
        1: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you choose this domain at 1st level, you take your place on the line between the two aspects of mercy: healing and killing. You gain proficiency in the Medicine skill and with the poisoner\'s kit. In addition, you gain proficiency with heavy armor and martial weapons.'
            },

    'Mischief Domain': {
        1: [
            {
                'name': 'Spreader of Mischief',
                'description': 'At 1st level, when you choose this domain, you can endow others with the power to make mischief. As an action, you may touch a willing creature, and that creature gains advantage when making Dexterity (Stealth) checks for the next hour. The effect ends early if you use the feature on a different creature. You may not use this feature on yourself.'
            },

    'Oath of Justice': {
        3: [
            {
                'name': 'Tenets of Justice',
                'description': 'All paladins of justice uphold the law in some capacity, but their oath differs depending on their station. A paladin who serves a queen upholds slightly different tenets than one who serves a small town.  ***Uphold the Law.*** The law represents the triumph of civilization over the untamed wilds. It must be preserved at all costs.  ***Punishment Fits the Crime.*** The severity of justice acts in equal measure to the severity of a wrongdoer\'s transgressions. Oath Spells You gain oath spells at t...'
            },

    'Oath of Safeguarding': {
        3: [
            {
                'name': 'Tenets of Safeguarding',
                'description': 'Paladins undertaking the Oath of Safeguarding take their responsibilities seriously and are most likely to seek atonement should they fail in their duties. However, they have no qualms about terminating their protection when their charges prove nefarious. In these cases, they won\'t leave people stranded in a hostile environment or situation, but they also focus their efforts on their allies over unworthy, former charges. Even when these paladins serve no charge, they seek opportunities to shield...'
            },

    'Oath of the Elements': {
        3: [
            {
                'name': 'Tenets of the Elements',
                'description': 'Though exact interpretations and words of the Oath of the Elements vary between those who serve the subtle, elemental spirits of the world and those who serve elemental deities or genies, paladins of this oath share these tenets.  ***Defend the Natural World.*** Every mountaintop, valley, cave, stream, and spring is sacred. You would fight to your last breath to protect natural places from harm.  ***Lead the Line.*** You stand at the forefront of every battle as a beacon of hope to lead your all...'
            },

    'Oath of the Guardian': {
        3: [
            {
                'name': 'Tenets of the Guardian',
                'description': 'When you take this oath, you always do so with a particular group, town, region, or government in mind, pledging to protect them.  ***Encourage Prosperity.*** You must work hard to bring joy and prosperity to all around you.  ***Preserve Order.*** Order must be protected and preserved for all to enjoy. You must work to keep treasured people, objects, and communities safe.  ***Decisive Action.*** Threats to peaceful life are often nefarious and subtle. The actions you take to combat such threats ...'
            },

    'Oath of the Hearth': {
        3: [
            {
                'name': 'Tenets of the Hearth',
                'description': 'Paladins who take the Oath of the Hearth accommodate all creatures and attempt to find diplomatic solutions to conflicts. Once engaged in battle, though, these paladins fight until they defeat their enemies, or their enemies surrender. They rarely extend this peaceful stance to creatures who attack with cold or desire to spread cold conditions beyond natural confines.  ***Bastion of Peace.*** Reach out the hand of friendship when encountering strangers, and advocate for peace at the outset of an...'
            },

    'Oath of the Plaguetouched': {
        3: [
            {
                'name': 'Restriction: Non-Darakhul',
                'description': 'You can choose this paladin sacred oath only if you are not a darakhul.'
            },

    'Oathless Betrayer': {
        3: [
            {
                'name': 'Tenets of the Betrayer',
                'description': 'By their very nature, Oathless Betrayers do not share any common ideals, but may hold to one of the following tenets.  **_Twisted Honor._** You still cling to your former oath, but distorted to serve your new purpose. For instance, you may still demand a fair fight against a worthy adversary, but show only contempt to those you deem weak.  **_Utter Depravity._** You follow some part of your former oath to the opposite extreme. If you were once honest to a fault, you might now tell lies for the s...'
            },

    'Old Wood': {
        1: [
            {
                'name': 'Sap Magic',
                'description': 'At 1st level, your patron bestows upon you the ability to absorb magic from nearby spellcasting. When a creature casts a spell of a level you can cast or lower within 30 feet of you, you can use your reaction to synthesize the magic. The spell resolves as normal, but you have a 25% chance of regaining hit points equal to your warlock level + your Charisma modifier (minimum of 1 hit point).'
            },

    'Path of Booming Magnificence': {
        3: [
            {
                'name': 'Roar of Defiance',
                'description': 'Beginning at 3rd level, you can announce your presence by unleashing a thunderous roar as part of the bonus action you take to enter your rage. Until the beginning of your next turn, each creature of your choice within 30 feet of you that can hear you has disadvantage on any attack roll that doesn\'t target you.   Until the rage ends, if a creature within 5 feet of you that heard your Roar of Defiance deals damage to you, you can use your reaction to bellow at them. Your attacker must succeed on ...'
            },

    'Path of Mistwood': {
        3: [
            {
                'name': 'Bonus Proficiency',
                'description': 'At 3rd level, you gain proficiency in the Stealth skill. If you are already proficient in Stealth, you gain proficiency in another barbarian class skill of your choice.'
            },

    'Path of Thorns': {
        3: [
            {
                'name': 'Blossoming Thorns',
                'description': 'Beginning at 3rd level, when you enter your rage, hard, sharp thorns emerge over your whole body, turning your unarmed strikes into dangerous weapons. When you hit with an unarmed strike while raging, your unarmed strike deals piercing damage equal to 1d4 + your Strength modifier, instead of the bludgeoning damage normal for an unarmed strike. In addition, while raging, when you use the Attack action with an unarmed strike on your turn, you can make one unarmed strike as a bonus action.   The un...'
            },

    'Path of the Dragon': {
        3: [
            {
                'name': 'Totem Dragon',
                'description': 'Starting when you choose this path at 3rd level, you choose which type of dragon you seek to emulate. You can speak and read Draconic, and you are resistant to the damage type of your chosen dragon.  | Dragon | Damage Type |  |---------------------|-------------|  | Black or Copper | Acid |  | Blue or Bronze | Lightning |  | Brass, Gold, or Red | Fire |  | Green | Poison |  | Silver or White | Cold |'
            },

    'Path of the Herald': {
        3: [
            {
                'name': 'Oral Tradition',
                'description': 'When you adopt this path at 3rd level, you gain proficiency in History and Performance. If you already have proficiency in one of these skills, your proficiency bonus is doubled for ability checks you make using that skill.'
            },

    'Path of the Inner Eye': {
        3: [
            {
                'name': 'Anticipatory Stance',
                'description': 'When you choose this path at 3rd level, you can\'t be surprised unless you are incapacitated, and attacks against you before your first turn have disadvantage. If you take damage before your first turn, you can enter a rage as a reaction, gaining resistance to bludgeoning, piercing, and slashing damage from the triggering attack.   When you reach 8th level in this class, you get 1 extra reaction on each of your turns. This extra reaction can be used only for features granted by the Path of the In...'
            },

    'Path of the Juggernaut': {
        3: [
            {
                'name': 'Thunderous Blows',
                'description': 'Starting when you choose this path at 3rd level, your rage instills you with the strength to batter around your foes, making any battlefield your domain. Once per turn while raging, when you damage a creature with a melee attack, you can force the target to make a Strength saving throw (DC 8 + your proficiency bonus + your Strength modifier). On a failure, you push the target 5 feet away from you, and you can choose to immediately move 5 feet into the target’s previous position.'
            },

    'Portal Domain': {
        1: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you choose this domain at 1st level, you gain proficiency with heavy armor and either cartographer\'s tools or navigator\'s tools (your choice). In addition, you gain proficiency in the Arcana skill.'
            },

    'Primordial': {
        1: [
            {
                'name': 'Convulsion of the Worldbuilder',
                'description': 'At 1st level, you can use an action to call upon the bond between your primordial patron and the world it created to ripple shockwaves through the ground. Choose a point you can see within 60 feet of you, then choose if the ripples happen in a 30-foot cone, a 30-foot line that is 5 feet wide, or a 20-foot-radius burst. The ripples originate from or are centered on the point you chose, depending on the form the ripples take. Each creature in the cone, line, or burst must succeed on a Dexterity sa...'
            },

    'Pugilist': {
        3: [
            {
                'name': 'Unarmed Warrior',
                'description': 'When you choose this archetype at 3rd level, you learn to use your fists, knees, elbows, head, and feet to attack your opponents. You gain the following benefits while you are not wearing heavy armor and while you are not wielding weapons or a shield:  * Your unarmed strikes deal bludgeoning damage equal to 1d6 + your Strength modifier on a hit. Your unarmed strike damage increases as you reach higher levels. The d6 becomes a d8 at 10th level and a d10 at 18th level.  * When you use the Attack a...'
            },

    'Radiant Pikeman': {
        3: [
            {
                'name': 'Harassing Strike',
                'description': 'Beginning when you choose this archetype at 3rd level, when a creature you can see enters your reach, you can use your reaction to Shove the creature. To use this feature, you must be wielding a glaive, halberd, lance, pike, or spear.'
            },

    'Resonant Body': {
        1: [
            {
                'name': 'Reverberating Quintessence',
                'description': 'At 1st level, you harbor sonic vibrations within you. You are immune to the deafened condition, and you have tremorsense out to a range of 10 feet. In addition, you have advantage on saving throws against effects that deal thunder damage.   When you reach 3rd level in this class, you have resistance to thunder damage, and at 6th level, your tremorsense extends to 20 feet.'
            },

    'Rifthopper': {
        1: [
            {
                'name': 'Teleport Object',
                'description': 'Starting at 1st level, you can use an action to teleport a small object that isn\'t being worn or carried and that you can see within 30 feet of you into your hand. Alternatively, you can teleport an object from your hand to a space you can see within 30 feet of you. The object can weigh no more than 5 pounds and must be able to fit into a 1-foot cube.   The weight of the object you can teleport increases when you reach certain levels in this class: at 6th (10 pounds), 14th level (15 pounds), and...'
            },

    'Runechild': {
        1: [
            {
                'name': 'Essence Runes',
                'description': 'At 1st level, your body has begun to express your innate magical energies as natural runes that hide beneath your skin. You begin with 1 Essence Rune, and gain an addi- tional rune whenever you gain a level in this class. Runes can manifest anywhere on your body, though the first usually manifests on the forehead. They remain invisible when inert. At the end of a turn where you spent any number of sorcery points for any of your class features, an equal number of essence runes glow with stored en...'
            },

    'Sapper': {
        3: [
            {
                'name': 'Combat Engineer',
                'description': 'When you select this archetype at 3rd level, you gain proficiency in alchemist\'s supplies, carpenter\'s tools, mason\'s tools, and tinker\'s tools. Using these tools, you can do or create the following.  ***Alchemical Bomb.*** As an action, you can mix together volatile chemicals into an explosive compound and throw it at a point you can see within 30 feet of you. Each creature within 10 feet of that point must make a Dexterity saving throw (DC equals 8 + your proficiency bonus + your Intelligence ...'
            },

    'School of Divining and Soothsaying': {
        2: [
            {
                'name': 'Expert Diviner',
                'description': 'Starting at 2nd level when you choose this school, you only need to spend half as much time and gold as normal in order to copy a spell into your spellbook if the spell is from the divination school.'
            },

    'School of Illusions and Phantasms': {
        2: [
            {
                'name': 'Expert Illusionist',
                'description': 'Starting at 2nd level when you choose this school, you only need to spend half as much time and gold as normal in order to copy a spell into your spellbook if the spell is from the illusion school.'
            },

    'School of Liminality': {
        2: [
            {
                'name': 'Liminal Savant',
                'description': 'Beginning when you select this school at 2nd level, the gold and time you must spend to copy a liminal spell (see the Magic and Spells chapter) into your spellbook is halved.'
            },

    'School of Necrotic Arts': {
        2: [
            {
                'name': 'Expert Necromancer',
                'description': 'Starting at 2nd level when you choose this school, you only need to spend half as much time and gold as normal in order to copy a spell into your spellbook if the spell is from the necromancy school.'
            },

    'Serpent Domain': {
        1: [
            {
                'name': 'Envenomed',
                'description': 'When you choose this domain at 1st level, you learn the *poison spray* cantrip. In addition, you gain proficiency in the Deception skill, with a poisoner\'s kit, and with martial weapons that have the Finesse property. You can apply poison to a melee weapon or three pieces of ammunition as a bonus action.'
            },

    'Shadow Domain': {
        1: [
            {
                'name': 'Cover of Night',
                'description': 'When you choose this domain at 1st level, you gain proficiency in the Stealth skill and darkvision out to a range of 60 feet. If you already have darkvision, its range increases by 30 feet. In addition, when you are in dim light or darkness, you can use a bonus action to Hide.'
            },

    'Smuggler': {
        3: [
            {
                'name': 'Dab-handed Dealer',
                'description': 'When you choose this archetype at 3rd level, you gain proficiency with vehicles (land and water) and with your choice of either the disguise kit or navigator-s tools. Moreover, when determining your carrying capacity, you are considered one size category larger than your actual size.   Starting at this level, you also have advantage on Dexterity (Sleight of Hand) checks to hide objects on vehicles, and you can use the bonus action granted by your Cunning Action to make a check to control a vehic...'
            },

    'Snake Speaker': {
        3: [
            {
                'name': 'Snake Speaker Magic',
                'description': 'Starting at 3rd level, you learn an additional spell when you reach certain levels in this class, as shown in the Snake Speaker Spells table. The spell counts as a ranger spell for you, but it doesn\'t count against the number of ranger spells you know.  **Snake Speaker Spells** | Ranger Level  | Spells            |  |---------------|-------------------|  | 3rd           | *charm person*    |  | 5th           | *suggestion*      |  | 9th           | *tongues*         |  | 13th          | *confusi...'
            },

    'Soulspy': {
        1: [
            {
                'name': 'Spells Known of 1st-Level and Higher',
                'description': 'You know three 1st-level cleric spells of your choice, two of which you must choose from the abjuration and necromancy spells on the cleric spell list. The Spells Known column of the Soulspy Spellcasting table shows when you learn more cleric spells of 1st level or higher. Each of these spells must be an abjuration or necromancy spell and must be of a level for which you have spell slots. The spells you learn at 8th, 14th, and 20th level can be from any school of magic.   When you gain a level i...'
            },

    'Spear of the Weald': {
        3: [
            {
                'name': 'Restriction: Alseid',
                'description': 'You can choose this archetype only if you are an alseid.'
            },

    'Spellsmith': {
        2: [
            {
                'name': 'Arcane Emendation',
                'description': 'Beginning when you choose this tradition at 2nd level, you can manipulate the magical energy in scrolls to change the spells written on them. While holding a scroll, you can spend 1 hour for each level of the spell focusing on the magic within the scroll to change the spell on the scroll to another spell. The new spell must be of the same school, must be on the wizard spell list, and must be of the same or lower level than the original spell. If the new spell has any material components with a c...'
            },

    'Spore Sorcery': {
        1: [
            {
                'name': 'Spore Transmission',
                'description': 'At 1st level, your spores allow you to communicate with creatures telepathically. You can use a bonus action to create a telepathic link with one creature you can see within 30 feet of you. Until the link ends, you can telepathically speak to the target, and, if it understands at least one language, it can speak telepathically to you. The link lasts for 10 minutes or until you use another bonus action to break the link or to establish this link with a different creature.   If the target is unwil...'
            },

    'Storm Domain': {
        1: [
            {
                'name': 'Bonus Proficiency',
                'description': 'When you choose this domain at 1st level, you gain proficiency with heavy armor as well as with martial weapons.'
            },

    'The Ancient Fey Court': {
        1: [
            {
                'name': 'Courtier’s Aspect',
                'description': 'Beginning at 1st level, you are able to take on a fey aspect that can both enchant and terrify. You may use an action to force all creatures within a 10-foot cube that originates from you to make a Wisdom saving throw using your warlock spell save DC. Until the end of your next turn, you can choose for all the creatures that fail their saving throw to become either charmed by you or frightened of you.  After using this feature, you cannot use it again until after finishing a short or long rest.'
            },

    'The Great Elder Thing': {
        1: [
            {
                'name': 'Outward Cerebration',
                'description': 'Beginning at 1st level, you can push your thoughts into other minds, speaking telepathically to a creature within 30 feet as long as you can see that creature. The creature must know some language to hear your projections, but it does not need to speak the same language as you.'
            },

    'Timeblade': {
        3: [
            {
                'name': 'Temporal Strike',
                'description': 'Starting at 3rd level, when you hit a creature with a weapon attack, you can use a bonus action to trigger one of the following effects:  * **Dislocative Step.** You step outside of time and move to an unoccupied space you can see within 15 feet of you. This movement doesn\'t provoke opportunity attacks. At 10th level, you can move up to 30 feet.  * **Dislocative Shove.** You push the target of your attack to an unoccupied space you can see within 15 feet of you. You can move the target only hori...'
            },

    'Tunnel Watcher': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'At 3rd level, you gain proficiency with thieves\' tools and mason\'s tools.'
            },

    'Underfoot': {
        1: [
            {
                'name': 'Spells Known of 1st-Level and Higher',
                'description': 'You know three 1st-level druid spells of your choice, two of which you must choose from the divination and transmutation spells on the druid spell list. The Spells Known column of the Underfoot Spellcasting table shows when you learn more druid spells of 1st level or higher. Each of these spells must be a divination or transmutation spell of your choice and must be of a level for which you have spell slots. The spells you learn at 8th, 14th, and 20th level can be from any school of magic.   When...'
            },

    'Vermin Domain': {
        1: [
            {
                'name': 'The Unseen',
                'description': 'When you choose this domain at 1st level, you gain proficiency with shortswords and hand crossbows. You also gain proficiency in Stealth and Survival. You can communicate simple ideas telepathically with vermin, such as mice, spiders, and ants, within 100 feet of you. A vermin\'s responses, if any, are limited by its intelligence and typically convey the creature\'s current or most recent state, such as “hungry” or “in danger.”'
            },

    'Wasteland Strider': {
        3: [
            {
                'name': 'Chaotic Strikes',
                'description': 'When you choose this archetype at 3rd level, you\'ve learned to channel the unpredictable energies of magical wastelands into your weapon attacks. You can use a bonus action to imbue your weapon with chaotic energy for 1 minute. Roll a d8 and consult the Chaotic Strikes table to determine which type of energy is imbued in your weapon. While your weapon is imbued with chaotic energy, it deals an extra 1d4 damage of the imbued type to any target you hit with it. If you are no longer holding or carr...'
            },

    'Wastelander': {
        1: [
            {
                'name': 'Alien Alteration',
                'description': 'At 1st level, the influence of raw magical energy in your bloodline remodeled your form. You choose one of the following features as the alteration from your ancestry.  ***Binary Mind.*** Your cranium is larger than most creatures of your type and houses your enlarged brain, which is partitioned in a manner that allows you to work on simultaneous tasks. You can use the Search action or make an Intelligence or Wisdom check as a bonus action on your turn.  ***Digitigrade Legs.*** Your legs are sim...'
            },

    'Way of Concordant Motion': {
        3: [
            {
                'name': 'Cooperative Ki',
                'description': 'Starting when you choose this tradition at 3rd level, when you spend ki on certain features, you can share some of the effects with your allies.  ***Flurry of Blows.*** When you spend ki to use Flurry of Blows, you can use a bonus action to empower up to two allies you can see within 30 feet of you instead of making two unarmed strikes. The next time an empowered ally hits a creature with an attack before the start of your next turn, the ally\'s attack deals extra damage of the attack\'s type equa...'
            },

    'Way of Shadowdancing': {
        3: [
            {
                'name': 'Magic of Shadow',
                'description': 'At 3rd level, you can channel your ki to cast a selection of spells tied to the plane of shadow. You learn the cantrip *minor illusion*. You can also use an action and 2 ki points to cast any of the following spells without the need for material components: *darkness*, *darkvision*, *silence*, and *pass without trace*.'
            },

    'Way of the Cerulean Spirit': {
        3: [
            {
                'name': 'Mystical Erudition',
                'description': 'Upon choosing this tradition at 3rd level, you’ve undergone extensive training with the Cerulean Spirit, allowing you to mystically recall information on history and lore from the monastery’s collected volumes. Whenever you make an Intelligence (Arcana), Intelligence (History), or Intelligence (Religion) check, you can spend 1 ki point to gain advantage on the roll. In addition, you learn one language of your choice. You gain additional languages at 11th and 17th level.'
            },

    'Way of the Dragon': {
        3: [
            {
                'name': 'Draconic Affiliation',
                'description': 'Starting when you choose this tradition at 3rd level, you feel an affinity for one type of dragon, which you choose from the Draconic Affiliation table. You model your fighting style to match that type of dragon, and some of the features you gain from following this Way depend upon the affiliation you chose.  | Dragon              | Associated Skill  | Damage Type |  |---------------------|-------------------|-------------|  | Black or Copper     | Stealth           | Acid        |  | Blue or Br...'
            },

    'Way of the Humble Elephant': {
        3: [
            {
                'name': 'Slow to Anger',
                'description': 'Starting when you choose this tradition at 3rd level, when you use Patient Defense and an attack hits you, you can use your reaction to halve the damage that you take. When you use Patient Defense and a melee attack made by a creature within your reach misses you, you can use your reaction to force the target to make a Strength saving throw. On a failure, the target is knocked prone.   When you use either of these reactions, you can spend 1 ki point. If you do, your first melee weapon attack tha...'
            },

    'Way of the Still Waters': {
        3: [
            {
                'name': 'Perfect Calm',
                'description': 'Starting when you choose this tradition at 3rd level, when you spend a ki point on Flurry of Blows, Patient Defense, or Step of the Wind, you also have advantage on one saving throw of your choice that you make before the end of your next turn.'
            },

    'Way of the Tipsy Monkey': {
        3: [
            {
                'name': 'Adaptive Fighting',
                'description': 'Monks of the Way of the Tipsy Monkey keep their foes off-balance by using unexpected things as weapons. Starting when you choose this tradition at 3rd level, you are proficient with improvised weapons, and you can treat them as monk weapons. When you use a magic item as an improvised weapon, you gain a bonus to attack and damage rolls with that improvised weapon based on the magic item\'s rarity: +1 for uncommon, +2 for rare, or +3 for very rare. At the GM\'s discretion, some magic items, such as ...'
            },

    'Way of the Unerring Arrow': {
        3: [
            {
                'name': 'Archery Training',
                'description': 'When you choose this tradition at 3rd level, your particular martial arts training guides you to master the use of bows. The shortbow and longbow are monk weapons for you. Being within 5 feet of a hostile creature doesn\'t impose disadvantage on your ranged attack rolls with shortbows or longbows.   When you make an unarmed strike as a bonus action as part of your Martial Arts feature or as part of a Flurry of Blows, you can choose for the unarmed strike to deal piercing damage as you jab the tar...'
            },

    'Way of the Wildcat': {
        3: [
            {
                'name': 'Enhanced Agility',
                'description': 'When you choose this tradition at 3rd level, you gain proficiency in the Acrobatics skill if you don\'t already have it. When you move at least 10 feet on your turn, you have advantage on the next Dexterity (Acrobatics) check you make before the start of your next turn.'
            },
        ],
    },

    'Wind Domain': {
        1: [
            {
                'name': 'Wind\'s Chosen',
                'description': 'When you choose this domain at 1st level, you learn the *mage hand* cantrip and gain proficiency in the Nature skill. When you cast *mage hand*, you can make the hand invisible, and you can control the hand as a bonus action.'
            },
        ],
    },

    'Wyrd Magic': {
        1: [
            {
                'name': 'Flood of Chaos',
                'description': 'Beginning at 1st level when you select this bloodline, you sometimes release a flood of magical energy with your spellcasting. The Game Master can tell you to roll 1d20 at any time right after you cast a sorcerer spell that is not a cantrip. If the result is a 1, you then roll 1d100 on the Flood of Chaos table to determine an additional magical effect at random. A Flood of Chaos can happen at most once per turn.  Sometimes a Flood of Chaos forces you to cast a spell. Unlike normal spells, you ca...'
            },
        ],
    },

    'Wyrdweaver': {
        1: [
            {
                'name': 'Probability Wellspring',
                'description': 'Starting at 1st level, you gain the ability to manipulate probability. You have a pool of d6s that you spend to fuel your patron abilities. The number of probability dice in the pool equals 1 + your warlock level.   You can use these dice to turn the odds in your or your ally\'s favor. When you or a friendly creature you can see within 30 feet of you makes an attack roll, ability check, or saving throw, you can use your reaction to expend probability dice from the pool, rolling the dice and addin...'
            },
        ],
    },
}


def get_subclass_features(subclass_name, level):
    """
    Get subclass features for a specific subclass at a specific level.
    
    Args:
        subclass_name: Name of the subclass (e.g., 'Champion', 'School of Evocation')
        level: Character level (1-20)
    
    Returns:
        List of feature dictionaries with 'name' and 'description' keys
    """
    if subclass_name not in SUBCLASS_FEATURES:
        return []
    
    if level not in SUBCLASS_FEATURES[subclass_name]:
        return []
    
    return SUBCLASS_FEATURES[subclass_name][level]


def get_all_subclass_features_up_to_level(subclass_name, level):
    """
    Get all subclass features from the first subclass level up to the specified level.
    
    Args:
        subclass_name: Name of the subclass
        level: Character level
    
    Returns:
        Dictionary mapping level to list of features
    """
    if subclass_name not in SUBCLASS_FEATURES:
        return {}
    
    features_by_level = {}
    for lvl in range(1, level + 1):
        if lvl in SUBCLASS_FEATURES[subclass_name]:
            features = SUBCLASS_FEATURES[subclass_name][lvl]
            if features:  # Only include levels with features
                features_by_level[lvl] = features
    
    return features_by_level