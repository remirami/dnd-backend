# Generated manually to fix weapon ranges, thrown property, and weapon types

from django.db import migrations


def fix_weapon_ranges_and_types(apps, schema_editor):
    Weapon = apps.get_model('items', 'Weapon')

    TYPE_MAP = {
        'simple melee weapons': 'simple_melee',
        'simple ranged weapons': 'simple_ranged',
        'martial melee weapons': 'martial_melee',
        'martial ranged weapons': 'martial_ranged',
        'simple melee': 'simple_melee',
        'simple ranged': 'simple_ranged',
        'martial melee': 'martial_melee',
        'martial ranged': 'martial_ranged',
    }

    for w in Weapon.objects.all():
        cur = (w.weapon_type or '').strip().lower()
        if cur in TYPE_MAP:
            w.weapon_type = TYPE_MAP[cur]
            w.save(update_fields=['weapon_type'])

    WEAPON_UPDATES = {
        'Javelin': {'weapon_type': 'simple_melee', 'thrown': True, 'range_normal': 30, 'range_long': 120},
        'Shortbow': {'weapon_type': 'simple_ranged', 'ammunition': True, 'two_handed': True, 'range_normal': 80, 'range_long': 320},
        'Dart': {'weapon_type': 'simple_ranged', 'finesse': True, 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Dagger': {'weapon_type': 'simple_melee', 'finesse': True, 'light': True, 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Handaxe': {'weapon_type': 'simple_melee', 'light': True, 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Light hammer': {'weapon_type': 'simple_melee', 'light': True, 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Spear': {'weapon_type': 'simple_melee', 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Trident': {'weapon_type': 'martial_melee', 'thrown': True, 'range_normal': 20, 'range_long': 60},
        'Crossbow, light': {'weapon_type': 'simple_ranged', 'ammunition': True, 'loading': True, 'two_handed': True, 'range_normal': 80, 'range_long': 320},
        'Crossbow, heavy': {'weapon_type': 'martial_ranged', 'ammunition': True, 'heavy': True, 'loading': True, 'two_handed': True, 'range_normal': 100, 'range_long': 400},
        'Crossbow, hand': {'weapon_type': 'martial_ranged', 'ammunition': True, 'light': True, 'loading': True, 'range_normal': 30, 'range_long': 120},
        'Longbow': {'weapon_type': 'martial_ranged', 'ammunition': True, 'heavy': True, 'two_handed': True, 'range_normal': 150, 'range_long': 600},
        'Sling': {'weapon_type': 'simple_ranged', 'ammunition': True, 'range_normal': 30, 'range_long': 120},
        'Blowgun': {'weapon_type': 'martial_ranged', 'ammunition': True, 'loading': True, 'range_normal': 25, 'range_long': 100},
        'Net': {'weapon_type': 'martial_ranged', 'thrown': True, 'range_normal': 5, 'range_long': 15},
    }

    for name, fields in WEAPON_UPDATES.items():
        for w in Weapon.objects.filter(name__iexact=name):
            for k, v in fields.items():
                setattr(w, k, v)
            w.save(update_fields=list(fields.keys()))


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0005_alter_weapon_weapon_type'),
    ]

    operations = [
        migrations.RunPython(fix_weapon_ranges_and_types, reverse_code=migrations.RunPython.noop),
    ]
