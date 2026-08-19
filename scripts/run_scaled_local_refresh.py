#!/usr/bin/env python3
"""Run append-only scaled-local refreshes with recovery and measured controls."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from build_full_data_layer import (
    RESTRICTED,
    ROOT,
    stage_member,
    standard_members,
    write_partition,
)
from build_metric_engine import build as build_metric_engine
from build_metric_engine import sha256, sql_literal
from intake_clarity_archive import LLD_FILE, expected_period, normalized_deal_id


DEFAULT_ARCHIVE = RESTRICTED / "fre-crt-2023-07-2026-07.zip"
DEFAULT_FOUNDATION = RESTRICTED / "full-data"
DEFAULT_DATABASE = RESTRICTED / "metrics" / "metrics.duckdb"
DEFAULT_RELEASE = ROOT / "data" / "derived" / "real_aggregate.csv"
DEFAULT_OPERATIONS = RESTRICTED / "operations"
DEFAULT_EVALUATION = ROOT / "data" / "derived" / "m12_scaled_local_evaluation.json"
MATERIALIZED_TABLES = (
    "pool_period_components",
    "pool_period_metrics",
    "deal_period_components",
    "deal_period_metrics",
    "portfolio_period_components",
    "portfolio_period_metrics",
    "deal_period_flow_metrics",
    "deal_period_risk_layer_metrics",
    "portfolio_d60_decomposition",
    "release_reference",
    "release_reconciliation",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def archive_inventory(archive: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    with zipfile.ZipFile(archive) as package:
        accepted, rejected = standard_members(package)
        inventory: dict[str, dict[str, Any]] = {}
        for info in accepted:
            match = LLD_FILE.fullmatch(Path(info.filename).name)
            assert match is not None
            deal_id = normalized_deal_id(match.group("short_deal"))
            reporting_period = expected_period(match.group("as_of"))
            key = f"{deal_id}|{reporting_period}"
            inventory[key] = {
                "source_member": info.filename,
                "deal_id": deal_id,
                "reporting_period": reporting_period,
                "source_crc32": f"{info.CRC:08x}",
                "source_bytes": info.file_size,
            }
    return inventory, rejected


def partition_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        f"{item['deal_id']}|{item['reporting_period']}": item
        for item in manifest["partitions"]
    }


def initialize_inventory(
    archive: Path,
    manifest: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    inventory_path: Path,
) -> dict[str, Any]:
    if sha256(archive) != manifest["source_archive_sha256"]:
        raise ValueError("initial incremental inventory requires the foundation's exact source archive")
    partitions = partition_map(manifest)
    if set(partitions) != set(inventory):
        raise ValueError("source archive keys do not match the current foundation")
    for key, partition in partitions.items():
        if partition["source_member"] != inventory[key]["source_member"]:
            raise ValueError(f"source member changed for {key}")
    state = {
        "version": 1,
        "initialized_at": utc_now(),
        "source_archive_sha256": manifest["source_archive_sha256"],
        "partitions": inventory,
    }
    atomic_json(inventory_path, state)
    return state


def validate_append_only(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> list[str]:
    missing = sorted(set(previous) - set(current))
    if missing:
        raise ValueError(f"incoming archive omits existing partition(s): {', '.join(missing[:3])}")
    changed = [
        key
        for key in previous
        if any(
            previous[key].get(field) != current[key].get(field)
            for field in ("source_member", "source_crc32", "source_bytes")
        )
    ]
    if changed:
        raise ValueError(f"incoming archive revises existing partition(s): {', '.join(changed[:3])}")
    return sorted(set(current) - set(previous))


def recover_interrupted_runs(operations: Path, foundation: Path) -> dict[str, int]:
    manifest = load_json(foundation / "manifest.json")
    committed = {item["parquet_path"] for item in manifest["partitions"]}
    removed_orphans = 0
    recovered_runs = 0
    runs_dir = operations / "runs"
    for run_path in sorted(runs_dir.glob("*.json")) if runs_dir.exists() else []:
        run = load_json(run_path)
        if run.get("status") not in {"running", "failed"}:
            continue
        changed = False
        for relative in run.get("planned_partition_paths", []):
            if relative in committed:
                continue
            target = (foundation / relative).resolve()
            if not target.is_relative_to(foundation.resolve()):
                raise ValueError(f"unsafe recovery path: {relative}")
            if target.is_file():
                target.unlink()
                removed_orphans += 1
                parent = target.parent
                while parent != foundation and parent != foundation / "loan_period":
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            changed = True
        if changed or run.get("status") == "running":
            run["recovered_at"] = utc_now()
            run["status"] = "recovered" if run.get("status") == "running" else run["status"]
            atomic_json(run_path, run)
            recovered_runs += 1
    staging = operations / "staging"
    removed_staging = 0
    if staging.exists():
        for path in staging.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
                removed_staging += 1
    return {
        "recovered_runs": recovered_runs,
        "removed_orphan_partitions": removed_orphans,
        "removed_staging_directories": removed_staging,
    }


def append_partitions(
    archive: Path,
    foundation: Path,
    staging: Path,
    new_keys: list[str],
    inventory: dict[str, dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    manifest_path = foundation / "manifest.json"
    manifest = load_json(manifest_path)
    if not new_keys:
        return manifest, []
    staged_root = staging / "foundation"
    staged_text = staging / "source"
    staged_root.mkdir(parents=True)
    staged_text.mkdir()
    connection = duckdb.connect()
    additions: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(archive) as package:
            infos = {info.filename: info for info in package.infolist()}
            for index, key in enumerate(new_keys, start=1):
                source = inventory[key]
                info = infos[source["source_member"]]
                text_path = staged_text / f"{index:03d}.txt"
                records, width = stage_member(package, info, text_path, source["reporting_period"])
                relative = Path("loan_period") / f"deal_id={source['deal_id']}" / f"reporting_period={source['reporting_period']}" / "data.parquet"
                parquet = staged_root / relative
                parquet.parent.mkdir(parents=True)
                write_partition(connection, text_path, parquet, source["deal_id"], source["source_member"], width)
                text_path.unlink()
                actual = int(
                    connection.execute(
                        f"SELECT count(*) FROM read_parquet({sql_literal(parquet)}, hive_partitioning=false)"
                    ).fetchone()[0]
                )
                if actual != records:
                    raise ValueError(f"staged partition {key} row count mismatch")
                additions.append(
                    {
                        "source_member": source["source_member"],
                        "deal_id": source["deal_id"],
                        "reporting_period": source["reporting_period"],
                        "source_field_count": width,
                        "records": records,
                        "parquet_path": str(relative),
                        "parquet_bytes": parquet.stat().st_size,
                        "parquet_sha256": sha256(parquet),
                    }
                )
    finally:
        connection.close()
    for item in additions:
        source = staged_root / item["parquet_path"]
        target = foundation / item["parquet_path"]
        if target.exists():
            raise ValueError(f"refusing to overwrite partition: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
    partitions = sorted(
        [*manifest["partitions"], *additions],
        key=lambda item: (item["reporting_period"], item["deal_id"]),
    )
    width_counts: dict[str, int] = {}
    for item in partitions:
        width = str(item["source_field_count"])
        width_counts[width] = width_counts.get(width, 0) + int(item["records"])
    updated = {
        **manifest,
        "manifest_version": 2,
        "build_date": datetime.now(UTC).date().isoformat(),
        "source_archive_name": archive.name,
        "source_archive_sha256": sha256(archive),
        "accepted_files": len(partitions),
        "rejected_members": rejected,
        "records": sum(int(item["records"]) for item in partitions),
        "source_field_count_records": dict(sorted(width_counts.items())),
        "partitions": partitions,
        "refresh_mode": "append-only-incremental",
    }
    atomic_json(manifest_path, updated)
    return updated, [item["parquet_path"] for item in additions]


def derive_release_aggregate(archive: Path, output_dir: Path) -> Path:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "intake_clarity_archive.py"),
            str(archive),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return output_dir / "real_aggregate.csv"


def metric_period(database: Path) -> str:
    with duckdb.connect(str(database), read_only=True) as connection:
        value = connection.execute("SELECT max(reporting_period) FROM portfolio_period_metrics").fetchone()[0]
    return str(value)


def release_period(release_aggregate: Path) -> str:
    with release_aggregate.open(encoding="utf-8", newline="") as handle:
        periods = [row["reporting_period"] for row in csv.DictReader(handle)]
    if not periods:
        raise ValueError("release aggregate has no reporting periods")
    return max(periods)


def create_delta_foundation(
    foundation: Path,
    manifest: dict[str, Any],
    target: Path,
    first_period: str,
) -> tuple[Path, set[str]]:
    selected = [item for item in manifest["partitions"] if str(item["reporting_period"]) >= first_period]
    periods = {str(item["reporting_period"]) for item in selected}
    for item in selected:
        source = foundation / item["parquet_path"]
        destination = target / item["parquet_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)
    delta_manifest = {
        **manifest,
        "accepted_files": len(selected),
        "records": sum(int(item["records"]) for item in selected),
        "partitions": selected,
    }
    atomic_json(target / "manifest.json", delta_manifest)
    return target, periods


def subset_release(source: Path, target: Path, periods: set[str]) -> Path:
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader if row["reporting_period"] in periods]
        fields = reader.fieldnames
    if not rows or fields is None:
        raise ValueError("delta release aggregate has no selected rows")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return target


def table_history_hashes(connection: duckdb.DuckDBPyConnection, cutoff: str) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for table in MATERIALIZED_TABLES:
        columns = [
            row[0]
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_catalog=current_database() AND table_schema='main' AND table_name=? ORDER BY ordinal_position",
                [table],
            ).fetchall()
        ]
        quoted = ",".join(f'"{column}"' for column in columns)
        count, fingerprint = connection.execute(
            f"SELECT count(*), coalesce(bit_xor(hash({quoted})), 0) FROM {table} WHERE reporting_period::VARCHAR <= ?",
            [cutoff],
        ).fetchone()
        result[table] = [int(count), int(fingerprint)]
    return result


def merge_metric_delta(
    database: Path,
    delta_database: Path,
    candidate: Path,
    cutoff: str,
    expected_records: int,
) -> dict[str, Any]:
    shutil.copy2(database, candidate)
    connection = duckdb.connect(str(candidate))
    try:
        before = table_history_hashes(connection, cutoff)
        connection.execute(f"ATTACH {sql_literal(delta_database)} AS delta (READ_ONLY)")
        connection.execute("BEGIN")
        for table in MATERIALIZED_TABLES:
            connection.execute(f"DELETE FROM {table} WHERE reporting_period::VARCHAR > ?", [cutoff])
            connection.execute(
                f"INSERT INTO {table} SELECT * FROM delta.{table} WHERE reporting_period::VARCHAR > ?",
                [cutoff],
            )
        connection.execute("COMMIT")
        after = table_history_hashes(connection, cutoff)
        if before != after:
            raise ValueError("incremental metric refresh changed unaffected history")
        actual_records = int(connection.execute("SELECT count(*) FROM loan_period_typed").fetchone()[0])
        if actual_records != expected_records:
            raise ValueError(f"metric view has {actual_records:,} rows; foundation expects {expected_records:,}")
        reconciliation = connection.execute(
            """
            SELECT count(*) FILTER (WHERE missing_group),
                   max(abs(current_upb_variance)), max(abs(d30_plus_upb_variance)),
                   max(abs(d60_plus_upb_variance)), max(abs(d30_plus_rate_variance)),
                   max(abs(d60_plus_rate_variance)), max(abs(record_variance))
            FROM release_reconciliation
            """
        ).fetchone()
        if any(value not in (0, 0.0, None) for value in reconciliation):
            raise ValueError(f"incremental release reconciliation failed: {reconciliation}")
        unmatched = int(connection.execute("SELECT coalesce(sum(error_unmatched_records),0) FROM deal_period_flow_metrics").fetchone()[0])
        if unmatched:
            raise ValueError(f"incremental transition integrity failed: {unmatched} unmatched records")
        decomposition = connection.execute(
            """
            WITH effects AS (
                SELECT reporting_period, sum(rate_effect_bps+mix_effect_bps) AS value
                FROM portfolio_d60_decomposition GROUP BY 1
            )
            SELECT max(abs(e.value-p.d60_change_1m_bps))
            FROM effects e JOIN portfolio_period_metrics p USING(reporting_period)
            """
        ).fetchone()[0]
        if decomposition is None or float(decomposition) > 0.01:
            raise ValueError(f"incremental decomposition variance is {decomposition}")
        latest = str(connection.execute("SELECT max(reporting_period) FROM portfolio_period_metrics").fetchone()[0])
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    os.replace(candidate, database)
    return {
        "historical_row_hashes_preserved": True,
        "source_records": expected_records,
        "latest_reporting_period": latest,
        "maximum_decomposition_variance_bps": float(decomposition),
    }


def refresh_metrics_incrementally(
    foundation: Path,
    database: Path,
    release_aggregate: Path,
    staging: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cutoff = metric_period(database)
    periods = sorted({str(item["reporting_period"]) for item in manifest["partitions"]})
    pending = [period for period in periods if period > cutoff]
    if not pending:
        return {"mode": "not-required", "previous_period": cutoff, "new_periods": []}
    cutoff_index = periods.index(cutoff)
    first_period = periods[max(0, cutoff_index - 2)]
    delta_foundation, delta_periods = create_delta_foundation(
        foundation,
        manifest,
        staging / "delta-foundation",
        first_period,
    )
    delta_release = subset_release(release_aggregate, staging / "delta-release.csv", delta_periods)
    delta_database = staging / "delta.duckdb"
    delta_evaluation = staging / "delta-evaluation.json"
    build_metric_engine(delta_foundation, delta_database, delta_evaluation, delta_release)
    candidate = staging / "metrics-candidate.duckdb"
    result = merge_metric_delta(database, delta_database, candidate, cutoff, int(manifest["records"]))
    return {
        "mode": "rolling-window-incremental",
        "previous_period": cutoff,
        "new_periods": pending,
        "recomputed_periods": sorted(delta_periods),
        **result,
    }


def benchmark_scaled_local(foundation: Path, database: Path) -> dict[str, Any]:
    manifest = load_json(foundation / "manifest.json")
    partitions = manifest["partitions"]
    latest = max(partitions, key=lambda item: (item["reporting_period"], item["deal_id"]))
    parquet_glob = str((foundation / "loan_period" / "**" / "*.parquet").resolve())
    connection = duckdb.connect()
    try:
        explain = connection.execute(
            "EXPLAIN ANALYZE SELECT sum(length(loan_identifier)) FROM read_parquet(?, hive_partitioning=true) WHERE deal_id=? AND reporting_period=?",
            [parquet_glob, latest["deal_id"], latest["reporting_period"]],
        ).fetchone()[1]
        match = re.search(r"Scanning Files: (\d+)/(\d+)", explain)
        if match is None:
            raise ValueError("DuckDB profile did not report partition file pruning")
        filtered_started = time.perf_counter()
        connection.execute(
            "SELECT sum(length(loan_identifier)) FROM read_parquet(?, hive_partitioning=true) WHERE deal_id=? AND reporting_period=?",
            [parquet_glob, latest["deal_id"], latest["reporting_period"]],
        ).fetchone()
        filtered_ms = (time.perf_counter() - filtered_started) * 1000
        full_started = time.perf_counter()
        full_identifier_characters = connection.execute(
            "SELECT sum(length(loan_identifier)) FROM read_parquet(?, hive_partitioning=true)",
            [parquet_glob],
        ).fetchone()[0]
        full_scan_ms = (time.perf_counter() - full_started) * 1000
    finally:
        connection.close()
    query_times: list[float] = []
    with duckdb.connect(str(database), read_only=True) as metric_connection:
        for _ in range(20):
            started = time.perf_counter()
            metric_connection.execute(
                "SELECT deal_id, d60_plus_rate, d60_change_1m_bps FROM deal_period_metrics WHERE reporting_period=(SELECT max(reporting_period) FROM deal_period_metrics) ORDER BY d60_change_1m_bps DESC"
            ).fetchall()
            query_times.append((time.perf_counter() - started) * 1000)
    query_times.sort()
    parquet_bytes = sum(int(item["parquet_bytes"]) for item in partitions)
    disk = shutil.disk_usage(foundation)
    return {
        "hardware": {
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "available_disk_bytes": disk.free,
        },
        "foundation": {
            "records": int(manifest["records"]),
            "partitions": len(partitions),
            "parquet_bytes": parquet_bytes,
            "full_identifier_characters": int(full_identifier_characters),
        },
        "partition_pruning": {
            "selected_deal": latest["deal_id"],
            "selected_period": latest["reporting_period"],
            "files_read": int(match.group(1)),
            "files_available": int(match.group(2)),
            "filtered_scan_ms": round(filtered_ms, 3),
            "status": "pass" if int(match.group(1)) == 1 else "fail",
        },
        "capacity": {
            "full_history_column_scan_ms": round(full_scan_ms, 3),
            "full_history_scan_threshold_ms": 5000.0,
            "metric_query_p95_ms": round(query_times[18], 3),
            "metric_query_threshold_ms": 2000.0,
            "status": "pass" if full_scan_ms < 5000 and query_times[18] < 2000 else "fail",
        },
        "scale_trigger": {
            "local_storage_utilization": round(parquet_bytes / (parquet_bytes + disk.free), 6),
            "migrate_when": [
                "full metric refresh exceeds 120 seconds twice on standard hardware",
                "common warm query exceeds 2 seconds",
                "restricted storage exceeds 70% of available local capacity",
                "more than one governed concurrent analyst or shared scheduled refresh is required",
            ],
        },
    }


def prune_run_manifests(runs_dir: Path, retain: int, current: Path) -> list[str]:
    paths = sorted((path for path in runs_dir.glob("*.json") if path != current), key=lambda path: path.stat().st_mtime)
    remove_count = max(0, len(paths) + 1 - retain)
    removed: list[str] = []
    for path in paths[:remove_count]:
        removed.append(path.name)
        path.unlink()
    return removed


def run(args: argparse.Namespace) -> dict[str, Any]:
    archive = args.archive.resolve()
    foundation = args.foundation.resolve()
    database = args.database.resolve()
    release_aggregate = args.release_aggregate.resolve()
    operations = args.operations_dir.resolve()
    evaluation_path = args.evaluation.resolve()
    if not archive.is_file() or not (foundation / "manifest.json").is_file() or not database.is_file():
        raise ValueError("archive, foundation manifest, and metric database are required")
    if not args.allow_nonrestricted_output:
        for path in (foundation, database, operations):
            if not path.is_relative_to(RESTRICTED.resolve()):
                raise ValueError(f"restricted output must remain under {RESTRICTED}: {path}")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:8]}"
    run_path = operations / "runs" / f"{run_id}.json"
    staging = operations / "staging" / run_id
    started = time.perf_counter()
    recovery = recover_interrupted_runs(operations, foundation)
    manifest = load_json(foundation / "manifest.json")
    inventory, rejected = archive_inventory(archive)
    inventory_path = operations / "source_inventory.json"
    if inventory_path.exists():
        inventory_state = load_json(inventory_path)
    else:
        inventory_state = initialize_inventory(archive, manifest, inventory, inventory_path)
    new_keys = validate_append_only(inventory_state["partitions"], inventory)
    planned = [
        str(Path("loan_period") / f"deal_id={inventory[key]['deal_id']}" / f"reporting_period={inventory[key]['reporting_period']}" / "data.parquet")
        for key in new_keys
    ]
    record: dict[str, Any] = {
        "version": 1,
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "source_archive_name": archive.name,
        "source_archive_sha256": sha256(archive),
        "baseline_records": int(manifest["records"]),
        "baseline_partitions": int(manifest["accepted_files"]),
        "new_partition_keys": new_keys,
        "planned_partition_paths": planned,
        "recovery": recovery,
        "data_classification": "restricted-operational-evidence",
        "public_release_allowed": False,
    }
    atomic_json(run_path, record)
    try:
        staging.mkdir(parents=True)
        manifest, appended_paths = append_partitions(
            archive,
            foundation,
            staging,
            new_keys,
            inventory,
            rejected,
        )
        if new_keys:
            inventory_state = {
                "version": 1,
                "initialized_at": inventory_state["initialized_at"],
                "updated_at": utc_now(),
                "source_archive_sha256": sha256(archive),
                "partitions": inventory,
            }
            atomic_json(inventory_path, inventory_state)
        latest_foundation_period = max(str(item["reporting_period"]) for item in manifest["partitions"])
        release_rebuild_required = latest_foundation_period > release_period(release_aggregate)
        if new_keys or release_rebuild_required:
            aggregate_dir = staging / "aggregate"
            candidate_release = derive_release_aggregate(archive, aggregate_dir)
        else:
            candidate_release = release_aggregate
        metric_refresh = refresh_metrics_incrementally(
            foundation,
            database,
            candidate_release,
            staging,
            manifest,
        )
        if candidate_release != release_aggregate:
            release_aggregate.parent.mkdir(parents=True, exist_ok=True)
            os.replace(candidate_release, release_aggregate)
        benchmark = benchmark_scaled_local(foundation, database)
        if benchmark["partition_pruning"]["status"] != "pass" or benchmark["capacity"]["status"] != "pass":
            raise ValueError("scaled-local benchmark failed")
        record.update(
            {
                "status": "pass",
                "completed_at": utc_now(),
                "result_records": int(manifest["records"]),
                "result_partitions": int(manifest["accepted_files"]),
                "appended_partition_paths": appended_paths,
                "metric_refresh": metric_refresh,
                "benchmark": benchmark,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
        record["retention"] = {
            "retained_run_manifests": args.retain_runs,
            "removed_run_manifests": prune_run_manifests(run_path.parent, args.retain_runs, run_path),
            "source_and_foundation_policy": "Retain current approved source archive and foundation; replace only after a verified append-only refresh.",
        }
        atomic_json(run_path, record)
        evaluation = {
            "report_version": 1,
            "evaluation_date": datetime.now(UTC).date().isoformat(),
            "milestone": "M12",
            "status": "pass",
            "incremental_refresh": {
                "status": "pass",
                "new_partitions": len(new_keys),
                "mode": metric_refresh["mode"],
                "unaffected_history_preserved": metric_refresh.get("historical_row_hashes_preserved", True),
            },
            "recovery": {"status": "pass", **recovery},
            "run_manifest": {
                "status": "pass",
                "path": str(run_path),
                "retention_count": args.retain_runs,
            },
            **benchmark,
            "limitations": [
                "Append-only refresh rejects revised or missing historical deal-period files and requires a controlled full rebuild for approved revisions.",
                "Capacity evidence is single-user local execution, not hosted concurrency evidence.",
            ],
        }
        atomic_json(evaluation_path, evaluation)
        return evaluation
    except Exception as error:
        record.update(
            {
                "status": "failed",
                "completed_at": utc_now(),
                "error": str(error),
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
        atomic_json(run_path, record)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--foundation", type=Path, default=DEFAULT_FOUNDATION)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--release-aggregate", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--operations-dir", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--retain-runs", type=int, default=12)
    parser.add_argument("--allow-nonrestricted-output", action="store_true", help="Tests only")
    args = parser.parse_args()
    if args.retain_runs < 2:
        raise SystemExit("retain-runs must be at least 2")
    try:
        result = run(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"M12 scaled-local controls pass: {result['foundation']['records']:,} rows, "
        f"{result['partition_pruning']['files_read']}/{result['partition_pruning']['files_available']} files read",
        flush=True,
    )


if __name__ == "__main__":
    main()
