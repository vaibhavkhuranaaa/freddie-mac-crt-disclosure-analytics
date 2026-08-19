# Append-only scaled-local refresh

## Decision

Keep DuckDB and partitioned Parquet. Add cumulative-archive inventory, append-only partition staging, rolling-window materialized metric refresh, restricted run manifests, interrupted-run recovery, and explicit local scale triggers.

## Why

Current 20,439,666-row workload reads one of 292 files for keyed partition query, completes full-history column scan in 214.706 ms, keeps common metric query p95 at 0.588 ms, and previously completed full metric refresh in 63.402 seconds. New platform would add cost, access surface, and data movement without measured need.

## Alternatives rejected

- Rebuild every Parquet partition monthly: wastes work and weakens recovery boundary.
- Mutate existing partition after source revision: breaks append-only lineage.
- Add scheduler or local service framework: single monthly owner-run command is enough.
- Provision cloud warehouse now: no capacity trigger crossed and no cloud approval exists.
- Add table-format dependency: current partition manifest and atomic files cover approved single-writer workflow.

## Not done

No cloud resource, paid service, concurrent service, public deployment, historical revision merge, or automatic deletion of committed source data.

## Changed

Monthly runner now processes unseen deal-period members only, recalculates affected metric window, verifies unchanged historical rows, recovers declared incomplete work, keeps latest 12 run manifests, and fails closed on missing or revised history.
