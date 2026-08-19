# Approved Clarity download selection

## Selected cohort

This was the initial portal selection used to obtain the approved package. The local restricted area retains the complete downloaded archive; the current intake processes every standard monthly loan-level disclosure (`*_lld.txt`) in that archive, rather than enforcing this cohort as a source gate.

| Portal filter | Exact selection |
| --- | --- |
| Deal Name | `2022-HQA1`, `2022-HQA2`, `2022-HQA3`, `2023-HQA1`, `2023-HQA2`, `2023-HQA3` |
| Deal Type | `High LTV` |
| Series Year | `2022`, `2023` |
| Disclosure Type | `Monthly` |
| Period Start | `Jul 2023` |
| Period End | `Jul 2026` |

The Clarity CRT Data Download UI returned **217 files** for these exact selections on 2026-08-01. The downloaded authorized ZIP ultimately contained **292 standard monthly loan-level files** across **10 deals** and **37 reporting periods** after related issuance additions were included. The intake manifest is the authoritative record of processed standard-layout files.

## Why these filters were used for acquisition

- Six related deals support cross-deal comparisons rather than a single-deal anecdote.
- A 37-month reporting window supports trend, delinquency-migration, and seasoning views.
- The cohort excludes unrelated deal types and issuance-only records, keeping the project focused on realized monthly reference-pool performance.
- The portal also includes new-issuance and supplementary files in the returned package; they are retained locally with the authorized archive.

## Browser procedure

1. Open **Clarity → CRT Data → Custom Download**.
2. Apply the exact filters in the table. Confirm that the page displays **217 files** (or record the current count if the portal has refreshed).
3. Before downloading, confirm the active terms, the download timestamp, the selected deal list, and the displayed file count in the project intake record.
4. Download the package manually. Do not publish or commit its contents.
5. Retain the complete package beneath `data/restricted/`. Do not publish or commit it.
6. Run the archive intake without a deal filter to process every standard monthly loan-level disclosure in the package. Supplementary and EU-format files remain retained in the source package; they are not mixed into the standard-layout performance metric until their distinct layout is separately mapped.

## Exclusions

- Do not use the portal's `Monthly Disclosures` bulk shortcut: it is a broader all-deal package than this documented cohort.
- Do not mix issuance files, geographic files, pre-HARP tapes, lifetime-payment-history files, or EU-format files into the standard monthly performance metric without their own documented layouts and metric definitions.
- Do not expose raw rows, loan identifiers, or other record-level fields in the portfolio site.

## Evidence captured

The authenticated Clarity page stated that all STACR and ACIS files are available by deal in the latest format for all time periods, and it exposed the custom filters used above. The selected state was left open in the browser without clicking **Download**.
