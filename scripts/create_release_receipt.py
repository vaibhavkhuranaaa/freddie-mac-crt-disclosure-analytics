#!/usr/bin/env python3
"""Create a versioned, aggregate-only release receipt after a verified local build."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from intake_real_clarity import sha256


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, default=ROOT / "data" / "derived" / "real_aggregate.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "real-release-receipt.json")
    parser.add_argument("--deployment-url", required=True)
    parser.add_argument("--approver", required=True)
    args = parser.parse_args()
    archive, aggregate, output = args.archive.resolve(), args.aggregate.resolve(), args.output.resolve()
    if not archive.is_file() or not aggregate.is_file():
        raise SystemExit("archive and aggregate output must exist before issuing a receipt")
    receipt = {
        "receipt_version": 1,
        "release_scope": "Freddie Mac CRT reference-pool D30+/D60+/current-UPB analytics only",
        "input_archive": {"name": archive.name, "sha256": sha256(archive)},
        "aggregate_output": {"path": str(aggregate.relative_to(ROOT)) if aggregate.is_relative_to(ROOT) else str(aggregate), "sha256": sha256(aggregate)},
        "build_command": "python3 scripts/build_release.py",
        "test_command": "python3 -m unittest discover -s tests -v && git diff --check",
        "deployment_url": args.deployment_url,
        "issued_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "approver": args.approver,
        "rollback_procedure": "In Vercel, promote the last verified aggregate-only deployment or remove this deployment. Do not substitute a synthetic or raw-data bundle; the restricted archive remains local and excluded.",
        "limitations": ["No raw archive or loan-level row is included.", "No tranche waterfall, cash-flow, loss-allocation, prepayment, or borrower-level analytics is claimed."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Release receipt written: {output}")


if __name__ == "__main__":
    main()
