from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

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


def aggregate_patient_results(rows: Sequence[CandidateRow], limit: int) -> list[RankedPatient]:
    by_patient: dict[str, list[CandidateRow]] = {}
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
