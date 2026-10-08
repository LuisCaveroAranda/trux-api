from django.contrib import admin
from .models import Compra, CompraItem, StockInicial


class CompraItemInline(admin.TabularInline):
    model = CompraItem
    extra = 1
    readonly_fields = ('num_bultos', 'flete_agencia_proporcional', 'flete_proveedor_proporcional', 'costo_directo', 'subtotal')


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'proveedor', 'almacen', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'tipo', 'almacen')
    search_fields = ('proveedor__nombre',)
    readonly_fields = ('creado_en', 'actualizado_en')
    inlines = [CompraItemInline]

    def numero(self, obj):
        return obj.numero
    numero.short_description = 'Número'

    def total(self, obj):
        return f'S/ {obj.total:.2f}'
    total.short_description = 'Total'


@admin.register(StockInicial)
class StockInicialAdmin(admin.ModelAdmin):
    list_display = ('presentacion', 'almacen', 'cantidad', 'costo_aproximado', 'fecha')
    list_filter = ('almacen',)
    readonly_fields = ('creado_en',)
