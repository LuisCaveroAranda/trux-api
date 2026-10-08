# CONTEXTO DEL PROYECTO — SISTEMA COMERCIAL CHARITO
> Pega este documento completo en Claude Code para continuar el desarrollo
> sin necesidad de explicar nada desde cero.

---

## 1. RESUMEN DEL PROYECTO

Sistema web comercial para negocio de mercería/hogar en Perú.
El núcleo del sistema es un **chat con IA llamado "Charito"** que ayuda
a vendedores (con precios y costos) y clientes (solo precios y cotizaciones).

---

## 2. STACK TECNOLÓGICO

| Capa | Tecnología |
|---|---|
| Backend | Python + Django + Django REST Framework |
| Base de datos | PostgreSQL |
| Chat IA | Anthropic API (claude-haiku-4-5) — intercambiable por config |
| Frontend | Django Templates + JS vanilla para empezar |
| Servidor | AWS EC2 (ya disponible) |
| Acceso | IP directa por ahora, dominio después |
| Autenticación | Django Auth personalizado con roles |
| Storage fotos | Local por ahora, Cloudinary después |

---

## 3. ROLES DEL SISTEMA

| Rol | Permisos |
|---|---|
| admin | Acceso total, configuración, usuarios |
| supervisor | Reportes, descuentos, anulaciones |
| vendedor | Ventas, cobros, chat IA con precios y costos |
| almacenero | Compras, stock, transferencias |
| cliente | Chat IA solo precios, cotizaciones, sus pedidos |

---

## 4. INFRAESTRUCTURA

- Servidor: AWS EC2 ya configurado
- Sin dominio por ahora → acceso por IP: `http://IP:8000`
- Solo Perú, un solo idioma: español
- HTTPS después cuando haya dominio
- Backup después
- Un solo programador (el dueño del negocio)

---

## 5. MÓDULOS Y ORDEN DE DESARROLLO

### FASE 1 — PRIORITARIA (arrancar aquí)
1. Configuración Django + PostgreSQL + estructura base
2. Registro de productos completo
3. Stock inicial por almacén
4. Registro de proveedores
5. Guías de compra con cálculo de flete

### FASE 2 — SIGUIENTE
6. Chat IA Charito (Anthropic API)
7. Cotizaciones con flujo cliente-vendedor

### FASE 3 — DESPUÉS
8. Ventas, boletas y facturas
9. Devoluciones
10. Transferencias entre almacenes
11. Reportes y dashboards
12. SUNAT API (cuando tenga RUC 20)

---

## 6. REGLAS DE NEGOCIO IMPORTANTES

### Productos
- Código automático formato: `PRO-00000001`
- Cada producto tiene múltiples **presentaciones** (Unidad, Docena, Caja, etc.)
- El stock se maneja en **unidades base** (la unidad mínima del producto)
- Cada presentación define cuántas unidades base equivale
- Ejemplo: Docena = 12 unidades base, Caja x5 doc = 60 unidades base
- Hasta 4 fotos por producto, una es la principal
- Si no hay foto → mostrar imagen por defecto
- Campo `aliases` separado por comas para búsqueda en chat IA
- Estado del producto: `activo`, `inactivo`, `incompleto`
- Producto incompleto: se crea rápido desde compra, se completa después
- Campos personalizados opcionales (color, material, etc.)
- Etiquetas opcionales para agrupar productos libremente

### Fracciones
- Solo algunos productos permiten fracción
- Las fracciones se definen manualmente en el producto, NO se calculan
- Ejemplo: Algodón paquete x13 → mitad = 6 unidades (no 6.5)
- Docenas y paquetes: pueden tener mitad y/o cuarto
- Cajones/Cajas: solo hasta la mitad
- Unidades sueltas: nunca fracción
- El vendedor puede modificar el precio sugerido de la fracción

### Precios
- Cada presentación tiene precio **minorista** y **mayorista**
- El cajero/vendedor decide qué precio aplicar línea por línea
- Puede dar descuento puntual por línea en el momento
- El vendedor puede modificar cualquier precio final
- Todo cambio de precio queda registrado con quién y cuándo
- No hay límite de descuento por ahora

### Stock
- Stock en **unidades base** por almacén (no por presentación)
- 3 almacenes actualmente, con opción de agregar más
- Alerta cuando stock baja del mínimo configurado por producto
- Vista de stock puede mostrar en unidades base o convertido a presentaciones
- Productos sin movimiento: alerta configurable (algunos son de movimiento lento normal)

### Proveedores y Costos
- Múltiples proveedores por producto
- Historial de costos — nunca sobreescribir, siempre nueva entrada
- Costo directo = costo producto + flete proveedor proporcional + flete agencia proporcional
- Costo real = costo directo + gastos fijos mensuales proporcionales
- El chat IA muestra ambos costos al vendedor

### Guías de Compra
- 3 tipos: `con_documento`, `sin_documento`, `mercado`
- Todas tienen: quién registró, almacén destino, forma de pago
- **Flete proveedor**: monto fijo que cobra el proveedor (S/15, S/20, S/50, etc.)
- **Flete agencia**: se calcula por bultos
  - Cada item indica cuántas cajas van por bulto
  - Sistema calcula: CEIL(cantidad / cajas_por_bulto) = num_bultos
  - Flete agencia item = num_bultos × precio_por_bulto
  - precio_por_bulto se define una vez para toda la guía
- Flete se distribuye proporcionalmente entre items para calcular costo directo
- Se puede modificar la guía antes de confirmarla (con historial de cambios)
- Al confirmar → actualiza stock e historial de costos automáticamente
- Si producto no existe → crear producto mínimo desde la guía (estado: incompleto)

### Ventas (Fase 3)
- Tipos: boleta, factura, nota_pedido
- Correlativo automático por serie
- Pagos combinados: efectivo + Yape + transferencia en una misma venta
- Vuelto automático cuando pagan en efectivo
- Comprobante en PDF (no impresión física)
- IGV 18% separado en facturas
- Vendedor puede anular con motivo obligatorio
- Devoluciones hasta 15 días, opcional, puede o no regresar al stock

### Cotizaciones (Fase 2)
- Número automático formato: `COT-00000001`
- Cliente cotiza por chat IA → vendedor responde dentro del sistema
- Vendedor puede modificar precios antes de responder
- Cliente elige tipo de pago y hora de recojo en la cotización
- Al aceptar → se convierte en venta
- También el vendedor puede crear cotizaciones manualmente

### Chat IA Charito
- Nombre del asistente: **Charito**
- Vendedor: ve precios minorista, mayorista Y costos (directo y real)
- Cliente: solo ve precios de venta, sin costos
- Chat 24/7 para clientes
- Vendedor disponible 8am a 7pm; fuera de horario el chat avisa
- Todas las conversaciones se guardan siempre (para mejorar el sistema)
- Cliente puede calificar el chat del 1 al 5
- Respuestas predefinidas para preguntas frecuentes
- Palabras prohibidas configurables
- El chat muestra foto principal del producto cuando está disponible
- Pantalla del vendedor: chat a la izquierda, cotización/venta a la derecha
- Desde el chat el vendedor agrega productos directamente a la cotización

### Proveedor IA intercambiable
```python
# settings.py — para cambiar de proveedor sin tocar nada más
AI_PROVIDER = "anthropic"
AI_MODEL = "claude-haiku-4-5-20251001"
AI_API_KEY = env("ANTHROPIC_API_KEY")
```

---

## 7. CASOS ESPECIALES

### Producto de transformación (naftalinas)
- Entra materia prima (bolsa de 25kg) → salen productos terminados (bolsas de 60 bolitas)
- Se registra cuántas bolsas de 60 bolitas salieron ese día
- El sistema descuenta la materia prima y agrega el producto terminado al stock

### Stock inicial
- Productos que ya existen antes de usar el sistema
- Se registran con: producto, proveedor opcional, cantidad, costo aproximado
- El kardex los registra como tipo: `stock_inicial`

### Ajustes de inventario
- Tipos: merma, consumo_interno, remate, diferencia_conteo, vencimiento
- Motivo obligatorio en todos los casos

### Forma de pago en compras
- Caja del negocio, adelanto del dueño, o combinado
- Los adelantos del dueño quedan registrados para reembolso posterior

---

## 8. BASE DE DATOS

**Motor**: PostgreSQL 15+
**Archivo SQL completo**: `base_de_datos_charito.sql` (adjunto)

### Tablas principales (46 en total):
```
empresa, configuracion, roles, usuarios, clientes
almacenes, usuario_almacenes
categorias, subcategorias, marcas, etiquetas
productos, producto_fotos, producto_campos, producto_etiquetas
producto_precios, producto_precio_fracciones
proveedores, producto_proveedor, proveedor_calificaciones
inventario, kardex
compras, compra_items, compra_historial
gastos_categorias, gastos_fijos, activos_fijos
costo_real_mensual, adelantos_dueno
series_comprobantes, ventas, venta_items
venta_historial_precios, venta_pagos
devoluciones, devolucion_items
cotizaciones, cotizacion_items
transferencias, transferencia_items
ajustes_inventario
transformaciones, transformacion_entradas, transformacion_salidas
chat_conversaciones, chat_mensajes
palabras_prohibidas_chat, respuestas_predefinidas
notificaciones
```

### Vistas ya creadas:
```
v_stock_total           — stock sumado de todos los almacenes
v_stock_por_almacen     — stock con estado OK/ALERTA/SIN STOCK
v_costo_promedio        — costo promedio ponderado por producto
v_ventas_hoy            — ventas del día actual
v_proximos_a_vencer     — productos que vencen en 30 días
```

---

## 9. CONFIGURACIÓN INICIAL YA EN BASE DE DATOS

### Roles insertados:
- admin, supervisor, vendedor, almacenero, cliente

### Series de comprobantes:
- B001 (boleta), F001 (factura), COT (cotización), NP (nota pedido)

### Categorías de gastos:
- Alquiler local, Alquiler almacén, Sueldos, Luz, Agua, Internet,
  Teléfono, Movilidad, Útiles de oficina, Reparaciones, Otros

### Configuraciones del sistema:
- nombre_asistente = Charito
- horario_atencion_inicio = 08:00
- horario_atencion_fin = 19:00
- dias_max_devolucion = 15
- igv_porcentaje = 18
- moneda = PEN

---

## 10. INSTRUCCIONES PARA CLAUDE CODE

### Lo que debes hacer primero:

1. **Crear el proyecto Django**
```bash
pip install django djangorestframework psycopg2-binary python-decouple pillow anthropic
django-admin startproject charito_project
cd charito_project
```

2. **Crear las apps Django**
```bash
python manage.py startapp productos
python manage.py startapp compras
python manage.py startapp ventas
python manage.py startapp clientes
python manage.py startapp chat_ia
python manage.py startapp reportes
```

3. **Ejecutar el SQL de la base de datos**
- Crear la BD en PostgreSQL
- Ejecutar el archivo `base_de_datos_charito.sql`
- Configurar Django para que use esas tablas (managed = False en los modelos
  o generar migraciones desde cero)

4. **Arrancar con la Fase 1:**
   - Modelos Django para todas las tablas
   - Panel admin Django para gestión rápida
   - Vistas y formularios para:
     - Registro de productos con presentaciones y fracciones
     - Carga de stock inicial
     - Registro de proveedores
     - Registro de guías de compra con cálculo de flete automático

### Variables de entorno (.env):
```
SECRET_KEY=tu_secret_key
DEBUG=True
DB_NAME=charito_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
ANTHROPIC_API_KEY=tu_api_key_aqui
AI_MODEL=claude-haiku-4-5-20251001
```

### Consideraciones técnicas:
- Usar `python-decouple` para variables de entorno
- Señales Django (signals) para actualizar kardex automáticamente al confirmar compra
- Señales para actualizar inventario al confirmar venta
- El cálculo de bultos: `import math; math.ceil(cantidad / cajas_por_bulto)`
- El cálculo de flete proporcional: por valor de mercadería de cada item
- Código automático de producto: trigger o lógica en el modelo `save()`
- Para el chat IA: endpoint DRF que recibe mensaje, consulta precios de BD,
  llama a Anthropic API con contexto del producto, devuelve respuesta

---

## 11. PANTALLA PRINCIPAL DEL VENDEDOR (REFERENCIA UI)

```
+---------------------------+---------------------------+
|   Chat Charito (IA)       |   Cotización / Venta      |
|---------------------------|---------------------------|
| Vendedor: precio          | Cliente: [selector]       |
|   escobilla docena        |---------------------------|
|                           | Escobilla docena x1       |
| Charito:                  | Mayor  S/1.70  [x] [editar|
|  Minorista: S/2.00 [+]   |                           |
|  Mayorista: S/1.70 [+]   | Imperdible N3 x2          |
|  Costo dir: S/1.30        | Menor  S/2.50  [x] [editar|
|  Stock: 180 und           |---------------------------|
|                           | Total: S/6.90             |
| [escribir mensaje...]     | [PDF/Cotiz] [Cobrar]      |
+---------------------------+---------------------------+
```

---

## 12. NOTAS FINALES

- El negocio está en Perú, moneda soles (PEN)
- RUC 10 por ahora (persona natural), después RUC 20 (empresa)
- SUNAT API se conectará después en Fase 3
- WhatsApp Business API puede integrarse después para cotizaciones
- Delivery deshabilitado en UI pero estructura lista en BD
- El sistema debe ser mobile-friendly (vendedores usan celular)
- Idioma: solo español

---
*Documento generado desde conversación de requerimientos completa.*
*Todo lo aquí descrito fue definido y aprobado por el dueño del negocio.*
