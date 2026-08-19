#!/usr/bin/env python3
"""Build public full-record Parquet partitions with direct identifiers masked."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOUNDATION = ROOT / "data/restricted/full-data"
DEFAULT_OUTPUT = ROOT / "data/public/full-data"
DEFAULT_MASK_KEY = ROOT / "data/restricted/public-mask.key"
MASKED_FIELDS = ("loan_identifier", "postal_code_3_digit")


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def build(foundation: Path, output: Path, mask_key: Path) -> dict[str, object]:
    started = time.perf_counter()
    manifest_path = foundation / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Full-data manifest not found: {manifest_path}")
    key = mask_key.read_bytes() if mask_key.is_file() else b""
    if len(key) < 32:
        raise ValueError("Public masking key must contain at least 32 random bytes.")
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix=".full-data-public-", dir=output.parent))
    connection = duckdb.connect()
    assets: list[dict[str, object]] = []
    public_fields: list[str] = []
    secret = key.hex()
    try:
        for index, partition in enumerate(source["partitions"], start=1):
            deal_id = str(partition["deal_id"])
            period = str(partition["reporting_period"])
            source_path = foundation / str(partition["parquet_path"])
            target = build_dir / f"{deal_id}--{period}.parquet"
            connection.execute(
                f"""
                COPY (
                    SELECT * REPLACE (
                        CASE WHEN loan_identifier IS NULL OR loan_identifier = '' THEN NULL
                             ELSE concat('loan-', left(sha256({sql_literal(secret)} || ':' || loan_identifier), 20)) END
                            AS loan_identifier,
                        CASE WHEN postal_code_3_digit IS NULL OR postal_code_3_digit = '' THEN NULL
                             ELSE concat('geo-', left(sha256({sql_literal(secret)} || ':' || postal_code_3_digit), 12)) END
                            AS postal_code_3_digit
                    )
                    FROM read_parquet({sql_literal(source_path)}, hive_partitioning=false)
                ) TO {sql_literal(target)} (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
                """
            )
            records = int(
                connection.execute(
                    "SELECT count(*) FROM read_parquet(?)", [str(target)]
                ).fetchone()[0]
            )
            if records != int(partition["records"]):
                raise ValueError(
                    f"Sanitized partition count mismatch for {deal_id} {period}."
                )
            fields = [
                item[0]
                for item in connection.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)", [str(target)]
                ).fetchall()
            ]
            if not public_fields:
                public_fields = fields
            elif fields != public_fields:
                raise ValueError(
                    f"Sanitized field layout mismatch for {deal_id} {period}."
                )
            assets.append(
                {
                    "asset": target.name,
                    "deal_id": deal_id,
                    "reporting_period": period,
                    "records": records,
                    "bytes": target.stat().st_size,
                }
            )
            if index == 1 or index % 25 == 0 or index == len(source["partitions"]):
                print(
                    f"[{index}/{len(source['partitions'])}] {sum(int(item['records']) for item in assets):,} rows sanitized",
                    flush=True,
                )
        sample = connection.execute(
            "SELECT loan_identifier, postal_code_3_digit FROM read_parquet(?) LIMIT 100",
            [str(build_dir / assets[0]["asset"])],
        ).fetchall()
        if any(
            identifier and not identifier.startswith("loan-")
            for identifier, _ in sample
        ):
            raise ValueError("Loan identifier masking verification failed.")
        if any(zip3 and not zip3.startswith("geo-") for _, zip3 in sample):
            raise ValueError("ZIP3 masking verification failed.")
        public_manifest = {
            "version": 1,
            "release": "full-data-v2026-07",
            "classification": "public-full-record-masked",
            "records": int(source["records"]),
            "partitions": len(assets),
            "fields": len(public_fields),
            "source_disclosure_fields": int(source["fields_retained"]),
            "masked_fields": list(MASKED_FIELDS),
            "assets": assets,
            "runtime_seconds": round(time.perf_counter() - started, 3),
        }
        (build_dir / "manifest.json").write_text(
            json.dumps(public_manifest, indent=2) + "\n", encoding="utf-8"
        )
        if output.exists():
            shutil.rmtree(output)
        build_dir.replace(output)
        return public_manifest
    except Exception:
        shutil.rmtree(build_dir, ignore_errors=True)
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation", type=Path, default=DEFAULT_FOUNDATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mask-key", type=Path, default=DEFAULT_MASK_KEY)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = build(
        args.foundation.resolve(), args.output.resolve(), args.mask_key.resolve()
    )
    print(
        f"Public full-data release: {result['records']:,} rows, {result['partitions']} partitions"
    )


if __name__ == "__main__":
    main()
