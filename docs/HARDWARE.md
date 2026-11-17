# Hardware evidence / Evidencia física

## English

Post-release observations on 2026-11-17: a native-raster text proof was visually checked as complete and centered. A separate logo-plus-variable-text proof was also checked as complete. Finally, the operator confirmed that **all five consecutive numbered mixed labels printed correctly**, including the last label, with consistent placement. The mixed artwork was composed in the host application from fixed assets and external string fields, then sent through the public SDK image-plan API. These host templates and private artwork are not bundled SDK features/assets.

This verifies one short batch on this U1/Windows setup with 50 × 25 mm media, a 2 mm gap and darkness 5/5. It does not verify longer runs, other sizes/models, or the final roll origin. The batch used one initialization, 216-unit pitch per label, no additional final eject/query, 135 mm total planned travel, and the default passive wait. The completion report was `transmitted_unconfirmed` until the operator supplied the result; no automatic physical acknowledgment was discovered.

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

This SDK removes those additional final movements/queries, keeps initialization once per session, honors flow control, and uses a conservative passive wait based on travel. The post-release five-label run confirms complete output and placement for that short batch. The earlier legacy eight-label incident remains a separate observation; final roll-origin behavior and longer runs still need acceptance testing.

An earlier mixed single-label attempt was incomplete; the operator subsequently reported that the media roll ran out and appeared to lose traction. The full encoded raster contained the missing fields. After replacement/alignment, the repeated single-label proof and five-label batch were accepted. Another text proof was superimposed on earlier artwork; its cause was not established. Neither incident was used to claim a verified firmware diagnosis.

There is no verified per-label physical completion acknowledgment for this adapter. `transmitted_unconfirmed`, `position_after="expected_next_label_start"`, and elapsed waiting time are software estimates. They are never sensor measurements or delivery proof. No hardware printing is performed by CI or package builds.

## Español

Observaciones posteriores a la publicación, del 17/11/2026: se revisó una prueba de texto nativo completa y centrada, y otra de logo con campos variables completa. Después, el operador confirmó que **las cinco etiquetas mixtas consecutivas salieron correctamente**, incluida la última y sin desplazamiento observado. La aplicación externa compuso logo y campos de texto y los entregó al SDK mediante su API pública de imágenes; esas plantillas y recursos privados no forman parte del paquete.

Esto valida un lote corto en esta U1/Windows con papel de 50 × 25 mm, separación de 2 mm y oscuridad 5/5. No verifica lotes largos, otros tamaños/modelos ni el origen final del rollo. Se usó una inicialización, paso de 216 unidades, sin expulsión/consulta final adicional, recorrido calculado de 135 mm y espera pasiva predeterminada. El comprobante permaneció `transmitted_unconfirmed` hasta la confirmación del operador; no se encontró una confirmación física automática.

La calibración inicial procede de experimentos anteriores con una U1, firmware reportado `1.0.1E`, desde Windows por Bluetooth Classic. Es un punto de partida para esa unidad; no es una especificación del fabricante ni garantiza todas las variantes U1.

El rollo usado tenía etiquetas precortadas de **50 × 25 mm**, con **2 mm de separación**. La tabla anterior resume los valores. Para una imagen de 548 × 246 píxeles, el diseño resultó de 352 × 158 puntos en x=32, y=19. Las imágenes originales generaban 174 filas y 42 unidades de avance, sumando un paso de 216. **Las filas y el avance dependen del contenido**: el SDK los calcula para cada imagen y tamaño.

El operador confirmó una posición consistente en cinco etiquetas del programa anterior. En un lote posterior de ocho informó que faltó la última y el papel quedó fuera de la separación. La causa exacta no se estableció. El programa anterior añadía avances finales, consulta de estado y una espera fija.

El SDK elimina esos movimientos y consultas adicionales al cerrar, inicializa una vez por sesión, respeta el control de flujo y espera según el recorrido estimado. El lote posterior de cinco confirma salida completa y posición en ese lote corto. El incidente anterior de ocho sigue siendo una observación separada; el origen final del rollo y los lotes largos siguen pendientes de aceptación.

Una prueba mixta individual previa salió incompleta; el operador informó después que se agotó el rollo y parecía haber perdido tracción. El ráster enviado contenía los campos faltantes. Tras cambiar/alinear el papel, se aceptaron la repetición individual y el lote de cinco. Otra prueba de texto quedó superpuesta a arte anterior y su causa no se estableció. No se presenta ninguno de esos incidentes como diagnóstico verificado del firmware.

No existe confirmación física verificable por etiqueta en este adaptador. `transmitted_unconfirmed`, `position_after="expected_next_label_start"` y la espera transcurrida son estimaciones de software. No son mediciones del sensor ni prueba de entrega. CI y la compilación no imprimen papel.
