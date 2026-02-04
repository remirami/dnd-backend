import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from spells.models import Spell

def cleanup_srd_spells():
    print("Enforcing Strict SRD 5.2.1 Spell List...")

    allowed_spells_text = """
Acid Splash
Chill Touch
Dancing Lights
Druidcraft
Eldritch Blast
Fire Bolt
Guidance
Light
Mage Hand
Mending
Message
Minor Illusion
Poison Spray
Prestidigitation
Produce Flame
Ray of Frost
Resistance
Sacred Flame
Shillelagh
Shocking Grasp
Spare the Dying
Thaumaturgy
True Strike
Vicious Mockery
Alarm
Animal Friendship
Bane
Bless
Burning Hands
Charm Person
Color Spray
Command
Comprehend Languages
Create or Destroy Water
Cure Wounds
Detect Evil and Good
Detect Magic
Detect Poison and Disease
Disguise Self
Divine Favor
Entangle
Expeditious Retreat
Faerie Fire
False Life
Feather Fall
Find Familiar
Floating Disk
Fog Cloud
Goodberry
Grease
Guiding Bolt
Healing Word
Hellish Rebuke
Heroism
Hideous Laughter
Hunter’s Mark
Identify
Illusory Script
Inflict Wounds
Jump
Longstrider
Mage Armor
Magic Missile
Protection from Evil and Good
Purify Food and Drink
Sanctuary
Shield
Shield of Faith
Silent Image
Sleep
Speak with Animals
Thunderwave
Unseen Servant
Aid
Alter Self
Animal Messenger
Arcane Lock
Augury
Blindness/Deafness
Blur
Calm Emotions
Continual Flame
Crown of Madness
Darkness
Darkvision
Detect Thoughts
Enhance Ability
Enlarge/Reduce
Enthrall
Flaming Sphere
Gentle Repose
Gust of Wind
Hold Person
Invisibility
Knock
Levitate
Locate Object
Magic Mouth
Magic Weapon
Mirror Image
Misty Step
Pass Without Trace
Prayer of Healing
Protection from Poison
Ray of Enfeeblement
Rope Trick
Scorching Ray
See Invisibility
Shatter
Silence
Spider Climb
Spike Growth
Suggestion
Web
Animate Dead
Beacon of Hope
Bestow Curse
Blink
Call Lightning
Clairvoyance
Create Food and Water
Daylight
Dispel Magic
Elementalism
Fear
Fireball
Fly
Gaseous Form
Glyph of Warding
Haste
Hypnotic Pattern
Leomund’s Tiny Hut
Lightning Bolt
Magic Circle
Major Image
Nondetection
Phantom Steed
Protection from Energy
Remove Curse
Revivify
Sending
Sleet Storm
Slow
Stinking Cloud
Tongues
Water Breathing
Water Walk
Arcane Eye
Banishment
Blight
Confusion
Dimension Door
Evard’s Black Tentacles
Freedom of Movement
Greater Invisibility
Ice Storm
Locate Creature
Polymorph
Stoneskin
Wall of Fire
Animate Objects
Cloudkill
Cone of Cold
Conjure Elemental
Conjure Volley
Creation
Ensnaring Strike
Greater Restoration
Hold Monster
Immolation
Mass Cure Wounds
Planar Binding
Raise Dead
Scrying
Seeming
Telekinesis
Teleportation Circle
Wall of Force
Wall of Stone
Wrath of Nature
Arcane Gate
Chain Lightning
Circle of Death
Contingency
Disintegrate
Eyebite
Forbiddance
Globe of Invulnerability
Mass Suggestion
Move Earth
Otiluke’s Freezing Sphere
Programmed Illusion
True Seeing
Wall of Thorns
Delayed Blast Fireball
Etherealness
Finger of Death
Fire Storm
Mirage Arcane
Plane Shift
Prismatic Spray
Reverse Gravity
Sequester
Symbol
Teleport
Antimagic Field
Clone
Control Weather
Dominate Monster
Earthquake
Sunburst
Telepathy
Tsunami
Astral Projection
Foresight
Gate
Mass Polymorph
Power Word Heal
Power Word Kill
Prismatic Wall
Shapechange
Storm of Vengeance
Time Stop
"""
    # Parse the list
    allowed_names = set()
    for line in allowed_spells_text.strip().split('\n'):
        name = line.strip()
        if name and not name.startswith("🔮") and not name.startswith("⚡") and not name.startswith("🔥") and not name.startswith("🪄") and not name.startswith("🌀") and not name.startswith("🌊") and not name.startswith("☀️") and not name.startswith("🐉") and not name.startswith("💫") and not name.startswith("🌟") and not name.startswith("📌") and "Level" not in name:
             # Handle special characters like curly quotes in the source text
             # "Hunter’s Mark" -> "Hunter's Mark" normalization might be needed
             # The DB likely uses straight quotes.
             cleaned_name = name.replace('’', "'")
             allowed_names.add(cleaned_name.lower())
             if '’' in name:
                 allowed_names.add(name.lower()) # Add original too just in case

    print(f"Loaded {len(allowed_names)} allowed spell names.")

    # Fetch all spells
    all_spells = Spell.objects.all()
    deleted_count = 0
    kept_count = 0
    
    for spell in all_spells:
        # Check against allowed list (case-insensitive)
        spell_name_lower = spell.name.lower().replace('’', "'")
        
        # Exact match or normalized match
        if spell_name_lower in allowed_names:
            kept_count += 1
            # print(f"Keeping: {spell.name}")
        else:
            # Check for close matches or issues
            # print(f"Deleting disallowed spell: {spell.name}")
            spell.delete()
            deleted_count += 1

    print(f"\nCleanup Complete.")
    print(f"Kept: {kept_count}")
    print(f"Deleted: {deleted_count}")

    # Verify specific removals mentioned by user
    print("\nVerifying specific removals:")
    for bad in ["Blade Ward", "Thorn Whip", "Ice Knife", "Summon Dragon"]:
        if Spell.objects.filter(name__iexact=bad).exists():
             print(f"WARNING: {bad} still exists!")
        else:
             print(f"Confirmed removed: {bad}")

if __name__ == "__main__":
    cleanup_srd_spells()
