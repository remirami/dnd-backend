from django.db import migrations

def sync_weapon_booleans(apps, schema_editor):
    Weapon = apps.get_model('items', 'Weapon')
    for weapon in Weapon.objects.all():
        properties = [p.name for p in weapon.properties.all()]
        weapon.two_handed = 'Two-Handed' in properties
        weapon.light = 'Light' in properties
        weapon.heavy = 'Heavy' in properties
        weapon.finesse = 'Finesse' in properties
        weapon.thrown = 'Thrown' in properties
        weapon.ammunition = 'Ammunition' in properties
        weapon.loading = 'Loading' in properties
        weapon.reach = 'Reach' in properties
        weapon.save()

def reverse_sync(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('items', '0002_weapon_mastery_property'),
    ]

    operations = [
        migrations.RunPython(sync_weapon_booleans, reverse_sync),
    ]
