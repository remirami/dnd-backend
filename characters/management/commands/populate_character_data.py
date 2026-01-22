from django.core.management.base import BaseCommand
from characters.models import CharacterClass, CharacterRace, CharacterBackground


class Command(BaseCommand):
    help = 'Populate D&D 5e character classes, races, and backgrounds'

    def handle(self, *args, **options):
        # D&D 5e Character Classes
        classes = [
            {
                'name': 'barbarian',
                'hit_dice': 'd12',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'STR,CON',
                'description': 'A fierce warrior of primitive background who can enter a battle rage.'
            },
            {
                'name': 'bard',
                'hit_dice': 'd8',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'DEX,CHA',
                'description': 'An inspiring magician whose power echoes the music of creation.'
            },
            {
                'name': 'cleric',
                'hit_dice': 'd8',
                'primary_ability': 'WIS',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A priestly champion who wields divine magic in service of a higher power.'
            },
            {
                'name': 'druid',
                'hit_dice': 'd8',
                'primary_ability': 'WIS',
                'saving_throw_proficiencies': 'INT,WIS',
                'description': 'A priest of the Old Faith, wielding the powers of nature.'
            },
            {
                'name': 'fighter',
                'hit_dice': 'd10',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'STR,CON',
                'description': 'A master of martial combat, skilled with a variety of weapons and armor.'
            },
            {
                'name': 'monk',
                'hit_dice': 'd8',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'STR,DEX',
                'description': 'A master of martial arts, harnessing the power of the body in pursuit of physical and spiritual perfection.'
            },
            {
                'name': 'paladin',
                'hit_dice': 'd10',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A holy warrior bound to a sacred oath.'
            },
            {
                'name': 'ranger',
                'hit_dice': 'd10',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'STR,DEX',
                'description': 'A warrior who uses martial prowess and nature magic to combat threats on the edges of civilization.'
            },
            {
                'name': 'rogue',
                'hit_dice': 'd8',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'DEX,INT',
                'description': 'A scoundrel who uses stealth and trickery to overcome obstacles and enemies.'
            },
            {
                'name': 'sorcerer',
                'hit_dice': 'd6',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'CON,CHA',
                'description': 'A spellcaster who draws on inherent magic from a gift or bloodline.'
            },
            {
                'name': 'warlock',
                'hit_dice': 'd8',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A wielder of magic that is derived from a bargain with an extraplanar entity.'
            },
            {
                'name': 'wizard',
                'hit_dice': 'd6',
                'primary_ability': 'INT',
                'saving_throw_proficiencies': 'INT,WIS',
                'description': 'A scholarly magic-user capable of manipulating the structures of reality.'
            },
        ]
        
        for class_data in classes:
            CharacterClass.objects.update_or_create(
                name=class_data['name'],
                defaults={
                    'hit_dice': class_data['hit_dice'],
                    'primary_ability': class_data['primary_ability'],
                    'saving_throw_proficiencies': class_data['saving_throw_proficiencies'],
                    'description': class_data['description']
                }
            )
            self.stdout.write(f'Created/updated class: {class_data["name"]}')
        
        # D&D 5e Character Races
        races = [
            {
                'name': 'human',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+1,DEX+1,CON+1,INT+1,WIS+1,CHA+1',
                'skill_proficiencies': 'Persuasion',
                'traits': [
                    {'name': 'Extra Language', 'description': 'You can speak, read, and write one extra language of your choice.'}
                ],
                'description': 'Humans are the most adaptable and ambitious people among the common races.'
            },
            {
                'name': 'elf',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'DEX+2',
                'skill_proficiencies': 'Perception',
                'traits': [
                    {'name': 'Darkvision', 'description': 'Accustomed to twilit forests and the night sky, you have superior vision in dark and dim conditions.'},
                    {'name': 'Fey Ancestry', 'description': 'You have advantage on saving throws against being charmed, and magic can’t put you to sleep.'},
                    {'name': 'Trance', 'description': 'Elves don’t need to sleep. Instead, they meditate deeply, remaining semiconscious, for 4 hours a day.'}
                ],
                'description': 'Elves are a magical people of otherworldly grace, living in the world but not entirely part of it.'
            },
            {
                'name': 'dwarf',
                'size': 'M',
                'speed': 25,
                'ability_score_increases': 'CON+2',
                'skill_proficiencies': '',
                'traits': [
                    {'name': 'Darkvision', 'description': 'Accustomed to life underground, you have superior vision in dark and dim conditions.'},
                    {'name': 'Dwarven Resilience', 'description': 'You have advantage on saving throws against poison, and you have resistance against poison damage.'},
                    {'name': 'Stonecunning', 'description': 'Whenever you make an Intelligence (History) check related to the origin of stonework, you are considered proficient in the History skill and add double your proficiency bonus to the check.'}
                ],
                'description': 'Bold and hardy, dwarves are known as skilled warriors, miners, and workers of stone and metal.'
            },
            {
                'name': 'halfling',
                'size': 'S',
                'speed': 25,
                'ability_score_increases': 'DEX+2',
                'skill_proficiencies': '',
                'traits': [
                    {'name': 'Lucky', 'description': 'When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and must use the new roll.'},
                    {'name': 'Brave', 'description': 'You have advantage on saving throws against being frightened.'},
                    {'name': 'Halfling Nimbleness', 'description': 'You can move through the space of any creature that is of a size larger than yours.'}
                ],
                'description': 'The diminutive halflings survive in a world full of larger creatures by avoiding notice.'
            },
            {
                'name': 'dragonborn',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+2,CHA+1',
                'skill_proficiencies': '',
                'traits': [
                    {'name': 'Draconic Ancestry', 'description': 'You have draconic ancestry. Choose one type of dragon from the Draconic Ancestry table.'},
                    {'name': 'Breath Weapon', 'description': 'You can use your action to exhale destructive energy.'},
                    {'name': 'Damage Resistance', 'description': 'You have resistance to the damage type associated with your draconic ancestry.'}
                ],
                'description': 'Born of dragons, as their name proclaims, the dragonborn walk proudly through a world that greets them with fearful incomprehension.'
            },
            {
                'name': 'gnome',
                'size': 'S',
                'speed': 25,
                'ability_score_increases': 'INT+2',
                'skill_proficiencies': '',
                'traits': [
                    {'name': 'Darkvision', 'description': 'Accustomed to life underground, you have superior vision in dark and dim conditions.'},
                    {'name': 'Gnome Cunning', 'description': 'You have advantage on all Intelligence, Wisdom, and Charisma saving throws against magic.'}
                ],
                'description': 'A gnome\'s energy and enthusiasm for living shines through every inch of their tiny body.'
            },
            {
                'name': 'half-elf',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'CHA+2',
                'skill_proficiencies': '', # Usually choice of 2, hard to model simply. Leave empty for now or give defaults? Defaults: Perception, Deception?
                # Actually, standard is "Skill Versatility: You gain proficiency in two skills of your choice."
                # I'll just leave it empty for now as user choice is handled elsewhere or manual.
                'traits': [
                    {'name': 'Darkvision', 'description': 'Thanks to your elf blood, you have superior vision in dark and dim conditions.'},
                    {'name': 'Fey Ancestry', 'description': 'You have advantage on saving throws against being charmed, and magic can’t put you to sleep.'},
                ],
                'description': 'Half-elves combine what some say are the best qualities of their elf and human parents.'
            },
            {
                'name': 'half-orc',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+2,CON+1',
                'skill_proficiencies': 'Intimidation',
                'traits': [
                    {'name': 'Darkvision', 'description': 'Thanks to your orc blood, you have superior vision in dark and dim conditions.'},
                    {'name': 'Relentless Endurance', 'description': 'When you are reduced to 0 hit points but not killed outright, you can drop to 1 hit point instead. You can’t use this feature again until you finish a long rest.'},
                    {'name': 'Savage Attacks', 'description': 'When you score a critical hit with a melee weapon attack, you can roll one of the weapon’s damage dice one additional time and add it to the extra damage of the critical hit.'}
                ],
                'description': 'Half-orcs\' grayish pigmentation, sloping foreheads, jutting jaws, prominent teeth, and towering builds make their orcish heritage plain for all to see.'
            },
            {
                'name': 'tiefling',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'CHA+2,INT+1',
                'skill_proficiencies': '',
                'traits': [
                    {'name': 'Darkvision', 'description': 'Thanks to your infernal heritage, you have superior vision in dark and dim conditions.'},
                    {'name': 'Hellish Resistance', 'description': 'You have resistance to fire damage.'},
                    {'name': 'Infernal Legacy', 'description': 'You know the thaumaturgy cantrip. Once you reach 3rd level, you can cast the hellish rebuke spell once per day as a 2nd-level spell. Once you reach 5th level, you can also cast the darkness spell once per day. Charisma is your spellcasting ability for these spells.'}
                ],
                'description': 'To be greeted with stares and whispers, to suffer violence and insult on the street, to see mistrust and fear in every eye: this is the lot of the tiefling.'
            },
        ]
        
        for race_data in races:
            CharacterRace.objects.update_or_create(
                name=race_data['name'],
                defaults={
                    'size': race_data['size'],
                    'speed': race_data['speed'],
                    'ability_score_increases': race_data['ability_score_increases'],
                    'skill_proficiencies': race_data.get('skill_proficiencies', ''),
                    'traits': race_data.get('traits', []),
                    'description': race_data['description']
                }
            )
            self.stdout.write(f'Created/updated race: {race_data["name"]}')
        
        # D&D 5e Character Backgrounds
        backgrounds = [
            {
                'name': 'acolyte',
                'skill_proficiencies': 'Insight,Religion',
                'tool_proficiencies': '',
                'languages': 2,
                'feature_name': 'Shelter of the Faithful',
                'feature_description': 'As an acolyte, you command the respect of those who share your faith, and you can perform religious ceremonies. You and your adventuring companions can expect to receive free healing and care at a temple, shrine, or other established presence of your faith.',
                'description': 'You have spent your life in the service of a temple to a specific god or pantheon of gods.'
            },
            {
                'name': 'criminal',
                'skill_proficiencies': 'Deception,Stealth',
                'tool_proficiencies': 'Thieves\' Tools',
                'languages': 0,
                'feature_name': 'Criminal Contact',
                'feature_description': 'You have a reliable and trustworthy contact who acts as your liaison to a network of other criminals. You know how to get messages to and from your contact, even over great distances.',
                'description': 'You are an experienced criminal with a history of breaking the law.'
            },
            {
                'name': 'folk-hero',
                'skill_proficiencies': 'Animal Handling,Survival',
                'tool_proficiencies': 'One type of artisan\'s tools, vehicles (land)',
                'languages': 0,
                'feature_name': 'Rustic Hospitality',
                'feature_description': 'Since you come from the ranks of the common folk, you fit in among them with ease. You can find a place to hide, rest, or recuperate among other commoners, unless you have shown yourself to be a danger to them.',
                'description': 'You come from a humble social rank, but you are destined for so much more.'
            },
            {
                'name': 'noble',
                'skill_proficiencies': 'History,Persuasion',
                'tool_proficiencies': 'One type of gaming set',
                'languages': 1,
                'feature_name': 'Position of Privilege',
                'feature_description': 'Thanks to your noble birth, people are inclined to think the best of you. You are welcome in high society, and people assume you have the right to be wherever you are. The common folk make every effort to accommodate you and avoid your displeasure.',
                'description': 'You understand wealth, power, and privilege. You carry a noble title, and your family owns land, collects taxes, and wields significant political influence.'
            },
            {
                'name': 'sage',
                'skill_proficiencies': 'Arcana,History',
                'tool_proficiencies': '',
                'languages': 2,
                'feature_name': 'Researcher',
                'feature_description': 'When you attempt to learn or recall a piece of lore, if you do not know that information, you often know where and from whom you can obtain it.',
                'description': 'You spent years learning the lore of the multiverse. You scoured manuscripts, studied scrolls, and listened to the greatest experts on the subjects that interest you.'
            },
            {
                'name': 'soldier',
                'skill_proficiencies': 'Athletics,Intimidation',
                'tool_proficiencies': 'One type of gaming set, vehicles (land)',
                'languages': 0,
                'feature_name': 'Military Rank',
                'feature_description': 'You have a military rank from your career as a soldier. Soldiers loyal to your former military organization still recognize your authority and influence, and they defer to you if they are of a lower rank.',
                'description': 'War has been your life for as long as you care to remember.'
            },
            {
                'name': 'hermit',
                'skill_proficiencies': 'Medicine,Religion',
                'tool_proficiencies': 'Herbalism Kit',
                'languages': 1,
                'feature_name': 'Discovery',
                'feature_description': 'The quiet seclusion of your extended hermitage gave you access to a unique and powerful discovery. The exact nature of this revelation depends on the nature of your seclusion.',
                'description': 'You lived in seclusion—either in a sheltered community such as a monastery, or entirely alone—for a formative part of your life.'
            },
            {
                'name': 'outlander',
                'skill_proficiencies': 'Athletics,Survival',
                'tool_proficiencies': 'One type of musical instrument',
                'languages': 1,
                'feature_name': 'Wanderer',
                'feature_description': 'You have an excellent memory for maps and geography, and you can always recall the general layout of terrain, settlements, and other features around you. In addition, you can find food and fresh water for yourself and up to five other people each day.',
                'description': 'You grew up in the wilds, far from civilization and the comforts of town and technology.'
            },
            {
                'name': 'entertainer',
                'skill_proficiencies': 'Acrobatics,Performance',
                'tool_proficiencies': 'Disguise Kit, one type of musical instrument',
                'languages': 0,
                'feature_name': 'By Popular Demand',
                'feature_description': 'You can always find a place to perform, usually in an inn or tavern but possibly with a circus, at a theater, or even in a noble’s court. At such a place, you receive free lodging and food of a modest or comfortable standard.',
                'description': 'You thrive in front of an audience. You know how to entrance them, entertain them, and even inspire them.'
            },
            {
                'name': 'guild-artisan',
                'skill_proficiencies': 'Insight,Persuasion',
                'tool_proficiencies': 'One type of artisan\'s tools',
                'languages': 1,
                'feature_name': 'Guild Membership',
                'feature_description': 'As an established and respected member of a guild, you can rely on certain benefits that membership provides. Your fellow guild members will provide you with lodging and food if necessary, and pay for your funeral if needed.',
                'description': 'You are a member of an artisan\'s guild, skilled in a particular field and closely associated with other artisans.'
            },
            {
                'name': 'charlatan',
                'skill_proficiencies': 'Deception,Sleight of Hand',
                'tool_proficiencies': 'Disguise Kit, Forgery Kit',
                'languages': 0,
                'feature_name': 'False Identity',
                'feature_description': 'You have created a second identity that includes documentation, established acquaintances, and disguises that allow you to assume that persona. Additionally, you can forge documents including official papers and personal letters.',
                'description': 'You have always had a way with people. You know what makes them tick, you can tease out their secrets, and, with a few leading questions, you can read them like they were children\'s books.'
            },
            {
                'name': 'sailor',
                'skill_proficiencies': 'Athletics,Perception',
                'tool_proficiencies': 'Navigator\'s Tools, vehicles (water)',
                'languages': 0,
                'feature_name': 'Ship\'s Passage',
                'feature_description': 'When you need to, you can secure free passage on a sailing ship for yourself and your adventuring companions. You might sail on the ship you served on, or another ship you have good relations with.',
                'description': 'You sailed on a seagoing vessel for years. In that time, you faced down mighty storms, monsters of the deep, and those who wanted to sink your craft to the bottomless depths.'
            },
            {
                'name': 'athlete',
                'skill_proficiencies': 'Acrobatics,Athletics',
                'tool_proficiencies': 'Vehicles (land)',
                'languages': 1,
                'feature_name': 'Eco-Mover',
                'feature_description': 'You have advantage on saving throws made against extreme environmental hazards (heat, cold, altitude). You can also carry 20% more weight than your Strength allows before being encumbered.',
                'description': 'You strive for physical perfection and elite performance, whether in the arena, the wilderness, or the dungeon.'
            }
        ]
        
        for bg_data in backgrounds:
            CharacterBackground.objects.update_or_create(
                name=bg_data['name'],
                defaults={
                    'skill_proficiencies': bg_data['skill_proficiencies'],
                    'tool_proficiencies': bg_data['tool_proficiencies'],
                    'languages': bg_data['languages'],
                    'feature_name': bg_data.get('feature_name', ''),
                    'feature_description': bg_data.get('feature_description', ''),
                    'description': bg_data['description']
                }
            )
            self.stdout.write(f'Created/updated background: {bg_data["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated character classes, races, and backgrounds!')
        )

