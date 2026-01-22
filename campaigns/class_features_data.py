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
                'description': 'Your blessed touch can heal wounds. You have a pool of healing power that replenishes when you take a long rest. With that pool, you can restore a total number of hit points equal to your paladin level * 5. As an action, you can touch a creature and draw power from the pool to restore a number of hit points to that creature, up to the maximum amount remaining in your pool. Alternatively, you can expend 5 hit points from your pool of healing to cure the target of one disease or neutralize one poison affecting it.'
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
    },
    'barbarian': {
        1: [
            {
                'name': 'Rage',
                'description': 'In battle, you fight with primal ferocity. On your turn, you can enter a rage as a bonus action. While raging, you gain the following benefits if you aren\'t wearing heavy armor: You have advantage on Strength checks and Strength saving throws. When you make a melee weapon attack using Strength, you gain a bonus to the damage roll. You have resistance to bludgeoning, piercing, and slashing damage. You can\'t cast spells or concentrate on them while raging. Your rage lasts for 1 minute. It ends early if you are knocked unconscious or if your turn ends and you haven\'t attacked a hostile creature since your last turn or taken damage since then. You can also end your rage on your turn as a bonus action. You use this feature twice per long rest at 1st level.'
            },
            {
                'name': 'Unarmored Defense',
                'description': 'While you are not wearing any armor, your Armor Class equals 10 + your Dexterity modifier + your Constitution modifier. You can use a shield and still gain this benefit.'
            }
        ],
        2: [
            {
                'name': 'Reckless Attack',
                'description': 'Starting at 2nd level, you can throw aside all concern for defense to attack with fierce desperation. When you make your first attack on your turn, you can decide to attack recklessly. Doing so gives you advantage on melee weapon attack rolls using Strength during this turn, but attack rolls against you have advantage until your next turn.'
            },
            {
                'name': 'Danger Sense',
                'description': 'At 2nd level, you gain an uncanny sense of when things nearby aren\'t as they should be, giving you an edge when you dodge away from danger. You have advantage on Dexterity saving throws against effects that you can see, such as traps and spells. To gain this benefit, you can\'t be blinded, deafened, or incapacitated.'
            }
        ],
        3: [
            {
                'name': 'Primal Path',
                'description': 'You choose a path that shapes the nature of your rage (Path of the Berserker). Your choice grants you features at 3rd level and again at 6th, 10th, and 14th level.'
            }
        ],
        4: [], # ASI
        5: [
            {
                'name': 'Extra Attack',
                'description': 'Beginning at 5th level, you can attack twice, instead of once, whenever you take the Attack action on your turn.'
            },
            {
                'name': 'Fast Movement',
                'description': 'Starting at 5th level, your speed increases by 10 feet while you aren\'t wearing heavy armor.'
            }
        ],
        6: [], # Primal Path
        7: [
            {
                'name': 'Feral Instinct',
                'description': 'By 7th level, your instincts are so honed that you have advantage on initiative rolls. Additionally, if you are surprised at the beginning of combat and aren\'t incapacitated, you can act normally on your first turn, but only if you enter your rage before doing anything else on that turn.'
            }
        ],
        8: [], # ASI
        9: [
            {
                'name': 'Brutal Critical (1 die)',
                'description': 'Beginning at 9th level, you can roll one additional weapon damage die when determining the extra damage for a critical hit with a melee attack.'
            }
        ],
        10: [], # Primal Path
        11: [
            {
                'name': 'Relentless Rage',
                'description': 'Starting at 11th level, your rage can keep you fighting despite grievous wounds. If you drop to 0 hit points while you\'re raging and don\'t die outright, you can make a DC 10 Constitution saving throw. If you succeed, you drop to 1 hit point instead. Each time you use this feature after the first, the DC increases by 5. When you finish a short or long rest, the DC resets to 10.'
            }
        ],
        12: [], # ASI
        13: [
            {
                'name': 'Brutal Critical (2 dice)',
                'description': 'You can roll two additional weapon damage dice when determining the extra damage for a critical hit with a melee attack.'
            }
        ],
        14: [], # Primal Path
        15: [
            {
                'name': 'Persistent Rage',
                'description': 'Beginning at 15th level, your rage is so fierce that it ends early only if you fall unconscious or if you choose to end it.'
            }
        ],
        16: [], # ASI
        17: [
            {
                'name': 'Brutal Critical (3 dice)',
                'description': 'You can roll three additional weapon damage dice when determining the extra damage for a critical hit with a melee attack.'
            }
        ],
        18: [
            {
                'name': 'Indomitable Might',
                'description': 'Beginning at 18th level, if your total for a Strength check is less than your Strength score, you can use that score in place of the total.'
            }
        ],
        19: [], # ASI
        20: [
            {
                'name': 'Primal Champion',
                'description': 'At 20th level, you embody the power of the wilds. Your Strength and Constitution scores increase by 4. Your maximum for those scores is now 24.'
            }
        ]
    },
    'monk': {
        1: [
            {
                'name': 'Unarmored Defense',
                'description': 'Beginning at 1st level, while you are wearing no armor and not wielding a shield, your AC equals 10 + your Dexterity modifier + your Wisdom modifier.'
            },
            {
                'name': 'Martial Arts',
                'description': 'At 1st level, your practice of martial arts gives you mastery of combat styles that use unarmed strikes and monk weapons. You gain the following benefits while you are unarmed or wielding only monk weapons and you aren\'t wearing armor or wielding a shield: You can use Dexterity instead of Strength for attack and damage rolls. You can roll a d4 in place of the normal damage. When you use the Attack action with an unarmed strike or a monk weapon on your turn, you can make one unarmed strike as a bonus action.'
            }
        ],
        2: [
            {
                'name': 'Ki',
                'description': 'Starting at 2nd level, your training allows you to harness the mystic energy of ki. You have 2 ki points, and you gain more as you reach higher levels. You can spend these points to fuel various ki features. You start with three features: Flurry of Blows, Patient Defense, and Step of the Wind.'
            },
             {
                'name': 'Unarmored Movement',
                'description': 'Starting at 2nd level, your speed increases by 10 feet while you are not wearing armor or wielding a shield. This bonus increases when you reach certain monk levels.'
            }
        ],
        3: [
            {
                'name': 'Monastic Tradition',
                'description': 'You commit yourself to a monastic tradition (Way of the Open Hand). Your tradition grants you features at 3rd level and again at 6th, 11th, and 17th level.'
            },
            {
                'name': 'Deflect Missiles',
                'description': 'Starting at 3rd level, you can use your reaction to deflect or catch the missile when you are hit by a ranged weapon attack. When you do so, the damage you take from the attack is reduced by 1d10 + your Dexterity modifier + your monk level.'
            }
        ],
        4: [
            {
                'name': 'Slow Fall',
                'description': 'Beginning at 4th level, you can use your reaction when you fall to reduce any falling damage you take by an amount equal to five times your monk level.'
            }
        ], 
        5: [
            {
                'name': 'Extra Attack',
                'description': 'Beginning at 5th level, you can attack twice, instead of once, whenever you take the Attack action on your turn.'
            },
            {
                'name': 'Stunning Strike',
                'description': 'Starting at 5th level, you can interfere with the flow of ki in an opponent\'s body. When you hit another creature with a melee weapon attack, you can spend 1 ki point to attempt to stunning strike. The target must succeed on a Constitution saving throw or be stunned until the end of your next turn.'
            }
        ],
        6: [
            {
                'name': 'Ki-Empowered Strikes',
                'description': 'Starting at 6th level, your unarmed strikes count as magical for the purpose of overcoming resistance and immunity to nonmagical attacks and damage.'
            }
        ],
        7: [
            {
                'name': 'Evasion',
                'description': 'At 7th level, your instinctive agility lets you dodge out of the way of certain area effects, such as a blue dragon\'s lightning breath or a fireball spell. When you are subjected to an effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail.'
            },
            {
                'name': 'Stillness of Mind',
                'description': 'Starting at 7th level, you can use your action to end one effect on yourself that is causing you to be charmed or frightened.'
            }
        ],
        8: [], # ASI
        9: [
            {
                'name': 'Unarmored Movement Improvement',
                'description': 'At 9th level, you gain the ability to move along vertical surfaces and across liquids on your turn without falling during the move.'
            }
        ],
        10: [
            {
                'name': 'Purity of Body',
                'description': 'At 10th level, your mastery of the ki flowing through you makes you immune to disease and poison.'
            }
        ],
        11: [], # Tradition
        12: [], # ASI
        13: [
            {
                'name': 'Tongue of the Sun and Moon',
                'description': 'Starting at 13th level, you learn to touch the ki of other minds so that you understand all spoken languages. Moreover, any creature that can understand a language can understand what you say.'
            }
        ],
        14: [
            {
                'name': 'Diamond Soul',
                'description': 'Beginning at 14th level, your mastery of ki grants you proficiency in all saving throws. Additionally, whenever you make a saving throw and fail, you can spend 1 ki point to reroll it and take the second result.'
            }
        ],
        15: [
            {
                'name': 'Timeless Body',
                'description': 'At 15th level, your ki sustains you so that you suffer none of the frailty of old age, and you can\'t be aged magically. You can still die of old age, however. In addition, you no longer need food or water.'
            }
        ],
        16: [], # ASI
        17: [], # Tradition
        18: [
            {
                'name': 'Empty Body',
                'description': 'Beginning at 18th level, you can use your action to spend 4 ki points to become invisible for 1 minute. During that time, you also have resistance to all damage but force damage. Additionally, you can spend 8 ki points to cast the astral projection spell, without needing material components. When you do so, you can\'t take any other creatures with you.'
            }
        ],
        19: [], # ASI
        20: [
            {
                'name': 'Perfect Self',
                'description': 'At 20th level, when you roll for initiative and have no ki points remaining, you regain 4 ki points.'
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
        # Try lowercase as fallback
        if class_name.lower() in CLASS_FEATURES:
            class_name = class_name.lower()
        # Try title case as fallback
        elif class_name.title() in CLASS_FEATURES:
            class_name = class_name.title()
        else:
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


# Available subclasses by class
AVAILABLE_SUBCLASSES = {
    'Fighter': ['Champion', 'Battle Master'],
    'Rogue': ['Thief', 'Assassin'],
    'Wizard': ['School of Evocation'],
    'Cleric': ['Life Domain'],
    'Druid': ['Circle of the Land'],
    'Monk': ['Way of the Open Hand'],
    'Paladin': ['Oath of Devotion'],
    'Ranger': ['Hunter'],
    'Sorcerer': ['Draconic Bloodline'],
    'Warlock': ['The Fiend'],
    'Barbarian': ['Path of the Berserker'],
    'Bard': ['College of Lore'],
}


# Subclass features by subclass name and level
# Only includes official D&D 5e Core Rules subclasses from Open5e
SUBCLASS_FEATURES = {
    'Champion': {
        3: [
            {
                'name': 'Improved Critical',
                'description': 'Beginning when you choose this archetype at 3rd level, your weapon attacks score a critical hit on a roll of 19 or 20.'
            },
        ],
        7: [
            {
                'name': 'Remarkable Athlete',
                'description': 'Starting at 7th level, you can add half your proficiency bonus (round up) to any Strength, Dexterity, or Constitution check you make that doesn\'t already use your proficiency bonus. In addition, when you make a running long jump, the distance you can cover increases by a number of feet equal to your Strength modifier.'
            },
        ],
        10: [
            {
                'name': 'Additional Fighting Style',
                'description': 'At 10th level, you can choose a second option from the Fighting Style class feature.'
            },
        ],
        15: [
            {
                'name': 'Superior Critical',
                'description': 'Starting at 15th level, your weapon attacks score a critical hit on a roll of 18-20.'
            },
        ],
        18: [
            {
                'name': 'Survivor',
                'description': 'At 18th level, you attain the pinnacle of resilience in battle. At the start of each of your turns, you regain hit points equal to 5 + your Constitution modifier if you have no more than half of your hit points left. You don\'t gain this benefit if you have 0 hit points.'
            },
        ],
    },

    'Battle Master': {
        3: [
            {
                'name': 'Combat Superiority',
                'description': 'When you choose this archetype at 3rd level, you learn maneuvers that are fueled by special dice called superiority dice. You learn three maneuvers of your choice. You gain four superiority dice, which are d8s. A superiority die is expended when you use it. You regain all of your expended superiority dice when you finish a short or long rest.'
            },
            {
                'name': 'Student of War',
                'description': 'At 3rd level, you gain proficiency with one type of artisan\'s tools of your choice.'
            },
        ],
        7: [
            {
                'name': 'Know Your Enemy',
                'description': 'Starting at 7th level, if you spend at least 1 minute observing or interacting with another creature outside combat, you can learn certain information about its capabilities compared to your own.'
            },
        ],
        10: [
            {
                'name': 'Improved Combat Superiority (d10)',
                'description': 'At 10th level, your superiority dice turn into d10s.'
            },
        ],
        15: [
            {
                'name': 'Relentless',
                'description': 'Starting at 15th level, when you roll initiative and have no superiority dice remaining, you regain 1 superiority die.'
            },
        ],
        18: [
            {
                'name': 'Improved Combat Superiority (d12)',
                'description': 'At 18th level, your superiority dice turn into d12s.'
            },
        ],
    },

    'College of Lore': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you join the College of Lore at 3rd level, you gain proficiency with three skills of your choice.'
            },
            {
                'name': 'Cutting Words',
                'description': 'Also at 3rd level, you learn how to use your wit to distract, confuse, and otherwise sap the confidence and competence of others. When a creature that you can see within 60 feet of you makes an attack roll, an ability check, or a damage roll, you can use your reaction to expend one of your uses of Bardic Inspiration, rolling a Bardic Inspiration die and subtracting the number rolled from the creature\'s roll. You can choose to use this feature after the creature makes its roll, but before the GM determines whether the attack hits or fails, or the check succeeds or fails.'
            },
        ],
        6: [
            {
                'name': 'Additional Magical Secrets',
                'description': 'At 6th level, you learn two spells of your choice from any class. A spell you choose must be of a level you can cast, as shown on the Bard table, or a cantrip. The chosen spells count as bard spells for you but don\'t count against the number of bard spells you know.'
            },
        ],
        14: [
            {
                'name': 'Peerless Skill',
                'description': 'Starting at 14th level, when you make an ability check, you can expend one use of Bardic Inspiration. Roll a Bardic Inspiration die and add the number rolled to your ability check. You can choose to do so after you roll the die for the ability check, but before the GM tells you whether you succeed or fail.'
            },
        ],
    },

    'Life Domain': {
        1: [
            {
                'name': 'Bonus Proficiency',
                'description': 'When you choose this domain at 1st level, you gain proficiency with heavy armor.'
            },
            {
                'name': 'Disciple of Life',
                'description': 'Also starting at 1st level, your healing spells are more effective. Whenever you use a spell of 1st level or higher to restore hit points to a creature, the creature regains additional hit points equal to 2 + the spell\'s level.'
            },
        ],
        2: [
            {
                'name': 'Channel Divinity: Preserve Life',
                'description': 'Starting at 2nd level, you can use your Channel Divinity to heal the badly injured. As an action, you present your holy symbol and evoke healing energy that can restore a number of hit points equal to five times your cleric level. Choose any creatures within 30 feet of you, and divide those hit points among them. This feature can restore a creature to no more than half of its hit point maximum. You can\'t use this feature on an undead or a construct.'
            },
        ],
        6: [
            {
                'name': 'Blessed Healer',
                'description': 'Beginning at 6th level, the healing spells you cast on others heal you as well. When you cast a spell of 1st level or higher that restores hit points to a creature other than you, you regain hit points equal to 2 + the spell\'s level.'
            },
        ],
        8: [
            {
                'name': 'Divine Strike',
                'description': 'At 8th level, you gain the ability to infuse your weapon strikes with divine energy. Once on each of your turns when you hit a creature with a weapon attack, you can cause the attack to deal an extra 1d8 radiant damage to the target. When you reach 14th level, the extra damage increases to 2d8.'
            },
        ],
        17: [
            {
                'name': 'Supreme Healing',
                'description': 'Starting at 17th level, when you would normally roll one or more dice to restore hit points with a spell, you instead use the highest number possible for each die. For example, instead of restoring 2d6 hit points to a creature, you restore 12.'
            },
        ],
    },

    'Circle of the Land': {
        2: [
            {
                'name': 'Bonus Cantrip',
                'description': 'When you choose this circle at 2nd level, you learn one additional druid cantrip of your choice.'
            },
            {
                'name': 'Natural Recovery',
                'description': 'Starting at 2nd level, you can regain some of your magical energy by sitting in meditation and communing with nature. During a short rest, you choose expended spell slots to recover. The spell slots can have a combined level that is equal to or less than half your druid level (rounded up), and none of the slots can be 6th level or higher. You can\'t use this feature again until you finish a long rest. For example, when you are a 4th-level druid, you can recover up to two levels worth of spell slots. You can recover either a 2nd-level slot or two 1st-level slots.'
            },
        ],
        3: [
            {
                'name': 'Circle Spells',
                'description': 'Your mystical connection to the land infuses you with the ability to cast certain spells. At 3rd, 5th, 7th, and 9th level you gain access to circle spells connected to the land where you became a druid. Choose that land—arctic, coast, desert, forest, grassland, mountain, or swamp—and consult the associated list of spells. Once you gain access to a circle spell, you always have it prepared, and it doesn\'t count against the number of spells you can prepare each day. If you gain access to a spell that doesn\'t appear on the druid spell list, the spell is nonetheless a druid spell for you.'
            },
        ],
        6: [
            {
                'name': 'Land\'s Stride',
                'description': 'Starting at 6th level, moving through nonmagical difficult terrain costs you no extra movement. You can also pass through nonmagical plants without being slowed by them and without taking damage from them if they have thorns, spines, or a similar hazard. In addition, you have advantage on saving throws against plants that are magically created or manipulated to impede movement, such those created by the entangle spell.'
            },
        ],
        10: [
            {
                'name': 'Nature\'s Ward',
                'description': 'When you reach 10th level, you can\'t be charmed or frightened by elementals or fey, and you are immune to poison and disease.'
            },
        ],
        14: [
            {
                'name': 'Nature\'s Sanctuary',
                'description': 'When you reach 14th level, creatures of the natural world sense your connection to nature and become hesitant to attack you. When a beast or plant creature attacks you, that creature must make a Wisdom saving throw against your druid spell save DC. On a failed save, the creature must choose a different target, or the attack automatically misses. On a successful save, the creature is immune to this effect for 24 hours. The creature is aware of this effect before it makes its attack against you.'
            },
        ],
    },

    'Way of the Open Hand': {
        3: [
            {
                'name': 'Open Hand Technique',
                'description': 'Starting when you choose this tradition at 3rd level, you can manipulate your enemy\'s ki when you harness your own. Whenever you hit a creature with one of the attacks granted by your Flurry of Blows, you can impose one of the following effects on that target: It must succeed on a Dexterity saving throw or be knocked prone. It must make a Strength saving throw. If it fails, you can push it up to 15 feet away from you. It can\'t take reactions until the end of your next turn.'
            },
        ],
        6: [
            {
                'name': 'Wholeness of Body',
                'description': 'At 6th level, you gain the ability to heal yourself. As an action, you can regain hit points equal to three times your monk level. You must finish a long rest before you can use this feature again.'
            },
        ],
        11: [
            {
                'name': 'Tranquility',
                'description': 'Beginning at 11th level, you can enter a special meditation that surrounds you with an aura of peace. At the end of a long rest, you gain the effect of a sanctuary spell that lasts until the start of your next long rest (the spell can end early as normal). The saving throw DC for the spell equals 8 + your Wisdom modifier + your proficiency bonus.'
            },
        ],
        17: [
            {
                'name': 'Quivering Palm',
                'description': 'At 17th level, you gain the ability to set up lethal vibrations in someone\'s body. When you hit a creature with an unarmed strike, you can spend 3 ki points to start these imperceptible vibrations, which last for a number of days equal to your monk level. The vibrations are harmless unless you use your action to end them. To do so, you and the target must be on the same plane of existence. When you use this action, the creature must make a Constitution saving throw. If it fails, it is reduced to 0 hit points. If it succeeds, it takes 10d10 necrotic damage.'
            },
        ],
    },

    'Oath of Devotion': {
        3: [
            {
                'name': 'Channel Divinity: Sacred Weapon',
                'description': 'As an action, you can imbue one weapon that you are holding with positive energy, using your Channel Divinity. For 1 minute, you add your Charisma modifier to attack rolls made with that weapon (with a minimum bonus of +1). The weapon also emits bright light in a 20-foot radius and dim light 20 feet beyond that. If the weapon is not already magical, it becomes magical for the duration. You can end this effect on your turn as part of any other action. If you are no longer holding or carrying this weapon, or if you fall unconscious, this effect ends.'
            },
            {
                'name': 'Channel Divinity: Turn the Unholy',
                'description': 'As an action, you present your holy symbol and speak a prayer censuring fiends and undead, using your Channel Divinity. Each fiend or undead that can see or hear you within 30 feet of you must make a Wisdom saving throw. If the creature fails its saving throw, it is turned for 1 minute or until it takes damage. A turned creature must spend its turns trying to move as far away from you as it can, and it can\'t willingly move to a space within 30 feet of you. It also can\'t take reactions. For its action, it can use only the Dash action or try to escape from an effect that prevents it from moving. If there\'s nowhere to move, the creature can use the Dodge action.'
            },
        ],
        7: [
            {
                'name': 'Aura of Devotion',
                'description': 'Starting at 7th level, you and friendly creatures within 10 feet of you can\'t be charmed while you are conscious. At 18th level, the range of this aura increases to 30 feet.'
            },
        ],
        15: [
            {
                'name': 'Purity of Spirit',
                'description': 'Beginning at 15th level, you are always under the effects of a protection from evil and good spell.'
            },
        ],
        20: [
            {
                'name': 'Holy Nimbus',
                'description': 'At 20th level, as an action, you can emanate an aura of sunlight. For 1 minute, bright light shines from you in a 30-foot radius, and dim light shines 30 feet beyond that. Whenever an enemy creature starts its turn in the bright light, the creature takes 10 radiant damage. In addition, for the duration, you have advantage on saving throws against spells cast by fiends or undead. Once you use this feature, you can\'t use it again until you finish a long rest.'
            },
        ],
    },

    'Hunter': {
        3: [
            {
                'name': 'Hunter\'s Prey',
                'description': 'At 3rd level, you gain one of the following features of your choice. Colossus Slayer. Your tenacity can wear down the most potent foes. When you hit a creature with a weapon attack, the creature takes an extra 1d8 damage if it\'s below its hit point maximum. You can deal this extra damage only once per turn. Giant Killer. When a Large or larger creature within 5 feet of you hits or misses you with an attack, you can use your reaction to attack that creature immediately after its attack, provided that you can see the creature. Horde Breaker. Once on each of your turns when you make a weapon attack, you can make another attack with the same weapon against a different creature that is within 5 feet of the original target and within range of your weapon.'
            },
        ],
        7: [
            {
                'name': 'Defensive Tactics',
                'description': 'At 7th level, you gain one of the following features of your choice. Escape the Horde. Opportunity attacks against you are made with disadvantage. Multiattack Defense. When a creature hits you with an attack, you gain a +4 bonus to AC against all subsequent attacks made by that creature for the rest of the turn. Steel Will. You have advantage on saving throws against being frightened.'
            },
        ],
        11: [
            {
                'name': 'Multiattack',
                'description': 'At 11th level, you gain one of the following features of your choice. Volley. You can use your action to make a ranged attack against any number of creatures within 10 feet of a point you can see within your weapon\'s range. You must have ammunition for each target, as normal, and you make a separate attack roll for each target. Whirlwind Attack. You can use your action to make a melee attack against any number of creatures within 5 feet of you, with a separate attack roll for each target.'
            },
        ],
        15: [
            {
                'name': 'Superior Hunter\'s Defense',
                'description': 'At 15th level, you gain one of the following features of your choice. Evasion. When you are subjected to an effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail. Stand Against the Tide. When a hostile creature misses you with a melee attack, you can use your reaction to force that creature to repeat the same attack against another creature (other than itself) of your choice. Uncanny Dodge. When an attacker that you can see hits you with an attack, you can use your reaction to halve the attack\'s damage against you.'
            },
        ],
    },

    'Thief': {
        3: [
            {
                'name': 'Fast Hands',
                'description': 'Starting at 3rd level, you can use the bonus action granted by your Cunning Action to make a Dexterity (Sleight of Hand) check, use your thieves\' tools to disarm a trap or open a lock, or take the Use an Object action.'
            },
            {
                'name': 'Second-Story Work',
                'description': 'When you choose this archetype at 3rd level, you gain the ability to climb faster than normal; climbing no longer costs you extra movement. In addition, when you make a running jump, the distance you can cover increases by a number of feet equal to your Dexterity modifier.'
            },
        ],
        9: [
            {
                'name': 'Supreme Sneak',
                'description': 'Starting at 9th level, you have advantage on a Dexterity (Stealth) check if you move no more than half your speed on the same turn.'
            },
        ],
        13: [
            {
                'name': 'Use Magic Device',
                'description': 'By 13th level, you have learned enough about the workings of magic that you can improvise the use of items even when they are not intended for you. You ignore all class, race, and level requirements on the use of magic items.'
            },
        ],
        17: [
            {
                'name': 'Thief\'s Reflexes',
                'description': 'When you reach 17th level, you have become adept at laying ambushes and quickly escaping danger. You can take two turns during the first round of any combat. You take your first turn at your normal initiative and your second turn at your initiative minus 10. You can\'t use this feature when you are surprised.'
            },
        ],
    },

    'Assassin': {
        3: [
            {
                'name': 'Bonus Proficiencies',
                'description': 'When you choose this archetype at 3rd level, you gain proficiency with the disguise kit and the poisoner\'s kit.'
            },
            {
                'name': 'Assassinate',
                'description': 'Starting at 3rd level, you are at your deadliest when you get the drop on your enemies. You have advantage on attack rolls against any creature that hasn\'t taken a turn in the combat yet. In addition, any hit you score against a creature that is surprised is a critical hit.'
            },
        ],
        9: [
            {
                'name': 'Infiltration Expertise',
                'description': 'Starting at 9th level, you can unfailingly create false identities for yourself. You must spend seven days and 25 gp to establish the history, profession, and affiliations for an identity.'
            },
        ],
        13: [
            {
                'name': 'Impostor',
                'description': 'At 13th level, you gain the ability to unerringly mimic another person\'s speech, writing, and behavior. You must spend at least three hours studying these three components of the person\'s behavior.'
            },
        ],
        17: [
            {
                'name': 'Death Strike',
                'description': 'Starting at 17th level, you become a master of instant death. When you attack and hit a creature that is surprised, it must make a Constitution saving throw (DC 8 + your Dexterity modifier + your proficiency bonus). On a failed save, double the damage of your attack against the creature.'
            },
        ],
    },

    'Draconic Bloodline': {
        1: [
            {
                'name': 'Dragon Ancestor',
                'description': 'At 1st level, you choose one type of dragon as your ancestor. The damage type associated with each dragon is used by features you gain later. You can speak, read, and write Draconic. Additionally, whenever you make a Charisma check when interacting with dragons, your proficiency bonus is doubled if it applies to the check.'
            },
            {
                'name': 'Draconic Resilience',
                'description': 'As your draconic ancestry manifests, your hit point maximum increases by 1 and increases by 1 again whenever you gain a level in this class. Additionally, parts of your skin are covered by a thin sheen of dragon-like scales. When you aren\'t wearing armor, your AC equals 13 + your Dexterity modifier.'
            },
        ],
        6: [
            {
                'name': 'Elemental Affinity',
                'description': 'Starting at 6th level, when you cast a spell that deals damage of the type associated with your draconic ancestry, you can add your Charisma modifier to one damage roll of that spell. At the same time, you can spend 1 sorcery point to gain resistance to that damage type for 1 hour.'
            },
        ],
        14: [
            {
                'name': 'Dragon Wings',
                'description': 'At 14th level, you gain the ability to sprout a pair of dragon wings from your back, gaining a flying speed equal to your current speed. You can create these wings as a bonus action on your turn. They last until you dismiss them as a bonus action on your turn. You can\'t manifest your wings while wearing armor unless the armor is made to accommodate them, and clothing not made to accommodate them might be destroyed when you manifest them.'
            },
        ],
        18: [
            {
                'name': 'Draconic Presence',
                'description': 'Beginning at 18th level, you can channel the dread presence of your dragon ancestor, causing those around you to become awestruck or frightened. As an action, you can spend 5 sorcery points to draw on this power and exude an aura of awe or fear (your choice) to a distance of 60 feet. For 1 minute or until you lose your concentration (as if you were casting a concentration spell), each hostile creature that starts its turn in this aura must succeed on a Wisdom saving throw or be charmed (if you chose awe) or frightened (if you chose fear) until the aura ends. A creature that succeeds on this saving throw is immune to your aura for 24 hours.'
            },
        ],
    },

    'The Fiend': {
        1: [
            {
                'name': 'Dark One\'s Blessing',
                'description': 'Starting at 1st level, when you reduce a hostile creature to 0 hit points, you gain temporary hit points equal to your Charisma modifier + your warlock level (minimum of 1).'
            },
        ],
        6: [
            {
                'name': 'Dark One\'s Own Luck',
                'description': 'Starting at 6th level, you can call on your patron to alter fate in your favor. When you make an ability check or a saving throw, you can use this feature to add a d10 to your roll. You can do so after seeing the initial roll but before any of the roll\'s effects occur. Once you use this feature, you can\'t use it again until you finish a short or long rest.'
            },
        ],
        10: [
            {
                'name': 'Fiendish Resilience',
                'description': 'Starting at 10th level, you can choose one damage type when you finish a short or long rest. You gain resistance to that damage type until you choose a different one with this feature. Damage from magical weapons or silver weapons ignores this resistance.'
            },
        ],
        14: [
            {
                'name': 'Hurl Through Hell',
                'description': 'Starting at 14th level, when you hit a creature with an attack, you can use this feature to instantly transport the target through the lower planes. The creature disappears and hurtles through a nightmare landscape. At the end of your next turn, the target returns to the space it previously occupied, or the nearest unoccupied space. If the target is not a fiend, it takes 10d10 psychic damage as it reels from its horrific experience. Once you use this feature, you can\'t use it again until you finish a long rest.'
            },
        ],
    },

    'School of Evocation': {
        2: [
            {
                'name': 'Evocation Savant',
                'description': 'Beginning when you select this school at 2nd level, the gold and time you must spend to copy an evocation spell into your spellbook is halved.'
            },
            {
                'name': 'Sculpt Spells',
                'description': 'Beginning at 2nd level, you can create pockets of relative safety within the effects of your evocation spells. When you cast an evocation spell that affects other creatures that you can see, you can choose a number of them equal to 1 + the spell\'s level. The chosen creatures automatically succeed on their saving throws against the spell, and they take no damage if they would normally take half damage on a successful save.'
            },
        ],
        6: [
            {
                'name': 'Potent Cantrip',
                'description': 'Starting at 6th level, your damaging cantrips affect even creatures that avoid the brunt of the effect. When a creature succeeds on a saving throw against your cantrip, the creature takes half the cantrip\'s damage (if any) but suffers no additional effect from the cantrip.'
            },
        ],
        10: [
            {
                'name': 'Empowered Evocation',
                'description': 'Beginning at 10th level, you can add your Intelligence modifier to the damage roll of any wizard evocation spell you cast.'
            },
        ],
        14: [
            {
                'name': 'Overchannel',
                'description': 'Starting at 14th level, you can increase the power of your simpler spells. When you cast a wizard spell of 5th level or lower that deals damage, you can deal maximum damage with that spell. The first time you do so, you suffer no adverse effect. If you use this feature again before you finish a long rest, you take 2d12 necrotic damage for each level of the spell, immediately after you cast it. This damage can\'t be reduced or prevented in any way.'
            },
        ],
    },

    'Path of the Berserker': {
        3: [
            {
                'name': 'Frenzy',
                'description': 'Starting when you choose this path at 3rd level, you can go into a frenzy when you rage. If you do so, for the duration of your rage you can make a single melee weapon attack as a bonus action on each of your turns after this one. When your rage ends, you suffer one level of exhaustion.'
            },
        ],
        6: [
            {
                'name': 'Mindless Rage',
                'description': 'Beginning at 6th level, you can\'t be charmed or frightened while raging. If you are charmed or frightened when you enter your rage, the effect is suspended for the duration of the rage.'
            },
        ],
        10: [
            {
                'name': 'Intimidating Presence',
                'description': 'Beginning at 10th level, you can use your action to frighten someone with your menacing presence. When you do so, choose one creature that you can see within 30 feet of you. If the creature can see or hear you, it must succeed on a Wisdom saving throw (DC equal to 8 + your proficiency bonus + your Charisma modifier) or be frightened of you until the end of your next turn. On subsequent turns, you can use your action to extend the duration of this effect on the frightened creature until the end of your next turn. This effect ends early if the frightened creature ends its turn in a location where it doesn\'t have line of sight to you. The effect also ends if the creature has succeeded on a saving throw against an effect that uses the same DC as this feature.'
            },
        ],
        14: [
            {
                'name': 'Retaliation',
                'description': 'Starting at 14th level, when you take damage from a creature that is within 5 feet of you, you can use your reaction to make a melee weapon attack against that creature.'
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