# User manual

[Español](USER_GUIDE.es.md) · [Home](../README.md) · [Integration guide](INTEGRATION.en.md)

## 1. Prepare the workstation

Install Python >=3.10 and the SDK using the [installation instructions](../README.md#install). Printing requires a U1 and Bluetooth Classic/SPP on the host. Turn on the printer, load compatible media, and pair it through the operating system if required. Disconnect TinyPrint and other applications that could own the printer connection. Use its exact Bluetooth name/address as `--target`; `U1-XXXX` throughout this manual is a placeholder.

The current release is experimental. Read [compatibility](COMPATIBILITY.md) and [hardware evidence](HARDWARE.md) before a production batch. All file paths are local to the workstation running Python. Profile paths below assume a repository checkout; a wheel-only installation can use defaults or a separately downloaded JSON profile.

## 2. Choose media and artwork

**Text in 0.2.0:** use [text labels and external fields](TEXT.en.md) for configured fonts, bold, alignment, wrapping, fit policies and data composed by an Excel-reading application. `preview-text`/`print-text` take external JSON; they share the printing and recovery workflow below. Images remain supported unchanged.

Width runs across the print head. Height runs along paper travel. `gap_mm` is the blank separation between die-cut labels, not part of label height. The default is width=50, height=25, gap=2 mm, giving a 27 mm pitch. For continuous paper set the gap to 0 and define a deliberate pitch through label height; there is no cutter control.

One static image is one label. PNG is recommended; other static raster formats supported by Pillow can be decoded. Transparent pixels become white. EXIF orientation is applied. The image keeps its aspect ratio, fits inside the available area, and is thresholded to black/white. Text and barcodes should be high contrast; previews cannot certify barcode readability. PDFs, animated images, and printer command languages are not inputs.

Defaults: darkness=5/5, margin=2 mm, horizontal calibration offset=+2 mm, vertical offset=−0.25 mm. These offsets reproduce the earlier trial setup. They are not universal centering values for every roll. Positive X moves right; positive Y moves down along the label. Calibration that clips the image is rejected.

## 3. Preview without consuming paper

```shell
tinylabel preview first.png second.png --profile profiles/u1_50x25_gap2.json --out preview
```

Inspect `preview/0001.png`, `0002.png`, and `plan.json`. PNGs show the entire 384-dot head canvas; the narrower physical label is centered within that head for narrower rolls. The CLI prints JSON to standard output, including dimensions, content boxes, digests, and `printed:false`.

Select another size explicitly:

```shell
tinylabel preview first.png --width-mm 40 --height-mm 30 --gap-mm 2 --darkness 4 --out preview
```

Or copy a profile and edit `media`, `calibration`, `options`, and `drain`. The example [40 × 30 profile](../profiles/u1_40x30_gap2.example.json) is not hardware validated. Do not increase the nominal width limit or scale to bypass an error without checking actual hardware capability.

## 4. Establish the physical origin

Align the beginning of a label using the known printer/app procedure, then disconnect the phone app. The SDK cannot read the gap sensor or home the roll. After stopping the printer, losing power, changing media, moving paper manually, or observing a missing/misaligned label, treat position as unknown and align again.

`--aligned` and `confirm_alignment()` acknowledge this operator action. They send no movement command. A new session always requires this acknowledgment. In a persistent session, do not reinitialize between labels or batches; keep identical media/calibration/options until the session is closed.

## 5. Submit one batch

Use a stable, unique ID for this intentional print request:

```shell
tinylabel print first.png second.png --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id shipment-104-v1 --aligned
```

Images print in argument order. The folder example sorts numeric PNG names numerically and other names alphabetically. There is no implicit duplication. Keep one shared, persistent journal directory for every worker controlling this physical printer; do not put it in a temporary directory or give each request a separate directory.

The connection stays open during sending and passive waiting. The default wait uses a conservative assumed minimum of 2 mm/s: eight 27 mm pitches imply about 108 seconds from send start, plus settling/quiet conditions where applicable. This is deliberately longer than a fixed 20-second wait and remains an estimate. Printer flow pauses must clear; disconnects or timeouts produce uncertain results. Do not kill the process because Bluetooth transmission has finished.

After the planned last pitch the SDK sends no extra ejection, reverse movement, mode reset, or final status query. Closing a session disconnects the transport only. The SDK does not know whether the final physical position is correct.

## 6. Interpret the receipt

| State | Meaning | Operator action |
| --- | --- | --- |
| `reserved` | Job ID durably claimed | If worker crashed, inspect and recover; never replay automatically |
| `sending` | Transmission started; crash can leave this state | Treat as uncertain until reviewed |
| `transmitted_unconfirmed` | Payload sent and passive drain estimate finished | Check actual labels and paper position |
| `uncertain` | Failure, cancellation, or interrupted worker | Some/all labels may have printed; inspect |
| `confirmed` | Operator recorded all requested label IDs | Check `physical_alignment_ok` separately |
| `partial_confirmed` | Operator recorded a subset, possibly empty | Review missing labels before explicit recovery |

`transmitted:true` is transport evidence only. `confirmed_label_ids:null` means no physical observation has been recorded. `position_after:"expected_next_label_start"` is an expectation, not a sensor result. `confirmed` with `physical_alignment_ok:false` still requires realignment before another print.

Inspect a stored receipt:

```shell
tinylabel inspect --journal .label-jobs --job-id shipment-104-v1
```

After physically checking both labels and the position:

```shell
tinylabel confirm --journal .label-jobs --job-id shipment-104-v1 --label-id first.png --label-id second.png --alignment-ok --note "Both labels checked"
```

Path inputs use the file basename as label ID. Python `LabelInput` lets the application choose business IDs. Confirmation is an operator assertion, not printer telemetry. Omit `--alignment-ok` when the position is wrong or unknown.

CLI exit codes: **0** completed software operation (read state); **2** invalid input or operation error; **4** job not found by `inspect`. Argument errors may be plain argparse text; operation errors are JSON on stderr. After any print error, inspect the journal before further action.

## 7. Recover without duplicate labels

If the worker died leaving `reserved`/`sending`, stop the old worker, inspect physical output, then explicitly mark the interrupted job uncertain:

```shell
tinylabel recover --journal .label-jobs --job-id shipment-104-v1 --note "Worker stopped; output being inspected"
```

This acquires the same printer lock, rejects a live owner, and sends no Bluetooth commands. It does not release the ID for reuse. Record the physically observed subset with `confirm`.

If only the last image is missing, do not resend the entire batch. Review which ID is missing, realign the roll, and authorize a new request containing **only that image**, with a new ID such as `shipment-104-recovery-1`. The SDK never performs this recovery print automatically.

## 8. Troubleshooting

| Symptom | Check / response |
| --- | --- |
| Printer not found | Exact target, power, pairing, Classic adapter, phone app disconnected; only model key `u1` is admitted |
| `PrinterBusy` | Another worker owns the printer; use the same journal and serialize requests |
| First label shifted | Physical origin and calibration offsets; preview only describes raster placement |
| Progressive vertical drift | Measured height/gap, movement scale, single persistent initialization; validate a long run |
| Final label missing / position wrong | Do not infer success from send; inspect IDs, record subset, realign, recover only missing labels |
| Light black output | Check darkness, battery and paper; protocol energy/speed values are not calibrated physical units |
| `DuplicateJob` | Inspect existing receipt; never replace its ID merely to bypass protection |
| `DeliveryUncertain` / timeout | Inspect receipt and physical output; no automatic retry |

Before changing a production roll/profile, preview, validate one label, then a short batch, then a longer batch with first/last position and count checks. Calibration cannot guarantee consistent physical output without this acceptance process.
