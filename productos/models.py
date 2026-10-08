import os
from django.conf import settings
from django.db import models
from core.models import Almacen


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'categorias'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'subcategorias'
        unique_together = ('categoria', 'nombre')
        ordering = ['nombre']

    def __str__(self):
        return f'{self.categoria} / {self.nombre}'


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'marcas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Etiqueta(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'etiquetas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('incompleto', 'Incompleto'),
    ]

    # Columnas exactas del SQL
    codigo = models.CharField(max_length=20, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.SET_NULL, null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    aliases = models.TextField(blank=True, null=True)
    tiene_fecha_vencimiento = models.BooleanField(default=False)
    dias_alerta_vencimiento = models.IntegerField(default=30)
    es_transformado = models.BooleanField(default=False)
    movimiento_lento = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='incompleto')
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'productos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            ultimo = Producto.objects.order_by('-id').first()
            siguiente = (ultimo.id + 1) if ultimo else 1
            self.codigo = f'PRO-{siguiente:08d}'
        super().save(*args, **kwargs)
        carpeta = os.path.join(settings.MEDIA_ROOT, 'dataset_entrenamiento', self.codigo)
        os.makedirs(carpeta, exist_ok=True)

    @property
    def foto_principal(self):
        return self.fotos.filter(es_principal=True).first()

    @property
    def alias_lista(self):
        if not self.aliases:
            return []
        return [a.strip() for a in self.aliases.split(',') if a.strip()]

    @property
    def inventarios_resumen(self):
        return Inventario.objects.filter(
            presentacion__producto=self
        ).select_related('presentacion').order_by('presentacion__unidades_base')


class ProductoFoto(models.Model):
    # El SQL guarda URL (string), no archivo subido
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='fotos')
    url = models.CharField(max_length=255)
    es_principal = models.BooleanField(default=False)
    orden = models.IntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'producto_fotos'
        ordering = ['-es_principal', 'orden']

    def save(self, *args, **kwargs):
        if self.es_principal:
            ProductoFoto.objects.filter(producto=self.producto, es_principal=True).exclude(pk=self.pk).update(es_principal=False)
        super().save(*args, **kwargs)


class ProductoCampo(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='campos')
    nombre = models.CharField(max_length=100, db_column='clave')
    valor = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'producto_campos'


class ProductoEtiqueta(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    etiqueta = models.ForeignKey(Etiqueta, on_delete=models.CASCADE)

    class Meta:
        db_table = 'producto_etiquetas'
        unique_together = ('producto', 'etiqueta')


class ProductoPrecio(models.Model):
    """Presentación del producto: Unidad, Docena, Caja x5 doc, etc."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='presentaciones')
    tipo_venta = models.CharField(max_length=100)       # Ej: Unidad, Docena, Caja x5 doc
    unidades_base = models.IntegerField()               # cuántas unidades base equivale
    precio_minorista = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_mayorista = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    permite_fraccion = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'producto_precios'
        ordering = ['unidades_base']

    def __str__(self):
        return f'{self.producto.nombre} — {self.tipo_venta}'


class PrecioFraccion(models.Model):
    # El SQL no guarda precio en la fracción, solo define cuántas unidades base
    presentacion = models.ForeignKey(
        ProductoPrecio, on_delete=models.CASCADE,
        related_name='fracciones', db_column='producto_precio_id'
    )
    nombre = models.CharField(max_length=20)            # 'mitad', 'cuarto'
    unidades_base = models.IntegerField()               # unidades reales (ej: 6 para media docena de 12)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'producto_precio_fracciones'


class Proveedor(models.Model):
    # El SQL usa razon_social, no nombre
    nombre = models.CharField(max_length=200, db_column='razon_social')
    ruc = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    numero_cuenta = models.CharField(max_length=150, blank=True, null=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)
    numero_contacto = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ProductoProveedor(models.Model):
    """Historial de costos por presentación y proveedor. Nunca se sobreescribe."""
    presentacion = models.ForeignKey(
        ProductoPrecio, on_delete=models.CASCADE,
        related_name='costos_proveedor', db_column='producto_precio_id'
    )
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='productos', null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    costo_con_flete = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'producto_proveedor'


class Inventario(models.Model):
    """Stock por presentación y almacén, en unidades base."""
    # El SQL vincula a producto_precios, no a productos directamente
    presentacion = models.ForeignKey(
        ProductoPrecio, on_delete=models.CASCADE,
        related_name='inventarios', db_column='producto_precio_id'
    )
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE, related_name='inventarios')
    stock_actual = models.IntegerField(default=0, help_text='En unidades base')
    stock_minimo = models.IntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventario'
        unique_together = ('presentacion', 'almacen')

    def __str__(self):
        return f'{self.presentacion} | {self.almacen}: {self.stock_actual}'

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return 'SIN STOCK'
        if self.stock_actual <= self.stock_minimo:
            return 'ALERTA'
        return 'OK'

    @property
    def producto(self):
        return self.presentacion.producto


class Kardex(models.Model):
    # El SQL usa cantidad_entrada/salida separadas, y tipo_movimiento
    presentacion = models.ForeignKey(
        ProductoPrecio, on_delete=models.CASCADE,
        related_name='kardex', db_column='producto_precio_id'
    )
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    tipo_movimiento = models.CharField(max_length=50)
    referencia_tipo = models.CharField(max_length=50, blank=True, null=True)
    referencia_id = models.IntegerField(null=True, blank=True)
    cantidad_entrada = models.IntegerField(default=0)
    cantidad_salida = models.IntegerField(default=0)
    stock_resultante = models.IntegerField(null=True, blank=True)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='usuario_id'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kardex'
        ordering = ['-fecha']
