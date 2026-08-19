# Separated serving boundaries

## Decision

Serve private evidence through loopback-only read-only HTTP and public evidence through fixed static assets.

## Why

Separate surfaces make trust boundary explicit. Private service can query permitted rows locally; public twin ships only an allowlisted aggregate projection with no runtime API or DB.

## Alternatives rejected

- Deploy private workbench publicly: violates access contract.
- Copy restricted DuckDB into public bundle: exposes rows and local lineage.
- Recalculate metrics in JavaScript: duplicates governed semantic logic.

## Not done

No hosted authentication layer, serverless API, public row drill-through, or per-query bill.

## Changed

M9 delivered loopback analyst workflow with masked on-demand rows. M10 delivered static aggregate twin with exact parity and fixed release manifest.
