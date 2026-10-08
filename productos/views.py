from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum

from .models import (
    Producto, Categoria, Subcategoria, Marca, Proveedor,
    ProductoPrecio, PrecioFraccion, ProductoFoto, ProductoCampo,
    ProductoProveedor, Inventario, Kardex,
)
# Proveedores, Marcas y Categorías se gestionan desde core/views.py


@login_required
def lista_productos(request):
    qs = Producto.objects.select_related('categoria', 'subcategoria', 'marca').prefetch_related('presentaciones__costos_proveedor__proveedor', 'fotos')
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(aliases__icontains=q))
    categoria = request.GET.get('categoria')
    if categoria:
        qs = qs.filter(categoria_id=categoria)
    estado = request.GET.get('estado')
    if estado:
        qs = qs.filter(estado=estado)

    for p in qs:
        p.stock_total = Inventario.objects.filter(
            presentacion__producto=p
        ).aggregate(t=Sum('stock_actual'))['t'] or 0

    paginator = Paginator(qs, 25)
    productos = paginator.get_page(request.GET.get('page'))
    return render(request, 'productos/lista.html', {
        'productos': productos,
        'categorias': Categoria.objects.all(),
    })


@login_required
def crear_producto(request):
    if request.method == 'POST':
        producto = _guardar_producto(request, None)
        if request.FILES.get('foto'):
            try:
                import cloudinary.uploader
                archivo = request.FILES['foto']
                import time
                resultado = cloudinary.uploader.upload(
                    archivo,
                    folder='charito_productos',
                    public_id=f'producto_{producto.id}_{int(time.time())}',
                    overwrite=False,
                )
                ProductoFoto.objects.create(
                    producto=producto,
                    url=resultado['secure_url'],
                    es_principal=True,
                )
            except Exception as e:
                messages.warning(request, f'Producto creado pero error al subir foto: {e}')
        messages.success(request, f'Producto {producto.codigo} creado correctamente.')
        return redirect('productos:detalle', producto.id)
    return render(request, 'productos/form.html', _contexto_form(None))


@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        try:
            _guardar_producto(request, producto)
            if request.FILES.get('foto'):
                import cloudinary.uploader, time
                archivo = request.FILES['foto']
                resultado = cloudinary.uploader.upload(
                    archivo,
                    folder='charito_productos',
                    public_id=f'producto_{pk}_{int(time.time())}',
                    overwrite=False,
                )
                es_principal = not producto.fotos.exists()
                ProductoFoto.objects.create(
                    producto=producto,
                    url=resultado['secure_url'],
                    es_principal=es_principal,
                )
            messages.success(request, 'Producto actualizado correctamente.')
        except Exception as e:
            import traceback
            print(f'ERROR editar_producto: {traceback.format_exc()}')
            messages.error(request, f'Error al guardar: {e}')
        return redirect('productos:detalle', producto.id)
    return render(request, 'productos/form.html', _contexto_form(producto))


def _contexto_form(producto):
    return {
        'producto': producto,
        'categorias': Categoria.objects.all(),
        'subcategorias': Subcategoria.objects.select_related('categoria').all(),
        'marcas': Marca.objects.all(),
        'proveedores': Proveedor.objects.filter(activo=True),
        'presentaciones': producto.presentaciones.prefetch_related('fracciones').all() if producto else [],
        'fotos': producto.fotos.all() if producto else [],
        'campos': producto.campos.all() if producto else [],
    }


def _guardar_producto(request, producto):
    data = request.POST
    if not producto:
        producto = Producto()
    producto.nombre = data['nombre']
    producto.aliases = data.get('aliases', '')
    producto.descripcion = data.get('descripcion', '').strip()
    producto.estado = 'activo' if 'estado_activo' in data else 'inactivo'
    cat_id = data.get('categoria')
    producto.categoria_id = cat_id if cat_id else None
    sub_id = data.get('subcategoria')
    producto.subcategoria_id = sub_id if sub_id else None
    marca_id = data.get('marca')
    producto.marca_id = marca_id if marca_id else None
    producto.save()

    # Presentaciones (array fields from form)
    tipos = data.getlist('pres_tipo[]')
    unidades_list = data.getlist('pres_unidades[]')
    precios = data.getlist('pres_precio[]')
    precios_may = data.getlist('pres_precio_may[]')
    costos = data.getlist('pres_costo[]')
    mitades = data.getlist('pres_mitad[]')   # valores posicionales no disponibles en checkbox múltiple
    cuartos = data.getlist('pres_cuarto[]')

    # Para checkboxes múltiples necesitamos índices — usamos campos hidden con índice
    # Los checkboxes envían solo los que están marcados sin posición, así que
    # usamos un enfoque diferente: el form envía pres_mitad_N y pres_cuarto_N
    # Eliminar presentaciones que ya no están en el formulario, solo si no tienen compras
    from compras.models import CompraItem
    tipos_enviados = {t.strip().upper() for t in tipos if t.strip()}
    pres_a_borrar = producto.presentaciones.exclude(tipo_venta__in=tipos_enviados)
    pres_con_compras = set(CompraItem.objects.filter(presentacion__in=pres_a_borrar).values_list('presentacion_id', flat=True))
    pres_a_borrar.exclude(id__in=pres_con_compras).delete()

    tipos_procesados = set()
    for i, tipo in enumerate(tipos):
        tipo = tipo.strip().upper()
        if not tipo or tipo in tipos_procesados:
            continue
        tipos_procesados.add(tipo)

        unidades = int(unidades_list[i]) if i < len(unidades_list) and unidades_list[i] else 1
        precio = precios[i] if i < len(precios) and precios[i] else None
        precio_may = precios_may[i] if i < len(precios_may) and precios_may[i] else None
        costo = costos[i] if i < len(costos) and costos[i] else None
        print(f'  presentacion[{i}] tipo={tipo} unidades={unidades} precio={precio} precio_may={precio_may} costo={costo}')

        permite_mitad = data.get(f'pres_mitad_{i}') == '1'
        permite_cuarto = data.get(f'pres_cuarto_{i}') == '1'

        pres = ProductoPrecio.objects.filter(producto=producto, tipo_venta__iexact=tipo).first()
        if pres:
            pres.tipo_venta = tipo
            pres.unidades_base = unidades
            pres.precio_minorista = precio
            pres.precio_mayorista = precio_may
            pres.permite_fraccion = permite_mitad or permite_cuarto
            pres.save()
        else:
            pres = ProductoPrecio.objects.create(
                producto=producto, tipo_venta=tipo,
                unidades_base=unidades,
                precio_minorista=precio,
                precio_mayorista=precio_may,
                permite_fraccion=permite_mitad or permite_cuarto,
            )

        # El costo por presentación se propaga al final del loop

        # Fracciones automáticas
        pres.fracciones.all().delete()
        if permite_mitad and unidades >= 2:
            PrecioFraccion.objects.create(
                presentacion=pres, nombre='mitad', unidades_base=unidades // 2
            )
        if permite_cuarto and unidades >= 4:
            PrecioFraccion.objects.create(
                presentacion=pres, nombre='cuarto', unidades_base=unidades // 4
            )

    # Guardar costos exactos ingresados en el formulario
    from decimal import Decimal
    prov_id = data.get('proveedor_nuevo') or None

    # Mapa tipo_venta → costo exacto ingresado (en mayúsculas igual que las presentaciones)
    costos_ingresados = {}
    for i, tipo in enumerate(tipos):
        tipo = tipo.strip().upper()
        if not tipo:
            continue
        costo = costos[i] if i < len(costos) and costos[i] else None
        if costo:
            costos_ingresados[tipo] = Decimal(costo)

    if prov_id:
        # Nuevo proveedor seleccionado — limpiar y recrear con costos ingresados
        ProductoProveedor.objects.filter(
            presentacion__producto=producto, proveedor_id=prov_id
        ).delete()
        for pres in producto.presentaciones.all():
            costo_val = costos_ingresados.get(pres.tipo_venta, Decimal('0'))
            ProductoProveedor.objects.create(
                presentacion=pres, proveedor_id=prov_id, costo=costo_val,
            )
    elif costos_ingresados:
        # Sin proveedor nuevo — actualizar costos en registros existentes
        for pres in producto.presentaciones.all():
            if pres.tipo_venta not in costos_ingresados:
                continue
            costo_val = costos_ingresados[pres.tipo_venta]
            pp_qs = ProductoProveedor.objects.filter(presentacion=pres)
            if pp_qs.exists():
                pp_qs.update(costo=costo_val)
            else:
                ProductoProveedor.objects.create(presentacion=pres, costo=costo_val)

    # Campos personalizados
    nombres_campo = data.getlist('campo_nombre[]')
    valores_campo = data.getlist('campo_valor[]')
    for nombre_c, valor_c in zip(nombres_campo, valores_campo):
        nombre_c = nombre_c.strip()
        valor_c = valor_c.strip()
        if nombre_c and valor_c:
            ProductoCampo.objects.update_or_create(
                producto=producto, nombre=nombre_c, defaults={'valor': valor_c}
            )

    return producto


@login_required
def detalle_producto(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria', 'marca')
        .prefetch_related('fotos', 'presentaciones__fracciones', 'campos'),
        pk=pk
    )
    inventarios = Inventario.objects.filter(
        presentacion__producto=producto
    ).select_related('presentacion', 'almacen')
    kardex = Kardex.objects.filter(
        presentacion__producto=producto
    ).select_related('almacen').order_by('-fecha')[:20]
    from compras.models import HistorialCosto
    historial_costos = HistorialCosto.objects.filter(
        presentacion__producto=producto
    ).select_related('presentacion', 'proveedor', 'compra').order_by('-fecha')[:20]
    return render(request, 'productos/detalle.html', {
        'producto': producto,
        'inventarios': inventarios,
        'kardex': kardex,
        'historial_costos': historial_costos,
    })


@login_required
def subir_foto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST' and request.FILES.get('foto'):
        archivo = request.FILES['foto']
        try:
            import cloudinary.uploader
            import time
            resultado = cloudinary.uploader.upload(
                archivo,
                folder='charito_productos',
                public_id=f'producto_{pk}_{int(time.time())}',
                overwrite=False,
            )
            url = resultado['secure_url']
            es_principal = not producto.fotos.exists()
            ProductoFoto.objects.create(
                producto=producto,
                url=url,
                es_principal=es_principal,
            )
            messages.success(request, 'Foto subida correctamente.')
        except Exception as e:
            messages.error(request, f'Error al subir foto: {e}')
    return redirect('productos:editar', pk)


@login_required
def eliminar_foto(request, foto_id):
    foto = get_object_or_404(ProductoFoto, pk=foto_id)
    producto_id = foto.producto_id
    try:
        import cloudinary.uploader
        from urllib.parse import urlparse
        path = urlparse(foto.url).path
        public_id = '/'.join(path.split('/')[3:]).rsplit('.', 1)[0]
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass
    foto.delete()
    messages.success(request, 'Foto eliminada.')
    return redirect('productos:editar', producto_id)



@login_required
def inventario(request):
    from core.models import Almacen
    from collections import defaultdict

    almacenes = Almacen.objects.filter(activo=True).order_by('nombre')
    q = request.GET.get('q', '')

    qs = Inventario.objects.select_related(
        'presentacion__producto', 'almacen'
    ).filter(stock_actual__gt=0)
    if q:
        qs = qs.filter(presentacion__producto__nombre__icontains=q)

    almacenes_list = list(almacenes)
    almacen_ids = [a.id for a in almacenes_list]

    # Agrupar stock total en unidades base por (producto, almacen)
    stock_map = defaultdict(lambda: defaultdict(int))  # {prod_id: {almacen_id: unidades_base}}
    prod_map = {}  # {prod_id: producto}

    for inv in qs:
        prod = inv.presentacion.producto
        stock_map[prod.id][inv.almacen_id] += inv.stock_actual
        prod_map[prod.id] = prod

    # Presentaciones por producto ordenadas de mayor a menor unidades_base
    pres_map = defaultdict(list)
    prod_ids = list(prod_map.keys())
    for pres in ProductoPrecio.objects.filter(producto_id__in=prod_ids).order_by('-unidades_base'):
        pres_map[pres.producto_id].append(pres)

    def descomponer(total_unidades, presentaciones):
        resultado = []
        restante = total_unidades
        for pres in sorted(presentaciones, key=lambda p: -p.unidades_base):
            if restante <= 0:
                break
            cantidad = restante // pres.unidades_base
            if cantidad > 0:
                resultado.append({'pres': pres, 'cantidad': cantidad})
                restante -= cantidad * pres.unidades_base
        return resultado

    prods_sorted = sorted(prod_map.values(), key=lambda p: p.nombre)

    filas = []
    for prod in prods_sorted:
        stocks_por_almacen = [stock_map[prod.id].get(aid, 0) for aid in almacen_ids]
        total = sum(stocks_por_almacen)
        if total == 0:
            continue
        presentaciones = pres_map[prod.id]
        descomp_por_almacen = []
        for stock in stocks_por_almacen:
            descomp_por_almacen.append(descomponer(stock, presentaciones) if stock > 0 else [])
        descomp_total = descomponer(total, presentaciones)
        filas.append({
            'producto': prod,
            'stocks_por_almacen': descomp_por_almacen,
            'total_unidades': total,
            'descomp_total': descomp_total,
        })

    return render(request, 'productos/inventario.html', {
        'filas': filas,
        'almacenes': almacenes_list,
        'q': q,
    })
