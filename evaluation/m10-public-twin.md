# M10 aggregate-only public twin evaluation

## Result

M10 passes locally. The public twin preserves the private workbench's portfolio pulse, deal watchlist, selected-deal comparison, exact D60+ driver attribution, delinquency flows, reference-pool view, governed definition, and evidence boundary using only reviewed aggregates from metric version `m8.1.0`.

This milestone does not change live Vercel deployment. Candidate remains local after M13 packaging; deployment and publication require separate approvals.

## Full-data basis and shared metric parity

- Source basis: all 20,439,666 accepted loan-period records in the authorized archive.
- Shared projection: 37 portfolio periods, 292 deal-period groups, and 292 reference-pool-period groups.
- Latest result: July 2026 D60+ is 1.27996%; monthly change is +4.7944 bp.
- Exact attribution: deal contributions sum to the portfolio D60+ monthly change; maximum engine variance remains 2.31e-14 bp.
- Automated parity tests compare the public latest portfolio and selected-deal values directly with the restricted DuckDB tables.

## Analyst filter contract

The public and private profiles use the same three controls:

1. Disclosure month, displayed as a readable month while retaining `YYYYMM` URL and metric keys.
2. Deal to investigate, limited to deals with an observation in the selected month.
3. Rank deals by one of five transparent measures: portfolio D60+ contribution, deal monthly D60+ change, D60+ level, Current-to-D30 roll rate, or D30-to-D60 roll rate.

The default is portfolio D60+ contribution because it answers which deal most affected the portfolio movement. The watchlist always exposes the selected measure, D60+ level, monthly change, D60+ UPB, rate effect, mix effect, and the exact prior-loan match state. There is no composite score.

## Public field boundary

The projection allowlists only portfolio-, deal-, flow-, decomposition-, reference-pool-, metric-definition-, source-scope-, and control fields required by the workflow. It excludes loan rows, identifiers, payment histories, borrower attributes, risk-layer rows, seller/servicer and geographic dimensions, local paths, and the restricted database.

`scripts/build_release.py` fails closed on the approved classification, public-release flag, prohibited keys, prohibited paths, and required boundary copy. The local bundle contains only:

- `index.html`
- `styles.css`
- `app.js`
- `data/public/crt_public_projection.json`
- `DEPLOYMENT.md`
- `manifest.json`

## Browser and accessibility verification

The private and public profiles were exercised in the in-app browser on 2026-08-09.

- Both profiles load and expose labelled controls, headings, captions, live status, keyboard-selectable watchlist rows, scrollable table focus targets, and text alternatives for the chart.
- Dynamic chart rendering preserves its accessible title and description.
- July 2023 narrows the deal selector to the five deals reported in that month in both profiles.
- Changing the rank metric changes the visible selected-measure column and URL state.
- The public profile has no row-detail or identifier control and explains the controlled-local boundary.
- No console warning or error was observed.

The first design review scored 28/40 before correction. The post-change review returned no remaining findings for `app/index.html` or `private_app/index.html`.

## Performance and cost

- Public projection size: 305,060 bytes, or 15.3% of the 2 MB split trigger.
- Public load: four static requests (HTML, CSS, JavaScript, projection); no database, API, serverless function, or paid runtime.
- Private initial workflow: bootstrap 20.85 ms, overview 19.87 ms, and deal detail 18.63 ms in focused loopback measurements.
- Restricted rows: the 315.40 ms query is removed from initial load and occurs only after the explicit local-access action.

The single-file static projection is the smallest credible architecture at 292 deal-period groups. Split projection files by month only if the uncompressed projection exceeds 2 MB or materially impairs measured browser load. Do not introduce a cloud database or API until concurrent access, scheduled shared refresh, governed multi-user access, or measured local capacity creates that requirement and the owner approves cost and exposure.

Chrome DevTools performance tracing was not configured in this environment, so Core Web Vitals were not claimed. M10 uses request composition, payload size, repository timings, browser behavior, and console state as its proportional evidence; M11 retains the full performance and accessibility evaluation gate.

## Limitations

- Descriptive surveillance is not a forecast, causal estimate, investment recommendation, or borrower decision.
- Flow rates are aggregate and do not expose transition counts in the public projection.
- Risk-layer and loan-level investigation remain available only in the controlled local profile.
- The current public projection is a local release candidate, not the deployed site.
