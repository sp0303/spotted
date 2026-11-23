"""Full ("paid") audit, free-run limits and the direct OpenAI runner (build steps 3 and 7). No live AI calls."""

import json
import time

import httpx
import pytest
import respx

from spotted.airun import plan_jobs, summarize
from spotted.models import Fact, Location
from spotted.openai_runner import OPENAI_RESPONSES_URL, openai_answer, parse_response
from spotted.platforms import PLATFORMS, location_method
from spotted.prompts import BRANDED_INTENTS, PAID_BRANDED_MAX, PAID_CORE_MAX, for_location, full_audit_prompts
from test_airun import profile


# ---------- prompts ----------

def test_full_audit_prompts_cover_the_taxonomy_within_the_caps():
    p = profile(target_customer=Fact(value="couples planning a wedding", origin="confirmed"),
                locations=[Location(address="1200 Elm St", city="Dallas", region="TX", postal_code="75201",
                                    country_code="US", lat=32.78, lng=-96.8, origin="confirmed")])
    out = full_audit_prompts(p)
    core = [x for x in out if x.intent not in BRANDED_INTENTS]
    branded = [x for x in out if x.intent in BRANDED_INTENTS]
    assert 15 <= len(core) <= PAID_CORE_MAX and 1 <= len(branded) <= PAID_BRANDED_MAX
    assert {x.intent for x in core} == {"discovery", "service", "problem", "budget", "attribute", "neighborhood",
                                        "comparison"}
    assert {x.intent for x in branded} == {"branded", "accuracy"}
    assert out[-1].intent in BRANDED_INTENTS and out[0].text == "best florists in Dallas"
    texts = [x.text.lower() for x in out]
    assert len(texts) == len(set(texts))
    assert all("dallas" in t or "75201" in t for t in texts)
    assert not any("petal lane" in x.text.lower() for x in core)  # visibility prompts never name the client


def test_full_audit_prompts_keep_the_cap_with_many_services():
    from spotted.models import Service

    p = profile(services=[Service(value=f"service {i}", origin="confirmed") for i in range(12)],
                differentiators=[Fact(value=f"thing {i}", origin="confirmed") for i in range(5)])
    out = full_audit_prompts(p)
    assert sum(1 for x in out if x.intent not in BRANDED_INTENTS) == PAID_CORE_MAX
    assert sum(1 for x in out if x.intent in BRANDED_INTENTS) <= PAID_BRANDED_MAX


def test_for_location_swaps_city_and_postcode():
    dallas = {"city": "Dallas", "postal_code": "75201"}
    plano = {"city": "Plano", "postal_code": "75024"}
    assert for_location("best florists in Dallas", dallas, plano) == "best florists in Plano"
    assert for_location("best florist near 75201", dallas, plano) == "best florist near 75024"
    assert for_location("who sells peonies?", dallas, plano) == "who sells peonies in Plano?"
    assert for_location("best florists in Dallas", dallas, dallas) == "best florists in Dallas"


# ---------- planning and summary ----------

def _paid_audit(runs_list=None):
    return {
        "_id": "a2", "business_id": "b1", "status": "complete", "tier": "paid", "cost_usd": 0.1,
        "previous_audit_id": "a1", "methodology_version": "ai-run-2",
        "config": {"platforms": ["gemini_search", "gemini_maps", "gemini_memory"], "runs": 3, "branded_runs": 1,
                   "location": {"city": "Dallas"}, "skipped": {},
                   "locations": [{"id": "L1", "city": "Dallas", "lat": 32.7, "lng": -96.8},
                                 {"id": "L2", "city": "Plano", "lat": 33.0, "lng": -96.7}]},
        "prompts": [{"id": "p1", "text": "best florists in Dallas", "intent": "discovery"},
                    {"id": "p2", "text": "affordable florist in Dallas", "intent": "budget"},
                    {"id": "p3", "text": "what is Petal Lane?", "intent": "branded"}],
        "runs": runs_list or [], "expected_runs": 39,
    }


def test_plan_jobs_repeats_core_prompts_per_location_and_branded_once():
    jobs = plan_jobs(_paid_audit())
    assert len(jobs) == 2 * 3 * 2 * 3 + 1 * 1 * 1 * 3
    branded = [j for j in jobs if j[0]["id"] == "p3"]
    assert {(j[2], j[3]["id"]) for j in branded} == {(1, "L1")}
    assert [j[2] for j in jobs[:12]] == [1] * 12  # run 1 of everything first


def _run(rid, pid, key, idx, loc, client=False, comps=("McShan Florist",), status="done"):
    ms = [{"entity_name": c, "normalized": c.lower(), "is_client": False, "competitor": None, "position": i + 1,
           "kind": "recommended", "context": "", "facts_wrong": {}} for i, c in enumerate(comps)]
    if client:
        ms.append({"entity_name": "Petal Lane", "normalized": "petal lane", "is_client": True, "competitor": None,
                   "position": len(ms) + 1, "kind": "recommended", "context": "x", "facts_wrong": {}})
    return {"id": rid, "prompt_id": pid, "platform_key": key, "run_index": idx, "location_id": loc,
            "status": status, "error": None if status == "done" else "Budget", "latency_ms": 1000, "cost_usd": 0.001,
            "response": {"text": "..."}, "mentions": ms if status == "done" else [], "citations": []}


def test_summary_counts_frequency_search_contrast_and_locations():
    runs = [
        _run("r1", "p1", "gemini_search", 1, "L1", client=True),
        _run("r2", "p1", "gemini_search", 2, "L1", client=True),
        _run("r3", "p1", "gemini_search", 3, "L1"),
        _run("r4", "p1", "gemini_memory", 1, "L1", comps=("Old Closed Florist",)),
        _run("r5", "p1", "gemini_memory", 2, "L1", comps=("Old Closed Florist", "McShan Florist")),
        _run("r6", "p1", "gemini_search", 1, "L2", comps=("Plano Petals",)),
        _run("r7", "p1", "gemini_search", 2, "L2", status="skipped"),
    ]
    s = summarize(_paid_audit(runs))
    q = s["prompts"][0]
    f = {(x["platform_key"], x["location_id"]): x for x in q["frequency"]}
    assert (f[("gemini_search", "L1")]["named"], f[("gemini_search", "L1")]["runs"]) == (2, 3)
    assert f[("gemini_search", "L2")]["done"] == 1 and f[("gemini_search", "L2")]["runs"] == 2
    assert {r["city"] for r in q["results"]} == {"Dallas", "Plano"}
    g = {p["key"]: p for p in s["platforms"]}
    assert (g["gemini_search"]["answers"], g["gemini_search"]["named"]) == (4, 2)
    assert (g["gemini_search"]["prompts_asked"], g["gemini_search"]["prompts_named"]) == (2, 1)
    assert g["gemini_search"]["skipped"] == 1 and g["gemini_search"]["errors"] == 0
    sc = s["search_comparison"]
    assert sc["search_on"]["answers"] == 3 and sc["search_on"]["named"] == 2  # L1 only: asked both ways there
    assert sc["search_off"] == {"answers": 2, "named": 0, "recommended": 0, "platforms": ["Gemini (no search)"]}
    assert sc["competitors_both"] == ["McShan Florist"] and sc["competitors_only_search_off"] == ["Old Closed Florist"]
    locs = {x["city"]: x for x in s["locations"]}
    assert (locs["Dallas"]["answers"], locs["Dallas"]["named"]) == (5, 2)
    assert locs["Plano"]["competitors"] == [{"name": "Plano Petals", "answers": 1}]
    assert s["skipped_runs"] == 1 and s["previous_audit_id"] == "a1" and s["runs_per_prompt"] == 3


# ---------- OpenAI Responses runner ----------

OPENAI_REPLY = {
    "id": "resp_1", "model": "gpt-5-mini-2026", "status": "completed",
    "output": [
        {"type": "web_search_call", "id": "ws_1", "status": "completed",
         "action": {"type": "search", "query": "best florists Dallas",
                    "sources": [{"type": "url", "url": "https://www.dmagazine.com/florists"},
                                {"type": "url", "url": "https://www.yelp.com/dallas-florists"}]}},
        {"type": "reasoning", "id": "rs_1", "summary": []},
        {"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": "Try McShan Florist or Petal Lane Florist.",
             "annotations": [{"type": "url_citation", "start_index": 4, "end_index": 18,
                              "url": "https://www.dmagazine.com/florists", "title": "Best florists"},
                             {"type": "url_citation", "url": "https://petallane.example/", "title": "Petal Lane"}]}]},
    ],
    "usage": {"input_tokens": 1000, "output_tokens": 500, "output_tokens_details": {"reasoning_tokens": 100}},
}


async def test_openai_runner_sends_location_and_reads_citations(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    with respx.mock() as mock:
        route = mock.post(OPENAI_RESPONSES_URL).respond(200, json=OPENAI_REPLY)
        async with httpx.AsyncClient() as http:
            ans = await openai_answer(http, "best florists in Dallas",
                                      {"city": "Dallas", "region": "TX", "country_code": "US"})
    sent = json.loads(route.calls[0].request.content)
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-test"
    assert sent["tools"] == [{"type": "web_search", "user_location": {"type": "approximate", "country": "US",
                                                                      "city": "Dallas", "region": "TX"}}]
    assert sent["include"] == ["web_search_call.action.sources"] and sent["input"] == "best florists in Dallas"
    assert ans.text == "Try McShan Florist or Petal Lane Florist."
    assert [s["url"] for s in ans.sources] == ["https://www.dmagazine.com/florists", "https://petallane.example/",
                                              "https://www.yelp.com/dallas-florists"]
    assert ans.search_queries == ["best florists Dallas"] and ans.model == "gpt-5-mini-2026"
    # 1000 in at $0.25/M + 500 out at $2/M + one search at $10/1k
    assert ans.cost_usd == pytest.approx(0.00025 + 0.001 + 0.01)


async def test_openai_runner_errors_and_odd_shapes(monkeypatch):
    from spotted.platforms import PlatformError

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with respx.mock() as mock:
        mock.post(OPENAI_RESPONSES_URL).respond(429, json={"error": {"message": "Rate limit reached"}})
        async with httpx.AsyncClient() as http:
            with pytest.raises(PlatformError, match="OpenAI 429: Rate limit"):
                await openai_answer(http, "x", None)
    odd = parse_response({"output": [None, {"type": "message", "content": None}], "output_text": "hi"}, "m")
    assert (odd.text, odd.sources, odd.tokens_in, odd.cost_usd) == ("hi", [], 0, 0.0)


def test_chatgpt_location_method_follows_the_key(monkeypatch):
    from spotted import platforms

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert location_method(PLATFORMS["chatgpt"]) == "prompt_only"
    assert "chatgpt" in {x["key"] for x in platforms.coming_soon()}
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert location_method(PLATFORMS["chatgpt"]) == "api_location"
    assert "chatgpt" in platforms.available_platforms()
    assert "chatgpt" not in {x["key"] for x in platforms.coming_soon()}
    copilot = next(x for x in platforms.coming_soon() if x["key"] == "copilot")
    assert "Azure grounding with Bing" in copilot["note"]


# ---------- API (MongoDB) ----------

class Answerer:
    def __init__(self):
        self.calls = []

    async def answer(self, platform, prompt, lat, lng, where=None):
        from spotted.platforms import Answer

        self.calls.append({"key": platform.key, "prompt": prompt, "lat": lat, "where": where})
        named = platform.search_enabled and "Plano" not in prompt
        text = "Try McShan Florist or Petal Lane Florist." if named else "Try McShan Florist."
        return Answer(text=text, model="fake", tokens_in=10, tokens_out=20, cost_usd=0.001, latency_ms=50,
                      sources=[{"url": "https://www.yelp.com/x", "title": "Yelp"}])


class Reader:
    async def read(self, answer, profile):
        from spotted.analysis import AnswerReading, NamedBusiness

        names = [n for n in ("McShan Florist", "Petal Lane Florist") if n in answer]
        return AnswerReading(businesses=[NamedBusiness(name=n, kind="recommended", context=n) for n in names]), 5, 5


@pytest.fixture
def ai(client, florist_site, monkeypatch):
    """A confirmed business targeting Dallas and Plano (both with map positions) and fake AI platforms."""
    from spotted import api, platforms

    for k in ("PAID_AUDITS_ENABLED", "OPENAI_API_KEY", "AI_PAID_MAX_USD", "AI_FREE_PER_BUSINESS_PER_DAY",
              "AI_FREE_PER_IP_PER_DAY", "AI_PAID_CONCURRENCY"):
        monkeypatch.delenv(k, raising=False)
    ready = ["gemini_search", "gemini_maps", "gemini_memory", "chatgpt"]
    monkeypatch.setattr(platforms, "available_platforms", lambda: ready)
    monkeypatch.setattr(api, "available_platforms", lambda: ready)
    monkeypatch.setattr(platforms, "default_platforms", lambda: ["gemini_search", "gemini_maps"])
    monkeypatch.setattr(api, "default_platforms", lambda: ["gemini_search", "gemini_maps"])
    fake = Answerer()
    api.app.dependency_overrides[api.get_answerer] = lambda: fake
    api.app.dependency_overrides[api.get_reader] = lambda: Reader()
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    p = client.get(f"/api/businesses/{bid}").json()["profile"]
    dallas = next(loc for loc in p["locations"] if loc["city"] == "Dallas")
    plano = next(loc for loc in p["locations"] if loc["city"] == "Plano")
    dallas.update(lat=32.78, lng=-96.8, priority=1)
    plano.update(lat=33.02, lng=-96.7, priority=2)
    p["locations"] = [dallas, plano]
    assert client.put(f"/api/businesses/{bid}/profile", json=p).status_code == 200
    return {"client": client, "bid": bid, "fake": fake}


def _wait(client, audit_id):
    for _ in range(100):
        run = client.get(f"/api/ai-runs/{audit_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.1)
    raise AssertionError("still running")


def test_paid_audit_is_coming_soon_until_enabled(ai):
    c, bid = ai["client"], ai["bid"]
    got = c.get(f"/api/businesses/{bid}/ai-prompts").json()
    assert got["full_audit"]["enabled"] is False and "coming soon" in got["full_audit"]["message"]
    assert got["full_audit"]["locations"] == ["Dallas", "Plano"] and got["full_audit"]["runs"] == 3
    assert any("Screenshots" in x for x in got["full_audit"]["coming_soon"])
    assert len(got["full_prompts"]) > len(got["prompts"])
    assert got["free_limits"]["per_business_per_day"] == 3
    resp = c.post(f"/api/businesses/{bid}/ai-runs", json={"prompts": got["full_prompts"][:2], "tier": "paid"})
    assert resp.status_code == 403 and "coming soon" in resp.json()["detail"]


def test_paid_audit_runs_every_location_with_repeats_and_search_off(ai, monkeypatch):
    c, bid, fake = ai["client"], ai["bid"], ai["fake"]
    monkeypatch.setenv("PAID_AUDITS_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    got = c.get(f"/api/businesses/{bid}/ai-prompts").json()
    assert got["full_audit"]["enabled"] is True
    assert got["full_audit"]["platforms"] == ["gemini_search", "gemini_maps", "chatgpt", "gemini_memory"]
    free = c.post(f"/api/businesses/{bid}/ai-runs", json={"prompts": got["prompts"][:1]}).json()
    _wait(c, free["audit_id"])

    core = [p for p in got["full_prompts"] if p["intent"] not in ("branded", "accuracy")][:2]
    branded = [p for p in got["full_prompts"] if p["intent"] == "branded"][:1]
    fake.calls.clear()
    resp = c.post(f"/api/businesses/{bid}/ai-runs", json={"prompts": core + branded, "tier": "paid", "runs": 2})
    assert resp.status_code == 202, resp.text
    body = resp.json()
    # core: 2 prompts x 2 runs x 2 locations x 4 platforms; branded: 1 x 1 run x 1 location x 4 platforms
    assert body["expected_runs"] == 2 * 2 * 2 * 4 + 4 and body["reused"] is False
    run = _wait(c, body["audit_id"])
    assert run["status"] == "complete" and run["finished_runs"] == run["expected_runs"]
    assert run["tier"] == "paid" and run["runs_per_prompt"] == 2 and run["previous_audit_id"] == free["audit_id"]
    assert [x["city"] for x in run["locations"]] == ["Dallas", "Plano"]
    plano_maps = [x for x in fake.calls if x["key"] == "gemini_maps" and "Plano" in x["prompt"]]
    assert plano_maps and all(x["lat"] == 33.02 for x in plano_maps)
    gpt = [x for x in fake.calls if x["key"] == "chatgpt"]
    assert {x["where"]["city"] for x in gpt} == {"Dallas", "Plano"}
    assert all(x["where"] is None for x in fake.calls if x["key"] != "chatgpt")
    freq = run["prompts"][0]["frequency"]
    dallas_search = next(f for f in freq if f["platform_key"] == "gemini_search" and f["city"] == "Dallas")
    assert (dallas_search["named"], dallas_search["runs"]) == (2, 2)
    sc = run["search_comparison"]
    assert sc["search_off"]["named"] == 0 and sc["search_on"]["named"] > 0
    by = {p["key"]: p for p in run["platforms"]}
    assert by["chatgpt"]["location_method"] == "api_location"


def test_paid_audit_stops_at_the_spending_limit(ai, monkeypatch):
    c, bid = ai["client"], ai["bid"]
    monkeypatch.setenv("PAID_AUDITS_ENABLED", "1")
    monkeypatch.setenv("AI_PAID_MAX_USD", "0.0001")
    monkeypatch.setenv("AI_PAID_CONCURRENCY", "1")
    resp = c.post(f"/api/businesses/{bid}/ai-runs",
                  json={"prompts": [{"text": "best florists in Dallas", "intent": "discovery"}], "tier": "paid",
                        "platforms": ["gemini_search"], "search_off": False, "all_locations": False})
    run = _wait(c, resp.json()["audit_id"])
    assert run["expected_runs"] == 3 and run["finished_runs"] == 3
    assert run["skipped_runs"] == 2 and run["status"] == "partial" and "spending limit" in run["note"]
    assert run["platforms"][0]["errors"] == 0 and run["platforms"][0]["skipped"] == 2


def test_free_run_reuse_and_daily_limits(ai, monkeypatch):
    c, bid = ai["client"], ai["bid"]
    monkeypatch.setenv("AI_FREE_PER_BUSINESS_PER_DAY", "2")
    q = lambda t: {"prompts": [{"text": t, "intent": "discovery"}], "platforms": ["gemini_search"]}  # noqa: E731
    first = c.post(f"/api/businesses/{bid}/ai-runs", json=q("best florists in Dallas")).json()
    _wait(c, first["audit_id"])
    again = c.post(f"/api/businesses/{bid}/ai-runs", json=q("Best florists in Dallas ")).json()
    assert again == {"audit_id": first["audit_id"], "expected_runs": 1, "reused": True, "tier": "free"}
    second = c.post(f"/api/businesses/{bid}/ai-runs", json=q("florist near downtown Dallas"))
    assert second.status_code == 202 and second.json()["reused"] is False
    third = c.post(f"/api/businesses/{bid}/ai-runs", json=q("cheap florist Dallas"))
    assert third.status_code == 429 and "free AI runs for this business" in third.json()["detail"]

    monkeypatch.setenv("AI_FREE_PER_BUSINESS_PER_DAY", "10")
    monkeypatch.setenv("AI_FREE_PER_IP_PER_DAY", "2")
    ip = c.post(f"/api/businesses/{bid}/ai-runs", json=q("roses in Dallas"))
    assert ip.status_code == 429 and "network" in ip.json()["detail"]
