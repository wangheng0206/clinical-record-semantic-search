# Execution Plan

Plan ID: 2026-07-31-t004-search-ui
Created: 2026-07-31
Updated: 2026-07-31
Active Since: 2026-07-31
Status: active
Supersedes: 2026-07-31-t003-semantic-search-api (completed, archived to plans/)

Bug Context Evidence: none
Related Bug IDs: none

Plan Scope:
- Type: task
- ID: T004
- Title: Search experience (`/search`)
- Included Tasks: T004
- Design Slices: DS-05 UI states

Branch Context Evidence:
- Branch Strategy Status / Profile: not-needed / not-applicable (local-only delivery)
- Target Release Context: not-applicable
- Target Branch: not-applicable
- Current Branch Context Evidence: `notes.md#current-branch-context`
- Sealed Check: not-applicable
- Customer Isolation Check: not-applicable
- Git actions authorized by this plan: none

Feature Context: `scripts/check-feature-context.py` = CURRENT (2026-07-31). Product Slice: `product.md#in-scope` (search UI). Acceptance: AC-7. Invariants preserved: no browser-direct API calls (Server Action only); no credentials/server config in browser code; relevance score shown only as a retrieval aid, never as confidence.

## Goal

Replace the `/search` shell with a working experience: natural-language query, optional document-type filter, ranked patient results with evidence passage, patient-detail navigation, and all six states (idle, loading, results, no-results, invalid-input, dependency-failure).

## Architecture Summary

`app/search/page.tsx` (server: session + layout) → `features/search/components/search-experience.tsx` (client state machine) → Server Action `features/search/actions.ts#runClinicalSearch` → provided `searchClinicalRecords` (server-only `apiRequest` with zod) → API. Presentational `search-results.tsx` renders the ranked list. Action returns a discriminated union (`ok | invalid | failed`) so the component never catches raw transport errors.

## Technical Context

- Language/Version: TypeScript, React 19, Next.js 16 App Router, Tailwind v4
- Testing: vitest + @testing-library/react (existing `alert.test.tsx` pattern), `make test-web`
- Constraints: server-only imports stay out of client components; use provided design-system primitives; no visual redesign
- Provided seams: `features/search/api.ts#searchClinicalRecords`, `features/search/schemas.ts` (zod contracts), `DOCUMENT_TYPE_LABELS`, `formatDocumentDate`, primitives (`TextField, Button, Card, Badge, Alert, EmptyState, Spinner`)

## Source Structure Decision

- Existing structure followed: feature-local code in `apps/web/features/search/` (`components/`, `actions.ts`), route stays thin.
- New structure: two small components + one action module; no new directories beyond `components/`.

## Files

- Create: `apps/web/features/search/actions.ts`
- Create: `apps/web/features/search/components/search-experience.tsx`
- Create: `apps/web/features/search/components/search-results.tsx`
- Create: `apps/web/features/search/components/search-results.test.tsx`
- Modify: `apps/web/app/search/page.tsx` (replace starter shell)
- Read: `apps/web/features/search/api.ts`, `apps/web/lib/api/client.ts`, `apps/web/components/ui/*`

## Interface Contracts

### `runClinicalSearch`

Location: `apps/web/features/search/actions.ts`
Kind: server action (`"use server"`)
Signature: `runClinicalSearch(input: ClinicalSearchRequest) -> Promise<SearchActionResult>`
Return: `{status:"ok", response} | {status:"invalid", message} | {status:"failed", message}` — 422 → `invalid` (message from API), anything else → `failed` (generic dependency message)
Errors: never throws to the client component
Tests proving contract: exercised through component tests + manual E2E (E2E003)

### `SearchExperience`

Location: `apps/web/features/search/components/search-experience.tsx`
Kind: client component
State: `{kind:"idle"} | {kind:"loading"} | {kind:"results", response} | {kind:"no-results", query} | {kind:"invalid", message} | {kind:"failed", message}`
Events: submit (client-side blank guard first, then action), document-type checkbox toggle, retry after failure
Rendering: form always visible; state area below swaps per state kind

### `SearchResults`

Location: `apps/web/features/search/components/search-results.tsx`
Kind: presentational component
Props: `{ results: ClinicalSearchResponse["results"] }`
Rendering: ordered list of cards: patient display name (link to `/patients/<id>`), document-type Badge, document title + formatted date, snippet, footer with `Relevance score <n>` (retrieval aid) and `+N more matching documents` when N > 0
Tests proving contract: `search-results.test.tsx` (WT-01)

## Steps

- [ ] Step 1: Failing component tests (RED)

File: `apps/web/features/search/components/search-results.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SearchResults } from "./search-results";

const RESULTS = [
  {
    patient: { id: "patient-0001", displayName: "Alice Example" },
    bestMatch: {
      documentId: "document-000001",
      documentType: "diagnostic_note" as const,
      documentTitle: "Migraine review",
      documentDate: "2026-05-11",
      snippet: "reports recurring headaches preceded by flashing lights",
      relevanceScore: 0.87,
    },
    additionalMatchingDocuments: 1,
  },
];

describe("SearchResults", () => {
  it("renders the patient, evidence, and navigation link", () => {
    render(<SearchResults results={RESULTS} />);
    const link = screen.getByRole("link", { name: /Alice Example/ });
    expect(link).toHaveAttribute("href", "/patients/patient-0001");
    expect(screen.getByText("Migraine review")).toBeInTheDocument();
    expect(
      screen.getByText(/reports recurring headaches preceded by flashing lights/),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 more matching document/)).toBeInTheDocument();
  });

  it("presents the score as a retrieval aid, not confidence", () => {
    render(<SearchResults results={RESULTS} />);
    expect(screen.getByText(/Relevance score 0.87/)).toBeInTheDocument();
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/probability/i)).not.toBeInTheDocument();
  });
});
```

Run:

```text
docker compose run --rm --no-deps web pnpm vitest run features/search
```

Expected RED: module not found `./search-results`.

- [ ] Step 2: Server action

File: `apps/web/features/search/actions.ts`

```ts
"use server";

import { ApiError } from "@/lib/api/client";

import { searchClinicalRecords } from "./api";
import type { ClinicalSearchRequest, ClinicalSearchResponse } from "./schemas";

export type SearchActionResult =
  | { status: "ok"; response: ClinicalSearchResponse }
  | { status: "invalid"; message: string }
  | { status: "failed"; message: string };

export async function runClinicalSearch(
  input: ClinicalSearchRequest,
): Promise<SearchActionResult> {
  try {
    const response = await searchClinicalRecords(input);
    return { status: "ok", response };
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { status: "invalid", message: error.message };
    }
    return {
      status: "failed",
      message: "The search service is unavailable. Please try again shortly.",
    };
  }
}
```

- [ ] Step 3: Presentational results list

File: `apps/web/features/search/components/search-results.tsx`

```tsx
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
                <Badge tone="info">
                  {DOCUMENT_TYPE_LABELS[result.bestMatch.documentType]}
                </Badge>
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
```

- [ ] Step 4: Client experience with all six states

File: `apps/web/features/search/components/search-experience.tsx`

```tsx
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
        <div className="flex items-center gap-3 text-content-secondary" role="status">
          <Spinner /> Searching records…
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
```

- [ ] Step 5: Wire the route

File: `apps/web/app/search/page.tsx` (full replacement)

```tsx
import { SearchExperience } from "@/features/search/components/search-experience";
import { fetchSession } from "@/features/session/api";

export const metadata = { title: "Clinical search" };

export default async function ClinicalSearchPage() {
  const session = await fetchSession();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Clinical search</h1>
        <p className="mt-1 text-content-secondary">
          Describe a presentation in plain language to find patients in{" "}
          {session.practiceName} whose existing documents are relevant.
        </p>
      </header>
      <SearchExperience />
    </div>
  );
}
```

- [ ] Step 6: Verify GREEN

Run:

```text
docker compose run --rm --no-deps web pnpm test
docker compose run --rm --no-deps web pnpm lint
docker compose run --rm --no-deps web pnpm typecheck
```

Expected GREEN: vitest all passed (2 new + provided), eslint clean, tsc clean. Manual E2E (E2E001..E2E003) follows at T006 against `make dev`.

## TDD Plan

RED: Step 1 (module missing). Verify RED: vitest reports unresolved module. GREEN: Steps 2–5. Verify GREEN: Step 6. Refactor: none planned.

## Risks / Rollback

- Server Action boundary: `actions.ts` is `"use server"`; the client component never imports `api.ts` (server-only) directly — verified by typecheck/lint boundaries in Next.
- Checkbox filter maps cleanly to `documentTypes` (zod enum array); empty selection sends `undefined` (no filter).
- Rollback: restore `app/search/page.tsx` from git; delete the four new feature files.
- Relevance score wording: fixed label "Relevance score" with a two-decimal number; test asserts no confidence/probability wording.

## Self Review

- Spec coverage: AC-7 — query input (Step 4), optional type filter (Step 4), ranked results + evidence (Step 3), patient navigation (Step 3), six states (Step 4).
- Placeholder scan: none.
- Type/signature consistency: zod schemas are the single source; component props derive from `ClinicalSearchResponse`.
- Command specificity: exact `make test-web`-equivalent container commands.
- Branch context: not-applicable; Git actions authorized by this plan: none.

## Handoff

Next action: execute Steps 1–6, then T005 (acceptance coverage sweep) and T006 (E2E + README).
Stop condition: repeated verification failure after diagnosis, or contract change.
Evidence to record in notes.md: RED/GREEN outputs, test/lint/typecheck results.
