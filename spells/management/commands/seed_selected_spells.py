import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from spells.models import Spell
from characters.models import CharacterClass

# List provided by user (Levels 2-9)
APPROVED_SPELLS = [
    # Level 2
    "Aid", "Alter Self", "Animal Messenger", "Arcane Lock", "Augury", 
    "Blindness/Deafness", "Blur", "Calm Emotions", "Continual Flame", 
    "Crown of Madness", "Darkness", "Darkvision", "Detect Thoughts", 
    "Enhance Ability", "Enlarge/Reduce", "Enthrall", "Flaming Sphere", 
    "Gentle Repose", "Gust of Wind", "Hold Person", "Invisibility", 
    "Knock", "Levitate", "Locate Object", "Magic Mouth", "Magic Weapon", 
    "Mirror Image", "Misty Step", "Pass Without Trace", "Prayer of Healing", 
    "Protection from Poison", "Ray of Enfeeblement", "Rope Trick", 
    "Scorching Ray", "See Invisibility", "Shatter", "Silence", 
    "Spider Climb", "Spike Growth", "Suggestion", "Web",
    
    # Level 3
    "Animate Dead", "Beacon of Hope", "Bestow Curse", "Blink", 
    "Call Lightning", "Clairvoyance", "Create Food and Water", "Daylight", 
    "Dispel Magic", "Elementalism", "Fear", "Fireball", "Fly", 
    "Gaseous Form", "Glyph of Warding", "Haste", "Hypnotic Pattern", 
    "Leomund's Tiny Hut", "Lightning Bolt", "Magic Circle", "Major Image", 
    "Nondetection", "Phantom Steed", "Protection from Energy", 
    "Remove Curse", "Revivify", "Sending", "Sleet Storm", "Slow", 
    "Stinking Cloud", "Tongues", "Water Breathing", "Water Walk",
    
    # Level 4
    "Arcane Eye", "Banishment", "Blight", "Confusion", "Dimension Door", 
    "Evard's Black Tentacles", "Freedom of Movement", "Greater Invisibility", 
    "Ice Storm", "Locate Creature", "Polymorph", "Stoneskin", "Wall of Fire",
    
    # Level 5
    "Animate Objects", "Cloudkill", "Cone of Cold", "Conjure Elemental", 
    "Conjure Volley", "Creation", "Ensnaring Strike", "Greater Restoration", 
    "Hold Monster", "Immolation", "Mass Cure Wounds", "Planar Binding", 
    "Raise Dead", "Scrying", "Seeming", "Telekinesis", "Teleportation Circle", 
    "Wall of Force", "Wall of Stone", "Wrath of Nature",
    
    # Level 6
    "Arcane Gate", "Chain Lightning", "Circle of Death", "Contingency", 
    "Disintegrate", "Eyebite", "Forbiddance", "Globe of Invulnerability", 
    "Mass Suggestion", "Move Earth", "Otiluke's Freezing Sphere", 
    "Programmed Illusion", "True Seeing", "Wall of Thorns",
    
    # Level 7
    "Delayed Blast Fireball", "Etherealness", "Finger of Death", 
    "Fire Storm", "Mirage Arcane", "Plane Shift", "Prismatic Spray", 
    "Reverse Gravity", "Sequester", "Symbol", "Teleport",
    
    # Level 8
    "Antimagic Field", "Clone", "Control Weather", "Dominate Monster", 
    "Earthquake", "Sunburst", "Telepathy", "Tsunami",
    
    # Level 9
    "Astral Projection", "Foresight", "Gate", "Mass Polymorph", 
    "Power Word Heal", "Power Word Kill", "Prismatic Wall", 
    "Shapechange", "Storm of Vengeance", "Time Stop", "Imprisonment", "True Polymorph",

    # Warlock / Missing SRD Additions
    "Hellish Rebuke", "Armor of Agathys", "Arms of Hadar", "Hunger of Hadar", # Verify SRD status (Hellish Rebuke is SRD, others might not be)
    "Vampiric Touch", "Counterspell", "Hallucinatory Terrain", 
    "Contact Other Plane", "Dream", "Conjure Fey", "Create Undead", "Flesh to Stone",
    "Forcecage", "Demiplane", "Feeblemind", "Glibness", "Power Word Stun"
]

class Command(BaseCommand):
    help = 'Seed only user-approved SRD spells from Open5e API'

    def handle(self, *args, **options):
        self.stdout.write('Fetching spells from Open5e API...')
        
        # Use a dictionary for O(1) lookups
        approved_set = {s.lower().strip() for s in APPROVED_SPELLS}
        
        base_url = 'https://api.open5e.com/spells'
        next_url = base_url
        processed_count = 0
        created_count = 0
        
        while next_url:
            try:
                response = requests.get(next_url, timeout=30)
                response.raise_for_status()
                data = response.json()
                next_url = data.get('next')
                
                for spell_data in data.get('results', []):
                    processed_count += 1
                    name = spell_data.get('name', '').strip()
                    
                    if name.lower() not in approved_set:
                        continue
                        
                    # Map Open5e data to our model
                    spell_defaults = {
                        'slug': spell_data.get('slug', slugify(name)),
                        'level': self._parse_level(spell_data.get('level', 0)),
                        'school': self._parse_school(spell_data.get('school', '')),
                        'casting_time': spell_data.get('casting_time', '1 action'),
                        'range': spell_data.get('range', 'Self'),
                        'components': spell_data.get('components', 'V, S'),
                        'material': spell_data.get('material', ''),
                        'duration': spell_data.get('duration', 'Instantaneous'),
                        'concentration': 'concentration' in spell_data.get('duration', '').lower(),
                        'ritual': spell_data.get('ritual', 'no').lower() == 'yes',
                        'description': spell_data.get('desc', ''),
                        'higher_level': spell_data.get('higher_level', ''),
                        'source_ruleset': '2014', # Most Open5e content is 2014 SRD
                    }
                    
                    spell, created = Spell.objects.update_or_create(
                        name=name,
                        defaults=spell_defaults
                    )
                    
                    if created:
                        self.stdout.write(f'Created: {name}')
                    else:
                        self.stdout.write(f'Updated: {name}')
                        
                    created_count += 1
                    
                    # Add classes
                    if 'dnd_class' in spell_data and spell_data['dnd_class']:
                        self._add_spell_classes(spell, spell_data['dnd_class'])
                
                self.stdout.write(f'Processed {processed_count} spells...')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error fetching spells: {e}'))
                return

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} approved spells.'))

    def _parse_level(self, level_str):
        if isinstance(level_str, int): return level_str
        level_str = str(level_str).lower()
        if 'cantrip' in level_str: return 0
        for i in range(10):
            if str(i) in level_str: return i
        return 0

    def _parse_school(self, school_str):
        school_str = str(school_str).lower().strip()
        valid_schools = ['abjuration', 'conjuration', 'divination', 'enchantment', 
                         'evocation', 'illusion', 'necromancy', 'transmutation']
        for school in valid_schools:
            if school in school_str: return school
        return 'evocation'

    def _add_spell_classes(self, spell, class_string):
        if not class_string: return
        class_names = [c.strip().lower() for c in class_string.split(',')]
        for class_name in class_names:
            try:
                char_class = CharacterClass.objects.filter(name__iexact=class_name).first()
                if char_class:
                    spell.classes.add(char_class)
            except: pass
