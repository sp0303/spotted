import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import SearchPage, { listingLabel } from "./pages/SearchPage";
import type { SearchCheck } from "./searchApi";

const done: SearchCheck = {
  audit_id: "s1", business_id: "b1", status: "complete", started_at: "2026-11-24T00:00:00Z",
  finished_at: "2026-11-24T00:00:40Z", expected_calls: 4, finished_calls: 4,
  location: { city: "Dallas", lat: 32.78, lng: -96.8 }, maps_skipped: null, top_n: 10, cost_usd: 0.0151, note: null,
  summary: {
    checked_at: "2026-11-24T00:00:40Z", queries: [], coming_soon: ["google_rankings", "yelp"],
    press: {
      client_articles: [{ title: "Petal Lane opens a second shop", source: "D Magazine", source_url: "https://www.dmagazine.com",
                          url: "https://news.google.com/rss/articles/a1", published: "2026-11-18T08:00:00+00:00" }],
      category_articles: [{ title: "The best florists in Dallas", source: "CultureMap Dallas", source_url: "https://dallas.culturemap.com",
                            url: null, published: null }],
      competitor_articles: [
        { competitor: "McShan Florist", title: "McShan at 75", source: "D Magazine", source_url: "https://www.dmagazine.com", url: null, published: null },
        { competitor: "McShan Florist", title: "McShan weddings", source: "PaperCity Magazine", source_url: "https://www.papercitymag.com", url: null, published: null },
      ],
      client_sources: ["dmagazine.com"], competitor_only_sources: ["papercitymag.com"],
    },
    listings: [
      { platform: "google_business_profile", status: "found", url: "https://maps.google.com/?cid=2",
        issues: ["Google Maps shows your name as “Petal Lane Flowers”, but your confirmed name is “Petal Lane Florist”."] },
      { platform: "yelp", status: "coming_soon", url: "https://www.yelp.com/search?find_desc=Petal+Lane&find_loc=Dallas", issues: [] },
      { platform: "instagram", status: "found", url: "https://www.instagram.com/petallane", issues: [] },
    ],
  },
  queries: [
    {
      query: "florists in Dallas", intent: "category",
      maps: { status: "done", error: null, client_rank: 2, seconds: 9, search_queries: [], results: [
        { title: "McShan Florist", uri: null, place_id: "p1", position: 1, is_client: false },
        { title: "Petal Lane Flowers", uri: "https://maps.google.com/?cid=2", place_id: "p2", position: 2, is_client: true },
      ] },
      web: { status: "done", error: null, client_rank: null, seconds: 11, search_queries: [], results: [
        { domain: "yelp.com", url: null, title: "Top 10 Florists in Dallas", position: 1, is_client: false, source_type: "directory" },
      ] },
      check_urls: { google: "https://www.google.com/search?q=florists+in+Dallas", bing: "https://www.bing.com/search?q=florists+in+Dallas" },
    },
  ],
  coming_soon: [{ key: "google_rankings", label: "Your real Google ranking", needs: "a search-results data provider",
                  check_url: "https://www.google.com/search?q=florists+in+Dallas" }],
};

describe("SearchPage", () => {
  it("starts a check and shows Maps ranks, web sources and listings", async () => {
    let posted = false;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      const json = (status: number, data: unknown) => new Response(JSON.stringify(data), { status });
      if (url === "/api/businesses/b1/search" && init?.method === "POST") {
        posted = true;
        return json(202, { audit_id: "s1", expected_calls: 4 });
      }
      if (url === "/api/businesses/b1/search") return posted ? json(200, done) : json(404, { detail: "No search check yet." });
      return json(404, { detail: "nope" });
    }));

    render(
      <MemoryRouter initialEntries={["/b/b1/search"]}>
        <Routes><Route path="/b/:id/search" element={<SearchPage />} /></Routes>
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Check search and Maps" }));

    expect(await screen.findByText("You're #2")).toBeInTheDocument();
    expect(posted).toBe(true);
    expect(screen.getByText("Your website isn't in the top 10")).toBeInTheDocument();
    expect(screen.getByText("Petal Lane Flowers").closest("li")).toHaveClass("is-client");
    expect(screen.getByText("yelp.com")).toBeInTheDocument();
    expect(screen.getByText(/Seen through Gemini, not your exact ranking/)).toBeInTheDocument();

    const listings = screen.getByRole("heading", { name: "Business listings" }).closest("section")!;
    const gbp = within(listings).getByText("Google Business Profile").closest("li")!;
    expect(within(gbp).getByText("Found")).toBeInTheDocument();
    expect(within(gbp).getByText(/shows your name as/)).toBeInTheDocument();
    const yelp = within(listings).getByText("Yelp").closest("li")!;
    expect(within(yelp).getByText("Coming soon")).toBeInTheDocument();
    expect(within(yelp).getByRole("link", { name: "Check by hand" })).toHaveAttribute(
      "href", "https://www.yelp.com/search?find_desc=Petal+Lane&find_loc=Dallas");
    expect(screen.getByRole("link", { name: "Next: your report →" })).toHaveAttribute("href", "/b/b1/report");
    expect(screen.getByText(/cost \$0\.015/)).toBeInTheDocument();

    const news = screen.getByRole("heading", { name: /In the news/ }).closest("section")!;
    expect(within(news).getByText("Google News")).toBeInTheDocument();
    expect(within(news).getByRole("link", { name: "Petal Lane opens a second shop" })).toBeInTheDocument();
    expect(within(news).getByText("D Magazine · Nov 18, 2026")).toBeInTheDocument();
    const pubs = within(news).getByText("Publications that cover your competitors but not you").nextElementSibling!;
    expect(within(pubs as HTMLElement).getByText("PaperCity Magazine")).toBeInTheDocument();
    expect(within(pubs as HTMLElement).queryByText("D Magazine")).toBeNull();
  });

  it("labels listing platforms", () => {
    expect(listingLabel("bing_places")).toBe("Bing Places");
    expect(listingLabel("some_new_site")).toBe("Some new site");
  });
});
