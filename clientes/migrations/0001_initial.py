from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('documento', models.CharField(blank=True, max_length=20)),
                ('telefono', models.CharField(blank=True, max_length=20)),
                ('direccion', models.CharField(blank=True, max_length=300)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'clientes', 'ordering': ['nombre']},
        ),
    ]
