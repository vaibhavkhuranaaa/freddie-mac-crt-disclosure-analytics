# M11 technical usability, analytical-quality, and controls evaluation

Status: **complete under revised technical scope on 2026-08-12**. Automated and technical gates pass. No independent user study was performed; observed result remains `0/5`, and no independent or representative usability claim is made.

## Decision

The complete 20,439,666-row private foundation, metric version `m8.1.0`, and the 305,060-byte public projection remain reconciled and inside the approved aggregate-only boundary. The public and private loopback surfaces pass the implemented Chromium, keyboard, responsive, accessibility, error-state, header, boundary, and local performance checks. `data/derived/m11_evaluation.json` is the machine-readable scorecard.

Owner removed independent review from M11 completion scope on 2026-08-12 because no eligible reviewers were available. This is a claim reduction, not a passed human study. Optional future protocol remains at `docs/m11-representative-review-protocol.md`.

## Reconciliation and boundary

| Gate | Verified result |
| --- | --- |
| Fresh public/private parity | The checked-in public projection equals a fresh projection from the restricted metric engine across all portfolio, deal, pool, and metric-catalog rows. |
| Shared rows | 37 portfolio periods, 292 deal periods, and 292 reference-pool periods exact. |
| Release reconciliation | Current UPB, D30+ rate, and D60+ rate maximum variance are all `0`. |
| Decomposition | Maximum identity variance is `2.842170943040401e-14` bp against a `0.01` bp gate. |
| Projection boundary | 305,060 bytes; no loan row, identifier, restricted path, runtime API, or database. |
| Static artifact | Six allowlisted files plus deterministic private integrity manifest verify. |

Git metadata records the source revision, branch, and clean-worktree state. Final release attestation remains an M13 gate because later approved work may change the candidate.

## Browser, accessibility, keyboard, and responsive evidence

Chromium 151 was exercised at 1440x900, 768x1024, 390x844, and 320x844; the 320 CSS-pixel profile is the reflow equivalent of 400% zoom at 1280 CSS pixels. All four profiles retained a visible workspace, no body overflow, and locally scrollable analytical tables. Keyboard-only watchlist selection updated both selected state and URL on the public and private surfaces. July 2023 correctly narrowed the public deal selector to five period-valid deals. Reduced-motion detection and the named projection-error recovery state passed.

Axe-core 4.12.1 reported zero WCAG A/AA violations on public desktop, public mobile, and private initial-load states. Axe left one manual `color-contrast` check because it cannot infer SVG image-node or partially obscured table backgrounds. Exact foreground/background calculations were 5.591, 6.027, 7.094, and 7.845, all above the 4.5 normal-text minimum. The invalid definition-list and generic-container ARIA defects found in the baseline were removed.

Firefox and Safari were not available in this environment. No cross-engine claim is made.

## Performance and security controls

| Measure | Result | Gate |
| --- | ---: | ---: |
| Local public TTFB | 0.6 ms | <800 ms |
| Local public FCP | 68 ms | <1,800 ms |
| Local public LCP | 68 ms | <2,500 ms |
| Local public CLS | 0 | <0.1 |
| Local filter feedback | 32.6 ms | <100 ms |
| Technical walkthrough | 14.704 s | <300 s |
| Private bootstrap / overview / deal first query | 11.419 / 14.127 / 17.657 ms | <5,000 ms |
| Explicit 50-row query first / warm maximum | 247.246 / 263.153 ms | <2,000 ms warm |

These are local lab measurements, not hosted or real-user results. INP is not claimed because the synthetic run did not produce a field-style INP sample.

The static candidate declares CSP, frame denial, content-type, referrer, permissions, cross-origin opener/resource, and HSTS policies in `vercel.json`; the loopback server returns the applicable non-HSTS headers. The private service returns the same local controls, accepts same-origin loopback Host/Origin pairs only, and returned 421 for a non-loopback Host/Origin probe. Restricted rows remained absent from initial requests, loaded only after the explicit action, returned 50 masked rows, and left identifier reveal off. No raw row or identifier was retained in the M11 evidence.

## Three analytical findings

### 1. July deterioration was performance-led

July 2026 eligible current UPB was $176.245821B and D60+ was 1.27996%, up 4.79439 bp month over month and 8.87807 bp over three periods. Rate effect was +4.82720 bp while mix effect was -0.03281 bp, reconciling to +4.79439 bp. This supports investigating within-deal performance before treating portfolio composition as the driver. The attribution is descriptive, not causal, predictive, or an estimate of loss.

### 2. Portfolio impact differs from deal severity

`2022-HQA1` contributed the most, +1.23598 bp, from $33.216445B eligible UPB and a +6.40931 bp deal move. `2026-HQA1` had the largest deal move, +8.92038 bp, but contributed +0.80801 bp from $15.964608B eligible UPB. This supports portfolio contribution as first triage and deal rate change as a separate severity lens. Contribution depends on portfolio weight and is not a risk score.

### 3. Low stock can coexist with elevated flow

`2026-HQA1` had the highest D30-to-D60 UPB roll rate at 27.72071% while its D60+ stock was 0.17472%. Forty-three of 171 matched prior-D30 loans rolled to D60+, while 78 of 202 matched prior-D30+ loans cured; the cure UPB rate was 37.90100%. This supports monitoring inflow and cure together rather than relying on the D60+ level alone. The flow cohorts are small, denominators are matched prior-state populations, and a cure may be temporary.

## Independent review limitation

- Representative reviewers: `0` evidenced.
- Unassisted completions: `0` evidenced.
- Original threshold: at least `4` of `5`, with zero critical defects and owner attestation.
- Scope decision: independent review is not required for revised M11 completion.
- Claim boundary: technical usability is verified; independent, representative, user-tested, and hiring-manager-validated usability are not claimed.
- Result: M11 is complete under revised technical scope. M12 was unauthorized and M13 was blocked at M11 close; M12 received separate approval on 2026-08-13.
