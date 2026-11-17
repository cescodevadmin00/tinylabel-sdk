# Contributing / Contribuir

## English

Open an issue describing the observed behavior, expected behavior, SDK/Python/OS versions, printer model/firmware and media measurements. Use synthetic artwork and redact Bluetooth addresses, paths, customer details and receipts containing business IDs. For missing labels, distinguish transport completion from physically observed output.

For development:

```shell
python -m pip install -e . build
python -m unittest discover -s tests -v
python scripts/check_docs.py
python -m build
python scripts/check_wheel.py dist/tinylabel_sdk-0.2.0-py3-none-any.whl
```

Tests and CI must never connect to hardware or print automatically. Changes to movement, session lifecycle, flow control or retry behavior need meaningful simulated tests and an explicit hardware evidence note. Preserve stable IDs, the shared printer lock and unconfirmed delivery semantics. Keep English and Spanish manuals consistent.

Text changes must cover accented glyphs, wrapping, overflow/minimum font size, calibration and mixed image/text pitch. Keep bundled font checksums and OFL attribution intact. Spreadsheet parsing belongs to the host application.

Do not edit vendored upstream files casually. Update their pinned revision, NOTICE and provenance if changing the snapshot, and document any modifications. New printer support needs a model-specific adapter and hardware evidence; do not advertise the whole upstream catalog.

## Español

Abre una incidencia con resultado real/esperado, versiones de SDK/Python/SO, modelo/firmware y medidas del papel. Usa imágenes sintéticas y oculta direcciones Bluetooth, rutas, clientes e IDs del negocio. Si faltan etiquetas, distingue envío de salida física observada.

Los comandos anteriores instalan, prueban, validan enlaces locales y construyen el paquete. Las pruebas y CI no deben conectar hardware ni imprimir automáticamente. Cambios de avance, ciclo, flujo o reintento requieren pruebas simuladas útiles y una nota explícita de evidencia física. Conserva IDs estables, bloqueo compartido y estados de entrega sin confirmar. Actualiza ambos idiomas.

Al actualizar el código original incluido, conserva licencia, revisión y procedencia, documentando modificaciones. Los nuevos modelos necesitan adaptador y evidencia propios; no anuncies compatibilidad de todo el catálogo original.
