from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('compras/', views.reporte_compras, name='compras'),
    path('ventas/', views.reporte_ventas, name='ventas'),
    path('inventario/', views.reporte_inventario, name='inventario'),
    path('catalogo/', views.catalogo_precios, name='catalogo'),
]
