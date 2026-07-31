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
