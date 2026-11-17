"""Passive Tiny flow/status observation and conservative drain estimate."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import threading
import time

from .codec import Decoder
from .errors import DrainTimeout, PrinterFault
from .models import DrainPolicy


@dataclass(frozen=True)
class Snapshot:
    paused: bool
    busy: bool
    last_activity: float
    error: BaseException | None


class Monitor:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self.paused, self.busy = False, False
        self.last_activity = clock()
        self.error = None

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(self.paused, self.busy, self.last_activity, self.error)

    def fail(self, error: BaseException):
        with self._lock:
            self.error = error
            self.last_activity = self.clock()

    def check(self):
        error = self.snapshot().error
        if error is not None:
            raise error


class TinyRuntime:
    """Duck-types the pinned upstream runtime callback; no printing lifecycle hooks."""
    def __init__(self, monitor: Monitor):
        self.monitor, self.decoder = monitor, Decoder()

    def handle_notification(self, session, payload: bytes):
        with self.monitor._lock:
            self.monitor.last_activity = self.monitor.clock()
        for frame in self.decoder.feed(payload):
            if not frame.response:
                continue
            if frame.opcode == 0xAE and frame.data in (b"\x10", b"\x00"):
                paused = frame.data == b"\x10"
                with self.monitor._lock:
                    self.monitor.paused = paused
                session.set_flow_paused(paused, payload=payload)
            if frame.opcode == 0xA3 and frame.data:
                status = frame.data[0]
                with self.monitor._lock:
                    self.monitor.busy = bool(status & 0x80)
                if status & 0x0F:
                    error = PrinterFault(f"Printer reported fault bits 0x{status & 0x0F:02x}")
                    self.monitor.fail(error)
                    # The upstream Classic receive hub aborts the writer on listener errors.
                    raise error

    async def before_write(self, session, *, size: int, timeout: float):
        self.monitor.check()
        return None

    async def stop(self, session):
        """Upstream Classic detach hook. No queries, feed, or reverse on close."""
        return None


async def wait_for_drain(monitor: Monitor, *, started: float, sent_at: float, travel_mm: float,
                         policy: DrainPolicy, clock=time.monotonic, sleep=asyncio.sleep) -> float:
    duration = travel_mm / policy.minimum_print_speed_mm_s
    not_before = max(started+duration, sent_at+policy.settle_after_send_s)
    deadline = sent_at + (policy.max_wait_s if policy.max_wait_s is not None else max(60, duration+30))
    while True:
        monitor.check()
        now = clock()
        state = monitor.snapshot()
        if now >= not_before and not state.paused and not state.busy and now-state.last_activity >= policy.quiet_s:
            return max(0, now-sent_at)
        if now >= deadline:
            raise DrainTimeout("Passive drain did not settle; physical delivery remains uncertain")
        await sleep(min(policy.poll_s, max(0.001, deadline-now)))
