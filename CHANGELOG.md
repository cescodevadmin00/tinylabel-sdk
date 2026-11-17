# Changelog

## 0.2.0 — Configurable text and external fields

- `TextLabel`, `TextBlock`, `TextStyle` and `prepare_text_batch` for native raster text.
- Per-block font size, regular/bold, alignment, wrapping, line/block spacing and vertical alignment.
- Explicit overflow rejection or controlled shrink with a minimum font size; resolved layout metadata in previews.
- Optional `format_text` for preformatted external string fields; no Excel importer or new spreadsheet dependency.
- `preview-text` / `print-text` and schema 1 JSON text jobs, including templates and relative custom-font paths.
- Mixed image/text plans share the existing calibration, movement calculation, session, journal and delivery semantics.
- Bundled, pinned Noto Sans Regular/Bold under OFL-1.1 for portable Spanish/English typography.
- Expanded English/Spanish manuals and external-data examples; image API remains compatible.
- Hardware acceptance remains pending; this release does not claim a new physical validation.

Español: etiquetas de texto con fuentes y bloques configurables, campos externos preformateados, CLI JSON y lotes mixtos. La aplicación lee Excel fuera del SDK. Se conservan geometría, avance, sesiones y confirmación física de imágenes. Manuales bilingües actualizados; aceptación física pendiente.

## 0.1.0 — Initial experimental release

- Async Python API and JSON CLI for a U1 Classic Bluetooth adapter.
- Configurable media dimensions, calibrated offsets and aspect-preserving previews.
- Continuous-session initialization and cumulative fractional pitch calculation.
- Native flow control and conservative passive drain; no extra final eject/query.
- SQLite job receipts, duplicate-ID rejection, OS printer ownership and explicit crash recovery.
- Physical delivery remains unconfirmed until recorded by an operator.
- English and Spanish user manuals, integration contracts, compatibility matrix and examples.
- Apache-2.0 distribution with pinned TiMini-Print attribution and provenance.

Full SDK hardware acceptance is pending. Earlier legacy trials reported a missing final label and final paper displacement; this release does not claim those physical issues are already verified as resolved.

## Español

Primera versión experimental: API Python y CLI JSON para U1 Classic, tamaños configurables, vistas previas, sesiones continuas, paso acumulativo, control de flujo, espera pasiva, registro SQLite, protección contra duplicados y recuperación explícita. Manuales y ejemplos bilingües. La aceptación física integral sigue pendiente; no se declara resuelto físicamente el incidente anterior de última etiqueta ausente y posición final incorrecta.
