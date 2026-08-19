# M7 full-data foundation evaluation

Status: verified locally on 2026-08-09. Restricted row-level outputs are excluded from Git and public deployment.

## Build result

| Check | Verified result |
| --- | --- |
| Source archive integrity | Verified in private intake record |
| Standard monthly files | 292 accepted; 13 non-standard members excluded |
| Loan-period rows | 20,439,666 |
| Deals / reporting periods | 10 / 37, from 2023-07 through 2026-07 |
| Source widths | 5,988,012 rows with 89 fields; 13,770,891 with 90; 680,763 with 93 |
| Full fields retained | 93 official positions plus three lineage columns |
| Restricted partitions | 292 Zstandard-compressed Parquet files |
| Restricted layer size | 633 MB on the verified local filesystem |
| Runtime | 185,376.353 ms |
| Within-file duplicate pool/loan keys | 0 |
| Existing intake reconciliation | Pass: 292 files and 20,439,666 records exactly |
| Public-release permission | False; exclusion check passed |

Build command:

```bash
uv sync
uv run python scripts/build_full_data_layer.py \
  data/restricted/fre-crt-2023-07-2026-07.zip
```

## Schema and lineage controls

- The builder accepts only 89-, 90-, and 93-field rows, validates period against the member name, requires pool and loan identifiers, and rejects duplicate loan identifiers within a reference pool/file.
- Historical trailing fields are null-padded to the 93-position v4.2 contract without shifting any position.
- Each Parquet row carries deal, exact source member, and original field count. Restricted manifest binds every partition to private integrity evidence, record count, and file size.
- The build is staged under the restricted root and atomically promoted only after all partitions and full-archive reconciliation pass.
- Existing output is never overwritten by the M7 builder. Incremental/replacement behavior is intentionally deferred to M12.

## Selected full-field coverage

| Field | Non-null rows |
| --- | ---: |
| Loan Identifier | 20,439,666 |
| Classic FICO | 20,439,666 |
| Payment History | 20,439,666 |
| Current Actual UPB | 20,439,666 |
| Zero Balance Code | 1,899,656 |
| Modification Flag | 66,783 |
| Payment Deferral Flag | 112,921 |
| Temporary Subsidy Buydown Plan Type | 14,451,654 |
| VantageScore 4.0 | 680,763 |
| Actual Loss | 572 |
| Cumulative Modification Costs | 680,763 |

These are availability counts, not analytical results. Sentinel and applicability semantics remain field-specific.

## Verification

- Focused builder tests cover all three approved widths, trailing null-padding, public-release metadata, and fail-closed handling of an 88-field row.
- An independent DuckDB scan of all partitions returned 20,439,666 rows, 292 source members, 10 deals, and 37 periods.
- `data/restricted/` remains ignored. The public build manifest contains no restricted path or full-data asset.

## Limitations and next gate

- M7 preserves source values as nullable strings. Typed casting, semantic sentinel handling, reference-pool construct mapping, metric populations, and business calculations are M8 work.
- Aggregate-postal-code and other non-standard members remain separate; they are not mixed into the loan-period layer.
- Official file-level totals were unavailable. M7 therefore reconciles to the separately verified full-archive aggregate intake, not to an official source-total file.
- Updated credit-score fields remain terms-gated. No new public output, dashboard capability, or metric claim is authorized by M7.
