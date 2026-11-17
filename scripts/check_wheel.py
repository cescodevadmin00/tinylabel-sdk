"""Inspect and import an extracted wheel outside the source tree; no hardware."""
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

wheel = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        required = [
            "tinylabel_sdk/_vendor/LICENSE", "tinylabel_sdk/_vendor/NOTICE",
            "tinylabel_sdk/_vendor/UPSTREAM.json",
            "tinylabel_sdk/_vendor/timiniprint/data/printer_models.json",
            "tinylabel_sdk/fonts/NotoSans-Regular.ttf", "tinylabel_sdk/fonts/NotoSans-Bold.ttf",
            "tinylabel_sdk/fonts/OFL.txt", "tinylabel_sdk/fonts/UPSTREAM.json",
        ]
        assert all(name in names for name in required), "Wheel missing attribution/catalog"
        assert not any(name.endswith((".pyc", ".sqlite3")) for name in names)
        archive.extractall(target)
    code = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import tinylabel_sdk
from tinylabel_sdk._vendor.timiniprint.devices import PrinterCatalog
from tinylabel_sdk._vendor.timiniprint.transport.bluetooth import BluetoothDiscovery, BleakBluetoothConnector
from PIL import Image
assert Path(tinylabel_sdk.__file__).is_relative_to(Path(sys.argv[1]))
assert "pypdfium2" not in sys.modules
catalog = PrinterCatalog.load()
plan = tinylabel_sdk.prepare_batch([Image.new("RGB", (548, 246), "black")])
assert len(plan.labels) == 1
assert tinylabel_sdk.encode_batch(plan).pitch_units == (216,)
text_plan = tinylabel_sdk.prepare_text_batch([
    tinylabel_sdk.TextLabel.from_text("Texto / Text: 001", "sample-text")
])
assert tinylabel_sdk.encode_batch(text_plan).pitch_units == (216,)
assert len(text_plan.labels[0].rows) > 0
print("Wheel imports, private catalog and planner OK; no Bluetooth connection")
'''
    subprocess.run([sys.executable, "-I", "-c", code, str(target)], cwd=target, check=True)
