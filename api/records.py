"""Public full-record query function for masked CRT disclosure partitions."""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import duckdb

RELEASE_TAG = "full-data-v2026-07"
DEAL_PATTERN = re.compile(r"^[0-9]{4}-HQA[0-9]$")
PERIOD_PATTERN = re.compile(r"^20[0-9]{4}$")
STATUSES = {"all", "current", "d30", "d60", "d90", "reo", "zero_balance"}
MAX_PAGE_SIZE = 50
MAX_OFFSET = 150_000
MAX_ASSET_BYTES = 12_000_000


class QueryError(ValueError):
    pass


def validated(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not pattern.fullmatch(value):
        raise QueryError(f"{label} is invalid.")
    return value


def asset_name(deal_id: str, period: str) -> str:
    return f"{validated(deal_id, DEAL_PATTERN, 'Deal')}--{validated(period, PERIOD_PATTERN, 'Period')}.parquet"


def download_asset(name: str) -> Path:
    local_dir = os.environ.get("CRT_DATA_DIR")
    if local_dir:
        path = Path(local_dir).resolve() / name
        if not path.is_file():
            raise QueryError("The selected full-data partition is unavailable.")
        return path
    target = Path(tempfile.gettempdir()) / f"crt-{name}"
    if target.is_file():
        return target
    gateway_url = os.environ.get("CRT_DATA_GATEWAY_URL", "").rstrip("/")
    gateway_token = os.environ.get("CRT_DATA_GATEWAY_TOKEN", "")
    if not gateway_url or not gateway_token:
        raise RuntimeError("The full-data gateway is not configured.")
    request = urllib.request.Request(
        f"{gateway_url}/{RELEASE_TAG}/{name}",
        headers={
            "Authorization": f"Bearer {gateway_token}",
            "User-Agent": "crt-full-data-query/1.0",
        },
    )
    temporary = Path(tempfile.mkstemp(prefix="crt-download-", suffix=".parquet")[1])
    try:
        with (
            urllib.request.urlopen(request, timeout=20) as response,
            temporary.open("wb") as destination,
        ):
            declared = int(response.headers.get("Content-Length", "0") or 0)
            if declared > MAX_ASSET_BYTES:
                raise QueryError(
                    "The selected partition exceeds the query-service limit."
                )
            copied = 0
            while chunk := response.read(1024 * 1024):
                copied += len(chunk)
                if copied > MAX_ASSET_BYTES:
                    raise QueryError(
                        "The selected partition exceeds the query-service limit."
                    )
                destination.write(chunk)
        temporary.replace(target)
        return target
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def status_sql(status: str) -> tuple[str, list[Any]]:
    if status not in STATUSES:
        raise QueryError("Loan status filter is not supported.")
    if status == "all":
        return "TRUE", []
    if status == "current":
        return "current_loan_delinquency_status = '00'", []
    if status == "d30":
        return "current_loan_delinquency_status = '01'", []
    if status == "d60":
        return "current_loan_delinquency_status = '02'", []
    if status == "d90":
        return "try_cast(current_loan_delinquency_status AS INTEGER) >= 3", []
    if status == "reo":
        return "current_loan_delinquency_status = 'RA'", []
    return "zero_balance_code IS NOT NULL AND zero_balance_code <> ''", []


def query_partition(path: Path, status: str, limit: int, offset: int) -> dict[str, Any]:
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise QueryError(f"Page size must be between 1 and {MAX_PAGE_SIZE}.")
    if not 0 <= offset <= MAX_OFFSET:
        raise QueryError("Page offset is outside the supported range.")
    predicate, parameters = status_sql(status)
    if not path.is_file():
        raise QueryError("The selected full-data partition is unavailable.")
    connection = duckdb.connect()
    try:
        total = int(
            connection.execute(
                f"SELECT count(*) FROM read_parquet(?) WHERE {predicate}",
                [str(path), *parameters],
            ).fetchone()[0]
        )
        relation = connection.execute(
            f"""
            SELECT * FROM read_parquet(?) WHERE {predicate}
            ORDER BY try_cast(current_loan_delinquency_status AS INTEGER) DESC NULLS LAST,
                     try_cast(current_actual_upb AS DOUBLE) DESC NULLS LAST, loan_identifier
            LIMIT ? OFFSET ?
            """,
            [str(path), *parameters, limit, offset],
        )
        fields = [column[0] for column in relation.description]
        rows = [
            dict(zip(fields, record, strict=True)) for record in relation.fetchall()
        ]
    finally:
        connection.close()
    return {
        "classification": "public-full-record-masked",
        "release": RELEASE_TAG,
        "masked_fields": ["loan_identifier", "postal_code_3_digit"],
        "total": total,
        "limit": limit,
        "offset": offset,
        "fields": fields,
        "rows": rows,
    }


def payload(query: dict[str, list[str]]) -> dict[str, Any]:
    deal_id = query.get("deal", [""])[0]
    period = query.get("period", [""])[0]
    status = query.get("status", ["all"])[0]
    try:
        limit = int(query.get("limit", ["25"])[0])
        offset = int(query.get("offset", ["0"])[0])
    except (TypeError, ValueError) as error:
        raise QueryError("Page controls must be whole numbers.") from error
    result = query_partition(
        download_asset(asset_name(deal_id, period)), status, limit, offset
    )
    result.update({"deal_id": deal_id, "reporting_period": period, "status": status})
    return result


class handler(BaseHTTPRequestHandler):
    server_version = "CRTRecords/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        try:
            body = json.dumps(
                payload(parse_qs(urlparse(self.path).query)), ensure_ascii=False
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header(
                "Cache-Control", "public, s-maxage=86400, stale-while-revalidate=604800"
            )
        except (QueryError, TypeError, ValueError) as error:
            body = json.dumps(
                {"error": str(error), "recovery": "Reset the record filters and retry."}
            ).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
        except (OSError, RuntimeError) as error:
            print(f"record query failed: {type(error).__name__}")
            body = json.dumps(
                {
                    "error": "The full-data partition could not be queried.",
                    "recovery": "Retry the selected deal and month.",
                }
            ).encode("utf-8")
            self.send_response(HTTPStatus.BAD_GATEWAY)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
