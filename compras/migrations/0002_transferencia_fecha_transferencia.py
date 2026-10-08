from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferencia',
            name='fecha_transferencia',
            field=models.DateField(null=True, blank=True),
        ),
    ]
