# Private masked-data serving runbook

## Purpose

This runbook covers the masked full-record serving path only. It does not authorize provisioning or publication. The required human gate covers the R2 bucket, Worker, secret creation, object upload, Vercel environment changes, preview deployment, production promotion, and any paid spend.

## Fixed resources

- R2 bucket: `freddie-mac-crt-disclosure-data`
- Worker: `crt-data-gateway`
- R2 binding: `CRT_DATA`
- Release prefix: `full-data-v2026-07/`
- Local reviewed source: `data/public/full-data/`
- Vercel server variables: `CRT_DATA_GATEWAY_URL` and `CRT_DATA_GATEWAY_TOKEN`

Use R2 Standard storage. Keep the bucket private. Do not enable an `r2.dev` URL or custom public domain.

## Current deployment receipt

- R2 bucket created in ENAM with Standard storage on 2026-08-18; no public bucket endpoint configured.
- Worker origin: `https://crt-data-gateway.vaibhavkhuranaaa.workers.dev`
- Worker secret-change version: `6fcda102-4045-42ea-8cf4-9a5d1450d6f8`
- Verified preview: `dpl_74S61hXpVUTV2QHhY3DN3by4CzJE`
- Production: `dpl_AmsfPoLKBjHUrgkhhL5NBhHr8GVE`
- Rollback: `dpl_92yPJkaDxdwTNtm7iYirJNiTmVvt`
- Incremental cost: $0. The Worker remains on the Free plan with a 100,000-request daily ceiling.

## Preflight

1. Run the Python suite, gateway tests, full-record evaluation, and release build.
2. Confirm the local manifest reports 20,439,666 rows, 292 Parquet assets, 96 columns, and 894,590,461 asset bytes.
3. Confirm every manifest asset exists and matches its recorded byte size.
4. Confirm the explicit infrastructure and publication approval is recorded.

## Provision and configure

1. Create the private R2 Standard bucket in Eastern North America.
2. Generate one random 32-byte token without printing it to logs or writing it into the repository.
3. Store the token as the Worker secret `DATA_GATEWAY_TOKEN`.
4. Store the same token as Vercel `CRT_DATA_GATEWAY_TOKEN` for preview and production.
5. Deploy the Worker with the checked-in R2 binding.
6. Store the resulting Worker origin as Vercel `CRT_DATA_GATEWAY_URL` for preview and production.

## Upload and verification

1. Upload each Parquet file under the immutable release prefix, then upload `manifest.json`.
2. Compare object count and byte sizes with the local manifest.
3. Verify an anonymous Worker request returns 401.
4. Verify an invalid authenticated path returns 404.
5. Verify one authenticated object request returns the expected content length and ETag.
6. Deploy a Vercel preview. Verify one cold record query, one repeated query, pagination, all 96 detail fields, raw-identifier exclusion, and browser error logs.
7. Promote only the exact verified preview. Keep the prior P9 deployment identifier as rollback target.

## Rollback

If hosted verification fails, restore the prior P9 production deployment. Do not delete the bucket or release objects during incident response. Disable the Worker route or rotate the gateway token if the credential boundary is in doubt. Record the failure and recovery evidence before another promotion attempt.

## Rotation

Create a new random token, set it on the Worker, update Vercel preview and production, deploy both services, verify a record request, and then retire the prior token. Never place either token in source control, screenshots, shell history, or release evidence.
