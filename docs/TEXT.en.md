# Text labels and external fields — 0.2.0

[Español](TEXT.es.md) · [User manual](USER_GUIDE.en.md) · [Integration](INTEGRATION.en.md)

## What the SDK accepts

Version 0.2.0 adds configurable text labels. Your application may obtain values from Excel, a database, a form or an API, compose the text externally, and pass it to the SDK. **The SDK does not open or import Excel files.** It requires no spreadsheet dependency.

Text is rasterized at the printer's native dot scale and uses the same physical canvas, margins, calibration, threshold, row packing, pitch calculation, session and job journal as image labels. Text is not sent through an unverified printer-native font command. Image and text labels can share one continuous batch/session.

The existing U1/Classic compatibility and experimental hardware status remain unchanged. No physical printing was performed to validate this feature; preview and transport tests do not prove paper registration. See [hardware evidence](HARDWARE.md).

## A single configured text label

```python
from tinylabel_sdk import Media, TextLabel, TextStyle, prepare_text_batch

label = TextLabel.from_text(
    "Café molido\nPrecio: USD 7,82\nLote: 0017",
    label_id="item-0017",
    style=TextStyle(font_size_mm=3, align="center", bold=False),
    vertical_align="center",
)
plan = prepare_text_batch([label], Media(50, 25, 2))
plan.save_previews("preview-text")  # no Bluetooth or paper movement
```

`font_size_mm` specifies the nominal font em size in millimeters. Actual glyph ink height depends on font metrics; it is not a promise that every capital letter measures exactly that height. With 8 dots/mm, 3 mm selects a 24-pixel font. Check the preview at native size and physically validate readability.

The initial profile keeps the same +2 mm horizontal and −0.25 mm vertical calibration used by images. These are device/roll offsets, not new text-specific feed commands. The text's visible vertical extent is centered by default. Narrower media and different heights are calculated dynamically.

## Different title and detail styles

```python
from tinylabel_sdk import TextBlock, TextLabel, TextStyle

label = TextLabel("item-0017", blocks=(
    TextBlock("Café molido", TextStyle(font_size_mm=4, bold=True), gap_after_mm=0.75),
    TextBlock("USD 7,82\nLote: 0017", TextStyle(font_size_mm=3, align="left")),
), vertical_align="center")
```

| Setting | Meaning / default |
| --- | --- |
| `TextStyle.font_size_mm` | Nominal font size, default 3 mm |
| `TextStyle.align` | `left`, `center` (default), `right`, per block |
| `TextStyle.bold` | Select bundled regular/bold face; default `False` |
| `TextStyle.font_path` | Optional local `.ttf`/`.otf` font file |
| `TextStyle.line_spacing_mm` | Extra spacing between lines, default 0.5 mm |
| `TextStyle.wrap` | Automatic wrapping, default `True` |
| `TextBlock.gap_after_mm` | Extra spacing after a block, default 0.75 mm; no trailing visible padding after the final block |
| `TextLabel.vertical_align` | `top`, `center` (default), `bottom` |
| `TextLabel.overflow` | `error` (default) or explicit `shrink` |
| `TextLabel.min_font_size_mm` | Shrink floor, default 1.5 mm |

Explicit newlines are respected. Automatic wrapping normalizes spaces between words and hard-wraps identifiers that exceed a line; use `wrap=False` when an identifier must stay on one line. Tabs expand to spaces. Blank internal lines remain; leading/trailing empty vertical space does not change the visible-ink centering. Blocks share one available text area; per-block styles do not change media pitch.

Bundled **Noto Sans Regular/Bold** fonts support the Spanish/English examples, including accents, ñ and currency symbols tested by the suite. Font files and their OFL-1.1 license/provenance are included. Other writing systems require a suitable font and visual validation; no automatic font fallback or universal Unicode coverage is promised. For custom bold fonts, set `font_path` to the bold font file and leave `bold=False`; combining a custom path with `bold=True` is rejected. Keep the font version fixed for consistent typography across machines; pin Pillow/FreeType versions as well when pixel-identical raster output is required.

## Use already formatted external data

The integration boundary is plain strings. The host application must decide how to handle spreadsheet cell types, leading zeros, formulas, missing values, decimal separators, currencies and dates **before** constructing the label. Never turn an empty value into the literal `None` accidentally or assume a numeric Excel cell still contains its displayed leading zeros.

```python
from tinylabel_sdk import TextLabel, format_text, prepare_text_batch

# Produced by your application, regardless of how it reads Excel:
rows = [
    {"id": "item-0017", "name": "Café molido", "price": "USD 7,82", "lot": "0017"},
    {"id": "item-0018", "name": "Arroz integral", "price": "USD 5,83", "lot": "0018"},
]
labels = [TextLabel.from_text(
    format_text("{name}\n{price}\nLote: {lot}", row), label_id=row["id"]
) for row in rows]
plan = prepare_text_batch(labels)
```

You can instead compose the final string entirely outside the SDK with your own template engine or f-string. `format_text` is optional. It accepts flat placeholders such as `{name}` or `{Product name}` and string values only. Missing fields and numeric/`None` values raise `ConfigurationError`. There is no attribute/index access, conversion, evaluation, nested substitution, or format specification; preformat numbers/dates externally. Use `{{`/`}}` for literal braces. Substituted values containing braces are not interpreted again.

See the runnable preview-only [external fields example](../examples/text_from_fields.py):

```shell
python examples/text_from_fields.py
```

## External JSON and CLI

Other languages can pass UTF-8 JSON. A label may contain literal `text`, or a `template` plus `fields`, or a `blocks` array. A block requires exactly one of `text` or `template`. Templates use the label's `fields`; literal `text` is never interpolated. Unknown settings are rejected to catch typos. Custom font paths in JSON are relative to the JSON file, not the worker's current directory.

```json
{
  "schema": 1,
  "labels": [
    {
      "label_id": "item-0017",
      "template": "{name}\n{price}\nLote: {lot}",
      "fields": {"name": "Café molido", "price": "USD 7,82", "lot": "0017"},
      "style": {"font_size_mm": 3, "align": "center"},
      "vertical_align": "center",
      "overflow": "error"
    }
  ]
}
```

Preview the bundled [multi-style JSON example](../examples/text_labels.json):

```shell
tinylabel preview-text examples/text_labels.json --profile profiles/u1_50x25_gap2.json --out preview-text
tinylabel preview-text examples/text_labels.json --width-mm 40 --height-mm 30 --gap-mm 2 --out preview-text-40x30
```

For an explicitly authorized and physically aligned print:

```shell
tinylabel print-text examples/text_labels.json --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id text-batch-104-v1 --aligned
```

All text is prepared and checked before connecting. `print-text` has the same alignment, durable ID, flow control, passive wait and physical-confirmation rules as image `print`. CLI success remains `transmitted_unconfirmed` until observed. Use `inspect`, `confirm` and `recover` as described in the [user manual](USER_GUIDE.en.md).

## Fit, placement and verification

With `overflow="error"`, text that is too wide/tall raises `GeometryError` before any send. No clipping or silent font reduction occurs. With `overflow="shrink"`, the SDK reduces a common font scale while preserving the size hierarchy and rewrapping. It never goes below the configured minimum; spacing stays as configured. If the minimum cannot fit, it rejects the label. Shrinking can reduce readability; confirm actual printed text size before production.

`plan.summary()` and saved `plan.json` include `text_layout`: resolved font sizes per block in pixels, line count, `shrunk`, area rectangle and vertical alignment. `content_box_px` describes the rendered text extent. Source text/fields are not added to journal receipts; the host must retain immutable label definitions if later recovery needs them.

Use `prepare_batch([TextLabel(...), LabelInput(...)], media)` for mixed batches. Pass the resulting plan to the existing `printer.print_batch(plan, job_id=...)`; there is no separate printer lifecycle for text. Each label's advance is derived from its own bitmap rows and the shared media pitch. Do not reuse the old sample's 174-row/42-feed values for text.

For rollout, preview representative longest/shortest fields, accented text and missing-value cases, then explicitly validate physical count, first/last placement, final boundary and legibility. An arithmetic pitch test cannot establish physical alignment on its own.
