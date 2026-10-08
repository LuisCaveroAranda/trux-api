import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clientes', '0001_initial'),
        ('core', '0001_initial'),
        ('productos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Venta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(blank=True, max_length=20, unique=True)),
                ('tipo', models.CharField(choices=[('nota', 'Nota de Pedido'), ('boleta', 'Boleta'), ('factura', 'Factura')], default='nota', max_length=10)),
                ('estado', models.CharField(choices=[('borrador', 'Borrador'), ('confirmada', 'Confirmada'), ('anulada', 'Anulada')], default='borrador', max_length=15)),
                ('fecha', models.DateField()),
                ('cliente_nombre', models.CharField(blank=True, max_length=200)),
                ('observaciones', models.TextField(blank=True)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('igv', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('confirmado_en', models.DateTimeField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('almacen', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.almacen')),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='clientes.cliente')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'ventas', 'ordering': ['-creado_en']},
        ),
        migrations.CreateModel(
            name='VentaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.IntegerField()),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('presentacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='productos.productoprecio')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='ventas.venta')),
            ],
            options={'db_table': 'venta_items'},
        ),
    ]
