# Decision 0012: publish the masked full-record register

## Decision

Replace the aggregate-only public boundary with an unauthenticated full-record register. Preserve all 20,439,666 accepted loan-period rows and all 93 disclosure fields. Replace loan identifier and ZIP3 offline with stable keyed tokens before any public asset is created.

## Why

Aggregate measures alone do not provide enough evidence for real collateral-surveillance investigation. The complete disclosure register lets a reviewer inspect the records behind a measured exception while keeping the direct identifier boundary explicit.

## Controls

- The masking key remains local under `data/restricted/` and never enters Git, a release asset, the deployment bundle, or a function environment variable.
- Public Parquet assets contain masked loan identifier and masked ZIP3 only.
- The public query validates a fixed deal and month format, reads one partition, caps the response at 50 rows, and caps the offset.
- Derived aggregate measures remain for navigation and reconciliation, not as a substitute for record evidence.
- The interface warns that other disclosed field combinations may remain linkable to the original source.
- Re-identification, outside-data matching, and borrower decisioning remain out of scope.

## Consequences

The public release includes a bounded runtime function backed by separately stored masked Parquet assets. Decision 0013 defines the private serving boundary. Privacy, correctness, browser, and hosted checks passed on 2026-08-18; the earlier P9 aggregate deployment remains the rollback target.
