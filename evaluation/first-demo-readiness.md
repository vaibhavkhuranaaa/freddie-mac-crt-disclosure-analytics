# Release readiness packet

**Status:** Historical M5 live-release readiness packet. The verified M10 local candidate supersedes it for current development evidence; the legacy Vercel release itself remains live and unchanged.

Current successor evidence: `evaluation/m10-public-twin.md` and `data/derived/m10_public_twin_evaluation.json`.

## Live scope

The dashboard uses aggregate results derived from the complete authorized Clarity ZIP. It supports deal and reporting-period filtering for D30+, D60+, current-UPB, and aggregated-record-count review at reference-pool level.

It does not claim tranche waterfall, credit-event, prepayment, loss-allocation, investor-cash-flow, or borrower-level analytics.

## Verified release evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Production health | HTTP 200 | `evaluation/public-release-verification.md` |
| Public source classification | Approved real aggregate disclosure | `dist/manifest.json` |
| Restricted source exclusion | Pass | Public manifest omits `data/restricted` |
| Real aggregate coverage | 292 groups from 292 standard monthly files | `evaluation/real-release-evaluation.md` |
| Automated tests | Pass, 8 tests | `python3 -m unittest discover -s tests -v` |
| Historical synthetic regression | Pass, 10 rows / 4 groups | `evaluation/report.md` |

## Known limitations and next delivery

The legacy live release has no official file-level total comparison because the archive did not supply official totals and has no public Git revision attestation. M7 verifies restricted 89/90/93-field foundation, M8 verifies metric semantics, M9 verifies private full-data workflow, M10 verifies aggregate-only public twin and deliberate restricted state locally, and M11 verifies technical usability, accessibility, browser, security, performance, and analytical quality. No independent user study was performed. M10 candidate has not replaced live deployment. Tranche cash-flow analytics remain outside product contract.

## Rollback

Use the Vercel deployment record to remove or revert the public static release. The restricted archive remains local and is never part of the deployed artifact.
