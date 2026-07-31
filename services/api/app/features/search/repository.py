from dataclasses import dataclass
from datetime import date

import asyncpg

CANDIDATE_SQL = """
SELECT c.document_id, c.patient_id, c.document_type::text AS document_type,
       c.content, c.embedding <=> $1::vector AS distance,
       d.title, d.document_date,
       p.first_name, p.last_name
FROM document_chunks c
JOIN clinical_documents d ON d.id = c.document_id
JOIN patients p ON p.id = c.patient_id
WHERE c.practice_id = $2
  AND ($3::document_type[] IS NULL OR c.document_type = ANY($3::document_type[]))
ORDER BY c.embedding <=> $1::vector
LIMIT $4
"""


@dataclass(frozen=True)
class CandidateRow:
    document_id: str
    patient_id: str
    document_type: str
    content: str
    distance: float
    title: str
    document_date: date
    first_name: str
    last_name: str


def candidate_limit(result_limit: int) -> int:
    return max(result_limit * 5, 25)


# HNSW search is approximate: at the pgvector default (ef_search=40) true nearest
# chunks can silently miss the candidate set. 400 gives exact-grade recall at the
# exercise's ~4k-chunk scale for negligible cost; revisit with measurements when
# the corpus grows orders of magnitude.
EF_SEARCH_SQL = "SET LOCAL hnsw.ef_search = 400"


async def fetch_candidates(
    pool: asyncpg.Pool,
    query_vector: list[float],
    practice_id: str,
    document_types: list[str] | None,
    limit: int,
) -> list[CandidateRow]:
    async with pool.acquire() as connection, connection.transaction():
        await connection.execute(EF_SEARCH_SQL)
        records = await connection.fetch(
            CANDIDATE_SQL, query_vector, practice_id, document_types, limit
        )
    return [CandidateRow(**dict(record)) for record in records]
