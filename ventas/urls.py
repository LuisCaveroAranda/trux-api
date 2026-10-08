from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista'),
    path('nueva/', views.crear_venta, name='crear'),
    path('<int:pk>/', views.detalle_venta, name='detalle'),
    path('<int:pk>/editar/', views.editar_venta, name='editar'),
    path('<int:pk>/confirmar/', views.confirmar_venta, name='confirmar'),
    path('<int:pk>/anular/', views.anular_venta, name='anular'),
]
