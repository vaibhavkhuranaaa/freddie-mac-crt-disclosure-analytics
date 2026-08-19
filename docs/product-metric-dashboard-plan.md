# Product, metric, and dashboard plan

Status: approved by the project owner on 2026-08-09. M7-M10 are verified. M11 closed under owner-approved technical scope on 2026-08-12. M12 scaled-local hardening passed on 2026-08-13. Independent review remains `0/5` and unclaimed.

## 1. Product purpose

Build a **CRT collateral surveillance workbench** that helps a capital-markets analyst answer one recurring question:

> Which deal or reference-pool cohorts are deteriorating, what is driving the change, and is the evidence reliable enough to investigate?

The product is not a generic mortgage dashboard and is not a security-pricing or borrower-decision system. It supports monthly collateral surveillance of authorized Freddie Mac CRT reference-pool disclosures.

### Users and decisions

| User | Situation | Decision supported | Successful outcome |
| --- | --- | --- | --- |
| Capital-markets credit/risk analyst | Monthly surveillance after a new disclosure period | Rank deals and cohorts for investigation | Finds the largest deterioration, identifies its drivers, and traces the result to source and calculation evidence |
| Portfolio or model reviewer | Challenges an analytical finding | Decide whether a metric is reproducible and comparable | Verifies definition, version, population, exclusions, reconciliation, and limitation |
| Hiring manager | Reviews the public portfolio experience | Assess analytical, engineering, product, and control judgment | Completes the same aggregate decision workflow and sees honest evidence of the scaled local design |

### Primary workflow

1. Start at the latest reporting period and scan a ranked watchlist.
2. Select a period-valid deal and compare its keyed trailing history with the eligible-UPB-weighted portfolio baseline.
3. Explain the change through cohort rate effect versus portfolio mix effect.
4. Inspect delinquency transitions, exits, modifications, and loss signals.
5. In the private workbench only, explicitly load authorized loan-period rows; identifiers remain masked unless deliberately revealed.
6. Review freshness, schema coverage, exclusions, reconciliation, and metric version before exporting evidence.

### Non-goals

- No borrower lending, underwriting, pricing, marketing, servicing, or credit-granting decisions.
- No re-identification, outside-data enrichment, or person/property matching.
- No public record-level rows, identifiers, exact payment histories, or restricted derivatives.
- No claim of tranche cash-flow, waterfall, yield, spread, or investment analytics without separate transaction documents and validated models.
- No opaque risk score or predictive model in the first product release.

## 2. Evidence-backed current assessment

The project now has two deliberately separate surfaces. The legacy live release streams four approved fields from 292 monthly files into 292 reference-pool-period aggregates. The verified M9/M10 local system processes all 20,439,666 rows through a source-faithful 93-position foundation and metric version `m8.1.0`, then serves a private workbench and a 305,060-byte aggregate-only public projection from that shared engine.

Observed planning facts:

- The retained archive is approximately 1.07 GB and contains 292 standard monthly loan-level files, five aggregate-postal-code files, and eight other members.
- A read-only sample across every standard monthly file found 89-, 90-, and 93-field rows, so the normalized layer must be reporting-period/schema-version aware.
- The official v4.2 layout defines 93 loan-level positions, including origination attributes, current performance, payment history, zero-balance outcomes, modifications, assistance, valuation, and actual-loss fields.
- The legacy live dashboard remains useful evidence of safe aggregate intake but retains its original limited analytical workflow and mixed-deal line-chart limitation.
- The M9 private workbench and M10 public twin now rank transparent measures, preserve coherent selected-deal history, compare against the portfolio baseline, attribute exact D60+ rate/mix contributions, expose flow evidence, and attach governed definitions and control state.
- The latest full-engine result for 2026-07 is 1.27996% D60+ and 2.48970% D30+, with monthly D60+ change of +4.7944 bps. Release-compatible rates remain 1.27947% and 2.48875%; the denominator distinction is explicit in the metric evidence.

## 3. Metric system

### Metric spine

The dashboard must read as one analytical chain, not a collection of cards:

1. **Exposure:** current UPB and active-loan population.
2. **Level:** UPB-weighted D30+, D60+, and D90+ rates.
3. **Change:** month-over-month and three-month changes in basis points.
4. **Flow:** current-to-D30, D30-to-D60, cure, modification, voluntary payoff, and credit-event transitions.
5. **Outcome:** credit-event exits and actual loss where the field is applicable.
6. **Driver:** exact rate-effect and mix-effect decomposition by approved cohort.
7. **Evidence:** population coverage, match rate, null/unknown rates, schema version, reconciliation, freshness, and metric version.

### Anchor and decision metrics

**Anchor metric: UPB-weighted D60+ rate**

`sum(current_actual_upb where delinquency_bucket >= 2) / sum(current_actual_upb in eligible active population)`

This expresses the share of current collateral balance at least 60 days delinquent. RA, XX, removed loans, zero-UPB rows, and other exclusions must be reported separately rather than silently folded into the denominator.

**Decision metric: D60+ change decomposition**

For cohort `c`, reporting periods `t-1` and `t`, let `w` be the cohort share of eligible UPB and `r` its D60+ rate:

- `rate_effect_c = average(w_c,t, w_c,t-1) * (r_c,t - r_c,t-1)`
- `mix_effect_c = average(r_c,t, r_c,t-1) * (w_c,t - w_c,t-1)`
- `portfolio_change = sum(rate_effect_c + mix_effect_c)`

Multiply effects by 10,000 for basis points. This midpoint decomposition is exact: it separates worsening within a cohort from changes in the portfolio's composition. The default watchlist ranks total contribution to portfolio D60+ change while retaining rate and mix effects beside it; analysts can select other transparent rank measures.

### Approved metric-engine and cohort boundary

- The M10 public twin exposes only reporting period, deal, reference pool, portfolio/deal levels and changes, flow rates, exact decomposition, definitions, scope, and controls.
- The M9 private workbench additionally exposes approved risk layers and authorized loan-period evidence from the full-data engine.
- Origination vintage, Classic FICO, original LTV/CLTV, DTI, risk-layer count, loan purpose, channel, occupancy, property type, state, loan age, modification, payment deferral, borrower assistance, disaster, and zero-balance status remain approved private analytical dimensions when implemented and governed.
- Seller and servicer remain private-only unless a separate aggregate-public review approves them.

Updated credit scores require a terms-specific review before use. Postal data remains excluded from the first public cohort set.

## 4. One product, two delivery profiles

| Concern | Light public demo | Scaled local workbench |
| --- | --- | --- |
| Purpose | Hiring-manager evidence and safe analytical walkthrough | Authorized monthly surveillance and root-cause investigation |
| Data | Versioned, precomputed aggregate cohort cubes derived from the full archive | Full normalized loan-period disclosure layer plus aggregate metric views |
| Storage | Static CSV/JSON or Parquet assets sized for the browser | Restricted local DuckDB/Parquet, partitioned by reporting period and deal |
| Compute | Build-time calculations; browser filters already-approved aggregates | Local SQL metric views and restricted drill-through queries |
| UI capability | Overview, watchlist, comparison, drivers, flow evidence, metric evidence, and an explicit restricted state | Same views plus approved risk layers, authorized on-demand loan-period rows, and local evidence export |
| Security | No raw rows or row-level derivatives in bundle, Git, or unauthenticated routes | Local-only by default; restricted files and database ignored by Git; explicit access boundary |
| Cost | Existing static-hosting capacity; no new paid resources | Local machine only; no paid service required |
| Scale path | Publish smaller aggregates without changing metric semantics | Incremental partitions, predicate pushdown, materialized metric tables, then an approved warehouse only if measured limits require it |

The public demo is not a synthetic mock of the private product. It is a safe projection of the same metric engine, metric versions, filters, and evidence contract.

## 5. Dashboard brief

Mode: **Operate** for the analyst surface; the public version preserves the operating workflow and adds a concise case-study entry.

### Information architecture

1. **Portfolio pulse:** disclosure month, eligible UPB, D60+ level, monthly change, and largest portfolio contributor.
2. **Watchlist:** ranked deal table with the selected measure, D60+ level/change, affected UPB, rate effect, mix effect, and prior-loan match evidence.
3. **Compare:** coherent selected-deal history against the eligible-UPB-weighted portfolio baseline with explicit period-over-period deltas.
4. **Explain:** rate-effect/mix-effect waterfall and cohort contribution table.
5. **Flow and outcomes:** delinquency transition matrix, cure/roll rates, voluntary payoff, credit-event exits, modifications, and actual loss where applicable.
6. **Evidence drawer:** metric definition, denominator, exclusions, source fields, calculation version, as-of period, reconciliation, and limitations.
7. **Restricted drill-through:** private-only loan-period rows; the public twin shows an explicit restricted-state explanation.

### Required interaction behavior

- Shared global filters are disclosure month, a deal observed in that month, and one of five visible transparent rank measures. Portfolio D60+ contribution is the default.
- Filter state is URL-addressable in the public demo so a hiring manager can reopen a finding.
- Headline metrics attach definition, denominator, exclusions, source/metric version, coverage, and control evidence in the evidence rail.
- Charts never connect unrelated deal-period observations. Multi-deal views use small multiples or clearly keyed series.
- The watchlist supports keyboard selection, explicit units, visible rank values, and deterministic rank controls. The private evidence export is nonpublic and excludes loan rows and identifiers.
- Loading, no-match, partial-coverage, stale-source, calculation-error, and restricted states each explain recovery.

### First hiring-manager walkthrough

“D60+ rose by X bps in the latest period. Identify which deal drove the increase, determine whether the movement came from within-cohort deterioration or mix shift, inspect the delinquency-flow evidence, and verify the metric definition and source coverage.”

The target is a five-minute self-guided workflow with no domain explanation required outside the interface.

## 6. Milestone plan

### M6: Approve product, data, metric, and dashboard contract

Deliver this document, the proposed metric glossary, data profile, dual-profile architecture, evaluation contract, and updated milestones. Record owner corrections and approval before implementation.

Exit gate: the primary user, decision, metric spine, public/private boundary, and first walkthrough are explicitly approved. No application code is part of M6.

Hiring-manager evidence: concise product brief showing why the project exists and which analytical decisions it supports.

### M7: Build the controlled full-data foundation

Status: completed and verified on 2026-08-09.

Create a version-aware 89/90/93-field parser and normalized loan-period layer from every accepted standard monthly file. Retain the complete authorized layout in restricted local storage, document each field, and create aggregate-postal-code handling as a separate source family.

Exit gate: 292 accepted files and 20,439,666 rows reconcile to the current intake manifest; field-count/version drift, null/sentinel handling, loan-key uniqueness, period continuity, duplicate revisions, and row-level access controls pass. No restricted derivative enters Git or the public bundle.

Hiring-manager evidence: full-data schema map, quality profile, lineage diagram, and reproducible controlled build.

### M8: Implement and validate the metric engine

Status: completed and verified on 2026-08-09 as metric version `m8.1.0`.

Implement the metric spine as versioned SQL views or tables over the restricted layer. Start with exposure, D30/D60/D90, period changes, transition/cure rates, zero-balance outcomes, modification/deferral measures, risk-mix summaries, and exact rate/mix decomposition.

Exit gate: aggregate D30/D60/current-UPB outputs reconcile to the existing release; transition populations reconcile period-to-period; every metric has tests, definition, denominator, exclusions, desired direction, baseline, supported decision, and limitation. Priority thresholds, if used, are derived from observed distributions and backtested.

Hiring-manager evidence: metric contract, reconciliation report, explainable decomposition, and benchmark results.

### M9: Deliver the private analyst workbench

Status: completed and verified on 2026-08-09.

Build the overview, watchlist, compare, driver, transition/outcome, evidence, and restricted loan-detail views using the shared metric engine.

Exit gate: an authorized reviewer can complete the first walkthrough, trace a metric to contributing cohorts and permitted rows, and export an evidence package. Typical filtered interactions meet the approved private evaluation contract.

Hiring-manager evidence: private-mode architecture and redacted screenshots or recordings that reveal no restricted rows.

### M10: Produce the aggregate-only public twin

Status: completed and verified locally on 2026-08-09.

Export only approved aggregates from the shared metric engine and deliver the same overview, watchlist, compare, driver, transition, and evidence workflow. Replace loan detail with a deliberate restricted state.

Exit gate: no raw row, identifier, payment history, restricted dimension, or local path appears in the bundle; public metrics reconcile to the private engine and remain usable on the existing free static-hosting path.

Hiring-manager evidence: live, self-guided analytical workflow with metric lineage and zero paid runtime dependency.

### M11: Prove technical usability, analytical quality, and controls

Status: completed under revised technical scope. Automated reconciliation, Chromium accessibility/keyboard/responsive/error-state checks, local performance, security controls, and three analytical findings pass. Zero independent reviewers are evidenced; no representative-usability claim is made.

Run task-based usability checks, metric reconciliation, edge-case and status-code tests, accessibility checks, responsive/browser checks, and performance benchmarks. Write three evidence-backed findings with calculations and limitations.

Exit gate: technical walkthrough, accessibility/control, performance, reconciliation, and analytical-finding thresholds pass; independent review remains explicitly unavailable and unclaimed.

Hiring-manager evidence: evaluation scorecard, before/after workflow comparison, and documented analytical findings.

### M12: Harden scaled-local operation

Status: completed and verified on 2026-08-13.

Add incremental refresh, partition pruning, materialized metric refreshes, failure recovery, observable run manifests, retention controls, and measured capacity tests. Do not introduce cloud infrastructure unless local limits are demonstrated and a separate approval is recorded.

Exit gate: a new monthly partition can be ingested and reflected without rebuilding unaffected history; rollback/recovery is tested; full-history query and refresh budgets pass on documented hardware.

Hiring-manager evidence: scale test, cost model, operational runbook, and explicit cloud migration trigger.

### M13: Package the showcase and release

Status: local showcase package completed and verified on 2026-08-13. Deployment, publication, push, and portfolio-site application remain separately gated.

Update the case study, architecture/evidence diagrams, public claims, screenshots, portfolio record, and interview walkthrough. Deployment or portfolio publication requires a new explicit approval even when existing Vercel capacity is reused.

Exit gate: exact private source attestation, deterministic bundle manifest, local release verification, and release-readiness checks pass. Hosted and portfolio evidence remain later approved gates.

Hiring-manager evidence: live demo, concise case study, architecture narrative, metric glossary, evaluation report, and five-minute walkthrough.

## 7. Decisions resolved before M7

The project owner approved the positioning, D60+ metric spine, private seller/servicer boundary, updated-score terms gate, no-composite-score policy, hiring-manager walkthrough, and M7–M13 sequence on 2026-08-09. Canonical authority records live in the private sibling operations folder.
