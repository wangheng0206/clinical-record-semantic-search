from datetime import date

from pydantic import ConfigDict, Field, field_validator

from app.config import get_settings
from app.domain import DocumentType
from app.schemas import CamelModel


class ClinicalSearchRequest(CamelModel):
    # Practice context comes only from the server-side session; a client-supplied
    # practice identifier (or any unknown field) is rejected, never ignored.
    model_config = ConfigDict(extra="forbid")

    query: str
    document_types: list[DocumentType] | None = None
    limit: int | None = Field(default=None, ge=1)

    @field_validator("document_types")
    @classmethod
    def empty_type_list_means_no_filter(
        cls, value: list[DocumentType] | None
    ) -> list[DocumentType] | None:
        if value is not None and not value:
            return None
        return value

    @field_validator("query")
    @classmethod
    def query_must_be_searchable(cls, value: str) -> str:
        settings = get_settings()
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("query must not be blank")
        if len(trimmed) > settings.search_max_query_length:
            raise ValueError(f"query must be at most {settings.search_max_query_length} characters")
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


class PatientSummary(CamelModel):
    id: str
    display_name: str


class BestMatch(CamelModel):
    document_id: str
    document_type: DocumentType
    document_title: str
    document_date: date
    snippet: str
    relevance_score: float


class SearchResult(CamelModel):
    patient: PatientSummary
    best_match: BestMatch
    additional_matching_documents: int


class SearchMeta(CamelModel):
    result_count: int
    took_ms: int


class ClinicalSearchResponse(CamelModel):
    query: str
    results: list[SearchResult]
    meta: SearchMeta
