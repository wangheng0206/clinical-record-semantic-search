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
