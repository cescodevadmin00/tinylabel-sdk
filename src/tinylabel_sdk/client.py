from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
import time

from .errors import AlignmentRequired, ConfigurationError, DeliveryUncertain, PrinterBusy
from .journal import Journal, PrinterLock, Receipt
from .models import BatchPlan, Calibration, DrainPolicy, Media, fingerprint
from .planner import encode_batch
from .runtime import Monitor, wait_for_drain
from .transport import BluetoothTransport, Transport


class LabelPrinter:
    """One persistent, exclusively owned printer session; no auto alignment/ejection."""
    def __init__(self, target: str, *, journal_dir: str | Path, drain: DrainPolicy | None = None,
                 transport: Transport | None = None):
        if not isinstance(target, str) or not target.strip():
            raise ConfigurationError("An exact target identifier is required")
        self.target, self.journal = target, Journal(journal_dir)
        self.transport = transport if transport is not None else BluetoothTransport(target)
        self.drain = drain or DrainPolicy()
        self.monitor = Monitor()
        self.printer_id, self._lease = None, None
        self._open, self._initialized = False, False
        self._alignment, self._session_key = None, None
        self._label_index = 0
        self._mutex = asyncio.Lock()

    async def __aenter__(self):
        async with self._mutex:
            if self._open or self._lease is not None:
                raise ConfigurationError("Printer session is already open")
            self.printer_id = await self.transport.resolve()
            self._lease = PrinterLock(self.journal.directory, self.printer_id)
            try:
                self._lease.acquire()
                self.monitor = Monitor()
                self._initialized, self._session_key, self._alignment = False, None, None
                self._label_index = 0
                await self.transport.open(self.monitor)
                self._open = True
            except BaseException:
                self._lease.release()
                self._lease = None
                raise
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    def confirm_alignment(self, media: Media, *, calibration: Calibration | None = None):
        """Operator acknowledgement of an already aligned roll; performs no motion."""
        if not self._open:
            raise ConfigurationError("Open the printer session first")
        if self._initialized:
            raise AlignmentRequired("After paper movement/change, close and realign before opening a new session")
        calibration = calibration or Calibration()
        self._alignment = fingerprint({"media": asdict(media), "calibration": asdict(calibration)})
        self._label_index = 0

    async def print_batch(self, plan: BatchPlan, *, job_id: str) -> Receipt:
        async with self._mutex:
            if not self._open:
                raise ConfigurationError("Printer session is not open")
            alignment = fingerprint({"media": asdict(plan.media), "calibration": asdict(plan.calibration)})
            if alignment != self._alignment:
                raise AlignmentRequired("Confirm the physical origin for this media/calibration before printing")
            if self._initialized and self._session_key != plan.session_key:
                raise AlignmentRequired("Media/options changed; use a freshly aligned session")
            self.monitor.check()
            encoded = encode_batch(plan, start_index=self._label_index, initialize=not self._initialized)
            self.journal.reserve(job_id, plan.digest, self.printer_id, tuple(x.label_id for x in plan.labels))
            self.journal.update(job_id, state="sending", payload_bytes=len(encoded.payload))
            self._initialized, self._session_key = True, plan.session_key
            started = time.monotonic()
            try:
                await self.transport.send(encoded.payload)
                sent_at = time.monotonic()
                self._label_index += len(plan.labels)
                self.journal.update(job_id, transmitted=True)
                waited = await wait_for_drain(self.monitor, started=started, sent_at=sent_at,
                                              travel_mm=encoded.travel_mm, policy=self.drain)
                return self.journal.update(job_id, state="transmitted_unconfirmed", drain_wait_s=waited,
                    position_after="expected_next_label_start",
                    note="Passive drain estimate completed; U1 has no verified per-label completion acknowledgement")
            except BaseException as error:
                self._alignment = None
                try:
                    self.journal.update(job_id, state="uncertain", position_after="unknown", error_type=type(error).__name__,
                                        note="Some or all labels may have printed; never replay this job automatically")
                finally:
                    # Release the device even if the journal disk becomes unavailable.
                    try:
                        await self._disconnect()
                    except BaseException as cleanup_error:
                        if isinstance(error, asyncio.CancelledError):
                            raise error from cleanup_error
                if isinstance(error, asyncio.CancelledError):
                    raise
                raise DeliveryUncertain(job_id, error) from error

    async def _disconnect(self):
        try:
            await self.transport.close()
        finally:
            self._open = False
            self._alignment = None
            if self._lease is not None:
                self._lease.release()
                self._lease = None

    def confirm_delivery(self, job_id: str, *, printed_label_ids: list[str] | tuple[str, ...],
                         alignment_ok: bool, note: str = "") -> Receipt:
        """Record an operator observation, never an inference from transport success."""
        if self._mutex.locked():
            raise PrinterBusy("Wait for the current operation before recording delivery")
        receipt = self.journal.confirm(job_id, printed_label_ids=printed_label_ids,
                                       alignment_ok=alignment_ok, note=note)
        if not alignment_ok or receipt.state == "partial_confirmed":
            self._alignment = None
        return receipt

    async def aclose(self):
        async with self._mutex:
            if self._open or self._lease is not None:
                await self._disconnect()
