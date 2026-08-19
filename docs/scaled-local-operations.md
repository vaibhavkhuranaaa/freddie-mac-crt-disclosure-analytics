# Scaled-local operations

M12 adds append-only monthly refresh to the restricted local foundation and materialized metric database. It does not add a scheduler, hosted service, or cloud copy.

## Refresh

Place the cumulative approved archive under `data/restricted/`, then run:

```bash
.venv/bin/python scripts/run_scaled_local_refresh.py data/restricted/<approved-archive>.zip
```

The runner performs these steps:

1. Compare archive member metadata with restricted source inventory.
2. Reject missing or revised historical deal-period files.
3. Normalize only unseen deal-period members into staged Parquet.
4. Commit new partitions and foundation manifest without replacing existing history.
5. Rebuild only the rolling metric window needed for one-month flows, three-month change, and decomposition.
6. Verify historical materialized rows remain unchanged before replacing metric database.
7. Reconcile public-safe aggregates, transitions, and decomposition.
8. Write restricted run manifest and current M12 evaluation.

An unchanged cumulative archive runs as a verified no-op. An approved historical revision requires controlled full rebuild; append runner intentionally fails closed.

## Recovery and rollback

Each run declares planned partition paths before commit. Next run removes staged directories and any declared partition absent from committed foundation manifest. If foundation commit succeeded but aggregate or metric refresh stopped, next run detects foundation period ahead of public-safe aggregate or metric database and completes pending work.

Current metric database remains untouched until candidate database passes history-preservation, row-count, reconciliation, transition, and decomposition checks. Source archive and prior committed partitions remain recovery source.

## Retention

- Keep current approved cumulative source archive and committed foundation.
- Keep latest 12 restricted run manifests.
- Remove only abandoned staging directories and uncommitted declared partitions automatically.
- Never delete a committed source partition through incremental runner.
- Perform approved revision or source-retention change through separate controlled full rebuild.

## Capacity gates

M12 local gates are:

- Partition filter reads exactly one Parquet file for one deal-period key.
- Full-history identifier-column scan stays below 5,000 ms.
- Common materialized metric query p95 stays below 2,000 ms.
- Existing full metric refresh stays below 120 seconds.

Move beyond local DuckDB only after one of these triggers repeats:

- Full metric refresh exceeds 120 seconds twice on standard hardware.
- Common warm query exceeds 2 seconds.
- Restricted storage exceeds 70% of available local capacity.
- More than one governed concurrent analyst or shared scheduled refresh is required.

## Costed cloud alternative

BigQuery on-demand is documentary alternative, not approved target. Model assumes 5 GiB logical storage and 100 full 5 GiB scans each month. Google lists first 10 GiB storage and first 1 TiB monthly query processing free; paid list rate above free query allowance is $6.25 per TiB. Under those assumptions, current workload is $0 per month if account free allowance remains available. Without free allowance, modeled active logical storage is about $0.12 and query processing about $3.05 per month, about $3.17 total before network, logging, backup, governance, and support costs. See [official BigQuery pricing](https://cloud.google.com/bigquery/pricing).

Cloud migration requires separate approval, restricted-data governance review, regional and access design, cost cap, teardown plan, and evidence that local trigger was crossed.
