"""Report numbers (build step 4) and the Action Center API (step 5).

The saved audit documents below are shaped like airun/repo store them.
"""

from datetime import datetime, timedelta, timezone

from spotted import airun
from spotted.recommendations import build_recommendations
from spotted.report import ai_sections, compare, foundations_section, search_section
from uuid import uuid4

T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)

PROMPTS = [{"id": "p1", "text": "best florists in Dallas", "intent": "discovery", "user_edited": False, "sort_order": 0},
           {"id": "p2", "text": "who offers same-day delivery in Dallas?", "intent": "service", "user_edited": False,
            "sort_order": 1},
           {"id": "p3", "text": "what is Petal Lane Florist in Dallas?", "intent": "branded", "user_edited": False,
            "sort_order": 2}]


def mention(name, client=False, kind="recommended", wrong=None, attrs=None, position=1):
    return {"entity_name": name, "normalized": name.lower(), "is_client": client, "competitor": None,
            "position": position, "kind": kind, "context": f"{name} is nice.", "attributes": attrs or [], "facts": {},
            "facts_wrong": wrong or {}}


def cit(domain, kind="other"):
    return {"url": f"https://{domain}/page", "domain": domain, "title": None, "position": 1, "source_type": kind}


def run(prompt_id, key, mentions=(), citations=(), status="done"):
    return {"id": str(uuid4()), "prompt_id": prompt_id, "platform_key": key, "platform": "gemini", "label": key,
            "surface": "api", "run_index": 1, "status": status, "error": None if status == "done" else "boom",
            "latency_ms": 1000, "cost_usd": 0.001, "tokens_in": 1, "tokens_out": 1,
            "response": {"text": "answer", "search_queries": [], "maps_places": []} if status == "done" else None,
            "mentions": list(mentions), "citations": list(citations), "asked_for_location": False}


WRONG_PHONE = {"phone": {"said": "214-555-9999", "confirmed": ["+1 214-555-0142"]}}


def current_runs():
    return [
        run("p1", "gemini_search", [mention("McShan Florist", attrs=["same-day delivery"]),
                                    mention("Petal Lane Florist", client=True, position=2)],
            [cit("yelp.com", "directory"), cit("petallane.example", "own_site")]),
        run("p2", "gemini_search", [mention("McShan Florist", attrs=["since 1948"]), mention("Bloom Room")],
            [cit("dmagazine.com", "publication"), cit("yelp.com", "directory")]),
        run("p1", "gemini_maps", [mention("McShan Florist")], [cit("dmagazine.com", "publication")]),
        run("p2", "gemini_maps", [mention("Bloom Room"), mention("McShan Florist")]),
        run("p3", "gemini_search", [mention("Petal Lane Florist", client=True, wrong=WRONG_PHONE)]),
        run("p3", "gemini_maps", status="error"),
    ]


def previous_runs():
    return [
        run("p1", "gemini_search", [mention("McShan Florist")]),
        run("p2", "gemini_search", [mention("McShan Florist")]),
        run("p1", "gemini_maps", [mention("McShan Florist")]),
        run("p2", "gemini_maps", [mention("Bloom Room")]),
    ]


def ai_audit(business_id, runs, created=T0, status="complete"):
    return {"_id": str(uuid4()), "business_id": business_id, "tier": "free", "status": status,
            "methodology_version": "ai-run-1",
            "config": {"kind": "ai_run", "platforms": ["gemini_search", "gemini_maps"], "skipped": {}, "runs": 1,
                       "location": {"city": "Dallas", "lat": 32.78, "lng": -96.8}, "server_region": "local"},
            "prompts": PROMPTS, "runs": runs, "expected_runs": 6, "cost_usd": 0.006,
            "started_at": created, "first_results_at": created + timedelta(seconds=5),
            "finished_at": created + timedelta(seconds=30), "created_at": created}


def foundations_audit(business_id, created=T0):
    def check(check_type, status, summary, target="https://www.petallane.example/", fix=None):
        return {"check_type": check_type, "target": target, "status": status, "evidence_level": "observed",
                "summary": summary, "fix": fix, "evidence": {}, "checked_at": created}
    return {"_id": str(uuid4()), "business_id": business_id, "tier": "free", "status": "complete",
            "methodology_version": "foundations-1",
            "config": {"kind": "foundations", "url": "https://www.petallane.example/",
                       "final_url": "https://www.petallane.example/", "cdn": "cloudflare", "platform": None,
                       "rendered": False},
            "started_at": created, "first_results_at": created, "finished_at": created, "created_at": created,
            "checks": [
                check("http_status", "pass", "Your homepage loads over HTTPS without errors."),
                check("noindex", "issue", "This page tells search engines not to list it.",
                      "https://www.petallane.example/weddings", "Remove the noindex tag."),
                check("cdn_waf", "issue", "Crawlers that help you get found look blocked: OAI-SearchBot.",
                      fix="Allow these crawlers in your CDN bot settings."),
                check("sitemap", "pass", "Your sitemap lists 12 pages."),
                check("google_index", "not_verified", "Not verified yet.", fix="Verify in Google Search Console."),
            ],
            "crawler_access": [
                {"url": "https://www.petallane.example/", "user_agent": "OAI-SearchBot", "robots": "allow",
                 "http_status": 403, "challenge": True, "result": "likely_blocked", "cdn": "cloudflare",
                 "evidence": {"note": "Challenge page.", "robots_line": None}},
                {"url": "https://www.petallane.example/", "user_agent": "Googlebot", "robots": "allow",
                 "http_status": 200, "challenge": False, "result": "accessible", "cdn": "cloudflare",
                 "evidence": {"note": "", "robots_line": None}},
            ]}


def search_audit(business_id, created=T0):
    return {"_id": str(uuid4()), "business_id": business_id, "status": "complete", "created_at": created,
            "config": {"kind": "search_listings"},
            "summary": {
                "checked_at": created.isoformat(),
                "queries": [
                    {"query": "florist Dallas", "maps": {"client_rank": None, "results": ["McShan Florist", "Bloom Room"]},
                     "web": {"client_rank": 4, "results": [{"domain": "yelp.com", "title": "Best florists"}]}},
                    {"query": "flower delivery Dallas", "maps": {"client_rank": None, "results": ["McShan Florist"]}},
                    {"query": None},  # malformed rows are skipped
                ],
                "listings": [{"platform": "google_business_profile", "status": "not_found", "url": None, "issues": []},
                             {"platform": "yelp", "status": "found", "url": "https://yelp.com/biz/petal-lane",
                              "issues": ["Hours differ from your website"]},
                             {"platform": "apple_maps", "status": "coming_soon"}],
                "coming_soon": ["Apple Maps"],
                "press": {
                    "client_articles": [],
                    "category_articles": [{"title": "Best Dallas florists", "source": "D Magazine",
                                           "source_url": "https://www.dmagazine.com", "url": "https://n/1"}],
                    "competitor_articles": [
                        {"competitor": "McShan Florist", "title": "McShan turns 75", "source": "D Magazine",
                         "source_url": "https://www.dmagazine.com", "url": "https://n/2", "published": "2026-10-01"},
                        {"competitor": "Bloom Room", "title": "Bloom Room opens", "source": "Thursd",
                         "source_url": "https://thursd.com", "url": "https://n/3"},
                        "garbage"],
                    "client_sources": [],
                    "competitor_only_sources": ["https://www.dmagazine.com", "thursd.com"],
                },
            }}


# ---------------------------------------------------------------------------
# Pure numbers
# ---------------------------------------------------------------------------

def _sections(runs):
    audit = ai_audit("b1", runs)
    return audit, ai_sections(audit, airun.summarize(audit))


def test_visibility_counts_per_platform_skip_branded_and_failed():
    _, s = _sections(current_runs())
    by = {p["key"]: p for p in s["visibility"]["platforms"]}
    assert (by["gemini_search"]["answers"], by["gemini_search"]["named"]) == (2, 1)
    assert (by["gemini_maps"]["answers"], by["gemini_maps"]["named"], by["gemini_maps"]["errors"]) == (2, 0, 1)
    assert by["gemini_maps"]["missed_prompts"] == ["best florists in Dallas", "who offers same-day delivery in Dallas?"]
    assert by["gemini_maps"]["named_instead"][0] == {"name": "McShan Florist", "answers": 2}
    assert s["visibility"]["totals"] == {"answers": 4, "named": 1, "recommended": 1, "own_site_cited": 1, "errors": 1}


def test_share_of_voice_and_attributes():
    _, s = _sections(current_runs())
    c = s["competitors"]
    assert c["answers"] == 4 and c["client"] == {"answers": 1, "recommended": 1}
    assert [(o["name"], o["answers"]) for o in c["others"]] == [("McShan Florist", 4), ("Bloom Room", 2)]
    assert c["others"][0]["attributes"] == ["same-day delivery", "since 1948"]


def test_citation_gaps_exclude_sources_cited_with_the_client():
    _, s = _sections(current_runs())
    gaps = s["citations"]["gaps"]
    assert [g["domain"] for g in gaps] == ["dmagazine.com"]  # yelp.com was also cited in an answer naming you
    assert gaps[0]["answers"] == 2 and gaps[0]["competitors"][0] == "McShan Florist"
    assert set(gaps[0]["platforms"]) == {"Gemini (Google Search)", "Gemini (Google Maps)"}
    assert s["citations"]["own_site_cited"] == 1 and s["citations"]["answers_with_sources"] == 3


def test_accuracy_lists_wrong_facts():
    _, s = _sections(current_runs())
    assert s["accuracy"]["branded_answers"] == 1 and s["accuracy"]["answers_naming_you"] == 2
    assert s["accuracy"]["wrong"][0]["facts"]["phone"]["said"] == "214-555-9999"


def test_comparison_flags_small_changes():
    cur_audit, cur = _sections(current_runs())
    prev_audit, prev = _sections(previous_runs())
    out = compare(cur, prev, cur_audit, prev_audit)
    assert out["same_questions"] and out["same_platforms"]
    assert out["totals"]["before"]["named"] == 0 and out["totals"]["after"]["named"] == 1
    assert out["totals"]["named_change"] == 1 and out["totals"]["small"] is True
    assert "isn't evidence" in out["note"]


def test_search_section_reads_defensively():
    s = search_section(search_audit("b1"))
    assert [q["query"] for q in s["queries"]] == ["florist Dallas", "flower delivery Dallas"]
    assert s["maps"] == {"checked": 2, "found": 0} and s["web"] == {"checked": 1, "found": 1}
    assert s["listings"][2]["status"] == "coming_soon" and s["listings"][2]["issues"] == []
    assert s["press"]["competitor_only_sources"] == ["dmagazine.com", "thursd.com"]
    assert [a["domain"] for a in s["press"]["competitor_articles"]] == ["dmagazine.com", "thursd.com"]
    assert search_section({"summary": "garbage"})["queries"] == []
    assert search_section({"summary": {"press": "x"}})["press"] == {"available": False}
    assert search_section(None) == {"available": False}


def test_foundations_section_counts_and_blocked_crawlers():
    f = {"audit_id": "f1", "checked_at": "x", "url": "u",
         "checks": [{"check_type": "noindex", "status": "issue"}, {"check_type": "sitemap", "status": "pass"}],
         "crawlers": [{"token": "OAI-SearchBot", "purpose": "search", "result": "likely_blocked", "robots": "allow"},
                      {"token": "GPTBot", "purpose": "training", "result": "likely_blocked", "robots": "disallow"},
                      {"token": "Google-Extended", "purpose": "training", "result": "inconclusive", "token_only": True}]}
    s = foundations_section(f)
    assert s["counts"]["issue"] == 1 and s["counts"]["pass"] == 1
    assert [b["token"] for b in s["blocked_crawlers"]] == ["OAI-SearchBot"]  # training blocks are the owner's choice


def test_recommendations_from_saved_runs():
    _, s = _sections(current_runs())
    recs = build_recommendations({"business": {"name": "Petal Lane Florist", "domain": "petallane.example"},
                                  "foundations": {"available": False}, "search": {"available": False}, **s})
    keys = [r["rule_key"] for r in recs]
    assert "ai:not_named:gemini_maps" in keys and "ai:not_named:gemini_search" not in keys  # 1 of 2 is not "rarely"
    assert "accuracy:phone" in keys and "citation:dmagazine.com" in keys and "ai:competitors_ahead" in keys
    assert "citation:own_site_never" not in keys  # the site was cited once
    assert keys[-1] == "measure:rerun"


# ---------------------------------------------------------------------------
# API (needs TEST_MONGO_URL)
# ---------------------------------------------------------------------------

def _confirmed_business(client):
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    profile = client.get(f"/api/businesses/{bid}").json()["profile"]
    profile["locations"] = [loc for loc in profile["locations"] if loc["city"] == "Dallas"]
    assert client.put(f"/api/businesses/{bid}/profile", json=profile).status_code == 200
    return bid


def test_report_without_audits(client, florist_site):
    bid = _confirmed_business(client)
    resp = client.get(f"/api/businesses/{bid}/report")
    assert resp.status_code == 200, resp.text
    r = resp.json()
    assert r["business"]["name"] == "Petal Lane Florist" and r["business"]["city"] == "Dallas"
    for section in ("visibility", "competitors", "citations", "accuracy", "foundations", "search", "comparison"):
        assert r[section]["available"] is False
    assert r["actions"] == [] and r["action_counts"]["total"] == 0
    assert client.get("/api/businesses/00000000-0000-0000-0000-000000000000/report").status_code == 404


def test_report_end_to_end_keeps_action_status(client, florist_site, db, test_prefix):
    bid = _confirmed_business(client)
    audits = db[test_prefix + "audits"]
    audits.insert_many([ai_audit(bid, previous_runs(), created=T0 - timedelta(days=30)),
                        ai_audit(bid, current_runs()), foundations_audit(bid), search_audit(bid)])

    resp = client.get(f"/api/businesses/{bid}/report")
    assert resp.status_code == 200, resp.text
    r = resp.json()
    assert r["overview"]["method"] == "API view" and r["overview"]["visibility_questions"] == 2
    assert r["visibility"]["totals"]["named"] == 1 and r["foundations"]["counts"]["issue"] == 2
    assert r["comparison"]["available"] and r["comparison"]["totals"]["named_change"] == 1
    assert r["search"]["maps"] == {"checked": 2, "found": 0}
    keys = {a["rule_key"]: a for a in r["actions"]}
    for k in ("foundations:crawler_blocked", "foundations:noindex", "ai:not_named:gemini_maps", "accuracy:phone",
              "press:dmagazine.com", "press:thursd.com", "listing:google_business_profile", "listing_issues:yelp",
              "search:maps_missing", "measure:rerun"):
        assert k in keys, k
    assert "OAI-SearchBot" in keys["foundations:crawler_blocked"]["why"]
    # D Magazine covers competitors and AI cites it next to them: one high-priority outreach action, not two.
    assert keys["press:dmagazine.com"]["priority"] == "high" and "citation:dmagazine.com" not in keys
    assert "Pattern we see" in keys["press:dmagazine.com"]["why"] and "McShan Florist" in keys["press:dmagazine.com"]["why"]
    assert keys["press:thursd.com"]["priority"] == "low"
    assert all(a["status"] == "not_started" and a["id"] for a in r["actions"])
    assert r["action_counts"]["total"] == len(r["actions"]) and r["action_counts"]["high"] >= 4
    priorities = [a["priority"] for a in r["actions"]]
    assert priorities == sorted(priorities, key=["high", "medium", "low"].index)
    # Numbers saved for later comparison: both AI runs, the foundations and the search audit.
    assert db[test_prefix + "audit_metrics"].count_documents({"business_id": bid}) == 4
    named_all = next(m for m in r["metrics"] if m["metric"] == "named" and m["platform"] is None)
    assert (named_all["numerator"], named_all["denominator"]) == (1, 4)

    # Status changes survive regenerating the report; nothing is duplicated.
    action = keys["ai:not_named:gemini_maps"]
    resp = client.patch(f"/api/businesses/{bid}/actions/{action['id']}", json={"status": "in_progress"})
    assert resp.status_code == 200 and resp.json()["status"] == "in_progress"
    assert client.patch(f"/api/businesses/{bid}/actions/{action['id']}", json={"status": "maybe"}).status_code == 422
    other = "00000000-0000-0000-0000-000000000000"
    assert client.patch(f"/api/businesses/{bid}/actions/{other}", json={"status": "done"}).status_code == 404
    assert client.patch(f"/api/businesses/{other}/actions/{action['id']}", json={"status": "done"}).status_code == 404
    again = client.get(f"/api/businesses/{bid}/report").json()
    assert {a["rule_key"]: a["status"] for a in again["actions"]}["ai:not_named:gemini_maps"] == "in_progress"
    assert db[test_prefix + "actions"].count_documents({"business_id": bid}) == len(r["actions"])

    # A newer run where Maps names the client: that action is no longer shown.
    newer = current_runs()
    newer[2]["mentions"].append(mention("Petal Lane Florist", client=True, position=2))
    newer[3]["mentions"].append(mention("Petal Lane Florist", client=True, position=3))
    audits.insert_one(ai_audit(bid, newer, created=T0 + timedelta(days=1)))
    latest = client.get(f"/api/businesses/{bid}/report").json()
    assert "ai:not_named:gemini_maps" not in {a["rule_key"] for a in latest["actions"]}
    assert latest["comparison"]["totals"]["before"]["named"] == 1
    listed = client.get(f"/api/businesses/{bid}/actions").json()
    assert listed["action_counts"]["total"] == len(latest["actions"])
