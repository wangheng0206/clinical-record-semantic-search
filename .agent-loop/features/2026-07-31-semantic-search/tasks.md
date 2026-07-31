# Tasks: Clinical Record Semantic Search

Created: 2026-07-31
Updated: 2026-07-31
Status: active

## Execution Mode

Mode: linear
Default Split: vertical-slice

## Task Mode Legend

- Agent-ready: scope, acceptance, boundaries, and verification are clear enough for autonomous execution.
- Human-gated: product, design, architecture, security, data, or approval decisions are needed before execution.

## Status Rules

- Do not mark a task `done` from code changes alone.
- After implementation and fresh verification, use `Status: review` until Task Done Gate passes.
- Task Done Gate: implementation complete, required tests or substitute verification run fresh, evidence recorded in `notes.md`, lightweight Spec Review recorded, Standards Review recorded when triggered, drift decision recorded, and evidence location named below.

## Split Rules

- Prefer vertical slices / tracer bullets.
- T001 is a horizontal foundation task: no retrieval slice is possible before chunk storage exists. Proved by T002/T003 vertical slices.

## Stories to Tasks

- US1: T001, T002
- US2: T003
- US3: T004
- US4: T005, T006

## Stage 1: Foundation

- [x] T001 [US1] Chunk and embedding schema (migration 0002)
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: not-applicable
  - Slice Type: horizontal-foundation
  - Parent:
  - Derived From:
  - Depends on: environment up (`make setup && make seed`)
  - Blocked By:
  - Covers Stories: US1
  - Design Slices: DS-01
  - Human Gate:
  - Acceptance: AC-1 — migration 0002 creates chunk + embedding storage with practice/patient/document/type/position metadata, pgvector index, and safe deletion/update behavior; `make migrate` repeatable; 0001 untouched.
  - Verification: `make migrate` on dev and test databases; schema inspection; migration re-run is a no-op.
  - Evidence: notes.md — migrate applied 0001+0002 on both databases, re-run `skipped` (no-op), `\d document_chunks` shows vector(384) + HNSW + FK cascades
  - Review: Spec Review 2026-07-31 (AC-1 satisfied, schema matches plan DDL); Standards Review 2026-07-31 (data boundary: new tables follow 0001 conventions)
  - Drift: none
  - Proved By Future Slices: T002 (indexing writes through it), T003 (search reads through it)

Barrier:
- Verification: `make migrate` green on both databases.

## Stage 2: Indexing And Retrieval Core

- [x] T002 [US1] Indexing workflow (`make index`)
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: not-applicable
  - Slice Type: vertical
  - Parent:
  - Derived From:
  - Depends on: T001
  - Blocked By:
  - Covers Stories: US1
  - Design Slices: DS-02
  - Human Gate:
  - Acceptance: AC-2, AC-3 — chunked, embedded, stored corpus; idempotent re-run (zero duplicates on unchanged data); changed source reflected; single bad document tolerated; completion summary reported.
  - Verification: pytest for chunking/change-detection/failure tolerance; `make index` twice against real seed + embedding container, comparing chunk counts.
  - Evidence: notes.md — 35 passed (5 chunker unit + AT-01..03 acceptance + provided suites); `make index` #1 scanned=2400 indexed=2398 failed=2 chunks=3958 (136s); #2 indexed=0 skipped=2398 chunks_written=0 (0.35s); db confirms 3958 chunks, 2398 indexed / 2 failed states; ruff clean
  - Review: Spec Review 2026-07-31 (AC-2/AC-3 satisfied); Standards Review 2026-07-31 (no content in logs; per-document transactions)
  - Drift: none

- [x] T003 [US2] Semantic search API (`POST /api/clinical-search`)
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: not-applicable
  - Slice Type: vertical
  - Parent:
  - Derived From:
  - Depends on: T001 (T002 for realistic data; unit tests use deterministic embedding stub)
  - Blocked By:
  - Covers Stories: US2
  - Design Slices: DS-03, DS-04
  - Human Gate:
  - Acceptance: AC-4, AC-5, AC-6 — vector-ranked practice-isolated results; each patient once with document + excerpt evidence; deliberate empty/invalid/dependency-failure behavior; client-safe errors.
  - Verification: pytest with deterministic embedding stub: isolation, dedup, ranking, validation, failure paths; smoke query against real stack.
  - Evidence: notes.md — 48 passed (unit + acceptance, zero xfail left in acceptance file); integration 7 passed incl. IT-01 (all 6 curated cases, real embedder, 159s); ruff clean
  - Review: Spec Review 2026-07-31 (AC-4/5/6 satisfied); Standards Review 2026-07-31 (isolation in SQL, one embedding call, no internals in errors)
  - Drift: none

Barrier:
- Verification: `make test-api` green including new tests.

## Stage 3: Experience And Proof

- [x] T004 [US3] Search UI (`/search`)
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: not-applicable
  - Slice Type: vertical
  - Parent:
  - Derived From:
  - Depends on: T003 (API contract is fixed by provided schemas; UI can build against contract first)
  - Blocked By:
  - Covers Stories: US3
  - Design Slices: DS-05
  - Human Gate:
  - Acceptance: AC-7 — query input, optional document-type filter, ranked patient results with passages, patient-detail navigation; idle/loading/results/no-results/invalid-input/dependency-failure states.
  - Verification: `make test-web` (at least one state covered); manual run-through of all six states on `make dev`.
  - Evidence: notes.md — vitest 12 passed (2 new SearchResults tests: evidence+navigation render, retrieval-aid score wording); eslint clean; tsc clean. Six-state manual run-through scheduled at T006 (E2E001..003)
  - Review: Spec Review 2026-07-31 (AC-7 satisfied at component level; E2E pending T006)
  - Drift: none

- [x] T005 [US4] Acceptance tests (replace xfail placeholders)
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: accepted (single-file test addition `tests/test_migrations.py` + verification sweep; no behavior change; verification: `pytest -q`)
  - Slice Type: vertical
  - Parent:
  - Derived From:
  - Depends on: T002, T003 (placeholders target real behavior)
  - Blocked By:
  - Covers Stories: US4
  - Design Slices: DS-01..DS-05 (coverage sweep)
  - Human Gate:
  - Acceptance: AC-8 (test half) — placeholders replaced by deterministic tests: indexing safety, practice isolation, result behavior, request validation, one frontend state.
  - Verification: `make test` green with no candidate-owned `xfail` left.
  - Evidence: notes.md — all 9 acceptance placeholders replaced across T002/T003; MT-06 added (migration rerun no-op); backend 49 passed + frontend 12 passed, zero candidate xfail remaining
  - Review: Spec Review 2026-07-31 (AC-8 test half satisfied)
  - Drift: none

- [x] T006 [US4] End-to-end verification + README solution writeup
  - Status: done
  - Mode: Agent-ready
  - No-Plan Decision: accepted (verification sweep + documentation writeup; no new behavior; verification: `make test`, `make smoke`, live curl checks)
  - Slice Type: vertical
  - Parent:
  - Derived From:
  - Depends on: T001–T005
  - Blocked By:
  - Covers Stories: US4
  - Design Slices: DS-05, DS-06
  - Human Gate:
  - Acceptance: AC-8 (smoke half), AC-9 — `make smoke` green; example query returns relevant same-practice patients; practice switching shows isolation; README gains solution section (architecture, trade-offs, simplifications, future extensions); logs free of sensitive content.
  - Verification: fresh clone-style run (`make setup/seed/index/smoke/test/lint/typecheck`), manual UI verification of the design doc §11 checklist.
  - Evidence: notes.md — E2E001 (migraine query → patient-0001 top-1, evidence snippet, +1 doc), E2E002 (lakeshore: no northside patients; own decoy present), E2E003 (EMBEDDING_FAILURE_RATE=1.0 → 503 envelope), log privacy scan clean, `make smoke` ok, README solution notes added, full `make test`/`lint`/`typecheck` green, §11 checklist all confirmed
  - Review: Spec Review 2026-07-31 (AC-8/AC-9 satisfied)
  - Drift: none

Barrier:
- Verification: full Definition-of-done checklist (TAKE_HOME_DESIGN §11) passed and recorded in `notes.md`.

## Task Details

Task-level plans live in `plan.md` per task (Plan Gate before each execution).
