#!/usr/bin/env python3
"""Build the restricted M8 CRT surveillance metric engine from the full-data layer."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
from datetime import date
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
RESTRICTED = ROOT / "data" / "restricted"
DEFAULT_FOUNDATION = RESTRICTED / "full-data"
DEFAULT_OUTPUT = RESTRICTED / "metrics" / "metrics.duckdb"
DEFAULT_EVALUATION = ROOT / "data" / "derived" / "m8_metric_evaluation.json"
DEFAULT_RELEASE_AGGREGATE = ROOT / "data" / "derived" / "real_aggregate.csv"
METRIC_VERSION = "m8.1.0"
GLOSSARY = "Freddie Mac CRT Reference Pool Glossary v4.2, effective July 2026"


METRIC_CATALOG = [
    (
        "eligible_current_upb",
        "Sum of Current Actual UPB for positive-balance loans with a numeric delinquency state and no zero-balance code.",
        "Decimal sum after typed validity and active-population rules.",
        "Exposure represented by surveillance rates.",
        "Context, not directional.",
        "Existing release reported current UPB is retained separately for reconciliation.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Size and compare the active collateral population.",
        "Excludes REO/unknown states; Current Actual UPB can include deferred non-interest-bearing principal.",
    ),
    (
        "d30_plus_rate",
        "Eligible Current Actual UPB with delinquency months >=1 divided by eligible current UPB.",
        "UPB-weighted rate; release-compatible denominator is also retained.",
        "Broad early delinquency level.",
        "Lower.",
        "Existing release baseline used the reported-UPB denominator.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Identify broad deterioration and reconcile it to the prior release.",
        "A monthly snapshot; excluded REO and unknown balances are reported separately.",
    ),
    (
        "d60_plus_rate",
        "Eligible Current Actual UPB with delinquency months >=2 divided by eligible current UPB.",
        "UPB-weighted anchor rate; release-compatible denominator is also retained.",
        "Anchor collateral-deterioration level.",
        "Lower.",
        "Existing 2026-07 release-compatible baseline: 1.2795%.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Rank deals and explain changes in severe delinquency.",
        "Not a loss estimate, tranche metric, or borrower score.",
    ),
    (
        "d90_plus_rate",
        "Eligible Current Actual UPB with delinquency months >=3 divided by eligible current UPB.",
        "UPB-weighted rate.",
        "More severe delinquency level.",
        "Lower.",
        "Established by the M8 full-data run.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Separate severe arrears from broader D30+/D60+ movement.",
        "Current state does not describe the loan's full prior path.",
    ),
    (
        "d60_change_bps",
        "Current eligible D60+ rate minus its prior-period rate, multiplied by 10,000.",
        "One- and three-period window comparisons within the same deal or portfolio.",
        "Direction and persistence of deterioration.",
        "Lower or negative.",
        "Existing release-compatible change to 2026-07: +4.79 bps.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Rank the largest deteriorations for investigation.",
        "Population change can combine performance and mix effects.",
    ),
    (
        "d60_rate_effect_bps",
        "Average deal UPB weight multiplied by the change in that deal's eligible D60+ rate.",
        "Exact midpoint decomposition by deal; entry/exit rates are held at the observed rate.",
        "Within-deal contribution to portfolio deterioration.",
        "Lower or negative.",
        "Established by the M8 full-data run.",
        "portfolio_d60_decomposition",
        "Identify which deal's performance drove the portfolio change.",
        "Descriptive attribution, not causality.",
    ),
    (
        "d60_mix_effect_bps",
        "Average deal D60+ rate multiplied by the change in that deal's eligible-UPB weight.",
        "Exact midpoint decomposition by deal.",
        "Composition contribution to portfolio deterioration.",
        "Context; positive adverse contribution is undesirable.",
        "Established by the M8 full-data run.",
        "portfolio_d60_decomposition",
        "Distinguish performance movement from portfolio composition.",
        "Mix is descriptive and depends on the selected cohort boundary.",
    ),
    (
        "current_to_d30_roll_rate",
        "Matched prior-current loans becoming D30+ divided by matched prior-current loans.",
        "Reported by prior UPB and loan count.",
        "Early-warning flow into delinquency.",
        "Lower.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Find deals with rising early-stage delinquency pressure.",
        "Only adjacent-period matched loans are eligible.",
    ),
    (
        "d30_to_d60_roll_rate",
        "Matched prior-D30 loans becoming D60+ divided by matched prior-D30 loans.",
        "Reported by prior UPB and loan count.",
        "Escalation from early to more severe delinquency.",
        "Lower.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Identify escalation pressure.",
        "Small denominators require count and balance context.",
    ),
    (
        "cure_rate",
        "Matched prior-D30+ loans returning current divided by matched prior-D30+ loans.",
        "Reported by prior UPB and loan count.",
        "Resolution of delinquency.",
        "Higher.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Compare deterioration with resolution flow.",
        "A cure may be temporary; repeat delinquency is not inferred.",
    ),
    (
        "voluntary_payoff_rate",
        "New zero-balance code 01 prior UPB divided by beginning eligible UPB.",
        "Adjacent-period event detection using the official Actual Loss mapping.",
        "Voluntary collateral runoff.",
        "Context, not directional.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Separate payoff-driven runoff from adverse exits.",
        "Uses the observed HQA Actual Loss pool construct only.",
    ),
    (
        "credit_event_exit_rate",
        "New applicable credit-event zero-balance code prior UPB divided by beginning eligible UPB.",
        "Construct- and period-aware official code mapping.",
        "Adverse realized exits from the reference pool.",
        "Lower.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Distinguish adverse exits from voluntary runoff.",
        "Code meaning changes by pool construct and July 2026 reporting boundary.",
    ),
    (
        "actual_loss_rate",
        "Period-over-period increment in Actual Loss divided by beginning eligible UPB.",
        "Calculated only when both adjacent periods disclose the field.",
        "Realized loss or gain for applicable Actual Loss pools.",
        "Lower.",
        "July 2026 is the first disclosed period, so an incremental archive result is not yet available.",
        "deal_period_flow_metrics",
        "Monitor realized loss once two disclosed periods are present.",
        "Actual Loss can be negative and is unavailable for Fixed Severity pools.",
    ),
    (
        "new_modification_rate",
        "Active loans with Modification Flag Y divided by the active loan population.",
        "Official current-period modification event flag.",
        "Distress-intervention pressure.",
        "Lower, interpreted with cures.",
        "Established by the M8 full-data run.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Compare modification pressure with delinquency and cures.",
        "A modification is an intervention, not an adverse outcome by itself.",
    ),
    (
        "assistance_share",
        "Eligible UPB with borrower assistance or current/prior payment deferral divided by eligible UPB.",
        "Official assistance and deferral enumerations.",
        "Loss-mitigation exposure.",
        "Lower, interpreted with performance.",
        "Established by the M8 full-data run.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Understand whether observed performance includes active assistance.",
        "Program availability and reporting semantics vary over time.",
    ),
    (
        "pool_factor",
        "Reported Current Actual UPB divided by total UPB at Issuance for the period's pool rows.",
        "Decimal balance ratio.",
        "Remaining collateral balance.",
        "Context, usually declining.",
        "Established by the M8 full-data run.",
        "pool_period_metrics and higher aggregates",
        "Contextualize runoff and deal seasoning.",
        "Issuance rounding and removals affect interpretation.",
    ),
    (
        "weighted_average_risk_attributes",
        "Current-UPB-weighted valid Classic FICO, LTV, CLTV, DTI, coupon, and loan age.",
        "Field-specific sentinels are excluded and unknown UPB is reported.",
        "Risk-mix and comparability context.",
        "Context, metric-specific.",
        "Established by the M8 full-data run.",
        "pool_period_metrics, deal_period_metrics, portfolio_period_metrics",
        "Compare collateral composition without imputing unavailable values.",
        "Descriptive attributes are not predictions and updated scores are excluded.",
    ),
    (
        "risk_layer_share",
        "Eligible UPB grouped by 0-4 transparent conditions: FICO<680, LTV>90, DTI>45, and non-primary occupancy.",
        "Count of disclosed origination risk conditions; no composite weighting.",
        "Concentration of compounding origination risk.",
        "Lower high-layer share.",
        "Established by the M8 full-data run.",
        "deal_period_risk_layer_metrics",
        "Compare concentration while retaining each rule's meaning.",
        "Descriptive segmentation, not a borrower score, probability, or causal model.",
    ),
    (
        "loan_match_rate",
        "Prior-period records found under the same deal, pool, and loan key in the next adjacent period divided by prior records.",
        "Adjacent-period key reconciliation with approved-exit and error classes.",
        "Reliability of transition measures.",
        "Higher.",
        "Established by the M8 full-data run.",
        "deal_period_flow_metrics",
        "Decide whether transition metrics are sufficiently complete to use.",
        "A source revision or identifier change can break matching and must be investigated.",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def one(connection: duckdb.DuckDBPyConnection, query: str) -> object:
    return connection.execute(query).fetchone()[0]


def row_dict(connection: duckdb.DuckDBPyConnection, query: str) -> dict[str, object]:
    cursor = connection.execute(query)
    names = [item[0] for item in cursor.description]
    values = cursor.fetchone()
    return dict(zip(names, values, strict=True))


def build(
    foundation: Path,
    output: Path,
    evaluation_path: Path,
    release_aggregate: Path,
) -> dict[str, object]:
    started = time.perf_counter()
    foundation_manifest_path = foundation / "manifest.json"
    parquet_glob = foundation / "loan_period" / "**" / "*.parquet"
    if not foundation_manifest_path.is_file():
        raise ValueError(f"foundation manifest not found: {foundation_manifest_path}")
    if not release_aggregate.is_file():
        raise ValueError(f"release reconciliation input not found: {release_aggregate}")
    manifest = json.loads(foundation_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("data_classification") != "restricted-loan-level" or manifest.get("public_release_allowed") is not False:
        raise ValueError("foundation manifest does not declare the required restricted/public-exclusion boundary")
    expected_records = int(manifest["records"])
    output.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f"metric output already exists; M8 builder will not overwrite it: {output}")
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{output.stem}-building-", dir=output.parent))
    temporary_db = temporary_dir / output.name
    connection = duckdb.connect(str(temporary_db))
    try:
        connection.execute("SET preserve_insertion_order=false")
        connection.execute(
            f"""
            CREATE VIEW loan_period_typed AS
            WITH casted AS (
                SELECT
                    deal_id,
                    source_member,
                    source_field_count,
                    period AS reporting_period,
                    strptime(period, '%Y%m')::DATE AS period_date,
                    reference_pool_number,
                    loan_identifier,
                    try_cast(current_actual_upb AS DECIMAL(20,2)) AS current_upb,
                    try_cast(upb_at_issuance AS DECIMAL(20,2)) AS issuance_upb,
                    try_cast(upb_at_removal AS DECIMAL(20,2)) AS removal_upb,
                    CASE WHEN regexp_matches(current_loan_delinquency_status, '^[0-9]{{2}}$')
                        THEN try_cast(current_loan_delinquency_status AS INTEGER) END AS delinquency_months,
                    current_loan_delinquency_status AS delinquency_status_raw,
                    zero_balance_code,
                    modification_flag,
                    borrower_assistance_plan,
                    payment_deferral_flag,
                    delinquency_due_to_disaster,
                    distressed_principal_balance_flag,
                    try_cast(actual_loss AS DECIMAL(20,2)) AS actual_loss,
                    try_cast(cumulative_modification_costs AS DECIMAL(20,2)) AS cumulative_modification_costs,
                    CASE WHEN try_cast(classic_fico AS INTEGER) BETWEEN 300 AND 850
                        THEN try_cast(classic_fico AS INTEGER) END AS classic_fico_value,
                    CASE WHEN try_cast(original_ltv AS DECIMAL(10,4)) BETWEEN 1 AND 998
                              AND original_ltv <> '999'
                        THEN try_cast(original_ltv AS DECIMAL(10,4)) END AS original_ltv_value,
                    CASE WHEN try_cast(original_cltv AS DECIMAL(10,4)) BETWEEN 1 AND 998
                              AND original_cltv <> '999'
                        THEN try_cast(original_cltv AS DECIMAL(10,4)) END AS original_cltv_value,
                    CASE WHEN try_cast(original_dti AS DECIMAL(10,4)) BETWEEN 1 AND 65
                              AND original_dti <> '999'
                        THEN try_cast(original_dti AS DECIMAL(10,4)) END AS original_dti_value,
                    try_cast(current_interest_rate AS DECIMAL(10,5)) AS current_interest_rate_value,
                    try_cast(loan_age AS INTEGER) AS loan_age_value,
                    CASE WHEN regexp_matches(first_payment_date, '^[0-9]{{6}}$') THEN left(first_payment_date, 4) END AS origination_vintage,
                    loan_purpose,
                    channel,
                    occupancy_status,
                    property_type,
                    property_state,
                    seller_name,
                    servicer_name
                FROM read_parquet({sql_literal(parquet_glob)}, hive_partitioning=false)
            )
            SELECT
                *,
                CASE
                    WHEN delinquency_months = 0 THEN 'CURRENT'
                    WHEN delinquency_months = 1 THEN 'D30'
                    WHEN delinquency_months = 2 THEN 'D60'
                    WHEN delinquency_months >= 3 THEN 'D90_PLUS'
                    WHEN delinquency_status_raw = 'RA' THEN 'REO'
                    ELSE 'UNKNOWN'
                END AS performance_state,
                current_upb > 0 AND zero_balance_code IS NULL AND delinquency_months IS NOT NULL AS is_eligible_active,
                CASE
                    WHEN distressed_principal_balance_flag IN ('Y', 'N') THEN 'actual_loss'
                    WHEN distressed_principal_balance_flag = '9' THEN 'fixed_severity'
                    ELSE 'unknown'
                END AS pool_construct,
                CASE WHEN classic_fico_value IS NOT NULL AND original_ltv_value IS NOT NULL
                           AND original_dti_value IS NOT NULL AND occupancy_status IN ('P','S','I')
                    THEN (classic_fico_value < 680)::INTEGER
                       + (original_ltv_value > 90)::INTEGER
                       + (original_dti_value > 45)::INTEGER
                       + (occupancy_status IN ('S','I'))::INTEGER
                END AS risk_layer_count
            FROM casted
            """
        )
        actual_records = int(one(connection, "SELECT count(*) FROM loan_period_typed"))
        if actual_records != expected_records:
            raise ValueError(f"typed view has {actual_records:,} rows; foundation manifest expects {expected_records:,}")
        invalid_upb = int(one(connection, "SELECT count(*) FROM loan_period_typed WHERE current_upb IS NULL OR current_upb < 0"))
        invalid_status = int(
            one(
                connection,
                "SELECT count(*) FROM loan_period_typed WHERE delinquency_months IS NULL AND delinquency_status_raw NOT IN ('RA','XX')",
            )
        )
        unknown_construct = int(one(connection, "SELECT count(*) FROM loan_period_typed WHERE pool_construct='unknown'"))
        if invalid_upb or invalid_status or unknown_construct:
            raise ValueError(
                f"typed input gate failed: invalid_upb={invalid_upb}, invalid_status={invalid_status}, "
                f"unknown_pool_construct={unknown_construct}"
            )

        connection.execute(
            """
            CREATE TABLE pool_period_components AS
            SELECT
                deal_id,
                reference_pool_number,
                reporting_period,
                period_date,
                count(*)::BIGINT AS in_scope_records,
                sum(current_upb)::DECIMAL(24,2) AS reported_current_upb,
                count(*) FILTER (WHERE is_eligible_active)::BIGINT AS eligible_active_loans,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active), 0)::DECIMAL(24,2) AS eligible_current_upb,
                count(*) FILTER (WHERE delinquency_status_raw='RA')::BIGINT AS excluded_ra_records,
                coalesce(sum(current_upb) FILTER (WHERE delinquency_status_raw='RA'), 0)::DECIMAL(24,2) AS excluded_ra_upb,
                count(*) FILTER (WHERE delinquency_status_raw='XX')::BIGINT AS excluded_xx_records,
                coalesce(sum(current_upb) FILTER (WHERE delinquency_status_raw='XX'), 0)::DECIMAL(24,2) AS excluded_xx_upb,
                count(*) FILTER (WHERE zero_balance_code IS NOT NULL)::BIGINT AS zero_balance_records,
                count(*) FILTER (WHERE is_eligible_active AND delinquency_months>=1)::BIGINT AS d30_plus_loans,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND delinquency_months>=1), 0)::DECIMAL(24,2) AS d30_plus_upb,
                count(*) FILTER (WHERE is_eligible_active AND delinquency_months>=2)::BIGINT AS d60_plus_loans,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND delinquency_months>=2), 0)::DECIMAL(24,2) AS d60_plus_upb,
                count(*) FILTER (WHERE is_eligible_active AND delinquency_months>=3)::BIGINT AS d90_plus_loans,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND delinquency_months>=3), 0)::DECIMAL(24,2) AS d90_plus_upb,
                coalesce(sum(issuance_upb), 0)::DECIMAL(24,2) AS issuance_upb,
                coalesce(sum(current_upb * classic_fico_value) FILTER (WHERE is_eligible_active AND classic_fico_value IS NOT NULL), 0)::DECIMAL(30,4) AS fico_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND classic_fico_value IS NOT NULL), 0)::DECIMAL(24,2) AS fico_known_upb,
                coalesce(sum(current_upb * original_ltv_value) FILTER (WHERE is_eligible_active AND original_ltv_value IS NOT NULL), 0)::DECIMAL(30,4) AS ltv_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND original_ltv_value IS NOT NULL), 0)::DECIMAL(24,2) AS ltv_known_upb,
                coalesce(sum(current_upb * original_cltv_value) FILTER (WHERE is_eligible_active AND original_cltv_value IS NOT NULL), 0)::DECIMAL(30,4) AS cltv_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND original_cltv_value IS NOT NULL), 0)::DECIMAL(24,2) AS cltv_known_upb,
                coalesce(sum(current_upb * original_dti_value) FILTER (WHERE is_eligible_active AND original_dti_value IS NOT NULL), 0)::DECIMAL(30,4) AS dti_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND original_dti_value IS NOT NULL), 0)::DECIMAL(24,2) AS dti_known_upb,
                coalesce(sum(current_upb * current_interest_rate_value) FILTER (WHERE is_eligible_active AND current_interest_rate_value IS NOT NULL), 0)::DECIMAL(30,4) AS coupon_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND current_interest_rate_value IS NOT NULL), 0)::DECIMAL(24,2) AS coupon_known_upb,
                coalesce(sum(current_upb * loan_age_value) FILTER (WHERE is_eligible_active AND loan_age_value IS NOT NULL), 0)::DECIMAL(30,4) AS loan_age_weighted_sum,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND loan_age_value IS NOT NULL), 0)::DECIMAL(24,2) AS loan_age_known_upb,
                count(*) FILTER (WHERE is_eligible_active AND modification_flag='Y')::BIGINT AS new_modification_loans,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND modification_flag='Y'), 0)::DECIMAL(24,2) AS new_modification_upb,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND modification_flag IN ('Y','P')), 0)::DECIMAL(24,2) AS modified_upb,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND payment_deferral_flag IN ('C','P')), 0)::DECIMAL(24,2) AS payment_deferral_upb,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND borrower_assistance_plan IN ('F','R','T')), 0)::DECIMAL(24,2) AS borrower_assistance_upb,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND (
                    payment_deferral_flag IN ('C','P') OR borrower_assistance_plan IN ('F','R','T')
                )), 0)::DECIMAL(24,2) AS assistance_exposure_upb,
                coalesce(sum(current_upb) FILTER (WHERE is_eligible_active AND delinquency_due_to_disaster='Y'), 0)::DECIMAL(24,2) AS disaster_upb,
                coalesce(sum(actual_loss), 0)::DECIMAL(24,2) AS cumulative_actual_loss,
                count(actual_loss)::BIGINT AS actual_loss_observations
            FROM loan_period_typed
            GROUP BY ALL
            """
        )

        derived_columns = f"""
            *,
            eligible_current_upb / nullif(eligible_active_loans, 0) AS average_active_loan_upb,
            d30_plus_upb / nullif(eligible_current_upb, 0) AS d30_plus_rate,
            d60_plus_upb / nullif(eligible_current_upb, 0) AS d60_plus_rate,
            d90_plus_upb / nullif(eligible_current_upb, 0) AS d90_plus_rate,
            d30_plus_upb / nullif(reported_current_upb, 0) AS release_compatible_d30_plus_rate,
            d60_plus_upb / nullif(reported_current_upb, 0) AS release_compatible_d60_plus_rate,
            reported_current_upb / nullif(issuance_upb, 0) AS pool_factor,
            fico_weighted_sum / nullif(fico_known_upb, 0) AS wa_classic_fico,
            ltv_weighted_sum / nullif(ltv_known_upb, 0) AS wa_original_ltv,
            cltv_weighted_sum / nullif(cltv_known_upb, 0) AS wa_original_cltv,
            dti_weighted_sum / nullif(dti_known_upb, 0) AS wa_original_dti,
            coupon_weighted_sum / nullif(coupon_known_upb, 0) AS wa_current_coupon,
            loan_age_weighted_sum / nullif(loan_age_known_upb, 0) AS wa_loan_age,
            new_modification_loans::DOUBLE / nullif(eligible_active_loans, 0) AS new_modification_rate_count,
            new_modification_upb / nullif(eligible_current_upb, 0) AS new_modification_rate_upb,
            modified_upb / nullif(eligible_current_upb, 0) AS modified_share,
            payment_deferral_upb / nullif(eligible_current_upb, 0) AS payment_deferral_share,
            borrower_assistance_upb / nullif(eligible_current_upb, 0) AS borrower_assistance_share,
            assistance_exposure_upb / nullif(eligible_current_upb, 0) AS assistance_exposure_share,
            disaster_upb / nullif(eligible_current_upb, 0) AS disaster_share,
            '{METRIC_VERSION}'::VARCHAR AS metric_version
        """
        connection.execute(
            f"""
            CREATE TABLE pool_period_metrics AS
            WITH levels AS (SELECT {derived_columns} FROM pool_period_components),
            changed AS (
                SELECT *,
                    (d60_plus_rate - lag(d60_plus_rate) OVER (PARTITION BY deal_id, reference_pool_number ORDER BY period_date)) * 10000 AS d60_change_1m_bps,
                    (d60_plus_rate - lag(d60_plus_rate, 3) OVER (PARTITION BY deal_id, reference_pool_number ORDER BY period_date)) * 10000 AS d60_change_3m_bps
                FROM levels
            )
            SELECT * FROM changed
            """
        )

        connection.execute(
            """
            CREATE TABLE deal_period_components AS
            SELECT
                deal_id, reporting_period, period_date,
                sum(in_scope_records)::BIGINT AS in_scope_records,
                sum(reported_current_upb)::DECIMAL(24,2) AS reported_current_upb,
                sum(eligible_active_loans)::BIGINT AS eligible_active_loans,
                sum(eligible_current_upb)::DECIMAL(24,2) AS eligible_current_upb,
                sum(excluded_ra_records)::BIGINT AS excluded_ra_records,
                sum(excluded_ra_upb)::DECIMAL(24,2) AS excluded_ra_upb,
                sum(excluded_xx_records)::BIGINT AS excluded_xx_records,
                sum(excluded_xx_upb)::DECIMAL(24,2) AS excluded_xx_upb,
                sum(zero_balance_records)::BIGINT AS zero_balance_records,
                sum(d30_plus_loans)::BIGINT AS d30_plus_loans,
                sum(d30_plus_upb)::DECIMAL(24,2) AS d30_plus_upb,
                sum(d60_plus_loans)::BIGINT AS d60_plus_loans,
                sum(d60_plus_upb)::DECIMAL(24,2) AS d60_plus_upb,
                sum(d90_plus_loans)::BIGINT AS d90_plus_loans,
                sum(d90_plus_upb)::DECIMAL(24,2) AS d90_plus_upb,
                sum(issuance_upb)::DECIMAL(24,2) AS issuance_upb,
                sum(fico_weighted_sum)::DECIMAL(30,4) AS fico_weighted_sum,
                sum(fico_known_upb)::DECIMAL(24,2) AS fico_known_upb,
                sum(ltv_weighted_sum)::DECIMAL(30,4) AS ltv_weighted_sum,
                sum(ltv_known_upb)::DECIMAL(24,2) AS ltv_known_upb,
                sum(cltv_weighted_sum)::DECIMAL(30,4) AS cltv_weighted_sum,
                sum(cltv_known_upb)::DECIMAL(24,2) AS cltv_known_upb,
                sum(dti_weighted_sum)::DECIMAL(30,4) AS dti_weighted_sum,
                sum(dti_known_upb)::DECIMAL(24,2) AS dti_known_upb,
                sum(coupon_weighted_sum)::DECIMAL(30,4) AS coupon_weighted_sum,
                sum(coupon_known_upb)::DECIMAL(24,2) AS coupon_known_upb,
                sum(loan_age_weighted_sum)::DECIMAL(30,4) AS loan_age_weighted_sum,
                sum(loan_age_known_upb)::DECIMAL(24,2) AS loan_age_known_upb,
                sum(new_modification_loans)::BIGINT AS new_modification_loans,
                sum(new_modification_upb)::DECIMAL(24,2) AS new_modification_upb,
                sum(modified_upb)::DECIMAL(24,2) AS modified_upb,
                sum(payment_deferral_upb)::DECIMAL(24,2) AS payment_deferral_upb,
                sum(borrower_assistance_upb)::DECIMAL(24,2) AS borrower_assistance_upb,
                sum(assistance_exposure_upb)::DECIMAL(24,2) AS assistance_exposure_upb,
                sum(disaster_upb)::DECIMAL(24,2) AS disaster_upb,
                sum(cumulative_actual_loss)::DECIMAL(24,2) AS cumulative_actual_loss,
                sum(actual_loss_observations)::BIGINT AS actual_loss_observations
            FROM pool_period_components GROUP BY ALL
            """
        )
        connection.execute(
            f"""
            CREATE TABLE deal_period_metrics AS
            WITH levels AS (SELECT {derived_columns} FROM deal_period_components),
            changed AS (
                SELECT *,
                    (d60_plus_rate - lag(d60_plus_rate) OVER (PARTITION BY deal_id ORDER BY period_date)) * 10000 AS d60_change_1m_bps,
                    (d60_plus_rate - lag(d60_plus_rate, 3) OVER (PARTITION BY deal_id ORDER BY period_date)) * 10000 AS d60_change_3m_bps
                FROM levels
            ) SELECT * FROM changed
            """
        )
        connection.execute(
            """
            CREATE TABLE portfolio_period_components AS
            SELECT
                reporting_period, period_date,
                sum(in_scope_records)::BIGINT AS in_scope_records,
                sum(reported_current_upb)::DECIMAL(24,2) AS reported_current_upb,
                sum(eligible_active_loans)::BIGINT AS eligible_active_loans,
                sum(eligible_current_upb)::DECIMAL(24,2) AS eligible_current_upb,
                sum(excluded_ra_records)::BIGINT AS excluded_ra_records,
                sum(excluded_ra_upb)::DECIMAL(24,2) AS excluded_ra_upb,
                sum(excluded_xx_records)::BIGINT AS excluded_xx_records,
                sum(excluded_xx_upb)::DECIMAL(24,2) AS excluded_xx_upb,
                sum(zero_balance_records)::BIGINT AS zero_balance_records,
                sum(d30_plus_loans)::BIGINT AS d30_plus_loans,
                sum(d30_plus_upb)::DECIMAL(24,2) AS d30_plus_upb,
                sum(d60_plus_loans)::BIGINT AS d60_plus_loans,
                sum(d60_plus_upb)::DECIMAL(24,2) AS d60_plus_upb,
                sum(d90_plus_loans)::BIGINT AS d90_plus_loans,
                sum(d90_plus_upb)::DECIMAL(24,2) AS d90_plus_upb,
                sum(issuance_upb)::DECIMAL(24,2) AS issuance_upb,
                sum(fico_weighted_sum)::DECIMAL(30,4) AS fico_weighted_sum,
                sum(fico_known_upb)::DECIMAL(24,2) AS fico_known_upb,
                sum(ltv_weighted_sum)::DECIMAL(30,4) AS ltv_weighted_sum,
                sum(ltv_known_upb)::DECIMAL(24,2) AS ltv_known_upb,
                sum(cltv_weighted_sum)::DECIMAL(30,4) AS cltv_weighted_sum,
                sum(cltv_known_upb)::DECIMAL(24,2) AS cltv_known_upb,
                sum(dti_weighted_sum)::DECIMAL(30,4) AS dti_weighted_sum,
                sum(dti_known_upb)::DECIMAL(24,2) AS dti_known_upb,
                sum(coupon_weighted_sum)::DECIMAL(30,4) AS coupon_weighted_sum,
                sum(coupon_known_upb)::DECIMAL(24,2) AS coupon_known_upb,
                sum(loan_age_weighted_sum)::DECIMAL(30,4) AS loan_age_weighted_sum,
                sum(loan_age_known_upb)::DECIMAL(24,2) AS loan_age_known_upb,
                sum(new_modification_loans)::BIGINT AS new_modification_loans,
                sum(new_modification_upb)::DECIMAL(24,2) AS new_modification_upb,
                sum(modified_upb)::DECIMAL(24,2) AS modified_upb,
                sum(payment_deferral_upb)::DECIMAL(24,2) AS payment_deferral_upb,
                sum(borrower_assistance_upb)::DECIMAL(24,2) AS borrower_assistance_upb,
                sum(assistance_exposure_upb)::DECIMAL(24,2) AS assistance_exposure_upb,
                sum(disaster_upb)::DECIMAL(24,2) AS disaster_upb,
                sum(cumulative_actual_loss)::DECIMAL(24,2) AS cumulative_actual_loss,
                sum(actual_loss_observations)::BIGINT AS actual_loss_observations
            FROM deal_period_components GROUP BY ALL
            """
        )
        connection.execute(
            f"""
            CREATE TABLE portfolio_period_metrics AS
            WITH levels AS (SELECT {derived_columns} FROM portfolio_period_components),
            changed AS (
                SELECT *,
                    (d60_plus_rate - lag(d60_plus_rate) OVER (ORDER BY period_date)) * 10000 AS d60_change_1m_bps,
                    (d60_plus_rate - lag(d60_plus_rate, 3) OVER (ORDER BY period_date)) * 10000 AS d60_change_3m_bps
                FROM levels
            ) SELECT * FROM changed
            """
        )

        connection.execute(
            f"""
            CREATE TABLE deal_period_flow_metrics AS
            WITH period_sequence AS (
                SELECT deal_id, period_date AS current_date,
                       lag(period_date) OVER (PARTITION BY deal_id ORDER BY period_date) AS prior_date
                FROM (SELECT DISTINCT deal_id, period_date FROM loan_period_typed)
            ),
            period_pairs AS (
                SELECT * FROM period_sequence
                WHERE prior_date IS NOT NULL AND date_diff('month', prior_date, current_date)=1
            ),
            pairs AS (
                SELECT
                    pp.deal_id,
                    strftime(pp.current_date, '%Y%m') AS reporting_period,
                    pp.current_date AS period_date,
                    p.reference_pool_number,
                    p.loan_identifier,
                    p.current_upb AS prior_upb,
                    p.delinquency_months AS prior_delinquency_months,
                    p.zero_balance_code AS prior_zero_balance_code,
                    p.actual_loss AS prior_actual_loss,
                    c.loan_identifier IS NOT NULL AS is_matched,
                    c.current_upb,
                    c.delinquency_months,
                    c.zero_balance_code,
                    c.removal_upb,
                    c.modification_flag,
                    c.payment_deferral_flag,
                    c.actual_loss,
                    c.pool_construct
                FROM period_pairs pp
                JOIN loan_period_typed p ON p.deal_id=pp.deal_id AND p.period_date=pp.prior_date
                LEFT JOIN loan_period_typed c ON c.deal_id=p.deal_id
                    AND c.reference_pool_number=p.reference_pool_number
                    AND c.loan_identifier=p.loan_identifier
                    AND c.period_date=pp.current_date
            ),
            new_records AS (
                SELECT pp.deal_id, strftime(pp.current_date, '%Y%m') AS reporting_period,
                       count(*) FILTER (WHERE p.loan_identifier IS NULL)::BIGINT AS new_records
                FROM period_pairs pp
                JOIN loan_period_typed c ON c.deal_id=pp.deal_id AND c.period_date=pp.current_date
                LEFT JOIN loan_period_typed p ON p.deal_id=c.deal_id
                    AND p.reference_pool_number=c.reference_pool_number
                    AND p.loan_identifier=c.loan_identifier
                    AND p.period_date=pp.prior_date
                GROUP BY ALL
            ),
            aggregated AS (
                SELECT
                    deal_id, reporting_period, period_date,
                    count(*)::BIGINT AS prior_records,
                    count(*) FILTER (WHERE is_matched)::BIGINT AS matched_records,
                    count(*) FILTER (WHERE NOT is_matched AND prior_zero_balance_code IS NOT NULL)::BIGINT AS approved_exit_records,
                    0::BIGINT AS revision_exception_records,
                    count(*) FILTER (WHERE NOT is_matched AND prior_zero_balance_code IS NULL)::BIGINT AS error_unmatched_records,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched), 0)::DECIMAL(24,2) AS matched_prior_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=0)::BIGINT AS prior_current_matched_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=0), 0)::DECIMAL(24,2) AS prior_current_matched_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=0 AND delinquency_months>=1)::BIGINT AS current_to_d30_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=0 AND delinquency_months>=1), 0)::DECIMAL(24,2) AS current_to_d30_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=1)::BIGINT AS prior_d30_matched_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=1), 0)::DECIMAL(24,2) AS prior_d30_matched_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=1 AND delinquency_months>=2)::BIGINT AS d30_to_d60_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months=1 AND delinquency_months>=2), 0)::DECIMAL(24,2) AS d30_to_d60_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months>=1)::BIGINT AS prior_d30_plus_matched_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months>=1), 0)::DECIMAL(24,2) AS prior_d30_plus_matched_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months>=1 AND delinquency_months=0)::BIGINT AS cured_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months>=1 AND delinquency_months=0), 0)::DECIMAL(24,2) AS cured_upb,
                    count(*) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months IS NOT NULL)::BIGINT AS beginning_eligible_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_upb>0 AND prior_delinquency_months IS NOT NULL), 0)::DECIMAL(24,2) AS beginning_eligible_upb,
                    count(*) FILTER (WHERE is_matched AND prior_zero_balance_code IS NULL AND zero_balance_code='01')::BIGINT AS voluntary_payoff_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_zero_balance_code IS NULL AND zero_balance_code='01'), 0)::DECIMAL(24,2) AS voluntary_payoff_upb,
                    count(*) FILTER (WHERE is_matched AND prior_zero_balance_code IS NULL AND (
                        (pool_construct='actual_loss' AND reporting_period<'202607' AND zero_balance_code IN ('03','09')) OR
                        (pool_construct='actual_loss' AND reporting_period>='202607' AND zero_balance_code IN ('02','03','09','15')) OR
                        (pool_construct='fixed_severity' AND zero_balance_code IN ('02','03','04','08','97'))
                    ))::BIGINT AS credit_event_exit_loans,
                    coalesce(sum(prior_upb) FILTER (WHERE is_matched AND prior_zero_balance_code IS NULL AND (
                        (pool_construct='actual_loss' AND reporting_period<'202607' AND zero_balance_code IN ('03','09')) OR
                        (pool_construct='actual_loss' AND reporting_period>='202607' AND zero_balance_code IN ('02','03','09','15')) OR
                        (pool_construct='fixed_severity' AND zero_balance_code IN ('02','03','04','08','97'))
                    )), 0)::DECIMAL(24,2) AS credit_event_exit_upb,
                    count(*) FILTER (WHERE is_matched AND modification_flag='Y')::BIGINT AS new_modification_loans,
                    count(*) FILTER (WHERE is_matched AND payment_deferral_flag='C')::BIGINT AS new_payment_deferral_loans,
                    count(*) FILTER (WHERE is_matched AND actual_loss IS NOT NULL AND prior_actual_loss IS NOT NULL)::BIGINT AS actual_loss_increment_observations,
                    sum(actual_loss-prior_actual_loss) FILTER (WHERE is_matched AND actual_loss IS NOT NULL AND prior_actual_loss IS NOT NULL)::DECIMAL(24,2) AS actual_loss_increment
                FROM pairs GROUP BY ALL
            )
            SELECT
                a.*, n.new_records,
                matched_records::DOUBLE/nullif(prior_records,0) AS loan_match_rate,
                current_to_d30_loans::DOUBLE/nullif(prior_current_matched_loans,0) AS current_to_d30_rate_count,
                current_to_d30_upb/nullif(prior_current_matched_upb,0) AS current_to_d30_rate_upb,
                d30_to_d60_loans::DOUBLE/nullif(prior_d30_matched_loans,0) AS d30_to_d60_rate_count,
                d30_to_d60_upb/nullif(prior_d30_matched_upb,0) AS d30_to_d60_rate_upb,
                cured_loans::DOUBLE/nullif(prior_d30_plus_matched_loans,0) AS cure_rate_count,
                cured_upb/nullif(prior_d30_plus_matched_upb,0) AS cure_rate_upb,
                voluntary_payoff_loans::DOUBLE/nullif(beginning_eligible_loans,0) AS voluntary_payoff_rate_count,
                voluntary_payoff_upb/nullif(beginning_eligible_upb,0) AS voluntary_payoff_rate_upb,
                credit_event_exit_loans::DOUBLE/nullif(beginning_eligible_loans,0) AS credit_event_exit_rate_count,
                credit_event_exit_upb/nullif(beginning_eligible_upb,0) AS credit_event_exit_rate_upb,
                actual_loss_increment/nullif(beginning_eligible_upb,0) AS actual_loss_rate,
                '{METRIC_VERSION}'::VARCHAR AS metric_version
            FROM aggregated a JOIN new_records n USING (deal_id, reporting_period)
            """
        )

        connection.execute(
            f"""
            CREATE TABLE deal_period_risk_layer_metrics AS
            WITH grouped AS (
                SELECT deal_id, reporting_period, period_date, risk_layer_count,
                    count(*)::BIGINT AS eligible_loans,
                    sum(current_upb)::DECIMAL(24,2) AS eligible_current_upb
                FROM loan_period_typed
                WHERE is_eligible_active AND risk_layer_count IS NOT NULL
                GROUP BY ALL
            )
            SELECT *,
                eligible_loans::DOUBLE/sum(eligible_loans) OVER (PARTITION BY deal_id, reporting_period) AS loan_share,
                eligible_current_upb/sum(eligible_current_upb) OVER (PARTITION BY deal_id, reporting_period) AS upb_share,
                '{METRIC_VERSION}'::VARCHAR AS metric_version
            FROM grouped
            """
        )

        connection.execute(
            f"""
            CREATE TABLE portfolio_d60_decomposition AS
            WITH period_sequence AS (
                SELECT reporting_period, period_date,
                       lag(reporting_period) OVER (ORDER BY period_date) AS prior_reporting_period
                FROM portfolio_period_metrics
            ),
            period_pairs AS (
                SELECT * FROM period_sequence WHERE prior_reporting_period IS NOT NULL
            ),
            cohort_keys AS (
                SELECT pp.reporting_period, pp.prior_reporting_period, d.deal_id
                FROM period_pairs pp
                CROSS JOIN (SELECT DISTINCT deal_id FROM deal_period_metrics) d
                WHERE EXISTS (SELECT 1 FROM deal_period_metrics x WHERE x.deal_id=d.deal_id AND x.reporting_period IN (pp.reporting_period, pp.prior_reporting_period))
            ),
            values_joined AS (
                SELECT k.*,
                    coalesce(c.eligible_current_upb,0)::DOUBLE AS current_upb,
                    coalesce(p.eligible_current_upb,0)::DOUBLE AS prior_upb,
                    c.d60_plus_rate AS current_rate_raw,
                    p.d60_plus_rate AS prior_rate_raw,
                    cp.eligible_current_upb::DOUBLE AS current_portfolio_upb,
                    pp.eligible_current_upb::DOUBLE AS prior_portfolio_upb
                FROM cohort_keys k
                LEFT JOIN deal_period_metrics c ON c.deal_id=k.deal_id AND c.reporting_period=k.reporting_period
                LEFT JOIN deal_period_metrics p ON p.deal_id=k.deal_id AND p.reporting_period=k.prior_reporting_period
                JOIN portfolio_period_metrics cp ON cp.reporting_period=k.reporting_period
                JOIN portfolio_period_metrics pp ON pp.reporting_period=k.prior_reporting_period
            ),
            prepared AS (
                SELECT *,
                    current_upb/nullif(current_portfolio_upb,0) AS current_weight,
                    prior_upb/nullif(prior_portfolio_upb,0) AS prior_weight,
                    coalesce(current_rate_raw, prior_rate_raw, 0) AS current_rate,
                    coalesce(prior_rate_raw, current_rate_raw, 0) AS prior_rate
                FROM values_joined
            )
            SELECT
                reporting_period, prior_reporting_period, deal_id,
                current_upb, prior_upb, current_weight, prior_weight, current_rate, prior_rate,
                0.5*(current_weight+prior_weight)*(current_rate-prior_rate)*10000 AS rate_effect_bps,
                0.5*(current_rate+prior_rate)*(current_weight-prior_weight)*10000 AS mix_effect_bps,
                (current_weight*current_rate-prior_weight*prior_rate)*10000 AS total_contribution_bps,
                '{METRIC_VERSION}'::VARCHAR AS metric_version
            FROM prepared
            """
        )

        connection.execute(
            """
            CREATE TABLE metric_catalog (
                metric_id VARCHAR PRIMARY KEY, metric_version VARCHAR, definition VARCHAR, method VARCHAR,
                business_meaning VARCHAR, desired_direction VARCHAR, baseline VARCHAR, result_location VARCHAR,
                supported_decision VARCHAR, limitation VARCHAR
            )
            """
        )
        connection.executemany(
            "INSERT INTO metric_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(metric_id, METRIC_VERSION, *rest) for metric_id, *rest in METRIC_CATALOG],
        )

        connection.execute(
            f"""
            CREATE TABLE release_reference AS
            SELECT * FROM read_csv({sql_literal(release_aggregate)}, header=true, auto_detect=true)
            """
        )
        connection.execute(
            f"""
            CREATE TABLE release_reconciliation AS
            SELECT
                coalesce(m.reporting_period, r.reporting_period::VARCHAR) AS reporting_period,
                coalesce(m.deal_id, r.deal_id) AS deal_id,
                coalesce(m.reference_pool_number, r.reference_pool_number) AS reference_pool_number,
                round(m.reported_current_upb,2)-round(r.current_upb,2) AS current_upb_variance,
                round(m.d30_plus_upb,2)-round(r.d30_plus_upb,2) AS d30_plus_upb_variance,
                round(m.d60_plus_upb,2)-round(r.d60_plus_upb,2) AS d60_plus_upb_variance,
                round(m.release_compatible_d30_plus_rate,8)-round(r.d30_plus_rate,8) AS d30_plus_rate_variance,
                round(m.release_compatible_d60_plus_rate,8)-round(r.d60_plus_rate,8) AS d60_plus_rate_variance,
                m.in_scope_records-r.records_aggregated AS record_variance,
                m.reporting_period IS NULL OR r.reporting_period IS NULL AS missing_group,
                '{METRIC_VERSION}'::VARCHAR AS metric_version
            FROM pool_period_metrics m
            FULL OUTER JOIN release_reference r
              ON m.reporting_period=r.reporting_period::VARCHAR
             AND m.deal_id=r.deal_id
             AND m.reference_pool_number=r.reference_pool_number
            """
        )

        reconciliation = row_dict(
            connection,
            """
            SELECT count(*) AS groups,
                   max(abs(current_upb_variance)) AS max_current_upb_variance,
                   max(abs(d30_plus_upb_variance)) AS max_d30_plus_upb_variance,
                   max(abs(d60_plus_upb_variance)) AS max_d60_plus_upb_variance,
                   max(abs(d30_plus_rate_variance)) AS max_d30_plus_rate_variance,
                   max(abs(d60_plus_rate_variance)) AS max_d60_plus_rate_variance,
                   max(abs(record_variance)) AS max_record_variance,
                   count(*) FILTER (WHERE missing_group) AS missing_groups
            FROM release_reconciliation
            """,
        )
        if (
            reconciliation["groups"] != int(manifest["accepted_files"])
            or reconciliation["missing_groups"]
            or any(
                reconciliation[key] != 0
                for key in (
                    "max_current_upb_variance",
                    "max_d30_plus_upb_variance",
                    "max_d60_plus_upb_variance",
                    "max_d30_plus_rate_variance",
                    "max_d60_plus_rate_variance",
                    "max_record_variance",
                )
            )
        ):
            raise ValueError(f"release reconciliation failed: {reconciliation}")

        transition_audit = row_dict(
            connection,
            """
            SELECT sum(prior_records) AS prior_records,
                   sum(matched_records) AS matched_records,
                   sum(approved_exit_records) AS approved_exit_records,
                   sum(revision_exception_records) AS revision_exception_records,
                   sum(error_unmatched_records) AS error_unmatched_records,
                   sum(new_records) AS new_records,
                   min(loan_match_rate) AS minimum_deal_period_match_rate
            FROM deal_period_flow_metrics
            """,
        )
        if transition_audit["error_unmatched_records"]:
            raise ValueError(f"transition integrity failed: {transition_audit}")

        decomposition_audit = row_dict(
            connection,
            """
            WITH effects AS (
                SELECT reporting_period, sum(rate_effect_bps+mix_effect_bps) AS decomposed_change_bps
                FROM portfolio_d60_decomposition GROUP BY 1
            )
            SELECT max(abs(e.decomposed_change_bps-p.d60_change_1m_bps)) AS maximum_variance_bps
            FROM effects e JOIN portfolio_period_metrics p USING (reporting_period)
            """,
        )
        if decomposition_audit["maximum_variance_bps"] is None or float(decomposition_audit["maximum_variance_bps"]) > 0.01:
            raise ValueError(f"D60 decomposition failed: {decomposition_audit}")

        latest = row_dict(
            connection,
            """
            SELECT reporting_period, reported_current_upb, eligible_current_upb, excluded_ra_upb,
                   d30_plus_upb, d60_plus_upb, d90_plus_upb,
                   d30_plus_rate, d60_plus_rate, d90_plus_rate,
                   release_compatible_d30_plus_rate, release_compatible_d60_plus_rate,
                   d60_change_1m_bps, d60_change_3m_bps,
                   wa_classic_fico, wa_original_ltv, wa_original_cltv, wa_original_dti,
                   new_modification_rate_count, assistance_exposure_share,
                   cumulative_actual_loss, actual_loss_observations
            FROM portfolio_period_metrics ORDER BY period_date DESC LIMIT 1
            """,
        )
        latest_flow = row_dict(
            connection,
            """
            SELECT reporting_period,
                   sum(current_to_d30_loans)::BIGINT AS current_to_d30_loans,
                   sum(d30_to_d60_loans)::BIGINT AS d30_to_d60_loans,
                   sum(cured_loans)::BIGINT AS cured_loans,
                   sum(voluntary_payoff_loans)::BIGINT AS voluntary_payoff_loans,
                   sum(credit_event_exit_loans)::BIGINT AS credit_event_exit_loans,
                   sum(new_modification_loans)::BIGINT AS new_modification_loans,
                   sum(actual_loss_increment_observations)::BIGINT AS actual_loss_increment_observations,
                   sum(actual_loss_increment)::DECIMAL(24,2) AS actual_loss_increment
            FROM deal_period_flow_metrics
            GROUP BY reporting_period ORDER BY reporting_period DESC LIMIT 1
            """,
        )
        table_counts = {
            table: int(one(connection, f"SELECT count(*) FROM {table}"))
            for table in (
                "pool_period_metrics",
                "deal_period_metrics",
                "portfolio_period_metrics",
                "deal_period_flow_metrics",
                "deal_period_risk_layer_metrics",
                "portfolio_d60_decomposition",
                "metric_catalog",
                "release_reconciliation",
            )
        }
        query_started = time.perf_counter()
        connection.execute(
            "SELECT deal_id, d60_plus_rate, d60_change_1m_bps FROM deal_period_metrics WHERE reporting_period=(SELECT max(reporting_period) FROM deal_period_metrics) ORDER BY d60_change_1m_bps DESC"
        ).fetchall()
        common_query_ms = round((time.perf_counter() - query_started) * 1000, 3)
        connection.execute("CHECKPOINT")
    except Exception:
        connection.close()
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise
    else:
        connection.close()
        temporary_db.replace(output)
        temporary_dir.rmdir()

    evaluation = {
        "report_version": 1,
        "build_date": date.today().isoformat(),
        "metric_version": METRIC_VERSION,
        "official_glossary": GLOSSARY,
        "source_archive_sha256": manifest["source_archive_sha256"],
        "foundation_manifest_sha256": sha256(foundation_manifest_path),
        "source_records": actual_records,
        "typed_input_gate": {
            "status": "pass",
            "invalid_current_upb_records": invalid_upb,
            "invalid_delinquency_status_records": invalid_status,
            "unknown_pool_construct_records": unknown_construct,
        },
        "release_reconciliation": {"status": "pass", **reconciliation},
        "transition_integrity": {"status": "pass", **transition_audit},
        "decomposition_integrity": {"status": "pass", **decomposition_audit},
        "latest_portfolio_result": latest,
        "latest_flow_result": latest_flow,
        "table_rows": table_counts,
        "actual_loss_availability": {
            "status": "insufficient-adjacent-disclosed-periods" if not latest_flow["actual_loss_increment_observations"] else "available",
            "reason": "July 2026 is the first archive period containing Actual Loss; the metric requires two adjacent disclosed periods.",
        },
        "performance": {
            "full_refresh_ms": round((time.perf_counter() - started) * 1000, 3),
            "common_latest_watchlist_query_ms": common_query_ms,
        },
        "restricted_output": {
            "database": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
            "database_bytes": output.stat().st_size,
            "database_sha256": sha256(output),
            "data_classification": "restricted-derived-analytics",
            "public_release_allowed": False,
        },
    }
    evaluation_path.write_text(json.dumps(evaluation, indent=2, default=str) + "\n", encoding="utf-8")
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation", type=Path, default=DEFAULT_FOUNDATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--release-aggregate", type=Path, default=DEFAULT_RELEASE_AGGREGATE)
    parser.add_argument("--allow-nonrestricted-output", action="store_true", help="Tests only")
    args = parser.parse_args()
    foundation = args.foundation.resolve()
    output = args.output.resolve()
    evaluation_path = args.evaluation.resolve()
    release_aggregate = args.release_aggregate.resolve()
    if not args.allow_nonrestricted_output and not output.is_relative_to(RESTRICTED.resolve()):
        raise SystemExit(f"metric output must remain under {RESTRICTED}")
    try:
        evaluation = build(foundation, output, evaluation_path, release_aggregate)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(
        f"Built {METRIC_VERSION} from {evaluation['source_records']:,} full-data rows in "
        f"{evaluation['performance']['full_refresh_ms']:,.3f} ms: {output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
