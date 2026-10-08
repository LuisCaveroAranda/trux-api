from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, TruncDate, Coalesce
from django.db.models import Value
from datetime import date, timedelta
import json
from decimal import Decimal
from compras.models import Compra
from productos.models import Proveedor, Categoria, Producto, Inventario, ProductoPrecio
from ventas.models import Venta, VentaItem
from clientes.models import Cliente
from core.models import Almacen


@login_required
def reporte_ventas(request):
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    cliente_id = request.GET.get('cliente', '')
    producto_id = request.GET.get('producto', '')
    categoria_id = request.GET.get('categoria', '')

    # Defaults: mes actual
    if not fecha_desde:
        fecha_desde = date.today().replace(day=1).isoformat()
    if not fecha_hasta:
        fecha_hasta = date.today().isoformat()

    qs = Venta.objects.filter(estado='confirmada', fecha__gte=fecha_desde, fecha__lte=fecha_hasta)
    items_qs = VentaItem.objects.filter(
        venta__estado='confirmada',
        venta__fecha__gte=fecha_desde,
        venta__fecha__lte=fecha_hasta,
    )

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
        items_qs = items_qs.filter(venta__cliente_id=cliente_id)
    if producto_id:
        qs = qs.filter(items__presentacion__producto_id=producto_id).distinct()
        items_qs = items_qs.filter(presentacion__producto_id=producto_id)
    if categoria_id:
        qs = qs.filter(items__presentacion__producto__categoria_id=categoria_id).distinct()
        items_qs = items_qs.filter(presentacion__producto__categoria_id=categoria_id)

    # Métricas principales
    resumen = qs.aggregate(
        total=Sum('total'),
        num_ventas=Count('id'),
    )
    resumen['ticket_promedio'] = (
        (resumen['total'] or Decimal('0')) / resumen['num_ventas']
    ) if resumen['num_ventas'] else Decimal('0')

    # Top clientes
    por_cliente = (
        qs.annotate(
            nombre_cli=Coalesce('cliente__nombre', 'cliente_nombre', Value('Clientes Varios'))
        )
        .values('nombre_cli')
        .annotate(total=Sum('total'), ventas=Count('id'))
        .order_by('-total')[:10]
    )

    # Top productos más vendidos
    por_producto = (
        items_qs
        .annotate(monto=ExpressionWrapper(F('cantidad') * F('precio_unitario'), output_field=DecimalField()))
        .values('presentacion__producto__nombre', 'presentacion__tipo_venta')
        .annotate(cantidad=Sum('cantidad'), total=Sum('monto'))
        .order_by('-total')[:10]
    )

    # Ventas por día para gráfico
    por_dia = list(
        qs.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total=Sum('total'), ventas=Count('id'))
        .order_by('dia')
    )

    # Por mes histórico
    por_mes = (
        Venta.objects.filter(estado='confirmada')
        .annotate(mes_grupo=TruncMonth('fecha'))
        .values('mes_grupo')
        .annotate(total=Sum('total'), ventas=Count('id'))
        .order_by('-mes_grupo')[:12]
    )

    # Serializar para Chart.js
    chart_labels = [str(d['dia']) for d in por_dia]
    chart_totales = [float(d['total'] or 0) for d in por_dia]

    return render(request, 'reportes/ventas.html', {
        'resumen': resumen,
        'por_cliente': por_cliente,
        'por_producto': por_producto,
        'por_mes': por_mes,
        'ventas': qs.select_related('cliente', 'almacen').order_by('-fecha')[:100],
        'clientes': Cliente.objects.filter(activo=True).order_by('nombre'),
        'productos': Producto.objects.filter(estado='activo').order_by('nombre'),
        'categorias': Categoria.objects.all().order_by('nombre'),
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'cliente_sel': cliente_id,
        'producto_sel': producto_id,
        'categoria_sel': categoria_id,
        'chart_labels': json.dumps(chart_labels),
        'chart_totales': json.dumps(chart_totales),
    })


@login_required
def reporte_inventario(request):
    almacen_id = request.GET.get('almacen', '')
    categoria_id = request.GET.get('categoria', '')

    qs = Inventario.objects.select_related(
        'presentacion__producto__categoria', 'almacen'
    ).filter(stock_actual__gt=0)

    if almacen_id:
        qs = qs.filter(almacen_id=almacen_id)
    if categoria_id:
        qs = qs.filter(presentacion__producto__categoria_id=categoria_id)

    # Agrupar por producto
    from collections import defaultdict
    prod_map = {}       # {prod_id: producto}
    stock_map = defaultdict(lambda: defaultdict(int))   # {prod_id: {almacen_id: ub}}
    almacen_set = {}    # {almacen_id: almacen}

    for inv in qs:
        p = inv.presentacion.producto
        prod_map[p.id] = p
        stock_map[p.id][inv.almacen_id] += inv.stock_actual
        almacen_set[inv.almacen_id] = inv.almacen

    almacenes_lista = sorted(almacen_set.values(), key=lambda a: a.nombre)
    almacen_ids = [a.id for a in almacenes_lista]

    # Presentaciones por producto para descomponer
    pres_map = defaultdict(list)
    for pres in ProductoPrecio.objects.filter(producto_id__in=prod_map.keys()).order_by('-unidades_base'):
        pres_map[pres.producto_id].append(pres)

    def descomponer(total_ub, presentaciones):
        resultado, restante = [], total_ub
        for p in sorted(presentaciones, key=lambda x: -x.unidades_base):
            if restante <= 0:
                break
            cant = restante // p.unidades_base
            if cant > 0:
                resultado.append({'pres': p, 'cantidad': cant})
                restante -= cant * p.unidades_base
        return resultado

    filas = []
    for prod in sorted(prod_map.values(), key=lambda p: p.nombre):
        stocks = [stock_map[prod.id].get(aid, 0) for aid in almacen_ids]
        total = sum(stocks)
        filas.append({
            'producto': prod,
            'stocks': stocks,
            'total': total,
            'descomp': descomponer(total, pres_map[prod.id]),
        })

    # Métricas
    total_productos = len(filas)
    total_ub = sum(f['total'] for f in filas)

    return render(request, 'reportes/inventario.html', {
        'filas': filas,
        'almacenes_lista': almacenes_lista,
        'total_productos': total_productos,
        'total_ub': total_ub,
        'almacenes': Almacen.objects.filter(activo=True),
        'categorias': Categoria.objects.all().order_by('nombre'),
        'almacen_sel': almacen_id,
        'categoria_sel': categoria_id,
    })


@login_required
def catalogo_precios(request):
    from collections import defaultdict

    # Traer todos los productos activos con sus presentaciones y último costo
    productos = (
        Producto.objects
        .filter(estado__in=['activo', 'incompleto'])
        .select_related('categoria', 'subcategoria', 'marca')
        .prefetch_related(
            'presentaciones__costos_proveedor',
            'fotos'
        )
        .order_by('categoria__nombre', 'subcategoria__nombre', 'nombre')
    )

    # Agrupar: {categoria: {subcategoria: [filas]}}
    grupos = defaultdict(lambda: defaultdict(list))

    for prod in productos:
        cat = prod.categoria.nombre if prod.categoria else 'Sin categoría'
        sub = prod.subcategoria.nombre if prod.subcategoria else 'Sin subcategoría'

        presentaciones = []
        for pres in prod.presentaciones.all():
            ultimo_costo = pres.costos_proveedor.order_by('-creado_en').first()
            if ultimo_costo:
                costo = ultimo_costo.costo_con_flete or ultimo_costo.costo
                tiene_flete = bool(ultimo_costo.costo_con_flete)
            else:
                costo = None
                tiene_flete = False
            presentaciones.append({
                'tipo_venta': pres.tipo_venta,
                'unidades_base': pres.unidades_base,
                'precio_venta': pres.precio_minorista,
                'precio_mayorista': pres.precio_mayorista,
                'costo': costo,
                'tiene_flete': tiene_flete,
            })

        if presentaciones:
            foto = prod.fotos.all().first()
            grupos[cat][sub].append({
                'nombre': prod.nombre,
                'marca': prod.marca.nombre if prod.marca else None,
                'presentaciones': presentaciones,
                'foto': foto.url if foto else None,
            })

    # Convertir a lista ordenada, marcando cuándo mostrar encabezado de presentaciones
    grupos_ordenados = []
    for cat, subs in sorted(grupos.items()):
        subcats = []
        for sub, filas in sorted(subs.items()):
            prev_tipos = None
            for prod in filas:
                tipos = [p['tipo_venta'] for p in prod['presentaciones']]
                prod['mostrar_encabezado'] = (tipos != prev_tipos)
                prev_tipos = tipos
            subcats.append({'nombre': sub, 'filas': filas})
        grupos_ordenados.append({'categoria': cat, 'subcategorias': subcats})

    return render(request, 'reportes/catalogo.html', {
        'grupos': grupos_ordenados,
    })


def _youtube_embed(texto):
    """Extrae embed URL de YouTube desde un texto/URL. Retorna None si no hay."""
    import re
    if not texto:
        return None
    patrones = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})',
    ]
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return f'https://www.youtube.com/embed/{m.group(1)}?rel=0&autoplay=1'
    return None


def catalogo_precios_publico(request):
    from collections import defaultdict

    productos = (
        Producto.objects
        .filter(estado__in=['activo', 'incompleto'])
        .select_related('categoria', 'subcategoria', 'marca')
        .prefetch_related('presentaciones__costos_proveedor', 'fotos')
        .order_by('categoria__nombre', 'subcategoria__nombre', 'nombre')
    )

    grupos = defaultdict(lambda: defaultdict(list))
    for prod in productos:
        cat = prod.categoria.nombre if prod.categoria else 'Sin categoría'
        sub = prod.subcategoria.nombre if prod.subcategoria else 'Sin subcategoría'
        presentaciones = []
        for pres in prod.presentaciones.all():
            ultimo_costo = pres.costos_proveedor.order_by('-creado_en').first()
            costo = None
            if ultimo_costo:
                costo = ultimo_costo.costo_con_flete or ultimo_costo.costo
            presentaciones.append({
                'tipo_venta': pres.tipo_venta,
                'precio_venta': pres.precio_minorista,
                'precio_mayorista': pres.precio_mayorista,
                'costo': costo,
            })
        if presentaciones:
            foto = prod.fotos.all().first()
            grupos[cat][sub].append({
                'nombre': prod.nombre,
                'marca': prod.marca.nombre if prod.marca else None,
                'presentaciones': presentaciones,
                'foto': foto.url if foto else None,
                'video_url': prod.descripcion if prod.descripcion else None,
            })

    grupos_ordenados = []
    for cat, subs in sorted(grupos.items()):
        subcats = []
        for sub, filas in sorted(subs.items()):
            subcats.append({'nombre': sub, 'filas': filas})
        grupos_ordenados.append({'categoria': cat, 'subcategorias': subcats})

    return render(request, 'reportes/catalogo_publico.html', {'grupos': grupos_ordenados})


@login_required
def reporte_compras(request):
    mes = request.GET.get('mes', date.today().month)
    anio = request.GET.get('anio', date.today().year)
    proveedor_id = request.GET.get('proveedor', '')

    try:
        mes = int(mes)
        anio = int(anio)
    except (ValueError, TypeError):
        mes = date.today().month
        anio = date.today().year

    qs = Compra.objects.filter(estado='confirmada')
    if mes and anio:
        qs = qs.filter(fecha__month=mes, fecha__year=anio)
    if proveedor_id:
        qs = qs.filter(proveedor_id=proveedor_id)

    resumen = qs.aggregate(
        total=Sum('total'),
        flete_proveedor=Sum('flete_proveedor'),
        flete_agencia=Sum('flete_agencia_total'),
        subtotal=Sum('subtotal'),
        num_guias=Count('id'),
    )

    por_proveedor = (
        qs.values('proveedor__nombre')
        .annotate(total=Sum('total'), guias=Count('id'))
        .order_by('-total')
    )

    # Por mes (últimos 12 meses)
    from django.db.models.functions import TruncMonth
    por_mes = (
        Compra.objects.filter(estado='confirmada')
        .annotate(mes_grupo=TruncMonth('fecha'))
        .values('mes_grupo')
        .annotate(total=Sum('total'), guias=Count('id'))
        .order_by('-mes_grupo')[:12]
    )

    meses = [
        (1,'Enero'),(2,'Febrero'),(3,'Marzo'),(4,'Abril'),
        (5,'Mayo'),(6,'Junio'),(7,'Julio'),(8,'Agosto'),
        (9,'Septiembre'),(10,'Octubre'),(11,'Noviembre'),(12,'Diciembre'),
    ]
    anios = list(range(date.today().year, date.today().year - 5, -1))

    return render(request, 'reportes/compras.html', {
        'resumen': resumen,
        'por_proveedor': por_proveedor,
        'por_mes': por_mes,
        'proveedores': Proveedor.objects.filter(activo=True),
        'mes_sel': mes,
        'anio_sel': anio,
        'proveedor_sel': proveedor_id,
        'meses': meses,
        'anios': anios,
        'compras': qs.select_related('proveedor', 'almacen').order_by('-fecha'),
    })
