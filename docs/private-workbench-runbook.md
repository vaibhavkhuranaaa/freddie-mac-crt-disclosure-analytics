# Private analyst workbench runbook

## Boundary

This workbench reads `data/restricted/metrics/metrics.duckdb` and serves authorized row detail. Run it only on a controlled local machine. The service binds to `127.0.0.1`, uses read-only database connections, and does not serve the repository root.

Do not expose the port through a tunnel, proxy, container host binding, shared network, or public deployment. Do not capture screenshots while restricted identifiers are revealed.

## Start

From the repository root:

```bash
.venv/bin/python scripts/serve_private_workbench.py --port 8011
```

Open `http://127.0.0.1:8011/`.

The service fails closed when the metric database is missing or placed outside `data/restricted/`.

## Analyst workflow

1. Keep the latest reporting period selected.
2. Start with the default portfolio D60+ contribution rank, then use another visible transparent measure when the investigation calls for it.
3. Compare the first deal with the portfolio and its own history.
4. Use the driver section to distinguish the deal with the largest rate increase from the deal with the largest portfolio contribution.
5. Review delinquency flows, outcomes, risk layers, and reference pools.
6. Filter permitted loan rows. Keep identifiers masked unless the investigation requires the source key.
7. Use the evidence rail to verify definition, population, exclusions, version, and limitations.
8. Export the evidence package. It is marked nonpublic and excludes loan rows and identifiers.

## Verify

```bash
.venv/bin/python scripts/evaluate_private_workbench.py
UV_CACHE_DIR=/private/tmp/freddie-mac-crt-uv-cache \
  .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

The evaluation must pass the 5,000 ms first-interaction and 2,000 ms warm-query budgets. The public release manifest must remain free of private application paths, restricted database paths, identifiers, and row-level data.

## Recovery

- **Database missing:** rebuild M8 into an empty restricted output path, then restart the service.
- **No rows:** clear the loan status or risk-layer filter.
- **No prior-period flow:** choose a reporting period with an adjacent prior observation.
- **Calculation error:** stop the service, verify `data/derived/m8_metric_evaluation.json`, and rerun the M8 tests before restarting.
- **Unexpected network exposure:** stop the process immediately. Confirm the service was launched through this script and that no external proxy or tunnel is active.
