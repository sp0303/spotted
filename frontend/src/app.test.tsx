import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { BusinessProfile, Check } from "./api";
import ProfilePage, { confirmProblems } from "./pages/ProfilePage";
import { groupChecks } from "./pages/ChecksPage";

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
