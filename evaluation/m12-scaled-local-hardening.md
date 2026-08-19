# M12 scaled-local hardening evaluation

Status: **complete on 2026-08-13**.

## Decision

Keep current restricted workload on local DuckDB and partitioned Parquet. Append-only runner now ingests unseen deal-period files, recomputes rolling metric window, preserves unaffected materialized history, recovers interrupted work, retains restricted run evidence, and rejects historical revisions.

No cloud resource was created. Current local system remains well inside approved performance and storage triggers.

## Measured full-data evidence

Hardware: Apple M5 MacBook Air, 10 cores, 16 GB memory, macOS 26.5.2.

| Gate | Result | Threshold | Status |
| --- | ---: | ---: | --- |
| Restricted rows | 20,439,666 | complete archive | Pass |
| Parquet partitions | 292 | complete archive | Pass |
| Parquet bytes | 662,598,404 | observed | Context |
| Deal-period pruning | 1 of 292 files read | exactly 1 | Pass |
| Filtered partition scan | 80.861 ms | <1,000 ms | Pass |
| Full-history identifier-column scan | 214.706 ms | <5,000 ms | Pass |
| Materialized metric query p95, 20 runs | 0.588 ms | <2,000 ms | Pass |
| Existing full metric refresh | 63.402 s | <120 s | Pass |
| Local restricted-storage utilization | 0.7952% | <70% trigger | Pass |

Full-data run used unchanged approved cumulative archive, so refresh correctly performed no append. It initialized restricted source inventory, wrote restricted run manifest, and verified current capacity and pruning.

## Incremental and recovery evidence

Deterministic cumulative-archive fixture added one new monthly partition after two committed months. Incremental runner:

- wrote only unseen partition;
- recomputed rolling window needed for one-month flow and three-month change;
- retained unchanged historical materialized table rows;
- advanced portfolio metrics through new month;
- rejected changed source metadata for existing partition;
- recovered after foundation committed but metric database was unavailable;
- removed declared orphan partition from interrupted run;
- enforced two-run retention in test environment.

All 32 repository tests pass, including both M12 append and revision-rejection cases.

## Cost model and scale trigger

BigQuery on-demand was costed only as fallback. Conservative model uses 5 GiB logical storage and 500 GiB monthly scan volume. Current official free allowances would cover that isolated account usage. Without free allowances, modeled list cost is about $3.17 per month before network, observability, backup, and governance costs.

Migration is not justified while local full refresh remains below 120 seconds, common query remains below 2 seconds, storage remains below 70%, and workload remains one governed local analyst. Cloud data movement, provisioning, or spend still requires separate owner approval.

## Limitations

- New-month path is verified with deterministic cumulative-archive fixture because no newer approved disclosure archive was supplied.
- Capacity results are local single-user lab measurements, not concurrent or hosted evidence.
- Append runner rejects historical source revisions; approved revision requires controlled full rebuild.
- BigQuery estimate is a planning model, not bill, quote, deployment, or governance approval.
