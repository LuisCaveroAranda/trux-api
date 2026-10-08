"""
Reconocimiento de productos a partir de una foto, usando el modelo entrenado
en API/entrenamiento/modelo.keras. Reutilizado por el comando de prueba
(manage.py probar_modelo) y por el endpoint /chat/app-reconocer/.
"""
import json
import os
import threading

import cv2
import numpy as np
from django.conf import settings

IMG_SIZE = (224, 224)
UMBRAL_CONFIANZA = 0.65
ENTRENAMIENTO_DIR = os.path.join(settings.BASE_DIR, 'entrenamiento')

_modelo = None
_labels = None
_lock = threading.Lock()


def _cargar():
    global _modelo, _labels
    if _modelo is None:
        with _lock:
            if _modelo is None:
                from tensorflow.keras.models import load_model
                modelo_path = os.path.join(ENTRENAMIENTO_DIR, 'modelo.keras')
                labels_path = os.path.join(ENTRENAMIENTO_DIR, 'labels.json')
                _modelo = load_model(modelo_path)
                with open(labels_path, encoding='utf-8') as f:
                    _labels = json.load(f)
    return _modelo, _labels


def modelo_disponible():
    modelo_path = os.path.join(ENTRENAMIENTO_DIR, 'modelo.keras')
    labels_path = os.path.join(ENTRENAMIENTO_DIR, 'labels.json')
    return os.path.exists(modelo_path) and os.path.exists(labels_path)


def reconocer_frame(frame_bgr):
    """Recibe una imagen ya decodificada (formato BGR de OpenCV) y devuelve (codigo, confianza)."""
    modelo, labels = _cargar()
    # El modelo ya incluye preprocess_input internamente (ver entrenamiento/entrenar.py),
    # asi que aqui se le pasa la imagen cruda en RGB, sin normalizar de nuevo.
    img = cv2.resize(frame_bgr, IMG_SIZE)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
    x = np.expand_dims(img, axis=0)
    pred = modelo.predict(x, verbose=0)[0]
    idx = int(np.argmax(pred))
    return labels[str(idx)], float(pred[idx])


def reconocer_bytes(imagen_bytes):
    """Recibe los bytes crudos de una foto (jpg/png) y devuelve (codigo, confianza)."""
    arr = np.frombuffer(imagen_bytes, dtype=np.uint8)
    frame_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame_bgr is None:
        return None, 0.0
    return reconocer_frame(frame_bgr)


def obtener_info_producto(codigo):
    from productos.models import Producto

    try:
        producto = Producto.objects.prefetch_related('presentaciones__costos_proveedor').get(codigo=codigo)
    except Producto.DoesNotExist:
        return None

    presentaciones = []
    for pres in producto.presentaciones.all():
        costo_obj = pres.costos_proveedor.order_by('-creado_en').first()
        costo = None
        if costo_obj:
            costo = costo_obj.costo_con_flete if costo_obj.costo_con_flete is not None else costo_obj.costo
        presentaciones.append({
            'tipo_venta': pres.tipo_venta,
            'precio_costo': costo,
            'precio_venta_minorista': pres.precio_minorista,
            'precio_venta_mayorista': pres.precio_mayorista,
        })
    return {'nombre': producto.nombre, 'codigo': producto.codigo, 'presentaciones': presentaciones}
