import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app.features.indexing.runner import IndexSummary, index_documents
from tests.conftest import SingleConnectionPool
from tests.stubs import StubEmbeddingClient, UnavailableEmbeddingClient


async def _run_index(
    connection: asyncpg.Connection, embedding_client: StubEmbeddingClient
) -> IndexSummary:
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
    connection: asyncpg.Connection, embedding_client: StubEmbeddingClient, curated_cases: dict
) -> None:
    await _run_index(connection, embedding_client)
    document_id = curated_cases["cases"][0]["expectedDocumentId"]
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
    stale = {row["id"] for row in old} - {row["id"] for row in new}
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
    # The deterministic stub embeds by hashing the whole text, so only identical
    # strings are close. Two documents with identical bodies share one vector and
    # therefore both land at distance 0 for an exact-text query.
    shared = "Recurrent frontal headache with visual aura and photophobia."
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
            " VALUES ($1, 'practice-northside', 'patient-iso-multi',"
            " 'specialist_note', $2, '2026-02-02', 'Dr Test', $3)",
            f"document-iso-multi-{suffix.lower()}",
            f"Neurology consult {suffix}",
            shared,
        )
    await _run_index(connection, embedding_client)

    response = await _post_search(api, northside_headers, {"query": shared})
    assert response.status_code == 200
    results = response.json()["results"]
    patient_ids = [r["patient"]["id"] for r in results]
    assert len(patient_ids) == len(set(patient_ids))
    assert results[0]["patient"]["id"] == "patient-iso-multi"
    assert results[0]["additionalMatchingDocuments"] == 1
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
        pytest.param(
            {"query": "chest pain", "practiceId": "practice-lakeshore"}, id="practice-override"
        ),
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


async def test_empty_document_type_filter_means_no_filter(
    api: AsyncClient,
    connection: asyncpg.Connection,
    embedding_client: StubEmbeddingClient,
    northside_headers: dict[str, str],
) -> None:
    await _run_index(connection, embedding_client)
    unfiltered = await _post_search(api, northside_headers, {"query": "headache"})
    explicit_empty = await _post_search(
        api, northside_headers, {"query": "headache", "documentTypes": []}
    )
    assert unfiltered.status_code == explicit_empty.status_code == 200
    assert explicit_empty.json()["results"] == unfiltered.json()["results"]


async def test_document_type_filter_restricts_results(
    api: AsyncClient,
    connection: asyncpg.Connection,
    embedding_client: StubEmbeddingClient,
    northside_headers: dict[str, str],
) -> None:
    await _run_index(connection, embedding_client)
    response = await _post_search(
        api, northside_headers, {"query": "headache", "documentTypes": ["lab_report"]}
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert {r["bestMatch"]["documentType"] for r in results} == {"lab_report"}


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
