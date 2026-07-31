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
