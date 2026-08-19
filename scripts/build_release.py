#!/usr/bin/env python3
"""Create the provider-neutral public full-record workbench bundle."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PROJECTION = ROOT / "data/public/crt_public_projection.json"
PUBLIC_INPUTS = {
    ROOT / "app/index.html": DIST / "index.html",
    ROOT / "app/styles.css": DIST / "styles.css",
    ROOT / "app/app.js": DIST / "app.js",
    ROOT / "app/vercel.json": DIST / "vercel.json",
    ROOT / "api/records.py": DIST / "api/records.py",
    ROOT / "api/release.py": DIST / "api/release.py",
    ROOT / "requirements.txt": DIST / "requirements.txt",
    PROJECTION: DIST / "data/public/crt_public_projection.json",
}
FORBIDDEN_KEYS = {
    "loan_identifier",
    "payment_history",
    "servicer_name",
    "seller_name",
    "property_state",
    "classic_fico_value",
    "original_ltv_value",
    "original_dti_value",
}
FORBIDDEN_TEXT = (
    "data/restricted",
    "metrics.duckdb",
    "loan_period_typed",
    "private_app",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append((key, child))
            found.extend(walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk(child))
    return found


def validate_public_inputs() -> dict[str, Any]:
    missing = [
        str(path.relative_to(ROOT)) for path in PUBLIC_INPUTS if not path.is_file()
    ]
    if missing:
        raise ValueError("public twin inputs are missing: " + ", ".join(missing))
    projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
    if projection.get("classification") != "approved-aggregate-projection":
        raise ValueError(
            "projection classification is not approved for aggregate release"
        )
    if projection.get("public_release_allowed") is not True:
        raise ValueError("projection is not marked public-release eligible")
    keys = {key.lower() for key, _ in walk(projection)}
    prohibited_keys = sorted(keys & FORBIDDEN_KEYS)
    if prohibited_keys:
        raise ValueError(
            "projection contains prohibited fields: " + ", ".join(prohibited_keys)
        )
    serialized = json.dumps(projection).lower()
    prohibited_text = [term for term in FORBIDDEN_TEXT if term in serialized]
    if prohibited_text:
        raise ValueError(
            "projection contains prohibited paths or private assets: "
            + ", ".join(prohibited_text)
        )
    page = (ROOT / "app/index.html").read_text(encoding="utf-8")
    for statement in (
        "All loan-period rows and disclosed fields are queryable",
        "Original loan identifier, ZIP3, source archives, and local paths are not published",
        "Other disclosed field combinations may remain linkable",
    ):
        if statement not in page:
            raise ValueError(f"public boundary statement is missing: {statement}")
    return projection


def main() -> None:
    projection = validate_public_inputs()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for source, destination in PUBLIC_INPUTS.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (DIST / "DEPLOYMENT.md").write_text(
        "# Deployment contract\n\n"
        "This bundle contains the reviewed public client, derived summary projection, and masked full-record query function. "
        "The function reads only from the approved authenticated data gateway. Set CRT_DATA_GATEWAY_URL and CRT_DATA_GATEWAY_TOKEN as server-side environment variables. Do not add raw identifiers, source archives, object-storage URLs, local paths, credentials, or an unmasked data source. "
        "Publishing or replacing a live deployment requires a separate release approval and rollback record.\n",
        encoding="utf-8",
    )
    files = sorted(
        path
        for path in DIST.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    )
    file_records = [
        {"path": str(path.relative_to(DIST)), "sha256": sha256(path)} for path in files
    ]
    artifact_sha256 = hashlib.sha256(
        json.dumps(file_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "release_type": "public-full-record-crt-workbench",
        "source_classification": projection["classification"],
        "metric_version": projection["metric_version"],
        "source_scope": projection["source_scope"],
        "artifact_sha256": artifact_sha256,
        "files": file_records,
    }
    (DIST / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (DIST / ".vercelignore").write_text(
        "manifest.json\n.env*\n.vercel\n.gitignore\n",
        encoding="utf-8",
    )
    print(f"Static public twin bundle created: {DIST}")


if __name__ == "__main__":
    main()
