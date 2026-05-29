from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0031_remove_character_builder_session'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characteritem',
            name='equipment_slot',
            field=models.CharField(
                choices=[
                    ('main_hand', 'Main Hand'),
                    ('off_hand', 'Off Hand'),
                    ('armor', 'Armor'),
                    ('shield', 'Shield'),
                    ('ring', 'Ring'),
                    ('ring_2', 'Ring 2'),
                    ('amulet', 'Amulet'),
                    ('boots', 'Boots'),
                    ('gloves', 'Gloves'),
                    ('helmet', 'Helmet'),
                    ('cloak', 'Cloak'),
                    ('inventory', 'Inventory'),
                ],
                default='inventory',
                max_length=20,
            ),
        ),
    ]
