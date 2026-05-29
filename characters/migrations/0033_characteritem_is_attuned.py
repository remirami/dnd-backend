from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0032_add_ring_2_slot'),
    ]

    operations = [
        migrations.AddField(
            model_name='characteritem',
            name='is_attuned',
            field=models.BooleanField(default=False),
        ),
    ]
