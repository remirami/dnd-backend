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
                'description': 'A fierce warrior of primitive background who can enter a battle rage.',
                'skill_proficiency_choices': 'Animal Handling,Athletics,Intimidation,Nature,Perception,Survival',
                'num_skill_choices': 2
            },
            {
                'name': 'bard',
                'hit_dice': 'd8',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'DEX,CHA',
                'description': 'An inspiring magician whose power echoes the music of creation.',
                'skill_proficiency_choices': 'Acrobatics,Animal Handling,Arcana,Athletics,Deception,History,Insight,Intimidation,Investigation,Medicine,Nature,Perception,Performance,Persuasion,Religion,Sleight of Hand,Stealth,Survival',
                'num_skill_choices': 3
            },
            {
                'name': 'cleric',
                'hit_dice': 'd8',
                'primary_ability': 'WIS',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A priestly champion who wields divine magic in service of a higher power.',
                'skill_proficiency_choices': 'History,Insight,Medicine,Persuasion,Religion',
                'num_skill_choices': 2
            },
            {
                'name': 'druid',
                'hit_dice': 'd8',
                'primary_ability': 'WIS',
                'saving_throw_proficiencies': 'INT,WIS',
                'description': 'A priest of the Old Faith, wielding the powers of nature.',
                'skill_proficiency_choices': 'Arcana,Animal Handling,Insight,Medicine,Nature,Perception,Religion,Survival',
                'num_skill_choices': 2
            },
            {
                'name': 'fighter',
                'hit_dice': 'd10',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'STR,CON',
                'description': 'A master of martial combat, skilled with a variety of weapons and armor.',
                'skill_proficiency_choices': 'Acrobatics,Animal Handling,Athletics,History,Insight,Intimidation,Perception,Survival',
                'num_skill_choices': 2
            },
            {
                'name': 'monk',
                'hit_dice': 'd8',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'STR,DEX',
                'description': 'A master of martial arts, harnessing the power of the body in pursuit of physical and spiritual perfection.',
                'skill_proficiency_choices': 'Acrobatics,Athletics,History,Insight,Religion,Stealth',
                'num_skill_choices': 2
            },
            {
                'name': 'paladin',
                'hit_dice': 'd10',
                'primary_ability': 'STR',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A holy warrior bound to a sacred oath.',
                'skill_proficiency_choices': 'Athletics,Insight,Intimidation,Medicine,Persuasion,Religion',
                'num_skill_choices': 2
            },
            {
                'name': 'ranger',
                'hit_dice': 'd10',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'STR,DEX',
                'description': 'A warrior who uses martial prowess and nature magic to combat threats on the edges of civilization.',
                'skill_proficiency_choices': 'Animal Handling,Athletics,Insight,Investigation,Nature,Perception,Stealth,Survival',
                'num_skill_choices': 3
            },
            {
                'name': 'rogue',
                'hit_dice': 'd8',
                'primary_ability': 'DEX',
                'saving_throw_proficiencies': 'DEX,INT',
                'description': 'A scoundrel who uses stealth and trickery to overcome obstacles and enemies.',
                'skill_proficiency_choices': 'Acrobatics,Athletics,Deception,Insight,Intimidation,Investigation,Perception,Performance,Persuasion,Sleight of Hand,Stealth',
                'num_skill_choices': 4
            },
            {
                'name': 'sorcerer',
                'hit_dice': 'd6',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'CON,CHA',
                'description': 'A spellcaster who draws on inherent magic from a gift or bloodline.',
                'skill_proficiency_choices': 'Arcana,Deception,Insight,Intimidation,Persuasion,Religion',
                'num_skill_choices': 2
            },
            {
                'name': 'warlock',
                'hit_dice': 'd8',
                'primary_ability': 'CHA',
                'saving_throw_proficiencies': 'WIS,CHA',
                'description': 'A wielder of magic that is derived from a bargain with an extraplanar entity.',
                'skill_proficiency_choices': 'Arcana,Deception,History,Intimidation,Investigation,Nature,Religion',
                'num_skill_choices': 2
            },
            {
                'name': 'wizard',
                'hit_dice': 'd6',
                'primary_ability': 'INT',
                'saving_throw_proficiencies': 'INT,WIS',
                'description': 'A scholarly magic-user capable of manipulating the structures of reality.',
                'skill_proficiency_choices': 'Arcana,History,Insight,Investigation,Medicine,Religion',
                'num_skill_choices': 2
            },
        ]
        
        for class_data in classes:
            CharacterClass.objects.update_or_create(
                name=class_data['name'],
                defaults={
                    'hit_dice': class_data['hit_dice'],
                    'primary_ability': class_data['primary_ability'],
                    'saving_throw_proficiencies': class_data['saving_throw_proficiencies'],
                    'description': class_data['description'],
                    'skill_proficiency_choices': class_data.get('skill_proficiency_choices', ''),
                    'num_skill_choices': class_data.get('num_skill_choices', 0)
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

