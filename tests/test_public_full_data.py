from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from api.records import QueryError, asset_name, download_asset, payload, query_partition
from scripts.build_public_full_data import build


class PublicFullDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.foundation = self.root / "foundation"
        self.output = self.root / "public"
        self.foundation.mkdir()
        self.key = self.root / "mask.key"
        self.key.write_bytes(b"test-only-public-mask-material" * 2)

        partitions = []
        records = {
            ("2022-HQA1", "202607"): [
                ("202607", "P1", "RAW-LOAN-001", "606", "00", "250000", "760"),
                ("202607", "P1", "RAW-LOAN-002", "606", "03", "190000", "700"),
            ],
            ("2022-HQA1", "202606"): [
                ("202606", "P1", "RAW-LOAN-001", "606", "01", "245000", "760"),
            ],
        }
        connection = duckdb.connect()
        try:
            for (deal_id, period), rows in records.items():
                path = (
                    self.foundation
                    / "loan_period"
                    / f"deal_id={deal_id}"
                    / f"reporting_period={period}"
                    / "data.parquet"
                )
                path.parent.mkdir(parents=True)
                connection.execute(
                    """
                    CREATE OR REPLACE TABLE sample (
                        period VARCHAR,
                        reference_pool_number VARCHAR,
                        loan_identifier VARCHAR,
                        postal_code_3_digit VARCHAR,
                        current_loan_delinquency_status VARCHAR,
                        current_actual_upb VARCHAR,
                        classic_fico VARCHAR
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO sample VALUES (?, ?, ?, ?, ?, ?, ?)", rows
                )
                connection.execute("COPY sample TO ? (FORMAT PARQUET)", [str(path)])
                partitions.append(
                    {
                        "deal_id": deal_id,
                        "reporting_period": period,
                        "records": len(rows),
                        "parquet_path": str(path.relative_to(self.foundation)),
                    }
                )
        finally:
            connection.close()
        (self.foundation / "manifest.json").write_text(
            json.dumps(
                {
                    "records": 3,
                    "fields_retained": 7,
                    "partitions": partitions,
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_builder_preserves_rows_and_masks_direct_identifiers_stably(self) -> None:
        manifest = build(self.foundation, self.output, self.key)
        self.assertEqual(manifest["records"], 3)
        self.assertEqual(manifest["partitions"], 2)
        self.assertEqual(manifest["classification"], "public-full-record-masked")
        self.assertEqual(
            manifest["masked_fields"], ["loan_identifier", "postal_code_3_digit"]
        )

        connection = duckdb.connect()
        try:
            current = connection.execute(
                "SELECT loan_identifier, postal_code_3_digit FROM read_parquet(?) ORDER BY loan_identifier",
                [str(self.output / "2022-HQA1--202607.parquet")],
            ).fetchall()
            prior = connection.execute(
                "SELECT loan_identifier, postal_code_3_digit FROM read_parquet(?)",
                [str(self.output / "2022-HQA1--202606.parquet")],
            ).fetchone()
        finally:
            connection.close()
        self.assertTrue(all(row[0].startswith("loan-") for row in current))
        self.assertTrue(all(row[1].startswith("geo-") for row in current))
        self.assertIn(prior, current)
        self.assertNotIn("RAW-LOAN-001", {value for row in current for value in row})
        self.assertNotIn("606", {value for row in current for value in row})

    def test_api_returns_all_stored_fields_and_enforces_filters(self) -> None:
        build(self.foundation, self.output, self.key)
        path = self.output / "2022-HQA1--202607.parquet"
        result = query_partition(path, "d90", 25, 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["fields"]), 7)
        self.assertEqual(set(result["rows"][0]), set(result["fields"]))
        self.assertTrue(result["rows"][0]["loan_identifier"].startswith("loan-"))

        with patch.dict("os.environ", {"CRT_DATA_DIR": str(self.output)}):
            response = payload(
                {
                    "deal": ["2022-HQA1"],
                    "period": ["202607"],
                    "status": ["all"],
                    "limit": ["1"],
                    "offset": ["1"],
                }
            )
        self.assertEqual(response["total"], 2)
        self.assertEqual(response["limit"], 1)
        self.assertEqual(response["offset"], 1)

    def test_api_rejects_unbounded_or_unsafe_requests(self) -> None:
        with self.assertRaises(QueryError):
            asset_name("../../private", "202607")
        with self.assertRaises(QueryError):
            query_partition(self.root / "missing.parquet", "all", 25, 0)
        build(self.foundation, self.output, self.key)
        path = self.output / "2022-HQA1--202607.parquet"
        with self.assertRaises(QueryError):
            query_partition(path, "all", 51, 0)
        with self.assertRaises(QueryError):
            query_partition(path, "all", 25, 150_001)
        with self.assertRaises(QueryError):
            query_partition(path, "unsupported", 25, 0)

    def test_remote_asset_uses_authenticated_gateway_and_fails_closed(self) -> None:
        class Response(io.BytesIO):
            def __init__(self, value: bytes):
                super().__init__(value)
                self.headers = {"Content-Length": "7"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        remote = self.root / "remote-cache"
        remote.mkdir()
        with (
            patch("api.records.tempfile.gettempdir", return_value=str(remote)),
            patch(
                "api.records.urllib.request.urlopen",
                return_value=Response(b"parquet"),
            ) as opened,
            patch.dict(
                os.environ,
                {
                    "CRT_DATA_GATEWAY_URL": "https://data.example.test",
                    "CRT_DATA_GATEWAY_TOKEN": "secret-token",
                },
                clear=True,
            ),
        ):
            downloaded = download_asset("2022-HQA1--202607.parquet")
        request = opened.call_args.args[0]
        self.assertEqual(downloaded.read_bytes(), b"parquet")
        self.assertEqual(
            request.full_url,
            "https://data.example.test/full-data-v2026-07/2022-HQA1--202607.parquet",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

        with (
            patch(
                "api.records.tempfile.gettempdir", return_value=str(remote / "empty")
            ),
            patch.dict(os.environ, {}, clear=True),
            self.assertRaises(RuntimeError),
        ):
            download_asset("2022-HQA1--202606.parquet")


if __name__ == "__main__":
    unittest.main()
