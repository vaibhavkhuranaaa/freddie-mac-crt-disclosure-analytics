# Optional independent-review protocol

## Status

Owner removed independent review from M11 completion scope on 2026-08-12 because no eligible reviewers were available. Current result remains `0/5`; no independent or representative usability claim is made. This protocol remains available for future evidence only.

Future evidence would require at least four of five independent reviewers to complete public aggregate walkthrough within five minutes without facilitator help, with zero critical accessibility or control defects. Automated browser runs, project owner, and implementation tools are technical self-tests, not participants.

## Representative reviewer

A representative reviewer is a capital-markets, credit/risk, analytics, or hiring reviewer who did not build this project and has not been coached through the answer. Do not collect borrower data, consumer identifiers, or unnecessary participant identity. A study coordinator may retain a pseudonymous participant code and role category in controlled local evidence.

## Five-minute task

Starting from the default public candidate view, without facilitator help:

1. State the latest portfolio D60+ level and monthly change.
2. Identify the deal that contributed most to the portfolio change.
3. Determine whether the portfolio change was driven by within-deal rate movement or portfolio mix.
4. Inspect the selected deal's delinquency-flow evidence.
5. Locate the metric definition, calculation method, supported decision, limitation, and restricted-source boundary.

Success requires all five answers to be correct, completion in 300 seconds or less, no facilitator help, and no attempt to access borrower-level data from the public surface.

## Controlled evidence record

The coordinator records one row per participant locally with: pseudonymous participant code, role category, start/end time, completion result, facilitator-help flag, task errors, accessibility/control defects, browser/version, viewport, and notes. Retain the detailed study under `data/restricted/`; copy only aggregate counts and non-identifying issue summaries into M11 evidence.

If future study is genuinely completed, provide `data/restricted/m11_representative_review.json` with this minimal owner-attested summary:

```json
{
  "study_version": 1,
  "representative_reviewers": 5,
  "completed_without_facilitator": 0,
  "critical_defects": 0,
  "attested_by": "project-owner",
  "attested_on": "YYYY-MM-DD"
}
```

Replace zero only with observed completion count. `scripts/evaluate_m11.py` reports whether optional study meets original threshold but does not use it to decide revised M11 completion.
