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

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
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
};
