from django.db import migrations


def update_and_seed_epic_boons(apps, schema_editor):
    Feat = apps.get_model('characters', 'Feat')
    Character = apps.get_model('characters', 'Character')
    CharacterFeat = apps.get_model('characters', 'CharacterFeat')

    epic_boons = [
        # SRD 5.2 / 2024 Epic Boons
        {
            "name": "Boon of Combat Prowess",
            "description": "When you miss with a melee weapon attack, you can choose to hit instead. Once you use this boon, you can't use it again until you finish a short rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Dimensional Travel",
            "description": "As an action, you can cast the Misty Step spell, without using a spell slot or any components. You can use this boon once per short rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Energy Resistance",
            "description": "You gain resistance to one type of damage of your choice: acid, cold, fire, lightning, necrotic, poison, psychic, radiant, or thunder. You can change this choice whenever you finish a short rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Fate",
            "description": "When another creature that you can see within 60 feet of you makes an ability check, an attack roll, or a saving throw, you can roll a d10 and apply the result as a bonus or penalty to the roll. Once you use this boon, you can't use it again until you finish a short rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Fortitude",
            "description": "Your hit point maximum increases by 40.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Irresistible Offense",
            "description": "You can bypass the damage resistances of any creature.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Recovery",
            "description": "You can use a bonus action to regain a number of hit points equal to half your hit point maximum. Once you use this boon, you can't use it again until you finish a long rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Speed",
            "description": "Your walking speed increases by 30 feet. In addition, you can use a bonus action to take the Dash or Disengage action.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Spell Recall",
            "description": "You can cast any spell you know or have prepared without expending a spell slot. Once you use this boon, you can't use it again until you finish a long rest.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of the Night Spirit",
            "description": "While you are in dim light or darkness, you can become invisible as an action. You remain invisible until you make an attack, cast a spell, or are in bright light.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Truesight",
            "description": "You have truesight out to a range of 60 feet.",
            "source": "SRD 5.2"
        },
        {
            "name": "Boon of Undetectability",
            "description": "You gain a +10 bonus to Dexterity (Stealth) checks, and you can't be detected by magical sensors.",
            "source": "SRD 5.2"
        },
        # Classic DMG Epic Boons
        {
            "name": "Boon of High Magic",
            "description": "You gain one 9th-level spell slot, provided you already have one.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Immortality",
            "description": "You stop aging. You are immune to any effect that would age you, and you can't die from old age.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Invulnerability",
            "description": "You have immunity to damage from nonmagical slashing, piercing, and bludgeoning attacks.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Luck",
            "description": "You can add a d10 roll to any ability check, attack roll, or saving throw you make. Once used, you can't use it again until you finish a short rest.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Magic Resistance",
            "description": "You have advantage on saving throws against spells and other magical effects.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Peerless Aim",
            "description": "You can give yourself a +20 bonus to a ranged attack roll you make. Once used, you can't use it again until you finish a short rest.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Perfect Health",
            "description": "You are immune to all diseases and poisons, and you have advantage on Constitution saving throws.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Planar Travel",
            "description": "You can cast the Plane Shift spell (targeting yourself and up to seven willing creatures) without expending a spell slot or material components. Once used, you can't use it again until you finish a short or long rest.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Quick Casting",
            "description": "Choose one of your spells of 1st through 3rd level that has a casting time of 1 action. That spell now has a casting time of 1 bonus action for you.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Resilience",
            "description": "You have resistance to bludgeoning, piercing, and slashing damage from nonmagical attacks.",
            "source": "Dungeon Master's Guide"
        },
        {
            "name": "Boon of Unmatched Skill",
            "description": "When you make an ability check, you can give yourself a +20 bonus to the check. Once used, you can't use it again until you finish a short rest.",
            "source": "Dungeon Master's Guide"
        }
    ]

    for boon in epic_boons:
        Feat.objects.update_or_create(
            name=boon['name'],
            defaults={
                'description': boon['description'],
                'minimum_level': 20,
                'category': 'epic_boon',
                'source': boon['source'],
                'strength_requirement': 0,
                'dexterity_requirement': 0,
                'constitution_requirement': 0,
                'intelligence_requirement': 0,
                'wisdom_requirement': 0,
                'charisma_requirement': 0,
            }
        )

    # Ensure all feats starting with 'Boon of' or category 'epic_boon' have minimum_level=20
    Feat.objects.filter(name__startswith='Boon of').update(minimum_level=20, category='epic_boon')
    Feat.objects.filter(category='epic_boon').update(minimum_level=20)

    # For any characters currently at level >= 20, make sure level 20 is pending if they haven't taken an epic boon / feat
    for char in Character.objects.filter(level__gte=20):
        pending = char.pending_asi_levels or []
        has_lvl20 = CharacterFeat.objects.filter(character=char, level_taken=20).exists()
        has_boon = CharacterFeat.objects.filter(character=char, feat__category='epic_boon').exists()
        if 20 not in pending and not has_lvl20 and not has_boon:
            pending.append(20)
            char.pending_asi_levels = pending
            char.save(update_fields=['pending_asi_levels'])


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0033_characteritem_is_attuned'),
    ]

    operations = [
        migrations.RunPython(update_and_seed_epic_boons, reverse_code=migrations.RunPython.noop),
    ]
