from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from reportes import views as reportes_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('productos/', include('productos.urls', namespace='productos')),
    path('compras/', include('compras.urls', namespace='compras')),
    path('ventas/', include('ventas.urls', namespace='ventas')),
    path('reportes/', include('reportes.urls', namespace='reportes')),
    path('almacenes/', core_views.almacenes, name='almacenes'),
    path('almacenes/<int:pk>/toggle/', core_views.toggle_almacen, name='toggle_almacen'),
    path('proveedores/', core_views.lista_proveedores, name='proveedores'),
    path('proveedores/nuevo/', core_views.crear_proveedor, name='crear_proveedor'),
    path('proveedores/<int:pk>/editar/', core_views.editar_proveedor, name='editar_proveedor'),
    path('marcas/', core_views.lista_marcas, name='marcas'),
    path('marcas/nueva/', core_views.crear_marca, name='crear_marca'),
    path('marcas/<int:pk>/editar/', core_views.editar_marca, name='editar_marca'),
    path('marcas/<int:pk>/eliminar/', core_views.eliminar_marca, name='eliminar_marca'),
    path('categorias/', core_views.lista_categorias, name='categorias'),
    path('categorias/nueva/', core_views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', core_views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', core_views.eliminar_categoria, name='eliminar_categoria'),
    path('subcategorias/nueva/', core_views.crear_subcategoria, name='crear_subcategoria'),
    path('subcategorias/<int:pk>/editar/', core_views.editar_subcategoria, name='editar_subcategoria'),
    path('subcategorias/<int:pk>/eliminar/', core_views.eliminar_subcategoria, name='eliminar_subcategoria'),
    path('catalogo/', core_views.catalogo_productos, name='catalogo'),
    path('precioshost/', reportes_views.catalogo_precios_publico, name='precios_publico'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
