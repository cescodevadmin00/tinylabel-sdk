"""Transport adapter only. Protocol/flow interpretation lives in runtime.py."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Protocol

from .errors import ConfigurationError, PrinterNotFound
from .runtime import Monitor, TinyRuntime


class Transport(Protocol):
    async def resolve(self) -> str: ...
    async def open(self, monitor: Monitor) -> None: ...
    async def send(self, payload: bytes) -> None: ...
    async def close(self) -> None: ...


class BluetoothTransport:
    def __init__(self, target: str):
        if not isinstance(target, str) or not target.strip():
            raise ConfigurationError("An exact printer name or address is required")
        self.target, self.device = target.strip(), None
        self.connection, self.health_task = None, None

    async def resolve(self) -> str:
        from ._vendor.timiniprint.devices import PrinterCatalog
        from ._vendor.timiniprint.transport.bluetooth import BluetoothDiscovery
        catalog = PrinterCatalog.load()
        devices = await BluetoothDiscovery(catalog).scan_devices(include_classic=True, include_ble=False)
        key = self.target.replace("-", ":").casefold()
        matches = [device for device in devices if device.model_key == "u1"
                   and (device.address.casefold() == key or self.target.casefold() in
                        [name.casefold() for name in device.advertised_names])]
        if len(matches) != 1:
            raise PrinterNotFound(f"Expected one exact U1 target; found {len(matches)}")
        device = matches[0]
        stream = replace(device.profile.stream, chunk_size=180, delay_ms=4)
        self.device = device.with_print_profile(replace(device.profile, stream=stream, post_print_feed_count=0))
        return device.address.upper()

    async def open(self, monitor: Monitor):
        from ._vendor.timiniprint.transport.bluetooth import BleakBluetoothConnector
        if self.device is None:
            raise ConfigurationError("resolve() must run before open()")
        self.connection = await BleakBluetoothConnector().connect(self.device)
        try:
            await self.connection.attach_runtime_controller(TinyRuntime(monitor))
            self.health_task = asyncio.create_task(self._watch(monitor))
        except BaseException:
            await self.connection.disconnect()
            self.connection = None
            raise

    async def _watch(self, monitor: Monitor):
        try:
            while True:
                # Passive receive only: sends no status query and does not move paper.
                await self.connection.wait_for_reply("sdk passive health", lambda data: False,
                                                     timeout=0.75, required=False)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            monitor.fail(error)

    async def send(self, payload: bytes):
        if self.connection is None:
            raise ConfigurationError("Transport is not open")
        await self.connection.send_standard_payload(payload)

    async def close(self):
        if self.health_task is not None:
            task, self.health_task = self.health_task, None
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.connection is not None:
            connection, self.connection = self.connection, None
            await connection.disconnect()
