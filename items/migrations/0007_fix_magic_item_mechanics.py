from django.db import migrations
import re


def fix_magic_items_mechanics(apps, schema_editor):
    MagicItem = apps.get_model('items', 'MagicItem')
    Item = apps.get_model('items', 'Item')

    for m in MagicItem.objects.all():
        name = m.name or ''
        desc = m.description or ''
        text = f'{name} {desc}'.lower()

        # Attunement detection
        known_attunement_names = [
            'amulet of health', 'belt of giant strength', 'gauntlets of ogre power', 'headband of intellect',
            'ring of protection', 'cloak of protection', 'bracers of defense', 'belt of dwarvenkind',
            'staff of power', 'defender', 'animated shield', 'spellguard shield', 'arrow-catching shield',
            'armor of invulnerability', 'demon armor', 'bracers of archery', 'boots of speed',
            'cloak of elvenkind', 'boots of elvenkind', 'ring of invisibility', 'ring of regeneration',
            'ring of spell storing', 'ring of the ram', 'robe of the archmagi', 'sun blade', 'vorpal sword',
            'holy avenger', 'luck blade', 'staff of the magi', 'scarab of protection'
        ]
        attune = (
            any(k in name.lower() for k in known_attunement_names)
            or bool(
                re.search(
                    r'requires attunement|attunement required|while you are attuned|when you attune|attuned to this',
                    text,
                )
            )
            or 'attun' in desc.lower()
        )

        # AC Bonus
        bonus_ac = 0
        m_ac = re.search(r'\+(\d+)\s+bonus to (?:your\s+)?(?:armor class|ac)', text)
        if not m_ac:
            m_ac = re.search(r'bonus to (?:your\s+)?(?:armor class|ac)(?: increases by)?\s+\+(\d+)', text)
        if not m_ac:
            m_ac = re.search(r'(?:shield|armor)\s+\+(\d+)', name.lower())
        if m_ac:
            bonus_ac = int(m_ac.group(1))
        elif 'ring of protection' in text or 'cloak of protection' in text:
            bonus_ac = 1
        elif 'bracers of defense' in text:
            bonus_ac = 2

        # Saves Bonus
        bonus_saves = 0
        m_saves = re.search(r'\+(\d+)\s+bonus to (?:all\s+)?saving throws', text)
        if not m_saves:
            m_saves = re.search(r'bonus to (?:all\s+)?saving throws\s+\+(\d+)', text)
        if m_saves:
            bonus_saves = int(m_saves.group(1))
        elif 'ring of protection' in text or 'cloak of protection' in text or 'stone of good luck' in text:
            bonus_saves = 1

        # Attack & Damage Bonus
        bonus_hit = 0
        bonus_dmg = 0
        is_pure_defense = (
            ('shield' in name.lower() and 'striking' not in name.lower())
            or any(k in name.lower() for k in ['armor', 'mail', 'plate', 'cuirass', 'breastplate'])
            or 'ring of protection' in name.lower()
            or 'cloak of protection' in name.lower()
            or 'bracers of defense' in name.lower()
        )

        if not is_pure_defense:
            m_atk_dmg = re.search(r'\+(\d+)\s+bonus to (?:attack and damage rolls|attack rolls and damage rolls)', text)
            if not m_atk_dmg:
                m_atk_dmg = re.search(r'\+(\d+)\s+bonus to attack rolls', text)
            if not m_atk_dmg:
                m_atk_dmg = re.search(
                    r'(?:sword|blade|dagger|bow|axe|spear|mace|hammer|staff|glaive|halberd|scythe|whip|flail|trident|lance|pike|crossbow|dart|sling|rapier|scimitar|greatsword|longsword|shortsword|warhammer|morningstar|weapon)\s+\+(\d+)',
                    name.lower(),
                )
            if m_atk_dmg:
                b = int(m_atk_dmg.group(1))
                bonus_hit = b
                bonus_dmg = b

        # Update fields if changed
        m.bonus_to_ac = bonus_ac
        m.bonus_to_saves = bonus_saves
        m.bonus_to_hit = bonus_hit
        m.bonus_to_damage = bonus_dmg
        m.attunement_required = attune
        m.requires_attunement = attune
        m.save(update_fields=[
            'bonus_to_ac', 'bonus_to_saves', 'bonus_to_hit', 'bonus_to_damage',
            'attunement_required', 'requires_attunement'
        ])


def reverse_magic_items_mechanics(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0006_fix_weapon_ranges_and_types'),
    ]

    operations = [
        migrations.RunPython(fix_magic_items_mechanics, reverse_magic_items_mechanics),
    ]
