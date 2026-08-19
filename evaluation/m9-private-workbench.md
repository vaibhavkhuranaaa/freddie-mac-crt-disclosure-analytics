# M9 private analyst workbench evaluation

Status: verified locally on 2026-08-09. M9 is complete; no public bundle or deployment changed.

Current-interface note: M10 aligned both surfaces to five visible rank measures, portfolio contribution as the default, readable disclosure months, period-valid deals, and explicit on-demand restricted-row loading. The walkthrough below is the frozen M9 verification record; use `evaluation/m10-public-twin.md` for the current shared interaction contract.

## Decision result

The private workbench turns metric version `m8.1.0` into a complete collateral-surveillance workflow over the full restricted foundation. At 2026-07, portfolio D60+ was **1.27996%**, up **4.7944 bps** month over month. `2026-HQA1` had the largest deal-level D60+ increase at **+8.9204 bps**, while `2022-HQA1` made the largest contribution to portfolio deterioration at **+1.2360 bps** because its exposure weight was materially larger. This distinction is the product decision: rank observed deterioration transparently, then use exact contribution analysis to identify what moved the portfolio.

The result is descriptive collateral surveillance. It does not establish causality, forecast loss, model a CRT tranche, recommend an investment, or support a borrower-level decision.

## Verified technical walkthrough

Implemented technical walkthrough covers approved sequence locally:

1. Open the latest period and read eligible UPB, D60+ level, monthly change, and largest worsening contributor.
2. Rank ten deals by monthly D60+ change, rate effect, D60+ level, flow pressure, credit-event exits, or assistance exposure. No composite score is used.
3. Select a watchlist row with pointer or keyboard and compare its keyed history with the eligible-UPB-weighted portfolio.
4. Reconcile signed rate and mix contributions to the exact portfolio change.
5. Inspect current-to-D30, D30-to-D60, cure, payoff, credit-event, modification, risk-layer, and reference-pool evidence.
6. Filter authorized loan-period rows. Identifiers are masked by default and revealed only through an explicit restricted control.
7. Inspect the metric catalog, population, exclusions, version, controls, and limitations in the attached evidence rail.
8. Export a nonpublic evidence JSON package that excludes loan rows and identifiers.

## Full-data verification

Machine evidence is retained in `data/derived/m9_workbench_evaluation.json`.

| Gate | Verified result |
| --- | --- |
| Metric source | Read-only 4.8 MB restricted DuckDB with private integrity verification |
| Coverage | 37 reporting periods, 10 deals, 19 governed metrics, 20,439,666 underlying loan-period rows |
| Walkthrough population | 2022-HQA1 at 2026-07; 143,457 permitted loan-detail rows |
| Watchlist | All ten current deals returned with level, change, affected UPB, drivers, flow, and evidence state |
| Decomposition | Rate plus mix differs from portfolio monthly change by `5.33e-15` bp |
| Transition evidence | Selected-deal flow view present with 100% adjacent-period loan match |
| Loan boundary | Masked identifiers by default; explicit reveal supported; evidence export contains no loan rows or identifiers |
| Public boundary | Existing `dist/manifest.json` contains no private app, restricted database, identifier, or restricted metric path |

## Performance

The M9 budget is at most 5,000 ms for a first local interaction and 2,000 ms warm.

| Query | First measured | Warm median | Warm maximum |
| --- | ---: | ---: | ---: |
| Bootstrap and metric catalog | 12.51 ms | 10.27 ms | 11.45 ms |
| Portfolio and watchlist | 12.99 ms | 12.77 ms | 14.61 ms |
| Selected deal workflow | 14.39 ms | 13.48 ms | 14.32 ms |
| 50-row loan-detail page from 143,457 rows | 385.27 ms | 385.81 ms | 397.85 ms |
| Evidence package | 32.71 ms | 27.69 ms | 29.90 ms |

Browser resource timing on the verified local session recorded 13.3 ms bootstrap, 13.6 ms overview, 17.5 ms selected deal, and 191.7 ms first loan page. These are local-machine measurements, not hosted-service claims.

## Interface and control checks

- Chromium loaded the workbench with meaningful content, no framework overlay, and no browser errors.
- Keyboard Enter on the first watchlist row changed the selected deal and URL-addressable filter state.
- The 390 x 844 responsive view had no body overflow; wide analytical tables remained locally scrollable.
- Every chart has an accessible table or summary, controls have labels and visible focus states, and reduced-motion behavior is defined.
- Loading, no-match, no-prior-period, restricted, success, and calculation-error states name a recovery path.
- The service binds only to `127.0.0.1`, opens DuckDB read-only, refuses databases outside `data/restricted/`, and sends no-store, CSP, frame, referrer, content-type, and permissions headers.
- Static assets are served only from `private_app/`; repository files and restricted database files are not reachable as static paths.

## Limitations

- This is a controlled local application, not authenticated multi-user infrastructure. It must not be exposed beyond loopback.
- Identifier reveal is authorized locally but should not be captured in screenshots, recordings, or evidence exports.
- Actual Loss rate remains unavailable because July 2026 is the first disclosed archive period with that field.
- Usability verification in M9 is an implemented workflow and technical/browser check. No independent user study was performed, so no representative-usability claim is made.
- M10 subsequently completed separately reviewed aggregate projection and public twin locally. Candidate remains undeployed after M13 local packaging pending separate deployment and publication approvals.
