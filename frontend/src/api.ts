// Types mirror backend/spotted/models.py and the foundations response in backend/spotted/api.py.

export type Origin = "extracted" | "inferred" | "confirmed";

export interface Fact {
  value: string;
  origin: Origin;
  source_url?: string | null;
  evidence?: string | null;
}

export interface Service extends Fact {
  description?: string | null;
}

export interface Location {
  label?: string | null;
  address?: string | null;
  city?: string | null;
  region?: string | null;
  country_code?: string | null;
  postal_code?: string | null;
  lat?: number | null;
  lng?: number | null;
  is_physical: boolean;
  is_target: boolean;
  priority: number;
  origin: Origin;
  source_url?: string | null;
  evidence?: string | null;
}

export interface SocialProfile {
  platform: string;
  url: string;
  origin: Origin;
  source_url?: string | null;
}

export interface BusinessProfile {
  website_url: string;
  domain: string;
  name: Fact;
  aliases: Fact[];
  category?: Fact | null;
  subcategories: Fact[];
  description?: Fact | null;
  services: Service[];
  locations: Location[];
  phones: Fact[];
  emails: Fact[];
  hours: Fact[];
  languages: Fact[];
  target_customer?: Fact | null;
  differentiators: Fact[];
  social_profiles: SocialProfile[];
  suggested_competitors: Fact[];
  warnings: string[];
  pages_read: string[];
}

export interface StoredProfile {
  business_id: string;
  confirmed: boolean;
  profile: BusinessProfile;
}

export type CheckStatus = "pass" | "issue" | "warning" | "opportunity" | "not_verified" | "inconclusive";

export interface Check {
  check_type: string;
  target: string | null;
  status: CheckStatus;
  evidence_level: "observed" | "likely" | "verified" | "submitted_only";
  summary: string;
  fix: string | null;
  evidence: Record<string, unknown> | null;
}

export type CrawlerPurpose = "search" | "user_fetch" | "training";

export interface CrawlerAccess {
  token: string;
  operator: string;
  purpose: CrawlerPurpose;
  url: string;
  robots: "allow" | "disallow" | "no_rule";
  robots_line: string | null;
  http_status: number | null;
  challenge: boolean | null;
  result: "accessible" | "likely_blocked" | "verified_blocked" | "error" | "inconclusive";
  cdn: string | null;
  note: string;
  token_only: boolean;
}

export interface Foundations {
  audit_id: string;
  checked_at: string;
  url: string | null;
  final_url: string | null;
  cdn: string | null;
  platform: string | null;
  rendered: boolean;
  checks: Check[];
  crawlers: CrawlerAccess[];
  purpose_labels: Record<CrawlerPurpose, string>;
}

// ---------- AI runs (build step 3) ----------

export type PromptIntent =
  | "discovery" | "service" | "problem" | "budget" | "attribute" | "neighborhood" | "comparison"
  | "branded" | "accuracy" | "voice_style";

export interface PromptIn {
  text: string;
  intent: PromptIntent;
  user_edited: boolean;
}

export interface PlatformOption {
  key: string;
  label: string;
  search_enabled: boolean;
  default: boolean;
}

export interface FullAuditInfo {
  enabled: boolean;
  message: string | null;
  max_core: number;
  max_branded: number;
  runs: number;
  branded_runs: number;
  platforms: string[];
  search_off: boolean;
  locations: string[];
  coming_soon: string[];
}

export interface PromptSuggestions {
  prompts: PromptIn[];
  platforms: PlatformOption[];
  coming_soon: { key: string; label: string; note?: string }[];
  max_prompts: number;
  // Full ("paid") audit, build step 7. Optional so older responses still type-check.
  full_prompts?: PromptIn[];
  full_audit?: FullAuditInfo;
  free_limits?: { per_business_per_day: number; per_ip_per_day: number; reuse_minutes: number };
}

export type AITier = "free" | "paid";

export interface StartAIRunResult {
  audit_id: string;
  expected_runs: number;
  reused?: boolean;
  tier?: AITier;
}

export interface AIPlatformSummary {
  key: string;
  label: string;
  search_enabled: boolean;
  answers: number;
  named: number;
  recommended: number;
  best_position: number | null;
  own_site_cited: number;
  errors: number;
  cost_usd: number;
  avg_seconds: number;
  skipped?: number;
  prompts_asked?: number;
  prompts_named?: number;
  location_method?: string;
}

export interface AIResult {
  run_id: string;
  platform_key: string;
  label: string;
  run_index: number;
  location_id?: string;
  city?: string | null;
  prompt_text?: string;
  status: "done" | "timeout" | "error" | "skipped";
  error: string | null;
  seconds: number;
  client: { position: number; kind: "recommended" | "mentioned"; context: string } | null;
  asked_for_location: boolean;
  names: string[];
  sources: { domain: string; type: string; url: string }[];
  search_queries: string[];
  text: string;
}

export interface AIRun {
  audit_id: string;
  business_id: string;
  status: "running" | "complete" | "partial" | "failed";
  started_at: string;
  finished_at: string | null;
  first_result_seconds: number | null;
  expected_runs: number;
  finished_runs: number;
  location: { city: string | null };
  skipped_platforms: { key: string; label: string; reason: string }[];
  cost_usd: number;
  visibility_answers: number;
  platforms: AIPlatformSummary[];
  competitors: { name: string; answers: number; platforms: string[]; known: boolean; prompts?: number }[];
  sources: { domain: string; answers: number; type: string }[];
  wrong_facts: { platform: string; prompt: string; facts: Record<string, { said: string; confirmed: string[] }> }[];
  prompts: { id: string; text: string; intent: PromptIntent; results: AIResult[]; frequency?: AIFrequency[] }[];
  note: string | null;
  // Added with the full audit (build step 7).
  tier?: AITier;
  runs_per_prompt?: number;
  previous_audit_id?: string | null;
  locations?: AILocationSummary[];
  search_comparison?: AISearchComparison | null;
  skipped_runs?: number;
}

/** How often one platform named the business for one question at one location, across repeat runs. */
export interface AIFrequency {
  platform_key: string;
  label: string;
  search_enabled: boolean;
  location_id: string;
  city: string | null;
  runs: number;
  done: number;
  named: number;
  recommended: number;
}

export interface AILocationSummary {
  id: string;
  city: string | null;
  region?: string | null;
  answers: number;
  named: number;
  recommended: number;
  platforms: { key: string; label: string; answers: number; named: number }[];
  competitors: { name: string; answers: number }[];
}

export interface AISearchSide {
  answers: number;
  named: number;
  recommended: number;
  platforms: string[];
}

export interface AISearchComparison {
  search_on: AISearchSide;
  search_off: AISearchSide;
  competitors_both: string[];
  competitors_only_search_on: string[];
  competitors_only_search_off: string[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** Shared fetch helper; feature API files (reportApi.ts, searchApi.ts) import it. */
export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Couldn't reach Spotted. Check your connection and try again.", 0);
  }
  if (!resp.ok) {
    let message = `Something went wrong (HTTP ${resp.status}).`;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(message, resp.status);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  extractProfile: (url: string) => request<StoredProfile>("POST", "/api/profiles", { url }),
  getProfile: (id: string) => request<StoredProfile>("GET", `/api/businesses/${id}`),
  confirmProfile: (id: string, profile: BusinessProfile) =>
    request<StoredProfile>("PUT", `/api/businesses/${id}/profile`, profile),
  getFoundations: (id: string) => request<Foundations>("GET", `/api/businesses/${id}/foundations`),
  runFoundations: (id: string) => request<Foundations>("POST", `/api/businesses/${id}/foundations`),
  getAIPrompts: (id: string) => request<PromptSuggestions>("GET", `/api/businesses/${id}/ai-prompts`),
  startAIRun: (id: string, prompts: PromptIn[], platforms: string[], tier: AITier = "free") =>
    request<StartAIRunResult>("POST", `/api/businesses/${id}/ai-runs`,
      tier === "paid" ? { prompts, tier } : { prompts, platforms }),
  getAIRun: (auditId: string) => request<AIRun>("GET", `/api/ai-runs/${auditId}`),
  getLatestAIRun: (id: string) => request<AIRun>("GET", `/api/businesses/${id}/ai-runs/latest`),
};
