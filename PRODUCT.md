# Product


## Platform

web

## Users

Primary user: a capital-markets analyst or risk reviewer examining transaction-level CRT reference-pool performance. A hiring manager is a secondary reader of the deployed portfolio evidence.

## Product Purpose

Provide a CRT collateral surveillance workbench that helps an analyst identify which deal or reference-pool cohorts are deteriorating, inspect the complete disclosed loan-period evidence, explain whether the change comes from within-cohort performance or portfolio mix, and verify that the finding is reliable enough to investigate. Success means a public user can move from a measured exception to masked records, cohort drivers, transitions, and provenance without authentication.

## Positioning

The product combines collateral surveillance, explainable metric decomposition, and release controls in one review surface. It is not a generic mortgage dashboard, a tranche cash-flow or investment-pricing engine, or a borrower-level lending, underwriting, pricing, servicing, or marketing system.

## Operating Context

The monthly workflow normalizes the full authorized Clarity loan-level layout in restricted local storage, replaces direct identifiers in an offline publication step, and calculates one versioned metric system. The analyst starts with D60+ level and change, inspects the complete masked register, compares deals and periods, explains rate versus mix effects, reviews delinquency flows and outcomes, and verifies lineage. The synthetic fixture remains a regression fallback only.

## Capabilities and Constraints

- The full authorized archive is retained in local restricted storage and is not deployed.
- The public data release preserves every one of the 20,439,666 records and all 93 disclosure fields, plus three lineage columns, across 292 masked Parquet assets.
- Loan identifier and ZIP3 are replaced with stable keyed tokens before publication. The masking key, raw archive, and local paths remain private.
- The public workbench uses derived summaries for navigation and an unauthenticated server-side query for the complete masked record register.
- Historical M7-M13 and P7 evidence covers the earlier aggregate release. The full-record revision requires its own privacy, API, browser, and hosted verification before its claims supersede that baseline.
- Independent review remains `0/5`, so no representative-usability claim is made.

## Evidence on Hand

- Live release evidence: `evaluation/real-release-evaluation.md`
- Public deployment receipt: `evaluation/public-release-verification.md`
- Full-data metric-engine evidence: `evaluation/m8-metric-engine.md`
- Private analyst workbench evidence: `evaluation/m9-private-workbench.md`
- Aggregate-only public-twin evidence: `evaluation/m10-public-twin.md`
- Completed M11 technical scorecard and findings: `evaluation/m11-usability-quality-controls.md`
- Completed M12 scaled-local evaluation: `evaluation/m12-scaled-local-hardening.md`
- M13 local showcase readiness: `evaluation/m13-showcase-readiness.md`
- P7 hosted candidate verification: `evaluation/p7-hosted-candidate-verification.md`
- Historical synthetic baseline: `evaluation/baseline.json` and `evaluation/report.md`

## Product Principles

1. Start with the decision, then expose the calculation and evidence.
2. Preserve full disclosed evidence for public analysis and mask direct identifiers before publication.
3. Separate performance change from portfolio-mix change.
4. Show provenance, population, exclusions, and limitations beside every material metric.
5. Make unsafe, unavailable, partial-coverage, masking, and linkage limits explicit rather than silent.
6. Prefer reproducible local evidence to unsupported production or scale claims.

## Accessibility & Inclusion

The web demo must be keyboard accessible, responsive, readable at browser zoom, and understandable without relying on color alone.
