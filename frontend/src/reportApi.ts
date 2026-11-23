// Report (build step 4) and Action Center (step 5). Types mirror backend/spotted/report.py and recommendations.py.
import { request } from "./api";

export { ApiError } from "./api";

export type ActionStatus = "not_started" | "in_progress" | "done" | "dismissed";
export type Priority = "high" | "medium" | "low";
export type ActionCategory =
  | "indexing" | "crawler_access" | "rendering" | "citation_source" | "entity_brand" | "recommendation_evidence"
  | "content_gap" | "reviews" | "listings_voice" | "agent_readiness" | "platform_specific" | "measurement";

export interface Action {
  id: string;
  rule_key: string;
  category: ActionCategory;
  priority: Priority;
  title: string;
  why: string;
  how: string[];
  effort: "low" | "medium" | "high";
  confidence: "low" | "medium" | "high";
  is_best_practice: boolean;
  evidence: Record<string, unknown>[];
  link: string | null;
  status: ActionStatus;
  status_changed_at: string | null;
  active: boolean;
}

export interface ActionCounts {
  total: number;
  high: number;
  medium: number;
  low: number;
  not_started: number;
  in_progress: number;
  done: number;
  dismissed: number;
}

interface Unavailable {
  available: false;
}

export interface PlatformVisibility {
  key: string;
  label: string;
  search_enabled: boolean;
  answers: number;
  named: number;
  recommended: number;
  best_position: number | null;
  own_site_cited: number;
  errors: number;
  missed_prompts: string[];
  named_instead: { name: string; answers: number }[];
}

export interface Totals {
  answers: number;
  named: number;
  recommended: number;
  own_site_cited: number;
}

export interface Visibility {
  available: true;
  audit_id: string;
  status: string;
  checked_at: string | null;
  platforms: PlatformVisibility[];
  totals: Totals & { errors: number };
}

export interface Competitors {
  available: true;
  answers: number;
  client: { answers: number; recommended: number };
  others: { name: string; answers: number; platforms: string[]; known: boolean; attributes: string[] }[];
}

export interface CitationGap {
  domain: string;
  type: string | null;
  answers: number;
  competitors: string[];
  prompts: string[];
  platforms: string[];
  example_url: string | null;
}

export interface Citations {
  available: true;
  answers_with_sources: number;
  own_site_cited: number;
  client_answers_with_sources: number;
  gaps: CitationGap[];
  top_sources: { domain: string; answers: number; type: string }[];
}

export interface Accuracy {
  available: true;
  branded_answers: number;
  answers_naming_you: number;
  wrong: { platform: string; prompt: string; facts: Record<string, { said: string; confirmed: string[] }> }[];
}

export interface FoundationsSummary {
  available: true;
  audit_id: string;
  checked_at: string;
  url: string | null;
  counts: Record<"issue" | "warning" | "inconclusive" | "opportunity" | "not_verified" | "pass", number>;
  issues: { check_type: string; status: string; summary: string; fix: string | null; target: string | null }[];
  blocked_crawlers: { token: string; operator: string | null; purpose: string; result: string; robots: string }[];
}

export interface SearchSummary {
  available: true;
  audit_id: string | null;
  checked_at: string | null;
  queries: {
    query: string;
    maps_checked: boolean;
    maps_rank: number | null;
    maps_results: string[];
    web_checked: boolean;
    web_rank: number | null;
    web_results: string[];
  }[];
  maps: { checked: number; found: number };
  web: { checked: number; found: number };
  listings: { platform: string; status: "found" | "not_found" | "coming_soon" | "unknown"; url: string | null; issues: string[] }[];
  coming_soon: string[];
  press?: Press | Unavailable;
}

export interface Article {
  title: string;
  source: string | null;
  domain: string | null;
  url: string | null;
  published: string | null;
  competitor?: string | null;
}

/** News coverage (Google News RSS) from the search step. */
export interface Press {
  available: true;
  client_articles: Article[];
  category_articles: Article[];
  competitor_articles: Article[];
  client_sources: string[];
  competitor_only_sources: string[];
}

export interface Comparison {
  available: true;
  previous_audit_id: string;
  previous_checked_at: string | null;
  same_questions: boolean;
  same_platforms: boolean;
  totals: { before: Totals; after: Totals; named_change: number; small: boolean };
  platforms: { key: string; label: string; before: Totals | null; after: Totals | null; named_change?: number; small?: boolean }[];
  competitors: { name: string; before: number; after: number }[];
  note: string;
}

export interface Report {
  business: {
    id: string;
    name: string;
    domain: string;
    website_url: string;
    category: string | null;
    city: string | null;
    confirmed: boolean;
    competitors: string[];
  };
  overview: {
    generated_at: string;
    method: string;
    foundations_checked_at: string | null;
    ai_checked_at: string | null;
    ai_status: string | null;
    ai_run_in_progress: boolean;
    search_checked_at: string | null;
    platforms: string[];
    questions: number;
    visibility_questions: number;
    runs_per_question: number | null;
    location: { city?: string | null } | null;
    skipped_platforms: { key: string; label: string; reason: string }[];
    limitations: string[];
    coming_soon: string[];
  };
  visibility: Visibility | Unavailable;
  competitors: Competitors | Unavailable;
  citations: Citations | Unavailable;
  accuracy: Accuracy | Unavailable;
  foundations: FoundationsSummary | Unavailable;
  search: SearchSummary | Unavailable;
  comparison: Comparison | Unavailable;
  actions: Action[];
  action_counts: ActionCounts;
}

export const reportApi = {
  getReport: (id: string) => request<Report>("GET", `/api/businesses/${id}/report`),
  setActionStatus: (id: string, actionId: string, status: ActionStatus) =>
    request<Action>("PATCH", `/api/businesses/${id}/actions/${actionId}`, { status }),
};
