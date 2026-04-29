/** TypeScript types mirroring the Django API responses. */

export type SourceType = "dataset" | "generated";

export interface MidiItem {
  id: number;
  name: string;
  filename: string;
  source_type: SourceType;
  file_url: string;
  duration_seconds: number | null;
  rating: number | null;
  approved: boolean | null;  // null=not reviewed, true=approved, false=rejected
  favorite: boolean;
  tags: string[];
  notes: string;
  file_missing: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  name: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface FeedbackPayload {
  rating?: number | null;
  approved?: boolean | null;
  favorite?: boolean;
  tags?: string[];
  notes?: string;
}

export interface MidiFilters {
  source_type?: SourceType | "all" | "favorites" | "approved" | "rejected" | "unreviewed";
  tag?: string;
  search?: string;
  min_rating?: number;
  page?: number;
}
