import asyncio
import time

from spotted import api, routes_search
from spotted.models import BusinessProfile, Fact, Location, Service, SocialProfile
from spotted.platforms import Answer, PlatformError
from spotted.search import (_business, build_queries, check_url, final_status, listings_from, news_queries,
                            parse_news_rss, press_summary, read_maps, read_web, run_all, run_news, summarize)


def profile(**kw) -> BusinessProfile:
    base = dict(
        website_url="https://www.petallane.example/", domain="petallane.example",
        name=Fact(value="Petal Lane Florist", origin="confirmed"),
        aliases=[Fact(value="Petal Lane", origin="confirmed")],
        category=Fact(value="Florist", origin="confirmed"),
        services=[Service(value="Same-day delivery", origin="confirmed"),
                  Service(value="Wedding flowers", origin="confirmed")],
        locations=[Location(address="1200 Elm St", city="Dallas", region="TX", country_code="US",
                            lat=32.78, lng=-96.8, origin="confirmed")],
        social_profiles=[SocialProfile(platform="instagram", url="https://www.instagram.com/petallane"),
                         SocialProfile(platform="facebook", url="https://facebook.com/petallane")],
    )
    base.update(kw)
    return BusinessProfile(**base)


def business(p=None):
    return _business(p or profile(), "Dallas")


# ---------- queries ----------

def test_build_queries_category_services_then_branded():
    qs = build_queries(profile())
    assert [q["text"] for q in qs] == ["florists in Dallas", "same-day delivery florist in Dallas",
                                       "wedding flowers in Dallas", "Petal Lane Florist Dallas"]
    assert [q["intent"] for q in qs] == ["category", "service", "service", "branded"]


def test_build_queries_caps_at_five_and_handles_no_city():
    many = [Service(value=v, origin="confirmed") for v in ("Weddings", "Sympathy", "Events", "Plants", "Gifts")]
    qs = build_queries(profile(services=many))
    assert len(qs) == 5 and qs[-1]["intent"] == "branded"
    bare = build_queries(profile(locations=[], category=None, services=[]))
    assert bare == [{"text": "Petal Lane Florist", "intent": "branded"}]


# ---------- reading answers ----------

def test_read_maps_orders_by_answer_and_finds_client():
    ans = Answer(text="1. McShan Florist\n2. Petal Lane Flowers\n3. Bloom Room", maps_places=[
        {"title": "Bloom Room", "uri": "https://maps.google.com/?cid=3", "place_id": "p3"},
        {"title": "McShan Florist", "uri": "https://maps.google.com/?cid=1", "place_id": "p1"},
        {"title": "Petal Lane Flowers - Google Maps", "uri": "https://maps.google.com/?cid=2", "place_id": "p2"},
        {"title": "McShan Florist", "uri": "https://maps.google.com/?cid=1", "place_id": "p1"},  # duplicate
    ])
    places, rank = read_maps(ans, business())
    assert [p["title"] for p in places] == ["McShan Florist", "Petal Lane Flowers", "Bloom Room"]
    assert rank == 2 and places[1]["is_client"]


def test_read_maps_does_not_match_a_different_shop():
    ans = Answer(text="", maps_places=[{"title": "Lane Florist", "uri": None, "place_id": None},
                                       {"title": "Dallas Florist", "uri": None, "place_id": None}])
    assert read_maps(ans, business())[1] is None


def test_read_web_finds_client_domain_and_titles():
    ans = Answer(text="yelp.com - Top 10 Florists in Dallas\npetallane.example - Petal Lane Florist | Dallas",
                 sources=[{"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/a", "title": "yelp.com"},
                          {"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/b",
                           "title": "www.petallane.example"},
                          {"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/c", "title": "yelp.com"}])
    sources, rank = read_web(ans, business())
    assert [(s["domain"], s["title"]) for s in sources] == [
        ("yelp.com", "Top 10 Florists in Dallas"), ("petallane.example", "Petal Lane Florist | Dallas")]
    assert rank == 2 and sources[0]["source_type"] == "directory"


# ---------- listings ----------

def audit_with(maps_results, status="complete", maps_skipped=None):
    p = profile()
    qs = build_queries(p)
    return {"_id": "a", "business_id": "b", "status": status, "started_at": None, "finished_at": None,
            "config": {"queries": qs, "business": business(p), "maps_skipped": maps_skipped,
                       "coming_soon": ["google_rankings", "bing_rankings", "apple_business_connect", "bing_places", "yelp"]},
            "results": maps_results}


def maps_result(i, intent, places, status="done"):
    return {"query_index": i, "query": f"q{i}", "intent": intent, "view": "maps", "status": status,
            "client_rank": next((p["position"] for p in places if p["is_client"]), None), "places": places}


def place(title, pos, client=False):
    return {"title": title, "uri": f"https://maps.google.com/?cid={pos}", "position": pos, "is_client": client}


def by_platform(listings):
    return {x["platform"]: x for x in listings}


def test_gbp_found_from_branded_maps_and_flags_a_different_name():
    a = audit_with([maps_result(0, "category", [place("McShan Florist", 1)]),
                    maps_result(3, "branded", [place("Petal Lane Flowers & Gifts", 1, True)])])
    ls = by_platform(listings_from(a))
    gbp = ls["google_business_profile"]
    assert gbp["status"] == "found" and gbp["url"] == "https://maps.google.com/?cid=1"
    assert "Petal Lane Flowers & Gifts" in gbp["issues"][0]
    assert ls["instagram"] == {"platform": "instagram", "status": "found",
                               "url": "https://www.instagram.com/petallane", "issues": []}
    for key in ("apple_business_connect", "bing_places", "yelp"):
        assert ls[key]["status"] == "coming_soon" and ls[key]["url"].startswith("https://")
    assert ls["yelp"]["url"] == "https://www.yelp.com/search?find_desc=Petal+Lane+Florist&find_loc=Dallas"


def test_gbp_same_name_has_no_issue():
    a = audit_with([maps_result(3, "branded", [place("Petal Lane Florist", 1, True)])])
    assert by_platform(listings_from(a))["google_business_profile"]["issues"] == []


def test_gbp_not_found_unknown_and_skipped():
    a = audit_with([maps_result(3, "branded", [place("Lane Florist", 1)])])
    gbp = by_platform(listings_from(a))["google_business_profile"]
    assert gbp["status"] == "not_found" and gbp["url"].startswith("https://www.google.com/maps/search/")
    failed = audit_with([maps_result(3, "branded", [], status="error")])
    assert by_platform(listings_from(failed))["google_business_profile"]["status"] == "unknown"
    skipped = audit_with([], maps_skipped="No map position.")
    assert by_platform(listings_from(skipped))["google_business_profile"]["status"] == "unknown"
    running = audit_with([], status="running")
    assert by_platform(listings_from(running))["google_business_profile"] == {
        "platform": "google_business_profile", "status": "unknown",
        "url": check_url("google_business_profile", "Petal Lane Florist", "Dallas"), "issues": []}


def test_summary_shape():
    a = audit_with([maps_result(0, "category", [place("McShan Florist", 1)])])
    a["results"].append({"query_index": 0, "view": "web", "status": "done", "client_rank": None,
                         "sources": [{"domain": "yelp.com", "title": None, "url": "u", "position": 1,
                                      "is_client": False, "source_type": "directory"}]})
    s = summarize(a)
    assert set(s) == {"checked_at", "queries", "listings", "coming_soon"}  # no "press" unless news ran
    assert s["queries"][0] == {"query": "florists in Dallas",
                               "maps": {"client_rank": None, "results": ["McShan Florist"]},
                               "web": {"client_rank": None, "results": [{"domain": "yelp.com", "title": None}]}}
    assert s["queries"][1]["maps"] == {"client_rank": None, "results": []}
    assert all(set(x) == {"platform", "status", "url", "issues"} for x in s["listings"])
    assert final_status([{"status": "done"}, {"status": "error"}]) == "partial"


# ---------- running (fake Gemini) ----------

class FakeGemini:
    """Maps puts the client second for the category search and first for its name; Search cites its site once."""

    def __init__(self, fail_web=False):
        self.calls = []
        self.fail_web = fail_web

    async def answer(self, platform, prompt, lat, lng):
        self.calls.append((platform.key, platform.grounding, prompt, lat, lng))
        if platform.grounding == "google_maps":
            names = ["Petal Lane Florist"] if "Petal Lane" in prompt else ["McShan Florist", "Petal Lane Flowers"]
            return Answer(text="\n".join(names), model="fake", tokens_in=100, tokens_out=50, cost_usd=0.001,
                          latency_ms=900, maps_places=[{"title": n, "uri": f"https://maps.google.com/?q={i}",
                                                        "place_id": n} for i, n in enumerate(names)])
        if self.fail_web:
            raise PlatformError("Gemini error 429: quota")
        srcs = [{"url": "https://vertexaisearch.cloud.google.com/r/1", "title": "yelp.com"}]
        if "florists in" in prompt:
            srcs.append({"url": "https://vertexaisearch.cloud.google.com/r/2", "title": "petallane.example"})
        return Answer(text="yelp.com - Best florists", model="fake", tokens_in=80, tokens_out=40, cost_usd=0.001,
                      latency_ms=1100, sources=srcs)


def test_run_all_separates_maps_and_search_and_survives_errors():
    a = audit_with([])
    a["config"]["location"] = {"city": "Dallas", "lat": 32.78, "lng": -96.8}
    fake = FakeGemini(fail_web=True)
    results = asyncio.run(run_all(fake, a))
    assert len(results) == 8
    assert {(k, g, lat is not None) for k, g, _, lat, _ in fake.calls} == {
        ("gemini_maps", "google_maps", True), ("gemini_search", "google_search", False)}
    assert {r["status"] for r in results if r["view"] == "web"} == {"error"}
    assert final_status(results) == "partial"


def test_search_api_post_then_get(client, florist_site, db, test_prefix):
    fake = FakeGemini()
    news = FakeNews()
    api.app.dependency_overrides[routes_search.get_search_answerer] = lambda: fake
    api.app.dependency_overrides[routes_search.get_news_fetcher] = lambda: news
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    assert client.get(f"/api/businesses/{bid}/search").status_code == 404
    assert client.post(f"/api/businesses/{bid}/search").status_code == 409  # not confirmed yet

    p = client.get(f"/api/businesses/{bid}").json()["profile"]
    p["locations"] = [dict(loc, lat=32.78, lng=-96.8) for loc in p["locations"] if loc["city"] == "Dallas"]
    assert client.put(f"/api/businesses/{bid}/profile", json=p).status_code == 200

    resp = client.post(f"/api/businesses/{bid}/search")
    assert resp.status_code == 202, resp.text
    assert resp.json()["expected_calls"] == 2 * len(build_queries(BusinessProfile.model_validate(p)))
    for _ in range(300):  # background work over a remote Mongo can take a few seconds
        got = client.get(f"/api/businesses/{bid}/search").json()
        if got["status"] != "running":
            break
        time.sleep(0.1)
    assert got["status"] == "complete" and got["finished_calls"] == got["expected_calls"]
    s = got["summary"]
    first = s["queries"][0]
    assert first["query"] == "florists in Dallas"
    assert first["maps"] == {"client_rank": 2, "results": ["McShan Florist", "Petal Lane Flowers"]}
    assert first["web"]["client_rank"] == 2
    gbp = next(x for x in s["listings"] if x["platform"] == "google_business_profile")
    assert gbp["status"] == "found" and gbp["url"].startswith("https://maps.google.com/")
    assert {x["platform"] for x in s["listings"] if x["status"] == "found"} >= {"instagram", "facebook"}
    assert "yelp" in s["coming_soon"] and got["coming_soon"][0]["check_url"].startswith("https://www.google.com/")
    assert got["cost_usd"] > 0 and got["queries"][0]["maps"]["results"][0]["title"] == "McShan Florist"

    doc = db[test_prefix + "audits"].find_one({"_id": got["audit_id"]})
    assert doc["config"]["kind"] == "search_listings" and doc["tier"] == "free"
    assert doc["summary"]["queries"] == s["queries"] and doc["tokens_in"] > 0
    assert news.queries[0].startswith('"Petal Lane')
    assert s["press"]["client_articles"][0]["title"] == "Petal Lane opens"
    assert s["press"]["client_sources"] == ["dmagazine.com"] and got["news"]["status"] == "done"


# ---------- Google News ----------

RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>x</title>
<item><title>Dallas's best florists - D Magazine</title><link>https://news.google.com/rss/articles/a1</link>
<pubDate>Tue, 18 Nov 2026 08:00:00 GMT</pubDate><source url="https://www.dmagazine.com">D Magazine</source></item>
<item><title>Petal Lane opens a second shop - PaperCity Magazine</title><link>https://news.google.com/rss/articles/a2</link>
<pubDate>bad date</pubDate><source url="https://www.papercitymag.com">PaperCity Magazine</source></item>
</channel></rss>"""


def test_parse_news_rss_strips_publication_and_reads_dates():
    items = parse_news_rss(RSS)
    assert items[0] == {"title": "Dallas's best florists", "source": "D Magazine", "source_url": "https://www.dmagazine.com",
                        "url": "https://news.google.com/rss/articles/a1", "published": "2026-11-18T08:00:00+00:00"}
    assert items[1]["published"] is None and items[1]["title"] == "Petal Lane opens a second shop"
    assert parse_news_rss("not xml") == [] and len(parse_news_rss(RSS, limit=1)) == 1


def test_news_queries_quote_names():
    b = business(profile(suggested_competitors=[Fact(value=n, origin="confirmed") for n in ("A", "B", "C", "D")]))
    qs = news_queries(b, "florist")
    assert [q["query"] for q in qs] == ['"Petal Lane Florist" Dallas', "best florists Dallas",
                                       '"A" Dallas', '"B" Dallas', '"C" Dallas']


def a_(title, src):
    return {"title": title, "source": src, "source_url": f"https://www.{src}.com", "url": "u", "published": None}


def test_press_summary_finds_competitor_only_publications():
    press = [{"kind": "client", "query": "q", "items": [a_("Petal Lane wins", "dmagazine")]},
             {"kind": "category", "query": "q", "items": [a_("Best florists", "culturemap")]},
             {"kind": "competitor", "competitor": "McShan Florist", "query": "q",
              "items": [a_("McShan at 75", "dmagazine"), a_("McShan weddings", "papercitymag")]}]
    s = press_summary(press)
    assert s["client_sources"] == ["dmagazine.com"]
    assert s["competitor_only_sources"] == ["papercitymag.com"]
    assert s["competitor_articles"][0]["competitor"] == "McShan Florist"
    assert set(s["category_articles"][0]) == {"title", "source", "source_url", "url", "published"}


class FakeNews:
    def __init__(self, fail=False):
        self.queries = []
        self.fail = fail

    async def search(self, query):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("offline")
        if query.startswith('"Petal Lane'):
            return [a_("Petal Lane opens", "dmagazine")]
        return [a_(f"About {query}", "culturemap")]


def test_run_news_survives_errors():
    out = asyncio.run(run_news(FakeNews(fail=True), [{"kind": "client", "query": "x"}]))
    assert out[0]["status"] == "error" and out[0]["items"] == []
