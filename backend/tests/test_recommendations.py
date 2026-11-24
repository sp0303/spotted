"""Recommendation rules (build step 5): evidence in, specific actions out, nothing generic."""

import re

from spotted.recommendations import CATEGORIES, build_recommendations

BUSINESS = {"name": "Petal Lane Florist", "domain": "petallane.example"}


def check(check_type, status, summary="Something we saw.", target="https://www.petallane.example/", fix=None):
    return {"check_type": check_type, "status": status, "summary": summary, "target": target, "fix": fix}


def foundations(*checks, blocked=()):
    return {"available": True, "checks": list(checks), "blocked_crawlers": list(blocked)}


def visibility(*platforms):
    plats = [{"key": k, "label": label, "search_enabled": search, "answers": a, "named": n, "recommended": 0,
              "own_site_cited": 0, "missed_prompts": missed, "named_instead": [{"name": "McShan Florist", "answers": a}]}
             for k, label, search, a, n, missed in platforms]
    totals = {"answers": sum(p["answers"] for p in plats), "named": sum(p["named"] for p in plats)}
    return {"available": True, "audit_id": "a1", "platforms": plats, "totals": totals}


def recs(**sections):
    return build_recommendations({"business": BUSINESS, **sections})


def by_key(out):
    return {r["rule_key"]: r for r in out}


def test_nothing_observed_means_no_recommendations():
    assert recs() == []
    assert recs(foundations={"available": False}, visibility={"available": False}, search={"available": False}) == []


def test_every_recommendation_has_the_required_fields():
    out = recs(foundations=foundations(check("noindex", "issue"), check("sitemap", "warning"),
                                       check("js_render", "issue"), check("google_index", "not_verified")),
               visibility=visibility(("gemini_search", "Gemini (Google Search)", True, 5, 0, ["best florists in Dallas"])))
    assert out
    for r in out:
        assert r["category"] in CATEGORIES and r["priority"] in ("high", "medium", "low")
        assert r["title"] and r["why"] and r["how"] and r["effort"] in ("low", "medium", "high") and r["evidence"]
        assert not re.search(r"%|percent", r["why"])  # counts, never percentages


def test_foundation_issues_become_actions():
    out = by_key(recs(foundations=foundations(
        check("cdn_waf", "issue", "Crawlers that help you get found look blocked: OAI-SearchBot.", fix="Allow them."),
        check("robots_txt", "issue", "Your robots.txt blocks Bingbot."),
        check("noindex", "issue", target="https://x.example/a"), check("noindex", "issue", target="https://x.example/b"),
        check("noindex", "pass", target="https://x.example/c"),
        check("sitemap", "pass"), check("js_render", "warning", "We couldn't find your phone in the HTML."),
        check("webmcp", "opportunity"),
        blocked=[{"token": "OAI-SearchBot", "result": "likely_blocked", "robots": "allow"}])))
    assert out["foundations:crawler_blocked"]["priority"] == "high"
    assert out["foundations:crawler_blocked"]["category"] == "crawler_access"
    assert "OAI-SearchBot" in out["foundations:crawler_blocked"]["why"]
    assert out["foundations:robots_txt"]["priority"] == "high"
    assert "2 pages" in out["foundations:noindex"]["why"] and len(out["foundations:noindex"]["evidence"]) == 2
    assert out["foundations:js_render:warning"]["priority"] == "medium"
    assert out["foundations:js_render:warning"]["category"] == "rendering"
    assert "foundations:sitemap" not in out  # it passed
    assert out["foundations:webmcp"]["priority"] == "low" and out["foundations:webmcp"]["is_best_practice"]


def test_unverified_indexing_is_more_urgent_when_ai_never_names_you():
    f = foundations(check("google_index", "not_verified"), check("bing_index", "not_verified"))
    unseen = by_key(recs(foundations=f, visibility=visibility(("gemini_search", "Gemini", True, 4, 0, []))))
    seen = by_key(recs(foundations=f, visibility=visibility(("gemini_search", "Gemini", True, 4, 4, []))))
    assert unseen["foundations:webmaster_tools"]["priority"] == "medium"
    assert seen["foundations:webmaster_tools"]["priority"] == "low"


def test_platform_not_naming_you():
    out = by_key(recs(visibility=visibility(
        ("gemini_search", "Gemini (Google Search)", True, 5, 0, ["best florists in Dallas"]),
        ("gemini_maps", "Gemini (Google Maps)", True, 5, 1, ["flower delivery Dallas"]),
        ("perplexity", "Perplexity", True, 5, 4, []),
        ("gemini_memory", "Gemini (no search)", False, 5, 0, []))))
    search = out["ai:not_named:gemini_search"]
    assert search["priority"] == "high" and search["category"] == "platform_specific"
    assert "0 of 5" in search["why"] and '"best florists in Dallas"' in search["why"] and "McShan" in search["why"]
    assert any("Google" in step for step in search["how"])
    maps = out["ai:not_named:gemini_maps"]
    assert maps["priority"] == "medium" and maps["category"] == "listings_voice" and "1 of 5" in maps["why"]
    assert "ai:not_named:perplexity" not in out  # named in 4 of 5
    memory = out["ai:model_knowledge:gemini_memory"]
    assert memory["priority"] == "low" and "months" in memory["why"]


def test_competitors_ahead_uses_observed_attributes_only():
    comp = {"client": {"answers": 1}, "others": [
        {"name": "McShan Florist", "answers": 4, "attributes": ["same-day delivery", "since 1948"]},
        {"name": "Bloom Room", "answers": 1, "attributes": ["luxury"]}]}
    out = by_key(recs(visibility=visibility(("gemini_search", "Gemini", True, 5, 1, [])), competitors=comp))
    r = out["ai:competitors_ahead"]
    assert r["category"] == "recommendation_evidence"
    assert "McShan Florist in 4" in r["why"] and '"same-day delivery"' in r["why"]
    assert "Bloom Room" not in r["why"]  # named once: not a pattern
    none_ahead = by_key(recs(visibility=visibility(("gemini_search", "Gemini", True, 5, 5, [])),
                             competitors={"client": {"answers": 5}, "others": comp["others"]}))
    assert "ai:competitors_ahead" not in none_ahead


def test_citation_gaps_never_claim_cause():
    cit = {"answers_with_sources": 6, "own_site_cited": 0, "gaps": [
        {"domain": "dmagazine.com", "type": "publication", "answers": 3, "competitors": ["McShan Florist"],
         "prompts": ["best florists in Dallas"]},
        {"domain": "yelp.com", "type": "directory", "answers": 1, "competitors": ["Bloom Room"], "prompts": []}]}
    out = by_key(recs(visibility=visibility(("gemini_search", "Gemini", True, 6, 3, [])), citations=cit))
    d = out["citation:dmagazine.com"]
    assert d["priority"] == "medium" and d["category"] == "citation_source"
    assert d["why"].startswith("Pattern we see") and "can't tell" in d["why"] and "3 answers" in d["why"]
    assert out["citation:yelp.com"]["priority"] == "low"
    assert any("listing" in s for s in out["citation:yelp.com"]["how"])
    own = out["citation:own_site_never"]
    assert own["category"] == "content_gap" and "6 answers" in own["why"] and "petallane.example" in own["why"]
    assert not any("caused" in r["why"] for r in out.values())


def test_wrong_facts_grouped_by_fact():
    acc = {"wrong": [
        {"platform": "Gemini", "prompt": "what is Petal Lane?",
         "facts": {"phone": {"said": "214-555-9999", "confirmed": ["+1 214-555-0142"]}}},
        {"platform": "Perplexity", "prompt": "Petal Lane phone",
         "facts": {"phone": {"said": "214-555-9999", "confirmed": ["+1 214-555-0142"]},
                   "address": {"said": "9 Main St", "confirmed": ["1200 Elm St, Dallas"]}}}]}
    out = by_key(recs(visibility=visibility(("gemini_search", "Gemini", True, 2, 2, [])), accuracy=acc))
    assert out["accuracy:phone"]["priority"] == "high" and out["accuracy:phone"]["category"] == "entity_brand"
    assert "2 answers" in out["accuracy:phone"]["why"] and '"214-555-9999"' in out["accuracy:phone"]["why"]
    assert len(out["accuracy:phone"]["evidence"]) == 2
    assert "accuracy:address" in out


def test_search_and_listings_rules():
    search = {"available": True, "listings": [
        {"platform": "google_business_profile", "status": "not_found", "issues": []},
        {"platform": "bing_places", "status": "not_found", "issues": []},
        {"platform": "yelp", "status": "found", "issues": ["Hours differ from your website"]},
        {"platform": "apple_maps", "status": "coming_soon", "issues": []},
        {"platform": "facebook", "status": "unknown", "issues": []}],
        "queries": [
            {"query": "florist Dallas", "maps_checked": True, "maps_rank": None, "maps_results": ["McShan Florist"],
             "web_checked": True, "web_rank": 3, "web_results": ["yelp.com"]},
            {"query": "flowers Dallas", "maps_checked": True, "maps_rank": None, "maps_results": ["Bloom Room"],
             "web_checked": True, "web_rank": None, "web_results": ["yelp.com", "dmagazine.com"]}]}
    out = by_key(recs(search=search))
    assert out["listing:google_business_profile"]["priority"] == "high"
    assert out["listing:bing_places"]["priority"] == "medium"
    assert "Hours differ" in out["listing_issues:yelp"]["why"]
    assert "listing:apple_maps" not in out and "listing:facebook" not in out  # not checked yet
    assert "2 of 2" in out["search:maps_missing"]["why"] and "McShan Florist" in out["search:maps_missing"]["why"]
    assert "1 of 2" in out["search:web_missing"]["why"]
    assert "measure:rerun" not in out  # no AI run to repeat


def test_sorted_by_priority_and_unique():
    out = recs(foundations=foundations(check("webmcp", "opportunity"), check("noindex", "issue"),
                                       check("sitemap", "warning")),
               visibility=visibility(("gemini_search", "Gemini", True, 5, 0, [])))
    order = [r["priority"] for r in out]
    assert order == sorted(order, key=["high", "medium", "low"].index)
    assert len({r["rule_key"] for r in out}) == len(out)


def test_press_coverage_cross_referenced_with_ai_citations():
    press = {"available": True, "client_articles": [], "competitor_only_sources": ["dmagazine.com", "thursd.com", "kera.org"],
             "competitor_articles": [
                 {"competitor": "McShan Florist", "title": "McShan turns 75", "source": "D Magazine", "domain": "dmagazine.com"},
                 {"competitor": "Bloom Room", "title": "Bloom Room opens", "source": "Thursd", "domain": "thursd.com"}]}
    cit = {"answers_with_sources": 4, "own_site_cited": 1, "top_sources": [{"domain": "thursd.com", "answers": 1}],
           "gaps": [{"domain": "dmagazine.com", "type": "publication", "answers": 2, "competitors": ["McShan Florist"]}]}
    out = by_key(recs(visibility=visibility(("gemini_search", "Gemini", True, 4, 1, [])), citations=cit,
                      search={"available": True, "press": press}))
    d = out["press:dmagazine.com"]
    assert d["priority"] == "high" and d["category"] == "citation_source"
    assert d["why"].startswith("Pattern we see") and "D Magazine" in d["why"] and "McShan Florist" in d["why"]
    assert "2 answers" in d["why"] and "isn't a guarantee" in d["why"]
    assert "citation:dmagazine.com" not in out  # merged into the press action
    assert out["press:thursd.com"]["priority"] == "medium" and out["press:kera.org"]["priority"] == "low"
    assert by_key(recs(search={"available": True, "press": {"available": False}})) == {}


def test_citation_gap_skipped_when_press_already_covers_client():
    from spotted.recommendations import build_recommendations

    sections = {
        "visibility": {"available": True, "platforms": [], "totals": {"answers": 3, "named": 1}},
        "citations": {"available": True, "answers_with_sources": 3, "own_site_cited": 1,
                      "gaps": [{"domain": "cbsnews.com", "type": "publication", "answers": 2,
                                "competitors": ["McShan Florist"], "prompts": ["affordable florist in Dallas"]},
                               {"domain": "magicpin.com", "type": "directory", "answers": 1,
                                "competitors": ["McShan Florist"], "prompts": []}]},
        "search": {"available": True, "press": {"available": True, "client_sources": ["www.cbsnews.com"],
                                                "competitor_only_sources": []}},
    }
    keys = [r["rule_key"] for r in build_recommendations(sections)]
    assert "citation:cbsnews.com" not in keys and "citation:magicpin.com" in keys
