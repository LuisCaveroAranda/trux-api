# Guía para tomar fotos de entrenamiento (Fuegos Artificiales TRUX)

Cada producto ya tiene su carpeta creada sola en `API/media/dataset_entrenamiento/<codigo>/`
al registrarlo en el sistema. Solo hay que arrastrar las fotos ahí, sin renombrar nada.

## Por qué falló la prueba anterior

Las fotos de cada producto se tomaron en una sola sesión (mismo fondo, misma luz).
El modelo "memorizó" esas condiciones en vez de aprender a reconocer la caja en
cualquier condición. La validación marcó 100% porque comparó fotos de esa MISMA
sesión — no porque funcione con una foto nueva. La variedad es más importante que
la cantidad.

## Cantidad

- Mínimo para que el script no descarte la carpeta: 20 fotos.
- Meta real por producto: 80–150 fotos.
- Forma rápida de llegar ahí: grabar un video corto (30–60 segundos) rotando la
  caja frente a la cámara, y de ahí sacar frames cada pocos fotogramas, en vez de
  tomar foto por foto.

## Variedad (esto es lo que más importa)

Repartir las fotos de cada producto en **al menos 3 sesiones distintas**, variando
cada vez:

- **Fondo**: mesa, piso, repisa, una tela, el mostrador — no siempre el mismo lugar.
- **Luz**: de día con luz natural, de noche con foco/luz artificial, con sombra parcial.
- **Distancia**: de cerca (llenando el cuadro) y de más lejos (como la sostendría
  alguien al mostrarla a la cámara del celular real).
- **Ángulo**: de frente, de lado, ligeramente inclinada — siempre mostrando la cara
  de la caja con el diseño/etiqueta visible (eso es lo que el modelo usa para
  distinguir un producto de otro).

## Qué evitar

- No tomar las 80-150 fotos en una sola sesión corrida — eso fue justo el problema.
- No tapar el diseño/etiqueta de la caja con la mano.
- No usar siempre el mismo fondo para un producto y otro fondo distinto para otro
  producto — si no, el modelo puede aprender a reconocer el fondo en vez de la caja.
- Evitar fotos borrosas por movimiento.

## Repetir por cada uno de los ~60 productos

El mismo criterio aplica a todos. Cuantos más productos tengan fotos variadas,
más fácil le resulta al modelo distinguir entre cajas parecidas.
