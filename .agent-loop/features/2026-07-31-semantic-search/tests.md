# Test Design: Clinical Record Semantic Search

Created: 2026-07-31
Updated: 2026-07-31
Status: active

AI reviews current top-level `Updated` / `Status`, Design Slice matrix `Status`, and Bug matrix `Result` / `Evidence Link` values directly and owns test semantics.

## Requirement Checklist

- [x] Requirements are testable and unambiguous (TAKE_HOME_DESIGN §6 + acceptance placeholders define observable behavior).
- [x] Success criteria are measurable (chunk counts, call counts, status codes, patient id sets).
- [x] Edge cases are identified: blank/whitespace documents, oversized document (~100k chars), changed source body, empty index, no semantic match, embedding-service failure, cross-practice decoys, in-practice distractors.

## Design Slice Verification Matrix

No project ADRs. Feature-local design slices (from spec.md Design Decisions):

| Design Slice ID | Required Verification | Test / Evidence | Status |
|---|---|---|---|
| DS-01 schema (migration 0002) | migrate on app+test db; re-run is no-op; FK cascade removes chunks when source document is removed | MT-06, AT-01/AT-02 fixture setup | verified |
| DS-02 chunking + change detection | unit tests for packing/splitting/overlap/blank/oversize; idempotency and re-index acceptance tests | MT-01..MT-05, AT-01, AT-02, AT-03 | verified |
| DS-03 retrieval + practice isolation + aggregation | SQL pre-filter by session practice; best-chunk-per-patient; additionalMatchingDocuments; one embedding call | AT-04, AT-05, AT-06, IT-01 | verified |
| DS-04 request validation + failure behavior | 422 without embedding call (5 payloads); 503 without stack trace; empty index / no match = 200 empty | AT-07, AT-08, MT-07 | verified |
| DS-05 UI states | at least one state in vitest; all six states verified manually | WT-01, E2E001..E2E003 | verified |
| DS-06 privacy in logs | no document bodies, excerpts, patient names, or vectors in logs | manual log inspection during E2E | verified |

## Bug Verification Matrix

Not applicable — this Feature resolves no Bug Records.

## Functional Test Cases

Mapped from `services/api/tests/acceptance/test_acceptance_checklist.py` (xfail placeholders to be replaced):

| ID | Case | Layer | Maps AC |
|---|---|---|---|
| AT-01 | Re-indexing unchanged documents creates no duplicates (chunk count identical after 2nd run) | acceptance (stub embedder) | AC-3 |
| AT-02 | Changed document body is re-indexed (stale chunks gone, replacements reflect new text) | acceptance (stub embedder) | AC-3 |
| AT-03 | Unindexable document does not abort the run (run completes, reports failure, everything else indexed) | acceptance (stub embedder) | AC-2, AC-3 |
| AT-04 | Search never returns a patient from another practice (curated crossPracticeDecoyPatientId absent) | acceptance (stub embedder) | AC-4 |
| AT-05 | Patient with multiple matching documents appears once; additionalMatchingDocuments reflects extra evidence | acceptance (stub embedder) | AC-5 |
| AT-06 | Search performs exactly one embedding call (call_count == 1) | acceptance (stub embedder) | AC-4 |
| AT-07 | Invalid requests rejected without embedding: empty / whitespace-only / over-max-length query, bad document type, limit too large → 422 validation_error, call_count == 0 | acceptance (5 params) | AC-6 |
| AT-08 | Embedding service down → 503, body contains no stack trace / internals | acceptance (UnavailableEmbeddingClient) | AC-6 |
| IT-01 | Curated queries return expectedPatientId within the default result limit (real embedder) | integration (`@pytest.mark.integration`) | AC-4 |

## Module Tests

New unit tests (pytest, deterministic, no containers beyond db where noted):

| ID | Case | Target |
|---|---|---|
| MT-01 | chunker packs paragraphs up to the char ceiling and never emits a chunk over the hard 8,000-char service limit | `app/features/indexing/chunking.py` |
| MT-02 | chunker splits an over-ceiling paragraph at sentence boundaries, then hard-cuts as last resort | chunking |
| MT-03 | chunker emits overlap context between consecutive chunks; chunk ids are deterministic (`<document_id>:<index>`) | chunking |
| MT-04 | blank / whitespace-only body produces zero chunks and a skip reason (not an exception) | chunking |
| MT-05 | content hash changes when body/title changes; identical content → identical hash | `app/features/indexing/` change detection |
| MT-06 | migration 0002 applies and re-applies as no-op on the test database | `database/migrations/0002_*.sql` via `apply_migrations` |
| MT-07 | search on empty index returns 200 with empty results (not an error) | search feature |

## API Tests

Covered by AT-01..AT-08 through the `api` ASGI fixture with `SingleConnectionPool` and `StubEmbeddingClient`, using `northside_headers` / `lakeshore_headers` / `summit_headers` tokens. Isolation assertions use `curated_cases.json` decoys.

## Web E2E Cases

Project E2E Capability:
- Source: .agent-loop/project.md
- Status: partial — `make dev` provides web :3000 + api :8000; no browser automation framework configured in the repo, so E2E is manual with recorded evidence.

Feature E2E Cases:
- E2E001 [US3] Example query end-to-end
  - URL: http://localhost:3000/search
  - Preconditions: `make setup && make seed && make index && make dev`; identity = northside
  - Test Data: curated case `case-migraine-aura` query
  - Steps: enter query, submit, read results, open patient detail
  - Assertions: ranked patient list with document title/type/date + excerpt; `patient-0001` present; result links to `/patients/patient-0001`; no score labelled as confidence
  - Automation: manual
  - Evidence to record: notes.md (observed result summary)
- E2E002 [US2] Practice isolation via identity switch
  - URL: /search
  - Steps: run same query as northside, then switch identity to lakeshore and repeat
  - Assertions: lakeshore results contain no northside-only curated patients; decoy patients never cross
  - Automation: manual
- E2E003 [US3] Dependency-failure state
  - URL: /search
  - Preconditions: `EMBEDDING_FAILURE_RATE=1.0`
  - Assertions: UI shows the dependency-failure state, not a crash or blank page
  - Automation: manual

Blocked / Manual:
- All three cases are manual by design; no Playwright/Cypress exists in the scaffold and adding one is out of scope (proportionality, TAKE_HOME_DESIGN §8).

## Regression Tests

- `make test` (backend + frontend) must stay green, including provided suites (`test_patients.py`, `test_session.py`, `test_health.py`, web component tests).
- `make lint && make typecheck` clean.

## Manual Verification

- `make index` twice on the real stack: second run reports zero new chunks (idempotency on real embedder).
- `make smoke` green (db + seed + real embedding call).
- Log inspection during indexing and a failed search: diagnostics present; no document bodies, excerpts, patient names, or vectors.
- Definition-of-done checklist (TAKE_HOME_DESIGN §11) walked through item by item at T006.

## Test Commands

- `make test-api` — pytest backend suite (unit + acceptance, stub embedder)
- `make test-web` — vitest frontend suite
- `make test-integration` — real embedding container tests (IT-01)
- `make smoke` — db + seed + real embedding call
- `make lint && make typecheck` — ruff, eslint, types
