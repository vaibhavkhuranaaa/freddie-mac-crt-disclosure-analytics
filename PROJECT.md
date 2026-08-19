# Freddie Mac CRT Disclosure Analytics

## Portfolio contract

- **Category / industry:** analytics / Capital markets
- **Source:** Original CRT-specific charter, informed by the finance analytics starter pattern.
- **Industry question:** Which Freddie Mac CRT deal or reference-pool cohorts are deteriorating, what is driving the change, and is the evidence reliable enough to investigate?
- **Owner-facing user and decision:** A capital-markets credit/risk analyst ranks deals and cohorts for monthly surveillance, compares performance, explains rate versus mix effects, and hands off a traceable investigation. This project does not support decisions about individual borrowers or households.
- **Data classification:** Approved Freddie Mac CRT disclosures. Full authorized loan-level processing and row-level analyst access are approved in a controlled private environment; public outputs remain aggregate-only. No re-identification or consumer credit decisioning.
- **Demo status:** Verified private analyst workbench plus aggregate-only public twin through M13; P7 hosted deployment and production verification pass.
- **Public URL target:** `/projects/freddie-mac-crt-disclosure-analytics` on the portfolio website, subject to the portfolio release contract.
- **GitHub repository:** Local project initialization only. Repository publication is a separate owner-gated action.

## Success criteria

1. An authorized analyst can run the documented private workflow against every approved standard monthly row, rank deterioration, compare pools, explain cohort drivers, inspect permitted loan-level evidence, and reproduce the result.
2. Every published metric records its source, reporting period, calculation definition, and release status.
3. The project produces a versioned evaluation report covering data quality, metric reconciliation, runtime, and control checks.
4. The public surface contains only approved aggregate results and clearly excludes borrower-level lending, underwriting, pricing, servicing, marketing, or household-level use.

## Next phased delivery

1. Approve the collateral-surveillance purpose, full metric system, dashboard workflow, and public/private boundary.
2. Normalize the complete authorized 89/90/93-field monthly layouts into a controlled full-data local layer.
3. Build and reconcile versioned exposure, delinquency, transition, exit, modification, loss, risk-mix, and rate/mix-decomposition metrics.
4. Deliver the private analyst workbench and an aggregate-only public twin from the same metric engine. **Completed through M10.**
5. Prove technical usability, analytical quality, accessibility, performance, controls, and scaled-local refresh behavior. **Completed through M12.** Independent review remains unavailable and unclaimed.
6. Package local showcase and bind release evidence to clean source revision. **M13 local package complete.**
7. Deploy and verify the aggregate-only candidate using existing free Vercel capacity. **P7 complete.** Publication, push, and portfolio-site application remain separately gated.

## End-to-end architecture

| Stage | Baseline choice | Evidence |
| --- | --- | --- |
| Ingestion | Manual approved-file placement, private source manifest, and version-aware validation of every standard monthly field | Source manifest, terms version, schema map, field profile, failure tests |
| Storage / transform | Restricted local DuckDB/Parquet loan-period layer plus shared versioned metric views and separate public aggregate exports | Lineage record, quality report, row/public boundary, reconciliation |
| Product / intelligence | Python and SQL metric engine with one private workbench and one aggregate-only static twin | Metric glossary, reproducible queries, rate/mix decomposition, task walkthrough |
| Evaluation | Schema pass rate, reconciliation variance, coverage, runtime, and control-test pass rate | Versioned evaluation report and baseline |
| Serving | Verified M13 static aggregate twin on Vercel; no runtime database or API | Public URL, P7 hosted verification, private rollback record, and deterministic local manifest |
| Observability | Structured run log, source/metric lineage, test and evaluation artifacts | Run manifest and release checklist |
| Security / delivery | Least privilege, encrypted local storage, no source data in Git or public assets | Retention record, exclusion rules, `.gitignore` |

## Cost, quality, and control requirements

- **Free-first:** Process the complete authorized package locally and publish only a compact reviewed aggregate projection. No new cloud resources or paid services are in baseline scope.
- **Private analyst access:** The authorized full loan-level layout may enter the private analytical layer for analyst review. Inputs are never joined to external person-, property-, or consumer-identifying datasets.
- **Publication boundary:** Only approved aggregate outputs may enter the portfolio site. Raw files, row-level derivatives, identifiers, and restricted scoring fields are excluded from Git and public assets.
- **Evaluation:** Validate required schema fields, reporting-period continuity, aggregation reconciliation, output suppression, source provenance, and runtime. Report failures and limitations rather than masking them.
- **Disclosure:** This is transaction analytics for CRT performance context, not investment advice and not a borrower-level lending system.

## Handoff contract

Canonical continuation records live in the private sibling operations folder. They identify the first unblocked milestone, verified starting state, exact commands, safety boundaries, and open gaps. Update architecture, evidence, state, and handoff whenever verified facts change.
