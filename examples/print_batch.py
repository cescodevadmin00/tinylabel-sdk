"""Run only after an operator has aligned the selected roll."""
import argparse
import asyncio
import json
from pathlib import Path

from tinylabel_sdk import LabelInput, LabelPrinter, load_profile, prepare_batch


async def run(args):
    media, calibration, options, drain = load_profile(args.profile)
    files = sorted(Path(args.images).glob("*.png"),
                   key=lambda path: (0, int(path.stem)) if path.stem.isdecimal() else (1, path.name.casefold()))
    plan = prepare_batch([LabelInput(path, path.name) for path in files], media,
                         calibration=calibration, options=options)
    plan.save_previews(args.preview)
    if not args.print:
        print(json.dumps(plan.summary(), indent=2))
        return
    if not args.aligned:
        raise SystemExit("Confirm actual paper alignment with --aligned before printing")
    async with LabelPrinter(args.target, journal_dir=args.journal, drain=drain) as printer:
        # This acknowledges an operator action. It does NOT home the printer.
        printer.confirm_alignment(media, calibration=calibration)
        receipt = await printer.print_batch(plan, job_id=args.job_id)
        print(json.dumps(receipt.to_dict(), indent=2))
        # Do not mark delivery confirmed here. Ask the operator/physical verifier.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True)
    parser.add_argument("--profile", default="profiles/u1_50x25_gap2.json")
    parser.add_argument("--target", default="U1-XXXX", help="Replace with the exact Bluetooth name/address")
    parser.add_argument("--journal", default=".label-jobs")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preview", default="preview")
    parser.add_argument("--aligned", action="store_true")
    parser.add_argument("--print", action="store_true")
    asyncio.run(run(parser.parse_args()))
