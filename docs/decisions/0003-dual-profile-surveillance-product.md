# Dual-profile surveillance product

## Decision

Use one governed metric engine for a restricted local analyst workbench and a separate aggregate-only public twin.

## Why

Analysts need permitted row evidence while public reviewers need same workflow and metric meaning without restricted detail. Shared calculations prevent interface-specific drift.

## Alternatives rejected

- One public application with disabled private controls: unclear boundary and accidental exposure risk.
- Two independent metric implementations: reconciliation burden and semantic drift.
- Opaque risk score: unsupported by surveillance decision and harmful to interpretability.

## Not done

No borrower decisioning, prediction, tranche pricing, yield/spread analysis, or causal claim.

## Changed

Approved D60+ anchor, five transparent rank measures, exact rate/mix attribution, public/private boundary, and M7 through M13 plan.
