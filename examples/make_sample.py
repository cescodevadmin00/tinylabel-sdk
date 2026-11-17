"""Create synthetic artwork; no printer connection and no business data."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_sample(output):
    canvas = Image.new("RGB", (548, 246), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((4, 4, 543, 241), outline="black", width=4)
    title = ImageFont.load_default(size=52)
    body = ImageFont.load_default(size=28)
    draw.text((274, 68), "TinyLabel", font=title, fill="black", anchor="mm")
    draw.text((274, 139), "SAMPLE / MUESTRA", font=body, fill="black", anchor="mm")
    draw.text((274, 188), "50 x 25 mm", font=body, fill="black", anchor="mm")
    canvas.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=Path("sample.png"))
    make_sample(parser.parse_args().output)
