import useSWR, { mutate as globalMutate } from "swr";
import client from "./client";
import type {
  MidiItem,
  Tag,
  PaginatedResponse,
  FeedbackPayload,
  MidiFilters,
} from "../types/midi";

// ─── Fetcher ──────────────────────────────────────────────────────────────────
const fetcher = (url: string) => client.get(url).then((r) => r.data);

// ─── Build query string from filters ─────────────────────────────────────────
export function buildMidiQueryString(filters: MidiFilters): string {
  const params = new URLSearchParams();

  if (filters.search) params.set("search", filters.search);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.page && filters.page > 1) params.set("page", String(filters.page));
  if (filters.min_rating) params.set("min_rating", String(filters.min_rating));

  switch (filters.source_type) {
    case "dataset":
    case "generated":
      params.set("source_type", filters.source_type);
      break;
    case "favorites":
      params.set("favorite", "true");
      break;
    case "approved":
      params.set("approved", "true");
      break;
    case "rejected":
      params.set("approved", "false");
      break;
    case "unreviewed":
      params.set("approved", "null");
      break;
    // "all" — no filter
  }

  const qs = params.toString();
  return qs ? `/midis/?${qs}` : "/midis/";
}

// ─── Hooks ────────────────────────────────────────────────────────────────────
export function useMidis(filters: MidiFilters) {
  const key = buildMidiQueryString(filters);
  return useSWR<PaginatedResponse<MidiItem>>(key, fetcher);
}

export function useTags() {
  return useSWR<Tag[]>("/tags/", fetcher);
}

// ─── Mutations ────────────────────────────────────────────────────────────────
export async function saveFeedback(
  id: number,
  payload: FeedbackPayload
): Promise<MidiItem> {
  const { data } = await client.patch<MidiItem>(
    `/midis/${id}/feedback/`,
    payload
  );
  return data;
}

export async function triggerScan(): Promise<{ status: string; total_items: number }> {
  const { data } = await client.post("/midis/scan/");
  return data;
}

/** Invalidate all /midis/ SWR cache entries (after feedback update, scan, etc.) */
export function revalidateMidis() {
  return globalMutate((key: string) => typeof key === "string" && key.startsWith("/midis"), undefined, { revalidate: true });
}
