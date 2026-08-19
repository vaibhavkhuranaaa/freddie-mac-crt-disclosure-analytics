# Approved real-data intake

## Official source

Use the official Freddie Mac Clarity Data Download route for a CRT Reference Pool loan-level disclosure file. The supported layout is **Reference Pool Disclosure File Layouts, Version 4.2, effective July 2026**. The file is pipe-delimited and has no column header.

The adapter reads only these layout positions:

| Position | Official field | Adapter use |
| --- | --- | --- |
| 1 | Period | Aggregate reporting period |
| 2 | Reference Pool Number | Aggregate pool identifier |
| 37 | Current Loan Delinquency Status | D30+ and D60+ aggregate categorization |
| 40 | Current Actual UPB | Aggregate current UPB and delinquent UPB |

The adapter does **not** retain or emit Loan Identifier, FICO/credit-score, postal code, seller, servicer, property, borrower, or other fields. It derives aggregates in a single pass. The complete authorized ZIP remains local and ignored; the approved aggregate CSV and its lineage manifest are included in the public release.

## Private full-data foundation

The aggregate adapter above remains the public-release path. Separately, the owner-approved M7 workflow runs:

```bash
uv run python scripts/build_full_data_layer.py \
  data/restricted/fre-crt-YYYY-MM-YYYY-MM.zip
```

This controlled local builder retains all 93 official positions as source-faithful nullable strings in partitioned Parquet under `data/restricted/full-data/`. It accepts only observed 89/90/93-field layouts, null-pads missing trailing positions, validates deal-period/loan keys, records private partition integrity, and reconciles full row count to verified aggregate intake. It is never a public build input. See `docs/data-dictionary.md` and `evaluation/m7-full-data-foundation.md`.

## Manual intake steps

1. Download the approved Clarity ZIP through Clarity.
2. Place it in `data/restricted/`; do not rename it before recording private source identity.
3. Record source URL, archive name, terms version, access date, retention date, and private integrity value in project private intake record.
4. Run:

```bash
python3 scripts/intake_clarity_archive.py \
  data/restricted/fre-crt-YYYY-MM-YYYY-MM.zip
```

5. Review `data/derived/real_aggregate.csv` and `data/derived/real_intake_manifest.json`. Publish only after release review confirms aggregate-only content and an exact deployment manifest.

## File-level quality and reconciliation

Each archive run writes `data/derived/real_intake_quality_report.json`. It contains only file-level operational evidence: accepted/rejected member names and reasons, record counts, aggregate groups, zero-UPB record counts, delinquency-status counts (including RA and XX), reporting-period continuity, duplicate/revision decisions, aggregate fallback reconciliations, and runtime. It never contains loan rows or row-level identifiers.

- A same-deal/same-file-period duplicate is treated as an ambiguous revised disclosure and every candidate is rejected. A canonical revision may be selected only after an approved official source identifies it; the adapter never silently selects one.
- If official file-level totals are available, pass a JSON file with `file_name`, `records`, and optionally `current_upb` using `--official-totals`; any mismatch rejects that file.
- The currently retained archive did not include official file-level totals. The report says `tested-unavailable` and proves fallback checks: accepted-file records reconcile to aggregate records and `D60+ UPB <= D30+ UPB <= current UPB`.
- Zero-UPB records remain counted. Their aggregate rate is reported as `0.0` to avoid a divide-by-zero claim.

## Metric definition

- `d30_plus_upb`: Current Actual UPB with a numeric Current Loan Delinquency Status of 1 or higher.
- `d60_plus_upb`: Current Actual UPB with a numeric Current Loan Delinquency Status of 2 or higher.
- `current_upb`: Sum of Current Actual UPB across all valid records.

`RA` and `XX` are counted separately and excluded from D30+/D60+ amounts. This adapter does not calculate prepayment, credit-event, tranche waterfall, loss-allocation, or investor-cash-flow measures because those require additional source fields, definitions, and validation.
