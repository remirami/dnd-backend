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
            CharacterClass.objects.get_or_create(
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
                'description': 'Humans are the most adaptable and ambitious people among the common races.'
            },
            {
                'name': 'elf',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'DEX+2',
                'description': 'Elves are a magical people of otherworldly grace, living in the world but not entirely part of it.'
            },
            {
                'name': 'dwarf',
                'size': 'M',
                'speed': 25,
                'ability_score_increases': 'CON+2',
                'description': 'Bold and hardy, dwarves are known as skilled warriors, miners, and workers of stone and metal.'
            },
            {
                'name': 'halfling',
                'size': 'S',
                'speed': 25,
                'ability_score_increases': 'DEX+2',
                'description': 'The diminutive halflings survive in a world full of larger creatures by avoiding notice.'
            },
            {
                'name': 'dragonborn',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+2,CHA+1',
                'description': 'Born of dragons, as their name proclaims, the dragonborn walk proudly through a world that greets them with fearful incomprehension.'
            },
            {
                'name': 'gnome',
                'size': 'S',
                'speed': 25,
                'ability_score_increases': 'INT+2',
                'description': 'A gnome\'s energy and enthusiasm for living shines through every inch of their tiny body.'
            },
            {
                'name': 'half-elf',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'CHA+2',
                'description': 'Half-elves combine what some say are the best qualities of their elf and human parents.'
            },
            {
                'name': 'half-orc',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'STR+2,CON+1',
                'description': 'Half-orcs\' grayish pigmentation, sloping foreheads, jutting jaws, prominent teeth, and towering builds make their orcish heritage plain for all to see.'
            },
            {
                'name': 'tiefling',
                'size': 'M',
                'speed': 30,
                'ability_score_increases': 'CHA+2,INT+1',
                'description': 'To be greeted with stares and whispers, to suffer violence and insult on the street, to see mistrust and fear in every eye: this is the lot of the tiefling.'
            },
        ]
        
        for race_data in races:
            CharacterRace.objects.get_or_create(
                name=race_data['name'],
                defaults={
                    'size': race_data['size'],
                    'speed': race_data['speed'],
                    'ability_score_increases': race_data['ability_score_increases'],
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
                'description': 'You have spent your life in the service of a temple to a specific god or pantheon of gods.'
            },
            {
                'name': 'criminal',
                'skill_proficiencies': 'Deception,Stealth',
                'tool_proficiencies': 'Thieves\' Tools',
                'languages': 0,
                'description': 'You are an experienced criminal with a history of breaking the law.'
            },
            {
                'name': 'folk-hero',
                'skill_proficiencies': 'Animal Handling,Survival',
                'tool_proficiencies': 'One type of artisan\'s tools, vehicles (land)',
                'languages': 0,
                'description': 'You come from a humble social rank, but you are destined for so much more.'
            },
            {
                'name': 'noble',
                'skill_proficiencies': 'History,Persuasion',
                'tool_proficiencies': 'One type of gaming set',
                'languages': 1,
                'description': 'You understand wealth, power, and privilege. You carry a noble title, and your family owns land, collects taxes, and wields significant political influence.'
            },
            {
                'name': 'sage',
                'skill_proficiencies': 'Arcana,History',
                'tool_proficiencies': '',
                'languages': 2,
                'description': 'You spent years learning the lore of the multiverse. You scoured manuscripts, studied scrolls, and listened to the greatest experts on the subjects that interest you.'
            },
            {
                'name': 'soldier',
                'skill_proficiencies': 'Athletics,Intimidation',
                'tool_proficiencies': 'One type of gaming set, vehicles (land)',
                'languages': 0,
                'description': 'War has been your life for as long as you care to remember.'
            },
            {
                'name': 'hermit',
                'skill_proficiencies': 'Medicine,Religion',
                'tool_proficiencies': 'Herbalism Kit',
                'languages': 1,
                'description': 'You lived in seclusion—either in a sheltered community such as a monastery, or entirely alone—for a formative part of your life.'
            },
            {
                'name': 'outlander',
                'skill_proficiencies': 'Athletics,Survival',
                'tool_proficiencies': 'One type of musical instrument',
                'languages': 1,
                'description': 'You grew up in the wilds, far from civilization and the comforts of town and technology.'
            },
            {
                'name': 'entertainer',
                'skill_proficiencies': 'Acrobatics,Performance',
                'tool_proficiencies': 'Disguise Kit, one type of musical instrument',
                'languages': 0,
                'description': 'You thrive in front of an audience. You know how to entrance them, entertain them, and even inspire them.'
            },
            {
                'name': 'guild-artisan',
                'skill_proficiencies': 'Insight,Persuasion',
                'tool_proficiencies': 'One type of artisan\'s tools',
                'languages': 1,
                'description': 'You are a member of an artisan\'s guild, skilled in a particular field and closely associated with other artisans.'
            },
            {
                'name': 'charlatan',
                'skill_proficiencies': 'Deception,Sleight of Hand',
                'tool_proficiencies': 'Disguise Kit, Forgery Kit',
                'languages': 0,
                'description': 'You have always had a way with people. You know what makes them tick, you can tease out their secrets, and, with a few leading questions, you can read them like they were children\'s books.'
            },
            {
                'name': 'sailor',
                'skill_proficiencies': 'Athletics,Perception',
                'tool_proficiencies': 'Navigator\'s Tools, vehicles (water)',
                'languages': 0,
                'description': 'You sailed on a seagoing vessel for years. In that time, you faced down mighty storms, monsters of the deep, and those who wanted to sink your craft to the bottomless depths.'
            },
        ]
        
        for bg_data in backgrounds:
            CharacterBackground.objects.get_or_create(
                name=bg_data['name'],
                defaults={
                    'skill_proficiencies': bg_data['skill_proficiencies'],
                    'tool_proficiencies': bg_data['tool_proficiencies'],
                    'languages': bg_data['languages'],
                    'description': bg_data['description']
                }
            )
            self.stdout.write(f'Created/updated background: {bg_data["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated character classes, races, and backgrounds!')
        )

