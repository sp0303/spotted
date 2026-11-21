-- AI Search & Business Visibility — PostgreSQL schema, draft v1 (20 Nov 2026)
-- PostgreSQL 15+. Raw provider payloads go in JSONB; everything we query or aggregate is a column.
-- Changes after v1 go through migrations (e.g. Alembic), never by editing this file in production.

-- =====================================================================
-- Enums
-- =====================================================================
CREATE TYPE audit_tier        AS ENUM ('free', 'paid');
CREATE TYPE audit_status      AS ENUM ('queued', 'running', 'partial', 'complete', 'failed', 'cancelled');
CREATE TYPE field_origin      AS ENUM ('extracted', 'inferred', 'confirmed');   -- where a profile value came from
CREATE TYPE prompt_intent     AS ENUM ('discovery', 'service', 'problem', 'budget', 'attribute',
                                       'neighborhood', 'comparison', 'branded', 'accuracy', 'voice_style');
CREATE TYPE ai_platform       AS ENUM ('chatgpt', 'gemini', 'perplexity', 'claude', 'copilot',
                                       'google_ai_overview', 'google_ai_mode');
CREATE TYPE run_surface       AS ENUM ('api', 'app');                           -- "API view" vs "app view"
CREATE TYPE location_method   AS ENUM ('none', 'prompt_only', 'api_location', 'maps_latlng', 'proxy_profile', 'real_user');
CREATE TYPE run_status        AS ENUM ('queued', 'running', 'done', 'timeout', 'error', 'blocked');
CREATE TYPE mention_kind      AS ENUM ('recommended', 'mentioned');
CREATE TYPE source_type       AS ENUM ('own_site', 'competitor_site', 'directory', 'review_site', 'publication',
                                       'blog_listicle', 'forum', 'social', 'maps', 'marketplace', 'other');
CREATE TYPE search_engine     AS ENUM ('google', 'bing', 'google_maps', 'bing_maps');
CREATE TYPE check_type        AS ENUM ('google_index', 'bing_index', 'sitemap', 'indexnow', 'robots_txt',
                                       'cdn_waf', 'js_render', 'hidden_content', 'http_status', 'noindex',
                                       'canonical', 'webmcp', 'listing');
CREATE TYPE check_status      AS ENUM ('pass', 'issue', 'warning', 'opportunity', 'not_verified', 'inconclusive');
CREATE TYPE evidence_level    AS ENUM ('observed', 'likely', 'verified', 'submitted_only');
CREATE TYPE crawler_group     AS ENUM ('search', 'user_fetch', 'training');
CREATE TYPE robots_rule       AS ENUM ('allow', 'disallow', 'no_rule');
CREATE TYPE listing_platform  AS ENUM ('google_business_profile', 'apple_business_connect', 'bing_places', 'yelp');
CREATE TYPE action_category   AS ENUM ('indexing', 'crawler_access', 'rendering', 'citation_source', 'entity_brand',
                                       'recommendation_evidence', 'content_gap', 'reviews', 'listings_voice',
                                       'agent_readiness', 'platform_specific', 'measurement');
CREATE TYPE action_priority   AS ENUM ('high', 'medium', 'low');
CREATE TYPE action_status     AS ENUM ('not_started', 'in_progress', 'done', 'dismissed');
CREATE TYPE job_status        AS ENUM ('queued', 'running', 'done', 'failed');

-- =====================================================================
-- Users and businesses
-- =====================================================================
CREATE TABLE users (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email       text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE businesses (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id      uuid REFERENCES users(id) ON DELETE SET NULL,
    name          text NOT NULL,
    website_url   text NOT NULL,
    domain        text NOT NULL,                   -- normalized, e.g. "mcshanflorist.com"
    category      text,
    subcategories text[] NOT NULL DEFAULT '{}',
    description   text,
    differentiators text[] NOT NULL DEFAULT '{}',
    languages     text[] NOT NULL DEFAULT '{}',
    profile_raw   jsonb,                           -- extraction output as returned
    field_origins jsonb NOT NULL DEFAULT '{}',     -- {"category": "inferred", "services": "confirmed", ...}
    confirmed_at  timestamptz,                     -- owner confirmed the profile
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX businesses_domain_idx ON businesses (domain);

-- Other names the business appears under (for matching mentions in AI answers)
CREATE TABLE business_aliases (
    business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    alias       text NOT NULL,
    PRIMARY KEY (business_id, alias)
);

CREATE TABLE business_locations (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    label         text,                            -- "Main shop", "Service area: Plano"
    address       text,
    city          text,
    region        text,
    country_code  char(2) NOT NULL,
    postal_code   text,
    lat           double precision,
    lng           double precision,
    is_physical   boolean NOT NULL DEFAULT true,   -- false = service area only
    is_target     boolean NOT NULL DEFAULT true,   -- owner wants to be found here
    priority      smallint NOT NULL DEFAULT 1,
    origin        field_origin NOT NULL DEFAULT 'extracted'
);
CREATE INDEX business_locations_business_idx ON business_locations (business_id);

CREATE TABLE services (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name        text NOT NULL,
    description text,
    origin      field_origin NOT NULL DEFAULT 'extracted'
);

CREATE TABLE competitors (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name        text NOT NULL,
    domain      text,
    origin      text NOT NULL DEFAULT 'observed' CHECK (origin IN ('suggested', 'user', 'observed')),
    first_seen  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (business_id, name)
);

-- =====================================================================
-- Location profiles (reusable, ~200–300 metros) and the crawler registry
-- =====================================================================
CREATE TABLE location_profiles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,          -- "us-tx-dallas"
    country_code    char(2) NOT NULL,
    region          text,
    city            text NOT NULL,
    lat             double precision NOT NULL,
    lng             double precision NOT NULL,
    locale          text NOT NULL,                 -- "en-US"
    timezone        text NOT NULL,                 -- "America/Chicago"
    proxy_provider  text,
    proxy_target    jsonb,                         -- provider-specific city/session settings (no secrets)
    device          text NOT NULL DEFAULT 'desktop' CHECK (device IN ('desktop', 'mobile')),
    active          boolean NOT NULL DEFAULT true,
    last_verified_at timestamptz,
    verified_ip_city text                          -- city the exit IP resolved to at last check
);

CREATE TABLE crawlers (
    user_agent   text PRIMARY KEY,                 -- "OAI-SearchBot"
    operator     text NOT NULL,                    -- "OpenAI"
    purpose      crawler_group NOT NULL,
    is_token_only boolean NOT NULL DEFAULT false,  -- robots.txt control token that doesn't crawl (Google-Extended, Applebot-Extended)
    docs_url     text,
    notes        text,
    verified_at  timestamptz                       -- last checked against official docs
);

-- =====================================================================
-- Audits and prompts
-- =====================================================================
CREATE TABLE audits (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id         uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    tier                audit_tier NOT NULL,
    status              audit_status NOT NULL DEFAULT 'queued',
    methodology_version text NOT NULL,             -- bump when prompts, models or method change
    config              jsonb NOT NULL,            -- platforms, runs, locations, timeouts as used
    requested_ip        inet,                      -- free-run abuse limits
    requested_email     text,
    started_at          timestamptz,
    first_results_at    timestamptz,               -- for the 60-second target
    finished_at         timestamptz,
    report_sent_at      timestamptz,
    cost_usd            numeric(10,4) NOT NULL DEFAULT 0,
    previous_audit_id   uuid REFERENCES audits(id),-- for before/after comparison
    created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audits_business_idx ON audits (business_id, created_at DESC);
CREATE INDEX audits_free_limits_idx ON audits (requested_ip, created_at) WHERE tier = 'free';

CREATE TABLE prompt_templates (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    intent    prompt_intent NOT NULL,
    template  text NOT NULL,                       -- "best {category} in {city}"
    version   int NOT NULL DEFAULT 1,
    active    boolean NOT NULL DEFAULT true,
    UNIQUE (template, version)
);

CREATE TABLE audit_prompts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id        uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    template_id     uuid REFERENCES prompt_templates(id),
    text            text NOT NULL,                 -- exact prompt sent
    intent          prompt_intent NOT NULL,
    target_location_id uuid REFERENCES business_locations(id),
    sort_order      smallint NOT NULL DEFAULT 0,
    user_edited     boolean NOT NULL DEFAULT false
);
CREATE INDEX audit_prompts_audit_idx ON audit_prompts (audit_id);

-- =====================================================================
-- AI platform runs: one row per call
-- =====================================================================
CREATE TABLE platform_runs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id            uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    audit_prompt_id     uuid NOT NULL REFERENCES audit_prompts(id) ON DELETE CASCADE,
    platform            ai_platform NOT NULL,
    surface             run_surface NOT NULL,
    model               text,                      -- "gemini-3.8-flash"
    search_enabled      boolean NOT NULL,          -- false = model-knowledge run
    grounding           text,                      -- "google_search", "google_maps", "web_search"
    location_method     location_method NOT NULL,
    location_profile_id uuid REFERENCES location_profiles(id),
    lat                 double precision,
    lng                 double precision,
    exit_ip_city        text,                      -- observed, for proxy/VPN runs
    server_region       text,                      -- where the call left from (API calls follow it)
    logged_in           boolean NOT NULL DEFAULT false,
    run_index           smallint NOT NULL,         -- 1..N repeat runs
    status              run_status NOT NULL DEFAULT 'queued',
    target_local_time   timestamp,                 -- time in the target city when run
    started_at          timestamptz,
    latency_ms          int,
    tokens_in           int,
    tokens_out          int,
    cost_usd            numeric(10,6),
    proxy_bytes         bigint,
    error               text
);
CREATE INDEX platform_runs_audit_idx ON platform_runs (audit_id, platform, audit_prompt_id);

CREATE TABLE responses (
    run_id          uuid PRIMARY KEY REFERENCES platform_runs(id) ON DELETE CASCADE,
    text            text NOT NULL,
    search_queries  text[] NOT NULL DEFAULT '{}',  -- queries the AI ran
    maps_places     jsonb,                         -- places returned by maps grounding
    screenshot_path text,                          -- object storage key
    raw             jsonb                          -- full provider payload
);

CREATE TABLE mentions (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id         uuid NOT NULL REFERENCES platform_runs(id) ON DELETE CASCADE,
    entity_name    text NOT NULL,                  -- as written in the answer
    normalized     text NOT NULL,                  -- for matching across runs
    is_client      boolean NOT NULL DEFAULT false,
    competitor_id  uuid REFERENCES competitors(id),
    position       smallint,                       -- order in the answer, when meaningful
    kind           mention_kind NOT NULL,
    context        text,                           -- sentence around the mention
    attributes     text[] NOT NULL DEFAULT '{}',   -- "luxury", "same-day", "since 1948"
    facts          jsonb,                          -- stated address, rating, category, hours
    facts_wrong    jsonb                           -- facts that conflict with the confirmed profile
);
CREATE INDEX mentions_run_idx ON mentions (run_id);
CREATE INDEX mentions_normalized_idx ON mentions (normalized);

CREATE TABLE citations (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                uuid NOT NULL REFERENCES platform_runs(id) ON DELETE CASCADE,
    url                   text NOT NULL,
    domain                text NOT NULL,
    title                 text,
    position              smallint,
    source_type           source_type,
    mentions_client       boolean,
    mentions_competitors  text[] NOT NULL DEFAULT '{}'
);
CREATE INDEX citations_run_idx ON citations (run_id);
CREATE INDEX citations_domain_idx ON citations (domain);

-- =====================================================================
-- Search engine and maps results (from SERP APIs)
-- =====================================================================
CREATE TABLE search_results (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id        uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    audit_prompt_id uuid REFERENCES audit_prompts(id) ON DELETE CASCADE,
    engine          search_engine NOT NULL,
    provider        text NOT NULL,                 -- SERP API vendor
    location_label  text,
    position        smallint,
    result_type     text,                          -- organic, local_pack, ai_overview, ad
    title           text,
    url             text,
    domain          text,
    place_id        text,
    rating          numeric(2,1),
    review_count    int,
    is_client       boolean NOT NULL DEFAULT false,
    captured_at     timestamptz NOT NULL DEFAULT now(),
    raw             jsonb
);
CREATE INDEX search_results_audit_idx ON search_results (audit_id, engine);

-- =====================================================================
-- Foundation audit
-- =====================================================================
CREATE TABLE foundation_checks (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id    uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    check_type  check_type NOT NULL,
    target      text,                              -- URL, sitemap, or listing platform
    status      check_status NOT NULL,
    evidence_level evidence_level NOT NULL DEFAULT 'observed',
    summary     text NOT NULL,                     -- plain-language result for the owner
    evidence    jsonb,                             -- headers, snippets, diffs
    checked_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX foundation_checks_audit_idx ON foundation_checks (audit_id);

CREATE TABLE crawler_access (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id      uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    url           text NOT NULL,
    user_agent    text NOT NULL REFERENCES crawlers(user_agent),
    robots        robots_rule NOT NULL,
    http_status   smallint,
    challenge     boolean,                         -- CDN/WAF challenge page detected
    result        text NOT NULL CHECK (result IN ('accessible', 'likely_blocked', 'verified_blocked', 'error', 'inconclusive')),
    cdn           text,                            -- "cloudflare"
    evidence      jsonb,
    checked_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (audit_id, url, user_agent)
);

CREATE TABLE listings (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    audit_id      uuid REFERENCES audits(id) ON DELETE SET NULL,
    platform      listing_platform NOT NULL,
    url           text,
    found         boolean NOT NULL,
    claimed       boolean,
    name_match    boolean,
    address_match boolean,
    phone_match   boolean,
    hours_match   boolean,
    category      text,
    rating        numeric(2,1),
    review_count  int,
    issues        jsonb,
    checked_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX listings_business_idx ON listings (business_id, platform);

-- =====================================================================
-- Report numbers and the Action Center
-- =====================================================================
-- Counts behind every reported number ("appeared in 5 of 25 prompts, 3 runs each")
CREATE TABLE audit_metrics (
    id           bigserial PRIMARY KEY,
    audit_id     uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    platform     ai_platform,                      -- NULL = all platforms
    surface      run_surface,
    metric       text NOT NULL,                    -- mention_rate, recommendation_rate, citation_rate, ...
    numerator    int NOT NULL,
    denominator  int NOT NULL,
    detail       jsonb,
    CONSTRAINT audit_metrics_unique UNIQUE NULLS NOT DISTINCT (audit_id, metric, platform, surface)
);

CREATE TABLE recommendations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id          uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    business_id       uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    category          action_category NOT NULL,
    title             text NOT NULL,
    finding           text NOT NULL,
    evidence          jsonb NOT NULL,              -- run ids, citation ids, check ids it rests on
    action            text NOT NULL,
    why               text,
    priority          action_priority NOT NULL,
    effort            text CHECK (effort IN ('low', 'medium', 'high')),
    confidence        text CHECK (confidence IN ('low', 'medium', 'high')),
    is_best_practice  boolean NOT NULL DEFAULT false, -- true = general advice, not backed by this audit's evidence
    linked_tool       text,                        -- existing SEO-product tool to open
    draft             jsonb,                       -- generated page draft, JSON-LD, WebMCP tool draft...
    status            action_status NOT NULL DEFAULT 'not_started',
    status_changed_at timestamptz,
    carried_from_id   uuid REFERENCES recommendations(id), -- same action across re-audits
    created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX recommendations_business_idx ON recommendations (business_id, status);

-- =====================================================================
-- Evaluation of our recommendations (Modern Web Guidance method)
-- =====================================================================
CREATE TABLE eval_expectations (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_category text NOT NULL,               -- "florist"
    kind             text NOT NULL CHECK (kind IN ('must', 'must_not')),
    rule             text NOT NULL,
    active           boolean NOT NULL DEFAULT true
);

CREATE TABLE eval_runs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    methodology_version text NOT NULL,
    model               text NOT NULL,
    started_at          timestamptz NOT NULL DEFAULT now(),
    notes               text
);

CREATE TABLE eval_scores (
    eval_run_id     uuid NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    audit_id        uuid NOT NULL REFERENCES audits(id) ON DELETE CASCADE,  -- a saved test-set audit
    expectation_id  uuid NOT NULL REFERENCES eval_expectations(id),
    passed          boolean NOT NULL,
    judge_notes     text,
    PRIMARY KEY (eval_run_id, audit_id, expectation_id)
);

-- =====================================================================
-- Job queue (Postgres, no Redis): workers use SELECT ... FOR UPDATE SKIP LOCKED
-- =====================================================================
CREATE TABLE jobs (
    id          bigserial PRIMARY KEY,
    kind        text NOT NULL,                     -- "platform_run", "foundation_check", "send_report"
    payload     jsonb NOT NULL,
    priority    smallint NOT NULL DEFAULT 5,       -- free runs get higher priority
    status      job_status NOT NULL DEFAULT 'queued',
    run_after   timestamptz NOT NULL DEFAULT now(),
    attempts    smallint NOT NULL DEFAULT 0,
    max_attempts smallint NOT NULL DEFAULT 3,
    locked_by   text,
    locked_at   timestamptz,
    last_error  text,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_ready_idx ON jobs (priority, run_after) WHERE status = 'queued';
