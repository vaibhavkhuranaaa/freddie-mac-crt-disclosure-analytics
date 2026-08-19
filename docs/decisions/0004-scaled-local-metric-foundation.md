# Scaled-local metric foundation

## Decision

Use source-faithful partitioned Parquet plus DuckDB for complete approved archive and versioned semantic layer.

## Why

Twenty million analytical rows require partition pruning and columnar scans but remain restricted and single-user. Local DuckDB/Parquet met reconciliation and refresh budgets without paid shared infrastructure.

## Alternatives rejected

- Postgres or warehouse: unnecessary service, cost, and data movement for current access pattern.
- One monolithic CSV: weak pruning, typing, and recovery properties.
- Rewrite source values during normalization: loses auditability across 89/90/93-field layouts.

## Not done

No cloud warehouse, scheduler, time-travel table format, or incremental-refresh claim. M12 owns operational hardening.

## Changed

M7 created 292 restricted Parquet partitions over 20,439,666 rows. M8 created metric version `m8.1.0` with exact shared reconciliation and decomposition.
