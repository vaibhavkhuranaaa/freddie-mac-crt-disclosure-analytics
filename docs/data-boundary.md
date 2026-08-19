# Data boundary and representative baseline

## Purpose

This document controls the historical synthetic baseline, private source layer, and public masked full-record release. It distinguishes the committed test fixture, completed authorized Freddie Mac disclosure intake, offline masking boundary, and public query assets.

## Baseline fixture

`tests/fixtures/crt_aggregate_fixture.csv` is a synthetic, deal-level aggregate fixture. It is not a Freddie Mac disclosure file and it contains no borrower, household, property, loan, account, or record-level information.

The fixture models the minimal fields needed to test the analytical contract:

| Field | Purpose | Public-demo status |
| --- | --- | --- |
| `reporting_period`, `deal_id`, `program` | Reporting and transaction context | Permitted synthetic example |
| `reference_pool_upb`, `delinquent_upb`, `prepayment_upb`, `credit_event_upb` | Aggregate pool performance | Permitted synthetic example |
| `tranche`, `attachment_pct`, `detachment_pct`, `tranche_notional` | Tranche structure | Permitted synthetic example |

## Completed approved-source intake

Current intake record is `data/derived/real_intake_manifest.json`. It records private source identity, layout version, terms reference, standard-file coverage, and aggregate groups. Complete archive remains in `data/restricted/` and is ignored by Git.

Any replacement source package must record:

1. Exact official URL, source name, reporting period, access date, and private integrity record.
2. Exact applicable terms version and the approval evidence authorizing the intended local use and public masked full-record release.
3. Direct-identifier masking policy, retained fields, and Updated FICO Score handling decision.
4. Retention date, access owner, storage location, and deletion/review procedure.
5. Public-output policy, including masking, linkage warning, source attribution, and reviewer.

`data/restricted/` is ignored by Git. No restricted source file, original direct identifier, masking key, credential, or local path may enter version control or public assets. Private R2 Parquet objects preserve the disclosed rows after loan identifier and ZIP3 replacement. The Vercel bundle contains the client, derived summary projection, and bounded query function, but not the Parquet objects, raw archive, masking key, gateway token, or storage URL.

## Private full-data authorization

On 2026-08-04 the project owner approved full authorized Clarity loan-level processing and row-level analyst access in a controlled private environment. On 2026-08-18 the owner explicitly approved unauthenticated use of the complete disclosure data after PII and direct-identifier masking. This permits public masked row-level assets and a public record query. Raw source files, original loan identifiers, original ZIP3 values, the masking key, and local paths remain excluded.

## Non-negotiable controls

- No joining, enrichment, matching, or correlation with person-, household-, address-, property-, or consumer-identifying data.
- No borrower-level lending, underwriting, pricing, marketing, servicing, or credit-granting use.
- Stable masked tokens support within-release continuity only; attempts to reverse, map, or enrich them are prohibited.
- No scraping, automated collection, or API use without source-specific written authorization.
- No direct public object-storage endpoint or bucket listing.
- No external release before the exact output and attribution have passed the recorded publication review.
