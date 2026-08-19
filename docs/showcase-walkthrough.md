# Five-minute showcase walkthrough

## 0:00 to 0:45: decision and boundary

Open public candidate. State question: which deal drove latest D60+ deterioration, was movement performance or mix, and is evidence reliable enough to investigate? Note public surface is aggregate-only. Loan rows remain controlled local evidence.

## 0:45 to 1:45: portfolio pulse and watchlist

Keep July 2026 selected. Portfolio eligible current UPB is $176.246 billion and D60+ is 1.27996%, up 4.79439 basis points over one month. Rank by portfolio contribution, not deal severity alone.

## 1:45 to 2:45: contribution versus severity

Select `2022-HQA1`. It contributes most to portfolio deterioration at +1.23598 basis points because $33.216 billion exposure gives its +6.40931 basis-point deal movement larger portfolio weight. Compare `2026-HQA1`: largest deal movement at +8.92038 basis points but smaller +0.80801 basis-point portfolio contribution.

Decision: investigate portfolio contribution first, then use deal movement as severity lens.

## 2:45 to 3:45: rate, mix, and flow

Portfolio change decomposes into +4.82720 basis-point rate effect and -0.03281 basis-point mix effect. Deterioration is performance-led, not composition-led. `2026-HQA1` also has 27.72071% D30-to-D60 UPB roll rate while D60+ stock remains 0.17472%, showing why flow and stock belong together.

Decision: prioritize within-deal performance investigation, then inspect inflow and cure populations. Attribution is descriptive, not causal or predictive.

## 3:45 to 4:30: evidence and controls

Open metric evidence. Confirm definition, denominator, exclusions, metric version, source coverage, exact public/private reconciliation, and calculation limitation. Public bundle contains no runtime database, loan row, identifier, or restricted dimension.

## 4:30 to 5:00: scale and honest limits

M12 processes 20,439,666 rows across 292 partitions. Keyed query reads one file; full-history column scan is 214.706 ms; materialized metric query p95 is 0.588 ms. Local DuckDB remains justified until refresh, query, storage, concurrency, or scheduling trigger is crossed.

Close with limits: no investment recommendation, borrower decision, representative-usability claim, cross-browser claim, real-user metrics, or concurrent-scale claim. P7 verifies the hosted candidate in Chromium with exact artifact parity and production headers.

## Screenshot pair

Stakeholder workflow:

![Desktop aggregate surveillance review docket](../evaluation/p9-redesign/public-desktop.png)

Technical responsive evidence:

![Mobile aggregate surveillance review docket](../evaluation/p9-redesign/public-mobile.png)

Current hosted production evidence:

![Hosted aggregate surveillance review docket](../evaluation/p9-redesign/public-production.png)
