"""
Entrena el modelo de reconocimiento de productos para Fuegos Artificiales TRUX.

Lee las fotos desde API/media/dataset_entrenamiento/<codigo_producto>/
(esas carpetas se crean solas al crear un producto en el sistema; las fotos
las pone el usuario manualmente ahi).

Uso:
    python entrenar.py
"""
import json
import os
import random

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, '..', 'media', 'dataset_entrenamiento')
IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 20
VALIDATION_SPLIT = 0.2
MIN_FOTOS_POR_CLASE = 20  # carpetas con menos fotos que esto se ignoran (aun no listas)
EXTENSIONES = ('.jpg', '.jpeg', '.png')


def listar_clases_listas():
    clases = []
    for nombre in sorted(os.listdir(DATASET_DIR)):
        carpeta = os.path.join(DATASET_DIR, nombre)
        if not os.path.isdir(carpeta):
            continue
        n_fotos = len([f for f in os.listdir(carpeta) if f.lower().endswith(EXTENSIONES)])
        if n_fotos >= MIN_FOTOS_POR_CLASE:
            clases.append(nombre)
        else:
            print(f'  omitido {nombre}: {n_fotos} fotos (minimo {MIN_FOTOS_POR_CLASE})')
    return clases


def construir_lista_archivos(clases):
    rutas, etiquetas = [], []
    for idx, nombre in enumerate(clases):
        carpeta = os.path.join(DATASET_DIR, nombre)
        for archivo in os.listdir(carpeta):
            if archivo.lower().endswith(EXTENSIONES):
                rutas.append(os.path.join(carpeta, archivo))
                etiquetas.append(idx)
    combinados = list(zip(rutas, etiquetas))
    random.Random(123).shuffle(combinados)
    rutas, etiquetas = zip(*combinados)
    return list(rutas), list(etiquetas)


def cargar_imagen(ruta, etiqueta):
    contenido = tf.io.read_file(ruta)
    img = tf.image.decode_image(contenido, channels=3, expand_animations=False)
    img = tf.image.resize(img, IMG_SIZE)
    return img, etiqueta


def construir_modelo(num_clases):
    aumentos = tf.keras.Sequential([
        layers.RandomFlip('horizontal'),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.15),
        layers.RandomBrightness(0.15),
    ])

    base = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet')
    base.trainable = False

    entradas = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = aumentos(entradas)
    x = preprocess_input(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    salidas = layers.Dense(num_clases, activation='softmax')(x)
    return models.Model(entradas, salidas)


def main():
    print('Buscando productos con suficientes fotos...')
    clases = listar_clases_listas()
    if len(clases) < 2:
        print('Se necesitan al menos 2 productos con suficientes fotos para entrenar. Aborto.')
        return
    print(f'Entrenando con {len(clases)} productos: {clases}')

    rutas, etiquetas = construir_lista_archivos(clases)
    n_val = max(1, int(len(rutas) * VALIDATION_SPLIT))
    rutas_val, etiquetas_val = rutas[:n_val], etiquetas[:n_val]
    rutas_train, etiquetas_train = rutas[n_val:], etiquetas[n_val:]
    print(f'Fotos totales: {len(rutas)} (entrenamiento: {len(rutas_train)}, validacion: {len(rutas_val)})')

    train_ds = tf.data.Dataset.from_tensor_slices((rutas_train, etiquetas_train))
    train_ds = train_ds.map(cargar_imagen, num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.shuffle(500).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    val_ds = tf.data.Dataset.from_tensor_slices((rutas_val, etiquetas_val))
    val_ds = val_ds.map(cargar_imagen, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    labels = {str(i): nombre for i, nombre in enumerate(clases)}
    with open(os.path.join(BASE_DIR, 'labels.json'), 'w', encoding='utf-8') as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    modelo = construir_modelo(len(clases))
    modelo.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    modelo.summary()

    callback_early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_accuracy', patience=4, restore_best_weights=True
    )
    modelo.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=[callback_early_stop])

    modelo.save(os.path.join(BASE_DIR, 'modelo.keras'))
    print(f'\nListo. modelo.keras y labels.json guardados en {BASE_DIR}')


if __name__ == '__main__':
    main()
