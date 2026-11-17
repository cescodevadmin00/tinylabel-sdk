# TinyLabel SDK 0.2.0 — Text labels / Etiquetas de texto

## English

This release adds configurable text from externally composed strings and fields, including applications that read Excel. The SDK does not import spreadsheets.

- `TextLabel`, `TextBlock`, `TextStyle`, `prepare_text_batch` and optional flat `format_text` substitution.
- Font size in mm, normal/bold, left/center/right alignment, top/center/bottom placement, wrapping and spacing.
- Explicit overflow rejection or controlled shrink with a minimum size, plus resolved preview metadata.
- `preview-text` / `print-text` for external JSON definitions with literal text or templates/fields.
- Pinned Noto Sans Regular/Bold fonts with accents, ñ and tested currency symbols; OFL-1.1 license included.
- Shared native canvas, calibration and pitch for images/text, including mixed continuous batches.
- Expanded user and agent integration manuals in English and Spanish.

Install the wheel or pinned source tag. Image APIs and receipt/session behavior remain compatible. The wheel and source archive have SHA-256 checksums in `SHA256SUMS.txt`.

Software verification: 68 local tests, including the original image/session regression suite and text/field/CLI tests. Package/font/provenance checks are included; consult repository Actions for CI results. Preview examples do not print paper.

**Compatibility remains U1 over Bluetooth Classic/SPP.** The new SDK lifecycle and text output still require physical acceptance; transmission remains `transmitted_unconfirmed` until observed. No automatic reprint, extra final ejection or gap homing has been added.

Read the [text manual](https://github.com/cescodevadmin00/tinylabel-sdk/blob/v0.2.0/docs/TEXT.en.md) and [integration guide](https://github.com/cescodevadmin00/tinylabel-sdk/blob/v0.2.0/docs/INTEGRATION.en.md).

## Español

Esta versión incorpora texto configurable mediante cadenas y campos compuestos externamente, incluso desde aplicaciones que lean Excel. El SDK no importa hojas de cálculo.

- API de etiquetas/bloques/estilos y sustitución plana opcional de campos.
- Tamaño en mm, normal/negrita, alineación horizontal/vertical, saltos y separaciones.
- Rechazo de desbordamiento o reducción controlada con mínimo y metadatos de vista previa.
- `preview-text` / `print-text` con JSON externo, texto literal o plantillas/campos.
- Fuentes Noto Sans incluidas con acentos, ñ y símbolos probados; licencia OFL-1.1 conservada.
- Geometría, calibración y paso compartidos con imágenes, también en lotes mixtos.
- Manuales de usuario e integración para agentes actualizados en español e inglés.

Instala el wheel o la versión fijada del código fuente. Se mantienen las API de imágenes, sesiones y comprobantes. `SHA256SUMS.txt` cubre ambas distribuciones.

Validación de software: 68 pruebas locales, incluyendo regresión de imágenes/sesiones y texto/campos/CLI. Se comprueban paquete, fuentes y procedencia; consulta Actions para CI. Los ejemplos de vista previa no imprimen.

**La compatibilidad sigue siendo U1 por Bluetooth Classic/SPP.** El ciclo nuevo y el texto requieren aceptación física; el envío sigue como `transmitted_unconfirmed` hasta observarlo. No se añadió reimpresión automática, expulsión final extra ni búsqueda del sensor de separación.

Consulta el [manual de texto](https://github.com/cescodevadmin00/tinylabel-sdk/blob/v0.2.0/docs/TEXT.es.md) y la [guía de integración](https://github.com/cescodevadmin00/tinylabel-sdk/blob/v0.2.0/docs/INTEGRATION.es.md).
