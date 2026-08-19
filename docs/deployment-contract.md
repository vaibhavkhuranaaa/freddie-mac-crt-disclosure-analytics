# Public masked full-record release contract

## Live release

- URL: https://freddie-mac-crt-disclosure-analytic.vercel.app
- Provider: Vercel
- Release type: `public-full-record-crt-workbench`
- Current hosted verification: `evaluation/full-record-public-release.md`
- Historical release verification: `evaluation/public-release-verification.md`

The full-record revision was promoted to production on 2026-08-18. It uses the existing Vercel project, a private R2 bucket, and an authenticated GET-only Worker. Production deployment `dpl_AmsfPoLKBjHUrgkhhL5NBhHr8GVE` is live; prior P9 deployment `dpl_92yPJkaDxdwTNtm7iYirJNiTmVvt` remains the rollback target.

## Permitted public inputs

- Static dashboard HTML, CSS, and JavaScript.
- Reviewed aggregate projection (`data/public/crt_public_projection.json`).
- Masked full-record Python query function and its DuckDB runtime dependency.
- Private immutable Parquet objects classified `public-full-record-masked`.
- Server-side `CRT_DATA_GATEWAY_URL` and `CRT_DATA_GATEWAY_TOKEN` environment variables.
- Deployment contract and deterministic release manifest.

The public release must not contain the restricted ZIP, original loan identifier, original ZIP3, masking key, credentials, direct object-storage URL, local paths, or an unmasked row-level derivative. The R2 bucket must not expose an `r2.dev` or custom public domain.

## Release checks

1. Build `dist/` using `python3 scripts/build_release.py`.
2. Verify `dist/manifest.json` identifies `public-full-record-crt-workbench` and lists only the client, `api/records.py`, `requirements.txt`, `vercel.json`, public projection, and `DEPLOYMENT.md`.
3. Verify the masked release manifest reports 20,439,666 rows, 292 assets, and 96 stored columns. Scan every row for valid `loan-` and `geo-` tokens.
4. Verify the R2 bucket is private, the Worker has read-only behavior, anonymous requests fail, invalid paths fail before R2 access, and bucket listing is unavailable.
5. Run the complete tests, local API checks, accessibility scan, responsive browser workflow, and full-record evaluation before release review.
6. Verify a preview cold request and cached request before promoting that exact candidate.
7. Verify the production alias, headers, API response, record-detail interaction, raw-identifier exclusion, secret exclusion, and rollback target after promotion.

## Known release gaps

- No Firefox, Safari, assistive-technology session, field-vitals, or representative-user evidence exists.
- Portfolio-site application, future cloud-resource changes, and paid spend remain separately gated.
- Exact source attestation remains in the private operations record; deployment identifiers are recorded in the hosted release evaluation.
