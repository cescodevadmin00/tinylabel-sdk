"""Shared physical canvas and row packing for images and text."""
from decimal import Decimal, ROUND_FLOOR
import hashlib
from io import BytesIO

from PIL import Image

from .errors import GeometryError
from .models import Calibration, Media, PreparedLabel, rounded


def geometry(media: Media, calibration: Calibration) -> tuple[int, int, int, int]:
    if media.width_mm > calibration.configured_max_paper_width_mm:
        raise GeometryError("Paper width exceeds the configured hardware limit")
    scale = Decimal(str(calibration.dots_per_mm))
    width = min(int((Decimal(str(media.width_mm))*scale).to_integral_value(rounding=ROUND_FLOOR)), calibration.head_width_dots)
    height = int((Decimal(str(media.height_mm))*scale).to_integral_value(rounding=ROUND_FLOOR))
    margin = rounded(Decimal(str(calibration.margin_mm))*scale)
    if min(width, height) < 1 or width <= 2*margin or height <= 2*margin:
        raise GeometryError("Media is too small for the selected margins")
    return width, height, margin, (calibration.head_width_dots-width)//2


def finish(canvas: Image.Image, label_id: str, content_box: tuple[int, int, int, int],
           calibration: Calibration) -> PreparedLabel:
    canvas = canvas.point(lambda value: 0 if value < calibration.threshold else 255)
    pixels = canvas.tobytes()
    row_bytes = calibration.head_width_dots//8
    rows = []
    for row in range(canvas.height):
        packed = bytearray(row_bytes)
        for col, value in enumerate(pixels[row*canvas.width:(row+1)*canvas.width]):
            if value == 0:
                packed[col//8] |= 1 << (col % 8)
        rows.append(bytes(packed))
    while rows and not any(rows[-1]):
        rows.pop()
    output = BytesIO()
    canvas.save(output, format="PNG", dpi=(calibration.dots_per_mm*25.4,)*2)
    return PreparedLabel(label_id, tuple(rows), output.getvalue(), canvas.width, canvas.height,
                         content_box, hashlib.sha256(pixels).hexdigest())
