from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from io import BytesIO, StringIO
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from tinylabel_sdk import (Calibration, LabelInput, LabelPrinter, Media, TextBlock,
                           TextLabel, TextStyle, encode_batch, format_text,
                           load_text_labels, prepare_batch, prepare_text_batch)
from tinylabel_sdk.cli import main as cli
from tinylabel_sdk.errors import ConfigurationError, GeometryError
from tinylabel_sdk.models import rounded
import tinylabel_sdk.text as text_module
from test_sdk import FAST, FakeTransport, frames


def label(text="Café · Código 0017", **kwargs):
    return TextLabel.from_text(text, "item-001", **kwargs)


def ink(prepared):
    canvas = Image.open(BytesIO(prepared.preview_png)).convert("L")
    return ImageChops.invert(canvas).getbbox()


class TextLayoutTests(unittest.TestCase):
    def test_default_centers_visible_text_with_existing_offsets(self):
        prepared = prepare_text_batch([label()]).labels[0]
        x0, y0, x1, y1 = ink(prepared)
        self.assertLessEqual(abs((x0+x1)/2-208), 1.5)
        self.assertLessEqual(abs((y0+y1)/2-98), 1.5)
        self.assertEqual((prepared.canvas_width, prepared.canvas_height), (384,200))
        self.assertEqual(prepared.text_layout.font_sizes_px, (24,))
        self.assertFalse(prepared.text_layout.shrunk)

    def test_horizontal_alignment_changes_position_not_font_size(self):
        boxes = []
        for align in ("left", "center", "right"):
            prepared = prepare_text_batch([label("Hello", style=TextStyle(align=align))]).labels[0]
            boxes.append(ink(prepared))
        self.assertLess(boxes[0][0], boxes[1][0])
        self.assertLess(boxes[1][0], boxes[2][0])
        self.assertLessEqual(abs(boxes[0][0]-32), 2)
        self.assertLessEqual(abs(boxes[2][2]-384), 2)
        self.assertEqual([b[2]-b[0] for b in boxes], [boxes[0][2]-boxes[0][0]]*3)

    def test_vertical_top_center_bottom(self):
        boxes = [ink(prepare_text_batch([label("Hello", vertical_align=align)]).labels[0])
                 for align in ("top", "center", "bottom")]
        self.assertLess(boxes[0][1], boxes[1][1])
        self.assertLess(boxes[1][1], boxes[2][1])
        self.assertLessEqual(abs(boxes[0][1]-14), 1)
        self.assertLessEqual(abs(boxes[2][3]-182), 1)

    def test_bundled_accented_glyphs_are_not_missing_glyph_boxes(self):
        font = text_module._font(TextStyle(), 24)
        missing = font.getmask("\U0010ffff")
        for char in "áéíóúÁÉÍÓÚñÑüÜ¿¡€":
            with self.subTest(char=char):
                glyph = font.getmask(char)
                self.assertNotEqual((glyph.size, bytes(glyph)), (missing.size, bytes(missing)))

    def test_bold_font_and_per_block_sizes_are_distinct(self):
        normal = prepare_text_batch([label("Title")]).labels[0]
        bold = prepare_text_batch([label("Title", style=TextStyle(bold=True))]).labels[0]
        self.assertNotEqual(normal.digest, bold.digest)
        prepared = prepare_text_batch([TextLabel("multi", (
            TextBlock("Title", TextStyle(font_size_mm=4, bold=True)),
            TextBlock("Price USD 7,82", TextStyle(font_size_mm=2.5, align="left")),
        ))]).labels[0]
        self.assertEqual(prepared.text_layout.font_sizes_px, (32,20))
        self.assertEqual(prepared.text_layout.line_count, 2)

    def test_wrap_and_hard_wrap_preserve_all_non_space_characters(self):
        font = text_module._font(TextStyle(), 24)
        source = "SKU-01234567890123456789012345678901234567890123456789"
        wrapped = text_module._lines(source, font, 120, True)
        self.assertGreater(len(wrapped), 1)
        self.assertEqual("".join(wrapped), source)
        for value in wrapped:
            box = font.getbbox(value)
            self.assertLessEqual(box[2]-box[0], 120)

    def test_explicit_newlines_and_blank_lines_are_retained(self):
        prepared = prepare_text_batch([label("One\r\n\r\nTwo", style=TextStyle(font_size_mm=2))]).labels[0]
        self.assertEqual(prepared.text_layout.line_count, 3)

    def test_overflow_rejects_without_silently_reducing(self):
        for source in (label("Long title that cannot fit", style=TextStyle(font_size_mm=10, wrap=False)),
                       label("Line\n"*20)):
            with self.subTest(source=source), self.assertRaises(GeometryError):
                prepare_text_batch([source])

    def test_shrink_is_explicit_preserves_minimum_and_reports_resolved_sizes(self):
        source = label("HELLO WORLD", style=TextStyle(font_size_mm=8, wrap=False),
                       overflow="shrink", min_font_size_mm=1.5)
        prepared = prepare_text_batch([source]).labels[0]
        self.assertTrue(prepared.text_layout.shrunk)
        self.assertGreaterEqual(min(prepared.text_layout.font_sizes_px), 12)
        self.assertLess(max(prepared.text_layout.font_sizes_px), 64)
        self.assertLessEqual(ink(prepared)[2], 384)

    def test_shrink_never_crops_when_minimum_cannot_fit(self):
        with self.assertRaises(GeometryError):
            prepare_text_batch([label("X"*300, style=TextStyle(wrap=False), overflow="shrink")])

    def test_other_roll_and_30_fractional_labels_use_shared_pitch(self):
        for media in (Media(40,30,2), Media(50,25.125,2.04)):
            labels = [replace(label("Line\n"*(i%3)+str(i)), label_id=str(i)) for i in range(30)]
            plan = prepare_text_batch(labels, media)
            encoded = encode_batch(plan)
            self.assertEqual(sum(encoded.pitch_units), rounded(media.pitch_mm*Decimal(8)*30))
            for item, advance, pitch in zip(plan.labels, encoded.advance_units, encoded.pitch_units):
                self.assertEqual(len(item.rows)+advance, pitch)

    def test_mixed_images_and_text_share_one_setup_and_no_footer(self):
        plan = prepare_batch([label(), LabelInput(Image.new("RGB",(548,246),"black"), "image")])
        decoded = frames(encode_batch(plan).payload)
        self.assertEqual(sum(frame.opcode == 0xBE for frame in decoded), 1)
        self.assertFalse(any(frame.opcode in (0xA3,0xA0) for frame in decoded))
        self.assertEqual(encode_batch(plan).pitch_units, (216,216))
        self.assertIsNone(plan.labels[1].text_layout)

    def test_text_preview_rows_match_transmitted_black_pixels(self):
        prepared = prepare_text_batch([label()]).labels[0]
        canvas = Image.open(BytesIO(prepared.preview_png)).convert("L")
        for y, row in enumerate(prepared.rows):
            for x in range(384):
                self.assertEqual(bool(row[x//8] & (1 << (x%8))), canvas.getpixel((x,y)) == 0)

    def test_invalid_style_and_empty_text_fail_before_preparation(self):
        invalid = [dict(font_size_mm=0), dict(font_size_mm=float("nan")), dict(align="justify"),
                   dict(wrap=1), dict(bold=1), dict(line_spacing_mm=-1), dict(font_path="a.ttf",bold=True)]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ConfigurationError):
                TextStyle(**kwargs)
        for source in ("", " \n\t", "bad\x00text"):
            with self.subTest(source=source), self.assertRaises(ConfigurationError):
                label(source)
        with self.assertRaises(ConfigurationError):
            label("X", vertical_align="outside")
        with self.assertRaises(ConfigurationError):
            label("X", overflow="crop")

    def test_invalid_font_and_clipping_fail_before_print(self):
        with self.assertRaises(GeometryError):
            prepare_text_batch([label(style=TextStyle(font_path="missing-font.ttf"))])
        with self.assertRaises(GeometryError):
            prepare_text_batch([label()], calibration=Calibration(offset_x_mm=10))

    def test_text_only_helper_rejects_non_text_and_single_value(self):
        for source in (label(), ["some.png"], []):
            with self.subTest(source=source), self.assertRaises(ConfigurationError):
                prepare_text_batch(source)

    def test_font_assets_match_upstream_checksums_and_include_license(self):
        root = Path(text_module.__file__).with_name("fonts")
        provenance = json.loads((root/"UPSTREAM.json").read_text())
        for name, info in provenance["files"].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), info["sha256"])
        self.assertIn("SIL OPEN FONT LICENSE", (root/"OFL.txt").read_text())


class ExternalFieldsTests(unittest.TestCase):
    def test_external_values_keep_zeros_currency_dates_accents_and_braces(self):
        fields = {"Nombre del producto": "Café", "code": "0017", "price": "USD 7,82", "date": "17/11/2026"}
        value = format_text("{Nombre del producto}\n{code} | {price} | {date} {{literal}}", fields)
        self.assertEqual(value, "Café\n0017 | USD 7,82 | 17/11/2026 {literal}")

    def test_replacement_is_not_recursive(self):
        self.assertEqual(format_text("{name}", {"name": "{other}"}), "{other}")

    def test_missing_numeric_and_unsafe_templates_fail(self):
        for template, fields in [("{missing}", {}), ("{price}", {"price": 7.82}),
                                 ("{x.attr}", {}), ("{x[0]}", {}), ("{x!r}", {}),
                                 ("{x:.2f}", {}), ("{}", {}), ("{broken", {})]:
            with self.subTest(template=template), self.assertRaises(ConfigurationError):
                format_text(template, fields)

    def test_template_length_is_bounded(self):
        with self.assertRaises(ConfigurationError):
            format_text("{x}"*100, {"x": "a"*1000})

    def test_json_fields_and_literal_text_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            value = {"schema":1,"labels":[{"label_id":"one", "template":"Code {code}", "fields":{"code":"0017"}},
                                          {"label_id":"two", "text":"{literal}"}]}
            path.write_text(json.dumps(value), encoding="utf-8-sig")
            labels = load_text_labels(path)
            self.assertEqual(labels[0].blocks[0].text, "Code 0017")
            self.assertEqual(labels[1].blocks[0].text, "{literal}")

    def test_json_font_paths_are_relative_to_input_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            shutil.copyfile(Path(text_module.__file__).with_name("fonts")/"NotoSans-Regular.ttf", path.parent/"font.ttf")
            path.write_text(json.dumps({"schema":1,"labels":[{"label_id":"one","text":"Café","style":{"font_path":"font.ttf"}}]}))
            labels = load_text_labels(path)
            self.assertEqual(labels[0].blocks[0].style.font_path, path.parent/"font.ttf")
            self.assertTrue(prepare_text_batch(labels).labels[0].rows)

    def test_json_rejects_unknown_keys_ambiguous_content_and_numeric_fields(self):
        entries = [{"label_id":"one","text":"X","typo":1},
                   {"label_id":"one","text":"X","template":"Y"},
                   {"label_id":"one","template":"{code}","fields":{"code":17}},
                   {"label_id":"one","text":"X","style":{"typo":1}}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            for entry in entries:
                path.write_text(json.dumps({"schema":1,"labels":[entry]}))
                with self.subTest(entry=entry), self.assertRaises(ConfigurationError):
                    load_text_labels(path)


class TextCLITests(unittest.TestCase):
    def test_preview_text_outputs_geometry_without_bluetooth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            path.write_text(json.dumps({"schema":1,"labels":[{"label_id":"artículo-ñ","text":"Café 0017"}]}))
            output = StringIO()
            with patch("tinylabel_sdk.cli.LabelPrinter") as printer, redirect_stdout(output):
                result = cli(["preview-text",str(path),"--out",str(path.parent/"preview")])
            printer.assert_not_called()
            self.assertEqual(result,0)
            value = json.loads(output.getvalue())
            self.assertEqual(value["labels"][0]["label_id"], "artículo-ñ")
            self.assertTrue(output.getvalue().isascii())
            self.assertFalse(value["printed"])
            self.assertEqual(value["labels"][0]["text_layout"]["font_sizes_px"],[24])

    def test_print_text_needs_alignment_before_reading_any_input(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
            cli(["print-text","missing.json","--target","U1-TEST","--journal","unused","--job-id","job"])
        self.assertEqual(error.exception.code,2)

    def test_print_text_overflow_is_rejected_before_connecting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            path.write_text(json.dumps({"schema":1,"labels":[{"label_id":"one","text":"X"*100,"style":{"wrap":False}}]}))
            with patch("tinylabel_sdk.cli.LabelPrinter") as printer, redirect_stderr(StringIO()):
                result = cli(["print-text",str(path),"--target","U1-TEST","--journal",directory,"--job-id","job","--aligned"])
            self.assertEqual(result,2)
            printer.assert_not_called()


class TextSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_and_image_batches_keep_one_session_and_unconfirmed_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport()
            async with LabelPrinter("U1-TEST",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(Media())
                a = await printer.print_batch(prepare_batch([Image.new("RGB",(100,50),"black")]), job_id="image")
                b = await printer.print_batch(prepare_text_batch([label()]), job_id="text")
            self.assertEqual((a.state,b.state), ("transmitted_unconfirmed",)*2)
            decoded = frames(b"".join(transport.payloads))
            self.assertEqual(sum(frame.opcode == 0xBE for frame in decoded), 1)
            self.assertFalse(any(frame.opcode in (0xA3,0xA0) for frame in decoded))
