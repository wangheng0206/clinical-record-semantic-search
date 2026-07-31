# Execution Plan

Plan ID: 2026-07-31-us1-searchable-index
Created: 2026-07-31
Updated: 2026-07-31
Active Since: 2026-07-31
Status: active
Supersedes: none

Bug Context Evidence: none
Related Bug IDs: none

Plan Scope:
- Type: story
- ID: US1
- Title: Searchable representation and indexing
- Included Tasks: T001 (migration 0002), T002 (indexing workflow)
- Design Slices: DS-01 schema, DS-02 chunking + change detection

Branch Context Evidence:
- Branch Strategy Status / Profile: not-needed / not-applicable (local-only delivery)
- Target Release Context: not-applicable
- Target Branch: not-applicable
- Current Branch Context Evidence: `notes.md#current-branch-context`
- Sealed Check: not-applicable
- Customer Isolation Check: not-applicable
- Git actions authorized by this plan: none

Feature Context: `scripts/check-feature-context.py` = CURRENT (2026-07-31). Product Slice: `product.md#in-scope` (searchable representation + indexing workflow). Acceptance: AC-1, AC-2, AC-3. Invariants preserved: base schema 0001 untouched; embedding service contract respected (≤64 texts/request, ≤8,000 chars/text, blank rejected); no document content in logs.

## Goal

Create the chunk/embedding storage (migration 0002) and the idempotent indexing workflow so `make index` turns the seeded corpus into searchable vectors, repeatably and with per-document failure tolerance.

## Architecture Summary

`clinical_documents` (provided) → chunker (pure function, stdlib only) → `EmbeddingClient.embed` (provided, batches at 64) → `document_chunks` (new, vectors + source metadata) with `document_index_state` (new, per-document content hash + status) driving idempotency and failure reporting. One transaction per document: a failed document never corrupts the rest of the run. Service-level embedding failure aborts the run (already-committed documents stay indexed; rerun resumes).

## Technical Context

- Language/Version: Python 3.13
- Frameworks/Libraries: FastAPI 0.140, asyncpg 0.31, pgvector 0.5, pydantic 2.13 (provided; no new dependencies)
- Runtime: Docker Compose (`api`, `db`, `embedding` services)
- Storage/Data: PostgreSQL 18 + pgvector; 2,400 documents, median body ~1.2k chars, max ~100k chars, 2 blank bodies
- Testing: pytest 9 + pytest-asyncio (asyncio_mode=auto), `StubEmbeddingClient` deterministic stub, test db via `prepared_database` fixture
- Target Platform: local Docker on macOS
- Constraints: ruff line-length 100; never modify 0001; no document content in logs; migration files run in filename order inside a transaction
- Scale/Scope: ~2,400 documents → ~4,000–5,000 chunks; trivial for HNSW

## Source Structure Decision

- Existing structure followed: feature-local modules under `app/features/<feature>/`; module-level SQL constants + dataclasses (patients/repository.py pattern); script wiring under `app/scripts/`; migration as new numbered file.
- New structure: `app/features/indexing/chunking.py` + `app/features/indexing/runner.py` (feature README directs implementation here).
- Why: keeps chunking pure/testable without db; runner owns db + embedding orchestration; script is thin.

## Files

- Create: `database/migrations/0002_document_chunks.sql`
- Create: `services/api/app/features/indexing/chunking.py`
- Create: `services/api/app/features/indexing/runner.py`
- Modify: `services/api/app/scripts/index_clinical_documents.py` (replace stub)
- Test: `services/api/tests/test_indexing_chunking.py` (new)
- Test: `services/api/tests/acceptance/test_acceptance_checklist.py` (replace 3 xfail placeholders: AT-01, AT-02, AT-03)
- Read: `services/api/app/db/pool.py`, `services/api/app/clients/embedding.py`, `services/api/tests/conftest.py`, `services/api/tests/stubs.py`

## Code Context

Existing functions/classes/modules:
- `apply_migrations(pool, migrations_dir)` in `app/db/migrations.py`: applies `*.sql` in filename order, each in a transaction, ledger table `schema_migrations`; rerun skips applied files.
- `open_pool(dsn, min_size, max_size)` in `app/db/pool.py`: async context manager; pool `init` registers pgvector per connection (vectors can be passed as `list[float]`).
- `EmbeddingClient.embed(texts)` in `app/clients/embedding.py`: batches by 64; raises `EmbeddingInputRejected` on 422 (blank/over-length), `EmbeddingServiceError` on transport/5xx. `SupportsEmbedding` Protocol = test seam.
- `StubEmbeddingClient` in `tests/stubs.py`: deterministic vectors; rejects blank and >8,000-char texts; records `calls`.
- `SingleConnectionPool` in `tests/conftest.py`: wraps the test `connection` fixture as a pool; conftest connection already runs `register_vector`.
- Migration SQL style in `0001_base_schema.sql`: `text` PKs, `timestamptz DEFAULT now()`, CHECK constraints, `document_type` enum.

Existing patterns to follow:
- Module-level SQL constants, `dataclass(frozen=True)` records, `pool.fetchrow/fetch` (patients/repository.py).
- Script pattern: argparse/asyncio.run/configure_logging/exit codes (migrate.py, seed.py).

Call chain:

```text
make index
  → docker compose run api python -m app.scripts.index_clinical_documents
  → run() → EmbeddingClient(settings) + open_pool(database_url)
  → index_documents(pool, embedding)
  → per document: content_hash → state lookup → chunk_document → embedding.embed → tx(DELETE+INSERT chunks, UPSERT state)
```

Data flow: CSV seed → `clinical_documents` → chunks + vectors in `document_chunks`; state in `document_index_state`.

Authorization / validation / side effects: none (operator-run local script). Side effects limited to the two new tables.

## Interface Contracts

### `content_hash`

Location: `services/api/app/features/indexing/chunking.py`
Kind: function
Signature: `content_hash(title: str, body: str) -> str`
Parameters:
- `title`: document title
- `body`: document body
Return: hex sha256 of `f"{title.strip()}\n{body.strip()}"`
Errors: none
Side effects: none
Existing callers: none
New callers: `runner.index_documents`
Tests proving contract: `test_content_hash_tracks_title_and_body`

### `chunk_document`

Location: `services/api/app/features/indexing/chunking.py`
Kind: function
Signature: `chunk_document(body: str, *, target_chars: int = TARGET_CHUNK_CHARS, overlap_chars: int = OVERLAP_CHARS) -> list[str]`
Parameters:
- `body`: raw document body
- `target_chars`: packing ceiling (default 1,000 ≈ ≤256 tokens at ~4 chars/token)
- `overlap_chars`: tail carried into the next chunk (default 150)
Return: chunk texts; `[]` for blank input; every chunk ≤ `target + overlap + 2` ≪ 8,000 hard service limit
Errors: none (blank input returns `[]`, caller records failure)
Side effects: none
Existing callers: none
New callers: `runner.index_documents`
Tests proving contract: MT-01..MT-04 in `tests/test_indexing_chunking.py`

### `index_documents`

Location: `services/api/app/features/indexing/runner.py`
Kind: function
Signature: `index_documents(pool: asyncpg.Pool, embedding: SupportsEmbedding) -> IndexSummary`
Parameters:
- `pool`: asyncpg pool (or `SingleConnectionPool` in tests)
- `embedding`: `SupportsEmbedding` (real client or stub)
Return: `IndexSummary{scanned, skipped_unchanged, indexed, chunks_written, failures, duration_seconds}`; `failed` property
Errors: `EmbeddingServiceError` propagates (systemic failure aborts run); per-document `EmbeddingInputRejected` and blank bodies are recorded as failures and skipped
Side effects: DELETE+INSERT on `document_chunks`, UPSERT on `document_index_state`, one transaction per document
Existing callers: none
New callers: `app/scripts/index_clinical_documents.py::run`
Tests proving contract: AT-01, AT-02, AT-03

### `main`

Location: `services/api/app/scripts/index_clinical_documents.py`
Kind: command
Signature: `main() -> int`
Return: exit code 0 on completed run (per-document failures reported, not fatal); 1 on fatal (embedding unhealthy at start, service failure mid-run, db error)
Side effects: prints summary counts + failed document ids with reasons (no content)
Tests proving contract: manual `make index` twice at T006; AT-01..03 cover the runner

## Data / API Contract

Persistence (migration `0002_document_chunks.sql`):

```sql
CREATE TABLE document_index_state (
    document_id      text PRIMARY KEY REFERENCES clinical_documents (id) ON DELETE CASCADE,
    content_hash     text NOT NULL,
    chunk_count      integer NOT NULL,
    status           text NOT NULL,
    failure_reason   text,
    indexed_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_index_state_status_allowed CHECK (status IN ('indexed', 'failed'))
);

CREATE TABLE document_chunks (
    id              text PRIMARY KEY,
    document_id     text NOT NULL REFERENCES clinical_documents (id) ON DELETE CASCADE,
    practice_id     text NOT NULL REFERENCES practices (id) ON DELETE CASCADE,
    patient_id      text NOT NULL REFERENCES patients (id) ON DELETE CASCADE,
    document_type   document_type NOT NULL,
    chunk_index     integer NOT NULL,
    content         text NOT NULL,
    embedding       vector(384) NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_chunks_document_chunk_key UNIQUE (document_id, chunk_index),
    CONSTRAINT document_chunks_content_not_blank CHECK (btrim(content) <> '')
);

CREATE INDEX document_chunks_practice_type_idx
    ON document_chunks (practice_id, document_type);
CREATE INDEX document_chunks_patient_idx ON document_chunks (patient_id);
CREATE INDEX document_chunks_embedding_hnsw_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

Design notes:
- Chunk id = `<document_id>:<chunk_index>` (deterministic → physical idempotency; re-insert after DELETE is stable).
- `practice_id`/`patient_id`/`document_type` denormalized onto the chunk: search pre-filters by practice inside SQL without joining back; `(practice_id, document_type)` index supports the optional type filter; HNSW cosine index for `<=>` distance.
- Both tables CASCADE on source delete: a reseed (`TRUNCATE ... CASCADE`) clears derived data, so the next run re-indexes from the fresh source of truth.
- `document_index_state` also records `failed` rows with a short reason code, so bad documents are visible and retried on the next run.

Migration: new file only; runner is the provided `apply_migrations` (transactional, ledgered).

## Steps

- [ ] Step 1: Write failing chunker unit tests (RED)

File: `services/api/tests/test_indexing_chunking.py`

```python
from app.features.indexing.chunking import (
    HARD_MAX_CHARS,
    OVERLAP_CHARS,
    TARGET_CHUNK_CHARS,
    chunk_document,
    content_hash,
)

CHUNK_CEILING = TARGET_CHUNK_CHARS + OVERLAP_CHARS + 2


def test_paragraphs_are_packed_up_to_the_target() -> None:
    paragraphs = [f"Paragraph {index} " + "x" * 400 for index in range(4)]
    chunks = chunk_document("\n\n".join(paragraphs))
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CEILING
        assert len(chunk) <= HARD_MAX_CHARS


def test_blank_body_produces_no_chunks() -> None:
    assert chunk_document("   \n\t \n") == []


def test_oversized_paragraph_is_split_without_losing_order() -> None:
    sentences = [f"Sentence {index} ends here." for index in range(120)]
    chunks = chunk_document(" ".join(sentences))
    assert len(chunks) >= 3
    rejoined = " ".join(chunks)
    assert "Sentence 0 ends here." in rejoined
    assert "Sentence 119 ends here." in rejoined
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CEILING


def test_consecutive_chunks_overlap_for_context() -> None:
    paragraphs = [f"P{index} " + "y" * 600 for index in range(3)]
    chunks = chunk_document("\n\n".join(paragraphs))
    assert len(chunks) >= 2
    first_tail = chunks[0][-OVERLAP_CHARS:].lstrip()
    assert first_tail
    assert chunks[1].startswith(first_tail[:40])


def test_content_hash_tracks_title_and_body() -> None:
    base = content_hash("Title", "Body text")
    assert base == content_hash("Title", "Body text")
    assert base != content_hash("Title", "Body text changed")
    assert base != content_hash("Title changed", "Body text")
```

Run:

```text
docker compose exec -T api pytest tests/test_indexing_chunking.py -q
```

Expected RED:

```text
ModuleNotFoundError: No module named 'app.features.indexing.chunking'
```

- [ ] Step 2: Implement the chunker (GREEN)

File: `services/api/app/features/indexing/chunking.py`

```python
"""Split clinical document bodies into embedding-sized chunks.

Sizing rationale: the embedding service accepts at most 256 tokens and
8,000 characters per text. English clinical prose averages ~4 characters
per token, so a 1,000-character packing target keeps every chunk inside
the token limit and far below the character hard limit.
"""

from __future__ import annotations

import hashlib
import re

TARGET_CHUNK_CHARS = 1_000
OVERLAP_CHARS = 150
HARD_MAX_CHARS = 8_000

_BLANK_LINE = re.compile(r"\n\s*\n+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def content_hash(title: str, body: str) -> str:
    """Stable hash of the searchable source content (title + body)."""
    normalized = f"{title.strip()}\n{body.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _split_oversized(paragraph: str, target_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(paragraph):
        candidate = f"{current} {sentence}" if current else sentence
        if current and len(candidate) > target_chars:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
        while len(current) > target_chars:
            pieces.append(current[:target_chars])
            current = current[target_chars:]
    if current:
        pieces.append(current)
    return pieces


def chunk_document(
    body: str,
    *,
    target_chars: int = TARGET_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[str]:
    """Split *body* into overlapping chunks. Blank input yields no chunks."""
    text = body.strip()
    if not text:
        return []

    pieces: list[str] = []
    for paragraph in _BLANK_LINE.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= target_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_oversized(paragraph, target_chars))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(candidate) > target_chars:
            chunks.append(current)
            tail = current[-overlap_chars:].lstrip()
            current = f"{tail}\n\n{piece}" if tail else piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
```

Run:

```text
docker compose exec -T api pytest tests/test_indexing_chunking.py -q
```

Expected GREEN:

```text
5 passed
```

- [ ] Step 3: Add migration 0002 and verify it applies (foundation)

File: `database/migrations/0002_document_chunks.sql` — exact DDL from "Data / API Contract" above.

Run:

```text
docker compose exec -T api python -m app.scripts.migrate
docker compose exec -T api python -m app.scripts.migrate --database test
```

Expected GREEN (first run): `applied 0002_document_chunks.sql`; second run of the same command: `skipped 0002_document_chunks.sql` (ledger no-op). Verify schema:

```text
docker compose exec -T db psql -U clinical -d clinical_search -c '\d document_chunks'
```

Expected: columns and constraints as in the DDL, `embedding | vector(384)`.

- [ ] Step 4: Write failing acceptance tests for the runner (RED)

File: `services/api/tests/acceptance/test_acceptance_checklist.py` — replace the three xfail placeholders with real tests (keep the remaining xfail placeholders for T003):

```python
async def _run_index(connection: asyncpg.Connection, embedding_client: StubEmbeddingClient):
    from app.features.indexing.runner import index_documents
    from tests.conftest import SingleConnectionPool

    return await index_documents(SingleConnectionPool(connection), embedding_client)


async def test_reindexing_unchanged_documents_creates_no_duplicates(
    connection: asyncpg.Connection, embedding_client: StubEmbeddingClient
) -> None:
    first = await _run_index(connection, embedding_client)
    count_first = await connection.fetchval("SELECT count(*) FROM document_chunks")
    second = await _run_index(connection, embedding_client)
    count_second = await connection.fetchval("SELECT count(*) FROM document_chunks")
    assert count_first > 0
    assert count_second == count_first
    assert second.indexed == 0
    assert second.skipped_unchanged == first.indexed


async def test_changed_document_is_reindexed(
    connection: asyncpg.Connection, embedding_client: StubEmbeddingClient
) -> None:
    await _run_index(connection, embedding_client)
    document_id = "document-000001"
    old = await connection.fetch(
        "SELECT id, content FROM document_chunks WHERE document_id = $1 ORDER BY chunk_index",
        document_id,
    )
    assert old
    await connection.execute(
        "UPDATE clinical_documents SET body = $1 WHERE id = $2",
        "Updated assessment: patient reports a completely new symptom pattern.",
        document_id,
    )
    await _run_index(connection, embedding_client)
    new = await connection.fetch(
        "SELECT id, content FROM document_chunks WHERE document_id = $1 ORDER BY chunk_index",
        document_id,
    )
    assert any("completely new symptom pattern" in row["content"] for row in new)
    old_ids = {row["id"] for row in old}
    new_ids = {row["id"] for row in new}
    stale = old_ids - new_ids
    if stale:
        remaining = await connection.fetchval(
            "SELECT count(*) FROM document_chunks WHERE id = ANY($1)", list(stale)
        )
        assert remaining == 0


async def test_unindexable_document_does_not_abort_the_run(
    connection: asyncpg.Connection, embedding_client: StubEmbeddingClient
) -> None:
    summary = await _run_index(connection, embedding_client)
    total = await connection.fetchval("SELECT count(*) FROM clinical_documents")
    assert summary.scanned == total
    assert summary.failed >= 1
    assert summary.indexed == total - summary.failed
    for failure in summary.failures:
        assert failure.reason
    states = await connection.fetch(
        "SELECT status, count(*) AS n FROM document_index_state GROUP BY status"
    )
    by_status = {row["status"]: row["n"] for row in states}
    assert by_status.get("failed") == summary.failed
    assert by_status.get("indexed") == summary.indexed
```

(Also remove the three `@pytest.mark.xfail` markers for these tests.)

Run:

```text
docker compose exec -T api pytest tests/acceptance/test_acceptance_checklist.py -q
```

Expected RED:

```text
ModuleNotFoundError: No module named 'app.features.indexing.runner'
```

- [ ] Step 5: Implement the runner (GREEN)

File: `services/api/app/features/indexing/runner.py`

```python
"""Idempotent indexing run over clinical_documents.

One transaction per document: an individual bad document is recorded in
document_index_state and skipped without affecting the rest of the run.
Systemic embedding failures (service down) propagate and abort the run;
already-indexed documents stay committed and are skipped on rerun.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import asyncpg

from app.clients.embedding import EmbeddingInputRejected, SupportsEmbedding
from app.features.indexing.chunking import chunk_document, content_hash

logger = logging.getLogger("api.indexing")

DOCUMENTS_SQL = """
SELECT id, practice_id, patient_id, document_type, title, body
FROM clinical_documents
ORDER BY id
"""

STATE_SQL = "SELECT content_hash, status FROM document_index_state WHERE document_id = $1"

INSERT_CHUNK_SQL = """
INSERT INTO document_chunks
    (id, document_id, practice_id, patient_id, document_type,
     chunk_index, content, embedding)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""

DELETE_CHUNKS_SQL = "DELETE FROM document_chunks WHERE document_id = $1"

UPSERT_STATE_SQL = """
INSERT INTO document_index_state
    (document_id, content_hash, chunk_count, status, failure_reason, indexed_at)
VALUES ($1, $2, $3, $4, $5, now())
ON CONFLICT (document_id) DO UPDATE SET
    content_hash = EXCLUDED.content_hash,
    chunk_count = EXCLUDED.chunk_count,
    status = EXCLUDED.status,
    failure_reason = EXCLUDED.failure_reason,
    indexed_at = EXCLUDED.indexed_at
"""


@dataclass(frozen=True)
class DocumentFailure:
    document_id: str
    reason: str


@dataclass
class IndexSummary:
    scanned: int = 0
    skipped_unchanged: int = 0
    indexed: int = 0
    chunks_written: int = 0
    failures: list[DocumentFailure] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def failed(self) -> int:
        return len(self.failures)


async def _record_failure(
    pool: asyncpg.Pool, document_id: str, digest: str, reason: str
) -> None:
    async with pool.acquire() as connection, connection.transaction():
        await connection.execute(DELETE_CHUNKS_SQL, document_id)
        await connection.execute(UPSERT_STATE_SQL, document_id, digest, 0, "failed", reason)


async def index_documents(pool: asyncpg.Pool, embedding: SupportsEmbedding) -> IndexSummary:
    summary = IndexSummary()
    started = time.perf_counter()

    async with pool.acquire() as connection:
        documents = await connection.fetch(DOCUMENTS_SQL)

    for document in documents:
        document_id = document["id"]
        summary.scanned += 1
        digest = content_hash(document["title"], document["body"])

        async with pool.acquire() as connection:
            state = await connection.fetchrow(STATE_SQL, document_id)
        if state and state["status"] == "indexed" and state["content_hash"] == digest:
            summary.skipped_unchanged += 1
            continue

        chunks = chunk_document(document["body"])
        if not chunks:
            await _record_failure(pool, document_id, digest, "blank_body")
            summary.failures.append(DocumentFailure(document_id, "blank_body"))
            logger.warning("indexing skipped document_id=%s reason=blank_body", document_id)
            continue

        try:
            batch = await embedding.embed(chunks)
        except EmbeddingInputRejected:
            await _record_failure(pool, document_id, digest, "embedding_rejected")
            summary.failures.append(DocumentFailure(document_id, "embedding_rejected"))
            logger.warning("indexing rejected document_id=%s", document_id)
            continue

        if len(batch.vectors) != len(chunks):
            await _record_failure(pool, document_id, digest, "embedding_count_mismatch")
            summary.failures.append(DocumentFailure(document_id, "embedding_count_mismatch"))
            logger.warning("embedding count mismatch document_id=%s", document_id)
            continue

        async with pool.acquire() as connection, connection.transaction():
            await connection.execute(DELETE_CHUNKS_SQL, document_id)
            for index, (chunk, vector) in enumerate(zip(chunks, batch.vectors)):
                await connection.execute(
                    INSERT_CHUNK_SQL,
                    f"{document_id}:{index}",
                    document_id,
                    document["practice_id"],
                    document["patient_id"],
                    document["document_type"],
                    index,
                    chunk,
                    vector,
                )
            await connection.execute(
                UPSERT_STATE_SQL, document_id, digest, len(chunks), "indexed", None
            )

        summary.indexed += 1
        summary.chunks_written += len(chunks)

    summary.duration_seconds = round(time.perf_counter() - started, 2)
    logger.info(
        "indexing run complete scanned=%d indexed=%d skipped=%d failed=%d chunks=%d",
        summary.scanned,
        summary.indexed,
        summary.skipped_unchanged,
        summary.failed,
        summary.chunks_written,
    )
    return summary
```

Run:

```text
docker compose exec -T api pytest tests/acceptance/test_acceptance_checklist.py -q
```

Expected GREEN:

```text
3 passed (plus remaining xfail placeholders reported as xfailed)
```

- [ ] Step 6: Wire the `make index` entry point

File: `services/api/app/scripts/index_clinical_documents.py` (full replacement)

```python
import asyncio
import logging
import sys

from app.clients.embedding import EmbeddingClient
from app.config import get_settings
from app.db.pool import open_pool
from app.errors import EmbeddingServiceError
from app.features.indexing.runner import index_documents
from app.observability import configure_logging

logger = logging.getLogger("api.scripts.index")


async def run() -> int:
    settings = get_settings()
    embedding = EmbeddingClient(
        base_url=settings.embedding_service_url,
        timeout_seconds=settings.embedding_request_timeout_seconds,
        max_batch_size=settings.embedding_max_batch_size,
    )
    try:
        if not await embedding.is_healthy():
            print("embedding service is not healthy; start it and retry", file=sys.stderr)
            return 1
        async with open_pool(settings.database_url, min_size=1, max_size=2) as pool:
            summary = await index_documents(pool, embedding)
    except EmbeddingServiceError:
        print("embedding service failed during indexing; rerun to resume", file=sys.stderr)
        return 1
    finally:
        await embedding.aclose()

    print(
        f"scanned={summary.scanned} skipped_unchanged={summary.skipped_unchanged} "
        f"indexed={summary.indexed} failed={summary.failed} "
        f"chunks_written={summary.chunks_written} duration_s={summary.duration_seconds}"
    )
    for failure in summary.failures:
        print(f"failed document_id={failure.document_id} reason={failure.reason}")
    return 0


def main() -> int:
    configure_logging(get_settings().api_log_level)
    try:
        return asyncio.run(run())
    except Exception as exc:
        logger.error("indexing failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Run:

```text
make index
```

Expected GREEN (first run): exit 0, `indexed=2398 failed=2` (2 blank documents), `chunks_written` ≈ 4,000–5,000. Second `make index`: `indexed=0 skipped_unchanged=2398 failed=2` (blank docs retried and re-failed fast, no new chunks).

- [ ] Step 7: Full backend suite + lint

Run:

```text
make test-api
make lint
```

Expected GREEN: all tests pass, remaining acceptance placeholders still xfail (they belong to T003/T005); ruff clean.

## TDD Plan

### RED

Steps 1 and 4 (unit + acceptance tests written first, fail on missing modules).

### Verify RED

`pytest tests/test_indexing_chunking.py -q` → ModuleNotFoundError; `pytest tests/acceptance/test_acceptance_checklist.py -q` → ModuleNotFoundError.

### GREEN

Steps 2, 3, 5, 6 (chunker, migration, runner, script).

### Verify GREEN

Same commands pass; `make index` twice on the real stack proves idempotency outside the stub.

### Refactor

Only if duplication appears between `_record_failure` paths; keep the runner flat and readable. No abstractions beyond what is shown.

## Commands

```bash
docker compose exec -T api pytest tests/test_indexing_chunking.py -q
docker compose exec -T api pytest tests/acceptance/test_acceptance_checklist.py -q
docker compose exec -T api python -m app.scripts.migrate
docker compose exec -T api python -m app.scripts.migrate --database test
make index
make test-api
make lint
```

## Expected Outputs

- chunker tests: 5 passed
- acceptance: 3 passed, 6 xfailed (remaining placeholders)
- migrate: `applied 0002_document_chunks.sql` then `skipped` on rerun
- `make index` #1: exit 0, indexed≈2398, failed=2, summary printed
- `make index` #2: exit 0, indexed=0, skipped_unchanged≈2398
- `make test-api`: green; `make lint`: clean

## Risks / Rollback

- Docker daemon down → all container verification blocked; escalate to human (environment prerequisite, not a code problem).
- Migration rollback (manual, no down-migrations in the runner): `DROP TABLE document_chunks, document_index_state; DELETE FROM schema_migrations WHERE filename='0002_document_chunks.sql';` then delete the file.
- Code rollback: delete the two new modules, restore `index_clinical_documents.py` stub from git, restore acceptance file from git.
- HNSW build on ~5k rows: trivial; if it ever slowed a fresh migrate, build it after the first index run instead (documented alternative, not expected).
- The single ~100k-char document yields ~110 chunks → `EmbeddingClient` auto-batches at 64; no service limit is crossed.
- Seed reload truncates source tables and cascades into the new tables: next `make index` re-indexes everything. Intended; noted for the README trade-offs.

## Self Review

- Spec coverage: AC-1 (Step 3), AC-2 (Steps 5–6), AC-3 (Steps 4–6) mapped; AC-4..AC-9 belong to later tasks/plans.
- Placeholder scan: no TBD/TODO; all code complete.
- Type/signature consistency: `IndexSummary.failed` used by tests; `DocumentFailure.reason` asserted; chunk ids deterministic `<document_id>:<index>`.
- Command specificity: all commands exact, container-based, matching Makefile conventions.
- Risk/rollback coverage: migration + code rollback documented; environment blocker named.
- Branch context / sealed / customer isolation check: not-applicable (local-only); Git actions authorized by this plan: none.

## Handoff

Next action: execute Steps 1–7 (TDD), then rotate a new plan for T003 (search API).
Stop condition: Docker unavailable after human follow-up, or any acceptance test failing after diagnosis.
Evidence to record in notes.md: RED/GREEN outputs, migrate output, both `make index` runs, task status transitions.
