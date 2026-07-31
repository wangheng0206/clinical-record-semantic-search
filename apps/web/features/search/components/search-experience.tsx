"use client";

import { useState, useTransition } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_LABELS,
  type DocumentType,
} from "@/features/clinical-documents/document-types";

import { runClinicalSearch } from "../actions";
import type { ClinicalSearchResponse } from "../schemas";
import { SearchResults } from "./search-results";

type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "results"; response: ClinicalSearchResponse }
  | { kind: "no-results"; query: string }
  | { kind: "invalid"; message: string }
  | { kind: "failed"; message: string };

export function SearchExperience() {
  const [query, setQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<DocumentType[]>([]);
  const [state, setState] = useState<SearchState>({ kind: "idle" });
  const [isPending, startTransition] = useTransition();

  function toggleType(documentType: DocumentType) {
    setSelectedTypes((current) =>
      current.includes(documentType)
        ? current.filter((item) => item !== documentType)
        : [...current, documentType],
    );
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setState({ kind: "invalid", message: "Enter a clinical description to search." });
      return;
    }
    setState({ kind: "loading" });
    startTransition(async () => {
      const result = await runClinicalSearch({
        query: trimmed,
        documentTypes: selectedTypes.length ? selectedTypes : undefined,
      });
      if (result.status === "ok") {
        setState(
          result.response.results.length
            ? { kind: "results", response: result.response }
            : { kind: "no-results", query: trimmed },
        );
      } else if (result.status === "invalid") {
        setState({ kind: "invalid", message: result.message });
      } else {
        setState({ kind: "failed", message: result.message });
      }
    });
  }

  const busy = isPending || state.kind === "loading";

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField
          label="Clinical description"
          name="query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="e.g. recurring headaches preceded by flashing lights and nausea"
          hint="Describe the presentation in plain language."
          errorMessage={state.kind === "invalid" ? state.message : undefined}
        />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-content">
            Document types (optional)
          </legend>
          <div className="flex flex-wrap gap-3">
            {DOCUMENT_TYPES.map((documentType) => (
              <label
                key={documentType}
                className="inline-flex items-center gap-2 text-sm text-content-secondary"
              >
                <input
                  type="checkbox"
                  checked={selectedTypes.includes(documentType)}
                  onChange={() => toggleType(documentType)}
                />
                {DOCUMENT_TYPE_LABELS[documentType]}
              </label>
            ))}
          </div>
        </fieldset>
        <Button type="submit" disabled={busy}>
          {busy ? "Searching…" : "Search"}
        </Button>
      </form>

      {state.kind === "loading" ? (
        <div className="flex items-center gap-3 text-content-secondary">
          <Spinner label="Searching records" /> Searching records…
        </div>
      ) : null}
      {state.kind === "results" ? <SearchResults results={state.response.results} /> : null}
      {state.kind === "no-results" ? (
        <EmptyState
          title="No matching records"
          description={`No documents in your practice matched "${state.query}". Try different wording or broaden the document-type filter.`}
        />
      ) : null}
      {state.kind === "failed" ? (
        <Alert tone="danger" title="Search unavailable">
          {state.message}
        </Alert>
      ) : null}
    </div>
  );
}
