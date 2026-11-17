# TinyLabel SDK

[![Tests](https://github.com/cescodevadmin00/tinylabel-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/cescodevadmin00/tinylabel-sdk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Local label printing for U1 thermal printers: configurable media, continuous batches, and durable job receipts.**

[Español](README.es.md) · [User manual](docs/USER_GUIDE.en.md) · [Agent integration](docs/INTEGRATION.en.md) · [Compatibility](docs/COMPATIBILITY.md)

TinyLabel turns image files into correctly sized monochrome label plans and sends them through a single Bluetooth session. It includes a Python async API, a JSON CLI, previews, persistent duplicate-job protection, flow control, and explicit operator confirmation.

**Release status: experimental / alpha.** The current adapter targets **U1 over Bluetooth Classic/SPP**, using a 384-dot print head. Earlier U1 hardware trials established a useful 50 × 25 mm layout, but a later legacy batch missed its final label and lost alignment. The SDK changes session ending and waiting behavior; its complete lifecycle still needs hardware acceptance testing. A successful send returns `transmitted_unconfirmed`, never a claim that every label physically printed. See [hardware evidence](docs/HARDWARE.md).

## Install

Python 3.10 or newer and a Bluetooth Classic adapter are required for printing. Windows is the primary target. Download a wheel from [Releases](https://github.com/cescodevadmin00/tinylabel-sdk/releases), then:

```powershell
python -m pip install .\tinylabel_sdk-0.1.0-py3-none-any.whl
```

Or install the pinned source release:

```shell
python -m pip install "git+https://github.com/cescodevadmin00/tinylabel-sdk.git@v0.1.0"
```

This project is not currently distributed through PyPI. To develop locally, clone the repository and run `python -m pip install -e .`.

## Start with a preview

From a repository checkout, with your own `label.png`:

```shell
tinylabel preview label.png --profile profiles/u1_50x25_gap2.json --out preview
```

This produces numbered PNG previews and `plan.json`; it never opens Bluetooth or moves paper. Defaults are 50 × 25 mm labels, a 2 mm gap, and darkness 5/5. Other dimensions can be selected with `--width-mm`, `--height-mm`, and `--gap-mm`.

## Print one explicitly aligned batch

Align the start of a label using the phone app or the printer's established procedure, then disconnect the phone app. Replace `U1-XXXX` with the exact Bluetooth name or address:

```shell
tinylabel print label.png --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id order-104-labels-v1 --aligned
```

`--aligned` acknowledges a physical action already completed by the operator. It does not home the printer. Preserve the journal and reuse the same job ID when checking an existing request; duplicate IDs are rejected, including failed attempts. Never automatically retry an uncertain job under a new ID.

CLI exit code 0 means the operation completed at the software level. Read the JSON `state` before updating business records. Physical completion requires a separate observation.

## Python API

```python
import asyncio
from tinylabel_sdk import LabelInput, LabelPrinter, Media, prepare_batch

async def main():
    media = Media(width_mm=50, height_mm=25, gap_mm=2)
    plan = prepare_batch([LabelInput("label.png", "item-104")], media)
    plan.save_previews("preview")

    # Operator has already aligned this roll and disconnected the phone app.
    async with LabelPrinter("U1-XXXX", journal_dir=".label-jobs") as printer:
        printer.confirm_alignment(media, calibration=plan.calibration)
        receipt = await printer.print_batch(plan, job_id="order-104-labels-v1")
        print(receipt.to_dict())  # transmitted_unconfirmed

asyncio.run(main())
```

For a label management system, keep one worker and one persistent session per printer. Submit successive batches through that session without reinitializing between labels. See the [integration contract](docs/INTEGRATION.en.md), including recovery, cancellation, dimensions, and a Node.js bridge.

## Supported scope

| Capability | Current status |
| --- | --- |
| U1 / Tiny protocol, Classic Bluetooth | Implemented; end-to-end SDK hardware acceptance pending |
| 50 × 25 mm, 2 mm gap | Starting profile based on prior U1 trials |
| Other roll dimensions | Configurable; require physical calibration and validation |
| Other TiMini-Print models | Not enabled by this SDK |
| PDF, ZPL, ESC/POS, USB, Wi-Fi, BLE-only printers | Not exposed by this SDK |
| Automatic gap sensing / homing | Not implemented |
| Verified physical completion acknowledgment | Not available |

The bundled TiMini-Print catalog contains many models; it does **not** expand this SDK's compatibility. See the full [model and platform matrix](docs/COMPATIBILITY.md).

## Documentation

| English | Español |
| --- | --- |
| [User manual](docs/USER_GUIDE.en.md) | [Manual de usuario](docs/USER_GUIDE.es.md) |
| [Agent / application integration](docs/INTEGRATION.en.md) | [Integración para agentes y aplicaciones](docs/INTEGRATION.es.md) |
| [Compatibility / Compatibilidad](docs/COMPATIBILITY.md) | [Hardware evidence / Evidencia física](docs/HARDWARE.md) |

Run tests with `python -m unittest discover -s tests -v`. Tests use synthetic images and simulated transports; they do not consume labels. Build with `python -m pip install build` and `python -m build`.

## License and attribution

Apache-2.0. Includes an unmodified, privately namespaced snapshot of [TiMini-Print](https://github.com/Dejniel/TiMini-Print) by Daniel Banecki. The pinned revision, license, and notices are included in the package. See [NOTICE](NOTICE), [LICENSE](LICENSE), and [upstream metadata](src/tinylabel_sdk/_vendor/UPSTREAM.json). TinyLabel is an independent integration project.
