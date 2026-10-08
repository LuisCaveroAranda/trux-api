from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from decimal import Decimal

from .models import Venta, VentaItem
from clientes.models import Cliente
from core.models import Almacen
from productos.models import Producto, ProductoPrecio


@login_required
def lista_ventas(request):
    qs = Venta.objects.select_related('almacen', 'cliente', 'registrado_por').order_by('-creado_en')
    estado = request.GET.get('estado')
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, 'ventas/lista.html', {
        'ventas': qs,
        'estados': Venta.ESTADO_CHOICES,
    })


@login_required
def crear_venta(request):
    if request.method == 'POST':
        venta = _guardar_venta(request, None)
        messages.success(request, f'{venta.numero} creada.')
        return redirect('ventas:detalle', venta.id)
    return render(request, 'ventas/form.html', _contexto_venta(None))


@login_required
def editar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk, estado='borrador')
    if request.method == 'POST':
        _guardar_venta(request, venta)
        messages.success(request, 'Venta actualizada.')
        return redirect('ventas:detalle', venta.id)
    return render(request, 'ventas/form.html', _contexto_venta(venta))


@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related('almacen', 'cliente', 'registrado_por')
        .prefetch_related('items__presentacion__producto'),
        pk=pk
    )
    return render(request, 'ventas/detalle.html', {'venta': venta})


@login_required
@require_POST
def confirmar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk, estado='borrador')
    try:
        venta.confirmar()
        messages.success(request, f'{venta.numero} confirmada. Stock actualizado.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('ventas:detalle', pk)


@login_required
@require_POST
def anular_venta(request, pk):
    from django.db import transaction
    from django.utils import timezone
    from productos.models import Inventario, Kardex
    venta = get_object_or_404(Venta, pk=pk, estado='confirmada')
    try:
        with transaction.atomic():
            for item in venta.items.select_related('presentacion__producto'):
                unidades = item.cantidad * item.presentacion.unidades_base
                invs = Inventario.objects.filter(
                    presentacion__producto=item.presentacion.producto,
                    almacen=venta.almacen,
                ).order_by('stock_actual')
                restante = unidades
                for inv in invs:
                    if restante <= 0:
                        break
                    inv.stock_actual += restante
                    inv.save()
                    restante = 0
                stock_final = Inventario.objects.filter(
                    presentacion__producto=item.presentacion.producto,
                    almacen=venta.almacen,
                ).values_list('stock_actual', flat=True).first() or 0
                Kardex.objects.create(
                    presentacion=item.presentacion,
                    almacen=venta.almacen,
                    tipo_movimiento='venta_anulada',
                    cantidad_entrada=unidades,
                    stock_resultante=stock_final,
                    referencia_tipo='venta',
                    referencia_id=venta.id,
                    fecha=timezone.now(),
                )
            venta.estado = 'anulada'
            venta.save()
        messages.success(request, f'{venta.numero} anulada. Stock devuelto.')
    except Exception as e:
        messages.error(request, f'Error al anular: {e}')
    return redirect('ventas:detalle', pk)


def _contexto_venta(venta):
    return {
        'venta': venta,
        'clientes': Cliente.objects.filter(activo=True).order_by('nombre'),
        'almacenes': Almacen.objects.filter(activo=True),
        'productos': Producto.objects.filter(estado='activo').select_related('marca').order_by('nombre'),
    }


def _guardar_venta(request, venta):
    data = request.POST
    if not venta:
        venta = Venta()
        venta.registrado_por = request.user

    venta.tipo = data['tipo']
    venta.fecha = data['fecha']
    venta.almacen_id = data['almacen']
    venta.observaciones = data.get('observaciones', '')

    cliente_id = data.get('cliente')
    if cliente_id:
        venta.cliente_id = cliente_id
        venta.cliente_nombre = ''
    else:
        venta.cliente = None
        venta.cliente_nombre = data.get('cliente_nombre', '').strip()

    venta.save()
    venta.items.all().delete()

    presentacion_ids = data.getlist('item_presentacion')
    cantidades = data.getlist('item_cantidad')
    precios = data.getlist('item_precio')

    subtotal = Decimal('0')
    for i, pres_id in enumerate(presentacion_ids):
        if not pres_id:
            continue
        cantidad = int(cantidades[i]) if i < len(cantidades) and cantidades[i] else 0
        precio = Decimal(precios[i]) if i < len(precios) and precios[i] else Decimal('0')
        if not cantidad or not precio:
            continue
        VentaItem.objects.create(
            venta=venta,
            presentacion_id=pres_id,
            cantidad=cantidad,
            precio_unitario=precio,
        )
        subtotal += Decimal(str(cantidad)) * precio

    IGV_RATE = Decimal('0.18')
    if venta.tipo in ('boleta', 'factura'):
        igv = (subtotal / Decimal('1.18') * IGV_RATE).quantize(Decimal('0.01'))
    else:
        igv = Decimal('0')

    venta.subtotal = subtotal
    venta.igv = igv
    venta.total = subtotal
    venta.save()
    return venta
