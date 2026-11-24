import pytest

from spotted import api


def test_extract_then_confirm(client, florist_site, db, test_prefix):
    resp = client.post("/api/profiles", json={"url": "petallane.example"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["confirmed"] is False
    bid = body["business_id"]

    got = client.get(f"/api/businesses/{bid}").json()
    assert got["profile"]["name"]["value"] == "Petal Lane Florist"

    # Owner edits: drops the guessed Fort Worth area and an inferred service, adds a competitor.
    profile = got["profile"]
    profile["locations"] = [loc for loc in profile["locations"] if loc["city"] != "Fort Worth"]
    profile["services"] = [s for s in profile["services"] if s["value"] != "Corporate events"]
    profile["suggested_competitors"].append({"value": "Bloom Room", "origin": "inferred"})
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 200, resp.text
    confirmed = resp.json()
    assert confirmed["confirmed"] is True
    assert confirmed["profile"]["name"]["origin"] == "confirmed"
    assert confirmed["profile"]["services"][0]["source_url"]  # where it came from is kept
    assert confirmed["profile"]["warnings"] == []

    doc = db[test_prefix + "businesses"].find_one({"_id": bid})
    assert doc["name"] == "Petal Lane Florist" and doc["category"] == "florist"
    assert doc["phones"] == ["+1 214-555-0142"]
    assert doc["field_origins"]["name"] == "confirmed" and doc["profile_raw"] and doc["confirmed_at"] is not None
    locs = sorted((loc["city"], loc["is_physical"], loc["country_code"], loc["origin"]) for loc in doc["locations"])
    assert locs == [("Dallas", True, "US", "confirmed"), ("Plano", False, "US", "confirmed")]
    assert len(doc["services"]) == 2
    assert sorted(c["name"] for c in doc["competitors"]) == ["Bloom Room", "Dr Delphinium", "McShan Florist"]
    assert doc["aliases"] == ["Petal Lane"]

    # Confirming again replaces the embedded lists rather than duplicating them.
    assert client.put(f"/api/businesses/{bid}/profile", json=confirmed["profile"]).status_code == 200
    doc = db[test_prefix + "businesses"].find_one({"_id": bid})
    assert len(doc["locations"]) == 2 and len(doc["competitors"]) == 3


def test_confirm_requires_country_and_target(client, florist_site):
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    profile = client.get(f"/api/businesses/{bid}").json()["profile"]
    profile["locations"][0]["country_code"] = None
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 422 and "country" in resp.json()["detail"]
    profile["locations"] = []
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 422 and "customers to find you" in resp.json()["detail"]


def test_bad_urls_get_plain_errors(client):
    resp = client.post("/api/profiles", json={"url": "localhost"})
    assert resp.status_code == 422 and "website address" in resp.json()["detail"]
    resp = client.post("/api/profiles", json={"url": "http://127.0.0.1/"})
    assert resp.status_code == 422 and "isn't a public website" in resp.json()["detail"]


def test_unknown_business_is_404(client):
    assert client.get("/api/businesses/00000000-0000-0000-0000-000000000000").status_code == 404


def test_foundations_endpoint(client, florist_site, monkeypatch):
    from spotted import foundations

    monkeypatch.setattr(foundations, "default_renderer", lambda: None)
    florist_site.get("http://www.petallane.example/").respond(301, headers={"location": "https://www.petallane.example/"})
    florist_site.route(host="www.petallane.example").respond(404, headers={"content-type": "text/html"})
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    assert client.get(f"/api/businesses/{bid}/foundations").status_code == 404

    resp = client.post(f"/api/businesses/{bid}/foundations")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    types = {c["check_type"] for c in body["checks"]}
    assert {"http_status", "robots_txt", "sitemap", "cdn_waf", "js_render", "noindex", "webmcp"} <= types
    assert len(body["crawlers"]) == 16 and body["crawlers"][0]["token"] == "Googlebot"
    assert body["purpose_labels"]["search"].startswith("Search")
    assert client.get(f"/api/businesses/{bid}/foundations").json()["audit_id"] == body["audit_id"]


class FakeAnswerer:
    """Stands in for the AI platforms: names the client only on Gemini search, and fails Perplexity."""

    def __init__(self):
        self.calls = []

    async def answer(self, platform, prompt, lat, lng, where=None):
        from spotted.platforms import Answer, PlatformError

        self.calls.append((platform.key, prompt, lat, lng))
        if platform.key == "perplexity":
            raise PlatformError("Out of OpenRouter credit.")
        text = "Try McShan Florist or Petal Lane Florist." if platform.key == "gemini_search" else "Try McShan Florist."
        return Answer(text=text, model="fake", tokens_in=10, tokens_out=20, cost_usd=0.001, latency_ms=1200,
                      sources=[{"url": "https://www.yelp.com/x", "title": "Yelp"}])


class FakeReader:
    async def read(self, answer, profile):
        from spotted.analysis import AnswerReading, NamedBusiness

        names = [n for n in ("McShan Florist", "Petal Lane Florist") if n in answer]
        return AnswerReading(businesses=[NamedBusiness(name=n, kind="recommended", context=n) for n in names]), 5, 5


def test_ai_run_end_to_end(client, florist_site, monkeypatch):
    import time

    from spotted import platforms

    monkeypatch.setattr(platforms, "available_platforms",
                        lambda: ["gemini_search", "gemini_maps", "perplexity"])
    monkeypatch.setattr(api, "available_platforms", platforms.available_platforms)
    fake = FakeAnswerer()
    api.app.dependency_overrides[api.get_answerer] = lambda: fake
    api.app.dependency_overrides[api.get_reader] = lambda: FakeReader()

    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    assert client.get(f"/api/businesses/{bid}/ai-prompts").status_code == 409  # not confirmed yet
    profile = client.get(f"/api/businesses/{bid}").json()["profile"]
    profile["locations"] = [loc for loc in profile["locations"] if loc["city"] == "Dallas"]
    assert client.put(f"/api/businesses/{bid}/profile", json=profile).status_code == 200

    got = client.get(f"/api/businesses/{bid}/ai-prompts").json()
    assert got["prompts"][0]["text"] == "best florists in Dallas"
    prompts = got["prompts"][:2]
    resp = client.post(f"/api/businesses/{bid}/ai-runs",
                       json={"prompts": prompts, "platforms": ["gemini_search", "gemini_maps", "perplexity"]})
    assert resp.status_code == 202, resp.text
    audit_id = resp.json()["audit_id"]

    for _ in range(300):  # background work over a remote Mongo can take a few seconds
        run = client.get(f"/api/ai-runs/{audit_id}").json()
        if run["status"] != "running":
            break
        time.sleep(0.1)
    assert run["status"] == "partial"  # Perplexity failed, the rest finished
    assert run["finished_runs"] == run["expected_runs"]
    assert run["expected_runs"] == 6 and run["skipped_platforms"] == []
    # Maps grounding gets the location's map position; the others rely on the city in the prompt.
    assert {(k, lat is not None) for k, _, lat, _ in fake.calls} == {
        ("gemini_search", False), ("gemini_maps", True), ("perplexity", False)}
    by = {p["key"]: p for p in run["platforms"]}
    assert (by["gemini_search"]["answers"], by["gemini_search"]["named"]) == (2, 2)
    assert (by["gemini_maps"]["answers"], by["gemini_maps"]["named"]) == (2, 0)
    assert by["perplexity"]["errors"] == 2
    assert run["competitors"][0]["name"] == "McShan Florist" and run["competitors"][0]["answers"] == 4
    assert run["sources"][0] == {"domain": "yelp.com", "answers": 4, "type": "directory"}
    assert run["cost_usd"] > 0 and run["first_result_seconds"] is not None
    assert client.get(f"/api/businesses/{bid}/ai-runs/latest").json()["audit_id"] == audit_id
    assert all("Dallas" in p for _, p, _, _ in fake.calls)
