# M8 metric-engine evaluation

Status: verified locally on 2026-08-09. Metric version `m8.1.0`; no dashboard or public release changed.

## Decision result

At 2026-07, eligible D60+ was **1.27996%**, up **4.7944 bps** month over month and **8.8781 bps** over three reporting periods. The exact deal decomposition attributes **+4.8272 bps** to within-deal rate movement and **-0.0328 bps** to mix, so the observed monthly increase was performance-led rather than composition-led.

The largest absolute contribution was 2022-HQA1 at **+1.2360 bps**: +1.2071 bps rate effect and +0.0289 bps mix effect. The largest deal-level rate increase was 2026-HQA1 at **+8.9204 bps**, but its smaller portfolio weight limited its contribution to +0.8080 bps. These are surveillance priorities, not causal, investment, or borrower-level conclusions.

## Verified portfolio metrics

| Metric | 2026-07 result | Method / decision use | Limitation |
| --- | ---: | --- | --- |
| Reported Current Actual UPB | $176.3133B | Release-compatible exposure and reconciliation control | Includes $67.51M of REO-state balance |
| Eligible current UPB | $176.2458B | Numeric delinquency state, positive balance, no zero-balance code | Excludes REO/unknown states |
| D30+ | 2.48970% | UPB-weighted eligible rate | Release-compatible rate is 2.48875% |
| D60+ | 1.27996% | Anchor surveillance level | Release-compatible rate is 1.27947% |
| D90+ | 0.95302% | Severe delinquency level | Snapshot rather than path metric |
| D60+ monthly / three-period change | +4.7944 / +8.8781 bps | Rank deterioration and persistence | Population movement requires decomposition |
| Current→D30 roll rate | 0.6876% by count; 0.6627% by prior UPB | Early flow into delinquency | Matched adjacent-period population only |
| D30→D60 roll rate | 19.4105% by count; 19.4541% by prior UPB | Escalation pressure | Denominator must accompany the rate |
| Cure rate | 22.7615% by count; 22.3502% by prior UPB | Resolution flow | A cure may be temporary |
| Voluntary payoff | 4,675 loans; 0.8189% of beginning loans | Separate voluntary runoff from adverse exit | Official zero-balance event mapping |
| Credit-event exit | 55 loans; 0.00963% of beginning loans | Adverse realized exit signal | HQA Actual Loss construct and period-aware codes |
| New modification rate | 0.04787% of active loans | Distress-intervention pressure | Intervention is not an adverse result by itself |
| Assistance exposure share | 1.43137% of eligible UPB | Union of assistance-plan and deferral populations | Programs and reporting vary over time |
| Pool factor | 0.782445 | Remaining balance relative to issuance UPB | Issuance rounding and removals affect interpretation |
| WA Classic FICO / LTV / CLTV / DTI | 751.06 / 92.27 / 92.35 / 38.04 | Risk-mix context | Source sentinels excluded; no imputation |
| Risk-layer UPB: 0 / 1 / 2 / 3 / 4 | 28.85% / 57.29% / 13.51% / 0.36% / 0% | Transparent descriptive concentration | Not a score or prediction |
| Actual Loss rate | Not yet available | Requires two adjacent periods with the field | July 2026 is the first disclosed archive period |

## Calculation and control results

| Gate | Verified result |
| --- | --- |
| Full-data rows | 20,439,666 typed from the M7 Parquet foundation |
| Typed validity | 0 invalid Current Actual UPB rows; 0 invalid delinquency states; 0 unknown pool constructs |
| Release reconciliation | Exact across 292 groups for records, Current UPB, D30+ UPB/rate, and D60+ UPB/rate |
| Transition classification | 19,523,593 prior records; all matched; 0 approved exits, revision exceptions, errors, or new rows |
| Minimum deal-period match rate | 100% |
| Decomposition identity | Maximum variance 2.31e-14 bps; gate <=0.01 bp |
| Metric catalog | 19 material metrics with version, definition, method, meaning, direction, baseline, result location, decision, and limitation |
| Full refresh | 63.402 seconds on the verified local machine |
| Common latest-period watchlist query | 1.23 ms warm |
| Restricted database | 4,993,024 bytes; private integrity record verified |
| Public-release permission | False; database remains under ignored `data/restricted/` |

The release-compatible columns deliberately preserve the existing aggregate denominator for exact control reconciliation. The analytical D30+/D60+/D90+ columns exclude REO and unknown performance states from eligible UPB and expose excluded balance beside the metric. This makes the new denominator explicit without rewriting historical release evidence.

## Engine contents

- `loan_period_typed`: restricted typed view over every full-data Parquet row.
- `pool_period_metrics`, `deal_period_metrics`, and `portfolio_period_metrics`: exposure, levels, changes, modifications, assistance, pool factor, weighted risk attributes, exclusions, and metric version.
- `deal_period_flow_metrics`: transition, cure, exit, modification, deferral, match, and actual-loss-increment measures.
- `deal_period_risk_layer_metrics`: transparent 0–4 condition segmentation.
- `portfolio_d60_decomposition`: exact deal-level rate and mix contribution rows.
- `metric_catalog` and `release_reconciliation`: calculation contract and control evidence.

## Limitations and next gate

- Actual Loss is cumulative and first appears in July 2026. The engine implements period increments but correctly returns unavailable until a second disclosed period exists.
- Rate/mix attribution uses deal as the mutually exclusive portfolio cohort. Additional analyst-selected cohort dimensions belong to the M9 interaction workflow and must preserve the same exact identity.
- Risk layers use four disclosed, transparent conditions: Classic FICO <680, original LTV >90, original DTI >45, and non-primary occupancy. They are descriptive segmentation, never a probability, borrower score, or causal model.
- Updated credit-score fields remain terms-gated and are not used.
- The database is a restricted local analytical artifact. M8 does not authorize its publication or a dashboard change.
