import asyncio
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from decimal import Decimal
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from PIL import Image, ImageDraw

from tinylabel_sdk import (Calibration, DrainPolicy, Journal, LabelInput, LabelPrinter,
                           Media, PrintOptions, encode_batch, prepare_batch)
from tinylabel_sdk.cli import main as cli
from tinylabel_sdk.codec import Decoder, packet
from tinylabel_sdk.errors import (AlignmentRequired, ConfigurationError, DeliveryUncertain,
                                 DrainTimeout, DuplicateJob, GeometryError, PrinterBusy, PrinterFault)
from tinylabel_sdk.models import rounded
from tinylabel_sdk.runtime import Monitor, TinyRuntime, wait_for_drain
from tinylabel_sdk.transport import BluetoothTransport


def image():
    canvas = Image.new("RGBA", (548,246), "white")
    ImageDraw.Draw(canvas).rectangle((5,3,540,240), fill="black")
    return canvas


def plan(media=None, calibration=None, count=1):
    return prepare_batch([LabelInput(image(), f"label-{i}") for i in range(count)], media,
                         calibration=calibration)


def frames(data):
    decoder = Decoder()
    result = decoder.feed(data)
    assert not decoder.buffer
    return result


FAST = DrainPolicy(minimum_print_speed_mm_s=1e9, settle_after_send_s=0, quiet_s=0, poll_s=0.001)


class FakeTransport:
    def __init__(self, *, fail=False, block=False):
        self.payloads, self.closed, self.opened = [], False, False
        self.fail, self.block = fail, block
        self.entered = asyncio.Event()

    async def resolve(self):
        return "02:00:00:00:00:01"

    async def open(self, monitor):
        self.monitor, self.opened, self.closed = monitor, True, False

    async def send(self, data):
        self.payloads.append(data)
        self.entered.set()
        if self.fail:
            raise ConnectionError("simulated disconnect after bytes may have been written")
        if self.block:
            await asyncio.Event().wait()

    async def close(self):
        self.closed = True


class AdapterContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_detaches_through_real_upstream_backend_without_commands(self):
        from tinylabel_sdk._vendor.timiniprint.transport.bluetooth.backend import SppBackend
        backend = SppBackend()
        backend._classic_runtime_controller = TinyRuntime(Monitor())
        await backend._stop_classic_runtime_controller()
        self.assertIsNone(backend._classic_runtime_controller)

    async def test_exact_u1_discovery_uses_real_catalog_and_stream_settings(self):
        from tinylabel_sdk._vendor.timiniprint.devices import PrinterCatalog
        from tinylabel_sdk._vendor.timiniprint.transport.bluetooth import BluetoothDiscovery
        from tinylabel_sdk._vendor.timiniprint.transport.bluetooth.types import DeviceInfo
        discovery = BluetoothDiscovery(PrinterCatalog.load())
        devices = discovery.devices_from_scan([DeviceInfo("U1-TEST", "02:00:00:00:00:01", True)])
        self.assertEqual(len(devices), 1)
        with patch.object(BluetoothDiscovery, "scan_devices", new_callable=AsyncMock, return_value=devices) as scan:
            transport = BluetoothTransport("U1-TEST")
            self.assertEqual(await transport.resolve(), "02:00:00:00:00:01")
            self.assertEqual(transport.device.profile.stream.chunk_size, 180)
            self.assertEqual(transport.device.profile.stream.delay_ms, 4)
            self.assertEqual(transport.device.profile.post_print_feed_count, 0)
            scan.assert_awaited_once_with(include_classic=True, include_ble=False)
            from tinylabel_sdk.errors import PrinterNotFound
            with self.assertRaises(PrinterNotFound):
                await BluetoothTransport("U1-WRONG").resolve()

    async def test_open_watch_and_close_send_no_implicit_payload(self):
        from tinylabel_sdk._vendor.timiniprint.transport.bluetooth import BleakBluetoothConnector
        connection = AsyncMock()
        connection.wait_for_reply.side_effect = lambda *a, **kw: None
        transport = BluetoothTransport("U1-TEST")
        transport.device = object()
        with patch.object(BleakBluetoothConnector, "connect", new_callable=AsyncMock, return_value=connection):
            await transport.open(Monitor())
            await transport.close()
        connection.attach_runtime_controller.assert_awaited_once()
        connection.disconnect.assert_awaited_once()
        connection.send_standard_payload.assert_not_awaited()
        connection.send_control_packet.assert_not_awaited()


class GeometryTests(unittest.TestCase):
    def test_current_layout_and_default_pitch(self):
        prepared = plan()
        self.assertEqual(prepared.labels[0].content_box, (32,19,352,158))
        self.assertEqual(prepared.labels[0].canvas_height, 200)
        encoded = encode_batch(prepared)
        self.assertEqual(encoded.pitch_units, (216,))
        self.assertEqual(len(prepared.labels[0].rows)+encoded.advance_units[0], 216)

    def test_other_size_is_computed_not_hardcoded(self):
        prepared = plan(Media(40,30,2))
        encoded = encode_batch(prepared)
        self.assertEqual(prepared.labels[0].canvas_height, 240)
        self.assertEqual(encoded.pitch_units, (256,))
        self.assertNotEqual(encoded.advance_units, (42,))
        x,y,w,h = prepared.labels[0].content_box
        self.assertTrue(0 <= x < x+w <= 384 and 0 <= y < y+h <= 240)

    def test_30_fractional_pitches_bound_total_rounding(self):
        media = Media(50,25.125,2.04)
        prepared = plan(media, count=30)
        encoded = encode_batch(prepared)
        exact = media.pitch_mm*Decimal(8)*30
        self.assertEqual(sum(encoded.pitch_units), rounded(exact))
        self.assertLessEqual(abs(Decimal(sum(encoded.pitch_units))-exact), Decimal("0.5"))

    def test_fractional_pitch_keeps_phase_across_calls(self):
        prepared = plan(Media(50,25.125,2.04))
        separate = [encode_batch(prepared,start_index=i).pitch_units[0] for i in range(30)]
        together = encode_batch(plan(prepared.media,count=30)).pitch_units
        self.assertEqual(tuple(separate), together)

    def test_no_queries_reverse_or_ejection_in_batch(self):
        prepared = plan(count=8)
        decoded = frames(encode_batch(prepared).payload)
        self.assertEqual(sum(frame.opcode == 0xBE for frame in decoded), 1)
        self.assertEqual(sum(frame.opcode == 0xA4 for frame in decoded), 1)
        self.assertFalse(any(frame.opcode in (0xA3,0xA0) for frame in decoded))
        self.assertEqual(sum(frame.opcode == 0xA1 for frame in decoded), 8)
        self.assertEqual(sum(encode_batch(prepared).pitch_units), 216*8)

    def test_resume_payload_has_no_new_mode(self):
        decoded = frames(encode_batch(plan(), initialize=False).payload)
        self.assertTrue(all(frame.opcode in (0xA2,0xA1) for frame in decoded))

    def test_fully_blank_label_advances_without_bitmap(self):
        prepared = prepare_batch([Image.new("RGBA",(100,100),(0,0,0,0))])
        encoded = encode_batch(prepared)
        self.assertEqual(prepared.labels[0].rows, ())
        self.assertEqual(encoded.advance_units, (216,))
        self.assertFalse(any(frame.opcode == 0xA2 for frame in frames(encoded.payload)))

    def test_invalid_sizes_and_options(self):
        for value in (0,-1,float("nan"),float("inf"),True):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                Media(height_mm=value)
        with self.assertRaises(ConfigurationError):
            PrintOptions(darkness=6)
        with self.assertRaises(ConfigurationError):
            PrintOptions(speed=0)
        with self.assertRaises(ConfigurationError):
            Calibration(dots_per_mm=1e12)

    def test_rejects_unconfigured_width_and_clipping(self):
        with self.assertRaises(GeometryError):
            plan(Media(60,25,2))
        with self.assertRaises(GeometryError):
            plan(calibration=Calibration(offset_x_mm=10))

    def test_rejects_empty_duplicate_and_path_as_sequence(self):
        with self.assertRaises(ConfigurationError):
            prepare_batch([])
        with self.assertRaises(ConfigurationError):
            prepare_batch("a.png")
        with self.assertRaises(ConfigurationError):
            prepare_batch([LabelInput(image(),"same"),LabelInput(image(),"same")])

    def test_rejects_bad_image_and_animated_input(self):
        with self.assertRaises(GeometryError):
            prepare_batch([b"not a PNG"])
        output = BytesIO()
        Image.new("RGB",(10,10),"black").save(output,format="GIF",save_all=True,
            append_images=[Image.new("RGB",(10,10),"white")])
        with self.assertRaises(GeometryError):
            prepare_batch([output.getvalue()])

    def test_previews_use_safe_numbered_files(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = prepare_batch([LabelInput(image(),"../../outside")])
            paths = prepared.save_previews(directory)
            self.assertEqual(paths[0].name,"0001.png")
            self.assertTrue((Path(directory)/"plan.json").exists())


class CodecTests(unittest.TestCase):
    def test_known_query_bytes(self):
        self.assertEqual(packet(0xA3,b"\x00").hex(),"5178a30001000000ff")

    def test_fragmented_frames_and_bad_crc(self):
        good = packet(0xAE,b"\x10",response=True)
        corrupt = good[:-2]+bytes([good[-2]^1])+b"\xff"
        decoder = Decoder()
        results = []
        for byte in b"noise"+corrupt+good:
            results.extend(decoder.feed(bytes([byte])))
        self.assertEqual(len(results),1)
        self.assertEqual(results[0].data,b"\x10")


class JournalTests(unittest.TestCase):
    def test_connections_close_before_directory_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(directory)
            journal.reserve("closed", "hash", "printer", ("a",))
            journal.get("closed")
            # An open SQLite connection prevents this rename on Windows.
            journal.path.rename(journal.path.with_suffix(".renamed"))

    def test_recovery_marks_abandoned_send_uncertain_without_replaying(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(directory)
            journal.reserve("crashed", "hash", "printer", ("a",))
            journal.update("crashed", state="sending")
            receipt = journal.recover_interrupted("crashed", note="Worker stopped")
            self.assertEqual(receipt.state, "uncertain")
            self.assertEqual(receipt.position_after, "unknown")
            with self.assertRaises(DuplicateJob):
                journal.reserve("crashed", "hash", "printer", ("a",))

    def test_recovery_cannot_override_a_live_worker(self):
        from tinylabel_sdk.journal import PrinterLock
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(directory)
            journal.reserve("active", "hash", "printer", ("a",))
            lease = PrinterLock(journal.directory, "printer")
            lease.acquire()
            try:
                with self.assertRaises(PrinterBusy):
                    journal.recover_interrupted("active")
            finally:
                lease.release()

    def test_persistent_id_cannot_be_reserved_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            Journal(directory).reserve("job","hash","printer",("a","b"))
            with self.assertRaises(DuplicateJob):
                Journal(directory).reserve("job","other_hash","printer",("a","b"))

    def test_partial_confirmation_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(directory)
            journal.reserve("job","hash","printer",("a","b"))
            journal.update("job",state="transmitted_unconfirmed",transmitted=True)
            receipt = journal.confirm("job",printed_label_ids=["a"],alignment_ok=False,note="b missing")
            self.assertEqual(receipt.state,"partial_confirmed")
            self.assertEqual(receipt.confirmed_label_ids,("a",))
            with self.assertRaises(ConfigurationError):
                journal.confirm("job",printed_label_ids=["unknown"],alignment_ok=True)


class DriverTests(unittest.IsolatedAsyncioTestCase):
    async def test_alignment_is_required_without_sending(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport()
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                with self.assertRaises(AlignmentRequired):
                    await printer.print_batch(plan(),job_id="a")
            self.assertEqual(transport.payloads,[])

    async def test_success_is_unconfirmed_and_no_automatic_motion_at_close(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport()
            prepared = plan(count=8)
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(prepared.media)
                result = await printer.print_batch(prepared,job_id="eight")
                self.assertEqual(result.state,"transmitted_unconfirmed")
                self.assertIsNone(result.confirmed_label_ids)
                self.assertTrue(result.requires_confirmation)
                self.assertFalse(transport.closed)
            self.assertTrue(transport.closed)
            decoded = frames(b"".join(transport.payloads))
            self.assertFalse(any(x.opcode in (0xA0,0xA3) for x in decoded))
            self.assertEqual(len([x for x in decoded if x.opcode == 0xA1]),8)

    async def test_multiple_jobs_share_one_mode_and_duplicate_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport()
            prepared = plan()
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(prepared.media)
                await printer.print_batch(prepared,job_id="a")
                await printer.print_batch(prepared,job_id="b")
                with self.assertRaises(DuplicateJob):
                    await printer.print_batch(prepared,job_id="a")
            decoded = frames(b"".join(transport.payloads))
            self.assertEqual(sum(x.opcode == 0xBE for x in decoded),1)
            self.assertEqual(len(transport.payloads),2)

    async def test_changed_media_or_options_need_new_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport()
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(Media())
                await printer.print_batch(plan(),job_id="a")
                with self.assertRaises(AlignmentRequired):
                    await printer.print_batch(plan(Media(40,30,2)),job_id="b")
                changed = prepare_batch([image()], options=PrintOptions(darkness=4))
                with self.assertRaises(AlignmentRequired):
                    await printer.print_batch(changed,job_id="c")
            self.assertEqual(len(transport.payloads),1)

    async def test_mid_send_failure_is_uncertain_and_never_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport(fail=True)
            prepared = plan()
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(prepared.media)
                with self.assertRaises(DeliveryUncertain):
                    await printer.print_batch(prepared,job_id="failed")
            self.assertTrue(transport.closed)
            self.assertEqual(Journal(directory).get("failed").state,"uncertain")
            next_transport = FakeTransport()
            async with LabelPrinter("U1",journal_dir=directory,transport=next_transport,drain=FAST) as printer:
                printer.confirm_alignment(prepared.media)
                with self.assertRaises(DuplicateJob):
                    await printer.print_batch(prepared,job_id="failed")
            self.assertEqual(next_transport.payloads,[])

    async def test_cancelled_send_is_journaled_uncertain(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport(block=True)
            async with LabelPrinter("U1",journal_dir=directory,transport=transport,drain=FAST) as printer:
                printer.confirm_alignment(Media())
                task = asyncio.create_task(printer.print_batch(plan(),job_id="cancelled"))
                await transport.entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertEqual(Journal(directory).get("cancelled").state,"uncertain")
            self.assertTrue(transport.closed)

    async def test_two_workers_cannot_own_same_printer(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = FakeTransport(), FakeTransport()
            async with LabelPrinter("U1",journal_dir=directory,transport=first,drain=FAST):
                with self.assertRaises(PrinterBusy):
                    async with LabelPrinter("alias",journal_dir=directory,transport=second,drain=FAST):
                        pass
            self.assertFalse(second.opened)

    async def test_client_can_reopen_only_with_fresh_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            printer = LabelPrinter("U1",journal_dir=directory,transport=FakeTransport(),drain=FAST)
            async with printer:
                printer.confirm_alignment(Media())
                await printer.print_batch(plan(),job_id="a")
            async with printer:
                with self.assertRaises(AlignmentRequired):
                    await printer.print_batch(plan(),job_id="b")
                printer.confirm_alignment(Media())
                await printer.print_batch(plan(),job_id="b")

    async def test_partial_physical_report_invalidates_live_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            async with LabelPrinter("U1",journal_dir=directory,transport=FakeTransport(),drain=FAST) as printer:
                prepared = plan(count=2)
                printer.confirm_alignment(prepared.media)
                await printer.print_batch(prepared,job_id="a")
                receipt = printer.confirm_delivery("a",printed_label_ids=["label-0"],alignment_ok=False)
                self.assertEqual(receipt.state,"partial_confirmed")
                with self.assertRaises(AlignmentRequired):
                    await printer.print_batch(prepared,job_id="b")


class PassiveDrainTests(unittest.IsolatedAsyncioTestCase):
    async def test_long_batch_wait_scales_with_distance_not_fixed_twenty_seconds(self):
        now = [0.0]
        clock = lambda: now[0]
        monitor = Monitor(clock)
        async def sleep(seconds):
            now[0] += seconds
        waited = await wait_for_drain(monitor,started=0,sent_at=0,travel_mm=810,
            policy=DrainPolicy(poll_s=10),clock=clock,sleep=sleep)
        self.assertGreaterEqual(waited,405)

    async def test_final_flow_pause_must_resume_even_after_estimated_time(self):
        now = [0.0]
        clock = lambda: now[0]
        monitor = Monitor(clock)
        monitor.paused = True
        async def sleep(seconds):
            now[0] += seconds
            if now[0] >= 4:
                monitor.paused = False
                monitor.last_activity = now[0]
        waited = await wait_for_drain(monitor,started=0,sent_at=0,travel_mm=0,
            policy=DrainPolicy(settle_after_send_s=0,quiet_s=0,poll_s=1),clock=clock,sleep=sleep)
        self.assertEqual(waited,4)

    async def test_missing_resume_times_out_uncertain(self):
        now = [0.0]
        clock = lambda: now[0]
        monitor = Monitor(clock)
        monitor.paused = True
        async def sleep(seconds):
            now[0] += seconds
        with self.assertRaises(DrainTimeout):
            await wait_for_drain(monitor,started=0,sent_at=0,travel_mm=0,
                policy=DrainPolicy(settle_after_send_s=0,quiet_s=0,max_wait_s=2,poll_s=1),clock=clock,sleep=sleep)

    async def test_transport_error_during_drain_is_not_success(self):
        monitor = Monitor()
        monitor.fail(ConnectionError("lost"))
        with self.assertRaises(ConnectionError):
            await wait_for_drain(monitor,started=0,sent_at=0,travel_mm=0,policy=FAST)


class RuntimeTests(unittest.TestCase):
    def test_flow_control_decodes_fragments(self):
        monitor = Monitor()
        runtime = TinyRuntime(monitor)
        calls = []
        class Session:
            def set_flow_paused(self, value, **kwargs):
                calls.append(value)
        pause = packet(0xAE,b"\x10",response=True)
        runtime.handle_notification(Session(),pause[:4])
        self.assertFalse(monitor.paused)
        runtime.handle_notification(Session(),pause[4:])
        self.assertTrue(monitor.paused)
        runtime.handle_notification(Session(),packet(0xAE,b"\x00",response=True))
        self.assertEqual(calls,[True,False])

    def test_reported_paper_fault_aborts(self):
        monitor = Monitor()
        with self.assertRaises(PrinterFault):
            TinyRuntime(monitor).handle_notification(None,packet(0xA3,b"\x01",response=True))
        with self.assertRaises(PrinterFault):
            monitor.check()

    def test_charging_flag_is_not_a_fatal_fault(self):
        monitor = Monitor()
        TinyRuntime(monitor).handle_notification(None,packet(0xA3,b"\x10",response=True))
        monitor.check()


class CLITests(unittest.TestCase):
    def test_preview_returns_json_without_printing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"source.png"
            image().save(source)
            output = StringIO()
            with redirect_stdout(output):
                result = cli(["preview",str(source),"--out",str(Path(directory)/"previews")])
            self.assertEqual(result,0)
            self.assertFalse(json.loads(output.getvalue())["printed"])

    def test_print_requires_alignment_flag_before_any_io(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
            cli(["print","missing.png","--target","U1","--journal","unused","--job-id","x"])
        self.assertEqual(error.exception.code,2)


if __name__ == "__main__":
    unittest.main()
