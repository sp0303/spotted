"""Recommendations engine (build step 5): evidence-first actions from the report's numbers.

Every rule reads only what this audit observed (foundation checks, AI answers, search and listings results)
and writes the evidence into the recommendation: counts, the questions, the domains, the checks. Rules never
claim that a source caused a recommendation; citation patterns are "a pattern we see" (plan section 7).
Generic SEO advice ("write more blogs", "add FAQ schema") is never produced without a finding behind it.

Input is the report sections built by report.py (plain dicts, any section may be missing or unavailable).
Output: a list of recommendation dicts, each with a stable `rule_key` so the Action Center can keep the
owner's status across re-runs.
"""

from collections.abc import Iterable

CATEGORIES = ("indexing", "crawler_access", "rendering", "citation_source", "entity_brand", "recommendation_evidence",
              "content_gap", "reviews", "listings_voice", "agent_readiness", "platform_specific", "measurement")
PRIORITIES = ("high", "medium", "low")
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITIES)}

# Engines whose index a platform's answers draw on (documented behaviour, plan sections 17 and 21).
ENGINE_FOR_PLATFORM = {
    "gemini_search": "Google", "gemini_maps": "Google Maps", "google_ai_mode": "Google",
    "chatgpt": "Bing", "copilot": "Bing", "perplexity": "Perplexity's own index",
}

LISTING_NAMES = {
    "google_business_profile": "Google Business Profile", "gbp": "Google Business Profile",
    "bing_places": "Bing Places", "apple_maps": "Apple Business Connect (Apple Maps)",
    "apple_business_connect": "Apple Business Connect (Apple Maps)", "yelp": "Yelp", "facebook": "Facebook",
}
HIGH_PRIORITY_LISTINGS = {"google_business_profile", "gbp"}


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def _quote_list(items: Iterable[str], limit: int = 3) -> str:
    items = [i for i in items if i]
    shown = [f'"{i}"' for i in items[:limit]]
    more = len(items) - len(shown)
    text = ", ".join(shown)
    return text + (f" and {more} more" if more > 0 else "")


def _names(items: Iterable[str], limit: int = 3) -> str:
    items = [i for i in items if i]
    shown = items[:limit]
    more = len(items) - len(shown)
    if not shown:
        return ""
    text = shown[0] if len(shown) == 1 else ", ".join(shown[:-1]) + " and " + shown[-1]
    return text + (f" (and {more} more)" if more > 0 else "")


def _rec(rule_key: str, category: str, priority: str, title: str, why: str, how: list[str], effort: str,
         evidence: list[dict], confidence: str = "medium", best_practice: bool = False,
         link: str | None = None) -> dict:
    assert category in CATEGORIES and priority in PRIORITIES
    return {"rule_key": rule_key, "category": category, "priority": priority, "title": title, "why": why,
            "how": how, "effort": effort, "confidence": confidence, "is_best_practice": best_practice,
            "evidence": evidence, "link": link}


# ---------------------------------------------------------------------------
# Foundations
# ---------------------------------------------------------------------------

def _checks(foundations: dict, check_type: str, statuses: tuple[str, ...]) -> list[dict]:
    return [c for c in foundations.get("checks") or []
            if c.get("check_type") == check_type and c.get("status") in statuses]


def _check_ev(c: dict) -> dict:
    return {"kind": "foundation_check", "check_type": c.get("check_type"), "status": c.get("status"),
            "target": c.get("target"), "summary": c.get("summary")}


def foundation_rules(f: dict, ai_named_total: int | None) -> list[dict]:
    if not f or not f.get("available"):
        return []
    out = []
    link = "checks"

    blocked = f.get("blocked_crawlers") or []
    for c in _checks(f, "cdn_waf", ("issue",)):
        names = [b["token"] for b in blocked] or []
        out.append(_rec(
            "foundations:crawler_blocked", "crawler_access", "high",
            "Let search and AI crawlers reach your website",
            f"Our test requests suggest these crawlers can't read your homepage: {_names(names, 6) or 'see the check'}. "
            f"We found: {c.get('summary')} If a crawler can't read your site, the assistant it feeds can't quote it.",
            [c.get("fix") or "Allow these crawlers in robots.txt and in your firewall or CDN bot settings.",
             "Only allow the search and answer crawlers you want; training crawlers are a separate choice.",
             "Run the website checks again to confirm they get the normal page."],
            "low", [_check_ev(c)] + [{"kind": "crawler", "token": b["token"], "result": b.get("result"),
                                       "robots": b.get("robots")} for b in blocked],
            confidence="medium", link=link))

    for c in _checks(f, "robots_txt", ("issue",)):
        out.append(_rec("foundations:robots_txt", "crawler_access", "high", "Fix your robots.txt file",
                        f"{c.get('summary')}",
                        [c.get("fix") or "Correct the rule shown in the evidence.",
                         "Run the website checks again."], "low", [_check_ev(c)], confidence="high", link=link))
    for c in _checks(f, "robots_txt", ("warning",)):
        out.append(_rec("foundations:robots_txt_lines", "crawler_access", "low",
                        "Tidy up lines crawlers can't read in robots.txt", f"{c.get('summary')}",
                        [c.get("fix") or "Check the lines listed in the evidence for typos."], "low", [_check_ev(c)],
                        confidence="high", link=link))

    noindex = _checks(f, "noindex", ("issue",))
    if noindex:
        pages = [c.get("target") for c in noindex]
        out.append(_rec("foundations:noindex", "indexing", "high",
                        "Remove the 'don't list this page' tag from your pages",
                        f"{_plural(len(pages), 'page')} tell search engines not to list them: "
                        f"{_names(pages, 4)}. Pages search engines skip can't be found by AI assistants that search "
                        "the web either.",
                        [noindex[0].get("fix") or "Remove the noindex meta tag or X-Robots-Tag header from these pages.",
                         "If you use a site builder or SEO plugin, look for a 'hide from search engines' setting.",
                         "Run the website checks again."],
                        "low", [_check_ev(c) for c in noindex], confidence="high", link=link))

    for status, prio in (("issue", "high"), ("warning", "low")):
        for c in _checks(f, "http_status", (status,)):
            out.append(_rec(f"foundations:http_status:{status}", "indexing", prio,
                            "Fix how your homepage loads" if status == "issue" else "Tidy up your homepage redirects",
                            f"{c.get('summary')}", [c.get("fix") or "See the check for details."],
                            "medium" if status == "issue" else "low", [_check_ev(c)], confidence="high", link=link))

    sitemap = _checks(f, "sitemap", ("issue", "warning"))
    if sitemap:
        c = sitemap[0]
        out.append(_rec("foundations:sitemap", "indexing", "medium", "Give search engines a working sitemap",
                        f"{c.get('summary')} A sitemap is the list of pages you hand to Google and Bing so they "
                        "find all of them.",
                        [c.get("fix") or "Create a sitemap (most site builders and SEO plugins do this for you).",
                         "Add a 'Sitemap:' line to robots.txt and submit it in Google Search Console and Bing "
                         "Webmaster Tools."], "low", [_check_ev(c) for c in sitemap], confidence="high", link=link))

    for status, prio in (("issue", "high"), ("warning", "medium")):
        render = _checks(f, "js_render", (status,))
        if render:
            c = render[0]
            out.append(_rec(f"foundations:js_render:{status}", "rendering", prio,
                            "Put your key information in the page itself, not only in JavaScript",
                            f"{c.get('summary')} Most AI crawlers read the page without running JavaScript.",
                            [c.get("fix") or "Ask your web developer or platform to render this text on the server.",
                             "Run the website checks again."], "medium", [_check_ev(c)], confidence="medium",
                            link=link))

    canon = _checks(f, "canonical", ("issue",))
    if canon:
        out.append(_rec("foundations:canonical", "indexing", "medium", "Point your canonical tags at your own pages",
                        f"{_plural(len(canon), 'page')} point search engines to a different address: "
                        f"{_names([c.get('target') for c in canon], 3)}. {canon[0].get('summary')}",
                        [canon[0].get("fix") or "Set each page's canonical tag to its own address on your site."],
                        "low", [_check_ev(c) for c in canon], confidence="high", link=link))

    not_verified = [c for c in f.get("checks") or [] if c.get("check_type") in ("google_index", "bing_index")
                    and c.get("status") == "not_verified"]
    if not_verified:
        unseen = ai_named_total == 0
        out.append(_rec("foundations:webmaster_tools", "indexing", "medium" if unseen else "low",
                        "Check that Google and Bing have listed your site",
                        "We can't see whether Google and Bing have listed your pages until you connect their free "
                        "webmaster tools. Bing's index also feeds Copilot and ChatGPT search."
                        + (" None of the AI answers we collected named you, so this is worth confirming." if unseen
                           else ""),
                        [c.get("fix") for c in not_verified if c.get("fix")] or
                        ["Verify your site in Google Search Console and Bing Webmaster Tools."],
                        "medium", [_check_ev(c) for c in not_verified], confidence="low", link=link))

    for c in _checks(f, "webmcp", ("opportunity",)):
        out.append(_rec("foundations:webmcp", "agent_readiness", "low", "Later: offer actions AI agents can use",
                        f"{c.get('summary')}", [c.get("fix") or "No action needed today."], "high", [_check_ev(c)],
                        confidence="low", best_practice=True, link=link))
    return out


# ---------------------------------------------------------------------------
# AI answers
# ---------------------------------------------------------------------------

def ai_rules(vis: dict, comp: dict, cit: dict, acc: dict, business: dict) -> list[dict]:
    out = []
    if not vis or not vis.get("available"):
        return out
    name = business.get("name") or "your business"
    totals = vis.get("totals") or {}

    for p in vis.get("platforms") or []:
        answers, named = p.get("answers") or 0, p.get("named") or 0
        if not answers:
            continue
        key, label = p.get("key"), p.get("label") or p.get("key")
        missed = p.get("missed_prompts") or []
        instead = [n["name"] for n in p.get("named_instead") or []]
        ev = [{"kind": "ai_platform", "platform": key, "answers": answers, "named": named,
               "recommended": p.get("recommended", 0)}] + [{"kind": "prompt", "text": t} for t in missed[:5]]
        if not p.get("search_enabled", True):
            if named == 0:
                out.append(_rec(
                    f"ai:model_knowledge:{key}", "entity_brand", "low",
                    f"{label} doesn't know you from memory yet",
                    f"With web search off, {label} named you in 0 of {answers} answers (API view). This shows what "
                    "the AI learned in the past. It builds slowly, over months and years of being mentioned online, "
                    "and isn't something a quick fix changes.",
                    ["Focus on the actions that help the live-search answers first; they can change within weeks.",
                     "Keep earning genuine mentions: local press, directories you already appear in, reviews."],
                    "high", ev, confidence="medium"))
            continue
        if named == 0:
            prio = "high"
        elif named * 2 < answers:
            prio = "medium"
        else:
            continue
        engine = ENGINE_FOR_PLATFORM.get(key)
        why = (f"{label} named you in {named} of {answers} answers (API view). "
               + (f"Questions where you weren't named: {_quote_list(missed)}. " if missed else "")
               + (f"It named {_names(instead)} instead." if instead else ""))
        if key == "gemini_maps":
            out.append(_rec(
                f"ai:not_named:{key}", "listings_voice", prio, "Get your Google Maps listing in shape",
                why + " Answers grounded in Google Maps draw on Google Business Profile listings.",
                ["Search for your business on Google Maps and claim it if it isn't yours yet "
                 "(business.google.com).",
                 "Make the categories, services, hours and service area match what you confirmed in your profile.",
                 "Re-run the same questions afterwards and compare."],
                "medium", ev, confidence="medium"))
        else:
            how = []
            if engine and engine not in ("Perplexity's own index",):
                how.append(f"Fix any website-check issues first; {label} answers come from searching {engine}.")
            if missed:
                how.append(f"Make sure your site has a page that plainly says you offer what was asked "
                           f"({_quote_list(missed, 2)}), with your city in the text.")
            how.append("Re-run the same questions afterwards and compare.")
            out.append(_rec(f"ai:not_named:{key}", "platform_specific", prio,
                            f"{label} isn't naming you" if named == 0 else f"{label} rarely names you",
                            why, how, "medium", ev, confidence="low"))

    # Competitors named more often than the client, and what the answers praise them for.
    client_answers = (comp or {}).get("client", {}).get("answers", totals.get("named", 0)) if comp else 0
    ahead = [c for c in (comp or {}).get("others") or [] if (c.get("answers") or 0) >= 2
             and (c.get("answers") or 0) > client_answers]
    if ahead:
        top = ahead[:3]
        attrs = []
        for c in top:
            for a in c.get("attributes") or []:
                if a not in attrs:
                    attrs.append(a)
        listing = "; ".join(f"{c['name']} in {c['answers']}" for c in top)
        why = (f"Out of {totals.get('answers', 0)} answers, other businesses were named more often than you "
               f"({client_answers}): {listing}.")
        how = []
        if attrs:
            why += f" The answers describe them with words like {_quote_list(attrs, 5)}."
            how.append("Where those things are true for you too, say so clearly on your site and listings "
                       "(only what's true).")
        how += ["Look at the answers on the AI page to see how each one is described.",
                "Check where they're listed (see the citation gaps) and whether you're there too."]
        out.append(_rec("ai:competitors_ahead", "recommendation_evidence", "medium",
                        "See what AI says about the businesses it names instead of you", why, how, "low",
                        [{"kind": "competitor", "name": c["name"], "answers": c["answers"],
                          "attributes": c.get("attributes") or []} for c in top], confidence="low"))

    # Citation gaps: sources cited alongside competitors, never alongside the client.
    for g in (cit or {}).get("gaps") or []:
        if len([r for r in out if r["category"] == "citation_source"]) >= 5:
            break
        domain, kind, n = g.get("domain"), g.get("type"), g.get("answers") or 0
        if not domain or not n:
            continue
        comps = g.get("competitors") or []
        why = (f"Pattern we see: {domain} was cited in {_plural(n, 'answer')} that named "
               f"{_names(comps) or 'other businesses'} but not you"
               + (f", for questions like {_quote_list(g.get('prompts') or [], 2)}" if g.get("prompts") else "")
               + ". It was never cited in an answer that named you. We can't tell whether this site influenced "
                 "the answer.")
        how = {
            "directory": [f"Search {domain} for your business; claim or create your free listing.",
                          "Use the same name, address, phone and hours as your confirmed profile."],
            "review_site": [f"Check whether you're listed on {domain}; claim the listing if you are.",
                            "Invite real customers to leave a review there. Never buy or write fake reviews."],
            "publication": [f"Open the cited article on {domain} and see which businesses it features and why.",
                            "If you fit, contact the writer or editor with a short, factual note about your "
                            "business for future updates."],
            "social": [f"Make sure your {domain} profile exists, has your current details and is active."],
            "forum": [f"Read the cited {domain} thread. If it's appropriate, take part honestly as the business "
                      "owner; don't post fake recommendations."],
            "marketplace": [f"Consider whether listing on {domain} makes sense for you; it's where the answers "
                            "pointed customers."],
            "maps": ["Check your map listings (Google Business Profile, Apple Maps, Bing Places) are claimed "
                     "and complete."],
        }.get(kind, [f"Open the cited page on {domain} and see why those businesses are on it.",
                     "If there's a legitimate way to be included (a list, a directory, a feature), apply."])
        out.append(_rec(f"citation:{domain}", "listings_voice" if kind == "maps" else "citation_source",
                        "medium" if n >= 2 else "low", f"Look into {domain}", why, how, "medium",
                        [{"kind": "citation", "domain": domain, "type": kind, "answers": n, "competitors": comps,
                          "prompts": g.get("prompts") or [], "url": g.get("example_url")}],
                        confidence="low"))

    if cit and (cit.get("answers_with_sources") or 0) > 0 and (cit.get("own_site_cited") or 0) == 0:
        n = cit["answers_with_sources"]
        out.append(_rec("citation:own_site_never", "content_gap", "medium",
                        "Give AI assistants a page of yours worth citing",
                        f"{_plural(n, 'answer')} listed the websites they used, and none of them was yours "
                        f"({business.get('domain') or 'your site'}).",
                        ["Check the website checks first: a blocked or JavaScript-only page can't be cited.",
                         "Make sure each main service has its own page that states what you offer, where, and how "
                         "to order or book, in plain text.",
                         "Re-run the same questions afterwards and compare."],
                        "medium", [{"kind": "metric", "metric": "own_site_cited", "numerator": 0, "denominator": n}],
                        confidence="low"))

    # Wrong facts: grouped by fact type.
    by_fact: dict[str, list[dict]] = {}
    for w in (acc or {}).get("wrong") or []:
        for fact, detail in (w.get("facts") or {}).items():
            by_fact.setdefault(fact, []).append({"platform": w.get("platform"), "prompt": w.get("prompt"), **detail})
    for fact, rows in by_fact.items():
        said = list(dict.fromkeys(r.get("said") for r in rows if r.get("said")))
        confirmed = rows[0].get("confirmed") or []
        out.append(_rec(f"accuracy:{fact}", "entity_brand", "high", f"Correct your {fact} where AI finds it",
                        f"{_plural(len(rows), 'answer')} gave {name}'s {fact} as {_quote_list(said)}; "
                        f"your confirmed {fact} is {_quote_list(confirmed)}.",
                        [f"Update your {fact} on your website, Google Business Profile, Bing Places, Apple Maps, "
                         "Yelp and Facebook so they all match.",
                         "Search the wrong value to find old listings that still show it, and correct or remove them.",
                         "Re-run the questions that name you to check."],
                        "medium", [{"kind": "wrong_fact", "fact": fact, **r} for r in rows], confidence="high"))
    return out


# ---------------------------------------------------------------------------
# Search and listings
# ---------------------------------------------------------------------------

def search_rules(search: dict) -> list[dict]:
    out = []
    if not search or not search.get("available"):
        return out
    for item in search.get("listings") or []:
        plat = str(item.get("platform") or "")
        if not plat:
            continue
        label = LISTING_NAMES.get(plat, plat.replace("_", " ").title())
        status = item.get("status")
        if status == "not_found":
            out.append(_rec(f"listing:{plat}", "listings_voice",
                            "high" if plat in HIGH_PRIORITY_LISTINGS else "medium",
                            f"Create or claim your {label} listing",
                            f"We couldn't find a {label} listing for your business. Maps apps and voice assistants "
                            "answer from listings like this one.",
                            [f"Search for your business on {label}; claim it if it exists, create it if not.",
                             "Use the same name, address, phone and hours as your confirmed profile."],
                            "medium", [{"kind": "listing", "platform": plat, "status": status}], confidence="medium"))
        elif status == "found" and item.get("issues"):
            issues = [str(i) for i in item["issues"]]
            out.append(_rec(f"listing_issues:{plat}", "listings_voice", "medium", f"Fix your {label} listing",
                            f"Your {label} listing has {_plural(len(issues), 'problem')}: {'; '.join(issues[:4])}.",
                            [f"Sign in to {label} and correct the details listed.",
                             "Make them match your confirmed profile."],
                            "low", [{"kind": "listing", "platform": plat, "status": status, "issues": issues,
                                     "url": item.get("url")}], confidence="medium"))

    queries = search.get("queries") or []
    maps_checked = [q for q in queries if q.get("maps_checked")]
    maps_missing = [q for q in maps_checked if q.get("maps_rank") is None]
    if maps_checked and maps_missing and len(maps_missing) * 2 >= len(maps_checked):
        shown = list(dict.fromkeys(n for q in maps_missing for n in (q.get("maps_results") or [])[:3]))
        out.append(_rec("search:maps_missing", "listings_voice", "medium", "Show up in map results for your searches",
                        f"You weren't in the map results for {len(maps_missing)} of {len(maps_checked)} searches "
                        f"({_quote_list([q['query'] for q in maps_missing], 2)})."
                        + (f" The map showed {_names(shown)}." if shown else ""),
                        ["Check your Google Business Profile category matches what customers search for.",
                         "Make sure your address or service area covers the area searched."],
                        "medium", [{"kind": "search", "surface": "maps", "query": q["query"],
                                    "results": (q.get("maps_results") or [])[:5]} for q in maps_missing[:5]],
                        confidence="medium"))
    web_checked = [q for q in queries if q.get("web_checked")]
    web_missing = [q for q in web_checked if q.get("web_rank") is None]
    if web_checked and web_missing and len(web_missing) * 2 >= len(web_checked):
        doms = list(dict.fromkeys(d for q in web_missing for d in (q.get("web_results") or [])[:5]))
        out.append(_rec("search:web_missing", "content_gap", "medium", "Show up in web results for your searches",
                        f"Your site wasn't in the web results we checked for {len(web_missing)} of "
                        f"{len(web_checked)} searches ({_quote_list([q['query'] for q in web_missing], 2)})."
                        + (f" Sites that did appear include {_names(doms, 4)}." if doms else ""),
                        ["Check the website checks for anything stopping search engines from listing you.",
                         "Make sure a page on your site matches each search: the service and the city in its title "
                         "and text."],
                        "medium", [{"kind": "search", "surface": "web", "query": q["query"],
                                    "results": (q.get("web_results") or [])[:5]} for q in web_missing[:5]],
                        confidence="medium"))
    return out


def press_rules(search: dict, cit: dict) -> list[dict]:
    """Publications that wrote about competitors but not the client, cross-referenced with AI-cited domains."""
    press = (search or {}).get("press") or {}
    if not search or not search.get("available") or not press.get("available"):
        return []
    gaps = {g["domain"]: g for g in (cit or {}).get("gaps") or [] if g.get("domain")}
    cited = {s["domain"]: s.get("answers", 0) for s in (cit or {}).get("top_sources") or [] if s.get("domain")}
    out = []
    for domain in (press.get("competitor_only_sources") or [])[:8]:
        arts = [a for a in press.get("competitor_articles") or [] if a.get("domain") == domain]
        comps = list(dict.fromkeys(a["competitor"] for a in arts if a.get("competitor")))
        source = next((a["source"] for a in arts if a.get("source")), domain)
        titles = [a["title"] for a in arts]
        if domain in gaps:
            prio = "high"
            ai = (f" AI answers also cited {domain} in {_plural(gaps[domain]['answers'], 'answer')} that named "
                  "other businesses but not you.")
        elif cited.get(domain):
            prio = "medium"
            ai = f" AI answers cited {domain} in {_plural(cited[domain], 'answer')}."
        else:
            prio = "low"
            ai = ""
        why = (f"Pattern we see: {source} ({domain}) has written about "
               f"{_names(comps) or 'your competitors'} but we found nothing about you"
               + (f", for example {_quote_list(titles, 2)}" if titles else "") + "." + ai
               + " Coverage isn't a guarantee of being recommended, and we can't tell whether it influenced any answer.")
        out.append(_rec(f"press:{domain}", "citation_source", prio, f"Get on {source}'s radar", why,
                        [f"Read the {source} articles listed in the evidence and note what made those businesses "
                         "worth writing about.",
                         "If you have something genuinely newsworthy (an anniversary, a local event, an unusual "
                         "service), send the writer or editor a short, factual note.",
                         "Never pay for fake reviews or disguised advertising."],
                        "high", [{"kind": "press", "domain": domain, "source": source, "competitors": comps,
                                  "articles": arts[:5], "ai_cited_gap": domain in gaps,
                                  "ai_cited_answers": gaps[domain]["answers"] if domain in gaps else cited.get(domain, 0)}],
                        confidence="low"))
    return out


# ---------------------------------------------------------------------------

def build_recommendations(sections: dict) -> list[dict]:
    """All rules over the report sections, de-duplicated by rule_key and sorted by priority."""
    vis = sections.get("visibility") or {}
    named_total = (vis.get("totals") or {}).get("named") if vis.get("available") else None
    recs = (foundation_rules(sections.get("foundations") or {}, named_total)
            + ai_rules(vis, sections.get("competitors") or {}, sections.get("citations") or {},
                       sections.get("accuracy") or {}, sections.get("business") or {})
            + search_rules(sections.get("search") or {})
            + press_rules(sections.get("search") or {}, sections.get("citations") or {}))
    # A publication covered by the press rule replaces its plain citation-gap rule (same domain, more evidence).
    press_keys = {r["rule_key"].removeprefix("press:") for r in recs if r["rule_key"].startswith("press:")}
    recs = [r for r in recs if not (r["rule_key"].startswith("citation:") and
                                    r["rule_key"].removeprefix("citation:") in press_keys)]
    # A publication that already wrote about the client (Google News) isn't a gap, even if this AI run didn't
    # happen to cite it next to them.
    press = (sections.get("search") or {}).get("press") or {}
    covered = {d.lower().removeprefix("www.") for d in press.get("client_sources") or []}
    recs = [r for r in recs if not (r["rule_key"].startswith("citation:") and
                                    r["rule_key"].removeprefix("citation:") in covered)]
    if recs and vis.get("available"):
        recs.append(_rec("measure:rerun", "measurement", "low", "Re-run the same questions after your fixes",
                         f"This report is based on {_plural(vis.get('totals', {}).get('answers', 0), 'answer')} "
                         "(API view). Answers change from run to run, so compare the same questions on the same "
                         "assistants after you've made changes, ideally a few weeks later.",
                         ["Mark actions done as you finish them.",
                          "Run the AI check again with the same questions and compare in this report."],
                         "low", [{"kind": "audit", "audit_id": vis.get("audit_id")}], confidence="high"))
    seen, out = set(), []
    for r in recs:
        if r["rule_key"] in seen:
            continue
        seen.add(r["rule_key"])
        out.append(r)
    return sorted(out, key=lambda r: PRIORITY_ORDER[r["priority"]])  # stable: rule order within a priority
