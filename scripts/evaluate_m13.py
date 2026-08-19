#!/usr/bin/env python3
"""Evaluate local M13 showcase package and source attestation."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = ROOT / "data" / "derived" / "m13_showcase_evaluation.json"
SCREENSHOTS = {
    "stakeholder": ROOT / "evaluation" / "m11-browser" / "public-desktop.png",
    "technical": ROOT / "evaluation" / "m11-browser" / "public-mobile.png",
}
EXPECTED_RELEASE_FILES = {
    "DEPLOYMENT.md",
    "app.js",
    "data/public/crt_public_projection.json",
    "index.html",
    "styles.css",
    "vercel.json",
}
SECRET_LIKE = re.compile(r"\b[0-9a-f]{40}\b|\b[0-9a-f]{64}\b|sha256:", re.IGNORECASE)


def command(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path) -> list[int]:
    with path.open("rb") as source:
        if source.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"not a PNG: {path}")
        length = struct.unpack(">I", source.read(4))[0]
        if source.read(4) != b"IHDR" or length < 8:
            raise ValueError(f"missing PNG header: {path}")
        return list(struct.unpack(">II", source.read(8)))


def tracked_markdown() -> list[Path]:
    paths = command("git", "ls-files", "*.md").stdout.splitlines()
    return [ROOT / path for path in paths]


def evaluate() -> dict[str, object]:
    command(sys.executable, "scripts/build_release.py")
    manifest = json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))
    release_files = {item["path"] for item in manifest["files"]}
    integrity_passed = all(
        sha256(DIST / item["path"]) == item["sha256"]
        for item in manifest["files"]
    )
    documents = tracked_markdown()
    document_text = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in documents}
    exposed_integrity_values = [name for name, text in document_text.items() if SECRET_LIKE.search(text)]
    em_dash_documents = [name for name, text in document_text.items() if "—" in text]
    combined_copy = "\n".join(document_text.values())
    required_claims = {
        "m12_complete": "M12" in combined_copy and "scaled-local" in combined_copy,
        "legacy_live_separated": "legacy" in combined_copy.lower() and "not deployed" in combined_copy.lower(),
        "independent_review_unclaimed": "0/5" in combined_copy and "No independent" in combined_copy,
        "external_actions_gated": "separate" in combined_copy.lower() and "publication" in combined_copy.lower(),
    }
    screenshot_evidence = {
        role: {
            "path": str(path.relative_to(ROOT)),
            "dimensions": png_dimensions(path),
            "bytes": path.stat().st_size,
        }
        for role, path in SCREENSHOTS.items()
    }
    status_output = command("git", "status", "--porcelain", "--untracked-files=all").stdout
    revision = command("git", "rev-parse", "HEAD").stdout.strip()
    branch = command("git", "branch", "--show-current").stdout.strip()
    checks = {
        "release_type": manifest.get("release_type") == "static-aggregate-crt-twin",
        "release_file_allowlist": release_files == EXPECTED_RELEASE_FILES,
        "release_integrity": integrity_passed,
        "public_documents_exclude_revision_values": not exposed_integrity_values,
        "public_copy_has_no_em_dash": not em_dash_documents,
        "required_claims_present": all(required_claims.values()),
        "screenshot_pair_present": len(screenshot_evidence) == 2,
        "source_revision_available": len(revision) == 40,
        "source_branch_available": bool(branch),
        "working_tree_clean": not status_output,
    }
    result = {
        "report_version": 1,
        "evaluation_date": date.today().isoformat(),
        "milestone": "M13",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "release": {
            "files": sorted(release_files),
            "artifact_sha256": manifest.get("artifact_sha256"),
            "classification": manifest.get("source_classification"),
        },
        "claims": required_claims,
        "screenshots": screenshot_evidence,
        "source_attestation": {
            "revision": revision,
            "branch": branch,
            "working_tree_clean": not status_output,
        },
        "public_document_findings": {
            "revision_value_exposures": exposed_integrity_values,
            "em_dash_documents": em_dash_documents,
        },
        "claim_boundary": "Local M13 package only. Deployment, publication, push, hosted verification, and portfolio-site application remain unapproved.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = evaluate()
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
