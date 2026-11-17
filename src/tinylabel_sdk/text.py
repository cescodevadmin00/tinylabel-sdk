"""Raster text labels and flat external fields. No spreadsheet reader or device I/O."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
import json
import math
from pathlib import Path
from string import Formatter

from PIL import Image, ImageDraw, ImageFont

from .errors import ConfigurationError, GeometryError
from .models import Calibration, Media, TextLayout, positive, rounded
from .raster import finish, geometry

MAX_TEXT_CHARS = 10_000


def _check_text(text: str):
    if not isinstance(text, str) or len(text) > MAX_TEXT_CHARS:
        raise ConfigurationError("Text must be a string of at most 10000 characters")
    if any(ord(char) < 32 and char not in "\n\t\r" for char in text):
        raise ConfigurationError("Text contains unsupported control characters")


def format_text(template: str, fields: Mapping[str, str]) -> str:
    """Substitute flat {field} names; caller formats amounts, dates and identifiers."""
    _check_text(template)
    if not isinstance(fields, Mapping):
        raise ConfigurationError("fields must be a mapping of names to preformatted strings")
    result, length = [], 0
    try:
        for literal, name, spec, conversion in Formatter().parse(template):
            result.append(literal)
            length += len(literal)
            if name is None:
                continue
            if not name or any(char in name for char in ".[]{}") or spec or conversion:
                raise ConfigurationError("Use flat {field} names without indexing, conversion or format specs")
            if name not in fields:
                raise ConfigurationError(f"Missing text field: {name}")
            value = fields[name]
            _check_text(value)
            result.append(value)
            length += len(value)
            if length > MAX_TEXT_CHARS:
                raise ConfigurationError("Formatted text exceeds 10000 characters")
        text = "".join(result)
    except ValueError as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError(f"Invalid text template: {error}") from error
    _check_text(text)
    return text


@dataclass(frozen=True)
class TextStyle:
    font_size_mm: float = 3
    font_path: str | Path | None = None
    align: str = "center"
    line_spacing_mm: float = 0.5
    wrap: bool = True
    bold: bool = False

    def __post_init__(self):
        positive(self.font_size_mm, "font_size_mm")
        positive(self.line_spacing_mm, "line_spacing_mm", zero=True)
        if self.font_size_mm > 50 or self.line_spacing_mm > 50:
            raise ConfigurationError("Text font size/spacing exceed the 50 mm configuration limit")
        if self.font_path is not None and (not isinstance(self.font_path, (str, Path)) or not str(self.font_path)):
            raise ConfigurationError("font_path must be a local font path")
        if self.align not in ("left", "center", "right") or type(self.wrap) is not bool or type(self.bold) is not bool:
            raise ConfigurationError("Text align must be left/center/right; wrap/bold must be bools")
        if self.font_path is not None and self.bold:
            raise ConfigurationError("For custom fonts select the bold font file explicitly, leaving bold=False")


@dataclass(frozen=True)
class TextBlock:
    text: str
    style: TextStyle = field(default_factory=TextStyle)
    gap_after_mm: float = 0.75

    def __post_init__(self):
        _check_text(self.text)
        if not isinstance(self.style, TextStyle):
            raise ConfigurationError("style must be a TextStyle")
        positive(self.gap_after_mm, "gap_after_mm", zero=True)
        if self.gap_after_mm > 50:
            raise ConfigurationError("gap_after_mm exceeds 50 mm")


@dataclass(frozen=True)
class TextLabel:
    label_id: str
    blocks: tuple[TextBlock, ...]
    vertical_align: str = "center"
    overflow: str = "error"
    min_font_size_mm: float = 1.5

    def __post_init__(self):
        if not isinstance(self.label_id, str) or not self.label_id.strip() or len(self.label_id) > 256:
            raise ConfigurationError("label_id must be a nonempty string of at most 256 characters")
        if not isinstance(self.blocks, (tuple, list)) or not 1 <= len(self.blocks) <= 100:
            raise ConfigurationError("Use 1..100 text blocks per label")
        if not all(isinstance(block, TextBlock) for block in self.blocks):
            raise ConfigurationError("blocks must contain TextBlock instances")
        object.__setattr__(self, "blocks", tuple(self.blocks))
        if sum(len(block.text) for block in self.blocks) > MAX_TEXT_CHARS:
            raise ConfigurationError("A text label may contain at most 10000 characters")
        if not any(block.text.strip() for block in self.blocks):
            raise ConfigurationError("A text label needs visible text")
        if self.vertical_align not in ("top", "center", "bottom") or self.overflow not in ("error", "shrink"):
            raise ConfigurationError("Use vertical_align top/center/bottom and overflow error/shrink")
        positive(self.min_font_size_mm, "min_font_size_mm")
        if self.overflow == "shrink" and any(block.style.font_size_mm < self.min_font_size_mm for block in self.blocks):
            raise ConfigurationError("min_font_size_mm must not exceed any requested block font size")

    @classmethod
    def from_text(cls, text: str, label_id: str, *, style: TextStyle | None = None, **kwargs) -> TextLabel:
        return cls(label_id, (TextBlock(text, TextStyle() if style is None else style),), **kwargs)


def _font(style: TextStyle, size: int):
    try:
        path = style.font_path or Path(__file__).with_name("fonts") / ("NotoSans-Bold.ttf" if style.bold else "NotoSans-Regular.ttf")
        return ImageFont.truetype(str(path), size)
    except (OSError, ValueError) as error:
        raise GeometryError(f"Cannot load text font: {style.font_path}") from error


def _lines(text: str, font, max_width: int, wrap: bool) -> list[str]:
    def width(value):
        box = font.getbbox(value)
        return box[2]-box[0]

    result = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n"):
        if not wrap:
            result.append(paragraph)
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if width(candidate) <= max_width:
                current = candidate
                continue
            if current:
                result.append(current)
                current = ""
            # Hard-wrap identifiers longer than a line instead of cropping them.
            for char in word:
                if width(current+char) > max_width:
                    if not current:
                        raise GeometryError("A text glyph exceeds the available width")
                    result.append(current)
                    current = ""
                current += char
        result.append(current)
    return result


def _layout(label: TextLabel, sizes: tuple[int, ...], width: int, scale: Decimal, fonts: dict):
    lines, cursor, top, bottom = [], 0, None, None
    for block, size in zip(label.blocks, sizes):
        key = (str(block.style.font_path), block.style.bold, size)
        if key not in fonts:
            fonts[key] = _font(block.style, size)
        font = fonts[key]
        ascent, descent = font.getmetrics()
        spacing = rounded(Decimal(str(block.style.line_spacing_mm))*scale)
        wrapped = _lines(block.text, font, width, block.style.wrap)
        for index, text in enumerate(wrapped):
            box = font.getbbox(text, anchor="ls")
            ink_width = box[2]-box[0]
            if ink_width > width:
                raise GeometryError("Text exceeds the available width with wrapping disabled")
            baseline = cursor+ascent
            x = {"left": 0, "center": (width-ink_width)//2, "right": width-ink_width}[block.style.align]-box[0]
            lines.append((text, font, x, baseline))
            if box[3] > box[1]:
                top = baseline+box[1] if top is None else min(top, baseline+box[1])
                bottom = baseline+box[3] if bottom is None else max(bottom, baseline+box[3])
            cursor += ascent+descent
            if index < len(wrapped)-1:
                cursor += spacing
        cursor += rounded(Decimal(str(block.gap_after_mm))*scale)
    if top is None or bottom is None:
        raise GeometryError("Text produces no visible glyphs with this font")
    return lines, top, bottom-top


def render_text_label(label: TextLabel, media: Media, calibration: Calibration):
    width, height, margin, head_left = geometry(media, calibration)
    scale = Decimal(str(calibration.dots_per_mm))
    area_width, area_height = width-2*margin, height-2*margin
    area_x = margin+rounded(Decimal(str(calibration.offset_x_mm))*scale)
    area_y = margin+rounded(Decimal(str(calibration.offset_y_mm))*scale)
    if area_x < 0 or area_y < 0 or area_x+area_width > width or area_y+area_height > height:
        raise GeometryError("Text area would clip the label; adjust calibration offsets or margins")
    requested = tuple(max(1, rounded(Decimal(str(block.style.font_size_mm))*scale)) for block in label.blocks)
    minimum = max(1, math.ceil(Decimal(str(label.min_font_size_mm))*scale))
    # One common scale preserves the hierarchy. Font sizes never go below the floor.
    fonts = {(str(block.style.font_path), block.style.bold, size): _font(block.style, size)
             for block, size in zip(label.blocks, requested)}
    last_error = None
    for largest in range(max(requested), 0, -1):
        sizes = tuple(max(1, rounded(Decimal(size)*largest/ max(requested))) for size in requested)
        if label.overflow == "shrink" and min(sizes) < minimum:
            break
        if largest != max(requested):
            # Keep only this attempt's font faces, even for a large shrink search.
            fonts = {}
        try:
            lines, ink_top, ink_height = _layout(label, sizes, area_width, scale, fonts)
            if ink_height > area_height:
                raise GeometryError("Text exceeds the available height")
            break
        except GeometryError as error:
            last_error = GeometryError(str(error))
            if label.overflow != "shrink":
                raise
    else:
        raise GeometryError("Text cannot fit the selected label") from last_error
    if label.overflow == "shrink" and min(sizes) < minimum:
        raise GeometryError("Text cannot fit without going below min_font_size_mm") from last_error
    y_offset = {"top": 0, "center": (area_height-ink_height)//2, "bottom": area_height-ink_height}[label.vertical_align]
    canvas = Image.new("L", (calibration.head_width_dots, height), 255)
    draw = ImageDraw.Draw(canvas)
    for text, font, x, baseline in lines:
        draw.text((head_left+area_x+x, area_y+y_offset+baseline-ink_top), text, font=font, fill=0, anchor="ls")
    ink = Image.eval(canvas, lambda value: 255-value).getbbox()
    if ink is None:
        raise GeometryError("Text produces no visible glyphs")
    result = finish(canvas, label.label_id, (ink[0], ink[1], ink[2]-ink[0], ink[3]-ink[1]), calibration)
    if not result.rows:
        raise GeometryError("Text has no black dots at this font size/threshold")
    return replace(result, text_layout=TextLayout(sizes, len(lines), sizes != requested,
        (head_left+area_x, area_y, area_width, area_height), label.vertical_align))


def prepare_text_batch(labels, media=None, *, calibration=None, options=None):
    """Prepare TextLabel values using the same geometry and wire plan as images."""
    from .planner import prepare_batch
    if isinstance(labels, (TextLabel, str, bytes)):
        raise ConfigurationError("Pass a sequence of TextLabel values")

    def checked():
        for label in labels:
            if not isinstance(label, TextLabel):
                raise ConfigurationError("prepare_text_batch accepts only TextLabel values")
            yield label
    return prepare_batch(checked(), media, calibration=calibration, options=options)


def load_text_labels(path: str | Path) -> tuple[TextLabel, ...]:
    """Load external JSON text definitions; paths to fonts are relative to this file."""
    path = Path(path)
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or set(value) != {"schema", "labels"} or type(value["schema"]) is not int or value["schema"] != 1:
        raise ConfigurationError("Text JSON requires schema=1 and labels")
    if not isinstance(value["labels"], list) or not 1 <= len(value["labels"]) <= 500:
        raise ConfigurationError("Text JSON requires 1..500 label definitions")
    labels = []
    for entry in value["labels"]:
        try:
            data = dict(entry)
            fields = data.pop("fields", {})
            if not isinstance(fields, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in fields.items()):
                raise ConfigurationError("fields must contain preformatted string values")
            if "blocks" in data:
                blocks = data.pop("blocks")
            else:
                blocks = [{key: data.pop(key) for key in ("text", "template", "style") if key in data}]
            if not isinstance(blocks, list) or not 1 <= len(blocks) <= 100:
                raise ConfigurationError("Use a nonempty blocks array")
            rendered = []
            for block in blocks:
                block = dict(block)
                if ("text" in block) == ("template" in block):
                    raise ConfigurationError("Each text block requires exactly one text or template")
                text = block.pop("text") if "text" in block else format_text(block.pop("template"), fields)
                style = dict(block.pop("style", {}))
                if style.get("font_path") is not None:
                    style["font_path"] = path.parent / style["font_path"]
                rendered.append(TextBlock(text, TextStyle(**style), **block))
            labels.append(TextLabel(blocks=tuple(rendered), **data))
        except (TypeError, ValueError) as error:
            if isinstance(error, ConfigurationError):
                raise
            raise ConfigurationError(f"Invalid text label definition: {error}") from error
    return tuple(labels)
