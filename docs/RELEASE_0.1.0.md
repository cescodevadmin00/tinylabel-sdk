# TinyLabel SDK 0.1.0 — Experimental / Experimental

## English

Initial public release of a local Python SDK and JSON CLI for U1 label printing over Bluetooth Classic/SPP.

- Configurable label width, height, gap, darkness and calibrated placement.
- Aspect-preserving previews and cumulative pitch calculation.
- Persistent sessions, native flow control and passive drain waiting.
- Durable job IDs, duplicate rejection, exclusive ownership and explicit partial/crash recovery.
- English/Spanish user manuals, agent integration guides and Python/Node.js examples.
- Apache-2.0, with pinned TiMini-Print attribution.

Download the wheel for installation with pip, or the source archive for documentation, examples and development. `SHA256SUMS.txt` covers both distributions.

**Supported adapter: U1 Classic Bluetooth only.** Other upstream models are not enabled. Full SDK hardware acceptance remains pending. The previous legacy batch had a missing final label and final paper displacement; the revised lifecycle is software-tested, not yet physically verified. Receipts remain `transmitted_unconfirmed` until an operator records output. No additional labels were printed to prepare this release.

Software verification: 40 local tests passed; wheel import/catalog checks and documentation links passed. See [validation](VALIDATION.md) and repository Actions for CI results.

## Español

Primera versión pública del SDK Python y CLI JSON para imprimir etiquetas con U1 por Bluetooth Classic/SPP.

- Ancho, altura, separación, oscuridad y posición configurables.
- Vistas previas con proporción conservada y cálculo acumulativo del paso.
- Sesiones persistentes, control de flujo y espera pasiva.
- IDs persistentes, rechazo de duplicados, bloqueo y recuperación parcial/tras cierre abrupto.
- Manuales en español/inglés y ejemplos Python/Node.js.
- Licencia Apache-2.0 y reconocimiento de TiMini-Print.

Descarga el wheel para instalar con pip o el archivo fuente para documentación, ejemplos y desarrollo. `SHA256SUMS.txt` permite verificar ambas distribuciones.

**Adaptador admitido: solo U1 Classic Bluetooth.** Los otros modelos originales no están habilitados. La aceptación física integral sigue pendiente. El lote anterior presentó una última etiqueta ausente y desplazamiento final; el ciclo revisado está probado por software, todavía no físicamente. Los comprobantes permanecen `transmitted_unconfirmed` hasta registrar la observación. No se imprimieron etiquetas adicionales al preparar esta versión.

Validación: 40 pruebas locales aprobadas, comprobación del wheel/catálogo y enlaces documentales. Consulta [validación](VALIDATION.md) y Actions para CI.
