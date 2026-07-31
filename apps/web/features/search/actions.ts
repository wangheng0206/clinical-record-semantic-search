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
