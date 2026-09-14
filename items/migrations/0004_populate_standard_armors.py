from django.db import migrations


def populate_standard_armors(apps, schema_editor):
    ItemCategory = apps.get_model('items', 'ItemCategory')
    Armor = apps.get_model('items', 'Armor')

    armor_cat, _ = ItemCategory.objects.get_or_create(
        name='Armor',
        defaults={'description': 'Protective equipment and shields'}
    )

    armors = [
        {
            'name': 'Padded Armor',
            'armor_type': 'light',
            'base_ac': 11,
            'max_dex_bonus': None,
            'min_strength': 0,
            'stealth_disadvantage': True,
            'weight': 8.0,
            'value': 5,
            'description': 'Padded armor consists of quilted layers of cloth and batting. Base AC 11.'
        },
        {
            'name': 'Leather Armor',
            'armor_type': 'light',
            'base_ac': 11,
            'max_dex_bonus': None,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 10.0,
            'value': 10,
            'description': 'The breastplate and shoulder protectors of this armor are made of leather. Base AC 11.'
        },
        {
            'name': 'Studded Leather',
            'armor_type': 'light',
            'base_ac': 12,
            'max_dex_bonus': None,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 13.0,
            'value': 45,
            'description': 'Supple leather reinforced with close-set metal rivets or spikes. AC 12 + DEX mod.'
        },
        {
            'name': 'Hide Armor',
            'armor_type': 'medium',
            'base_ac': 12,
            'max_dex_bonus': 2,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 12.0,
            'value': 10,
            'description': 'Crude medium armor made from thick furs and pelts. AC 12 + DEX mod (max 2).'
        },
        {
            'name': 'Chain Shirt',
            'armor_type': 'medium',
            'base_ac': 13,
            'max_dex_bonus': 2,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 20.0,
            'value': 50,
            'description': 'Made of interlocking metal rings worn between layers of clothing. AC 13 + DEX mod (max 2).'
        },
        {
            'name': 'Scale Mail',
            'armor_type': 'medium',
            'base_ac': 14,
            'max_dex_bonus': 2,
            'min_strength': 0,
            'stealth_disadvantage': True,
            'weight': 45.0,
            'value': 50,
            'description': 'Medium armor made of overlapping steel pieces resembling scales. AC 14 + DEX mod (max 2).'
        },
        {
            'name': 'Breastplate',
            'armor_type': 'medium',
            'base_ac': 14,
            'max_dex_bonus': 2,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 20.0,
            'value': 400,
            'description': 'Fitted metal chest piece worn with supple leather. AC 14 + DEX mod (max 2).'
        },
        {
            'name': 'Half Plate',
            'armor_type': 'medium',
            'base_ac': 15,
            'max_dex_bonus': 2,
            'min_strength': 0,
            'stealth_disadvantage': True,
            'weight': 40.0,
            'value': 750,
            'description': 'Shaped metal plates covering most of the body. AC 15 + DEX mod (max 2).'
        },
        {
            'name': 'Ring Mail',
            'armor_type': 'heavy',
            'base_ac': 14,
            'max_dex_bonus': 0,
            'min_strength': 0,
            'stealth_disadvantage': True,
            'weight': 40.0,
            'value': 30,
            'description': 'Heavy leather armor with sturdy metal rings sewn into it. AC 14.'
        },
        {
            'name': 'Chain Mail',
            'armor_type': 'heavy',
            'base_ac': 16,
            'max_dex_bonus': 0,
            'min_strength': 13,
            'stealth_disadvantage': True,
            'weight': 55.0,
            'value': 75,
            'description': 'Heavy armor made of interlocking metal rings. Provides solid protection with base AC 16.'
        },
        {
            'name': 'Splint Armor',
            'armor_type': 'heavy',
            'base_ac': 17,
            'max_dex_bonus': 0,
            'min_strength': 15,
            'stealth_disadvantage': True,
            'weight': 60.0,
            'value': 200,
            'description': 'Vertical strips of metal riveted to leather backing. AC 17.'
        },
        {
            'name': 'Plate Armor',
            'armor_type': 'heavy',
            'base_ac': 18,
            'max_dex_bonus': 0,
            'min_strength': 15,
            'stealth_disadvantage': True,
            'weight': 65.0,
            'value': 1500,
            'description': 'Shaped, interlocking metal plates covering entire body. AC 18.'
        },
        {
            'name': 'Shield',
            'armor_type': 'shield',
            'base_ac': 2,
            'max_dex_bonus': None,
            'min_strength': 0,
            'stealth_disadvantage': False,
            'weight': 6.0,
            'value': 10,
            'description': 'A shield made of wood or metal carried in one hand. Adds +2 to AC.'
        },
    ]

    for armor_spec in armors:
        name = armor_spec.pop('name')
        Armor.objects.get_or_create(
            name=name,
            defaults={
                **armor_spec,
                'category': armor_cat,
                'rarity': 'common',
                'is_magical': False,
                'requires_attunement': False
            }
        )


def reverse_populate(apps, schema_editor):
    Armor = apps.get_model('items', 'Armor')
    Armor.objects.filter(name__in=[
        'Padded Armor', 'Leather Armor', 'Studded Leather',
        'Hide Armor', 'Chain Shirt', 'Scale Mail', 'Breastplate', 'Half Plate',
        'Ring Mail', 'Chain Mail', 'Splint Armor', 'Plate Armor', 'Shield'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0003_sync_weapon_boolean_properties'),
    ]

    operations = [
        migrations.RunPython(populate_standard_armors, reverse_populate),
    ]
