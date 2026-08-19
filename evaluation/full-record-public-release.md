# Masked full-record public release evaluation

## Scope

This evaluation owns the revision from the historical aggregate-only P9 release to an unauthenticated masked full-record workbench. It does not replace historical M7-M13 evidence.

## Local evidence

| Check | Result | Status |
| --- | --- | --- |
| Record preservation | 20,439,666 manifest rows and 20,439,666 complete-scan rows | Pass |
| Partition preservation | 292 manifest assets and 292 complete-scan deal-month groups | Pass |
| Field coverage | 93 disclosure fields plus three lineage columns | Pass |
| Loan identifier masking | Zero invalid tokens across the complete public row scan | Pass |
| ZIP3 masking | Zero invalid tokens across the complete public row scan | Pass |
| Stable masking | Same source identifier produces the same keyed token across periods in automated tests | Pass |
| API boundary | Deal and period formats, status values, page size, offset, and missing assets are rejected safely | Pass |
| Storage boundary | API has no repository-release fallback; missing gateway configuration fails closed | Pass |
| Gateway boundary | Anonymous and invalid requests fail before R2 access; valid requests resolve one exact immutable object | Pass |
| Page response | At most 50 records; every stored field returned for each selected record | Pass |
| Raw boundary | Raw archive, original identifiers, masking key, local paths, and metric DB are excluded | Pass |
| Automated tests | 38 Python tests and 4 gateway tests passed | Pass |
| Desktop browser | Real values appear in the first viewport; 25 masked rows load; 96-field detail and pagination work | Pass |
| Mobile browser | 390 px layout has zero body overflow and keeps the measured value in the first viewport | Pass |
| Accessibility | Zero automated WCAG A/AA violations on desktop and mobile; contrast remains a documented manual review item | Pass |
| Browser runtime | No page errors, console messages, or framework error overlay | Pass |
| Design detector | No blocking anti-pattern; responsive type-ramp advisories were incorporated into `DESIGN.md` | Pass |

## Hosted release evidence

| Check | Result | Status |
| --- | --- | --- |
| Private storage | R2 Standard bucket `freddie-mac-crt-disclosure-data` created in ENAM; no public bucket endpoint configured | Pass |
| Complete upload | 292 manifest-validated Parquet assets totaling 894,590,461 bytes uploaded; `manifest.json` uploaded last | Pass |
| Worker boundary | Anonymous valid-object request returned 401; authenticated request returned 200; invalid paths and non-GET methods are rejected | Pass |
| Object parity | Hosted `2022-HQA1--202307.parquet` returned 6,102,023 bytes and SHA-256 `7b7399b0c96e5976daf681452f3e3a28e0a09bc43ac631751a12f85fccd8ca46`, identical to the reviewed local asset | Pass |
| Worker deployment | `crt-data-gateway` secret-change version `6fcda102-4045-42ea-8cf4-9a5d1450d6f8`; 4 ms measured startup on initial upload | Pass |
| Server secrets | Gateway URL and token exist as Sensitive Vercel variables in Preview and Production; no value is present in source or browser assets | Pass |
| Preview | Vercel preview `dpl_74S61hXpVUTV2QHhY3DN3by4CzJE` reached Ready and passed the complete browser and API flow | Pass |
| API response | Hosted Jul 2026 query returned classification `public-full-record-masked`, 143,457 records, 96 fields, and valid `loan-` and `geo-` tokens | Pass |
| Cached request | Production API returned HTTP 200 with `x-vercel-cache: HIT`; the public page also returned HTTP 200 | Pass |
| Browser workflow | Production rendered 1-25 of 143,457, paginated to 26-50, and opened a detail region containing 96 field terms | Pass |
| Browser runtime | Zero application warnings or errors in the production Chromium session | Pass |
| Security headers | Production returned CSP, HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, COOP, CORP, Permissions Policy, and Referrer Policy | Pass |
| Production | Deployment `dpl_AmsfPoLKBjHUrgkhhL5NBhHr8GVE` reached Ready and owns `freddie-mac-crt-disclosure-analytic.vercel.app` | Pass |
| Rollback | Prior Ready P9 deployment `dpl_92yPJkaDxdwTNtm7iYirJNiTmVvt` retained | Pass |
| Runtime logs | Vercel production error scan returned no errors after hosted verification | Pass |
| Incremental cost | $0. R2 remains within its free tier, Vercel uses existing capacity, and Workers Free enforces 100,000 requests per day | Pass |

## Limitations

The tokens remove original loan identifier and ZIP3 values, but combinations of other disclosed fields may remain linkable to the original Freddie Mac disclosure. The product is descriptive collateral-surveillance evidence, not a borrower decisioning system, investment recommendation, forecast, or causal estimate.
