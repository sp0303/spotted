import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { AIRun, BusinessProfile, Check } from "./api";
import ProfilePage, { confirmProblems } from "./pages/ProfilePage";
import { groupChecks } from "./pages/ChecksPage";
import AIPage from "./pages/AIPage";

const profile: BusinessProfile = {
  website_url: "https://www.petallane.example/",
  domain: "petallane.example",
  name: { value: "Petal Lane Florist", origin: "extracted", source_url: "https://www.petallane.example/" },
  aliases: [],
  category: { value: "florist", origin: "inferred" },
  subcategories: [],
  description: null,
  services: [{ value: "Same-day delivery", origin: "extracted", source_url: "https://www.petallane.example/", evidence: "We deliver same-day" }],
  locations: [
    { city: "Dallas", region: "TX", country_code: "US", address: "1200 Elm St", is_physical: true, is_target: true, priority: 1, origin: "extracted" },
    { city: "Fort Worth", country_code: null, is_physical: false, is_target: true, priority: 1, origin: "inferred" },
  ],
  phones: [{ value: "+1 214-555-0142", origin: "extracted" }],
  emails: [],
  hours: [],
  languages: [],
  target_customer: null,
  differentiators: [],
  social_profiles: [],
  suggested_competitors: [{ value: "McShan Florist", origin: "inferred" }],
  warnings: ["Some locations are missing a country. Please add it."],
  pages_read: ["https://www.petallane.example/"],
};

describe("confirmProblems", () => {
  it("needs a country on every location and at least one target", () => {
    expect(confirmProblems(profile)).toEqual(["Add a two-letter country code for 1 location(s), e.g. US."]);
    expect(confirmProblems({ ...profile, locations: [] })).toEqual([
      "Add at least one place where you want customers to find you.",
    ]);
  });
});

describe("groupChecks", () => {
  const c = (check_type: string, status: Check["status"], target: string): Check => ({
    check_type, status, target, summary: "Search engines are allowed to list this page.", fix: null,
    evidence_level: "observed", evidence: null,
  });
  it("collapses passing per-page checks and keeps failing ones", () => {
    const out = groupChecks([c("noindex", "pass", "/a"), c("noindex", "pass", "/b"), c("canonical", "issue", "/c"),
      c("canonical", "pass", "/d"), c("sitemap", "pass", "/s")]);
    expect(out.map((x) => [x.check_type, x.status])).toEqual([["sitemap", "pass"], ["noindex", "pass"], ["canonical", "issue"]]);
    expect(out[1].summary).toBe("Search engines are allowed to list this page (2 pages checked).");
  });
});

describe("ProfilePage", () => {
  it("shows origins, blocks confirm until fixed, then saves and moves on", async () => {
    const calls: { method: string; url: string; body?: BusinessProfile }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(init.body as string) : undefined;
      calls.push({ method, url, body });
      const payload = { business_id: "b1", confirmed: method === "PUT", profile: body ?? profile };
      return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } });
    }));
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/b/b1"]}>
        <Routes>
          <Route path="/b/:id" element={<ProfilePage />} />
          <Route path="/b/:id/checks" element={<p>checks page</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { level: 1, name: "Petal Lane Florist" })).toBeInTheDocument();
    expect(screen.getAllByText("From your site").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Our guess").length).toBeGreaterThan(0);
    expect(screen.getByText("Some locations are missing a country. Please add it.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm and check my website" }));
    expect(await screen.findByText(/two-letter country code/)).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);

    // Remove the guessed Fort Worth area and edit a service.
    const removes = screen.getAllByRole("button", { name: "Remove" });
    await user.click(removes[1]);
    const svc = screen.getByLabelText("Products and services 1");
    await user.clear(svc);
    await user.type(svc, "Same-day flower delivery");
    await user.click(screen.getByRole("button", { name: "Confirm and check my website" }));

    await waitFor(() => expect(screen.getByText("checks page")).toBeInTheDocument());
    const put = calls.find((c) => c.method === "PUT")!;
    expect(put.url).toBe("/api/businesses/b1/profile");
    expect(put.body!.locations.map((l) => l.city)).toEqual(["Dallas"]);
    expect(put.body!.services[0]).toMatchObject({ value: "Same-day flower delivery", origin: "confirmed" });
  });
});

describe("AIPage", () => {
  const result = (over: Partial<AIRun["prompts"][0]["results"][0]>) => ({
    run_id: "r1", platform_key: "gemini_search", label: "Gemini (Google Search)", run_index: 1, status: "done" as const,
    error: null, seconds: 9.5, client: null, asked_for_location: false, names: ["McShan Florist"], sources: [],
    search_queries: [], text: "Try McShan Florist.", ...over,
  });
  const setupBody = (enabled: boolean) => ({
    max_prompts: 10,
    prompts: [{ text: "best florists in Dallas", intent: "discovery", user_edited: false },
              { text: "what is Petal Lane in Dallas and is it any good?", intent: "branded", user_edited: false }],
    platforms: [{ key: "gemini_search", label: "Gemini (Google Search)", search_enabled: true, default: true },
                { key: "perplexity", label: "Perplexity", search_enabled: true, default: true },
                { key: "gemini_memory", label: "Gemini (no search)", search_enabled: false, default: false }],
    coming_soon: [{ key: "copilot", label: "Microsoft Copilot", note: "via Azure grounding with Bing (needs an Azure key)" }],
    full_prompts: [{ text: "best florists in Dallas", intent: "discovery", user_edited: false },
                   { text: "affordable florist in Dallas", intent: "budget", user_edited: false },
                   { text: "what is Petal Lane in Dallas and is it any good?", intent: "branded", user_edited: false }],
    full_audit: { enabled, message: enabled ? null : "The full audit is coming soon.", max_core: 25, max_branded: 5,
                  runs: 3, branded_runs: 1, platforms: ["gemini_search", "gemini_memory"], search_off: true,
                  locations: ["Dallas", "Plano"], coming_soon: ["Screenshots of each answer"] },
    free_limits: { per_business_per_day: 3, per_ip_per_day: 10, reuse_minutes: 60 },
  });
  const renderPage = () => {
    render(
      <MemoryRouter initialEntries={["/b/b1/ai"]}>
        <Routes><Route path="/b/:id/ai" element={<AIPage />} /></Routes>
      </MemoryRouter>,
    );
    return userEvent.setup();
  };
  const json = (status: number, data: unknown) => new Response(JSON.stringify(data), { status });

  it("lets the owner edit questions, starts a run and shows who was named", async () => {
    const done: AIRun = {
      audit_id: "a1", business_id: "b1", status: "complete", started_at: "2026-11-24T00:00:00Z",
      finished_at: "2026-11-24T00:00:20Z", first_result_seconds: 9.5, expected_runs: 2, finished_runs: 2,
      location: { city: "Dallas" }, skipped_platforms: [], cost_usd: 0.0123, visibility_answers: 1, note: null,
      platforms: [
        { key: "gemini_search", label: "Gemini (Google Search)", search_enabled: true, answers: 1, named: 1,
          recommended: 1, best_position: 2, own_site_cited: 0, errors: 0, cost_usd: 0.01, avg_seconds: 9.5 },
        { key: "perplexity", label: "Perplexity", search_enabled: true, answers: 0, named: 0, recommended: 0,
          best_position: null, own_site_cited: 0, errors: 1, cost_usd: 0, avg_seconds: 0 },
      ],
      competitors: [{ name: "McShan Florist", answers: 1, platforms: ["Gemini (Google Search)"], known: true }],
      sources: [{ domain: "dmagazine.com", answers: 1, type: "publication" }],
      wrong_facts: [],
      prompts: [{ id: "p1", text: "best florists in Dallas", intent: "discovery", results: [
        result({ client: { position: 2, kind: "recommended", context: "Petal Lane is lovely." },
                 names: ["McShan Florist", "Petal Lane"], text: "Try McShan Florist or Petal Lane." }),
        result({ run_id: "r2", platform_key: "perplexity", label: "Perplexity", status: "error",
                 error: "Out of OpenRouter credit.", seconds: 0, names: [], text: "" }),
      ] }],
      tier: "free", runs_per_prompt: 1, locations: [], search_comparison: null,
    };
    let started: unknown;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/ai-runs/latest")) return json(404, { detail: "No AI run yet." });
      if (url.endsWith("/ai-prompts")) return json(200, setupBody(false));
      if (url.endsWith("/ai-runs") && init?.method === "POST") {
        started = JSON.parse(init.body as string);
        return json(202, { audit_id: "a1", expected_runs: 2, reused: true, tier: "free" });
      }
      if (url.endsWith("/api/ai-runs/a1")) return json(200, done);
      return json(404, { detail: "nope" });
    }));

    const user = renderPage();
    const q1 = await screen.findByLabelText("Question 1");
    // The full audit and Copilot are both "coming soon"; the full audit can't be picked.
    expect(screen.getAllByText("Coming soon")).toHaveLength(2);
    expect(screen.getByLabelText("Full audit")).toBeDisabled();
    expect(screen.getByText(/Azure grounding with Bing/)).toBeInTheDocument();
    await user.clear(q1);
    await user.type(q1, "best wedding florists in Dallas");
    await user.click(screen.getByLabelText("Remove question 2"));
    await user.click(screen.getByRole("button", { name: "Ask 2 assistants" }));

    await screen.findByText("Answers by question");
    expect(started).toEqual({ prompts: [{ text: "best wedding florists in Dallas", intent: "discovery", user_edited: true }],
                              platforms: ["gemini_search", "perplexity"] });
    expect(screen.getByText(/asked these same questions less than an hour ago/)).toBeInTheDocument();
    expect(screen.getByText("Recommended · #2")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("McShan Florist", { selector: ".truncate" })).toBeInTheDocument();
    expect(screen.getByText(/cost \$0\.012/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Next: search engines and Maps →" })).toBeInTheDocument();
    const bing = screen.getByRole("link", { name: "Bing AI Mode" });
    expect(bing).toHaveAttribute("href", "https://www.bing.com/copilotsearch?q=best%20florists%20in%20Dallas");
    expect(bing).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "Google AI Mode" }).getAttribute("href")).toContain("udm=50");
  });

  it("shows the daily limit message", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/ai-runs/latest")) return json(404, { detail: "No AI run yet." });
      if (url.endsWith("/ai-prompts")) return json(200, setupBody(false));
      if (url.endsWith("/ai-runs") && init?.method === "POST")
        return json(429, { detail: "You have used today's 3 free AI runs for this business." });
      return json(404, { detail: "nope" });
    }));
    const user = renderPage();
    await screen.findByLabelText("Question 1");
    await user.click(screen.getByRole("button", { name: "Ask 2 assistants" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("3 free AI runs");
  });

  it("starts a full audit and shows repeat runs, search off vs on and each location", async () => {
    const p = (key: string, label: string, search: boolean, named: number) => ({
      key, label, search_enabled: search, answers: 6, named, recommended: named, best_position: named ? 1 : null,
      own_site_cited: 0, errors: 0, cost_usd: 0.01, avg_seconds: 5,
    });
    const done: AIRun = {
      audit_id: "a2", business_id: "b1", status: "complete", started_at: "2026-11-24T00:00:00Z",
      finished_at: "2026-11-24T00:10:00Z", first_result_seconds: 4, expected_runs: 12, finished_runs: 12,
      location: { city: "Dallas" }, skipped_platforms: [], cost_usd: 0.2, visibility_answers: 12, note: null,
      platforms: [p("gemini_search", "Gemini (Google Search)", true, 2), p("gemini_memory", "Gemini (no search)", false, 0)],
      competitors: [], sources: [], wrong_facts: [],
      prompts: [{ id: "p1", text: "best florists in Dallas", intent: "discovery", results: [
        result({ run_id: "d1", location_id: "L1", city: "Dallas", prompt_text: "best florists in Dallas",
                 client: { position: 1, kind: "recommended", context: "x" } }),
        result({ run_id: "d2", run_index: 2, location_id: "L1", city: "Dallas", prompt_text: "best florists in Dallas",
                 client: { position: 1, kind: "recommended", context: "x" } }),
        result({ run_id: "d3", run_index: 3, location_id: "L1", city: "Dallas", prompt_text: "best florists in Dallas" }),
        result({ run_id: "m1", platform_key: "gemini_memory", label: "Gemini (no search)", location_id: "L1",
                 city: "Dallas", prompt_text: "best florists in Dallas" }),
        result({ run_id: "x1", location_id: "L2", city: "Plano", prompt_text: "best florists in Plano" }),
      ] }],
      tier: "paid", runs_per_prompt: 3, previous_audit_id: "a1", skipped_runs: 0,
      locations: [
        { id: "L1", city: "Dallas", answers: 8, named: 2, recommended: 2, platforms: [], competitors: [] },
        { id: "L2", city: "Plano", answers: 4, named: 0, recommended: 0, platforms: [],
          competitors: [{ name: "Plano Petals", answers: 3 }] },
      ],
      search_comparison: {
        search_on: { answers: 6, named: 2, recommended: 2, platforms: ["Gemini (Google Search)"] },
        search_off: { answers: 6, named: 0, recommended: 0, platforms: ["Gemini (no search)"] },
        competitors_both: ["McShan Florist"], competitors_only_search_on: [],
        competitors_only_search_off: ["Old Closed Florist"],
      },
    };
    let started: { prompts: { text: string }[]; tier?: string } | undefined;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/ai-runs/latest")) return json(404, { detail: "No AI run yet." });
      if (url.endsWith("/ai-prompts")) return json(200, setupBody(true));
      if (url.endsWith("/ai-runs") && init?.method === "POST") {
        started = JSON.parse(init.body as string);
        return json(202, { audit_id: "a2", expected_runs: 12, reused: false, tier: "paid" });
      }
      if (url.endsWith("/api/ai-runs/a2")) return json(200, done);
      return json(404, { detail: "nope" });
    }));

    const user = renderPage();
    await screen.findByLabelText("Question 1");
    expect(screen.getAllByText("Coming soon")).toHaveLength(1); // Copilot only
    await user.click(screen.getByLabelText("Full audit"));
    expect(screen.getByLabelText("Question 2")).toHaveValue("affordable florist in Dallas");
    await user.click(screen.getByRole("button", { name: "Start the full audit" }));

    await screen.findByText("Answers by question");
    expect(started?.tier).toBe("paid");
    expect(started?.prompts).toHaveLength(3);
    expect(screen.getByText("Named in 2 of 3 runs")).toBeInTheDocument();
    expect(screen.getByText("What AI remembers vs what it finds")).toBeInTheDocument();
    expect(screen.getByText(/Old Closed Florist/)).toBeInTheDocument();
    expect(screen.getByText(/most named: Plano Petals/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Plano" }));
    expect(screen.getByText(/best florists in Plano/, { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("Named in 0 of 1 run")).toBeInTheDocument();
  });
});
