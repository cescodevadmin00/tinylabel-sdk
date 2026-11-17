# Public API reference / Referencia de API

Imports below come from `tinylabel_sdk` unless stated otherwise. Methods that touch Bluetooth are async. / Los símbolos se importan desde `tinylabel_sdk` salvo indicación. Los métodos Bluetooth son asíncronos.

| Symbol | Contract / Contrato |
| --- | --- |
| `Media(width_mm=50, height_mm=25, gap_mm=2)` | Physical dimensions in mm; positive width/height, nonnegative gap / Dimensiones físicas |
| `Calibration(...)` | Frozen geometry and movement configuration / Configuración inmutable de geometría y movimiento |
| `PrintOptions(darkness=5, energy=8000, speed=10)` | Darkness 1–5; energy/speed are protocol values, not calibrated SI units / Oscuridad 1–5; energía/velocidad del protocolo |
| `DrainPolicy(...)` | Passive waiting assumptions, not completion proof / Supuestos de espera, sin prueba de entrega |
| `LabelInput(image, label_id)` | Path, encoded `bytes`, or Pillow image plus business ID / Ruta, bytes o imagen Pillow con ID |
| `prepare_batch(images, media=None, *, calibration=None, options=None)` | Pure planning; returns `BatchPlan`; no hardware / Preparación sin hardware |
| `BatchPlan.save_previews(directory)` | Numbered PNGs + `plan.json`; returns PNG paths / PNG numerados + plan |
| `BatchPlan.summary()` / `.digest` | JSON-compatible plan summary / SHA-256 digest / Resumen y huella |
| `load_profile(path)` | Returns `(Media, Calibration, PrintOptions, DrainPolicy)` from schema 1 JSON / Carga perfil |
| `LabelPrinter(target, *, journal_dir, drain=None, transport=None)` | Async context manager; exact target, mandatory durable journal / Sesión con destino exacto y registro persistente |
| `printer.confirm_alignment(media, *, calibration=None)` | Synchronous acknowledgment; requires open, uninitialized session; sends nothing / Confirmación sin movimiento |
| `await printer.print_batch(plan, *, job_id)` | Returns unconfirmed `Receipt` after send/drain; never retries / Devuelve comprobante sin reintento |
| `printer.confirm_delivery(job_id, *, printed_label_ids, alignment_ok, note="")` | Explicit physical observation; partial/bad alignment invalidates live origin / Observación física explícita |
| `await printer.aclose()` | Disconnects and releases lock; no paper movement / Desconecta sin mover papel |
| `Journal(directory).get(job_id)` | Returns stored receipt or `None` / Consulta persistente |
| `Journal.confirm(job_id, *, printed_label_ids, alignment_ok, note="")` | Operator assertion, does not notify another live worker / Observación sin actualizar otro proceso vivo |
| `Journal.recover_interrupted(job_id, *, note="")` | Explicit orphan recovery under printer lock; no transmission / Recuperación sin enviar |
| `Receipt.to_dict()` | JSON-compatible fields, including requested count and confirmation status / Campos JSON |
| `encode_batch(plan, *, start_index=0, initialize=True)` | Advanced wire-plan inspection; use `LabelPrinter` for sending / Inspección avanzada del protocolo |

## Calibration defaults / Valores iniciales

```python
Calibration(
    dots_per_mm=8,
    motion_units_per_mm=8,
    row_motion_units=1,
    head_width_dots=384,
    configured_max_paper_width_mm=50,
    margin_mm=2,
    offset_x_mm=2,
    offset_y_mm=-0.25,
    threshold=128,
)
DrainPolicy(
    minimum_print_speed_mm_s=2,
    settle_after_send_s=5,
    quiet_s=3,
    poll_s=0.25,
    max_wait_s=None,
)
```

Positive X is right; positive Y is down. Default max wait after send is `max(60, travel_mm / minimum_print_speed_mm_s + 30)` seconds. `max_wait_s` overrides that deadline, not the required estimated duration. / X positivo va a la derecha; Y positivo hacia abajo. El plazo se calcula después del envío. `max_wait_s` cambia el plazo, no el recorrido estimado exigido.

Batch limits / Límites: 1–500 labels, 64 MiB encoded payload, 25 megapixels per source image, unique nonempty label IDs up to 256 characters, stable job ID up to 128 characters. Height ≤500 mm and gap ≤50 mm are software configuration limits, not hardware compatibility claims. / Son límites de software, no especificaciones del hardware.

## Errors / Errores

Import from `tinylabel_sdk.errors`. / Importar desde ese módulo.

| Error | Handling / Manejo |
| --- | --- |
| `ConfigurationError`, `GeometryError` | Fix configuration/input before sending / Corregir antes de enviar |
| `AlignmentRequired` | Close if needed, physically realign and acknowledge new session / Realinear y abrir sesión |
| `PrinterNotFound` | Check exact U1 identity, adapter, pairing and availability / Revisar identificación y conexión |
| `PrinterBusy` | Serialize ownership; do not bypass lock with another journal / Serializar sin evitar bloqueo |
| `DuplicateJob` | Inspect `.receipt`; no new transmission / Revisar sin reenviar |
| `DeliveryUncertain` | Inspect `.job_id`, `.cause`, journal and physical output / Revisar registro y papel |
| `PrinterFault`, `DrainTimeout` | During printing these are wrapped by `DeliveryUncertain` / Durante impresión quedan como causa |
| `asyncio.CancelledError` | Propagates after uncertain receipt and cleanup attempt / Se propaga tras registrar incertidumbre |

Storage/OS failures can propagate directly. A hard crash or unavailable disk can leave a `sending` receipt rather than `uncertain`; never assume a raw exception means no bytes were sent. Private `_vendor` symbols and low-level upstream APIs are not a stable public interface. Alpha releases may change APIs; pin a tag and test before upgrading. / Errores de almacenamiento pueden propagarse directamente; tampoco significan que no se enviaron datos. `_vendor` no es API pública estable. Fijar versión y probar antes de actualizar.
