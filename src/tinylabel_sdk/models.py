from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


def positive(value: float, name: str, *, zero: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigurationError(f"{name} must be finite")
    if (value < 0 if zero else value <= 0):
        raise ConfigurationError(f"{name} must be {'nonnegative' if zero else 'positive'}")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rounded(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Media:
    width_mm: float = 50
    height_mm: float = 25
    gap_mm: float = 2

    def __post_init__(self):
        positive(self.width_mm, "width_mm")
        positive(self.height_mm, "height_mm")
        positive(self.gap_mm, "gap_mm", zero=True)
        if self.height_mm > 500 or self.gap_mm > 50:
            raise ConfigurationError("Configured limit: height <= 500 mm and gap <= 50 mm")

    @property
    def pitch_mm(self) -> Decimal:
        return Decimal(str(self.height_mm)) + Decimal(str(self.gap_mm))


@dataclass(frozen=True)
class Calibration:
    dots_per_mm: float = 8
    motion_units_per_mm: float = 8
    row_motion_units: int = 1
    head_width_dots: int = 384
    configured_max_paper_width_mm: float = 50
    margin_mm: float = 2
    offset_x_mm: float = 2
    offset_y_mm: float = -0.25
    threshold: int = 128

    def __post_init__(self):
        for name in ("dots_per_mm", "motion_units_per_mm", "configured_max_paper_width_mm"):
            positive(getattr(self, name), name)
        positive(self.margin_mm, "margin_mm", zero=True)
        for name in ("offset_x_mm", "offset_y_mm"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ConfigurationError(f"{name} must be finite")
            if abs(value) > 50:
                raise ConfigurationError(f"{name} exceeds the configured 50 mm adjustment limit")
        if not 1 <= self.dots_per_mm <= 32 or not 1 <= self.motion_units_per_mm <= 512:
            raise ConfigurationError("Calibration scale exceeds the supported configuration range")
        if self.configured_max_paper_width_mm > 1000 or self.margin_mm > 50:
            raise ConfigurationError("Configured paper/margin limit is too large")
        if self.head_width_dots != 384:
            raise ConfigurationError("This U1 adapter implements a 384-dot head")
        if type(self.row_motion_units) is not int or not 1 <= self.row_motion_units <= 16:
            raise ConfigurationError("row_motion_units must be an integer in 1..16")
        if type(self.threshold) is not int or not 1 <= self.threshold <= 254:
            raise ConfigurationError("threshold must be an integer in 1..254")


@dataclass(frozen=True)
class PrintOptions:
    darkness: int = 5
    energy: int = 8000
    speed: int = 10

    def __post_init__(self):
        for name, upper in (("darkness", 5), ("energy", 65535), ("speed", 255)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ConfigurationError(f"{name} must be an integer in 1..{upper}")


@dataclass(frozen=True)
class DrainPolicy:
    minimum_print_speed_mm_s: float = 2
    settle_after_send_s: float = 5
    quiet_s: float = 3
    poll_s: float = 0.25
    max_wait_s: float | None = None

    def __post_init__(self):
        positive(self.minimum_print_speed_mm_s, "minimum_print_speed_mm_s")
        positive(self.settle_after_send_s, "settle_after_send_s", zero=True)
        positive(self.quiet_s, "quiet_s", zero=True)
        positive(self.poll_s, "poll_s")
        if self.max_wait_s is not None:
            positive(self.max_wait_s, "max_wait_s")


@dataclass(frozen=True)
class LabelInput:
    image: Any
    label_id: str


@dataclass(frozen=True)
class PreparedLabel:
    label_id: str
    rows: tuple[bytes, ...]
    preview_png: bytes
    canvas_width: int
    canvas_height: int
    content_box: tuple[int, int, int, int]
    digest: str


@dataclass(frozen=True)
class BatchPlan:
    labels: tuple[PreparedLabel, ...]
    media: Media
    calibration: Calibration
    options: PrintOptions

    @property
    def session_key(self) -> str:
        return fingerprint({"media": asdict(self.media), "calibration": asdict(self.calibration), "options": asdict(self.options)})

    @property
    def digest(self) -> str:
        return fingerprint({"session": self.session_key, "labels": [(x.label_id, x.digest) for x in self.labels]})

    def summary(self) -> dict:
        return {"schema": 1, "digest": self.digest, "count": len(self.labels),
                "media": asdict(self.media), "calibration": asdict(self.calibration), "options": asdict(self.options),
                "labels": [{"label_id": x.label_id, "bitmap_rows": len(x.rows),
                            "canvas_px": [x.canvas_width, x.canvas_height], "content_box_px": list(x.content_box),
                            "digest": x.digest} for x in self.labels]}

    def save_previews(self, directory: str | Path) -> list[Path]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, label in enumerate(self.labels, 1):
            path = target / f"{index:04d}.png"
            path.write_bytes(label.preview_png)
            paths.append(path)
        (target / "plan.json").write_text(json.dumps(self.summary(), indent=2, ensure_ascii=False), encoding="utf-8")
        return paths


@dataclass(frozen=True)
class EncodedBatch:
    payload: bytes
    pitch_units: tuple[int, ...]
    advance_units: tuple[int, ...]
    travel_mm: float
    initialization_included: bool


def load_profile(path: str | Path) -> tuple[Media, Calibration, PrintOptions, DrainPolicy]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != 1:
        raise ConfigurationError("Unsupported profile schema")
    try:
        return (Media(**value["media"]), Calibration(**value.get("calibration", {})),
                PrintOptions(**value.get("options", {})), DrainPolicy(**value.get("drain", {})))
    except (KeyError, TypeError) as error:
        raise ConfigurationError(f"Invalid profile: {error}") from error
