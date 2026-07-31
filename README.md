# Clinical Record Semantic Search — take-home exercise

Make a corpus of synthetic clinical records semantically searchable, end to end.

A user types a natural-language description:

> recurring headaches preceded by flashing lights, nausea, and sensitivity to light

and gets a ranked list of patients **in their own practice** whose existing notes and
reports are relevant, each with the specific document and passage that explains the match.

This is retrieval. It must not generate a diagnosis, infer a condition that is not already
in the records, or present a similarity score as clinical confidence.

**Read [`docs/TAKE_HOME_DESIGN.md`](docs/TAKE_HOME_DESIGN.md) first.** It is the
specification; this file is the operating manual.

---

## Quick start

Requirements: Docker with Compose v2. Nothing else — Python, Node, pnpm, and the embedding
model all live inside the images.

```bash
cp .env.example .env
make setup     # build images, start services, apply migrations
make seed      # load the synthetic dataset
make dev       # web on http://localhost:3000, API on http://localhost:8000
```

In another shell:

```bash
make test      # backend and frontend suites
make smoke     # confirm database, seed data, and a real embedding call
```

`make index` is wired up but exits with a message: building the index is your task.

<details>
<summary>Without <code>make</code> (Windows PowerShell, or a bare shell)</summary>

Every target is one or two Compose commands.

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d db embedding api
docker compose run --rm api python -m app.scripts.wait_for_dependencies
docker compose exec -T api python -m app.scripts.migrate
docker compose exec -T api python -m app.scripts.migrate --database test
docker compose exec -T api python -m app.scripts.seed
docker compose up                                              # make dev
docker compose exec -T api pytest -q                           # make test-api
docker compose run --rm --no-deps web pnpm test                 # make test-web
```

`make help` lists every target with its description.
</details>

The first build downloads the embedding model (~90 MB) into the image. Later builds are
cached, and nothing reaches the network at run time.

---

## What you are given

| Area | State |
|---|---|
| Next.js 16 app shell, layout, navigation, design-system primitives | Provided |
| Mock session with a practice switcher | Provided |
| Patient detail route `/patients/[patientId]` | Provided and working |
| `/search` route | **Shell only — yours to build** |
| FastAPI service, config, connection pool, error envelope, request logging | Provided |
| Migration runner, seed loader, health endpoint | Provided |
| Embedding service (ONNX MiniLM, 384-dim) | Provided, not part of the assignment |
| Embedding client with batching and error translation | Provided |
| Synthetic dataset: 3 practices, 715 patients, 2,400 documents | Provided |
| Test harness, fixtures, deterministic embedding stub | Provided |
| Base tables `practices`, `users`, `patients`, `clinical_documents` | Provided |
| Chunk and embedding storage | **Yours to design** |
| Indexing workflow | **Yours to build** |
| `POST /api/clinical-search` | **Returns 501 — yours to build** |
| Acceptance tests | **Yours to write** |

### Where your work goes

| Task | Start here |
|---|---|
| Chunk and embedding schema | [`database/migrations/README.md`](database/migrations/README.md) |
| Indexing workflow | [`services/api/app/features/indexing/README.md`](services/api/app/features/indexing/README.md) |
| Search endpoint | [`services/api/app/features/search/README.md`](services/api/app/features/search/README.md) |
| Search UI | [`apps/web/features/search/README.md`](apps/web/features/search/README.md) |
| Tests | [`services/api/tests/acceptance/README.md`](services/api/tests/acceptance/README.md) |
| Synthetic dataset | [`docs/DATASET.md`](docs/DATASET.md) |

---

## Session and practice context

The provided mock session associates each demo user with one practice. The search request
must not accept a client-selected practice identifier, and results must remain isolated to
the authenticated user's current practice.

Use the dropdown in the header to switch between the supplied demo identities while
testing. The implementation of the search boundary is part of the exercise.

---

## Layout

```text
├── apps/web/                     Next.js 16, App Router, Tailwind v4
│   ├── app/                      routes: /, /search, /patients/[id], /api/demo-session
│   ├── components/ui/            design-system primitives
│   ├── features/                 feature-local code — search goes here
│   └── lib/                      server-only API client, types, formatting
├── services/
│   ├── api/                      FastAPI
│   │   ├── app/features/         health, session, patients, search*, indexing*
│   │   ├── app/clients/          embedding client
│   │   ├── app/scripts/          migrate, seed, index*, smoke, wait_for_dependencies
│   │   └── tests/                harness, worked examples, acceptance skeletons*
│   └── embedding/                provided embedding service
├── database/
│   ├── init/                     first-boot extension and test database
│   ├── migrations/               0001 base schema; add 0002 for your chunks*
│   └── seed/                     generator plus committed CSVs
└── docs/                         design document and dataset notes

* your work
```

---

## Configuration

Copy `.env.example` to `.env`. It holds no credentials worth protecting and is safe to
commit as an example; `.env` itself is git-ignored.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://clinical:local_dev_only@db:5432/clinical_search` | |
| `TEST_DATABASE_URL` | …`/clinical_search_test` | Created on first boot |
| `EMBEDDING_SERVICE_URL` | `http://embedding:8080` | |
| `EMBEDDING_MAX_BATCH_SIZE` | `64` | Service rejects larger batches |
| `SEARCH_DEFAULT_LIMIT` | `10` | |
| `SEARCH_MAX_LIMIT` | `25` | |
| `SEARCH_MAX_QUERY_LENGTH` | `500` | |
| `EMBEDDING_FAILURE_RATE` | `0.0` | Set to `1.0` to exercise the failure UI |
| `API_BASE_URL` | `http://api:8000` | Server-side only |

---

## Provided service contracts

Review [`services/embedding/README.md`](services/embedding/README.md) for the embedding API,
input limits, and failure responses. Respecting that contract is required; how it shapes
your implementation is a design decision.

---

## Testing

```bash
make test              # backend + frontend, no containers beyond the database
make test-api
make test-web
make test-integration  # needs the real embedding container
make lint              # ruff, eslint
make typecheck
```

A fresh clone is green. Candidate-owned acceptance placeholders remain marked `xfail` until
their behavior is implemented and tested.

---

## Submitting

Open a pull request against `main` and complete the
[`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md) provided beside this README. It asks
for architecture, tradeoffs, chunking and ranking decisions, limitations, and AI-tool
disclosure.

If you run out of time, submit what works and be explicit about what is incomplete. That is
read as good judgement. Polish does not substitute for practice isolation, source evidence,
idempotent indexing, or a working end-to-end flow.

---

## Troubleshooting

**`make setup` cannot reach the Docker daemon** — start Docker Desktop and retry.

**Database container exits immediately** — the volume was created by an older Postgres.
`make destroy` then `make setup`.

**`pgvector types are not available`** — migrations have not run. `make migrate`.

**Search returns 501** — expected. That endpoint is your task.

**Integration tests skip** — the embedding container is not up.
`docker compose up -d embedding`, then wait for its health check.

**Web shows "The API is not reachable"** — check `docker compose logs api`. The API needs a
migrated database to answer `/api/session`.

**`pnpm install` warns about ignored build scripts** — already handled via
`onlyBuiltDependencies` in `apps/web/package.json`; run `pnpm install` once more.

---

## Solution notes (candidate)

This section is the required writeup: architecture, key decisions and trade-offs,
intentional simplifications, known limitations, and future extensions.

### Architecture and data flow

```text
clinical_documents (provided)
  → chunking (app/features/indexing/chunking.py, pure stdlib)
  → EmbeddingClient (provided, batches of 64)
  → document_chunks (vectors + practice/patient/type metadata)
  → document_index_state (per-document content hash + status)

POST /api/clinical-search
  → session context (practice from users table, never from the request)
  → pydantic validation (422 before any embedding call)
  → one embed([query]) call
  → pgvector cosine search pre-filtered by practice_id (+ optional type filter)
  → patient-level aggregation (best chunk per patient)
  → ranked results with document + passage evidence
```

The UI submits through a Next.js Server Action (`apps/web/features/search/actions.ts`);
the browser never calls the API directly and never sees a practice selector.

### Schema (migration 0002)

Two tables. `document_chunks` stores one row per chunk with a deterministic id
(`<document_id>:<chunk_index>`), the embedding, and denormalized
`practice_id` / `patient_id` / `document_type`. Denormalization is deliberate:
retrieval filters by practice inside the same SQL query without joining back, and
the `(practice_id, document_type)` index supports the optional type filter. An HNSW
index over `vector_cosine_ops` serves `<=>` distance. Both tables cascade on source
deletes, so a reseed wipes derived data and the next run re-indexes cleanly.
`document_index_state` holds each document's content hash, status
(`indexed` / `failed`), and a short failure reason, which is what makes re-runs
idempotent and bad documents visible. `0001_base_schema.sql` is untouched.

### Chunking

Paragraph-boundary greedy packing with a ~1,000-character target (the embedding
service caps input at 256 tokens; ~4 chars/token for English prose keeps every
chunk inside the model's context) and a 150-character overlap between consecutive
chunks so context that straddles a boundary is not lost. Oversized single
paragraphs split at sentence boundaries, then hard-cut as a last resort. Every
chunk is ≤ ~1,150 chars, far below the 8,000-character service limit, so the
service never rejects a chunk for length. Blank documents produce zero chunks and
are recorded as `failed` with reason `blank_body` instead of aborting the run.

Trade-off: small chunks improve focus but can split a clinical narrative. The
overlap mitigates this; a structure-aware splitter (section headings) is a future
refinement.

### Change detection and idempotency

`content_hash = sha256(normalized title + body)` per document. On each run: hash
match + `indexed` → skip; hash differs → delete that document's chunks and
re-index inside one per-document transaction; `failed` → retry. Per-document
transactions mean one bad document cannot corrupt the run, and a service-level
embedding failure aborts the run with everything already committed intact (a rerun
resumes from the hash ledger). Deterministic chunk ids make re-inserts physically
idempotent as well.

### Retrieval, ranking, aggregation

Single round trip: `ORDER BY embedding <=> $1` over chunks filtered by
`practice_id` (and optional document types), over-fetching `max(limit × 5, 25)`
candidate chunks. Aggregation then keeps each patient once, picks their
lowest-distance chunk as the evidence (`bestMatch`), and reports
`additionalMatchingDocuments` as the number of other distinct documents that
patient matched inside the candidate set. `relevanceScore = 1 − cosine distance`,
exposed strictly as a retrieval aid — it is never labelled confidence or
probability, in the API or the UI.

HNSW recall: pgvector's approximate search at the default `ef_search=40` can
silently drop a true nearest chunk from the candidate set (observed here on a
curated case: the expected patient's best chunk at distance 0.47 never reached
the approximate top-50). The repository sets `SET LOCAL hnsw.ef_search = 400`
per query — exact-grade recall at the ~4k-chunk scale for negligible cost, and
the one knob to revisit (with measurements) when the corpus grows orders of
magnitude.

Trade-offs: max-score aggregation rewards the single best passage over document
volume (a patient with one highly relevant note ranks above one with many weakly
relevant ones). Over-fetch × 5 is a heuristic; with ~4k chunks it is cheap and has
not missed expected patients in the curated integration cases. A two-stage
reranker is intentionally out of scope per the assignment.

### Practice isolation

The practice boundary lives entirely server-side: the session token resolves to a
user, the user's `practice_id` is a SQL `WHERE` clause in the retrieval query, and
the request schema has no practice field (a client-supplied one is rejected by
validation). Isolation is pre-filter, not post-filter, so cross-practice rows are
never even read into ranking — verified by an acceptance test whose cross-practice
decoy would top the list unfiltered (exact-text match) yet never appears.

### Failure handling

- Blank / embedding-rejected documents: recorded `failed` with a reason, run continues, retried next run.
- Embedding service down during indexing: run aborts (systemic, not per-document); committed work stays.
- Embedding service down during search: 503 `embedding_service_unavailable` envelope, no internals, UI shows a dedicated failure state (`EMBEDDING_FAILURE_RATE=1.0` exercises it).
- Empty index / no match: 200 with an empty result list, plus an explicit no-results UI state.
- Invalid requests (blank/oversized query, bad type, oversized limit): 422 `validation_error` with zero embedding calls.

### Operational visibility and privacy

Indexing prints `scanned / indexed / skipped / failed / chunks_written / duration`
plus failed document ids with reason codes; the API logs request ids, counts, and
status codes only. Logs never contain document bodies, passages, patient names, or
vectors (verified by scanning logs after failure and success paths).

### Intentional simplifications

- Per-document embedding calls during indexing (clear failure attribution; ~2 min for 2,400 documents) instead of cross-document batch packing.
- `max`-score patient aggregation instead of count- or mean-weighted scoring.
- Full-chunk snippet (already an excerpt ≤ ~1,150 chars) instead of a second summarization pass.
- No reranking, no hybrid keyword+vector retrieval, no browser E2E framework (the repo ships none); frontend states are covered by component tests plus manual verification.

### Known limitations / incomplete

- Nothing in the assignment scope is left unimplemented: schema, indexing, search API, search UI, and acceptance tests are all delivered and green.
- Re-running `make seed` truncates the source tables and cascades into the derived tables, so the next `make index` re-indexes everything (correct, but full rebuild; acceptable at this scale).
- The chunker is paragraph/length based, not clinical-section aware; negation and history handling rely on the embedding model, as permitted by the assignment's out-of-scope list.

### Environment notes (this machine)

Two network/workstation issues required workarounds that do not touch provided files;
document them if you reproduce the setup behind a restricted network:

1. `docker.io` was unreachable — base images were pre-pulled via
   `mirror.gcr.io/library/...` and tagged to their canonical names.
2. `huggingface.co` was unreachable — the ONNX model files were fetched from a
   mirror and injected at build time with BuildKit
   `--build-context model=<dir>`, leaving `services/embedding/Dockerfile` untouched.
3. On Docker Desktop for macOS, `database/init/00-create-databases.sh` (committed
   non-executable) fails to run on first boot; the test database and pgvector
   extension were created manually with the same SQL the script contains.

### Future extensions

- Hybrid retrieval (pgvector + `tsvector` keyword score) for exact-term anchors like drug names.
- Section-aware chunking and per-type chunk profiles (labs vs narrative notes).
- Reranking stage and patient-level recency weighting.
- Incremental indexing trigger on `source_updated_at` instead of command runs.
- Streaming/debounced UI search and saved queries.

### Verification summary

- `pytest -q`: 49 passed (unit + acceptance, zero candidate `xfail` left)
- `pytest -q -m integration`: 7 passed against the real embedding service (all 6 curated cases)
- `pnpm test`: 12 passed; `pnpm lint`, `pnpm typecheck`, `ruff check`, `ruff format --check` clean
- `make index` twice: 3,958 chunks written once, zero new chunks on rerun; `make smoke`: ok
- Manual E2E: example query ranks the expected migraine patient first with evidence; practice switch proves isolation; `EMBEDDING_FAILURE_RATE=1.0` proves the failure path

### AI-tool disclosure

**Tools used:** Kimi Code CLI (an AI coding assistant run under an agent-loop
spec/plan/TDD workflow) for the bulk of the implementation; Docker/Make/pytest/
vitest for verification; my IDE for reviewing the full diff.

**Where they materially contributed:** decomposing the assignment into the six
work items; the schema, chunking, change-detection, and ranking design; all
backend and frontend implementation code and tests; the two environment
workarounds (registry mirror, model-file injection); and the first draft of these
solution notes.

**How I reviewed or tested the generated work:** I approved the design at two
explicit gates before any implementation, then verified every claim by running
it: backend suite (49 passed), frontend suite (12 passed), integration suite
against the real embedding service (7 passed, all six curated cases), `make index`
twice to prove idempotency, live requests as two different practices to prove
isolation, `EMBEDDING_FAILURE_RATE=1.0` to prove the 503 path, a log scan for
content leakage, and a manual run of the app in the browser. I reviewed the
complete diff in my IDE before accepting it.

**Suggestions I rejected, changed, or independently verified:**

1. The assistant's first acceptance fixture for patient aggregation assumed the
   deterministic embedding stub preserves text similarity (near-identical texts
   embed closely). It does not — the stub is sha256-based — so I changed the
   fixture to identical document bodies (identical vectors) and kept the semantic
   ranking proof in the real-embedder integration test instead.
2. When the environment broke (docker.io / huggingface.co unreachable, a
   non-executable init script under Docker Desktop), the straightforward fixes
   would have edited provided platform files. I rejected that and used
   non-invasive workarounds (mirror pulls, a BuildKit `--build-context` override,
   manual SQL), keeping every provided file untouched.
3. Before implementation I cross-checked the plan's predicted chunk counts and
   failure set against the real seed dataset (3,958 chunks, 2 blank documents);
   the plan matched, which is what let the indexing task land without rework.
