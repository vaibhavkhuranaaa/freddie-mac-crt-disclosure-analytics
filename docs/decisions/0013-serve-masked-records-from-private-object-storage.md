# Decision 0013: serve masked records from private object storage

## Decision

Store the 292 immutable masked Parquet assets in a private Cloudflare R2 Standard bucket. Bind that bucket to a small Cloudflare Worker that accepts only authenticated GET requests for the fixed release and deal-month asset pattern. Keep the Vercel record API public to users, but require it to authenticate to the Worker before retrieving one partition.

## Why

Repository releases couple operational data to source-code publication and make the complete Parquet collection directly downloadable. Vercel Blob would keep the stack smaller, but the 894,590,461-byte dataset consumes about 89.5 percent of its 1 GB Hobby storage allowance before growth, replacements, or rollback copies.

R2 provides a distinct data lifecycle, more storage headroom, and no egress charge. A private bucket and narrow gateway keep object locations and credentials out of the browser while preserving unauthenticated access to bounded record pages.

## Controls

- The bucket has no public `r2.dev` or custom-domain endpoint.
- The Worker binding can read the bucket but the HTTP interface exposes no list, write, delete, or arbitrary-path operation.
- One shared random token is stored only as a Worker secret and Vercel server-side environment variable.
- The Vercel API permits one validated deal-month asset per request, a maximum 50-row response, and a maximum 150,000-row offset.
- The browser receives records and field names, never an R2 URL, Worker token, or Parquet object.
- Release assets remain immutable under the `full-data-v2026-07/` prefix.

## Rejected alternatives

- GitHub Releases: wrong lifecycle boundary and direct bulk distribution.
- Public R2 endpoint: Cloudflare documents `r2.dev` as a non-production, rate-limited path, and it would bypass the gateway.
- Vercel Blob: insufficient growth and rollback headroom on the existing allowance.
- R2 SQL or a hosted analytical database: adds a query system before measured traffic or latency requires one.

## Consequences

The system gains one small Worker and one secret pair. The approved bucket, upload, Worker, Vercel configuration, preview, and production promotion completed on 2026-08-18 with $0 incremental cost. The Workers Free plan supplies a hard 100,000-request daily ceiling. Future provisioning, uploads, environment changes, deployments, or paid spend remain human approval gates. The P9 deployment is retained as the rollback target.

## References

- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Cloudflare R2 public bucket guidance](https://developers.cloudflare.com/r2/buckets/public-buckets/)
- [Vercel Blob usage and pricing](https://vercel.com/docs/vercel-blob/usage-and-pricing)
