# Feature Spec: Clinical Record Semantic Search

Created: 2026-07-31
Updated: 2026-07-31
Status: closed
Feature Type: normal

Source Requirements:
- Requirement: `docs/TAKE_HOME_DESIGN.md` (human-owned, in-repo, byte-stable; do not modify)
- Requirement: assignment email (2026-07-31, pasted by human): 48h window from confirmation, 8–12h expected effort, working explainable end-to-end feature first, and trade-offs / intentional simplifications / future extensions must be written up in README
- Prototype: provided scaffold stubs (indexing script, search router 501, `/search` shell, xfail acceptance placeholders)

## Product Requirement Source

- Requirement Set: .agent-loop/requirements/2026-07-31-clinical-semantic-search/README.md
- Effective Product Definition: .agent-loop/requirements/2026-07-31-clinical-semantic-search/product.md
- Product Definition Profile: brief
- Product Review Evidence: confirmed by human on 2026-07-31 ("批准" at Gate 1); see product.md "Product Human Review Evidence"
- Applicable Decisions: none

## Feature Context Snapshot

Requirement Set: .agent-loop/requirements/2026-07-31-clinical-semantic-search/README.md
Requirement Lifecycle: accepted
Resolved Product Source: .agent-loop/requirements/2026-07-31-clinical-semantic-search/product.md
Product Definition Profile: brief
Product Review: confirmed
Product Source SHA-256: 183c310721de16d96e88f18dd263267702188e1162abd8eef5883655acf5059d
Applicable Decisions: none
Decision Source SHA-256: none
Product Slice References: product.md#goal-expected-product-outcome, product.md#in-scope, product.md#acceptance-direction, product.md#out-of-scope-non-goals
Verified At: 2026-07-31T12:20:00+08:00
Freshness: current

### Product Outcome

A user types a natural-language clinical description and gets a ranked list of patients **in their own practice** whose existing records are semantically relevant, each result citing the source document and supporting passage.

### Actors And Core Journey

- Clinician (mock demo user bound to one practice): index corpus -> submit query -> read ranked patient results with evidence -> navigate to patient detail.

### Applicable Product Rules And Invariants

- Retrieval only: no diagnosis generation, no inferred conditions, similarity is never clinical confidence.
- Practice isolation: results never include another practice's patients; no request field may override practice context.
- Source grounding: every result traces to an existing synthetic document with a supporting excerpt.
- Patient-level results: each patient appears at most once in the primary list.
- Repeatability: re-indexing unchanged data creates no duplicates; relevant source changes are reflected.

### Applicable States, Exceptions, And Recovery

- UI states: idle, loading, results, no-results, invalid-input, dependency-failure.
- API behaviors: empty index, no match, embedding-service failure, database failure, unindexable individual documents — all deliberate, never silent failure or partial corruption.

### Feature Boundary And Acceptance Context

Candidate-owned areas only: chunk/embedding schema (migration 0002), indexing workflow, `POST /api/clinical-search`, `/search` UI, acceptance tests. Provided platform (scaffold, embedding service, base schema, seed) is not modified.

## Product Slice

| Source Section / Model ID | Feature Responsibility | Acceptance Mapping | Coverage |
|---|---|---|---|
| product.md#in-scope | chunk + embedding schema (migration 0002) | AC-1 | in-scope |
| product.md#in-scope | indexing workflow (`make index`) | AC-2, AC-3 | in-scope |
| product.md#in-scope | `POST /api/clinical-search` semantic retrieval | AC-4, AC-5, AC-6 | in-scope |
| product.md#in-scope | `/search` UI states and navigation | AC-7 | in-scope |
| product.md#in-scope | acceptance tests + operational visibility | AC-8 | in-scope |
| product.md#in-scope | README solution writeup | AC-9 | in-scope |
| product.md#out-of-scope-non-goals | exclusions (TAKE_HOME_DESIGN §9 + no submission) | — | out-of-scope |
| product.md#acceptance-direction | definition of done mapping | all ACs | in-scope |

Related Bugs: none
Bug Resolution Path: none

Related Feature: none
Flow-back Decision: none

Summary:
- Build the complete candidate-owned vertical: schema -> indexing -> API -> UI -> acceptance tests, verified end to end locally.

## Problem / Goal

The provided scaffold has a working platform but no semantic search: chunks/embeddings have no schema, `make index` is a stub, `POST /api/clinical-search` returns 501, `/search` is a shell, and acceptance tests are `xfail` placeholders. Goal: deliver a working, explainable, practice-isolated semantic search end to end, within the 48h exercise window.

## Applicable Decisions

- none (no project ADRs; feature-local decisions below)

## Scope

- Migration `database/migrations/0002_*.sql`: chunk + embedding storage with source metadata (practice, patient, document, type, position), constraints, indexes (pgvector), and lifecycle/deletion behavior.
- Indexing workflow in `services/api/app/features/indexing/` + `app/scripts/index_clinical_documents.py`: chunking, batch embedding via the provided client, hash-based change detection, idempotent re-runs, per-document failure tolerance, completion summary.
- Search API in `services/api/app/features/search/`: request validation, query embedding, pgvector retrieval pre-filtered by the session practice, patient-level aggregation (each patient once), evidence excerpt per result, deterministic empty/failure behavior, client-safe errors.
- Search UI in `apps/web/features/search/` + `app/search/page.tsx`: query input, optional document-type filter, ranked patient results with evidence passage, link to patient detail; all six UI states.
- Acceptance tests replacing the `xfail` placeholders: indexing idempotency, practice isolation, ranking/aggregation, request validation, at least one frontend state.
- Solution writeup in `README.md` (assignment email requirement): architecture and data flow, chunking / change-detection / ranking / isolation decisions and trade-offs, what is incomplete or intentionally simplified, and future extensions. PR template content folds into this since no PR is submitted.

## Stories

### US1: Searchable representation and indexing

Why this matters: without a sound chunk model and a safe, repeatable indexing run, nothing downstream can work.

Independent test: run `make index` twice against seeded data; second run creates no duplicates; a corrupted single document fails without corrupting the run; summary reports counts.

Acceptance scenarios:
- Given seeded documents, when `make index` runs, then all indexable documents are chunked, embedded, and stored with practice/patient/source metadata.
- Given an unchanged corpus, when `make index` runs again, then no duplicate chunks or embeddings are created.
- Given a source document whose content changed, when `make index` runs, then its chunks are refreshed without a full reset.
- Given one unindexable document, when `make index` runs, then that document is skipped/reported and the rest of the index stays intact.

### US2: Semantic search API

Why this matters: this is the core evaluated behavior — vector retrieval with a hard isolation boundary.

Independent test: POST a natural-language query as a demo user; results contain only that user's practice, each patient at most once, each with document + excerpt evidence.

Acceptance scenarios:
- Given an indexed corpus, when a valid query arrives, then results are ranked by vector similarity and restricted to the session practice.
- Given a query, when multiple matching documents belong to one patient, then the patient appears once with the best supporting evidence.
- Given an empty index or no semantic match, when queried, then the API returns a deliberate empty result (not an error).
- Given an embedding-service or database failure, when queried, then the API returns a client-safe error without internal details.
- Given an invalid request (too long, wrong shape, client-supplied practice id), when queried, then validation rejects it.

### US3: Search experience

Why this matters: the reviewer experiences the feature through the UI; clarity of evidence and states is the product judgment being evaluated.

Independent test: from `/search`, submit the example query, read ranked results with passages, click through to patient detail; toggle document-type filter; observe each state.

Acceptance scenarios:
- Given the `/search` page, when the user submits a natural-language query, then a ranked patient list with supporting passages is shown.
- Given results, when the user clicks a patient, then the existing patient-detail route opens.
- Given no matches, invalid input, or a failed dependency, then the UI shows a clear dedicated state (never a crash or silent blank).

### US4: Verification and operational visibility

Why this matters: §4.5 and the acceptance-test requirement are explicitly graded; deterministic tests prove the isolation and idempotency claims.

Independent test: `make test` green with the former `xfail` placeholders replaced by real tests; `make smoke` green; logs contain diagnostics without document content, patient names, or vectors.

Acceptance scenarios:
- Given the implemented feature, when `make test` runs, then indexing safety, practice isolation, result behavior, request validation, and at least one frontend state are covered deterministically.
- Given an indexing or search failure, when inspecting logs, then enough diagnostics exist to investigate without any sensitive content.

## Acceptance Criteria

- AC-1: migration 0002 creates the searchable representation; `make migrate` is repeatable; 0001 untouched.
- AC-2: `make index` indexes the seeded corpus through the real embedding service and reports a useful completion summary.
- AC-3: re-running `make index` on unchanged data creates zero duplicates; changed source content is reflected; one bad document does not corrupt the index.
- AC-4: `POST /api/clinical-search` returns vector-ranked, practice-isolated results; meaningful paraphrases retrieve relevant records within the result limit.
- AC-5: each result identifies a patient (at most once), the source document, and a supporting excerpt.
- AC-6: empty index, no match, invalid requests, and dependency failures all behave deliberately with client-safe errors.
- AC-7: `/search` supports query + optional document-type filter, shows evidence, links to patient detail, and handles all six UI states.
- AC-8: `make test`, `make lint`, `make typecheck`, `make smoke` are green; logs are diagnostic but free of sensitive content.
- AC-9: `README.md` gains a clearly-marked solution section (or linked `SOLUTION.md`) covering architecture, key decisions and trade-offs, intentional simplifications, incomplete parts, and future extensions.

## Behavior Changes

### Added

- Chunk/embedding tables (migration 0002), indexing workflow, semantic search endpoint, search UI, acceptance tests.

### Modified

- `app/scripts/index_clinical_documents.py` (stub -> real workflow), `app/features/search/router.py` (501 -> implementation), `app/search/page.tsx` (shell -> experience), acceptance placeholders (xfail -> real).

### Removed

- nothing.

## Dependencies

- Provided embedding service contract (384-dim, 256-token, 64/batch, 8000-char, blank-rejected limits).
- Provided session context for practice identity; provided migration runner; deterministic embedding stub for tests.
- Docker daemon running (environment prerequisite).

## Implements Decisions

| Decision | Design Slice ID | Responsibility | Verification | Coverage Status |
|---|---|---|---|---|
| — | — | — | — | — |

## Design Decisions

Feature-local decisions (to be finalized and justified during package preparation):

- Decision: chunking strategy — candidate direction: split documents on structural boundaries (sections/paragraphs) with a size ceiling under the 8,000-char limit and light overlap for context continuity.
  - Reason: embedding quality degrades on very long texts; the 256-token model limit makes small coherent chunks safer than whole documents.
  - Applies To: indexing workflow, schema
  - Placement: feature-local
- Decision: change detection via per-document content hash stored with chunks.
  - Reason: cheapest reliable idempotency + update reflection without timestamps that seed data may not provide.
  - Applies To: schema, indexing workflow
  - Placement: feature-local
- Decision: practice isolation via `practice_id` on the chunk table, filtered inside the SQL retrieval query (pre-filter, not post-filter).
  - Reason: isolation must hold inside the trusted backend boundary before records reach any client-facing assembly; post-filtering top-k can leak ranking information and return empty pages.
  - Applies To: schema, search API
  - Placement: feature-local
- Decision: patient aggregation by best (max) chunk similarity per patient, evidence = that chunk's document + excerpt.
  - Reason: simple, explainable, matches "each patient at most once"; alternatives (mean, count-weighted) reward document volume over relevance.
  - Applies To: search API
  - Placement: feature-local

## Out of Scope

- Everything in TAKE_HOME_DESIGN §9: production auth, hosted embedding, diagnosis generation, negation/history perfection, reranking models, production-scale infra, visual redesign.
- Opening a PR / pushing code (human decision 2026-07-31: no submission).
- Modifying provided platform code (base schema, embedding service, seed data).

## Open Questions

- Actual remaining time in the 48h window (repo access start unknown) — plan assumes ~8–12 focused hours suffice.
