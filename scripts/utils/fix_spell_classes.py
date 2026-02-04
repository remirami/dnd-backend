import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnd_backend.settings")
django.setup()

from spells.models import Spell
from characters.models import CharacterClass

# Mapping of Class Name -> List of Spell Names (SRD 5.2 subset)
# Ideally this would be the full list, but we'll start with a solid subset to unblock the UI.
# I've included the "Recommended" ones plus common ones.
CLASS_SPELLS = {
    'Wizard': [
        'Fire Bolt', 'Mage Hand', 'Prestidigitation', 'Acid Splash', 'Chill Touch', 'Light', 'Message', 'Minor Illusion', 'Poison Spray', 'Ray of Frost', 'Shocking Grasp', 'True Strike',
        'Mage Armor', 'Magic Missile', 'Shield', 'Sleep', 'Find Familiar', 'Burning Hands', 'Charm Person', 'Chromatic Orb', 'Comprehend Languages', 'Detect Magic', 'Disguise Self', 'Expeditious Retreat', 'False Life', 'Feather Fall', 'Fog Cloud', 'Grease', 'Identify', 'Jump', 'Longstrider', 'Protection from Evil and Good', 'Silent Image', 'Thunderwave', 'Unseen Servant', 'Witch Bolt'
    ],
    'Cleric': [
        'Guidance', 'Sacred Flame', 'Spare the Dying', 'Light', 'Mending', 'Resistance', 'Thaumaturgy',
        'Bless', 'Cure Wounds', 'Guiding Bolt', 'Healing Word', 'Shield of Faith', 'Bane', 'Command', 'Create or Destroy Water', 'Detect Evil and Good', 'Detect Magic', 'Detect Poison and Disease', 'Inflict Wounds', 'Protection from Evil and Good', 'Purify Food and Drink', 'Sanctuary'
    ],
    'Druid': [
        'Druidcraft', 'Produce Flame', 'Shillelagh', 'Guidance', 'Mending', 'Poison Spray', 'Resistance', 'Thorn Whip',
        'Goodberry', 'Entangle', 'Thunderwave', 'Cure Wounds', 'Faerie Fire', 'Animal Friendship', 'Charm Person', 'Create or Destroy Water', 'Detect Magic', 'Detect Poison and Disease', 'Fog Cloud', 'Healing Word', 'Jump', 'Longstrider', 'Purify Food and Drink', 'Speak with Animals'
    ],
    'Sorcerer': [
        'Fire Bolt', 'Mage Hand', 'Minor Illusion', 'Prestidigitation', 'Acid Splash', 'Chill Touch', 'Light', 'Message', 'Poison Spray', 'Ray of Frost', 'Shocking Grasp', 'True Strike',
        'Magic Missile', 'Shield', 'Sleep', 'Burning Hands', 'Mage Armor', 'Charm Person', 'Chromatic Orb', 'Comprehend Languages', 'Detect Magic', 'Disguise Self', 'Expeditious Retreat', 'False Life', 'Feather Fall', 'Fog Cloud', 'Jump', 'Silent Image', 'Thunderwave', 'Witch Bolt'
    ],
    'Warlock': [
        'Eldritch Blast', 'Mage Hand', 'Chill Touch', 'Minor Illusion', 'Poison Spray', 'Prestidigitation', 'True Strike',
        'Hex', 'Hellish Rebuke', 'Protection from Evil and Good', 'Armor of Agathys', 'Arms of Hadar', 'Charm Person', 'Comprehend Languages', 'Expeditious Retreat', 'Illusory Script', 'Unseen Servant', 'Witch Bolt'
    ],
    'Bard': [
        'Vicious Mockery', 'Minor Illusion', 'Blade Ward', 'Dancing Lights', 'Friends', 'Light', 'Mage Hand', 'Mending', 'Message', 'Prestidigitation', 'True Strike',
        'Healing Word', 'Thunderwave', 'Charm Person', 'Heroism', 'Faerie Fire', 'Animal Friendship', 'Bane', 'Comprehend Languages', 'Cure Wounds', 'Detect Magic', 'Disguise Self', 'Dissonant Whispers', 'Feather Fall', 'Identify', 'Longstrider', 'Silent Image', 'Sleep', 'Speak with Animals', 'Tasha\'s Hideous Laughter', 'Unseen Servant'
    ],
    'Paladin': [
          'Bless', 'Cure Wounds', 'Divine Favor', 'Shield of Faith', 'Command', 'Compelled Duel', 'Detect Evil and Good', 'Detect Magic', 'Detect Poison and Disease', 'Heroism', 'Protection from Evil and Good', 'Purify Food and Drink', 'Searing Smite', 'Thunderous Smite', 'Wrathful Smite'
    ],
    'Ranger': [
        'Hunter\'s Mark', 'Cure Wounds', 'Fog Cloud', 'Alarm', 'Animal Friendship', 'Detect Magic', 'Detect Poison and Disease', 'Ensnaring Strike', 'Goodberry', 'Hail of Thorns', 'Jump', 'Longstrider', 'Speak with Animals'
    ]
}

def fix_spells():
    print("Fixing spell class associations...")
    
    for class_name, spell_names in CLASS_SPELLS.items():
        try:
            char_class = CharacterClass.objects.get(name__iexact=class_name)
            print(f"Processing {class_name} ({len(spell_names)} spells)...")
            
            for spell_name in spell_names:
                try:
                    spell = Spell.objects.filter(name__iexact=spell_name).first()
                    if spell:
                        spell.classes.add(char_class)
                        # print(f"  Added {spell.name} to {class_name}")
                    else:
                        print(f"  WARNING: Spell '{spell_name}' not found for {class_name}")
                except Exception as e:
                    print(f"  Error adding {spell_name}: {e}")
                    
        except CharacterClass.DoesNotExist:
            print(f"Error: Class {class_name} not found")

    # Also verify counts
    print("\nVerification:")
    for class_name in CLASS_SPELLS.keys():
        count = Spell.objects.filter(classes__name__iexact=class_name).count()
        print(f"{class_name}: {count} spells linked")

if __name__ == '__main__':
    fix_spells()
