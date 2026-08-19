#!/usr/bin/env python3
"""Serve the restricted CRT analyst workbench on loopback only."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import duckdb


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "private_app"
DEFAULT_DATABASE = ROOT / "data/restricted/metrics/metrics.duckdb"
DEFAULT_EVALUATION = ROOT / "data/derived/m8_metric_evaluation.json"
HOST = "127.0.0.1"
PERIOD_PATTERN = re.compile(r"^\d{6}$")
DEAL_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,32}$")
SORT_COLUMNS = {
    "total_contribution_bps": "x.total_contribution_bps",
    "d60_change_1m_bps": "d.d60_change_1m_bps",
    "d60_plus_rate": "d.d60_plus_rate",
    "eligible_current_upb": "d.eligible_current_upb",
    "current_to_d30_rate_upb": "f.current_to_d30_rate_upb",
    "d30_to_d60_rate_upb": "f.d30_to_d60_rate_upb",
    "credit_event_exit_rate_upb": "f.credit_event_exit_rate_upb",
    "assistance_exposure_share": "d.assistance_exposure_share",
    "rate_effect_bps": "x.rate_effect_bps",
}
TOTAL_CONTRIBUTION_METRIC = {
    "metric_id": "d60_total_contribution_bps",
    "metric_version": "m8.1.0",
    "definition": "Signed deal contribution to the portfolio monthly D60+ rate change, in basis points.",
    "method": "Current deal weight times current D60+ rate minus prior deal weight times prior D60+ rate; exactly equals rate effect plus mix effect.",
    "business_meaning": "Ranks the deals that added most to or offset the portfolio movement.",
    "desired_direction": "Lower or negative contribution is favorable.",
    "baseline": "Eligible-current-UPB-weighted portfolio monthly D60+ change.",
    "result_location": "portfolio_d60_decomposition.total_contribution_bps",
    "supported_decision": "Choose which deal contribution to investigate first.",
    "limitation": "Contribution depends on both performance and portfolio weight and does not establish causality.",
}
PERFORMANCE_STATES = {
    "all": None,
    "current": "CURRENT",
    "d30": "D30",
    "d60": "D60",
    "d90": "D90_PLUS",
    "reo": "REO",
}


def local_request_allowed(host: str | None, origin: str | None, port: int) -> bool:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    normalized_host = (host or "").lower()
    if normalized_host not in allowed_hosts:
        return False
    if not origin:
        return True
    return origin.lower() in {f"http://{value}" for value in allowed_hosts}


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def rows(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[Any] | None = None) -> list[dict[str, Any]]:
    relation = connection.execute(sql, parameters or [])
    columns = [item[0] for item in relation.description]
    return [dict(zip(columns, record, strict=True)) for record in relation.fetchall()]


def one(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[Any] | None = None) -> dict[str, Any] | None:
    result = rows(connection, sql, parameters)
    return result[0] if result else None


class RequestError(ValueError):
    """A safe client-facing request failure."""


class WorkbenchRepository:
    def __init__(self, database: Path, evaluation: Path = DEFAULT_EVALUATION) -> None:
        self.database = database.resolve()
        self.evaluation = evaluation.resolve()

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.database), read_only=True)

    @staticmethod
    def validate_period(value: str) -> str:
        if not PERIOD_PATTERN.fullmatch(value):
            raise RequestError("Reporting period must use YYYYMM format.")
        return value

    @staticmethod
    def validate_deal(value: str) -> str:
        if not DEAL_PATTERN.fullmatch(value):
            raise RequestError("Deal identifier is invalid.")
        return value

    def _require_period(self, connection: duckdb.DuckDBPyConnection, period: str) -> str:
        self.validate_period(period)
        found = connection.execute(
            "SELECT 1 FROM portfolio_period_metrics WHERE reporting_period = ? LIMIT 1",
            [period],
        ).fetchone()
        if not found:
            raise RequestError("Reporting period is not available.")
        return period

    def _require_deal(self, connection: duckdb.DuckDBPyConnection, deal_id: str) -> str:
        self.validate_deal(deal_id)
        found = connection.execute(
            "SELECT 1 FROM deal_period_metrics WHERE deal_id = ? LIMIT 1",
            [deal_id],
        ).fetchone()
        if not found:
            raise RequestError("Deal is not available.")
        return deal_id

    def bootstrap(self) -> dict[str, Any]:
        started = time.perf_counter()
        with self.connect() as connection:
            periods = [record[0] for record in connection.execute(
                "SELECT reporting_period FROM portfolio_period_metrics ORDER BY reporting_period DESC"
            ).fetchall()]
            deals = [record[0] for record in connection.execute(
                "SELECT DISTINCT deal_id FROM deal_period_metrics ORDER BY deal_id"
            ).fetchall()]
            metric_versions = [record[0] for record in connection.execute(
                "SELECT DISTINCT metric_version FROM metric_catalog ORDER BY metric_version"
            ).fetchall()]
            catalog = rows(
                connection,
                """
                SELECT metric_id, metric_version, definition, method, business_meaning,
                       desired_direction, baseline, result_location, supported_decision, limitation
                FROM metric_catalog ORDER BY metric_id
                """,
            )
            catalog.append(TOTAL_CONTRIBUTION_METRIC)
        return {
            "local_only": True,
            "data_classification": "restricted-derived-analytics",
            "periods": periods,
            "deals": deals,
            "latest_period": periods[0],
            "metric_versions": metric_versions,
            "metric_catalog": catalog,
            "query_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def overview(
        self,
        period: str,
        sort_by: str = "total_contribution_bps",
        direction: str = "desc",
    ) -> dict[str, Any]:
        if sort_by not in SORT_COLUMNS:
            raise RequestError("Watchlist sort metric is not supported.")
        if direction not in {"asc", "desc"}:
            raise RequestError("Sort direction must be asc or desc.")
        started = time.perf_counter()
        with self.connect() as connection:
            period = self._require_period(connection, period)
            portfolio = one(
                connection,
                """
                SELECT reporting_period, period_date, in_scope_records, eligible_active_loans,
                       reported_current_upb, eligible_current_upb, excluded_ra_records,
                       excluded_ra_upb, excluded_xx_records, excluded_xx_upb,
                       d30_plus_upb, d60_plus_upb, d90_plus_upb, d30_plus_rate,
                       d60_plus_rate, d90_plus_rate, d60_change_1m_bps,
                       d60_change_3m_bps, pool_factor, wa_classic_fico,
                       wa_original_ltv, wa_original_cltv, wa_original_dti,
                       wa_current_coupon, wa_loan_age, new_modification_rate_count,
                       assistance_exposure_share, cumulative_actual_loss,
                       actual_loss_observations, metric_version
                FROM portfolio_period_metrics WHERE reporting_period = ?
                """,
                [period],
            )
            watchlist = rows(
                connection,
                f"""
                SELECT d.deal_id, d.reporting_period, d.eligible_active_loans,
                       d.eligible_current_upb, d.d60_plus_upb, d.d30_plus_rate, d.d60_plus_rate,
                       d.d90_plus_rate, d.d60_change_1m_bps, d.d60_change_3m_bps,
                       d.assistance_exposure_share, d.new_modification_rate_count,
                       d.wa_classic_fico, d.wa_original_ltv, d.wa_original_dti,
                       f.loan_match_rate, f.current_to_d30_rate_upb,
                       f.d30_to_d60_rate_upb, f.cure_rate_upb,
                       f.voluntary_payoff_rate_upb, f.credit_event_exit_rate_upb,
                       f.current_to_d30_loans, f.d30_to_d60_loans, f.cured_loans,
                       f.credit_event_exit_loans, x.rate_effect_bps,
                       x.mix_effect_bps, x.total_contribution_bps, d.metric_version
                FROM deal_period_metrics d
                LEFT JOIN deal_period_flow_metrics f USING (deal_id, reporting_period)
                LEFT JOIN portfolio_d60_decomposition x USING (deal_id, reporting_period)
                WHERE d.reporting_period = ?
                ORDER BY {SORT_COLUMNS[sort_by]} {direction.upper()} NULLS LAST, d.deal_id
                """,
                [period],
            )
            decomposition = rows(
                connection,
                """
                SELECT deal_id, current_upb, prior_upb, current_weight, prior_weight,
                       current_rate, prior_rate, rate_effect_bps, mix_effect_bps,
                       total_contribution_bps, metric_version
                FROM portfolio_d60_decomposition
                WHERE reporting_period = ?
                ORDER BY abs(total_contribution_bps) DESC, deal_id
                """,
                [period],
            )
        totals = {
            "rate_effect_bps": sum(float(item["rate_effect_bps"] or 0) for item in decomposition),
            "mix_effect_bps": sum(float(item["mix_effect_bps"] or 0) for item in decomposition),
            "total_contribution_bps": sum(float(item["total_contribution_bps"] or 0) for item in decomposition),
        }
        return {
            "period": period,
            "sort_by": sort_by,
            "direction": direction,
            "portfolio": portfolio,
            "watchlist": watchlist,
            "decomposition": decomposition,
            "decomposition_totals": totals,
            "query_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def deal(self, period: str, deal_id: str) -> dict[str, Any]:
        started = time.perf_counter()
        with self.connect() as connection:
            period = self._require_period(connection, period)
            deal_id = self._require_deal(connection, deal_id)
            current = one(
                connection,
                """
                SELECT * EXCLUDE (fico_weighted_sum, fico_known_upb, ltv_weighted_sum,
                                  ltv_known_upb, cltv_weighted_sum, cltv_known_upb,
                                  dti_weighted_sum, dti_known_upb, coupon_weighted_sum,
                                  coupon_known_upb, loan_age_weighted_sum, loan_age_known_upb)
                FROM deal_period_metrics WHERE reporting_period = ? AND deal_id = ?
                """,
                [period, deal_id],
            )
            if current is None:
                raise RequestError("The selected deal has no observation in this period.")
            series = rows(
                connection,
                """
                SELECT reporting_period, d30_plus_rate, d60_plus_rate, d90_plus_rate,
                       d60_change_1m_bps, eligible_current_upb
                FROM deal_period_metrics
                WHERE deal_id = ? AND reporting_period <= ? ORDER BY reporting_period
                """,
                [deal_id, period],
            )
            portfolio_series = rows(
                connection,
                """
                SELECT reporting_period, d60_plus_rate, d60_change_1m_bps,
                       eligible_current_upb
                FROM portfolio_period_metrics
                WHERE reporting_period <= ? ORDER BY reporting_period
                """,
                [period],
            )
            flow = one(
                connection,
                "SELECT * FROM deal_period_flow_metrics WHERE reporting_period = ? AND deal_id = ?",
                [period, deal_id],
            )
            risk_layers = rows(
                connection,
                """
                SELECT risk_layer_count, eligible_loans, eligible_current_upb,
                       loan_share, upb_share, metric_version
                FROM deal_period_risk_layer_metrics
                WHERE reporting_period = ? AND deal_id = ? ORDER BY risk_layer_count
                """,
                [period, deal_id],
            )
            pools = rows(
                connection,
                """
                SELECT reference_pool_number, eligible_active_loans, eligible_current_upb,
                       d30_plus_rate, d60_plus_rate, d90_plus_rate,
                       d60_change_1m_bps, assistance_exposure_share,
                       new_modification_rate_count, metric_version
                FROM pool_period_metrics
                WHERE reporting_period = ? AND deal_id = ?
                ORDER BY d60_change_1m_bps DESC NULLS LAST, reference_pool_number
                """,
                [period, deal_id],
            )
        return {
            "period": period,
            "deal_id": deal_id,
            "current": current,
            "series": series,
            "portfolio_series": portfolio_series,
            "flow": flow,
            "risk_layers": risk_layers,
            "pools": pools,
            "query_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def loans(
        self,
        period: str,
        deal_id: str,
        status: str = "all",
        risk_layer: str = "all",
        limit: int = 50,
        offset: int = 0,
        include_identifiers: bool = False,
    ) -> dict[str, Any]:
        if status not in PERFORMANCE_STATES:
            raise RequestError("Loan status filter is not supported.")
        if risk_layer != "all" and risk_layer not in {"0", "1", "2", "3", "4"}:
            raise RequestError("Risk-layer filter is not supported.")
        if not 1 <= limit <= 100:
            raise RequestError("Loan page size must be between 1 and 100.")
        if not 0 <= offset <= 1_000_000:
            raise RequestError("Loan offset is outside the supported range.")
        started = time.perf_counter()
        with self.connect() as connection:
            period = self._require_period(connection, period)
            deal_id = self._require_deal(connection, deal_id)
            predicates = ["reporting_period = ?", "deal_id = ?"]
            parameters: list[Any] = [period, deal_id]
            performance_state = PERFORMANCE_STATES[status]
            if performance_state:
                predicates.append("performance_state = ?")
                parameters.append(performance_state)
            if risk_layer != "all":
                predicates.append("risk_layer_count = ?")
                parameters.append(int(risk_layer))
            where = " AND ".join(predicates)
            total = connection.execute(
                f"SELECT count(*) FROM loan_period_typed WHERE {where}", parameters
            ).fetchone()[0]
            identifier = (
                "loan_identifier"
                if include_identifiers
                else "concat('restricted-', right(loan_identifier, 4)) AS loan_identifier"
            )
            page_parameters = [*parameters, limit, offset]
            data = rows(
                connection,
                f"""
                SELECT {identifier}, reference_pool_number, current_upb,
                       performance_state, delinquency_status_raw, zero_balance_code,
                       risk_layer_count, classic_fico_value, original_ltv_value,
                       original_cltv_value, original_dti_value, current_interest_rate_value,
                       loan_age_value, origination_vintage, loan_purpose, channel,
                       occupancy_status, property_type, property_state, modification_flag,
                       borrower_assistance_plan, payment_deferral_flag,
                       delinquency_due_to_disaster, servicer_name, pool_construct
                FROM loan_period_typed WHERE {where}
                ORDER BY risk_layer_count DESC, delinquency_months DESC NULLS LAST,
                         current_upb DESC NULLS LAST, loan_identifier
                LIMIT ? OFFSET ?
                """,
                page_parameters,
            )
        return {
            "period": period,
            "deal_id": deal_id,
            "status": status,
            "risk_layer": risk_layer,
            "identifiers_revealed": include_identifiers,
            "total": total,
            "limit": limit,
            "offset": offset,
            "rows": data,
            "query_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def evidence_package(self, period: str, deal_id: str) -> dict[str, Any]:
        overview = self.overview(period)
        detail = self.deal(period, deal_id)
        selected_driver = next(
            (item for item in overview["decomposition"] if item["deal_id"] == deal_id),
            None,
        )
        evaluation: dict[str, Any] = {}
        if self.evaluation.exists():
            evaluation = json.loads(self.evaluation.read_text(encoding="utf-8"))
        return {
            "package_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "data_classification": "restricted-derived-analytics",
            "public_release_allowed": False,
            "purpose": "Authorized CRT collateral-surveillance evidence handoff",
            "filters": {"reporting_period": period, "deal_id": deal_id},
            "metric_version": detail["current"]["metric_version"],
            "portfolio": overview["portfolio"],
            "deal": detail["current"],
            "driver": selected_driver,
            "flow": detail["flow"],
            "risk_layers": detail["risk_layers"],
            "controls": {
                "typed_input_gate": evaluation.get("typed_input_gate"),
                "release_reconciliation": evaluation.get("release_reconciliation"),
                "transition_integrity": evaluation.get("transition_integrity"),
                "decomposition_integrity": evaluation.get("decomposition_integrity"),
                "actual_loss_availability": evaluation.get("actual_loss_availability"),
                "source_archive_sha256": evaluation.get("source_archive_sha256"),
                "metric_database_sha256": evaluation.get("restricted_output", {}).get("database_sha256"),
            },
            "limitations": [
                "Descriptive surveillance analysis, not investment advice or borrower decisioning.",
                "Deal-level attribution is descriptive and does not establish causality.",
                "Loan rows and identifiers are intentionally excluded from this evidence package.",
                "Actual Loss rate remains unavailable until two adjacent disclosed periods exist.",
            ],
        }


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "CRTWorkbench/1.0"
    sys_version = ""

    def __init__(self, *args: Any, repository: WorkbenchRepository, **kwargs: Any) -> None:
        self.repository = repository
        super().__init__(*args, **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    def log_message(self, format_string: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format_string % args}")

    def send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
        filename: str | None = None,
        head_only: bool = False,
    ) -> None:
        body = json.dumps(payload, default=json_default, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def send_static(self, relative_path: str, head_only: bool = False) -> None:
        target = (APP_DIR / relative_path).resolve()
        if APP_DIR.resolve() not in target.parents and target != APP_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        types = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}
        content_type = types.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    @staticmethod
    def param(query: dict[str, list[str]], name: str, default: str = "") -> str:
        return query.get(name, [default])[0]

    def route(self, head_only: bool = False) -> None:
        if not local_request_allowed(
            self.headers.get("Host"),
            self.headers.get("Origin"),
            self.server.server_port,
        ):
            self.send_json(
                {
                    "error": "The private workbench accepts same-origin loopback requests only.",
                    "recovery": "Open the workbench from its displayed 127.0.0.1 URL.",
                },
                HTTPStatus.MISDIRECTED_REQUEST,
                head_only=head_only,
            )
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                self.send_json(
                    {"status": "ok", "local_only": True, "database_open": self.repository.database.exists()},
                    head_only=head_only,
                )
            elif parsed.path == "/api/bootstrap":
                self.send_json(self.repository.bootstrap(), head_only=head_only)
            elif parsed.path == "/api/overview":
                self.send_json(
                    self.repository.overview(
                        self.param(query, "period"),
                        self.param(query, "sort", "total_contribution_bps"),
                        self.param(query, "direction", "desc"),
                    ),
                    head_only=head_only,
                )
            elif parsed.path == "/api/deal":
                self.send_json(
                    self.repository.deal(
                        self.param(query, "period"), self.param(query, "deal_id")
                    ),
                    head_only=head_only,
                )
            elif parsed.path == "/api/loans":
                self.send_json(
                    self.repository.loans(
                        self.param(query, "period"),
                        self.param(query, "deal_id"),
                        self.param(query, "status", "all"),
                        self.param(query, "risk_layer", "all"),
                        int(self.param(query, "limit", "50")),
                        int(self.param(query, "offset", "0")),
                        self.param(query, "include_identifiers", "false") == "true",
                    ),
                    head_only=head_only,
                )
            elif parsed.path == "/api/evidence":
                period = self.param(query, "period")
                deal_id = self.param(query, "deal_id")
                filename = f"crt-evidence-{deal_id}-{period}.json"
                self.send_json(
                    self.repository.evidence_package(period, deal_id),
                    filename=filename,
                    head_only=head_only,
                )
            elif parsed.path in {"/", "/index.html"}:
                self.send_static("index.html", head_only)
            elif parsed.path in {"/styles.css", "/app.js"}:
                self.send_static(parsed.path.lstrip("/"), head_only)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except RequestError as error:
            self.send_json({"error": str(error), "recovery": "Reset the affected filter and retry."}, HTTPStatus.BAD_REQUEST, head_only=head_only)
        except (TypeError, ValueError):
            self.send_json({"error": "Request parameters are invalid.", "recovery": "Reset the affected filter and retry."}, HTTPStatus.BAD_REQUEST, head_only=head_only)
        except Exception as error:
            print(f"workbench error: {type(error).__name__}: {error}")
            self.send_json(
                {"error": "The local analytical query failed.", "recovery": "Verify the restricted metric database and restart the workbench."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
                head_only=head_only,
            )

    def do_GET(self) -> None:
        self.route()

    def do_HEAD(self) -> None:
        self.route(head_only=True)


def build_server(repository: WorkbenchRepository, port: int) -> ThreadingHTTPServer:
    handler = partial(WorkbenchHandler, repository=repository)
    return ThreadingHTTPServer((HOST, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the private CRT analyst workbench on loopback.")
    parser.add_argument("--port", type=int, default=8011, help="Loopback port (default: 8011).")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="Restricted M8 DuckDB database.")
    args = parser.parse_args()
    database = args.database.resolve()
    restricted_root = (ROOT / "data/restricted").resolve()
    if restricted_root not in database.parents:
        raise SystemExit("Refusing a metric database outside data/restricted/.")
    if not database.is_file():
        raise SystemExit(f"Metric database not found: {database}")
    repository = WorkbenchRepository(database)
    repository.bootstrap()
    server = build_server(repository, args.port)
    print(f"Private CRT workbench: http://{HOST}:{args.port}/")
    print("Restricted local mode. Do not expose this port beyond loopback.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPrivate CRT workbench stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
