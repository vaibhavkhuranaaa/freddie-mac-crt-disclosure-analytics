# Hiring-manager remediation plan

Status: historical M1–M5 remediation record. The proposed M6–M13 product and delivery plan is `docs/product-metric-dashboard-plan.md`.

## Phase 1: Factual consistency

- Remove stale synthetic/local claims from the live route and public metadata.
- Keep synthetic wording only in the fallback/test path.
- Publish an explicit retained-raw-fields versus retained-aggregate-dimensions statement.

**Acceptance:** live page, README, case study, deployment contract, readiness packet, and manifest tell one consistent story.

## Phase 2: Defensible data evidence

- Add file-level record-count and official-total reconciliation where source totals are available.
- Add duplicate, revised-disclosure, reporting-period continuity, zero-UPB, and status-validity gates.
- Produce immutable private release receipt with input/output integrity values, build/test command, approval, timestamp, and deployment URL.

**Acceptance:** a rerun can explain every accepted/rejected source file and demonstrate a repeatable release result.

## Phase 3: Credible CRT product scope

- Add documented transaction and tranche data, or permanently title the product “CRT reference-pool performance analytics.”
- Add weighted trends, period-over-period deltas, comparison mode, definitions/tooltips, data-as-of information, and approved aggregate export.
- Publish three evidence-backed findings with their calculation and limitation.

**Acceptance:** a reviewer can understand what changed, compare deals, and trace every insight to an approved metric.

## Phase 4: Engineering and portfolio polish

- Add browser interaction, accessibility, and visual-regression tests.
- Replace naive CSV splitting and `innerHTML` row injection with robust parsing and DOM-safe rendering.
- Add CSP/security headers and bind a release to a public Git revision plus a live verification endpoint before portfolio-registry admission.

**Acceptance:** the project meets the existing portfolio registry's exact-revision verification contract and supports an audit-ready technical interview walkthrough.
