# Scope

## User and decision

Capital-markets credit/risk analyst ranks Freddie Mac CRT deals and reference-pool cohorts for monthly surveillance, distinguishes portfolio contribution from deal-level deterioration, explains rate versus mix effects, and hands off traceable evidence for investigation.

## Included

- Complete approved standard monthly archive through July 2026.
- Exposure, D30+/D60+/D90+, change, transition, exit, modification, loss applicability, risk mix, and exact D60+ decomposition.
- Unauthenticated public workbench with the complete masked loan-period register, all disclosed fields, shared metric definitions, and deal-month filters.
- Restricted loopback workbench and raw source layer for controlled verification.
- Reconciliation, accessibility, browser, responsive, security, performance, and evidence controls.

## Excluded

- Re-identification or matching to outside person/property data.
- Consumer credit approval, denial, pricing, servicing, marketing, or scoring.
- Original direct identifiers, raw source archives, and the masking key in public assets.
- Tranche/waterfall cash flows, pricing, yield, spread, or investment recommendations.
- Forecasting and causal claims.
- Hosted restricted access or opaque composite score.

## Current release truth

The masked full-record revision is the current production release. It preserves 20,439,666 records across 292 private object-storage partitions and exposes all 93 disclosure fields plus three lineage columns through bounded public queries. The verified P9 aggregate deployment remains the rollback target. Portfolio-site changes remain separately gated.

## Evaluation gates

Technical M11 evaluation passes exact public/private parity, zero detected WCAG A/AA violations, responsive/keyboard checks, security controls, local performance, and three calculation-backed findings. No independent user study was performed; observed result remains `0/5`, and no representative-usability claim is made.
