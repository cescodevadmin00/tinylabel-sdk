"""Durable attempted-job IDs and OS printer lock; no automatic replay."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from .errors import ConfigurationError, DuplicateJob, PrinterBusy


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Receipt:
    job_id: str
    plan_digest: str
    printer_id: str
    state: str
    label_ids: tuple[str, ...]
    created_at: str
    updated_at: str
    transmitted: bool = False
    confirmed_label_ids: tuple[str, ...] | None = None
    physical_alignment_ok: bool | None = None
    position_after: str = "unknown"
    error_type: str | None = None
    payload_bytes: int = 0
    drain_wait_s: float = 0
    note: str = ""

    @property
    def requires_confirmation(self) -> bool:
        return self.state not in ("confirmed", "partial_confirmed")

    def to_dict(self) -> dict:
        value = asdict(self)
        value["requested_count"] = len(self.label_ids)
        value["requires_confirmation"] = self.requires_confirmation
        return value


class Journal:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "jobs.sqlite3"
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, receipt TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _decode(value: str) -> Receipt:
        raw = json.loads(value)
        raw["label_ids"] = tuple(raw["label_ids"])
        if raw.get("confirmed_label_ids") is not None:
            raw["confirmed_label_ids"] = tuple(raw["confirmed_label_ids"])
        return Receipt(**raw)

    def get(self, job_id: str) -> Receipt | None:
        with self._connect() as db:
            row = db.execute("SELECT receipt FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return None if row is None else self._decode(row[0])

    def reserve(self, job_id: str, digest: str, printer_id: str, label_ids: tuple[str, ...]) -> Receipt:
        if not isinstance(job_id, str) or not job_id.strip() or job_id != job_id.strip() or len(job_id) > 128:
            raise ConfigurationError("job_id must be a stable, nonempty string of at most 128 characters")
        stamp = utc()
        receipt = Receipt(job_id, digest, printer_id, "reserved", label_ids, stamp, stamp)
        try:
            with self._connect() as db:
                db.execute("INSERT INTO jobs VALUES (?,?)", (job_id, json.dumps(asdict(receipt))))
        except sqlite3.IntegrityError:
            raise DuplicateJob(job_id, self.get(job_id)) from None
        return receipt

    def update(self, job_id: str, **changes) -> Receipt:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT receipt FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            value = asdict(self._decode(row[0]))
            unknown = set(changes)-set(value)
            if unknown or {"job_id", "plan_digest", "printer_id", "label_ids", "created_at"} & changes.keys():
                raise ConfigurationError("Cannot change receipt identity")
            value.update(changes, updated_at=utc())
            receipt = Receipt(**value)
            db.execute("UPDATE jobs SET receipt=? WHERE job_id=?", (json.dumps(asdict(receipt)), job_id))
        return receipt

    def confirm(self, job_id: str, *, printed_label_ids: list[str] | tuple[str, ...],
                alignment_ok: bool, note: str = "") -> Receipt:
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        if current.state not in ("transmitted_unconfirmed", "uncertain", "confirmed", "partial_confirmed"):
            raise ConfigurationError("Cannot confirm a job while it is being sent")
        ids = tuple(printed_label_ids)
        if len(set(ids)) != len(ids) or not set(ids).issubset(current.label_ids):
            raise ConfigurationError("Confirmed label IDs must be a unique subset of the requested labels")
        if type(alignment_ok) is not bool:
            raise ConfigurationError("alignment_ok must be a bool")
        state = "confirmed" if set(ids) == set(current.label_ids) else "partial_confirmed"
        return self.update(job_id, state=state, confirmed_label_ids=ids,
                           physical_alignment_ok=alignment_ok, note=note)

    def recover_interrupted(self, job_id: str, *, note: str = "") -> Receipt:
        """Explicitly classify an orphaned reservation/send; never connects or replays."""
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        lease = PrinterLock(self.directory, current.printer_id)
        lease.acquire()
        try:
            current = self.get(job_id)
            if current.state not in ("reserved", "sending"):
                raise ConfigurationError("Only abandoned reserved/sending jobs need recovery")
            return self.update(job_id, state="uncertain", position_after="unknown",
                error_type="InterruptedWorker", note=note or "Operator recovered an interrupted worker; inspect physical output")
        finally:
            lease.release()


class PrinterLock:
    def __init__(self, directory: Path, printer_id: str):
        key = hashlib.sha256(printer_id.upper().encode()).hexdigest()
        self.path = directory / f"printer-{key}.lock"
        self.file = None

    def acquire(self):
        stream = self.path.open("a+b")
        try:
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise PrinterBusy("Another worker owns this printer; share one journal directory") from None
        self.file = stream

    def release(self):
        if self.file is not None:
            stream, self.file = self.file, None
            try:
                stream.seek(0)
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            finally:
                stream.close()
