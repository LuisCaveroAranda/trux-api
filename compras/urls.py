from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    path('', views.lista_compras, name='lista'),
    path('nueva/', views.crear_compra, name='crear'),
    path('<int:pk>/', views.detalle_compra, name='detalle'),
    path('<int:pk>/editar/', views.editar_compra, name='editar'),
    path('<int:pk>/confirmar/', views.confirmar_compra, name='confirmar'),
    path('<int:pk>/anular/', views.anular_compra, name='anular'),
    path('stock-inicial/', views.stock_inicial, name='stock_inicial'),
    path('buscar-producto/', views.buscar_producto_ajax, name='buscar_producto'),
    path('presentaciones/', views.presentaciones_ajax, name='presentaciones_ajax'),
    path('ajax/productos-almacen/', views.productos_por_almacen_ajax, name='productos_por_almacen'),
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),
    path('transferencias/nueva/', views.crear_transferencia, name='crear_transferencia'),
    path('transferencias/<int:pk>/', views.detalle_transferencia, name='detalle_transferencia'),
    path('transferencias/<int:pk>/editar/', views.editar_transferencia, name='editar_transferencia'),
    path('transferencias/<int:pk>/confirmar/', views.confirmar_transferencia, name='confirmar_transferencia'),
    path('transferencias/<int:pk>/anular/', views.anular_transferencia, name='anular_transferencia'),
]
