# Real aggregate release evaluation

Status: historical evaluation for the currently live legacy aggregate release. The full-data M8 engine and M10 local candidate have separate, newer evidence and do not change this receipt.

## Scope and coverage

| Check | Result |
| --- | --- |
| Source archive | `fre-crt-2023-07-2026-07.zip` |
| Intake scope | All standard monthly `*_lld.txt` files in the authorized archive |
| Standard monthly files accepted | 292 |
| Other or ambiguous archive members rejected | 13; non-standard monthly layouts are excluded from this metric |
| Aggregate groups | 292 |
| Unique deal / period / pool keys | 292; duplicates detected: 0 |
| Deals | 10 |
| Reporting periods | 37, from 2023-07 through 2026-07 |
| Source records aggregated | 20,439,666 |
| RA statuses excluded from D30+/D60+ | 6,433 |
| XX statuses excluded from D30+/D60+ | 0 |
| Raw row-level fields retained in derived output | 0 |
| Zero-UPB records | File-level counts retained in `data/derived/real_intake_quality_report.json`; zero-UPB pools receive a 0 rate rather than division by zero |
| Intake runtime | 76,584.436 ms |

## Controls verified

- The deployed manifest identifies `static-aggregate-crt-demo` and lists only static files, aggregate output, and release evidence.
- The aggregate output has no duplicate deal/reporting-period/reference-pool key.
- D30+/D60+ calculations use only the documented four standard-layout fields.
- The release excludes `data/restricted/` and the full ZIP.
- The file-level quality report records accepted/rejected source members, per-file records, RA/XX status counts, zero-UPB counts, duplicate/revision decisions, and contiguous reporting periods from 2023-07 through 2026-07.
- No official file-level source totals accompanied the authorized archive. The documented fallback reconciles every accepted file's record count to aggregate output and validates `D60+ UPB <= D30+ UPB <= current UPB`; it passed. The adapter accepts an official JSON total file and rejects a mismatch (covered by test).

## Limitations

This is reference-pool D30+/D60+/current-UPB analytics, not tranche waterfall, cash-flow, loss-allocation, prepayment, or borrower-level analytics. Official source totals remain unavailable for this archive, so the fallback reconciliation is not a substitute for an official-total comparison. The revised-disclosure policy rejects ambiguous same-deal/same-period candidates until an approved canonical revision is supplied.
