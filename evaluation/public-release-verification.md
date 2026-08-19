# Public release verification

Status: historical verification of the currently live legacy aggregate release. The M10 local candidate is separate and undeployed; use `evaluation/m10-public-twin.md` for current development evidence.

- Verified on: 2026-08-05
- Production URL: https://freddie-mac-crt-disclosure-analytic.vercel.app
- Vercel deployment: `dpl_G9fQVx6LPAwRdAwgkH1ZwmvDTnYP`
- Release type: `static-aggregate-crt-demo`
- Public aggregate source: 292 standard monthly loan-level disclosures streamed locally into 292 aggregate reference-pool groups.
- Public inputs verified: dashboard HTML, aggregate CSV, aggregate intake manifest, release manifest, and evaluation artifacts.
- Restricted archive verified absent: `data/restricted/` does not appear in the deployed manifest.

The canonical production URL returned HTTP 200. Its page no longer contains the stale synthetic/local-only release claims; its public manifest identifies `static-aggregate-crt-demo`, includes the aggregate CSV, file-level quality report, and release receipt, and contains no restricted path. The public quality report confirms 292 accepted standard monthly files and passing fallback reconciliation. The locally retained archive and all row-level records remain excluded.

## Phase 2 deployment status

The rebuilt bundle with `real_intake_quality_report.json` and `real-release-receipt.json` is now published. The regression test rejects synthetic/local-only claims whenever real aggregates are included. This release remains limited to reference-pool D30+/D60+/current-UPB analytics.
