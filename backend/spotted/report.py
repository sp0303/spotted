"""Report numbers (build step 4) and the Action Center store (build step 5).

The report combines the latest of each audit a business has: foundation checks, the AI run (and the one
before it, for a before/after comparison) and the search/listings check. It shows counts, never
precise-looking percentages (plan section 24). Numbers are saved per audit in the `audit_metrics`
collection (rows shaped like the schema's audit_metrics table) so later runs can be compared.

Recommendations become actions in the `actions` collection, one per (business, rule_key), so the owner's
status (not_started / in_progress / done / dismissed) survives re-generating the report.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from .analysis import retype_citations
from . import airun, repo
from .recommendations import PRIORITY_ORDER, build_recommendations
from .repo import col

ACTION_STATUSES = ("not_started", "in_progress", "done", "dismissed")
FINISHED = ("complete", "partial")
SMALL_CHANGE = 2  # answers; a change this size or smaller is within normal run-to-run variation
NON_VISIBILITY_INTENTS = ("branded", "accuracy")

LIMITATIONS = [
    "API view: answers come from the AI companies' developer APIs, which can differ from what their apps show.",
    "Answers change from run to run, so small numbers are a first look, not a score.",
    "A site cited in an answer is something we saw, not proof it caused the answer.",
]
COMING_SOON = ["ChatGPT, Claude, Copilot and Google AI Mode answers (until their keys are added)",
               "Answers as seen in the consumer apps, with screenshots",
               "Verified Google and Bing indexing (Search Console / Bing Webmaster Tools)"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# AI numbers
# ---------------------------------------------------------------------------

def _visibility_runs(audit: dict) -> tuple[dict, list[dict]]:
    prompts = {p["id"]: p for p in audit.get("prompts", [])}
    ok = [r for r in audit.get("runs", []) if r.get("status") == "done" and r.get("prompt_id") in prompts]
    return prompts, [r for r in ok if prompts[r["prompt_id"]].get("intent") not in NON_VISIBILITY_INTENTS]


def ai_sections(audit: dict, summary: dict) -> dict:
    """Visibility, competitor share, citation gaps and accuracy from one AI run (raw document + its summary)."""
    prompts, runs = _visibility_runs(audit)
    labels = {p["key"]: p["label"] for p in summary.get("platforms", [])}

    platforms = []
    for p in summary.get("platforms", []):
        rs = [r for r in runs if r.get("platform_key") == p["key"]]
        missed = [r for r in rs if not any(m.get("is_client") for m in r.get("mentions", []))]
        instead = Counter(m["entity_name"] for r in missed for m in r.get("mentions", []) if not m.get("is_client"))
        platforms.append({
            **{k: p.get(k) for k in ("key", "label", "search_enabled", "answers", "named", "recommended",
                                     "best_position", "own_site_cited", "errors")},
            "missed_prompts": list(dict.fromkeys(prompts[r["prompt_id"]]["text"] for r in missed)),
            "named_instead": [{"name": n, "answers": c} for n, c in instead.most_common(3)],
        })
    totals = {k: sum(p.get(k) or 0 for p in platforms) for k in ("answers", "named", "recommended",
                                                                   "own_site_cited", "errors")}
    visibility = {"available": True, "audit_id": audit["_id"], "status": audit.get("status"),
                  "checked_at": summary.get("finished_at") or summary.get("started_at"),
                  "platforms": platforms, "totals": totals}

    # Share of voice: answers that name each business, client first.
    client_runs = [r for r in runs if any(m.get("is_client") for m in r.get("mentions", []))]
    client_ids = {r["id"] for r in client_runs}
    attrs: dict[str, Counter] = defaultdict(Counter)
    for r in runs:
        for m in r.get("mentions", []):
            if not m.get("is_client"):
                for a in m.get("attributes") or []:
                    attrs[m.get("normalized") or m["entity_name"]][a.strip().lower()] += 1
    norm_of = {}
    for r in runs:
        for m in r.get("mentions", []):
            norm_of.setdefault(m["entity_name"], m.get("normalized") or m["entity_name"])
    others = []
    for c in summary.get("competitors", [])[:8]:
        key = norm_of.get(c["name"], c["name"])
        others.append({**c, "attributes": [a for a, _ in attrs[key].most_common(4)]})
    competitors = {
        "available": True, "answers": len(runs),
        "client": {"answers": len(client_runs),
                   "recommended": sum(1 for r in client_runs if any(m.get("is_client") and m.get("kind") == "recommended"
                                                                     for m in r.get("mentions", [])))},
        "others": others,
    }

    # Citation gaps: domains cited in answers naming a competitor but not the client, never with the client.
    client_domains = {c["domain"] for r in client_runs for c in r.get("citations", [])}
    gap: dict[str, dict] = {}
    for r in runs:
        names = [m["entity_name"] for m in r.get("mentions", []) if not m.get("is_client")]
        if r["id"] in client_ids or not names:
            continue
        for c in r.get("citations", []):
            d = c.get("domain")
            if not d or d in client_domains or c.get("source_type") in ("own_site", "competitor_site"):
                continue
            g = gap.setdefault(d, {"domain": d, "type": c.get("source_type"), "runs": set(), "competitors": Counter(),
                                   "prompts": [], "platforms": [], "example_url": c.get("url")})
            if r["id"] in g["runs"]:
                continue
            g["runs"].add(r["id"])
            g["competitors"].update(names)
            text = prompts[r["prompt_id"]]["text"]
            if text not in g["prompts"]:
                g["prompts"].append(text)
            label = labels.get(r["platform_key"], r["platform_key"])
            if label not in g["platforms"]:
                g["platforms"].append(label)
    gaps = sorted(({"domain": g["domain"], "type": g["type"], "answers": len(g["runs"]),
                    "competitors": [n for n, _ in g["competitors"].most_common(3)], "prompts": g["prompts"][:3],
                    "platforms": g["platforms"], "example_url": g["example_url"]} for g in gap.values()),
                  key=lambda g: (-g["answers"], g["domain"]))
    with_sources = [r for r in runs if r.get("citations")]
    citations = {
        "available": True,
        "answers_with_sources": len(with_sources),
        "own_site_cited": sum(1 for r in runs if any(c.get("source_type") == "own_site" for c in r.get("citations", []))),
        "client_answers_with_sources": sum(1 for r in client_runs if r.get("citations")),
        "gaps": gaps[:10],
        "top_sources": summary.get("sources", [])[:10],
    }

    branded = [r for r in audit.get("runs", []) if r.get("status") == "done" and r.get("prompt_id") in prompts
               and prompts[r["prompt_id"]].get("intent") in NON_VISIBILITY_INTENTS]
    accuracy = {
        "available": True,
        "branded_answers": len(branded),
        "answers_naming_you": sum(1 for r in audit.get("runs", []) if r.get("status") == "done"
                                  and any(m.get("is_client") for m in r.get("mentions", []))),
        "wrong": summary.get("wrong_facts", []),
    }
    return {"visibility": visibility, "competitors": competitors, "citations": citations, "accuracy": accuracy}


def ai_metric_rows(audit: dict, sections: dict) -> list[dict]:
    """audit_metrics rows: (metric, platform, numerator, denominator, detail); platform None = all platforms."""
    rows = []
    for p in sections["visibility"]["platforms"]:
        for metric, num in (("named", p["named"]), ("recommended", p["recommended"]),
                            ("own_site_cited", p["own_site_cited"])):
            rows.append({"metric": metric, "platform": p["key"], "surface": "api", "numerator": num or 0,
                         "denominator": p["answers"] or 0, "detail": None})
    t = sections["visibility"]["totals"]
    for metric in ("named", "recommended", "own_site_cited"):
        rows.append({"metric": metric, "platform": None, "surface": "api", "numerator": t[metric],
                     "denominator": t["answers"], "detail": None})
    total = sections["competitors"]["answers"]
    for c in sections["competitors"]["others"][:5]:
        rows.append({"metric": "competitor_named", "platform": None, "surface": "api", "numerator": c["answers"],
                     "denominator": total, "detail": {"name": c["name"]}})
    rows.append({"metric": "wrong_facts", "platform": None, "surface": "api",
                 "numerator": len(sections["accuracy"]["wrong"]),
                 "denominator": sections["accuracy"]["answers_naming_you"], "detail": None})
    rows.append({"metric": "citation_gaps", "platform": None, "surface": "api",
                 "numerator": len(sections["citations"]["gaps"]), "denominator": sections["citations"]["answers_with_sources"],
                 "detail": {"domains": [g["domain"] for g in sections["citations"]["gaps"]]}})
    return rows


def compare(current: dict, previous: dict, current_audit: dict, previous_audit: dict) -> dict:
    """Before/after between two AI runs of the same business: counts only, with the variation caveat."""
    before = {p["key"]: p for p in previous["visibility"]["platforms"]}
    after = {p["key"]: p for p in current["visibility"]["platforms"]}
    rows = []
    for key in list(after) + [k for k in before if k not in after]:
        b, a = before.get(key), after.get(key)
        row = {"key": key, "label": (a or b)["label"],
               "before": None if b is None else {k: b[k] for k in ("answers", "named", "recommended", "own_site_cited")},
               "after": None if a is None else {k: a[k] for k in ("answers", "named", "recommended", "own_site_cited")}}
        if a and b:
            row["named_change"] = a["named"] - b["named"]
            row["small"] = abs(row["named_change"]) <= SMALL_CHANGE
        rows.append(row)
    tb, ta = previous["visibility"]["totals"], current["visibility"]["totals"]
    q_before = {p["text"].strip().lower() for p in previous_audit.get("prompts", [])}
    q_after = {p["text"].strip().lower() for p in current_audit.get("prompts", [])}
    change = ta["named"] - tb["named"]
    comp_before = {c["name"]: c["answers"] for c in previous["competitors"]["others"]}
    return {
        "available": True,
        "previous_audit_id": previous_audit["_id"],
        "previous_checked_at": _iso(previous_audit.get("finished_at") or previous_audit.get("created_at")),
        "same_questions": q_before == q_after,
        "same_platforms": set(before) == set(after),
        "totals": {"before": {k: tb[k] for k in ("answers", "named", "recommended", "own_site_cited")},
                   "after": {k: ta[k] for k in ("answers", "named", "recommended", "own_site_cited")},
                   "named_change": change, "small": abs(change) <= SMALL_CHANGE},
        "platforms": rows,
        "competitors": [{"name": c["name"], "before": comp_before.get(c["name"], 0), "after": c["answers"]}
                        for c in current["competitors"]["others"][:5]],
        "note": "Answers vary from run to run. A change of a few answers isn't evidence that anything improved or "
                "got worse, and we can't say a change was caused by an action you took. Look for the same "
                "direction over several runs of the same questions.",
    }


# ---------------------------------------------------------------------------
# Foundations and search sections
# ---------------------------------------------------------------------------

def foundations_section(f: dict | None) -> dict:
    if not f:
        return {"available": False}
    counts = Counter(c.get("status") for c in f.get("checks", []))
    issues = [{k: c.get(k) for k in ("check_type", "status", "summary", "fix", "target")}
              for c in f.get("checks", []) if c.get("status") in ("issue", "warning", "inconclusive")]
    blocked = [{"token": c["token"], "operator": c.get("operator"), "purpose": c.get("purpose"),
                "result": c.get("result"), "robots": c.get("robots")}
               for c in f.get("crawlers", []) if c.get("purpose") in ("search", "user_fetch")
               and not c.get("token_only")
               and (c.get("result") in ("likely_blocked", "verified_blocked") or c.get("robots") == "disallow")]
    order = {"issue": 0, "warning": 1, "inconclusive": 2}
    return {"available": True, "audit_id": f.get("audit_id"), "checked_at": f.get("checked_at"), "url": f.get("url"),
            "counts": {s: counts.get(s, 0) for s in ("issue", "warning", "inconclusive", "opportunity",
                                                       "not_verified", "pass")},
            "issues": sorted(issues, key=lambda c: order.get(c["status"], 9)),
            "blocked_crawlers": blocked, "checks": f.get("checks", [])}


def _int_or_none(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def search_section(doc: dict | None) -> dict:
    """The search/listings audit, read defensively: any field may be missing (it's written by another step)."""
    if not doc:
        return {"available": False}
    s = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    queries = []
    for q in s.get("queries") or []:
        if not isinstance(q, dict) or not q.get("query"):
            continue
        maps = q.get("maps") if isinstance(q.get("maps"), dict) else None
        web = q.get("web") if isinstance(q.get("web"), dict) else None
        queries.append({
            "query": str(q["query"]),
            "maps_checked": maps is not None,
            "maps_rank": _int_or_none((maps or {}).get("client_rank")),
            "maps_results": [str(x) for x in (maps or {}).get("results") or [] if x][:10],
            "web_checked": web is not None,
            "web_rank": _int_or_none((web or {}).get("client_rank")),
            "web_results": [str(x.get("domain")) for x in (web or {}).get("results") or []
                            if isinstance(x, dict) and x.get("domain")][:10],
        })
    listings = [{"platform": str(x.get("platform")), "status": x.get("status") or "unknown", "url": x.get("url"),
                 "issues": [str(i) for i in x.get("issues") or []]}
                for x in s.get("listings") or [] if isinstance(x, dict) and x.get("platform")]
    return {
        "available": True, "audit_id": doc.get("_id"),
        "checked_at": _iso(s.get("checked_at") or doc.get("finished_at") or doc.get("created_at")),
        "queries": queries,
        "maps": {"checked": sum(q["maps_checked"] for q in queries),
                 "found": sum(1 for q in queries if q["maps_rank"] is not None)},
        "web": {"checked": sum(q["web_checked"] for q in queries),
                "found": sum(1 for q in queries if q["web_rank"] is not None)},
        "listings": listings,
        "coming_soon": [str(x) for x in s.get("coming_soon") or []],
        "press": press_section(s.get("press")),
    }


def site_domain(value) -> str:
    """'https://www.dmagazine.com/x' or 'www.dmagazine.com' -> 'dmagazine.com'."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    host = urlsplit(text if "//" in text else "//" + text).hostname or ""
    return host.removeprefix("www.")


def _articles(items, with_competitor: bool = False) -> list[dict]:
    out = []
    for a in items or []:
        if not isinstance(a, dict) or not (a.get("title") or a.get("url")):
            continue
        row = {"title": str(a.get("title") or a.get("url")), "source": str(a.get("source") or "") or None,
               "domain": site_domain(a.get("source_url")) or None, "url": a.get("url"),
               "published": str(a.get("published")) if a.get("published") else None}
        if with_competitor:
            row["competitor"] = str(a.get("competitor") or "") or None
        out.append(row)
    return out[:20]


def press_section(p) -> dict:
    """News coverage (Google News RSS) from the search step; optional, read defensively."""
    if not isinstance(p, dict):
        return {"available": False}
    return {
        "available": True,
        "client_articles": _articles(p.get("client_articles")),
        "category_articles": _articles(p.get("category_articles")),
        "competitor_articles": _articles(p.get("competitor_articles"), with_competitor=True),
        "client_sources": [d for d in (site_domain(x) for x in p.get("client_sources") or []) if d],
        "competitor_only_sources": [d for d in (site_domain(x) for x in p.get("competitor_only_sources") or []) if d],
    }


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

async def ensure_indexes(db: AsyncDatabase) -> None:
    await col(db, "actions").create_index([("business_id", ASCENDING), ("rule_key", ASCENDING)], unique=True)
    await col(db, "audit_metrics").create_index([("business_id", ASCENDING), ("kind", ASCENDING),
                                                 ("computed_at", DESCENDING)])


async def save_metrics(db: AsyncDatabase, audit_id: str, business_id: str, kind: str, rows: list[dict]) -> None:
    await col(db, "audit_metrics").update_one(
        {"_id": audit_id},
        {"$set": {"business_id": business_id, "kind": kind, "rows": rows, "computed_at": _now()}}, upsert=True)


async def _finished_ai_audits(db: AsyncDatabase, business_id: UUID, limit: int) -> list[dict]:
    cursor = col(db, "audits").find({"business_id": str(business_id), "config.kind": "ai_run",
                                     "status": {"$in": list(FINISHED)}}, sort=[("created_at", DESCENDING)],
                                    limit=limit)
    return [a async for a in cursor]


def _action_out(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = doc["_id"]
    for k in ("created_at", "updated_at", "status_changed_at", "last_seen_at"):
        if k in out:
            out[k] = _iso(out[k])
    return out


async def sync_actions(db: AsyncDatabase, business_id: str, recs: list[dict], source_audits: list[str]) -> list[dict]:
    """Upsert one action per rule_key. Status is never reset; actions no longer found are marked inactive."""
    actions = col(db, "actions")
    now = _now()
    keys = []
    for r in recs:
        keys.append(r["rule_key"])
        content = {k: r[k] for k in ("category", "priority", "title", "why", "how", "effort", "confidence",
                                     "is_best_practice", "evidence", "link")}
        await actions.update_one(
            {"business_id": business_id, "rule_key": r["rule_key"]},
            {"$set": {**content, "active": True, "last_seen_at": now, "source_audits": source_audits,
                      "updated_at": now},
             "$setOnInsert": {"_id": str(uuid4()), "status": "not_started", "status_changed_at": None,
                              "created_at": now}},
            upsert=True)
    await actions.update_many({"business_id": business_id, "rule_key": {"$nin": keys}, "active": True},
                              {"$set": {"active": False, "updated_at": now}})
    docs = [d async for d in actions.find({"business_id": business_id, "active": True})]
    order = {k: i for i, k in enumerate(keys)}
    docs.sort(key=lambda d: (PRIORITY_ORDER.get(d.get("priority"), 9), order.get(d["rule_key"], 999)))
    return [_action_out(d) for d in docs]


async def update_action_status(db: AsyncDatabase, business_id: str, action_id: str, status: str) -> dict | None:
    now = _now()
    doc = await col(db, "actions").find_one_and_update(
        {"_id": action_id, "business_id": business_id},
        {"$set": {"status": status, "status_changed_at": now, "updated_at": now}},
        return_document=True)
    return None if doc is None else _action_out(doc)


async def list_actions(db: AsyncDatabase, business_id: str) -> list[dict]:
    docs = [d async for d in col(db, "actions").find({"business_id": business_id, "active": True})]
    docs.sort(key=lambda d: (PRIORITY_ORDER.get(d.get("priority"), 9), d.get("created_at") or _now()))
    return [_action_out(d) for d in docs]


def action_counts(actions: list[dict]) -> dict:
    counts = Counter(a.get("priority") for a in actions)
    status = Counter(a.get("status") for a in actions)
    return {"total": len(actions), "high": counts.get("high", 0), "medium": counts.get("medium", 0),
            "low": counts.get("low", 0), **{s: status.get(s, 0) for s in ACTION_STATUSES}}


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def _business(stored) -> dict:
    p = stored.profile
    where = airun.target_point(p)
    return {"id": stored.business_id, "name": p.name.value, "domain": p.domain, "website_url": p.website_url,
            "category": p.category.value if p.category else None, "city": where.get("city"),
            "confirmed": stored.confirmed,
            "competitors": [c.value for c in p.suggested_competitors]}


def _safe_summary(audit: dict | None) -> dict | None:
    if audit is None:
        return None
    try:
        return airun.summarize(audit)
    except Exception:  # an unknown platform key or a malformed run shouldn't take the report down
        return None


async def build_report(db: AsyncDatabase, business_id: UUID) -> dict | None:
    stored = await repo.get_profile(db, business_id)
    if stored is None:
        return None
    await ensure_indexes(db)
    bid = str(business_id)
    business = _business(stored)

    foundations = foundations_section(await repo.latest_foundations(db, business_id))

    latest = await airun.latest_ai_audit(db, business_id)
    running = latest is not None and latest.get("status") == "running"
    finished = await _finished_ai_audits(db, business_id, 2)
    for audit in finished:  # stored runs get today's source-type rules
        retype_citations(audit, stored.profile)
    current_audit = finished[0] if finished else None
    previous_audit = finished[1] if len(finished) > 1 else None
    current_summary = _safe_summary(current_audit)

    sections = {"business": business, "foundations": foundations}
    metrics: list[dict] = []
    if current_audit and current_summary:
        ai = ai_sections(current_audit, current_summary)
        metrics = ai_metric_rows(current_audit, ai)
        await save_metrics(db, current_audit["_id"], bid, "ai_run", metrics)
    else:
        ai = {k: {"available": False} for k in ("visibility", "competitors", "citations", "accuracy")}
    sections.update(ai)

    comparison = {"available": False}
    prev_summary = _safe_summary(previous_audit)
    if current_summary and previous_audit and prev_summary:
        prev = ai_sections(previous_audit, prev_summary)
        await save_metrics(db, previous_audit["_id"], bid, "ai_run", ai_metric_rows(previous_audit, prev))
        comparison = compare(ai, prev, current_audit, previous_audit)

    search_doc = await col(db, "audits").find_one({"business_id": bid, "config.kind": "search_listings"},
                                                  sort=[("created_at", DESCENDING)])
    search = search_section(search_doc)
    sections["search"] = search

    if foundations["available"]:
        await save_metrics(db, foundations["audit_id"], bid, "foundations",
                           [{"metric": f"checks_{s}", "platform": None, "surface": None, "numerator": n,
                             "denominator": sum(foundations["counts"].values()), "detail": None}
                            for s, n in foundations["counts"].items()])
    if search["available"] and search.get("audit_id"):
        await save_metrics(db, search["audit_id"], bid, "search_listings", [
            {"metric": "maps_found", "platform": None, "surface": "maps", "numerator": search["maps"]["found"],
             "denominator": search["maps"]["checked"], "detail": None},
            {"metric": "web_found", "platform": None, "surface": "web", "numerator": search["web"]["found"],
             "denominator": search["web"]["checked"], "detail": None},
            {"metric": "listings_found", "platform": None, "surface": "listings",
             "numerator": sum(1 for x in search["listings"] if x["status"] == "found"),
             "denominator": len(search["listings"]), "detail": None}])

    recs = build_recommendations(sections)
    sources = [a for a in (foundations.get("audit_id"), current_audit and current_audit["_id"],
                           search.get("audit_id")) if a]
    has_evidence = bool(sources)
    actions = await sync_actions(db, bid, recs, sources) if has_evidence else await list_actions(db, bid)

    overview = {
        "generated_at": _now().isoformat(),
        "method": "API view",
        "foundations_checked_at": foundations.get("checked_at"),
        "ai_checked_at": ai["visibility"].get("checked_at"),
        "ai_status": current_audit.get("status") if current_audit else None,
        "ai_run_in_progress": running,
        "search_checked_at": search.get("checked_at"),
        "platforms": [p["label"] for p in ai["visibility"].get("platforms", [])],
        "questions": len(current_audit.get("prompts", [])) if current_audit else 0,
        "visibility_questions": sum(1 for p in (current_audit or {}).get("prompts", [])
                                    if p.get("intent") not in NON_VISIBILITY_INTENTS),
        "runs_per_question": (current_audit or {}).get("config", {}).get("runs"),
        "location": (current_audit or {}).get("config", {}).get("location"),
        "skipped_platforms": (current_summary or {}).get("skipped_platforms", []),
        "limitations": LIMITATIONS,
        "coming_soon": COMING_SOON + [x for x in search.get("coming_soon", []) if x not in COMING_SOON],
    }
    return {
        "business": business,
        "overview": overview,
        "visibility": ai["visibility"],
        "competitors": ai["competitors"],
        "citations": ai["citations"],
        "accuracy": ai["accuracy"],
        "foundations": {k: v for k, v in foundations.items() if k != "checks"},
        "search": search,
        "comparison": comparison,
        "actions": actions,
        "action_counts": action_counts(actions),
        "metrics": metrics,
    }
