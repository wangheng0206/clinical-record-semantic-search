# Execution Plan

Plan ID: 2026-07-31-t003-semantic-search-api
Created: 2026-07-31
Updated: 2026-07-31
Active Since: 2026-07-31
Status: active
Supersedes: 2026-07-31-us1-searchable-index (completed, archived to plans/)

Bug Context Evidence: none
Related Bug IDs: none

Plan Scope:
- Type: task
- ID: T003
- Title: Semantic search API (`POST /api/clinical-search`)
- Included Tasks: T003
- Design Slices: DS-03 retrieval + isolation + aggregation, DS-04 validation + failure behavior

Branch Context Evidence:
- Branch Strategy Status / Profile: not-needed / not-applicable (local-only delivery)
- Target Release Context: not-applicable
- Target Branch: not-applicable
- Current Branch Context Evidence: `notes.md#current-branch-context`
- Sealed Check: not-applicable
- Customer Isolation Check: not-applicable
- Git actions authorized by this plan: none

Feature Context: `scripts/check-feature-context.py` = CURRENT (2026-07-31, unchanged requirement sources). Product Slice: `product.md#in-scope` (search API). Acceptance: AC-4, AC-5, AC-6. Invariants preserved: practice isolation inside the SQL retrieval query (never post-filter, never from request payload); similarity never presented as clinical confidence; no internals in client errors; exactly one embedding call per search.

## Goal

Turn `POST /api/clinical-search` from 501 into validated, practice-isolated, vector-ranked retrieval with patient-level aggregation and evidence, covering empty/failure behaviors, and replace acceptance placeholders AT-04..AT-08 plus integration IT-01.

## Architecture Summary

Router (transport + validation via pydantic) → one `embed([query])` call → `repository.fetch_candidates` (pgvector cosine distance, `WHERE practice_id = context.practice_id`, optional document-type filter, over-fetch) → `service.aggregate_patient_results` (pure: best chunk per patient, distinct extra documents, deterministic ordering, top `limit`) → response. `EmbeddingServiceError` propagates to the provided 503 envelope.

## Technical Context

- Language/Version: Python 3.13
- Frameworks/Libraries: FastAPI, asyncpg + pgvector (registered on pool init), pydantic v2 (provided; no new dependencies)
- Runtime: Docker Compose; tests via `docker compose exec -T api pytest`
- Storage/Data: `document_chunks` (3,958 rows seeded by T002) + `clinical_documents`/`patients` joins for titles/dates/names
- Testing: pytest, `StubEmbeddingClient` (deterministic; identical text → identical vector → distance 0), `UnavailableEmbeddingClient` (503), `real_embedding_client` (integration)
- Constraints: response contract fixed by provided `schemas.py`; query ≤ 500 chars, limit default 10 / max 25 (settings); ruff line-length 100
- Scale/Scope: candidate over-fetch ≤ 50 rows per query; trivial for HNSW

## Source Structure Decision

- Existing structure followed: feature-local modules; `repository.py` holds SQL + records (patients pattern); pure logic separated for unit testing.
- New structure: `app/features/search/repository.py` (SQL), `app/features/search/service.py` (pure aggregation); `router.py` and `schemas.py` modified in place.
- Why: keeps SQL, ranking logic, and transport independently testable; mirrors the patients feature shape.

## Files

- Create: `services/api/app/features/search/repository.py`
- Create: `services/api/app/features/search/service.py`
- Modify: `services/api/app/features/search/schemas.py` (validation only; contract unchanged)
- Modify: `services/api/app/features/search/router.py` (replace 501 stub)
- Test: `services/api/tests/test_search.py` (new: empty-index + aggregation units)
- Modify: `services/api/tests/acceptance/test_acceptance_checklist.py` (replace AT-04..AT-08 + IT-01 placeholders)
- Read: `services/api/app/features/health/router.py` (`get_embedding_client` pattern), `services/api/app/schemas.py` (CamelModel)

## Code Context

Existing functions/classes/modules:
- `get_embedding_client(request)` in `app/features/health/router.py`: returns `request.app.state.embedding_client`; reused as the search embedding dependency (import, no duplication).
- `CamelModel` in `app/schemas.py`: camelCase aliases; provided `ClinicalSearchRequest/Response` models in `app/features/search/schemas.py` stay unchanged in shape.
- `StubEmbeddingClient`: `deterministic_vector(text)` — identical texts embed identically (cosine distance 0); distinct near-identical texts (small suffix changes) embed very close. Enables deterministic ranking fixtures.
- `SingleConnectionPool`: shares the test connection; uncommitted fixture rows visible to the runner and the app.
- `index_documents` (T002): used by tests to index fixtures/seed with the stub.
- Error handlers (`app/errors.py`): `RequestValidationError` → 422 `validation_error`; `EmbeddingServiceError` → 503 `embedding_service_unavailable`; envelope `{error:{code,message,requestId}}`, never leaks internals.

Call chain:

```text
POST /api/clinical-search (Bearer demo_<user>)
  → get_request_context → RequestContext.practice_id (server-side, from users table)
  → pydantic validation (422 before any embedding call)
  → embedding_client.embed([query])            # exactly one call
  → repository.fetch_candidates(pool, vector, practice_id, types, candidate_limit)
  → service.aggregate_patient_results(rows, limit)
  → ClinicalSearchResponse(query, results, meta{resultCount, tookMs})
```

Data flow: query text → 384-dim vector → cosine distance over practice-filtered chunks → patient-level ranking with evidence.

Authorization / validation / side effects: practice from session only (request has no practice field); side effects none (read-only query + one embedding call).

## Interface Contracts

### `fetch_candidates`

Location: `services/api/app/features/search/repository.py`
Kind: function
Signature: `fetch_candidates(pool: asyncpg.Pool, query_vector: list[float], practice_id: str, document_types: list[str] | None, candidate_limit: int) -> list[CandidateRow]`
Parameters:
- `query_vector`: 384-dim embedding of the query
- `practice_id`: session practice (server-side)
- `document_types`: optional filter; `None` = all four types
- `candidate_limit`: over-fetch size (default-limit × 5, min 25)
Return: `CandidateRow` records ordered by cosine distance asc: `document_id, patient_id, document_type, content, distance, title, document_date, first_name, last_name`
Errors: asyncpg errors propagate (→ 500 envelope)
Side effects: none
Tests proving contract: AT-04, AT-05, AT-06, MT-07, IT-01

### `aggregate_patient_results`

Location: `services/api/app/features/search/service.py`
Kind: function
Signature: `aggregate_patient_results(rows: Sequence[CandidateRow], limit: int) -> list[RankedPatient]`
Return: up to `limit` `RankedPatient` records: each patient once; `best` = lowest-distance row; `relevance_score = round(1 - distance, 4)`; `additional_matching_documents = distinct document_ids among that patient's candidate rows - 1`; ordered by (-score, patient_id)
Errors: none
Side effects: none
Tests proving contract: unit tests in `tests/test_search.py`

### `clinical_search` (endpoint)

Location: `services/api/app/features/search/router.py`
Kind: endpoint
Request: `ClinicalSearchRequest` — `query` (stripped, non-blank, ≤ `search_max_query_length`), `document_types` (enum list or null), `limit` (null → `search_default_limit`; 1..`search_max_limit`)
Response: `ClinicalSearchResponse` (provided contract) — each result `{patient{id,displayName}, bestMatch{documentId,documentType,documentTitle,documentDate,snippet,relevanceScore}, additionalMatchingDocuments}`
Validation: pydantic field validators; 422 with `validation_error`, zero embedding calls
Persistence: none
Authorization: `CurrentContext`; practice isolation via `context.practice_id` in SQL
Errors: 503 `embedding_service_unavailable` on embedding failure; 500 envelope otherwise
Tests proving contract: AT-04..AT-08, IT-01, MT-07

## Data / API Contract

Retrieval SQL (single round trip; isolation inside the query):

```sql
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
```

Over-fetch: `candidate_limit = max(limit * 5, 25)` — enough chunks for patient-level aggregation while staying tiny; recorded as a trade-off for the README.

## Steps

- [ ] Step 1: Failing tests — validation + empty index + aggregation units (RED)

File: `services/api/tests/test_search.py`

```python
import pytest
from httpx import AsyncClient

from app.features.search.service import aggregate_patient_results
from tests.stubs import StubEmbeddingClient


async def test_empty_index_returns_empty_results(
    api: AsyncClient, embedding_client: StubEmbeddingClient, northside_headers: dict
) -> None:
    response = await api.post(
        "/api/clinical-search", json={"query": "chest pain"}, headers=northside_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["meta"]["resultCount"] == 0
    assert body["meta"]["tookMs"] >= 0
    assert embedding_client.call_count == 1


def _row(patient_id: str, document_id: str, distance: float, title: str = "Note"):
    from app.features.search.repository import CandidateRow
    from datetime import date

    return CandidateRow(
        document_id=document_id,
        patient_id=patient_id,
        document_type="diagnostic_note",
        content=f"passage from {document_id}",
        distance=distance,
        title=title,
        document_date=date(2026, 1, 1),
        first_name="Test",
        last_name="Patient",
    )


def test_aggregate_keeps_each_patient_once_with_best_match() -> None:
    rows = [
        _row("patient-b", "doc-2", 0.30),
        _row("patient-a", "doc-1", 0.10),
        _row("patient-a", "doc-3", 0.20),
    ]
    ranked = aggregate_patient_results(rows, limit=10)
    assert [r.patient_id for r in ranked] == ["patient-a", "patient-b"]
    assert ranked[0].best_document_id == "doc-1"
    assert ranked[0].additional_matching_documents == 1
    assert ranked[0].relevance_score == pytest.approx(0.9)


def test_aggregate_applies_limit() -> None:
    rows = [_row(f"patient-{i}", f"doc-{i}", 0.01 * i) for i in range(1, 8)]
    ranked = aggregate_patient_results(rows, limit=3)
    assert [r.patient_id for r in ranked] == ["patient-1", "patient-2", "patient-3"]


def test_aggregate_empty_rows() -> None:
    assert aggregate_patient_results([], limit=10) == []
```

Run:

```text
docker compose exec -T api pytest tests/test_search.py -q
```

Expected RED: `ModuleNotFoundError: No module named 'app.features.search.service'`

- [ ] Step 2: Failing acceptance tests AT-04..AT-08 + IT-01 (RED)

File: `services/api/tests/acceptance/test_acceptance_checklist.py` — replace the six placeholders:

```python
async def _post_search(api: AsyncClient, headers: dict, payload: dict):
    return await api.post("/api/clinical-search", json=payload, headers=headers)


async def test_search_never_returns_a_patient_from_another_practice(
    api: AsyncClient,
    connection: asyncpg.Connection,
    embedding_client: StubEmbeddingClient,
    curated_cases: dict,
    northside_headers: dict[str, str],
    lakeshore_headers: dict[str, str],
) -> None:
    marker = "unique isolation marker zebra quasar lumen"
    await connection.execute(
        "INSERT INTO patients (id, practice_id, mrn, first_name, last_name, date_of_birth, sex)"
        " VALUES ('patient-iso-decoy', 'practice-lakeshore', 'MRN-ISO-1',"
        " 'Iso', 'Decoy', '1990-01-01', 'other')"
    )
    await connection.execute(
        "INSERT INTO clinical_documents"
        " (id, practice_id, patient_id, document_type, title, document_date, author_name, body)"
        " VALUES ('document-iso-decoy', 'practice-lakeshore', 'patient-iso-decoy',"
        " 'diagnostic_note', 'Isolation decoy', '2026-01-01', 'Dr Test', $1)",
        marker,
    )
    await _run_index(connection, embedding_client)

    control = await _post_search(api, lakeshore_headers, {"query": marker})
    assert control.status_code == 200
    control_results = control.json()["results"]
    assert control_results
    assert control_results[0]["patient"]["id"] == "patient-iso-decoy"

    response = await _post_search(api, northside_headers, {"query": marker})
    assert response.status_code == 200
    patient_ids = [r["patient"]["id"] for r in response.json()["results"]]
    assert "patient-iso-decoy" not in patient_ids

    for case in curated_cases["cases"]:
        swept = await _post_search(api, northside_headers, {"query": case["query"]})
        assert swept.status_code == 200
        swept_ids = [r["patient"]["id"] for r in swept.json()["results"]]
        assert case["crossPracticeDecoyPatientId"] not in swept_ids


async def test_patient_with_multiple_matching_documents_appears_once(
    api: AsyncClient,
    connection: asyncpg.Connection,
    embedding_client: StubEmbeddingClient,
    northside_headers: dict[str, str],
) -> None:
    shared = "Recurrent frontal headache with visual aura and photophobia. " * 30
    await connection.execute(
        "INSERT INTO patients (id, practice_id, mrn, first_name, last_name, date_of_birth, sex)"
        " VALUES ('patient-iso-multi', 'practice-northside', 'MRN-ISO-2',"
        " 'Multi', 'Doc', '1985-05-05', 'female')"
    )
    for suffix in ("A", "B"):
        await connection.execute(
            "INSERT INTO clinical_documents"
            " (id, practice_id, patient_id, document_type, title,"
            " document_date, author_name, body)"
            f" VALUES ('document-iso-multi-{suffix.lower()}', 'practice-northside',"
            " 'patient-iso-multi', 'specialist_note', $1, '2026-02-02', 'Dr Test', $2)",
            f"Neurology consult {suffix}",
            f"{shared} Tail of document {suffix}.",
        )
    await _run_index(connection, embedding_client)

    response = await _post_search(
        api,
        northside_headers,
        {"query": "Recurrent frontal headache with visual aura and photophobia."},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    patient_ids = [r["patient"]["id"] for r in results]
    assert len(patient_ids) == len(set(patient_ids))
    assert results[0]["patient"]["id"] == "patient-iso-multi"
    assert results[0]["additionalMatchingDocuments"] >= 1
    assert results[0]["bestMatch"]["snippet"]


async def test_search_performs_exactly_one_embedding_call(
    api: AsyncClient, embedding_client: StubEmbeddingClient, northside_headers: dict[str, str]
) -> None:
    response = await _post_search(api, northside_headers, {"query": "chest pain"})
    assert response.status_code == 200
    assert embedding_client.call_count == 1


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"query": ""}, id="empty"),
        pytest.param({"query": "   \t "}, id="whitespace-only"),
        pytest.param({"query": "x" * 5000}, id="over-max-length"),
        pytest.param({"query": "chest pain", "documentTypes": ["not_a_type"]}, id="bad-type"),
        pytest.param({"query": "chest pain", "limit": 10_000}, id="limit-too-large"),
    ],
)
async def test_invalid_requests_are_rejected_without_embedding(
    api: AsyncClient,
    embedding_client: StubEmbeddingClient,
    northside_headers: dict[str, str],
    payload: dict,
) -> None:
    response = await _post_search(api, northside_headers, payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert embedding_client.call_count == 0


async def test_search_reports_service_unavailable_when_embedding_is_down(
    connection: asyncpg.Connection, settings, northside_headers: dict[str, str]
) -> None:
    from app.main import create_app
    from tests.conftest import SingleConnectionPool as _Pool

    app = create_app()
    app.state.settings = settings
    app.state.pool = _Pool(connection)
    app.state.embedding_client = UnavailableEmbeddingClient()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await _post_search(client, northside_headers, {"query": "chest pain"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "embedding_service_unavailable"
    assert "Traceback" not in response.text
    assert "asyncpg" not in response.text


@pytest.mark.integration
async def test_curated_query_returns_the_expected_patient_in_top_results(
    connection: asyncpg.Connection,
    settings,
    curated_cases: dict,
    real_embedding_client,
    northside_headers: dict[str, str],
) -> None:
    from app.main import create_app
    from tests.conftest import SingleConnectionPool as _Pool

    await _run_index(connection, real_embedding_client)
    app = create_app()
    app.state.settings = settings
    app.state.pool = _Pool(connection)
    app.state.embedding_client = real_embedding_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for case in curated_cases["cases"]:
            response = await _post_search(client, northside_headers, {"query": case["query"]})
            assert response.status_code == 200
            patient_ids = [r["patient"]["id"] for r in response.json()["results"]]
            limit = settings.search_default_limit
            assert case["expectedPatientId"] in patient_ids[:limit], case["id"]
```

Run:

```text
docker compose exec -T api pytest tests/acceptance/test_acceptance_checklist.py -q
```

Expected RED: search tests return 501 (`assert response.status_code == 200` fails) — endpoint still stubbed.

- [ ] Step 3: Implement schemas validation

File: `services/api/app/features/search/schemas.py` — add to `ClinicalSearchRequest` only:

```python
from pydantic import Field, field_validator

from app.config import get_settings
from app.domain import DocumentType
from app.schemas import CamelModel


class ClinicalSearchRequest(CamelModel):
    query: str
    document_types: list[DocumentType] | None = None
    limit: int | None = Field(default=None, ge=1)

    @field_validator("query")
    @classmethod
    def query_must_be_searchable(cls, value: str) -> str:
        settings = get_settings()
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("query must not be blank")
        if len(trimmed) > settings.search_max_query_length:
            raise ValueError(
                f"query must be at most {settings.search_max_query_length} characters"
            )
        return trimmed

    @field_validator("limit")
    @classmethod
    def limit_within_bounds(cls, value: int | None) -> int | None:
        if value is None:
            return value
        settings = get_settings()
        if value > settings.search_max_limit:
            raise ValueError(f"limit must be at most {settings.search_max_limit}")
        return value
```

(Response models unchanged.)

- [ ] Step 4: Implement repository

File: `services/api/app/features/search/repository.py`

```python
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


async def fetch_candidates(
    pool: asyncpg.Pool,
    query_vector: list[float],
    practice_id: str,
    document_types: list[str] | None,
    limit: int,
) -> list[CandidateRow]:
    records = await pool.fetch(
        CANDIDATE_SQL, query_vector, practice_id, document_types, limit
    )
    return [CandidateRow(**dict(record)) for record in records]
```

- [ ] Step 5: Implement service

File: `services/api/app/features/search/service.py`

```python
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.features.search.repository import CandidateRow


@dataclass(frozen=True)
class RankedPatient:
    patient_id: str
    display_name: str
    best_document_id: str
    best_document_type: str
    best_title: str
    best_document_date: date
    snippet: str
    relevance_score: float
    additional_matching_documents: int


def aggregate_patient_results(
    rows: "Sequence[CandidateRow]", limit: int
) -> list[RankedPatient]:
    by_patient: dict[str, list] = {}
    for row in rows:
        by_patient.setdefault(row.patient_id, []).append(row)

    ranked = []
    for patient_id, patient_rows in by_patient.items():
        best = patient_rows[0]
        distinct_documents = {row.document_id for row in patient_rows}
        ranked.append(
            RankedPatient(
                patient_id=patient_id,
                display_name=f"{best.first_name} {best.last_name}",
                best_document_id=best.document_id,
                best_document_type=best.document_type,
                best_title=best.title,
                best_document_date=best.document_date,
                snippet=best.content,
                relevance_score=round(1.0 - best.distance, 4),
                additional_matching_documents=len(distinct_documents) - 1,
            )
        )

    ranked.sort(key=lambda r: (-r.relevance_score, r.patient_id))
    return ranked[:limit]
```

- [ ] Step 6: Implement the endpoint

File: `services/api/app/features/search/router.py`

```python
import time
from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.embedding import SupportsEmbedding
from app.config import get_settings
from app.context import CurrentContext, PoolDep
from app.errors import ErrorResponse
from app.features.health.router import get_embedding_client
from app.features.search.repository import candidate_limit, fetch_candidates
from app.features.search.schemas import (
    BestMatch,
    ClinicalSearchRequest,
    ClinicalSearchResponse,
    PatientSummary,
    SearchMeta,
    SearchResult,
)
from app.features.search.service import aggregate_patient_results

router = APIRouter(prefix="/api", tags=["search"])

EmbeddingDep = Annotated[SupportsEmbedding, Depends(get_embedding_client)]


@router.post(
    "/clinical-search",
    response_model=ClinicalSearchResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def clinical_search(
    payload: ClinicalSearchRequest,
    pool: PoolDep,
    context: CurrentContext,
    embedding_client: EmbeddingDep,
) -> ClinicalSearchResponse:
    started = time.perf_counter()
    settings = get_settings()
    limit = payload.limit if payload.limit is not None else settings.search_default_limit

    batch = await embedding_client.embed([payload.query])
    rows = await fetch_candidates(
        pool,
        batch.vectors[0],
        context.practice_id,
        payload.document_types,
        candidate_limit(limit),
    )
    ranked = aggregate_patient_results(rows, limit)

    took_ms = int((time.perf_counter() - started) * 1000)
    return ClinicalSearchResponse(
        query=payload.query,
        results=[
            SearchResult(
                patient=PatientSummary(id=r.patient_id, display_name=r.display_name),
                best_match=BestMatch(
                    document_id=r.best_document_id,
                    document_type=r.best_document_type,
                    document_title=r.best_title,
                    document_date=r.best_document_date,
                    snippet=r.snippet,
                    relevance_score=r.relevance_score,
                ),
                additional_matching_documents=r.additional_matching_documents,
            )
            for r in ranked
        ],
        meta=SearchMeta(result_count=len(ranked), took_ms=took_ms),
    )
```

- [ ] Step 7: Verify GREEN (unit + acceptance + full suite + integration)

Run:

```text
docker compose exec -T api pytest -q
docker compose exec -T api pytest -q -m integration
docker compose exec -T api ruff check app tests && docker compose exec -T api ruff format --check app tests
```

Expected GREEN: all non-integration tests pass (no xfail left in the acceptance file); integration test passes against the real embedding container (~2–3 min for the in-test indexing run); lint clean.

## TDD Plan

### RED

Steps 1–2 (module missing; endpoint 501).

### Verify RED

`pytest tests/test_search.py -q` → ModuleNotFoundError; acceptance search tests fail with 501 assertions.

### GREEN

Steps 3–6 (schemas, repository, service, router).

### Verify GREEN

Step 7 commands all green.

### Refactor

None planned; keep three small modules flat.

## Commands

```bash
docker compose exec -T api pytest tests/test_search.py -q
docker compose exec -T api pytest tests/acceptance/test_acceptance_checklist.py -q
docker compose exec -T api pytest -q
docker compose exec -T api pytest -q -m integration
docker compose exec -T api ruff check app tests && docker compose exec -T api ruff format --check app tests
```

## Expected Outputs

- `test_search.py`: 4 passed
- acceptance: all passed, zero xfail remaining in the file
- integration: 1 passed
- full suite: all green; lint clean

## Risks / Rollback

- Stub-vector determinism: fixtures rely on identical text → distance 0 and near-identical text → very close; assertions avoid exact-rank dependence beyond `results[0]` for crafted fixtures.
- Integration test cost: in-test full indexing ≈ 2–3 minutes; acceptable for the `-m integration` lane (excluded from default runs).
- `get_embedding_client` imported from the health feature: acceptable coupling for a two-line accessor; alternative (moving it to `app/context.py`) would touch provided code for no behavior gain.
- Rollback: restore `router.py`/`schemas.py`/acceptance file from git; delete `repository.py`, `service.py`, `test_search.py`. Index data untouched.

## Self Review

- Spec coverage: AC-4 (Steps 2/6, AT-04/AT-06, IT-01), AC-5 (Step 5, AT-05), AC-6 (Steps 3/6, AT-07/AT-08, MT-07) mapped.
- Placeholder scan: none.
- Type/signature consistency: `CandidateRow` field names match SQL aliases; `RankedPatient` matches response mapping in router; `document_type::text` cast keeps the dataclass `str`.
- Command specificity: exact container commands.
- Risk/rollback coverage: above.
- Branch context / sealed / customer isolation check: not-applicable; Git actions authorized by this plan: none.

## Handoff

Next action: execute Steps 1–7, then T004 (search UI) plan.
Stop condition: repeated verification failure after diagnosis, or scope/contract change discovered.
Evidence to record in notes.md: RED/GREEN outputs, integration run result, task status.
