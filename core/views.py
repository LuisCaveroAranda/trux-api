from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from productos.models import Producto, Inventario, Proveedor, Categoria, Subcategoria, Marca
from compras.models import Compra
from .models import Almacen


@login_required
def dashboard(request):
    hoy = timezone.now().date()
    from django.db.models import F
    alertas = list(Inventario.objects.filter(
        stock_actual__gt=0,
        stock_actual__lte=F('stock_minimo'),
    ).select_related('presentacion__producto', 'almacen')[:8])
    sin_stock = list(Inventario.objects.filter(
        stock_actual__lte=0
    ).select_related('presentacion__producto', 'almacen')[:4])
    alertas_stock = alertas + sin_stock

    context = {
        'total_productos': Producto.objects.filter(estado='activo').count(),
        'total_proveedores': Proveedor.objects.filter(activo=True).count(),
        'compras_mes': Compra.objects.filter(
            creado_en__year=hoy.year, creado_en__month=hoy.month
        ).count(),
        'alertas_stock': alertas_stock,
        'productos_alerta': len(alertas_stock),
        'ultimas_compras': Compra.objects.select_related('proveedor').order_by('-creado_en')[:5],
    }
    return render(request, 'dashboard.html', context)


@login_required
def almacenes(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        pk = request.POST.get('id')
        if nombre:
            if pk:
                a = get_object_or_404(Almacen, pk=pk)
                a.nombre = nombre
                a.direccion = direccion
                a.save()
                messages.success(request, 'Almacén actualizado.')
            else:
                Almacen.objects.create(nombre=nombre, direccion=direccion)
                messages.success(request, f'Almacén "{nombre}" creado.')
        return redirect('almacenes')

    lista = Almacen.objects.all().order_by('nombre')
    return render(request, 'almacenes.html', {'almacenes': lista})


@login_required
@require_POST
def toggle_almacen(request, pk):
    a = get_object_or_404(Almacen, pk=pk)
    a.activo = not a.activo
    a.save()
    return redirect('almacenes')


# ── Proveedores ──────────────────────────────────────────────────────────────

@login_required
def lista_proveedores(request):
    q = request.GET.get('q', '')
    qs = Proveedor.objects.all()
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(ruc__icontains=q))
    return render(request, 'proveedores/lista.html', {'proveedores': qs, 'q': q})


@login_required
def crear_proveedor(request):
    if request.method == 'POST':
        prov = _guardar_proveedor(request, None)
        if prov:
            messages.success(request, f'Proveedor "{prov.nombre}" creado.')
            return redirect('proveedores')
    return render(request, 'proveedores/form.html', {'proveedor': None})


@login_required
def editar_proveedor(request, pk):
    prov = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        result = _guardar_proveedor(request, prov)
        if result:
            messages.success(request, 'Proveedor actualizado.')
            return redirect('proveedores')
    return render(request, 'proveedores/form.html', {'proveedor': prov})


def _guardar_proveedor(request, prov):
    data = request.POST
    if not prov:
        prov = Proveedor()
    nombre = data['nombre'].strip().upper()
    duplicado = Proveedor.objects.filter(nombre__iexact=nombre).exclude(pk=prov.pk).first()
    if duplicado:
        messages.error(request, f'Ya existe un proveedor con el nombre "{duplicado.nombre}".')
        return None
    prov.nombre = nombre
    prov.ruc = data.get('ruc', '')
    prov.telefono = data.get('telefono', '')
    prov.whatsapp = data.get('whatsapp', '')
    prov.email = data.get('email', '')
    prov.direccion = data.get('direccion', '')
    prov.numero_cuenta = data.get('numero_cuenta', '')
    prov.contacto = data.get('contacto', '')
    prov.numero_contacto = data.get('numero_contacto', '')
    prov.activo = 'activo' in data
    prov.save()
    return prov


# ── Marcas ───────────────────────────────────────────────────────────────────

@login_required
def lista_marcas(request):
    marcas = Marca.objects.all()
    return render(request, 'marcas/lista.html', {'marcas': marcas})


@login_required
def crear_marca(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            _, created = Marca.objects.get_or_create(nombre=nombre)
            if created:
                messages.success(request, f'Marca "{nombre}" creada.')
            else:
                messages.warning(request, f'La marca "{nombre}" ya existe.')
    return redirect('marcas')


@login_required
def editar_marca(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            marca.nombre = nombre
            marca.save()
            messages.success(request, 'Marca actualizada.')
        return redirect('marcas')
    return render(request, 'marcas/editar.html', {'marca': marca})


@login_required
def eliminar_marca(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == 'POST':
        marca.delete()
        messages.success(request, 'Marca eliminada.')
    return redirect('marcas')


# ── Categorías ───────────────────────────────────────────────────────────────

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.prefetch_related('subcategorias').all()
    return render(request, 'categorias/lista.html', {'categorias': categorias})


@login_required
def crear_categoria(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            cat, created = Categoria.objects.get_or_create(nombre=nombre)
            if created:
                messages.success(request, f'Categoría "{nombre}" creada.')
            else:
                messages.warning(request, f'La categoría "{nombre}" ya existe.')
    return redirect('categorias')


@login_required
def editar_categoria(request, pk):
    cat = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            cat.nombre = nombre
            cat.save()
            messages.success(request, 'Categoría actualizada.')
        return redirect('categorias')
    return render(request, 'categorias/editar.html', {'categoria': cat})


@login_required
def eliminar_categoria(request, pk):
    cat = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Categoría eliminada.')
    return redirect('categorias')


@login_required
def crear_subcategoria(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        cat_id = request.POST.get('categoria')
        if nombre and cat_id:
            Subcategoria.objects.get_or_create(nombre=nombre, categoria_id=cat_id)
            messages.success(request, f'Subcategoría "{nombre}" creada.')
    return redirect('categorias')


@login_required
def editar_subcategoria(request, pk):
    sub = get_object_or_404(Subcategoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        cat_id = request.POST.get('categoria')
        if nombre:
            sub.nombre = nombre
            if cat_id:
                sub.categoria_id = cat_id
            sub.save()
            messages.success(request, f'Subcategoría actualizada.')
    return redirect('categorias')


@login_required
def eliminar_subcategoria(request, pk):
    sub = get_object_or_404(Subcategoria, pk=pk)
    if request.method == 'POST':
        sub.delete()
        messages.success(request, 'Subcategoría eliminada.')
    return redirect('categorias')



def catalogo_productos(request):
    from django.db.models import Count
    from django.utils import timezone
    import datetime
    hace_30_dias = timezone.now() - datetime.timedelta(days=30)
    qs = Producto.objects.filter(estado='activo') \
        .select_related('categoria', 'subcategoria', 'marca') \
        .prefetch_related('fotos', 'presentaciones') \
        .order_by('categoria__nombre', 'subcategoria__nombre', 'nombre')
    nuevos_ids = set(Producto.objects.filter(estado='activo', creado_en__gte=hace_30_dias).values_list('id', flat=True))

    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    subcategoria = request.GET.get('subcategoria', '')
    marca = request.GET.get('marca', '')

    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    if categoria:
        qs = qs.filter(categoria_id=categoria)
    if subcategoria:
        qs = qs.filter(subcategoria_id=subcategoria)
    if marca:
        qs = qs.filter(marca_id=marca)

    paginator = Paginator(qs, 24)
    page = request.GET.get('page', 1)
    productos = paginator.get_page(page)

    params = request.GET.copy()
    params.pop('page', None)
    query_string = params.urlencode()

    # Categorías con conteo
    categorias = Categoria.objects.annotate(
        total=Count('producto', filter=Q(producto__estado='activo'))
    ).filter(total__gt=0).order_by('nombre')

    # Subcategorías filtradas por categoría seleccionada
    subcategorias_filtradas = []
    if categoria:
        subcategorias_filtradas = Subcategoria.objects.filter(
            categoria_id=categoria
        ).annotate(
            total=Count('producto', filter=Q(producto__estado='activo'))
        ).filter(total__gt=0).order_by('nombre')

    return render(request, 'catalogo/catalogo.html', {
        'productos': productos,
        'total': paginator.count,
        'categorias': categorias,
        'subcategorias_filtradas': subcategorias_filtradas,
        'marcas': Marca.objects.all().order_by('nombre'),
        'q': q,
        'categoria': categoria,
        'subcategoria': subcategoria,
        'marca': marca,
        'query_string': query_string,
        'nuevos_ids': nuevos_ids,
    })
