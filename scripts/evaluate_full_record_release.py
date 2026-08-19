#!/usr/bin/env python3
# ruff: noqa: I001
"""Evaluate the masked public full-record assets and bounded query bundle."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.records import MAX_ASSET_BYTES, MAX_OFFSET, query_partition
from scripts.build_release import DIST, main as build_release


PUBLIC_DATA = ROOT / "data/public/full-data"
PUBLIC_MANIFEST = PUBLIC_DATA / "manifest.json"
MASK_KEY = ROOT / "data/restricted/public-mask.key"
OUTPUT = ROOT / "data/derived/full_record_public_evaluation.json"
EXPECTED_RELEASE_FILES = {
    "DEPLOYMENT.md",
    "api/records.py",
    "app.js",
    "data/public/crt_public_projection.json",
    "index.html",
    "requirements.txt",
    "styles.css",
    "vercel.json",
}


def evaluate() -> dict[str, Any]:
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    build_release()
    release = json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))
    release_paths = {item["path"] for item in release["files"]}
    masking_key = MASK_KEY.read_bytes()
    release_files = [path for path in DIST.rglob("*") if path.is_file()]
    api_source = (ROOT / "api/records.py").read_text(encoding="utf-8")
    gateway_source = (ROOT / "infra/data-gateway/src/index.mjs").read_text(
        encoding="utf-8"
    )
    gateway_config = (ROOT / "infra/data-gateway/wrangler.jsonc").read_text(
        encoding="utf-8"
    )

    connection = duckdb.connect()
    try:
        total, bad_loan_tokens, bad_geo_tokens, partitions = connection.execute(
            """
            SELECT
                count(*),
                count(*) FILTER (
                    WHERE loan_identifier IS NOT NULL
                      AND NOT regexp_matches(loan_identifier, '^loan-[0-9a-f]{20}$')
                ),
                count(*) FILTER (
                    WHERE postal_code_3_digit IS NOT NULL
                      AND NOT regexp_matches(postal_code_3_digit, '^geo-[0-9a-f]{12}$')
                ),
                count(DISTINCT deal_id || ':' || period)
            FROM read_parquet(?, hive_partitioning=false)
            """,
            [str(PUBLIC_DATA / "*.parquet")],
        ).fetchone()
    finally:
        connection.close()

    latest = max(assets, key=lambda item: item["reporting_period"])
    api_result = query_partition(PUBLIC_DATA / latest["asset"], "all", 2, 0)
    checks = {
        "classification_is_public_masked": manifest["classification"]
        == "public-full-record-masked",
        "all_records_preserved": manifest["records"] == total == 20_439_666,
        "all_partitions_preserved": manifest["partitions"]
        == partitions
        == len(assets)
        == 292,
        "all_fields_preserved": manifest["source_disclosure_fields"] == 93
        and manifest["fields"] == len(api_result["fields"]) == 96,
        "loan_tokens_valid_on_complete_scan": bad_loan_tokens == 0,
        "zip3_tokens_valid_on_complete_scan": bad_geo_tokens == 0,
        "assets_fit_runtime_guard": max(item["bytes"] for item in assets)
        <= MAX_ASSET_BYTES,
        "all_partition_rows_are_pageable": max(item["records"] for item in assets)
        <= MAX_OFFSET,
        "api_returns_every_stored_field": all(
            set(row) == set(api_result["fields"]) for row in api_result["rows"]
        ),
        "api_masks_both_direct_identifiers": api_result["masked_fields"]
        == ["loan_identifier", "postal_code_3_digit"],
        "api_requires_private_gateway": "CRT_DATA_GATEWAY_TOKEN" in api_source
        and "github.com" not in api_source,
        "gateway_is_private_and_read_only": "DATA_GATEWAY_TOKEN" in gateway_source
        and 'request.method !== "GET"' in gateway_source
        and ".list(" not in gateway_source
        and ".put(" not in gateway_source
        and ".delete(" not in gateway_source
        and '"binding": "CRT_DATA"' in gateway_config,
        "release_type_is_full_record_workbench": release["release_type"]
        == "public-full-record-crt-workbench",
        "release_file_allowlist_exact": release_paths == EXPECTED_RELEASE_FILES,
        "masking_key_absent_from_release": not any(
            masking_key in path.read_bytes() for path in release_files
        ),
        "restricted_paths_absent_from_release": not any(
            "data/restricted" in path.read_text(encoding="utf-8", errors="ignore")
            for path in release_files
        ),
    }
    result = {
        "report_version": 1,
        "evaluation_date": datetime.now(UTC).date().isoformat(),
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "records": total,
        "partitions": partitions,
        "stored_columns": len(api_result["fields"]),
        "source_disclosure_fields": manifest["source_disclosure_fields"],
        "public_asset_bytes": sum(item["bytes"] for item in assets),
        "maximum_asset_bytes": max(item["bytes"] for item in assets),
        "bad_loan_tokens": bad_loan_tokens,
        "bad_zip3_tokens": bad_geo_tokens,
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
