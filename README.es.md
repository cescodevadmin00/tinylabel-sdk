# TinyLabel SDK

[![Pruebas](https://github.com/cescodevadmin00/tinylabel-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/cescodevadmin00/tinylabel-sdk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Licencia](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Impresión local de etiquetas para U1: tamaños configurables, lotes continuos y registro persistente de trabajos.**

[English](README.md) · [Manual de usuario](docs/USER_GUIDE.es.md) · [Integración para agentes](docs/INTEGRATION.es.md) · [Compatibilidad](docs/COMPATIBILITY.md)

TinyLabel transforma imágenes en etiquetas monocromáticas y las envía en una sesión Bluetooth continua. Ofrece API asíncrona de Python, CLI con salida JSON, vistas previas, protección contra trabajos duplicados, control de flujo y confirmación física explícita.

**Estado: experimental / alfa.** El adaptador actual admite **U1 mediante Bluetooth Classic/SPP**, con cabezal de 384 puntos. Las pruebas anteriores con U1 permitieron ajustar un diseño de 50 × 25 mm; en un lote posterior del programa anterior faltó la última etiqueta y se perdió la alineación. Este SDK modifica el cierre y la espera, pero su ciclo completo todavía requiere validación física. Un envío correcto devuelve `transmitted_unconfirmed`; no demuestra que hayan salido todas las etiquetas. Consulta la [evidencia física](docs/HARDWARE.md).

## Instalación

Requiere Python 3.10 o superior y adaptador Bluetooth Classic para imprimir. Windows es la plataforma principal. Descarga el wheel desde [Releases](https://github.com/cescodevadmin00/tinylabel-sdk/releases):

```powershell
python -m pip install .\tinylabel_sdk-0.1.0-py3-none-any.whl
```

También puedes instalar la versión fijada del código fuente:

```shell
python -m pip install "git+https://github.com/cescodevadmin00/tinylabel-sdk.git@v0.1.0"
```

El proyecto todavía no se distribuye en PyPI. Para desarrollo, clona el repositorio y ejecuta `python -m pip install -e .`.

## Revisar antes de imprimir

Desde el repositorio, usando tu propia imagen `label.png`:

```shell
tinylabel preview label.png --profile profiles/u1_50x25_gap2.json --out preview
```

Genera PNG numerados y `plan.json`. No conecta Bluetooth ni mueve papel. El perfil inicial usa etiquetas de 50 × 25 mm, separación de 2 mm y oscuridad 5/5. Puedes seleccionar otras dimensiones mediante `--width-mm`, `--height-mm` y `--gap-mm`.

## Imprimir un lote alineado

Alinea el inicio de una etiqueta con la app del celular o con el procedimiento conocido de la impresora. Desconecta la app. Sustituye `U1-XXXX` por el nombre o dirección Bluetooth exactos:

```shell
tinylabel print label.png --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id pedido-104-etiquetas-v1 --aligned
```

`--aligned` registra que el operador ya alineó el papel; no busca automáticamente la separación. Conserva el registro de trabajos. Un mismo ID nunca se vuelve a enviar, incluso si hubo un error. No reintentes automáticamente un trabajo incierto con otro ID.

El código de salida 0 representa éxito de la operación de software. Consulta el campo JSON `state` antes de modificar los registros del negocio. La impresión física se confirma por separado.

## API Python

```python
import asyncio
from tinylabel_sdk import LabelInput, LabelPrinter, Media, prepare_batch

async def main():
    media = Media(width_mm=50, height_mm=25, gap_mm=2)
    plan = prepare_batch([LabelInput("label.png", "producto-104")], media)
    plan.save_previews("preview")

    # El operador ya alineó el rollo y desconectó la app del celular.
    async with LabelPrinter("U1-XXXX", journal_dir=".label-jobs") as printer:
        printer.confirm_alignment(media, calibration=plan.calibration)
        receipt = await printer.print_batch(plan, job_id="pedido-104-etiquetas-v1")
        print(receipt.to_dict())  # transmitted_unconfirmed

asyncio.run(main())
```

En un sistema de gestión de etiquetas, conserva un proceso y una sesión por impresora. Envía los lotes sucesivos por esa sesión, sin reiniciar el modo entre etiquetas. El [manual de integración](docs/INTEGRATION.es.md) explica recuperación, cancelación, dimensiones y conexión desde Node.js.

## Alcance

| Función | Estado actual |
| --- | --- |
| U1 / protocolo Tiny por Bluetooth Classic | Implementado; validación física integral del SDK pendiente |
| 50 × 25 mm y separación de 2 mm | Perfil inicial basado en pruebas previas |
| Otros tamaños | Configurables; necesitan calibración y comprobación física |
| Otros modelos de TiMini-Print | No habilitados en este SDK |
| PDF, ZPL, ESC/POS, USB, Wi-Fi o impresoras solo BLE | No expuestos por este SDK |
| Detección automática de separación / origen | No implementada |
| Confirmación verificable de impresión por etiqueta | No disponible |

El catálogo incluido de TiMini-Print contiene otros modelos, pero eso **no** amplía la compatibilidad del SDK. Consulta la [matriz completa](docs/COMPATIBILITY.md).

## Documentación y desarrollo

- [Manual de usuario en español](docs/USER_GUIDE.es.md) / [English user manual](docs/USER_GUIDE.en.md).
- [Integración para agentes y aplicaciones](docs/INTEGRATION.es.md) / [English integration guide](docs/INTEGRATION.en.md).
- [Compatibilidad](docs/COMPATIBILITY.md), [evidencia física](docs/HARDWARE.md), [contribuciones](CONTRIBUTING.md).

Pruebas: `python -m unittest discover -s tests -v`. Usan imágenes sintéticas y transportes simulados, sin gastar etiquetas. Compilación: `python -m pip install build` y `python -m build`.

## Licencia y reconocimiento

Apache-2.0. Incluye una copia sin cambios de algoritmos de [TiMini-Print](https://github.com/Dejniel/TiMini-Print), de Daniel Banecki, dentro de un espacio de nombres privado. La revisión, licencia y avisos están incluidos en el paquete: [NOTICE](NOTICE), [LICENSE](LICENSE), [metadatos originales](src/tinylabel_sdk/_vendor/UPSTREAM.json). TinyLabel es un proyecto de integración independiente.
