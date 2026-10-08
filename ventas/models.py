from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.db import transaction

from core.models import Almacen
from clientes.models import Cliente
from productos.models import ProductoPrecio, Inventario, Kardex


class Venta(models.Model):
    TIPO_CHOICES = [
        ('nota', 'Nota de Pedido'),
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
    ]
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('anulada', 'Anulada'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='nota')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='borrador')
    fecha = models.DateField()
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, blank=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    observaciones = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    confirmado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ventas'
        ordering = ['-creado_en']

    def __str__(self):
        return self.numero

    def get_cliente_display(self):
        if self.cliente:
            return self.cliente.nombre
        return self.cliente_nombre or 'Clientes Varios'

    def save(self, *args, **kwargs):
        if not self.numero:
            prefijos = {'nota': 'NP', 'boleta': 'BV', 'factura': 'FV'}
            prefijo = prefijos.get(self.tipo, 'VT')
            ultimo = Venta.objects.filter(tipo=self.tipo).count() + 1
            self.numero = f'{prefijo}-{ultimo:08d}'
        super().save(*args, **kwargs)

    @transaction.atomic
    def confirmar(self):
        if self.estado != 'borrador':
            raise ValueError('Solo se pueden confirmar ventas en borrador.')
        for item in self.items.select_related('presentacion__producto'):
            unidades = item.cantidad * item.presentacion.unidades_base

            # Buscar stock total del producto en el almacen (cualquier presentacion)
            invs = Inventario.objects.filter(
                presentacion__producto=item.presentacion.producto,
                almacen=self.almacen,
                stock_actual__gt=0
            ).order_by('-stock_actual')
            total_disponible = sum(i.stock_actual for i in invs)

            if total_disponible < unidades:
                raise ValueError(
                    f'Stock insuficiente para {item.presentacion.producto.nombre} '
                    f'({item.presentacion.tipo_venta}). Disponible: {total_disponible} unidades'
                )

            # Descontar de los registros disponibles
            restante = unidades
            for inv in invs:
                if restante <= 0:
                    break
                deducir = min(inv.stock_actual, restante)
                inv.stock_actual -= deducir
                inv.save()
                restante -= deducir

            stock_final = total_disponible - unidades
            Kardex.objects.create(
                presentacion=item.presentacion,
                almacen=self.almacen,
                tipo_movimiento='venta',
                cantidad_salida=unidades,
                stock_resultante=stock_final,
                referencia_tipo='venta',
                referencia_id=self.id,
            )

        from django.utils import timezone
        self.estado = 'confirmada'
        self.confirmado_en = timezone.now()
        self.save()


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    presentacion = models.ForeignKey(ProductoPrecio, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'venta_items'

    @property
    def subtotal(self):
        return Decimal(str(self.cantidad)) * self.precio_unitario
