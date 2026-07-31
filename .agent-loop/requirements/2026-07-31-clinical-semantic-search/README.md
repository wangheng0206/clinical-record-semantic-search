# Requirement Set: Clinical Semantic Search (Take-Home)

Archived: 2026-07-31
Topic: clinical-semantic-search
Status: accepted

## Date Meaning

- The date is the archive date only.
- It is not a deadline, feature duration, implementation start date, or implementation end date. The 48h exercise window is tracked in the Feature notes, not here.

## Lifecycle

Intake Type: human-request
Decision: accepted
Priority: high
Owner Feature: .agent-loop/features/2026-07-31-semantic-search/
Implemented By: .agent-loop/features/2026-07-31-semantic-search/
Superseded By: none
Last Reviewed: 2026-07-31
Exit Condition: working explainable end-to-end semantic search, verified locally; no code submission

## Summary

One-line summary: make the supplied synthetic clinical-record corpus semantically searchable end to end (indexing + practice-isolated vector search + search UI), per the take-home assignment.

Related Bugs: none
Requirement Impact: none

## Effective Product Definition

Source: product.md
Profile: brief
Product Review: confirmed
Previous Source: none
Last Confirmed: 2026-07-31
Reason / Reopen Trigger: none

This block is an effective-source and freshness pointer only. Product meaning stays in the referenced human-reviewed source file.

Product Review confirmation does not change Requirement Status or authorize Feature start.

## Delivery Phases

Not used — the assignment is one bounded feature.

## Design Readiness

Status: design-not-needed

| Signal | Evidence / Need |
|---|---|
| Multiple Features | no — single feature |
| End-to-End Business Closure | contained in one feature |
| Shared Domain / State / Source Of Truth | chunk/embedding store is feature-local |
| Consistency / Concurrency / Recovery | idempotent indexing covered by feature acceptance |
| Non-Functional Goals | local exercise scale (2,400 documents) |
| Cross-System / Durable Boundary | none beyond provided embedding service contract |

Shared Design Needs:
- none

Recommended Next Stage: Feature Spec with Product Slice

Decision Records:
- none

Coverage Status: not-applicable

## Applicable Decisions

- none

## Triggered Decisions

| Decision | Why Triggered | Status |
|---|---|---|
| — | — | not-needed |

## Source Files

- Product Definition: product.md (this directory)
- Product Definition Follow-ups: none
- Human Original Requirements: `docs/TAKE_HOME_DESIGN.md` (in-repo, byte-stable, human-owned), assignment email pasted by human on 2026-07-31 (48h window, 8–12h effort, README trade-off writeup)
- Prototype: provided scaffold stubs in the repo
- Feedback: none
- Screenshots: none
- Recordings: none
- Links: https://github.com/medlink-global/interview (origin; read-only context, no push)
- Change Requests: none
- Other: `docs/DATASET.md`, `database/seed/data/curated_cases.json`

## Original Sources

- `docs/TAKE_HOME_DESIGN.md` — the assignment specification (human-owned, never modify)
- Assignment email (2026-07-31) — time/effort expectations and README writeup requirement

## Source Conversation Summary

Source Conversation Summary:
- Human received a 48h full-stack take-home exercise (clinical record semantic search), asked agent-loop to initialize the project, decompose the work, and build the feature locally without code submission.

## Used By

- `.agent-loop/features/2026-07-31-semantic-search/spec.md`

## Implemented By

- `.agent-loop/features/2026-07-31-semantic-search/`

## Status History

- 2026-07-31:
  - Status: accepted
  - Reason: assignment confirmed by human; product definition reviewed and confirmed at Feature Gate 1
  - Human Decision: "批准" (2026-07-31)

## Notes

- The human source specification already lives in the repo as `docs/TAKE_HOME_DESIGN.md`; it is referenced rather than copied to keep one byte-stable original.
