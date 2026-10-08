from django.contrib import admin
from .models import (
    Categoria, Subcategoria, Marca, Etiqueta,
    Producto, ProductoFoto, ProductoCampo, ProductoEtiqueta,
    ProductoPrecio, PrecioFraccion,
    Proveedor, ProductoProveedor,
    Inventario, Kardex,
)


class SubcategoriaInline(admin.TabularInline):
    model = Subcategoria
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    inlines = [SubcategoriaInline]


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)


@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)


class ProductoFotoInline(admin.TabularInline):
    model = ProductoFoto
    extra = 1
    max_num = 4


class ProductoCampoInline(admin.TabularInline):
    model = ProductoCampo
    extra = 1


class ProductoPrecioInline(admin.TabularInline):
    model = ProductoPrecio
    extra = 1
    show_change_link = True


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'marca', 'estado')
    list_filter = ('estado', 'categoria', 'marca')
    search_fields = ('codigo', 'nombre', 'aliases')
    readonly_fields = ('codigo', 'creado_en', 'actualizado_en')
    inlines = [ProductoFotoInline, ProductoCampoInline, ProductoPrecioInline]
    fieldsets = (
        (None, {'fields': ('codigo', 'nombre', 'estado')}),
        ('Clasificación', {'fields': ('categoria', 'subcategoria', 'marca')}),
        ('Configuración', {'fields': ('aliases', 'tiene_fecha_vencimiento', 'es_transformado', 'movimiento_lento')}),
        ('Fechas', {'fields': ('creado_en', 'actualizado_en'), 'classes': ('collapse',)}),
    )


class PrecioFraccionInline(admin.TabularInline):
    model = PrecioFraccion
    extra = 0


@admin.register(ProductoPrecio)
class ProductoPrecioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo_venta', 'unidades_base', 'precio_minorista', 'precio_mayorista', 'activo')
    list_filter = ('activo', 'permite_fraccion')
    search_fields = ('producto__nombre', 'tipo_venta')
    inlines = [PrecioFraccionInline]


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc', 'telefono', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'ruc')


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('presentacion', 'almacen', 'stock_actual', 'stock_minimo', 'estado_stock')
    list_filter = ('almacen',)
    search_fields = ('presentacion__producto__nombre',)

    def estado_stock(self, obj):
        return obj.estado_stock
    estado_stock.short_description = 'Estado'


@admin.register(Kardex)
class KardexAdmin(admin.ModelAdmin):
    list_display = ('presentacion', 'almacen', 'tipo_movimiento', 'cantidad_entrada', 'cantidad_salida', 'stock_resultante', 'fecha')
    list_filter = ('tipo_movimiento', 'almacen')
    readonly_fields = ('fecha',)
