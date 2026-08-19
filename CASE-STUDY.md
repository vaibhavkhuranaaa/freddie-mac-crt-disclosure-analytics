# Freddie Mac CRT Disclosure Analytics

## The review question

Which Freddie Mac CRT deals and reference-pool cohorts warrant investigation, what changed in delinquency performance, and can an analyst trace the result back to the disclosed loan-period records?

## What is live

The [public collateral-surveillance workbench](https://freddie-mac-crt-disclosure-analytic.vercel.app) serves the complete masked release: 20,439,666 loan-period rows across 292 deal-month assets. An analyst can move from the portfolio review docket into a selected partition, page through masked records, and inspect all 93 disclosure fields plus three lineage columns.

The interface is public. The data path is deliberately private. Masked Parquet objects live in a private Cloudflare R2 bucket. A GET-only Worker accepts authenticated requests for one exact release object. The Vercel query function holds that credential server-side, validates the requested deal, period, status, page size, and offset, then returns at most 50 records. The browser receives neither an object-storage URL nor a service token.

## Why the full record matters

The earlier public release stopped at deal-period aggregates. That was useful for triage but weak for investigation: a reviewer could see that a deal moved without inspecting the disclosed records behind the movement. The current release keeps the aggregate decision frame and adds a bounded record register. This preserves the analytical chain from portfolio change to deal contribution, cohort context, and source-level evidence.

July 2026 eligible D60+ was 1.27996%, up 4.7944 basis points month over month. `2026-HQA1` recorded the largest deal-level rate increase at 8.9204 basis points, while `2022-HQA1` contributed the most to portfolio deterioration at 1.2360 basis points because its exposure weight was larger. The distinction prevents a reviewer from treating the worst rate movement as automatically the most important portfolio driver.

## Data and decision boundary

The source is the owner-approved Freddie Mac Clarity CRT disclosure archive. The build preserves every accepted standard monthly row and all supported source positions. Before any public asset is created, the original loan identifier and ZIP3 are replaced with stable keyed tokens. The raw archive, original identifiers, masking key, restricted metric database, credentials, and local paths remain outside Git and the browser bundle.

Masking two direct fields does not make every field combination anonymous. Other disclosed attributes may remain linkable to the original Freddie Mac release. Re-identification and outside-data matching are prohibited. The product supports collateral-surveillance investigation, not lending, underwriting, pricing, servicing, household-level decisions, forecasts, causal claims, or investment recommendations.

## Evidence

- Complete release scan: 20,439,666 rows, 292 partitions, 96 stored columns, zero invalid loan tokens, and zero invalid ZIP3 tokens.
- Metric controls: exact reconciliation across 292 shared groups and exact decomposition of portfolio D60+ change into rate and mix contributions.
- Local operations: one-file partition pruning, 214.706 ms full-history column scan, 0.588 ms materialized-query p95, append-only refresh, recovery, and retention checks.
- Hosted path: all 292 masked assets uploaded to private R2, anonymous Worker requests rejected, authenticated object parity verified, production API and dashboard returned HTTP 200, and required security headers were present.
- Product checks: 39 Python tests and four Worker tests passed; desktop and mobile flows passed with zero automated WCAG A/AA violations and no application browser errors.
- Cost: incremental deployment cost was $0. Workers Free supplies a hard 100,000-request daily ceiling.

## Tradeoffs

Private object storage separates the dataset lifecycle from source-code publication and leaves more free-tier headroom than the rejected Vercel Blob option. Retrieving a deal-month Parquet object through a server function is intentionally narrower than exposing bulk objects or operating a public analytical database. R2 SQL or a hosted database becomes justified only when measured concurrency, latency, query shape, or growth exceeds the current bounded design.

Evidence remains technical and single-browser unless stated otherwise. No independent user study, Firefox or Safari session, assistive-technology session, field performance measurement, or concurrent-load test has been completed.
