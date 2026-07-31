from datetime import date

import pytest
from httpx import AsyncClient

from app.features.search.repository import CandidateRow
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


def _row(patient_id: str, document_id: str, distance: float) -> CandidateRow:
    return CandidateRow(
        document_id=document_id,
        patient_id=patient_id,
        document_type="diagnostic_note",
        content=f"passage from {document_id}",
        distance=distance,
        title="Note",
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
