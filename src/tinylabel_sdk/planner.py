from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

from .codec import packet
from .errors import ConfigurationError, GeometryError
from .models import BatchPlan, Calibration, EncodedBatch, LabelInput, Media, PreparedLabel, PrintOptions, rounded
from .raster import finish, geometry
from .text import TextLabel, render_text_label

MAX_LABELS = 500
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024


def _image(value) -> Image.Image:
    if isinstance(value, Image.Image):
        if getattr(value, "n_frames", 1) != 1:
            raise GeometryError("Use one static image per label")
        original = value.copy()
    else:
        stream = BytesIO(value) if isinstance(value, bytes) else value
        with Image.open(stream) as opened:
            if getattr(opened, "n_frames", 1) != 1:
                raise GeometryError("Use one static image per label")
            original = ImageOps.exif_transpose(opened).convert("RGBA")
    if original.width * original.height > 25_000_000:
        raise GeometryError("Image exceeds 25 megapixels")
    rgba = ImageOps.exif_transpose(original).convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    return white.convert("L")


def _render(label: LabelInput, media: Media, calibration: Calibration) -> PreparedLabel:
    width, height, margin, head_left = geometry(media, calibration)
    scale = Decimal(str(calibration.dots_per_mm))
    try:
        source_image = _image(label.image)
    except (OSError, ValueError) as error:
        if isinstance(error, ConfigurationError):
            raise
        raise GeometryError(f"Cannot decode label {label.label_id!r}") from error
    fitted = ImageOps.contain(source_image, (width-2*margin, height-2*margin), Image.Resampling.LANCZOS)
    x = (width-fitted.width)//2 + rounded(Decimal(str(calibration.offset_x_mm))*scale)
    y = (height-fitted.height)//2 + rounded(Decimal(str(calibration.offset_y_mm))*scale)
    if x < 0 or y < 0 or x+fitted.width > width or y+fitted.height > height:
        raise GeometryError("Calibration would clip the image; adjust offsets or margins")
    canvas = Image.new("L", (calibration.head_width_dots, height), 255)
    canvas.paste(fitted, (head_left+x, y))
    return finish(canvas, label.label_id, (head_left+x, y, fitted.width, fitted.height), calibration)


def prepare_batch(images: Iterable, media: Media | None = None, *, calibration: Calibration | None = None,
                  options: PrintOptions | None = None) -> BatchPlan:
    """Pure preparation: no Bluetooth, file journal or paper movement."""
    media, calibration, options = media or Media(), calibration or Calibration(), options or PrintOptions()
    if isinstance(images, (str, bytes, Path, Image.Image, TextLabel)):
        raise ConfigurationError("Pass a sequence of images, not a single image/path")
    labels = []
    estimated_bytes = 0
    for index, source in enumerate(images):
        if index >= MAX_LABELS:
            raise ConfigurationError(f"At most {MAX_LABELS} labels per batch")
        if isinstance(source, (LabelInput, TextLabel)):
            label = source
        else:
            label = LabelInput(source, Path(source).name if isinstance(source, (str, Path)) else str(index+1))
        if not isinstance(label.label_id, str) or not label.label_id.strip() or len(label.label_id) > 256:
            raise ConfigurationError("Each label needs a nonempty label_id of at most 256 characters")
        rendered = render_text_label(label, media, calibration) if isinstance(label, TextLabel) else _render(label, media, calibration)
        estimated_bytes += len(rendered.rows)*56+10
        if estimated_bytes > MAX_PAYLOAD_BYTES:
            raise ConfigurationError("Prepared batch exceeds the 64 MiB wire limit")
        labels.append(rendered)
    if not labels:
        raise ConfigurationError("At least one label is required")
    if len({label.label_id for label in labels}) != len(labels):
        raise ConfigurationError("label_id values must be unique within a batch")
    plan = BatchPlan(tuple(labels), media, calibration, options)
    encode_batch(plan)  # Validate travel and size before allowing any I/O.
    return plan


def encode_batch(plan: BatchPlan, *, start_index: int = 0, initialize: bool = True) -> EncodedBatch:
    if type(start_index) is not int or start_index < 0:
        raise ConfigurationError("start_index must be a nonnegative integer")
    scale = Decimal(str(plan.calibration.motion_units_per_mm))
    pitch = plan.media.pitch_mm * scale
    output = bytearray()
    if initialize:
        output += packet(0xA4, bytes([0x30+plan.options.darkness]))
        output += packet(0xAF, plan.options.energy.to_bytes(2, "little"))
        output += packet(0xBE, b"\x01")
        output += packet(0xBD, bytes([plan.options.speed]))
    pitches, advances = [], []
    for index, label in enumerate(plan.labels, start_index):
        stride = rounded((index+1)*pitch)-rounded(index*pitch)
        advance = stride-len(label.rows)*plan.calibration.row_motion_units
        if advance < 0:
            raise GeometryError("Bitmap exceeds the calibrated media pitch")
        for row in label.rows:
            output += packet(0xA2, row)
        remaining = advance
        while remaining:
            part = min(remaining, 65535)
            output += packet(0xA1, part.to_bytes(2, "little"))
            remaining -= part
        pitches.append(stride)
        advances.append(advance)
        if len(output) > MAX_PAYLOAD_BYTES:
            raise ConfigurationError("Encoded batch exceeds 64 MiB")
    # Intentionally no A3 query, paper ejection, reverse or mode reset at the end.
    return EncodedBatch(bytes(output), tuple(pitches), tuple(advances), float(sum(pitches)/scale), initialize)
