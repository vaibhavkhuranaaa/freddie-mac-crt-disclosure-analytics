# Require human usability evidence

Status: superseded by decision `0007` on 2026-08-12 because no eligible independent reviewers were available.

## Decision

Keep M11 open until five eligible representative reviewers participate, at least four complete unassisted within five minutes, zero critical defects appear, and owner attests aggregate result.

## Why

Automated browser tests prove mechanics, not whether target reviewer understands decision flow. Honest human evidence prevents technical self-tests from becoming a usability claim.

## Alternatives rejected

- Count automated walkthroughs as participants: invalid evidence.
- Count owner or implementation agents: not independent representative reviewers.
- Waive gate because technical metrics pass: contradicts approved acceptance contract.

## Not done

No participant identity, borrower data, coached answers, or fabricated attestation enters evidence.

## Changed

Originally added controlled review protocol and fail-closed evaluator. Decision `0007` later removed this unavailable study from M11 completion scope while preserving `0/5` and prohibiting representative-usability claims.
