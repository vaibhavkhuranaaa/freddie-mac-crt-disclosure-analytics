# Static aggregate legacy release

## Decision

Publish only reviewed deal-period aggregates as static files on existing Vercel free capacity.

## Why

Static serving matched public data boundary, removed runtime database exposure, kept cost at zero, and preserved simple rollback.

## Alternatives rejected

- Hosted database or API: no public query need and larger exposure surface.
- Publish raw disclosure rows: prohibited by product boundary.

## Not done

No restricted input, identifier, loan row, secret, or paid resource entered release.

## Changed

Established verified legacy public release and deployment evidence for M4 and M5.
