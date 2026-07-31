import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { DOCUMENT_TYPE_LABELS } from "@/features/clinical-documents/document-types";
import { formatDocumentDate } from "@/lib/format";

import type { ClinicalSearchResponse } from "../schemas";

export function SearchResults({
  results,
}: {
  results: ClinicalSearchResponse["results"];
}) {
  return (
    <ol className="space-y-4">
      {results.map((result) => (
        <li key={result.patient.id}>
          <Card>
            <CardBody className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link
                  href={`/patients/${result.patient.id}`}
                  className="text-base font-semibold text-primary hover:underline"
                >
                  {result.patient.displayName}
                </Link>
                <Badge tone="info">{DOCUMENT_TYPE_LABELS[result.bestMatch.documentType]}</Badge>
              </div>
              <p className="text-sm font-medium text-content">
                {result.bestMatch.documentTitle}
                <span className="ml-2 font-normal text-content-muted">
                  {formatDocumentDate(result.bestMatch.documentDate)}
                </span>
              </p>
              <p className="text-sm text-content-secondary">{result.bestMatch.snippet}</p>
              <p className="text-xs text-content-muted">
                Relevance score {result.bestMatch.relevanceScore.toFixed(2)}
                {result.additionalMatchingDocuments > 0
                  ? ` · +${result.additionalMatchingDocuments} more matching document${
                      result.additionalMatchingDocuments === 1 ? "" : "s"
                    }`
                  : ""}
              </p>
            </CardBody>
          </Card>
        </li>
      ))}
    </ol>
  );
}
