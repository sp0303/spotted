// Types mirror backend/spotted/search.py (details() and summarize()).
import { ApiError, request } from "./api";

export { ApiError };

export type ListingStatus = "found" | "not_found" | "coming_soon" | "unknown";

export interface Listing {
  platform: string;
  status: ListingStatus;
  /** The listing itself when found; otherwise a search link to check by hand. */
  url: string | null;
  issues: string[];
}

export interface PressArticle {
  title: string;
  /** Publication name, e.g. "D Magazine". */
  source: string | null;
  /** The publication's site. */
  source_url: string | null;
  url: string | null;
  published: string | null;
}

export interface Press {
  client_articles: PressArticle[];
  category_articles: PressArticle[];
  competitor_articles: (PressArticle & { competitor: string })[];
  client_sources: string[];
  competitor_only_sources: string[];
}

export interface SearchSummary {
  checked_at: string | null;
  queries: {
    query: string;
    maps: { client_rank: number | null; results: string[] };
    web: { client_rank: number | null; results: { domain: string; title: string | null }[] };
  }[];
  listings: Listing[];
  coming_soon: string[];
  /** Google News articles; absent when the news check didn't run. */
  press?: Press;
}

export type ViewStatus = "done" | "error" | "timeout" | "skipped" | "pending";

export interface MapsPlace {
  title: string;
  uri: string | null;
  place_id: string | null;
  position: number;
  is_client: boolean;
}

export interface WebSource {
  domain: string;
  url: string | null;
  title: string | null;
  position: number;
  is_client: boolean;
  source_type: string;
}

interface ViewBase {
  status: ViewStatus;
  error: string | null;
  client_rank: number | null;
  seconds: number | null;
  search_queries: string[];
}

export interface SearchQueryDetail {
  query: string;
  intent: "category" | "service" | "branded";
  maps: ViewBase & { results: MapsPlace[] };
  web: ViewBase & { results: WebSource[] };
  check_urls: { google: string; bing: string };
}

export interface SearchCheck {
  audit_id: string;
  business_id: string;
  status: "running" | "complete" | "partial" | "failed";
  started_at: string | null;
  finished_at: string | null;
  expected_calls: number;
  finished_calls: number;
  location: { city: string | null; lat?: number | null; lng?: number | null };
  maps_skipped: string | null;
  top_n: number;
  cost_usd: number;
  note: string | null;
  summary: SearchSummary;
  queries: SearchQueryDetail[];
  news?: { status: "pending" | "done" | "not_run"; errors: string[]; queries: string[] };
  coming_soon: { key: string; label: string; needs: string; check_url: string }[];
}

export const searchApi = {
  start: (id: string) =>
    request<{ audit_id: string; expected_calls: number }>("POST", `/api/businesses/${id}/search`),
  latest: (id: string) => request<SearchCheck>("GET", `/api/businesses/${id}/search`),
};
