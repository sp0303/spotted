from spotted.airun import summarize
from spotted.analysis import (AnswerReading, NamedBusiness, category_words, citations_from, domain_of,
                              mentions_from, same_name)
from spotted.models import BusinessProfile, Fact, Location, Service
from spotted.prompts import plural, suggest_prompts


def profile(**kw) -> BusinessProfile:
    base = dict(
        website_url="https://www.petallane.example/", domain="petallane.example",
        name=Fact(value="Petal Lane Florist", origin="confirmed"),
        aliases=[Fact(value="Petal Lane", origin="confirmed")],
        category=Fact(value="Florist", origin="confirmed"),
        services=[Service(value="Same-day delivery", origin="confirmed"),
                  Service(value="Wedding flowers", origin="confirmed")],
        differentiators=[Fact(value="Family-owned since 1998", origin="confirmed")],
        phones=[Fact(value="+1 214-555-0142", origin="confirmed")],
        locations=[Location(address="1200 Elm St", city="Dallas", region="TX", country_code="US",
                            lat=32.78, lng=-96.8, origin="confirmed")],
        suggested_competitors=[Fact(value="McShan Florist", origin="confirmed")],
    )
    base.update(kw)
    return BusinessProfile(**base)


def test_plural():
    assert plural("florist") == "florists"
    assert plural("bakery") == "bakeries"
    assert plural("coach") == "coaches"
    assert plural("dental clinic") == "dental clinics"
    assert plural("day spa") == "day spas"


def test_suggest_prompts_names_the_city_and_keeps_branded_last():
    prompts = suggest_prompts(profile())
    texts = [p.text for p in prompts]
    assert texts[0] == "best florists in Dallas"
    assert "who offers same-day delivery in Dallas?" in texts
    assert all("Dallas" in t for t in texts)
    assert prompts[-1].intent == "branded" and "Petal Lane Florist" in prompts[-1].text
    assert len(texts) == len({t.lower() for t in texts}) <= 8


def test_suggest_prompts_without_city_or_category():
    p = profile(category=None, locations=[], services=[], differentiators=[])
    prompts = suggest_prompts(p)
    assert [x.intent for x in prompts] == ["branded"]


def test_name_matching_ignores_category_words():
    cw = category_words(profile())
    assert same_name("Petal Lane Flowers", "Petal Lane Florist", cw)
    assert same_name("McShan Florist Inc.", "McShan Florist", cw)
    assert not same_name("Lane Florist", "Petal Lane Florist", cw)  # a different shop
    assert not same_name("Dallas Florist", "Petal Lane Florist", cw)


def test_mentions_mark_client_competitor_and_wrong_phone():
    reading = AnswerReading(businesses=[
        NamedBusiness(name="McShan Florist", kind="recommended", context="McShan Florist is a classic."),
        NamedBusiness(name="Petal Lane", kind="recommended", context="Petal Lane, call 214-555-9999.",
                      stated_phone="214-555-9999", is_target_business=True),
        NamedBusiness(name="McShan Florist Inc", kind="mentioned", context="dup"),
        NamedBusiness(name="Bloom Room", kind="mentioned", context="Bloom Room is pricier."),
    ])
    ms = mentions_from(reading, profile(), ["McShan Florist"])
    assert [m["entity_name"] for m in ms] == ["McShan Florist", "Petal Lane", "Bloom Room"]
    assert ms[0]["competitor"] == "McShan Florist" and not ms[0]["is_client"]
    assert ms[1]["is_client"] and ms[1]["position"] == 2
    assert ms[1]["facts_wrong"]["phone"]["said"] == "214-555-9999"
    assert ms[2]["competitor"] is None


def test_neighbourhood_is_not_a_wrong_address():
    def client_says(address):
        reading = AnswerReading(businesses=[NamedBusiness(name="Petal Lane", kind="recommended", context="x",
                                                          stated_address=address)])
        return mentions_from(reading, profile(), [])[0]["facts_wrong"]
    assert client_says("Bishop Arts District") == {}
    assert client_says("1200 Elm St, Dallas, TX") == {}
    assert client_says("4500 Main St, Dallas")["address"]["said"] == "4500 Main St, Dallas"


def test_citations_sorted_into_types():
    srcs = [
        {"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "title": "dmagazine.com"},
        {"url": "https://www.yelp.com/search?find_desc=florist", "title": "Yelp"},
        {"url": "https://petallane.example/about", "title": None},
        {"url": "https://mcshanflorist.com/", "title": "McShan"},
        {"url": "https://www.reddit.com/r/Dallas/xyz", "title": None},
        {"url": "https://www.yelp.com/search?find_desc=florist", "title": "Yelp"},  # duplicate
    ]
    cs = citations_from(srcs, profile(), ["McShan Florist"])
    assert [(c["domain"], c["source_type"]) for c in cs] == [
        ("dmagazine.com", "publication"), ("yelp.com", "directory"), ("petallane.example", "own_site"),
        ("mcshanflorist.com", "competitor_site"), ("reddit.com", "forum")]
    assert domain_of("https://vertexaisearch.cloud.google.com/x", "Some Title") == ""


def test_summary_counts_unbranded_answers_only():
    audit = {
        "_id": "a1", "business_id": "b1", "status": "complete", "expected_runs": 3, "cost_usd": 0.01,
        "config": {"platforms": ["gemini_search"], "location": {"city": "Dallas"}, "skipped": {}},
        "prompts": [{"id": "p1", "text": "best florists in Dallas", "intent": "discovery"},
                    {"id": "p2", "text": "same-day flowers Dallas", "intent": "service"},
                    {"id": "p3", "text": "what is Petal Lane?", "intent": "branded"}],
        "runs": [
            {"id": "r1", "prompt_id": "p1", "platform_key": "gemini_search", "run_index": 1, "status": "done",
             "error": None, "latency_ms": 9000, "cost_usd": 0.004, "response": {"text": "..."},
             "mentions": [{"entity_name": "McShan Florist", "normalized": "mcshan", "is_client": False,
                           "competitor": "McShan Florist", "position": 1, "kind": "recommended", "context": "",
                           "facts_wrong": {}},
                          {"entity_name": "Petal Lane", "normalized": "petal lane", "is_client": True,
                           "competitor": None, "position": 2, "kind": "recommended", "context": "x",
                           "facts_wrong": {}}],
             "citations": [{"domain": "petallane.example", "source_type": "own_site", "url": "u"}]},
            {"id": "r2", "prompt_id": "p2", "platform_key": "gemini_search", "run_index": 1, "status": "done",
             "error": None, "latency_ms": 11000, "cost_usd": 0.004, "response": {"text": "..."},
             "mentions": [{"entity_name": "McShan", "normalized": "mcshan", "is_client": False, "competitor": None,
                           "position": 1, "kind": "recommended", "context": "", "facts_wrong": {}}],
             "citations": []},
            {"id": "r3", "prompt_id": "p3", "platform_key": "gemini_search", "run_index": 1, "status": "done",
             "error": None, "latency_ms": 5000, "cost_usd": 0.002, "response": {"text": "..."},
             "mentions": [{"entity_name": "Petal Lane", "normalized": "petal lane", "is_client": True,
                           "competitor": None, "position": 1, "kind": "mentioned", "context": "",
                           "facts_wrong": {"phone": {"said": "1", "confirmed": ["2"]}}}],
             "citations": []},
        ],
    }
    s = summarize(audit)
    g = s["platforms"][0]
    assert (g["answers"], g["named"], g["recommended"], g["best_position"], g["own_site_cited"]) == (2, 1, 1, 2, 1)
    assert s["competitors"][0] == {"name": "McShan Florist", "answers": 2, "platforms": ["Gemini (Google Search)"],
                                   "known": True, "prompts": 2}
    assert s["tier"] == "free" and s["runs_per_prompt"] == 1 and s["search_comparison"] is None
    assert s["prompts"][0]["frequency"][0]["named"] == 1 and s["locations"][0]["answers"] == 2
    assert s["wrong_facts"][0]["prompt"] == "what is Petal Lane?"
    assert s["visibility_answers"] == 2


async def test_fill_positions_only_for_targets_without_one():
    from spotted.geocode import fill_positions

    asked = []

    async def fake(query):
        asked.append(query)
        return None if query.startswith("9 Nowhere") else (32.7, -96.8)

    locs = [
        Location(address="9 Nowhere Ln", city="Dallas", region="TX", country_code="US", origin="confirmed"),
        Location(city="Plano", country_code="US", is_physical=False, origin="confirmed"),
        Location(city="Austin", country_code="US", is_target=False, origin="confirmed"),
        Location(city="Dallas", lat=1.0, lng=2.0, country_code="US", origin="confirmed"),
        Location(label="Online only", country_code="US", origin="confirmed"),
    ]
    out = await fill_positions(locs, fake)
    assert [(x.lat, x.lng) for x in out] == [(32.7, -96.8), (32.7, -96.8), (None, None), (1.0, 2.0), (None, None)]
    # Unknown street: falls back to the city.
    assert asked == ["9 Nowhere Ln, Dallas, TX, US", "Dallas, TX, US", "Plano, US"]


def test_same_trade_sites_and_news_are_typed():
    from spotted.analysis import source_type

    cw = category_words(profile())
    t = lambda d: source_type(d, f"https://{d}/x", "petallane.example", [], cw)  # noqa: E731
    assert t("estrellasflowershop.com") == "competitor_site"  # a florist's own site, even unnamed
    assert t("cbsnews.com") == "publication"
    assert t("magicpin.com") == "directory"
    assert t("1800flowers.com") == "marketplace"  # marketplaces are checked before the trade-word rule
