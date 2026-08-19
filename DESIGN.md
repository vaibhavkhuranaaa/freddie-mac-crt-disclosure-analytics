---
name: CRT Collateral Surveillance
description: A monthly risk-review docket for Freddie Mac CRT disclosure evidence.
colors:
  ink: "#171a1f"
  paper: "#eef1ef"
  sheet: "#ffffff"
  rule: "#aeb6bd"
  rule-light: "#d9dee0"
  muted: "#596169"
  field: "#e2e6e4"
  hover-sheet: "#f7f9f7"
  review-mark: "#d7ff3f"
  review-mark-ink: "#1c2600"
  selected-wash: "#f6ffd6"
  dark-ui-muted: "#cfd5d7"
  dark-ui-detail: "#c1c7ca"
  adverse: "#8f2735"
  favorable: "#176150"
typography:
  display:
    fontFamily: "Arial Narrow, Aptos Narrow, Helvetica Neue Condensed, sans-serif"
    fontSize: "clamp(2.5rem, 4.4vw, 4.7rem)"
    fontWeight: 800
    lineHeight: 0.86
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Arial, Helvetica Neue, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.5
  headline:
    fontFamily: "Arial Narrow, Aptos Narrow, Helvetica Neue Condensed, sans-serif"
    fontSize: "clamp(1.3rem, 2vw, 1.7rem)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.02em"
  metric:
    fontFamily: "Arial Narrow, Aptos Narrow, Helvetica Neue Condensed, sans-serif"
    fontSize: "clamp(1.7rem, 3vw, 3rem)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "-0.025em"
  finding:
    fontFamily: "Arial Narrow, Aptos Narrow, Helvetica Neue Condensed, sans-serif"
    fontSize: "clamp(3.7rem, 7vw, 5.4rem)"
    fontWeight: 850
    lineHeight: 0.8
    letterSpacing: "-0.035em"
  label:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "0.68rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.08em"
  detail:
    fontFamily: "Arial, Helvetica Neue, sans-serif"
    fontSize: "0.74rem"
    fontWeight: 400
    lineHeight: 1.48
rounded:
  control: "2px"
spacing:
  hairline: "1px"
  field: "12px"
  section: "24px"
  folio: "40px"
components:
  review-control:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 34px 10px 10px"
  selected-evidence:
    backgroundColor: "{colors.review-mark}"
    textColor: "{colors.review-mark-ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
---

# Design System: CRT Collateral Surveillance

## Overview

**Creative North Star: "The review docket"**

This interface behaves like the exception book prepared for a monthly risk committee. Findings are numbered, evidence is ruled and cross-referenced, and selection looks like a physical review mark. It refuses the generic SaaS dashboard pattern of a slogan followed by interchangeable cards.

Density is deliberate. Analysts should see the portfolio move in the first viewport and reach the complete masked record register immediately after it. Hiring managers should recognize a specific capital-markets workflow rather than a general analytics template.

**Key Characteristics:**

- Cool archival sheets, black registration ink, and one chartreuse review marker.
- Condensed headlines paired with monospaced labels and tabular figures.
- Numbered docket sections instead of floating cards.
- Rules, folio marks, and margin notes create hierarchy without shadows.

## Colors

Neutral documents carry the evidence. Chartreuse appears only where a reviewer has made or must make a choice.

### Primary

- **Review mark** (`#d7ff3f`): selected rows, current docket state, and keyboard focus support.

### Neutral

- **Registration ink** (`#171a1f`): primary text and structural rules.
- **Archive field** (`#eef1ef`): page ground.
- **Filed sheet** (`#ffffff`): evidence surfaces.
- **Rule gray** (`#aeb6bd`): secondary dividers and form outlines.
- **Field gray** (`#e2e6e4`): review controls and table headings.
- **Selected wash** (`#f6ffd6`): selected evidence row behind the chartreuse rank mark.
- **Margin note** (`#596169`): supporting copy.

### State

- **Adverse mark** (`#8f2735`): deterioration, always paired with a signed value or label.
- **Favorable mark** (`#176150`): offset or improvement, always paired with a signed value or label.

**The one-marker rule.** Chartreuse means current review focus. It never decorates headings, charts, or inactive controls.

## Typography

**Display Font:** Arial Narrow or the closest installed condensed grotesk.
**Body Font:** Arial with Helvetica Neue fallback.
**Label/Mono Font:** System monospace with tabular figures.

Condensed type gives the docket a filing-room economy. Monospace handles dates, basis points, deal IDs, ranks, and control states. Body copy remains plain and compact.

### Hierarchy

- **Display** (800, fluid 2.5 to 4.7rem, 0.86): one compact monthly filing title in the opening docket.
- **Finding** (850, fluid 3.7 to 5.4rem, 0.8): the signed monthly portfolio exception.
- **Metric** (800, fluid 1.7 to 3rem, 0.95): balances, levels, contributors, and flow values.
- **Headline** (800, fluid 1.3 to 1.7rem, 1): numbered section titles.
- **Title** (700, 1.3rem, 1.2): evidence rail and compact state titles.
- **Body** (400, 0.9rem, 1.5): explanations limited to roughly 68 characters.
- **Detail** (400, 0.74rem, 1.48): table support and evidence notes.
- **Label** (700, 0.61 to 0.68rem, 0.08em): dates, folio references, units, and statuses.

Responsive overrides preserve legibility in the single-column filing: display type uses a fluid 2.3 to 3rem range, and the primary finding uses a fluid 4 to 5.5rem range.

**The figure rule.** Every measure, period, deal ID, and control status uses tabular figures or monospace.

## Layout

Desktop uses a wide docket with a narrow folio margin, one main evidence column, and an attached review-notes rail. The compact opening file leads directly into the current portfolio finding, keeping real values in the first viewport. Review controls follow that finding, then the full masked register appears before the aggregate investigation queue. Each analytical section begins with an index number and a hard rule.

Below 1050px the notes rail follows the evidence. Below 700px the folio margin collapses, section numbers move into headers, and wide tables remain horizontally scrollable. Content never disappears to make the layout fit.

## Elevation & Depth

No shadows. Depth comes from sheet color, black rules, overlapping review marks, sticky headers, and the contrast between archive field and filed evidence.

**The filed-flat rule.** Every surface sits in the same physical plane. State changes alter ink, marker, or rule weight, never elevation.

## Shapes

Rectangles stay square or use a 2px technical radius. Round badges, pills, floating cards, and soft containers do not belong in the docket. A circular mark is reserved for the small CRT folio seal.

## Components

### Review controls

- **Shape:** square field with 2px radius and a 1px black outline.
- **State:** selected value remains white; focus adds a chartreuse offset block and black outline.
- **Labels:** monospaced docket language placed above the field.

### Evidence tables

- **Structure:** dense ruled rows, sticky header, tabular measures, no container shadow.
- **Selection:** chartreuse strip at the row edge plus a dark deal label.
- **Interaction:** hover strengthens the row rule; keyboard focus remains visible.

### Full record register

- **Structure:** server-side status filtering and 25-row pagination over one selected deal-month partition.
- **Preview:** a compact 12-column decision view keeps status, balance, coupon, and origination risk fields together.
- **Detail:** opening a row reveals every stored field in a dense ruled definition list; masked identifiers use the selected wash.
- **Boundary:** identifier masking and remaining linkage risk stay visible above the register.

### Docket sections

- **Structure:** index number, title, note, and hard top rule.
- **Background:** filed white sheet against the archive field.
- **Spacing:** compact inside data regions, generous before each new analytical question.

### Evidence rail

- **Structure:** margin-note blocks separated by black rules, not cards.
- **Boundary notice:** adverse state color and explicit masking and use-limit wording.

## Do's and Don'ts

### Do:

- **Do** lead with the month’s measured exception and explanation.
- **Do** make selection look like a reviewer’s deliberate mark.
- **Do** keep levels, changes, balances, and comparison bases together.
- **Do** retain visible loading, empty, error, masking, pagination, and keyboard states.

### Don't:

- **Don't** use a marketing hero, centered slogan, gradient, glass, or generic card grid.
- **Don't** use chartreuse as decoration or color as the only state signal.
- **Don't** soften dense evidence into oversized KPI tiles.
- **Don't** imitate a black-neon trading terminal.
