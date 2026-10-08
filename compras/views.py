from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Compra, CompraItem, StockInicial, Transferencia, TransferenciaItem
from productos.models import Producto, Proveedor
from core.models import Almacen


@login_required
def lista_compras(request):
    qs = Compra.objects.select_related('proveedor', 'almacen', 'registrado_por').order_by('-creado_en')
    estado = request.GET.get('estado')
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, 'compras/lista.html', {'compras': qs})


@login_required
def crear_compra(request):
    if request.method == 'POST':
        compra = _guardar_compra(request, None)
        messages.success(request, f'Guía {compra.numero} creada.')
        return redirect('compras:detalle', compra.id)
    return render(request, 'compras/form.html', _contexto_compra(None, request.user))


@login_required
def detalle_compra(request, pk):
    from decimal import Decimal
    compra = get_object_or_404(
        Compra.objects.select_related('proveedor', 'almacen', 'registrado_por')
        .prefetch_related('items__presentacion__producto__marca'),
        pk=pk
    )

    items = list(compra.items.all())

    items_con_costo = []
    for item in items:
        flete_prov_prop = item.flete_proveedor_proporcional
        costo_total_item = item.subtotal_calc + item.flete_agencia_proporcional + flete_prov_prop
        costo_pres_cflete = (costo_total_item / Decimal(str(item.cantidad))).quantize(Decimal('0.01')) if item.cantidad > 0 else Decimal('0')
        items_con_costo.append({
            'item': item,
            'flete_prov_prop': flete_prov_prop,
            'costo_cflete': costo_pres_cflete,
            'total_ub': item.cantidad * item.presentacion.unidades_base,
        })

    return render(request, 'compras/detalle.html', {'compra': compra, 'items_con_costo': items_con_costo})


@login_required
def editar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk, estado='borrador')
    if request.method == 'POST':
        _guardar_compra(request, compra)
        messages.success(request, 'Guía actualizada.')
        return redirect('compras:detalle', compra.id)
    return render(request, 'compras/form.html', _contexto_compra(compra, request.user))


@login_required
@require_POST
def anular_compra(request, pk):
    from django.db import transaction
    from django.utils import timezone
    compra = get_object_or_404(Compra, pk=pk, estado='confirmada')
    try:
        with transaction.atomic():
            from productos.models import Inventario, Kardex
            for item in compra.items.select_related('presentacion'):
                total_ub = item.cantidad * item.presentacion.unidades_base
                inv = Inventario.objects.filter(
                    presentacion=item.presentacion, almacen=compra.almacen
                ).first()
                if inv:
                    inv.stock_actual -= total_ub
                    inv.save()
                    Kardex.objects.create(
                        presentacion=item.presentacion,
                        almacen=compra.almacen,
                        tipo_movimiento='compra_anulada',
                        cantidad_salida=total_ub,
                        stock_resultante=inv.stock_actual,
                        referencia_tipo='compra',
                        referencia_id=compra.id,
                        fecha=timezone.now(),
                    )
            compra.estado = 'anulada'
            compra.save()
        messages.success(request, f'{compra.numero} anulada. Stock revertido.')
    except Exception as e:
        messages.error(request, f'Error al anular: {e}')
    return redirect('compras:detalle', pk)


@login_required
@require_POST
def confirmar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk, estado='borrador')
    try:
        compra.confirmar()
        messages.success(request, f'Guía {compra.numero} confirmada. Stock actualizado.')
    except Exception as e:
        messages.error(request, f'Error al confirmar: {e}')
    return redirect('compras:detalle', pk)


def _contexto_compra(compra, user):
    return {
        'compra': compra,
        'proveedores': Proveedor.objects.filter(activo=True),
        'almacenes': Almacen.objects.filter(activo=True),
        'productos': Producto.objects.filter(estado__in=['activo', 'incompleto']).select_related('marca').order_by('nombre'),
        'items': compra.items.select_related('presentacion__producto').all() if compra else [],
    }


def _guardar_compra(request, compra):
    data = request.POST
    if not compra:
        compra = Compra()
        compra.registrado_por = request.user

    prov_id = data.get('proveedor')
    compra.proveedor_id = prov_id if prov_id else None
    compra.almacen_id = data['almacen']
    compra.tipo = data['tipo']
    compra.fecha = data['fecha']
    compra.numero_documento = data.get('numero_documento', '')
    compra.flete_proveedor = (data.get('flete_proveedor') or '0').replace(',', '.')
    compra.observaciones = data.get('nota', '')
    compra.save()

    # Eliminar items existentes y recrear
    compra.items.all().delete()
    import math
    from decimal import Decimal

    productos_ids = data.getlist('item_producto')
    presentacion_ids = data.getlist('item_presentacion')
    cantidades = data.getlist('item_cantidad')
    precios = data.getlist('item_precio')
    num_bultos_list = data.getlist('item_num_bultos')
    precio_bulto_list = data.getlist('item_precio_bulto')
    grupo_bulto_list = data.getlist('item_grupo_bulto')

    # Calcular flete compartido por grupos
    grupos = {}
    for i, grupo in enumerate(grupo_bulto_list):
        g = grupo.strip().upper()
        if g:
            if g not in grupos:
                grupos[g] = []
            grupos[g].append(i)

    items_data = []
    for i, prod_id in enumerate(productos_ids):
        if not prod_id:
            continue
        cantidad = int(cantidades[i]) if i < len(cantidades) and cantidades[i] else 0
        costo_unit = Decimal(precios[i]) if i < len(precios) and precios[i] else Decimal('0')
        pres_id = presentacion_ids[i] if i < len(presentacion_ids) and presentacion_ids[i] else None
        precio_bulto_raw = Decimal(precio_bulto_list[i]) if i < len(precio_bulto_list) and precio_bulto_list[i] else Decimal('0')
        num_bultos_raw = num_bultos_list[i] if i < len(num_bultos_list) and num_bultos_list[i] else ''
        grupo = grupo_bulto_list[i].strip().upper() if i < len(grupo_bulto_list) else ''

        if not cantidad or not costo_unit:
            continue

        # Calcular bultos
        num_bultos = int(num_bultos_raw) if num_bultos_raw and num_bultos_raw.strip().lstrip('-').isdigit() else 1

        # Flete agencia: compartido o individual
        if grupo and grupo in grupos and len(grupos[grupo]) > 1:
            flete_agencia = precio_bulto_raw / len(grupos[grupo])
        else:
            flete_agencia = precio_bulto_raw * num_bultos

        items_data.append({
            'pres_id': pres_id,
            'cantidad': cantidad,
            'costo_unitario': costo_unit,
            'num_bultos': num_bultos,
            'flete_agencia_proporcional': flete_agencia,
            'precio_por_bulto': precio_bulto_raw,
            'grupo_bulto': grupo or '',
        })

    from decimal import Decimal as D
    subtotal_total = D('0')
    flete_ag_total = D('0')

    for item in items_data:
        subtotal_total += D(str(item['cantidad'])) * item['costo_unitario']

    flete_proveedor = D(str(compra.flete_proveedor))
    grupos_vistos = set()
    total_bultos = 0
    for item in items_data:
        grupo = item['grupo_bulto']
        if grupo:
            if grupo not in grupos_vistos:
                grupos_vistos.add(grupo)
                total_bultos += 1
        else:
            total_bultos += item['num_bultos'] or 1

    for item in items_data:
        grupo = item['grupo_bulto']
        grupo_count = sum(1 for i in items_data if i['grupo_bulto'] == grupo) if grupo else 1
        bultos_item = D('1') / D(str(grupo_count)) if grupo else D(str(item['num_bultos'] or 1))
        flete_prov_prop = (bultos_item / D(str(total_bultos)) * flete_proveedor).quantize(D('0.01')) if total_bultos > 0 else D('0')
        # flete_agencia_proporcional se calcula como property según num_bultos, precio_por_bulto y grupo
        grupo = item['grupo_bulto']
        grupo_count = sum(1 for i in items_data if i['grupo_bulto'] == grupo) if grupo else 1
        flete_ag_item = item['precio_por_bulto'] / D(str(grupo_count)) if grupo else D(str(item['num_bultos'] or 1)) * item['precio_por_bulto']
        flete_ag_total += flete_ag_item
        CompraItem.objects.create(
            compra=compra,
            presentacion_id=item['pres_id'],
            cantidad=item['cantidad'],
            costo_unitario=item['costo_unitario'],
            num_bultos=item['num_bultos'],
            precio_por_bulto=item['precio_por_bulto'],
            flete_proveedor_proporcional=flete_prov_prop,
            grupo_bulto=item['grupo_bulto'],
        )

    compra.subtotal = subtotal_total
    compra.flete_agencia_total = flete_ag_total
    compra.total = subtotal_total + D(str(compra.flete_proveedor)) + flete_ag_total
    compra.save()
    return compra


@login_required
def lista_transferencias(request):
    qs = Transferencia.objects.select_related('almacen_origen', 'almacen_destino', 'usuario').order_by('-fecha')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    almacen = request.GET.get('almacen')
    if fecha_desde:
        qs = qs.filter(fecha_transferencia__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_transferencia__lte=fecha_hasta)
    if almacen:
        qs = qs.filter(almacen_origen_id=almacen) | qs.filter(almacen_destino_id=almacen)
        qs = qs.order_by('-fecha')
    return render(request, 'transferencias/lista.html', {
        'transferencias': qs,
        'almacenes': Almacen.objects.filter(activo=True),
        'fecha_desde': fecha_desde or '',
        'fecha_hasta': fecha_hasta or '',
        'almacen_sel': almacen or '',
    })


@login_required
def crear_transferencia(request):
    if request.method == 'POST':
        t = Transferencia()
        t.almacen_origen_id = request.POST['almacen_origen']
        t.almacen_destino_id = request.POST['almacen_destino']
        t.motivo = request.POST.get('motivo', '')
        t.fecha_transferencia = request.POST.get('fecha_transferencia') or None
        t.usuario = request.user
        t.save()

        presentaciones = request.POST.getlist('presentacion_id')
        cantidades = request.POST.getlist('cantidad')
        from productos.models import ProductoPrecio
        for pres_id, cant in zip(presentaciones, cantidades):
            if pres_id and cant:
                pres = ProductoPrecio.objects.get(id=pres_id)
                TransferenciaItem.objects.create(
                    transferencia=t,
                    presentacion_id=pres_id,
                    cantidad_unidades_base=int(cant) * pres.unidades_base,
                )
        messages.success(request, f'{t.numero} creada.')
        return redirect('compras:detalle_transferencia', t.id)

    from productos.models import ProductoPrecio, Inventario
    almacenes = Almacen.objects.filter(activo=True)
    return render(request, 'transferencias/form.html', {
        'almacenes': almacenes,
        'productos': Producto.objects.filter(estado='activo').prefetch_related('presentaciones'),
    })


@login_required
def editar_transferencia(request, pk):
    t = get_object_or_404(Transferencia, pk=pk, estado='borrador')
    if request.method == 'POST':
        t.almacen_origen_id = request.POST['almacen_origen']
        t.almacen_destino_id = request.POST['almacen_destino']
        t.motivo = request.POST.get('motivo', '')
        t.fecha_transferencia = request.POST.get('fecha_transferencia') or None
        t.save()

        t.items.all().delete()
        presentaciones = request.POST.getlist('presentacion_id')
        cantidades = request.POST.getlist('cantidad')
        from productos.models import ProductoPrecio
        for pres_id, cant in zip(presentaciones, cantidades):
            if pres_id and cant:
                pres = ProductoPrecio.objects.get(id=pres_id)
                TransferenciaItem.objects.create(
                    transferencia=t,
                    presentacion_id=pres_id,
                    cantidad_unidades_base=int(cant) * pres.unidades_base,
                )
        messages.success(request, f'{t.numero} actualizada.')
        return redirect('compras:detalle_transferencia', t.id)

    items_edicion = [
        {
            'presentacion_id': item.presentacion_id,
            'producto_id': item.presentacion.producto_id,
            'cantidad': item.cantidad_unidades_base // (item.presentacion.unidades_base or 1),
        }
        for item in t.items.select_related('presentacion')
    ]
    return render(request, 'transferencias/form.html', {
        'transferencia': t,
        'almacenes': Almacen.objects.filter(activo=True),
        'items_edicion': items_edicion,
    })


@login_required
def detalle_transferencia(request, pk):
    t = get_object_or_404(Transferencia.objects.select_related('almacen_origen', 'almacen_destino', 'usuario')
                          .prefetch_related('items__presentacion__producto'), pk=pk)
    items_display = []
    for item in t.items.all():
        ub = item.presentacion.unidades_base or 1
        cant_pres = item.cantidad_unidades_base // ub
        items_display.append({
            'item': item,
            'cant_presentacion': cant_pres,
            'cant_base': item.cantidad_unidades_base,
        })
    return render(request, 'transferencias/detalle.html', {'transferencia': t, 'items_display': items_display})


@login_required
@require_POST
def anular_transferencia(request, pk):
    from django.db import transaction
    from django.utils import timezone
    t = get_object_or_404(Transferencia, pk=pk, estado='confirmada')
    try:
        with transaction.atomic():
            from productos.models import Inventario, Kardex
            for item in t.items.select_related('presentacion'):
                inv_origen, _ = Inventario.objects.get_or_create(
                    presentacion=item.presentacion, almacen=t.almacen_origen,
                    defaults={'stock_actual': 0}
                )
                inv_origen.stock_actual += item.cantidad_unidades_base
                inv_origen.save()
                Kardex.objects.create(
                    presentacion=item.presentacion,
                    almacen=t.almacen_origen,
                    tipo_movimiento='transferencia_anulada',
                    cantidad_entrada=item.cantidad_unidades_base,
                    stock_resultante=inv_origen.stock_actual,
                    referencia_tipo='transferencia',
                    referencia_id=t.id,
                    fecha=timezone.now(),
                )
                inv_destino = Inventario.objects.filter(
                    presentacion=item.presentacion, almacen=t.almacen_destino
                ).first()
                if inv_destino:
                    inv_destino.stock_actual -= item.cantidad_unidades_base
                    inv_destino.save()
                    Kardex.objects.create(
                        presentacion=item.presentacion,
                        almacen=t.almacen_destino,
                        tipo_movimiento='transferencia_anulada',
                        cantidad_salida=item.cantidad_unidades_base,
                        stock_resultante=inv_destino.stock_actual,
                        referencia_tipo='transferencia',
                        referencia_id=t.id,
                        fecha=timezone.now(),
                    )
            t.estado = 'anulada'
            t.save()
        messages.success(request, f'{t.numero} anulada. Stock revertido.')
    except Exception as e:
        messages.error(request, f'Error al anular: {e}')
    return redirect('compras:detalle_transferencia', pk)


@login_required
@require_POST
def confirmar_transferencia(request, pk):
    t = get_object_or_404(Transferencia, pk=pk, estado='borrador')
    try:
        t.confirmar()
        messages.success(request, f'{t.numero} confirmada. Stock actualizado.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('compras:detalle_transferencia', pk)


@login_required
def stock_inicial(request):
    if request.method == 'POST':
        from productos.models import ProductoPrecio
        pres_id = request.POST.get('presentacion')
        if not pres_id:
            messages.error(request, 'Debes seleccionar una presentación.')
            return redirect('compras:stock_inicial')
        si = StockInicial()
        si.presentacion_id = pres_id
        si.almacen_id = request.POST['almacen']
        prov_id = request.POST.get('proveedor')
        si.proveedor_id = prov_id if prov_id else None
        si.cantidad = request.POST['cantidad']
        si.costo_aproximado = request.POST.get('costo_aproximado') or 0
        si.registrado_por = request.user
        si.fecha = request.POST['fecha']
        si.save()
        si.aplicar()
        messages.success(request, f'Stock inicial de {si.presentacion.producto.nombre} aplicado correctamente.')
        return redirect('compras:stock_inicial')

    registros = StockInicial.objects.select_related('presentacion__producto', 'almacen', 'proveedor').order_by('-creado_en')[:30]
    return render(request, 'compras/stock_inicial.html', {
        'productos': Producto.objects.filter(estado__in=['activo', 'incompleto']).select_related('marca').order_by('nombre'),
        'almacenes': Almacen.objects.filter(activo=True),
        'proveedores': Proveedor.objects.filter(activo=True),
        'registros': registros,
    })



def presentaciones_ajax(request):
    prod_id = request.GET.get('producto_id')
    almacen_id = request.GET.get('almacen_id')
    from productos.models import ProductoPrecio, Inventario
    from django.db.models import Sum
    pres_qs = ProductoPrecio.objects.filter(producto_id=prod_id).values(
        'id', 'tipo_venta', 'unidades_base', 'precio_minorista'
    )
    pres_list = list(pres_qs)
    if almacen_id:
        total_base = Inventario.objects.filter(
            presentacion__producto_id=prod_id, almacen_id=almacen_id
        ).aggregate(t=Sum('stock_actual'))['t'] or 0
        for p in pres_list:
            p['stock'] = total_base // p['unidades_base'] if p['unidades_base'] else 0
    return JsonResponse({'presentaciones': pres_list})


def productos_por_almacen_ajax(request):
    almacen_id = request.GET.get('almacen_id')
    from productos.models import Inventario
    prod_ids = Inventario.objects.filter(
        almacen_id=almacen_id, stock_actual__gt=0
    ).values_list('presentacion__producto_id', flat=True).distinct()
    from productos.models import Producto
    productos = Producto.objects.filter(id__in=prod_ids, estado='activo').values('id', 'nombre').order_by('nombre')
    return JsonResponse({'productos': list(productos)})


def buscar_producto_ajax(request):
    q = request.GET.get('q', '')
    productos = Producto.objects.filter(
        nombre__icontains=q, estado__in=['activo', 'incompleto']
    ).values('id', 'nombre', 'codigo')[:10]
    return JsonResponse({'results': list(productos)})
