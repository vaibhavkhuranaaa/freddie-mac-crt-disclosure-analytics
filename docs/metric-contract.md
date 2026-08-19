# Metric contract

## Approved full-data metric system

M6 approved a private full-data collateral-surveillance metric engine and an aggregate-only public twin. M7 verified the controlled physical foundation; M8 verifies metric version `m8.1.0` over all 20,439,666 loan-period rows. Decision 0012 now publishes the complete masked record register while retaining the same metric definitions. The anchor is UPB-weighted D60+; the primary decision metric is month-over-month D60+ change decomposed exactly into deal rate effect and portfolio mix effect. Exposure, D30/D60/D90, changes, transitions, cures, exits, modifications, losses, risk mix, and evidence measures are defined in `docs/metric-glossary.md`.

The M8 engine and raw physical foundation remain local. Derived summaries and the separately masked record register are eligible for the public release after the new release gates pass.

## M8 implementation contract

- `loan_period_typed` performs field-specific casting without changing the source-faithful Parquet layer.
- Analytical delinquency denominators include positive-balance, non-removed loans with numeric status and exclude `RA`/`XX`; excluded counts and UPB remain visible.
- Release-compatible rates use the prior denominator solely to prove exact reconciliation across all 292 existing groups.
- Adjacent-period flows use stable deal/reference-pool/loan keys and classify every prior row before calculating roll or cure rates.
- HQA exit metrics use the official Actual Loss code map and the July 2026 code boundary.
- The midpoint deal decomposition must reconcile to the portfolio D60+ change within 0.01 bp.
- Every derived table and catalog record carries `m8.1.0`; the database remains under `data/restricted/` and is not publishable.

## M9 presentation contract

- The private workbench reads materialized M8 tables and `loan_period_typed`; it does not recalculate or override governed formulas in browser code.
- Watchlist order uses one named metric selected by the reviewer. No composite score or hidden weighting is permitted.
- Multi-period charts key observations to one selected deal and the portfolio; unrelated deal-period observations are never joined as one line.
- Level, change, affected balance, comparison basis, rate effect, mix effect, and evidence state remain visible together.
- The evidence rail reads the M8 metric catalog and shows definition, method, decision, direction, baseline, and limitation.
- Loan rows remain restricted. Identifiers are masked by default, and evidence exports exclude all loan rows and identifiers.
- Actual Loss rate displays unavailable until the engine records two adjacent applicable disclosed periods.

## Derived summary measures

| Metric | Formula | Validation |
| --- | --- | --- |
| D30+ delinquency rate | `sum(d30_plus_upb) / sum(current_upb)` | Current UPB non-negative; delinquent UPB cannot exceed current UPB within an aggregate group |
| D60+ delinquency rate | `sum(d60_plus_upb) / sum(current_upb)` | D60+ UPB cannot exceed D30+ UPB or current UPB within an aggregate group |
| Current pool UPB | `sum(current_upb)` | Aggregate-only sum by deal/reporting period/reference pool |
| RA / XX counts | Count of non-numeric statuses excluded from D30+/D60+ measures | Explicitly surfaced in the intake manifest/evaluation |

The summary layer uses these reference-pool performance measures for navigation. The record register exposes source disclosure fields but does not calculate tranche thickness, waterfall loss allocation, or investor cash flow.

## Historical synthetic baseline measures

| Metric | Formula | Validation |
| --- | --- | --- |
| Delinquency rate | `delinquent_upb / reference_pool_upb` | Both values non-negative; numerator no greater than pool UPB |
| Prepayment rate | `prepayment_upb / reference_pool_upb` | Both values non-negative; numerator no greater than pool UPB |
| Credit-event rate | `credit_event_upb / reference_pool_upb` | Both values non-negative; numerator no greater than pool UPB |
| Tranche thickness | `detachment_pct - attachment_pct` | Attachment must be lower than detachment |
| Coverage reconciliation | Sum of tranche notionals by deal/reporting period | Must match the expected synthetic fixture total exactly |

## Output contract

Each published summary retains source classification, reporting period, deal identifier, reference-pool identifier, current UPB, D30+/D60+ measures, record count, calculation version, and release status. Each public record asset retains all 93 disclosure fields plus deal ID, source member, and source field count. Loan identifier and ZIP3 contain stable keyed public tokens instead of their source values.

## Evaluation thresholds

- Historical synthetic checks remain in `evaluation/report.md`.
- Live-release coverage, uniqueness, status handling, and source lineage are documented in `evaluation/real-release-evaluation.md`.
- Revised-file handling, period continuity gates, fallback reconciliation, and release runtime are verified in `data/derived/real_intake_quality_report.json`. Official source-total comparison remains unavailable because no official file-level totals accompanied the archive.
