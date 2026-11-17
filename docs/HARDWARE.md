# Hardware evidence / Evidencia física

## English

Version 0.2.0 adds native-raster text planning on the same geometry/pitch path as images. No new physical hardware run was performed for text. This software addition does not change the evidence or completion limitations below.

The initial calibration comes from earlier experiments with one U1 printer, firmware reported as `1.0.1E`, controlled from a Windows PC over Bluetooth Classic. It is a starting point for that setup, not a factory specification or a guarantee for all U1 devices.

For 50 × 25 mm die-cut labels with a measured 2 mm gap:

| Parameter | Starting value |
| --- | --- |
| Head width | 384 dots |
| Raster scale | 8 dots/mm |
| Movement scale | 8 units/mm; 1 unit per bitmap row |
| Darkness / energy / speed | 5 / 8000 / 10 (protocol values) |
| Margin / horizontal offset / vertical offset | 2 mm / +2 mm / −0.25 mm |
| Example 548 × 246 image | Fit 352 × 158 at x=32, y=19 |
| Label pitch | (25 + 2) × 8 = 216 units |

With the original sample images, trailing white-row trimming produced 174 rows, followed by 42 advance units. **Those two values are content-dependent**; the SDK calculates them per image. Only the pitch is fixed by this roll/calibration.

An operator confirmed consistent positioning across a five-label legacy run. A subsequent eight-label legacy run was reported to miss its final label and leave the paper out of alignment. The exact cause was not established. That legacy script added final feed commands and a status query, and used a fixed final wait.

This SDK removes those additional final movements/queries, keeps initialization once per session, honors flow control, and uses a conservative passive wait based on travel. Software tests verify these behaviors. **The revised SDK has not yet completed a physical acceptance run.** These changes are not proof that the missing final label or final alignment issue is solved.

There is no verified per-label physical completion acknowledgment for this adapter. `transmitted_unconfirmed`, `position_after="expected_next_label_start"`, and elapsed waiting time are software estimates. They are never sensor measurements or delivery proof. No hardware printing is performed by CI or package builds.

## Español

La versión 0.2.0 añade preparación de texto ráster nativo sobre la misma geometría/paso de imágenes. No se realizó otra impresión física para texto. La función de software no cambia la evidencia ni las limitaciones de entrega descritas aquí.

La calibración inicial procede de experimentos anteriores con una U1, firmware reportado `1.0.1E`, desde Windows por Bluetooth Classic. Es un punto de partida para esa unidad; no es una especificación del fabricante ni garantiza todas las variantes U1.

El rollo usado tenía etiquetas precortadas de **50 × 25 mm**, con **2 mm de separación**. La tabla anterior resume los valores. Para una imagen de 548 × 246 píxeles, el diseño resultó de 352 × 158 puntos en x=32, y=19. Las imágenes originales generaban 174 filas y 42 unidades de avance, sumando un paso de 216. **Las filas y el avance dependen del contenido**: el SDK los calcula para cada imagen y tamaño.

El operador confirmó una posición consistente en cinco etiquetas del programa anterior. En un lote posterior de ocho informó que faltó la última y el papel quedó fuera de la separación. La causa exacta no se estableció. El programa anterior añadía avances finales, consulta de estado y una espera fija.

El SDK elimina esos movimientos y consultas adicionales al cerrar, inicializa una vez por sesión, respeta el control de flujo y espera de forma pasiva según el recorrido estimado. Las pruebas de software comprueban ese comportamiento. **El ciclo nuevo todavía no ha pasado una prueba física completa**; no se presenta como una solución física ya confirmada.

No existe confirmación física verificable por etiqueta en este adaptador. `transmitted_unconfirmed`, `position_after="expected_next_label_start"` y la espera transcurrida son estimaciones de software. No son mediciones del sensor ni prueba de entrega. CI y la compilación no imprimen papel.
