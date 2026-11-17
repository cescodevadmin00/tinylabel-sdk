# Compatibility / Compatibilidad

## Printer models / Modelos

| Model / Modelo | Transport / Transporte | SDK status / Estado |
| --- | --- | --- |
| **U1**, advertised as `U1-…`, TiMini model key `u1` | Bluetooth Classic / SPP | One five-label batch accepted on one Windows setup, 50 × 25 mm + 2 mm gap; broader acceptance pending / Lote de cinco aceptado en una U1/Windows, 50 × 25 mm + 2 mm; validación ampliada pendiente |
| Other printers using the Tiny protocol / Otras impresoras con protocolo Tiny | Any / Cualquiera | Not enabled; an identical protocol family does not establish model compatibility / No habilitadas; compartir protocolo no demuestra compatibilidad |
| Other TiMini-Print models, including other protocol families / Otros modelos y familias de TiMini-Print | Any / Cualquiera | Not supported by the public SDK adapter / No compatibles con el adaptador público actual |
| BLE-only, USB, Wi-Fi, ESC/POS or ZPL devices | Those interfaces / Esas interfaces | Not implemented / No implementadas |

The adapter requires an exact name/address match and a discovered catalog model key of `u1`. It never selects the first available printer. Unknown devices are rejected. The upstream catalog is bundled to support discovery, not as a claim that its entire model list is supported.

El adaptador exige coincidencia exacta de nombre/dirección y modelo detectado `u1`. No selecciona la primera impresora encontrada. Rechaza dispositivos desconocidos. El catálogo original se incluye para el descubrimiento, sin afirmar que toda su lista sea compatible.

## Platforms / Plataformas

| Platform / Plataforma | Status / Estado |
| --- | --- |
| Windows + Classic Bluetooth adapter | Primary environment; single text/mixed proofs and a five-label mixed batch accepted / Entorno principal; pruebas individuales de texto/mixtas y lote mixto de cinco aceptados |
| Linux | Upstream backend included; SDK hardware untested / Backend incluido; sin pruebas físicas del SDK |
| macOS | Upstream backend and conditional dependency included; SDK hardware untested / Backend y dependencia incluidos; sin pruebas físicas del SDK |
| Browser, Android, iOS | No native client; use a local Python worker / Sin cliente nativo; integrar mediante proceso local Python |
| Node.js, .NET, Java, other host languages | Invoke JSON CLI or a local service around Python / Invocar CLI JSON o servicio local sobre Python |

Python >=3.10 is required. CI exercises software tests on Windows/Linux and selected Python versions. A green CI run verifies software behavior, not Bluetooth hardware interoperability. Bluetooth Classic is required; BLE availability alone is insufficient.

Se requiere Python >=3.10. CI ejecuta pruebas de software en Windows/Linux y versiones seleccionadas de Python. CI no valida el hardware Bluetooth. Disponer únicamente de BLE no es suficiente.

## Media / Papel

Version 0.2.0 adds rasterized text and external fields; it does not add printer models or transports. Image and text plans use the same calibrated physical canvas/pitch. / La versión 0.2.0 incorpora texto renderizado y campos externos; no amplía modelos ni transportes. Comparte lienzo y paso físico con imágenes.

- Initial profile / Perfil inicial: **50 × 25 mm**, **2 mm gap / separación**, **5/5 darkness / oscuridad**.
- Native head / Cabezal: **384 dots / puntos**. Initial calibration / Calibración inicial: **8 dots/mm**, **8 motion units/mm**. A 50 mm roll does not imply 400 printable dots; the head remains 384 dots wide / Un rollo de 50 mm no implica 400 puntos imprimibles; el cabezal mantiene 384.
- Configured nominal width limit / Límite nominal configurado: **50 mm**. This is an application limit, not a verified specification for every U1 variant / Es un límite de configuración, no una especificación verificada de todas las variantes U1.
- Other dimensions are calculated dynamically. They need appropriate physical media, measured gap, calibrated origin and pitch, and first/last acceptance tests / Otros tamaños se calculan dinámicamente; necesitan papel compatible, separación medida y validación de origen y paso.
- No automatic gap sensor integration, homing, cutter, or end-of-roll detection is exposed / No se expone control automático de sensor de separación, origen, cortador o fin de rollo.

## Extending support / Ampliar compatibilidad

Submit a model-specific adapter and tests, plus hardware evidence: exact model/firmware, transport, head geometry, flow control, initial and final position, missing-label recovery, and a long batch. Do not remove the `u1` filter simply because another device connects.

Para incorporar un modelo, aporta adaptador y pruebas específicos, además de evidencia física: modelo/firmware, transporte, geometría, control de flujo, posiciones inicial/final, recuperación y lote largo. No elimines el filtro `u1` solo porque otro dispositivo conecte.
