"""JSON CLI suitable for a local worker in another language."""
import argparse
import asyncio
from dataclasses import replace
import json
import sys

from .client import LabelPrinter
from .errors import LabelSDKError
from .journal import Journal
from .models import Calibration, DrainPolicy, Media, PrintOptions, load_profile
from .planner import prepare_batch


def _parser():
    parser = argparse.ArgumentParser(prog="tinylabel")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "print"):
        command = commands.add_parser(name)
        command.add_argument("images", nargs="+")
        command.add_argument("--profile")
        command.add_argument("--width-mm", type=float)
        command.add_argument("--height-mm", type=float)
        command.add_argument("--gap-mm", type=float)
        command.add_argument("--darkness", type=int)
        if name == "preview":
            command.add_argument("--out", required=True)
        else:
            command.add_argument("--target", required=True)
            command.add_argument("--journal", required=True)
            command.add_argument("--job-id", required=True)
            command.add_argument("--aligned", action="store_true",
                                 help="Operator already aligned this roll and disconnected the phone app")
    for name in ("inspect", "confirm", "recover"):
        command = commands.add_parser(name)
        command.add_argument("--journal", required=True)
        command.add_argument("--job-id", required=True)
        if name == "confirm":
            command.add_argument("--label-id", action="append", default=[])
            command.add_argument("--alignment-ok", action="store_true")
            command.add_argument("--note", default="")
        elif name == "recover":
            command.add_argument("--note", default="")
    return parser


def _plan(args):
    media, calibration, options, drain = load_profile(args.profile) if args.profile else (
        Media(), Calibration(), PrintOptions(), DrainPolicy())
    changes = {name: getattr(args, name) for name in ("width_mm", "height_mm", "gap_mm") if getattr(args, name) is not None}
    media = replace(media, **changes)
    if args.darkness is not None:
        options = replace(options, darkness=args.darkness)
    return prepare_batch(args.images, media, calibration=calibration, options=options), drain


async def _print(args, plan, drain):
    async with LabelPrinter(args.target, journal_dir=args.journal, drain=drain) as printer:
        printer.confirm_alignment(plan.media, calibration=plan.calibration)
        return (await printer.print_batch(plan, job_id=args.job_id)).to_dict()


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "print" and not args.aligned:
        parser.error("--aligned is required after the operator confirms the physical origin; no paper was moved")
    try:
        if args.command == "preview":
            plan, _ = _plan(args)
            result = dict(plan.summary(), previews=[str(path) for path in plan.save_previews(args.out)], printed=False)
        elif args.command == "print":
            plan, drain = _plan(args)
            result = asyncio.run(_print(args, plan, drain))
        elif args.command == "inspect":
            receipt = Journal(args.journal).get(args.job_id)
            if receipt is None:
                print(json.dumps({"error": "JobNotFound", "job_id": args.job_id}))
                return 4
            result = receipt.to_dict()
        elif args.command == "recover":
            result = Journal(args.journal).recover_interrupted(args.job_id, note=args.note).to_dict()
        else:
            result = Journal(args.journal).confirm(args.job_id, printed_label_ids=args.label_id,
                alignment_ok=args.alignment_ok, note=args.note).to_dict()
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
