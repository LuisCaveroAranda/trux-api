import math
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User
from core.models import Almacen
from productos.models import Producto, Proveedor, ProductoPrecio, Inventario, Kardex


class HistorialCosto(models.Model):
    presentacion = models.ForeignKey(
        ProductoPrecio, on_delete=models.CASCADE,
        related_name='historial_costos', db_column='producto_precio_id'
    )
    compra = models.ForeignKey('Compra', on_delete=models.SET_NULL, null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    costo_con_flete = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_costos'
        ordering = ['-fecha']


class Compra(models.Model):
    TIPO_CHOICES = [
        ('con_documento', 'Con Documento'),
        ('sin_documento', 'Sin Documento'),
        ('mercado', 'Mercado'),
    ]
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('anulada', 'Anulada'),
    ]

    # Mapeo exacto a columnas del SQL
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, db_column='tipo_compra')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, null=True, blank=True)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, db_column='usuario_id')
    numero_documento = models.CharField(max_length=50, blank=True, null=True, db_column='num_documento')
    fecha = models.DateField(null=True, blank=True, db_column='fecha_documento')
    flete_proveedor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_por_bulto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    flete_agencia_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pagado_caja = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='pagado_caja')
    pagado_adelanto = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='pagado_adelanto_dueno')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'compras'
        ordering = ['-creado_en']

    def __str__(self):
        return f'Compra #{self.id} — {self.proveedor or "Sin proveedor"}'

    @property
    def numero(self):
        return f'GC-{self.id:08d}'

    @property
    def subtotal_mercaderia(self):
        return sum(item.subtotal_calc for item in self.items.all())

    @property
    def flete_agencia_calculado(self):
        return sum(item.flete_agencia_calc for item in self.items.all())

    @property
    def total_calculado(self):
        return self.subtotal_mercaderia + self.flete_proveedor + self.flete_agencia_calculado

    def get_estado_display_custom(self):
        return dict(self.ESTADO_CHOICES).get(self.estado, self.estado)

    def confirmar(self):
        with transaction.atomic():
            subtotal = Decimal('0')
            flete_ag = Decimal('0')
            for item in self.items.select_related('presentacion').all():
                subtotal += item.subtotal_calc
                flete_ag += item.flete_agencia_proporcional

                # Actualizar inventario en unidades base
                inv, _ = Inventario.objects.get_or_create(
                    presentacion=item.presentacion,
                    almacen=self.almacen,
                    defaults={'stock_actual': 0}
                )
                inv.stock_actual += item.cantidad * item.presentacion.unidades_base
                inv.save()

                # Calcular costo con flete por unidad base y propagar a todas las presentaciones
                from productos.models import ProductoProveedor, ProductoPrecio
                unidades_compradas = item.cantidad * item.presentacion.unidades_base
                costo_unit_base = (item.subtotal_calc + item.flete_agencia_proporcional + item.flete_proveedor_proporcional) / Decimal(str(unidades_compradas))

                for pres in ProductoPrecio.objects.filter(producto=item.presentacion.producto):
                    costo_pres = (costo_unit_base * Decimal(str(pres.unidades_base))).quantize(Decimal('0.0001'))
                    costo_base = item.costo_unitario * Decimal(str(pres.unidades_base)) / Decimal(str(item.presentacion.unidades_base))

                    # Actualizar si ya existe para este proveedor, sino crear (acepta proveedor nulo)
                    pp_qs = ProductoProveedor.objects.filter(presentacion=pres, proveedor=self.proveedor)
                    if pp_qs.exists():
                        pp_qs.update(costo=costo_base, costo_con_flete=costo_pres)
                    else:
                        ProductoProveedor.objects.create(
                            presentacion=pres,
                            proveedor=self.proveedor,
                            costo=costo_base,
                            costo_con_flete=costo_pres,
                        )

                    # Registrar en historial de costos
                    HistorialCosto.objects.create(
                        presentacion=pres,
                        compra=self,
                        proveedor=self.proveedor,
                        costo=costo_base,
                        costo_con_flete=costo_pres,
                    )

                # Registrar en kardex
                Kardex.objects.create(
                    presentacion=item.presentacion,
                    almacen=self.almacen,
                    tipo_movimiento='compra',
                    cantidad_entrada=item.cantidad * item.presentacion.unidades_base,
                    stock_resultante=inv.stock_actual,
                    costo_unitario=item.costo_unitario,
                    referencia_id=self.id,
                    referencia_tipo='compra',
                )

            self.subtotal = subtotal
            self.flete_agencia_total = flete_ag
            self.total = subtotal + self.flete_proveedor + flete_ag
            self.estado = 'confirmada'
            self.save()


class CompraItem(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='items')
    presentacion = models.ForeignKey(ProductoPrecio, on_delete=models.PROTECT, null=True, blank=True, db_column='producto_precio_id')

    @property
    def producto(self):
        return self.presentacion.producto if self.presentacion else None
    cantidad = models.IntegerField()
    cajas_por_bulto = models.IntegerField(default=1)
    num_bultos = models.IntegerField(null=True, blank=True)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    flete_proveedor_proporcional = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_por_bulto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grupo_bulto = models.CharField(max_length=5, blank=True, null=True)
    costo_directo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'compra_items'

    @property
    def subtotal_calc(self):
        return Decimal(str(self.cantidad)) * self.costo_unitario

    @property
    def flete_agencia_proporcional(self):
        if self.grupo_bulto:
            grupo_count = self.compra.items.filter(grupo_bulto=self.grupo_bulto).count()
            return self.precio_por_bulto / Decimal(str(grupo_count)) if grupo_count > 0 else Decimal('0')
        return Decimal(str(self.num_bultos or 1)) * self.precio_por_bulto


class Transferencia(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('anulada', 'Anulada'),
    ]
    almacen_origen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name='transferencias_salida', db_column='almacen_origen_id')
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name='transferencias_entrada', db_column='almacen_destino_id')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, db_column='usuario_id')
    motivo = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_transferencia = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'transferencias'
        ordering = ['-fecha']

    def __str__(self):
        return f'Transferencia #{self.id} {self.almacen_origen} → {self.almacen_destino}'

    @property
    def numero(self):
        return f'TR-{self.id:08d}'

    def confirmar(self):
        with transaction.atomic():
            for item in self.items.select_related('presentacion').all():
                # Restar del origen
                inv_origen = Inventario.objects.filter(
                    presentacion=item.presentacion, almacen=self.almacen_origen
                ).first()
                if not inv_origen or inv_origen.stock_actual < item.cantidad_unidades_base:
                    raise ValueError(f'Stock insuficiente en origen para {item.presentacion}')
                inv_origen.stock_actual -= item.cantidad_unidades_base
                inv_origen.save()

                # Sumar al destino
                inv_destino, _ = Inventario.objects.get_or_create(
                    presentacion=item.presentacion,
                    almacen=self.almacen_destino,
                    defaults={'stock_actual': 0}
                )
                inv_destino.stock_actual += item.cantidad_unidades_base
                inv_destino.save()

                # Kardex salida
                Kardex.objects.create(
                    presentacion=item.presentacion,
                    almacen=self.almacen_origen,
                    tipo_movimiento='transferencia_salida',
                    cantidad_salida=item.cantidad_unidades_base,
                    stock_resultante=inv_origen.stock_actual,
                    referencia_id=self.id,
                    referencia_tipo='transferencia',
                )
                # Kardex entrada
                Kardex.objects.create(
                    presentacion=item.presentacion,
                    almacen=self.almacen_destino,
                    tipo_movimiento='transferencia_entrada',
                    cantidad_entrada=item.cantidad_unidades_base,
                    stock_resultante=inv_destino.stock_actual,
                    referencia_id=self.id,
                    referencia_tipo='transferencia',
                )

            self.estado = 'confirmada'
            self.save()


class TransferenciaItem(models.Model):
    transferencia = models.ForeignKey(Transferencia, on_delete=models.CASCADE, related_name='items')
    presentacion = models.ForeignKey(ProductoPrecio, on_delete=models.PROTECT, db_column='producto_precio_id')
    cantidad_unidades_base = models.IntegerField()

    class Meta:
        db_table = 'transferencia_items'


class StockInicial(models.Model):
    presentacion = models.ForeignKey(ProductoPrecio, on_delete=models.PROTECT, null=True, blank=True)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.PositiveIntegerField()
    costo_aproximado = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_inicial'

    def aplicar(self):
        with transaction.atomic():
            total_ub = self.cantidad * self.presentacion.unidades_base
            inv, _ = Inventario.objects.get_or_create(
                presentacion=self.presentacion,
                almacen=self.almacen,
                defaults={'stock_actual': 0}
            )
            inv.stock_actual += total_ub
            inv.save()
            Kardex.objects.create(
                presentacion=self.presentacion,
                almacen=self.almacen,
                tipo_movimiento='stock_inicial',
                cantidad_entrada=total_ub,
                stock_resultante=inv.stock_actual,
                costo_unitario=self.costo_aproximado,
                referencia_id=self.id,
                referencia_tipo='stock_inicial',
            )
