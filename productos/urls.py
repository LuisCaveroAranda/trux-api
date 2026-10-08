from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.lista_productos, name='lista'),
    path('nuevo/', views.crear_producto, name='crear'),
    path('<int:pk>/', views.detalle_producto, name='detalle'),
    path('<int:pk>/editar/', views.editar_producto, name='editar'),
    path('<int:pk>/subir-foto/', views.subir_foto, name='subir_foto'),
    path('foto/<int:foto_id>/eliminar/', views.eliminar_foto, name='eliminar_foto'),
    path('inventario/', views.inventario, name='inventario'),
]
