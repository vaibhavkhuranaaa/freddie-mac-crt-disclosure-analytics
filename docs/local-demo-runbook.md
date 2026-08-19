# Public full-record workbench local runbook

## Purpose

This runbook opens the public workbench locally against the separately built masked full-record assets. The server never exposes the repository root, raw source archive, or masking key.

## Start

```bash
.venv/bin/python scripts/build_public_projection.py
.venv/bin/python scripts/build_public_full_data.py
.venv/bin/python scripts/build_release.py
.venv/bin/python scripts/serve_demo.py --port 8010
```

Open `http://127.0.0.1:8010/`. The server exposes `dist/` plus the `/api/records` handler. The handler reads only `data/public/full-data`, validates deal-month asset names, caps page size at 50, and has no synthetic fallback.

## Reviewer workflow

1. Confirm the source scope reports 20,439,666 records and metric version `m8.1.0`.
2. Change the disclosure month and confirm the deal list contains only deals reported then.
3. Confirm the record register reports the selected deal and month, then filter status and page forward and backward.
4. Open one record and confirm all 96 stored columns appear, including the 93 disclosure fields and three lineage columns.
5. Confirm loan identifier begins with `loan-` and ZIP3 begins with `geo-`; no original identifier or local path appears.
6. Rank by portfolio contribution, monthly change, D60+ level, and both roll-rate measures; review comparison, attribution, flows, definitions, and masking boundary.

## Verification

```bash
python3 -m unittest discover -s tests -v
.venv/bin/python scripts/evaluate_public_twin.py
.venv/bin/python scripts/build_release.py
```

The local workbench and release candidate do not support borrower-level decisions. Masked records are public descriptive evidence, and other field combinations may remain linkable to the original disclosure. The analytical scope is collateral surveillance, not tranche waterfall or investor cash-flow analysis.
