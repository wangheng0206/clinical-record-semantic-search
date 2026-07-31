# Product Requirement: Clinical Record Semantic Search

Requirement ID: REQ-2026-07-31-clinical-semantic-search
Product Definition Profile: brief
Product Review: confirmed

## Problem / Background

Clinicians hold many clinical documents per patient and cannot quickly find which patients' existing records match a described clinical presentation. The exercise provides a synthetic multi-practice corpus (3 practices, 715 patients, 2,400 documents), a working platform scaffold, and stubs for everything search-related. The corpus includes realistic quality variation and pathological documents; not every document is indexable.

## Target User / Scenario

A clinician (mock demo user bound to exactly one practice) types a natural-language description such as "recurring headaches preceded by flashing lights, nausea, and sensitivity to light" and receives a ranked list of patients **in their own practice** whose existing notes and reports are semantically relevant, each result showing the source document and the passage that explains the match, with navigation to the patient detail page.

## Goal / Expected Product Outcome

A working, explainable, end-to-end semantic retrieval feature: the supplied documents become searchable through a repeatable indexing workflow, and a natural-language query returns practice-isolated, patient-level ranked results grounded in source evidence. Retrieval only — the feature must not generate diagnoses, infer conditions not already in the records, or present similarity as clinical confidence.

## In Scope

- Searchable representation: chunk + embedding storage (migration 0002) preserving practice/patient/document/type metadata, supporting practice isolation, patient-level results, evidence, and safe updates when source documents change.
- Indexing workflow (`make index`): chunks source documents, embeds through the provided local embedding service, is idempotent on unchanged data, reflects relevant source changes, tolerates individual unindexable documents, and reports a useful completion summary.
- `POST /api/clinical-search`: validated vector-based semantic retrieval, practice isolation enforced server-side (no client-selected practice identifier), ranked patient-level results (each patient at most once) with supporting source evidence, deliberate behavior for empty index / no match / dependency failure, client-safe errors.
- Search UI (`/search`): natural-language query input, optional document-type filter, ranked patient results with supporting passage, navigation to patient detail, and clear idle / loading / results / no-results / invalid-input / dependency-failure states.
- Acceptance tests replacing the provided `xfail` placeholders: indexing safety, practice isolation, result behavior, request validation, and at least one frontend state; deterministic, no uncontrolled external service.
- Operational visibility: enough diagnostics to investigate indexing and search failures without logging document bodies, supporting passages, patient names, or embedding vectors.
- README solution writeup (per assignment email): architecture, key decisions and trade-offs, intentional simplifications, incomplete parts, and future extensions.

## Out Of Scope / Non-goals

- Production authentication or authorization infrastructure.
- Hosted embedding providers or any external service for records.
- Diagnosis generation or clinical decision support.
- Perfect negation / historical-condition / contradictory-note handling.
- Sophisticated reranking models; production-scale infrastructure.
- Unrelated visual redesign or optional product features.
- Code submission (push / PR) — human decision 2026-07-31: local delivery only.
- Modifying provided platform: base schema 0001, embedding service, seed data, human-owned docs.

## Acceptance Direction

- The application runs from the documented commands (`make setup / seed / index / dev / test / smoke`).
- Natural-language search returns semantically related records; meaningful paraphrases retrieve relevant source records within the result limit.
- Results are always restricted to the authenticated user's current practice; cross-practice decoys never appear.
- Every result includes the source document and a supporting excerpt; patients appear at most once; extra matching documents are counted.
- Re-running indexing on unchanged data creates no duplicates; changed source content is re-indexed; one bad document neither aborts the run nor corrupts the index.
- Invalid requests are rejected (422) without calling the embedding service; dependency failure yields a client-safe 503.
- Required UI states are handled; relevance score is never presented as diagnosis or clinical certainty.
- Backend and frontend suites, lint, typecheck, and smoke are green; README explains the implementation and its limitations.

## Source Evidence

| Source | Type | Product Claim Used | Preserved / Referenced |
|---|---|---|---|
| docs/TAKE_HOME_DESIGN.md | human original (in-repo) | entire product definition §1–§11 | referenced in place; never modified |
| assignment email 2026-07-31 | human original (conversation) | 48h window, 8–12h effort, end-to-end priority, README trade-off writeup | recorded in Feature notes |
| database/seed/data/curated_cases.json | provided fixture | graded retrieval/isolation cases | referenced |
| scaffold stubs + acceptance placeholders | provided code | candidate-owned surfaces and graded behaviors | referenced |

## Open Questions / Remaining Risk

- Exact remaining time in the 48h window (access start unknown); plan assumes ~8–12 focused hours suffice.
- Chunking / ranking parameters (target chunk size, candidate over-fetch) are tuned during implementation and recorded in the README writeup.

## Applicable Decisions

- none

## Product Traceability

| Product Claim | Source Evidence | Stable References | Downstream Direction |
|---|---|---|---|
| practice isolation server-side | TAKE_HOME_DESIGN §4.3, §6 | product.md#in-scope | Feature Spec AC-4; search API SQL pre-filter |
| patient-level results with evidence | TAKE_HOME_DESIGN §4.3, §6 | product.md#in-scope | Feature Spec AC-5; aggregation by best chunk |
| idempotent indexing with change reflection | TAKE_HOME_DESIGN §4.2, §6 | product.md#in-scope | Feature Spec AC-2/AC-3; content-hash change detection |
| README trade-off writeup | assignment email | product.md#in-scope | Feature Spec AC-9; T006 |

## Product Human Review Evidence

Decision: confirmed
Confirmed By: human (project owner), via agent-loop conversation
Confirmed At: 2026-07-31
Evidence: human approved the task breakdown and Feature definition ("请初始化项目", then "批准" at Gate 1 on 2026-07-31) after this product definition's content was presented as the Feature Spec Product Slice
Implementation Authorized: separately-confirmed

Product Review confirmation does not authorize Requirement acceptance, Feature start, ADR acceptance, code execution, or Git actions.
