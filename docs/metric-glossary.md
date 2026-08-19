# Metric glossary

Status: M8 metric version `m8.1.0` verified on the complete full-data foundation. Detailed results and controls are in `evaluation/m8-metric-engine.md`.

## Metric contract

| Metric | Definition and method | Business meaning / supported decision | Desired direction | Baseline / result | Material limitation |
| --- | --- | --- | --- | --- | --- |
| Eligible current UPB | Sum of positive Current Actual UPB for numeric delinquency states with no zero-balance code | Exposure represented by the selected view | Context, not directional | 2026-07: $176.2458B; $67.51M REO balance excluded | Current Actual UPB can include deferred non-interest-bearing balance after modification |
| UPB-weighted D30+ rate | D30+ eligible Current Actual UPB divided by eligible current UPB | Broad early delinquency level | Lower | 2026-07: 2.48970%; release-compatible 2.48875% | REO, unknown, removal, and zero-UPB treatment remains visible |
| UPB-weighted D60+ rate | D60+ eligible Current Actual UPB divided by eligible current UPB | Anchor collateral-deterioration level | Lower | 2026-07: 1.27996%; release-compatible 1.27947% | It is not a loss estimate or tranche-performance measure |
| UPB-weighted D90+ rate | D90+ eligible Current Actual UPB divided by eligible current UPB | More severe delinquency level | Lower | 2026-07: 0.95302% | Current status is a snapshot and may not describe prior paths |
| Monthly D60+ change | Current D60+ rate minus prior-period D60+ rate, multiplied by 10,000 | Identifies improving or worsening pools in comparable units | Lower / negative | 2026-07: +4.7944 bps | Denominator and population changes can mix composition with performance |
| Three-month D60+ change | Current D60+ rate minus rate three reporting periods earlier, multiplied by 10,000 | Separates persistent movement from one-month noise | Lower / negative | 2026-07: +8.8781 bps | Requires continuous comparable periods |
| D60+ rate effect | Average deal UPB weight times change in deal D60+ rate | Quantifies within-deal deterioration contribution | Lower / negative | 2026-07: +4.8272 bps | Deal is the M8 mutually exclusive cohort; attribution is descriptive |
| D60+ mix effect | Average deal D60+ rate times change in deal UPB weight | Quantifies portfolio-composition contribution | Context; adverse positive contribution is undesirable | 2026-07: -0.0328 bps | Mix is descriptive, not causal |
| Current-to-D30 roll rate | Prior-current loans becoming D30+ divided by matched prior-current population, reported by UPB and loan count | Early-warning flow into delinquency | Lower | 2026-07: 0.6876% count / 0.6627% prior UPB | Requires stable loan matching and explicit removed-loan handling |
| D30-to-D60 roll rate | Prior D30 loans becoming D60+ divided by matched prior-D30 population | Escalation pressure | Lower | 2026-07: 19.4105% count / 19.4541% prior UPB | Small cohorts need count and balance context |
| Cure rate | Prior D30+ loans returning current divided by matched prior-D30+ population | Resolution performance | Higher | 2026-07: 22.7615% count / 22.3502% prior UPB | A cure can be temporary; repeat delinquency remains separate |
| Voluntary payoff rate | New code-01 exit balance or count divided by beginning eligible balance or population | Collateral runoff/prepayment context | Context, not directional | 2026-07: 4,675 loans; 0.8189% of beginning loans | Zero Balance Code definitions differ by reference-pool construct and period |
| Credit-event exit rate | New construct- and period-eligible credit-event removals divided by beginning eligible balance or population | Realized adverse exits from the reference pool | Lower | 2026-07: 55 loans; 0.00963% of beginning loans | Fixed Severity and Actual Loss codes require separate mappings |
| Actual loss rate | Incremental Actual Loss divided by documented beginning balance for applicable Actual Loss pools | Realized loss or gain | Lower | Unavailable: July 2026 is the first disclosed archive period | Requires two adjacent disclosed periods and is inapplicable to Fixed Severity pools |
| New modification rate | Loans with current-period Modification Flag Y divided by eligible active population | Distress intervention pressure | Lower, interpreted with cures | 2026-07: 272 loans; 0.04787% of active loans | A modification is an intervention, not an adverse outcome by itself |
| Payment-deferral / assistance share | Union of eligible UPB with current/prior deferral or an assistance plan divided by eligible UPB | Loss-mitigation exposure | Lower, interpreted with performance | 2026-07: 1.43137% | Availability and semantics vary by reporting period |
| Pool factor | Reported Current Actual UPB divided by UPB at Issuance for the period population | Remaining collateral balance | Context, usually declining | 2026-07: 0.782445 | Issuance rounding and removals affect interpretation |
| WA Classic FICO / LTV / CLTV / DTI / coupon / loan age | Current-UPB-weighted valid field value with unavailable UPB retained separately | Risk-mix and comparability context | Context, metric-specific | 2026-07: 751.06 / 92.27 / 92.35 / 38.04 / 5.004% / 43.68 months | Do not impute sentinel/unavailable values into weighted averages |
| Risk-layer share | Eligible UPB with 0–4 conditions: FICO<680, LTV>90, DTI>45, and non-primary occupancy | Concentration of compounding origination risk | Lower high-layer share | 2026-07 UPB: 28.85% / 57.29% / 13.51% / 0.36% / 0% | Descriptive segmentation, not a borrower score or causal model |
| Loan match rate | Loans matched between adjacent periods divided by prior population | Transition-metric reliability | Higher | 19,523,593 of 19,523,593 prior rows matched; minimum deal-period rate 100% | Exits and new/revised records must be classified, not treated as match failures |
| Metric coverage | Eligible numerator/denominator population divided by in-scope source population | Whether a result represents the selected source | Higher | Full 20,439,666 rows typed; applicability retained per metric | Applicability varies by field, deal construct, and schema version |
| Reconciliation variance | Difference between normalized/metric totals and approved source/control totals | Reproducibility and control status | Zero or documented tolerance | Zero across all 292 shared aggregate groups | Official file-level totals were not supplied with the retained archive |

## Eligibility and version rules

- `m8.1.0` uses the official v4.2 glossary. Numeric delinquency values map 0=current, 1=D30, 2=D60, and 3+=D90+; `RA` and `XX` are excluded from analytical rate denominators and exposed separately.
- The retained HQA rows classify as Actual Loss pools through the applicable Distressed Principal Balance Flag values. Zero-balance exit codes are mapped by pool construct and the July 2026 boundary.
- Release-compatible rates preserve the prior reported-UPB denominator only for exact reconciliation. Analytical rates use eligible UPB.
- Actual Loss is treated as cumulative. A period rate is calculated only when both adjacent periods disclose a numeric value.
- Updated credit-score fields remain terms-gated and are not inputs to `m8.1.0`.

## Priority policy

The first product release will rank transparent metrics rather than publish an arbitrary composite score. Any later priority band must:

1. use thresholds derived from the observed full-data distribution;
2. show the exact triggered rules;
3. be backtested for stability and false-alert behavior;
4. never be described as a probability of loss, credit score, or investment recommendation.
