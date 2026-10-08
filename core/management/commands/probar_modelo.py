"""
Prueba el modelo entrenado (API/entrenamiento/modelo.keras) en tiempo real con la
camara de la PC, o sobre una imagen suelta, y muestra las presentaciones del
producto identificado con su precio de costo y precio de venta (consultados en
la base de datos real, no inventados).

Usa la misma logica que el endpoint /chat/app-reconocer/ (core/reconocimiento.py),
para que un bug arreglado aqui tambien quede arreglado alla.

Uso:
    python manage.py probar_modelo                  -> abre la camara
    python manage.py probar_modelo ruta/foto.jpg     -> prueba con una imagen
"""
import cv2
from django.core.management.base import BaseCommand

from core.reconocimiento import UMBRAL_CONFIANZA, modelo_disponible, obtener_info_producto, reconocer_frame


def formatear_presentacion(p):
    costo = f"S/{p['precio_costo']}" if p['precio_costo'] is not None else 'sin costo'
    venta_min = f"S/{p['precio_venta_minorista']}" if p['precio_venta_minorista'] is not None else 'sin precio'
    venta_may = f"S/{p['precio_venta_mayorista']}" if p['precio_venta_mayorista'] is not None else 'sin precio'
    return f"{p['tipo_venta']}: costo {costo} | venta minorista {venta_min} | venta mayorista {venta_may}"


class Command(BaseCommand):
    help = 'Prueba el modelo de reconocimiento entrenado con la camara o con una imagen suelta.'

    def add_arguments(self, parser):
        parser.add_argument('imagen', nargs='?', default=None, help='Ruta a una imagen para probar en vez de la camara')

    def handle(self, *args, **options):
        if not modelo_disponible():
            self.stderr.write('No encontre el modelo entrenado. Corre primero "python entrenar.py" en la carpeta entrenamiento/.')
            return

        self.stdout.write('Cargando modelo...')

        def imprimir_resultado(codigo, confianza):
            if confianza < UMBRAL_CONFIANZA:
                self.stdout.write(f'No reconocido (confianza {confianza:.0%})')
                return
            info = obtener_info_producto(codigo)
            if not info:
                self.stdout.write(f'{codigo} no existe en el catalogo (confianza {confianza:.0%})')
                return
            self.stdout.write(f"\n{info['nombre']} ({codigo}) - confianza {confianza:.0%}")
            for p in info['presentaciones']:
                self.stdout.write(f'  {formatear_presentacion(p)}')

        imagen_path = options.get('imagen')
        if imagen_path:
            frame = cv2.imread(imagen_path)
            if frame is None:
                self.stderr.write(f'No se pudo abrir la imagen: {imagen_path}')
                return
            codigo, confianza = reconocer_frame(frame)
            imprimir_resultado(codigo, confianza)
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stderr.write('No se pudo abrir la camara.')
            return
        self.stdout.write('Camara abierta. Presiona Q para salir.')

        ultimo_codigo = None
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            codigo, confianza = reconocer_frame(frame)
            lineas = []
            color = (0, 0, 255)

            if confianza >= UMBRAL_CONFIANZA:
                info = obtener_info_producto(codigo)
                if info:
                    color = (0, 200, 0)
                    lineas.append(f"{info['nombre']} ({confianza:.0%})")
                    for p in info['presentaciones']:
                        lineas.append(formatear_presentacion(p))
                    if codigo != ultimo_codigo:
                        imprimir_resultado(codigo, confianza)
                        ultimo_codigo = codigo
                else:
                    lineas.append(f'{codigo} no esta en el catalogo')
                    ultimo_codigo = None
            else:
                lineas.append(f'No reconocido ({confianza:.0%})')
                ultimo_codigo = None

            y = 30
            for linea in lineas:
                cv2.putText(frame, linea, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y += 26

            cv2.imshow('Probar modelo - Fuegos Artificiales TRUX', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
