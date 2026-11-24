import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { Action, Report } from "./reportApi";
import ReportPage, { groupActions } from "./pages/ReportPage";

function action(over: Partial<Action>): Action {
  return {
    id: "x", rule_key: "x", category: "indexing", priority: "high", title: "Title", why: "Why.", how: ["Step one."],
    effort: "low", confidence: "medium", is_best_practice: false, evidence: [{ kind: "foundation_check" }], link: null,
    status: "not_started", status_changed_at: null, active: true, ...over,
  };
}

const actions: Action[] = [
  action({ id: "a1", rule_key: "foundations:noindex", title: "Remove the 'don't list this page' tag from your pages",
           why: "2 pages tell search engines not to list them.", link: "checks" }),
  action({ id: "a2", rule_key: "citation:dmagazine.com", category: "citation_source", priority: "medium",
           title: "Look into dmagazine.com",
           why: "Pattern we see: dmagazine.com was cited in 2 answers that named McShan Florist but not you." }),
  action({ id: "a3", rule_key: "measure:rerun", category: "measurement", priority: "low",
           title: "Re-run the same questions after your fixes", status: "done" }),
];

const report: Report = {
  business: { id: "b1", name: "Petal Lane Florist", domain: "petallane.example", website_url: "https://www.petallane.example/",
              category: "florist", city: "Dallas", confirmed: true, competitors: ["McShan Florist"] },
  overview: {
    generated_at: "2026-11-24T00:00:00Z", method: "API view", foundations_checked_at: "2026-11-20T12:00:00Z",
    ai_checked_at: "2026-11-20T12:00:30Z", ai_status: "complete", ai_run_in_progress: false, search_checked_at: null,
    platforms: ["Gemini (Google Search)", "Gemini (Google Maps)"], questions: 3, visibility_questions: 2,
    runs_per_question: 1, location: { city: "Dallas" }, skipped_platforms: [],
    limitations: ["API view: answers come from the AI companies' developer APIs."],
    coming_soon: ["Answers as seen in the consumer apps, with screenshots"],
  },
  visibility: {
    available: true, audit_id: "ai1", status: "complete", checked_at: "2026-11-20T12:00:30Z",
    totals: { answers: 4, named: 1, recommended: 1, own_site_cited: 1, errors: 1 },
    platforms: [
      { key: "gemini_search", label: "Gemini (Google Search)", search_enabled: true, answers: 2, named: 1, recommended: 1,
        best_position: 2, own_site_cited: 1, errors: 0, missed_prompts: [], named_instead: [] },
      { key: "gemini_maps", label: "Gemini (Google Maps)", search_enabled: true, answers: 2, named: 0, recommended: 0,
        best_position: null, own_site_cited: 0, errors: 1, missed_prompts: ["best florists in Dallas"], named_instead: [] },
    ],
  },
  competitors: {
    available: true, answers: 4, client: { answers: 1, recommended: 1 },
    others: [{ name: "McShan Florist", answers: 4, platforms: [], known: true, attributes: ["same-day delivery"] }],
  },
  citations: {
    available: true, answers_with_sources: 3, own_site_cited: 1, client_answers_with_sources: 1,
    gaps: [{ domain: "dmagazine.com", type: "publication", answers: 2, competitors: ["McShan Florist"],
             prompts: ["best florists in Dallas"], platforms: ["Gemini (Google Search)"], example_url: null }],
    top_sources: [],
  },
  accuracy: {
    available: true, branded_answers: 1, answers_naming_you: 2,
    wrong: [{ platform: "Gemini (Google Search)", prompt: "what is Petal Lane Florist?",
              facts: { phone: { said: "214-555-9999", confirmed: ["+1 214-555-0142"] } } }],
  },
  foundations: {
    available: true, audit_id: "f1", checked_at: "2026-11-20T12:00:00Z", url: "https://www.petallane.example/",
    counts: { issue: 2, warning: 0, inconclusive: 0, opportunity: 0, not_verified: 1, pass: 2 },
    issues: [{ check_type: "noindex", status: "issue", summary: "This page tells search engines not to list it.",
               fix: null, target: null }],
    blocked_crawlers: [],
  },
  search: {
    available: true, audit_id: "s1", checked_at: "2026-11-20T12:00:00Z", queries: [],
    maps: { checked: 0, found: 0 }, web: { checked: 0, found: 0 }, listings: [], coming_soon: [],
    press: {
      available: true, client_articles: [], category_articles: [], client_sources: [],
      competitor_articles: [{ title: "McShan turns 75", source: "D Magazine", domain: "dmagazine.com", url: null,
                              published: null, competitor: "McShan Florist" }],
      competitor_only_sources: ["dmagazine.com"],
    },
  },
  comparison: {
    available: true, previous_audit_id: "ai0", previous_checked_at: "2026-10-21T12:00:00Z", same_questions: true,
    same_platforms: true,
    totals: { before: { answers: 4, named: 0, recommended: 0, own_site_cited: 0 },
              after: { answers: 4, named: 1, recommended: 1, own_site_cited: 1 }, named_change: 1, small: true },
    platforms: [{ key: "gemini_search", label: "Gemini (Google Search)",
                  before: { answers: 2, named: 0, recommended: 0, own_site_cited: 0 },
                  after: { answers: 2, named: 1, recommended: 1, own_site_cited: 1 }, named_change: 1, small: true }],
    competitors: [],
    note: "Answers vary from run to run. A change of a few answers isn't evidence that anything improved.",
  },
  actions,
  action_counts: { total: 3, high: 1, medium: 1, low: 1, not_started: 2, in_progress: 0, done: 1, dismissed: 0 },
};

describe("groupActions", () => {
  it("groups by priority in order and drops empty groups", () => {
    const groups = groupActions([actions[2], actions[0]]);
    expect(groups.map((g) => [g.priority, g.actions.map((a) => a.id)])).toEqual([["high", ["a1"]], ["low", ["a3"]]]);
  });
});

describe("ReportPage", () => {
  it("shows counts, gaps and accuracy, and saves an action's status", async () => {
    const patches: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      const json = (status: number, data: unknown) => new Response(JSON.stringify(data), { status });
      if (url === "/api/businesses/b1/report") return json(200, report);
      if (init?.method === "PATCH") {
        const body = JSON.parse(init.body as string);
        patches.push({ url, body });
        return json(200, { ...actions[0], status: body.status });
      }
      return json(404, { detail: "nope" });
    }));
    render(
      <MemoryRouter initialEntries={["/b/b1/report"]}>
        <Routes><Route path="/b/:id/report" element={<ReportPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { level: 1, name: "Petal Lane Florist" })).toBeInTheDocument();
    expect(screen.getAllByText("API view").length).toBeGreaterThan(0);
    // Counts, not percentages.
    expect(screen.getByText(/named you · recommended in 1/)).toBeInTheDocument();
    expect(screen.getByText("4 of 4")).toBeInTheDocument(); // McShan Florist's share
    expect(document.body.textContent).not.toMatch(/\d%/);
    expect(screen.getAllByText("dmagazine.com").length).toBe(2); // citation gap and press
    expect(screen.getByText(/A pattern we see, not proof/)).toBeInTheDocument();
    expect(screen.getByText("214-555-9999")).toBeInTheDocument();
    expect(screen.getByText(/Since your last check/)).toBeInTheDocument();
    expect(screen.getAllByText(/\(small\)/).length).toBeGreaterThan(0);
    expect(screen.getByText("We didn't find news articles about you.")).toBeInTheDocument();
    expect(screen.getByText(/· McShan Florist$/)).toBeInTheDocument();

    // Action Center grouped by priority.
    const center = screen.getByRole("region", { name: "Action Center" });
    const headings = within(center).getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(["Do these first (1)", "Next (1)", "When you have time (1)"]);
    expect(screen.getByText("3 actions: 1 high, 1 medium, 1 low")).toBeInTheDocument();

    const user = userEvent.setup();
    const picker = screen.getByLabelText("Status for Remove the 'don't list this page' tag from your pages");
    await user.selectOptions(picker, "in_progress");
    await waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0]).toEqual({ url: "/api/businesses/b1/actions/a1", body: { status: "in_progress" } });
    await waitFor(() => expect(picker).toHaveValue("in_progress"));
  });

  it("shows a plain error when the report can't load", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Business not found." }), { status: 404 })));
    render(
      <MemoryRouter initialEntries={["/b/zz/report"]}>
        <Routes><Route path="/b/:id/report" element={<ReportPage />} /></Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Business not found.");
  });
});
