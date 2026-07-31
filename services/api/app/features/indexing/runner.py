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


async def _record_failure(pool: asyncpg.Pool, document_id: str, digest: str, reason: str) -> None:
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
            for index, (chunk, vector) in enumerate(zip(chunks, batch.vectors, strict=True)):
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
