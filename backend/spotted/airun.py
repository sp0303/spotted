"""AI runs (build step 3) and the full audit's AI part (build step 7): ask AI platforms the customer prompts,
record who they name and cite.

Free run (plan section 25): 5-10 prompts x the available platforms x 1 run at the first target location, all in
parallel, results saved as each call finishes so the page can show them live. Limited per business and per IP a
day; a finished run for the same business and questions from the last hour is reused instead of re-run.

Full ("paid") audit (plan sections 24, 25, 28): up to 25 core prompts x 3 runs x every platform, search off
(gemini_memory: model knowledge) next to search on, at every target location that has a map position (city in the
prompt + Maps lat/lng), plus up to 5 branded/accuracy prompts asked once at the first location. Runs in the
background under a cost/time budget. Payment doesn't exist yet: only allowed when PAID_AUDITS_ENABLED=1.

Reports show counts ("named in 2 of 3 runs"), never rank-precise percentages (plan 24, 27). Branded prompts
always name the business, so they count toward accuracy, not visibility.

Settings (environment, read when used):
  PAID_AUDITS_ENABLED=1            allow tier "paid" (dev/admin until payment exists)
  AI_PAID_RUNS                     repeat runs per core prompt and platform (default 3)
  AI_PAID_MAX_CALLS                most AI calls one full audit may plan (default 1500)
  AI_PAID_MAX_USD                  spend at which a full audit stops starting calls (default 15)
  AI_PAID_MAX_MINUTES              time after which a full audit stops starting calls (default 60)
  AI_PAID_CONCURRENCY              calls in flight per full audit (default 8; provider caps also apply)
  AI_FREE_MAX_USD                  spend cap for one free run (default 1)
  AI_FREE_PER_BUSINESS_PER_DAY     free runs per business per 24 h (default 3)
  AI_FREE_PER_IP_PER_DAY           free runs per requester IP per 24 h (default 10)
  AI_FREE_REUSE_MINUTES            reuse a finished free run this recent (default 60)
"""

import asyncio
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from .analysis import Reader, citations_from, mentions_from
from .config import settings
from .models import BusinessProfile
from .platforms import PLATFORMS, Answerer, PlatformError, gemini_cost, location_method
from .prompts import BRANDED_INTENTS, PROMPTS_VERSION, PromptIn, for_location
from .repo import col

# ai-run-2: full audit tier, location runs, repeat runs, search-off runs, prompt taxonomy v2, ChatGPT direct.
METHODOLOGY_VERSION = "ai-run-2"
MAX_STORED_TEXT = 8000  # characters of each answer kept (a full audit holds hundreds of answers in one document)


def _env_num(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def paid_enabled() -> bool:
    return os.getenv("PAID_AUDITS_ENABLED") == "1"


def paid_runs() -> int:
    return max(1, min(10, int(_env_num("AI_PAID_RUNS", 3))))


def budget_for(tier: str) -> dict:
    if tier == "paid":
        return {"max_calls": int(_env_num("AI_PAID_MAX_CALLS", 1500)), "max_usd": _env_num("AI_PAID_MAX_USD", 15.0),
                "max_seconds": int(_env_num("AI_PAID_MAX_MINUTES", 60) * 60),
                "concurrency": max(1, int(_env_num("AI_PAID_CONCURRENCY", 8)))}
    return {"max_calls": 100, "max_usd": _env_num("AI_FREE_MAX_USD", 1.0), "max_seconds": 300, "concurrency": 0}


def free_limits() -> dict:
    return {"per_business_per_day": int(_env_num("AI_FREE_PER_BUSINESS_PER_DAY", 3)),
            "per_ip_per_day": int(_env_num("AI_FREE_PER_IP_PER_DAY", 10)),
            "reuse_minutes": _env_num("AI_FREE_REUSE_MINUTES", 60)}


class AuditTooBig(ValueError):
    """The planned audit is over the call budget; the message is safe to show."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- where the customer searches from ----------

def _loc_dict(loc, loc_id: str) -> dict:
    return {"id": loc_id, "city": loc.city, "region": loc.region, "country_code": loc.country_code,
            "postal_code": loc.postal_code, "lat": loc.lat, "lng": loc.lng}


def target_point(p: BusinessProfile) -> dict:
    """The place the customer is searching from: the first target location (its city goes in the prompts)."""
    targets = sorted((loc for loc in p.locations if loc.is_target), key=lambda loc: loc.priority) or p.locations
    loc = next((x for x in targets if x.lat is not None and x.lng is not None), targets[0] if targets else None)
    if loc is None:
        return {"city": None, "lat": None, "lng": None}
    return {"city": loc.city, "region": loc.region, "country_code": loc.country_code, "lat": loc.lat, "lng": loc.lng}


def target_locations(p: BusinessProfile, all_locations: bool) -> list[dict]:
    """Location runs: the first target only (free run), or every target location with a map position (full audit).

    Without any map position the first target is still used (city in the prompt; Maps grounding is skipped).
    """
    first = target_point(p)
    primary = {"id": "L1", **{k: first.get(k) for k in ("city", "region", "country_code", "lat", "lng")}}
    primary["postal_code"] = next((x.postal_code for x in p.locations if x.city == first.get("city") and
                                   x.lat == first.get("lat")), None)
    if not all_locations:
        return [primary]
    targets = sorted((loc for loc in p.locations if loc.is_target), key=lambda loc: loc.priority)
    out, seen = [primary], {(primary["city"] or "").lower()}
    for loc in targets:
        if loc.city and loc.lat is not None and loc.lng is not None and loc.city.lower() not in seen:
            seen.add(loc.city.lower())
            out.append(_loc_dict(loc, f"L{len(out) + 1}"))
    return out


def _locations(audit: dict) -> list[dict]:
    cfg = audit["config"]
    return cfg.get("locations") or [{"id": "L1", **cfg.get("location", {})}]


def plan_jobs(audit: dict) -> list[tuple[dict, str, int, dict]]:
    """(prompt, platform key, run index, location) for every call, run 1 of everything first.

    Branded/accuracy prompts are asked `branded_runs` times at the first location only (facts don't vary by city).
    """
    cfg = audit["config"]
    runs = cfg.get("runs", 1)
    branded_runs = cfg.get("branded_runs", runs)
    locs = _locations(audit)
    jobs = []
    for r in range(1, runs + 1):
        for p in audit["prompts"]:
            branded = p["intent"] in BRANDED_INTENTS
            if branded and r > branded_runs:
                continue
            for loc in locs[:1] if branded else locs:
                for key in cfg["platforms"]:
                    if PLATFORMS[key].needs_latlng and loc.get("lat") is None:
                        continue
                    jobs.append((p, key, r, loc))
    return jobs


# ---------- creating and running ----------

async def previous_ai_audit_id(db: AsyncDatabase, business_id: UUID) -> str | None:
    prev = await col(db, "audits").find_one({"business_id": str(business_id), "config.kind": "ai_run"}, {"_id": 1},
                                            sort=[("created_at", DESCENDING)])
    return prev["_id"] if prev else None


async def create_ai_audit(db: AsyncDatabase, business_id: UUID, profile: BusinessProfile, prompts: list[PromptIn],
                          platforms: list[str], runs: int, tier: str = "free", requested_ip: str | None = None,
                          all_locations: bool = False, branded_runs: int = 1) -> dict:
    locs = target_locations(profile, all_locations)
    use, skipped = [], {}
    for key in platforms:
        if PLATFORMS[key].needs_latlng and not any(loc.get("lat") is not None for loc in locs):
            skipped[key] = "No map position for your location yet."
        else:
            use.append(key)
    budget = budget_for(tier)
    now = _now()
    primary = {k: v for k, v in locs[0].items() if k not in ("id", "postal_code")}
    doc = {
        "_id": str(uuid4()), "business_id": str(business_id), "tier": tier, "status": "running",
        "methodology_version": METHODOLOGY_VERSION, "requested_ip": requested_ip,
        "previous_audit_id": await previous_ai_audit_id(db, business_id),
        "config": {"kind": "ai_run", "tier": tier, "platforms": use, "skipped": skipped, "runs": runs,
                   "branded_runs": min(runs, branded_runs), "location": primary, "locations": locs,
                   "search_off": any(not PLATFORMS[k].search_enabled for k in use),
                   "server_region": settings.server_region, "prompts_version": PROMPTS_VERSION, "budget": budget},
        "prompts": [{"id": str(uuid4()), "text": p.text, "intent": p.intent, "user_edited": p.user_edited,
                     "sort_order": i} for i, p in enumerate(prompts)],
        "runs": [], "cost_usd": 0.0,
        # first_results_at is left unset: the first finished run sets it with $min (null would always win $min).
        "started_at": now, "finished_at": None, "created_at": now,
    }
    jobs = plan_jobs(doc)
    if len(jobs) > budget["max_calls"]:
        raise AuditTooBig(f"This audit would ask {len(jobs)} questions; the limit is {budget['max_calls']}. "
                          "Remove some questions or locations.")
    doc["expected_runs"] = len(jobs)
    await col(db, "audits").insert_one(doc)
    return doc


def _new_run(prompt: dict, key: str, run_index: int, loc: dict, primary: dict) -> dict:
    plat = PLATFORMS[key]
    return {"id": str(uuid4()), "prompt_id": prompt["id"], "platform_key": key, "platform": plat.platform,
            "label": plat.label, "surface": "api", "search_enabled": plat.search_enabled, "grounding": plat.grounding,
            "location_method": location_method(plat), "location_id": loc.get("id"), "city": loc.get("city"),
            "prompt_text": for_location(prompt["text"], primary, loc),
            "lat": loc.get("lat") if plat.needs_latlng else None, "lng": loc.get("lng") if plat.needs_latlng else None,
            "run_index": run_index, "started_at": _now(), "status": "done", "error": None,
            "model": None, "latency_ms": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
            "response": None, "mentions": [], "citations": [], "asked_for_location": False}


async def _one_run(db, audit, prompt, key, run_index, profile, competitors, answerer: Answerer, reader: Reader,
                   loc: dict | None = None) -> float:
    plat = PLATFORMS[key]
    locs = _locations(audit)
    loc = loc or locs[0]
    run = _new_run(prompt, key, run_index, loc, locs[0])
    try:
        extra = {"where": {k: loc.get(k) for k in ("city", "region", "country_code")}} \
            if run["location_method"] == "api_location" else {}
        ans = await answerer.answer(plat, run["prompt_text"], run["lat"], run["lng"], **extra)
        run.update(model=ans.model, latency_ms=ans.latency_ms, tokens_in=ans.tokens_in, tokens_out=ans.tokens_out,
                   cost_usd=ans.cost_usd,
                   response={"text": ans.text[:MAX_STORED_TEXT], "search_queries": ans.search_queries,
                             "maps_places": ans.maps_places})
        reading, tin, tout = await reader.read(ans.text, profile)
        run["cost_usd"] += gemini_cost(tin, tout, grounded=False)
        run["analysis_tokens"] = {"in": tin, "out": tout}
        run["mentions"] = mentions_from(reading, profile, competitors)
        run["citations"] = citations_from(ans.sources, profile, [m["entity_name"] for m in run["mentions"]])
        run["asked_for_location"] = reading.asked_for_location
    except PlatformError as exc:
        run.update(status="timeout" if "within" in str(exc) else "error", error=str(exc))
    except Exception as exc:  # one failed call never sinks the audit
        run.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:200]}")
    now = _now()
    update = {"$push": {"runs": run}, "$inc": {"cost_usd": run["cost_usd"]}}
    if run["status"] == "done":  # a fast failure isn't a first result
        update["$min"] = {"first_results_at": now}
    await col(db, "audits").update_one({"_id": audit["_id"]}, update)
    return run["cost_usd"]


async def execute(db: AsyncDatabase, audit: dict, profile: BusinessProfile, competitors: list[str],
                  answerer: Answerer, reader: Reader) -> None:
    budget = audit["config"].get("budget") or budget_for(audit.get("tier", "free"))
    jobs = plan_jobs(audit)
    primary = _locations(audit)[0]
    state = {"cost": 0.0, "stopped": None}
    deadline = time.monotonic() + budget["max_seconds"]
    # Per-audit queue for the full audit (provider-wide caps live in LiveAnswerer); the free run starts everything.
    sem = asyncio.Semaphore(budget.get("concurrency") or max(1, len(jobs)))

    async def guarded(prompt, key, r, loc):
        async with sem:
            if state["cost"] >= budget["max_usd"]:
                state["stopped"] = f"Stopped early: this audit reached its ${budget['max_usd']:.2f} spending limit."
            elif time.monotonic() > deadline:
                state["stopped"] = "Stopped early: this audit reached its time limit."
            if state["stopped"]:
                run = _new_run(prompt, key, r, loc, primary)
                run.update(status="skipped", error=state["stopped"])
                await col(db, "audits").update_one({"_id": audit["_id"]}, {"$push": {"runs": run}})
                return
            state["cost"] += await _one_run(db, audit, prompt, key, r, profile, competitors, answerer, reader, loc)

    try:
        await asyncio.gather(*(guarded(*j) for j in jobs))
        done = await col(db, "audits").find_one({"_id": audit["_id"]}, {"runs.status": 1})
        statuses = [r["status"] for r in done.get("runs", [])]
        status = "complete" if statuses and all(s == "done" for s in statuses) else \
            "failed" if not any(s == "done" for s in statuses) else "partial"
    except Exception:
        status = "failed"
    update = {"status": status, "finished_at": _now()}
    if state["stopped"]:
        update["note"] = state["stopped"]
    await col(db, "audits").update_one({"_id": audit["_id"]}, {"$set": update})


async def get_ai_audit(db: AsyncDatabase, audit_id: str) -> dict | None:
    return await col(db, "audits").find_one({"_id": audit_id, "config.kind": "ai_run"})


async def latest_ai_audit(db: AsyncDatabase, business_id: UUID) -> dict | None:
    return await col(db, "audits").find_one({"business_id": str(business_id), "config.kind": "ai_run"},
                                            sort=[("created_at", DESCENDING)])


async def mark_stale_running(db: AsyncDatabase) -> None:
    """Audits left 'running' by a restart can't finish; close them with what they have."""
    await col(db, "audits").update_many({"config.kind": "ai_run", "status": "running"},
                                        {"$set": {"status": "partial", "finished_at": _now(),
                                                  "note": "Stopped early: the server restarted."}})


# ---------- free-run limits (plan 25) ----------

async def reusable_free_run(db: AsyncDatabase, business_id: UUID, prompts: list[PromptIn],
                            platforms: list[str]) -> dict | None:
    """A finished free run of the same questions on the same platforms for this business, recent enough to reuse."""
    since = _now() - timedelta(minutes=free_limits()["reuse_minutes"])
    texts = sorted(p.text.strip().lower() for p in prompts)
    cursor = col(db, "audits").find(
        {"business_id": str(business_id), "config.kind": "ai_run", "tier": "free",
         "status": {"$in": ["complete", "partial"]}, "created_at": {"$gte": since}},
        {"prompts.text": 1, "config.platforms": 1, "config.skipped": 1, "expected_runs": 1},
        sort=[("created_at", DESCENDING)])
    async for a in cursor:
        ran = set(a["config"]["platforms"]) | set(a["config"].get("skipped", {}))
        if sorted(p["text"].strip().lower() for p in a["prompts"]) == texts and ran == set(platforms):
            return a
    return None


async def free_limit_problem(db: AsyncDatabase, business_id: UUID, requested_ip: str | None) -> str | None:
    """A plain message when a new free run would go over today's limits, else None."""
    lim = free_limits()
    since = _now() - timedelta(days=1)
    base = {"config.kind": "ai_run", "tier": "free", "created_at": {"$gte": since}}
    if await col(db, "audits").count_documents({**base, "business_id": str(business_id)}) >= lim["per_business_per_day"]:
        return (f"You've used today's {lim['per_business_per_day']} free AI runs for this business. "
                "Your latest results are still here; try again tomorrow.")
    if requested_ip and await col(db, "audits").count_documents({**base, "requested_ip": requested_ip}) \
            >= lim["per_ip_per_day"]:
        return f"Too many free AI runs from your network today (limit {lim['per_ip_per_day']}). Try again tomorrow."
    return None


# ---------- what the page shows ----------

def _iso(dt):
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def _client(r: dict) -> dict | None:
    return next((m for m in r["mentions"] if m["is_client"]), None)


def _named(r: dict) -> bool:
    return _client(r) is not None


def _recommended(r: dict) -> bool:
    return any(m["is_client"] and m["kind"] == "recommended" for m in r["mentions"])


def _side(rs: list[dict]) -> dict:
    return {"answers": len(rs), "named": sum(1 for r in rs if _named(r)),
            "recommended": sum(1 for r in rs if _recommended(r)),
            "platforms": sorted({PLATFORMS[r["platform_key"]].label for r in rs})}


def _competitor_runs(rs: list[dict]) -> tuple[dict[str, set], dict[str, Counter]]:
    runs_by: dict[str, set] = defaultdict(set)
    names: dict[str, Counter] = defaultdict(Counter)
    for r in rs:
        for m in r["mentions"]:
            if not m["is_client"]:
                runs_by[m["normalized"]].add(r["id"])
                names[m["normalized"]][m["entity_name"]] += 1
    return runs_by, names


def _search_comparison(unbranded: list[dict]) -> dict | None:
    """Search on vs off (model knowledge vs live search), over the prompts and locations asked both ways."""
    on = [r for r in unbranded if PLATFORMS[r["platform_key"]].search_enabled]
    off = [r for r in unbranded if not PLATFORMS[r["platform_key"]].search_enabled]
    both = {(r["prompt_id"], r.get("location_id")) for r in on} & {(r["prompt_id"], r.get("location_id")) for r in off}
    on = [r for r in on if (r["prompt_id"], r.get("location_id")) in both]
    off = [r for r in off if (r["prompt_id"], r.get("location_id")) in both]
    if not on or not off:
        return None
    on_runs, on_names = _competitor_runs(on)
    off_runs, off_names = _competitor_runs(off)

    def label(k):
        return (on_names.get(k) or off_names[k]).most_common(1)[0][0]

    def ranked(keys, runs_by):
        return [label(k) for k in sorted(keys, key=lambda k: (-len(runs_by[k]), label(k)))][:10]

    return {"search_on": _side(on), "search_off": _side(off),
            "competitors_both": ranked(set(on_runs) & set(off_runs), on_runs),
            "competitors_only_search_on": ranked(set(on_runs) - set(off_runs), on_runs),
            "competitors_only_search_off": ranked(set(off_runs) - set(on_runs), off_runs)}


def summarize(audit: dict) -> dict:
    prompts = {p["id"]: p for p in audit["prompts"]}
    cfg = audit["config"]
    locs = _locations(audit)
    first_loc = locs[0]["id"]
    runs = [{**r, "location_id": r.get("location_id") or first_loc} for r in audit.get("runs", [])]
    ok = [r for r in runs if r["status"] == "done"]
    unbranded = [r for r in ok if prompts[r["prompt_id"]]["intent"] not in BRANDED_INTENTS]
    loc_city = {loc["id"]: loc.get("city") for loc in locs}

    platforms = []
    for key in cfg["platforms"]:
        rs = [r for r in unbranded if r["platform_key"] == key]
        named = [r for r in rs if _named(r)]
        positions = [m["position"] for r in named for m in r["mentions"] if m["is_client"]]
        all_runs = [r for r in runs if r["platform_key"] == key]
        asked = {(r["prompt_id"], r["location_id"]) for r in rs}
        platforms.append({
            "key": key, "label": PLATFORMS[key].label, "search_enabled": PLATFORMS[key].search_enabled,
            "answers": len(rs), "named": len(named),
            "recommended": sum(1 for r in named if _recommended(r)),
            "best_position": min(positions) if positions else None,
            "own_site_cited": sum(1 for r in rs if any(c["source_type"] == "own_site" for c in r["citations"])),
            "errors": sum(1 for r in all_runs if r["status"] not in ("done", "skipped")),
            "skipped": sum(1 for r in all_runs if r["status"] == "skipped"),
            "cost_usd": round(sum(r["cost_usd"] for r in all_runs), 4),
            "avg_seconds": round(sum(r["latency_ms"] or 0 for r in all_runs if r["latency_ms"]) /
                                 max(1, sum(1 for r in all_runs if r["latency_ms"])) / 1000, 1),
            # Distinct question x location pairs answered, and in how many the client was named at least once.
            "prompts_asked": len(asked),
            "prompts_named": len({(r["prompt_id"], r["location_id"]) for r in named}),
            "location_method": all_runs[0].get("location_method", PLATFORMS[key].location_method) if all_runs
            else PLATFORMS[key].location_method,
        })

    comp_runs: dict[str, set] = defaultdict(set)
    comp_names: dict[str, Counter] = defaultdict(Counter)
    comp_platforms: dict[str, set] = defaultdict(set)
    comp_prompts: dict[str, set] = defaultdict(set)
    comp_known: dict[str, bool] = {}
    for r in unbranded:
        for m in r["mentions"]:
            if m["is_client"]:
                continue
            k = m["normalized"]
            comp_runs[k].add(r["id"])
            comp_names[k][m["entity_name"]] += 1
            comp_platforms[k].add(PLATFORMS[r["platform_key"]].label)
            comp_prompts[k].add(r["prompt_id"])
            comp_known[k] = comp_known.get(k) or bool(m.get("competitor"))
    competitors = sorted(({"name": comp_names[k].most_common(1)[0][0], "answers": len(v),
                           "platforms": sorted(comp_platforms[k]), "known": comp_known[k],
                           "prompts": len(comp_prompts[k])}
                          for k, v in comp_runs.items()), key=lambda c: (-c["answers"], c["name"]))

    src_runs: dict[str, set] = defaultdict(set)
    src_type: dict[str, str] = {}
    for r in ok:
        for c in r["citations"]:
            src_runs[c["domain"]].add(r["id"])
            src_type[c["domain"]] = c["source_type"]
    sources = sorted(({"domain": d, "answers": len(v), "type": src_type[d]} for d, v in src_runs.items()),
                     key=lambda s: (-s["answers"], s["domain"]))

    wrong = [{"platform": PLATFORMS[r["platform_key"]].label, "prompt": prompts[r["prompt_id"]]["text"],
              "facts": m["facts_wrong"]} for r in ok for m in r["mentions"] if m["is_client"] and m["facts_wrong"]]

    by_prompt = []
    for p in audit["prompts"]:
        cells, freq = [], []
        for key in cfg["platforms"]:
            for loc in locs:
                rs = sorted((r for r in runs if r["prompt_id"] == p["id"] and r["platform_key"] == key
                             and r["location_id"] == loc["id"]), key=lambda r: r["run_index"])
                for r in rs:
                    client = _client(r)
                    cells.append({
                        "run_id": r["id"], "platform_key": key, "label": PLATFORMS[key].label,
                        "run_index": r["run_index"], "location_id": loc["id"], "city": loc.get("city"),
                        "prompt_text": r.get("prompt_text") or p["text"],
                        "status": r["status"], "error": r["error"], "seconds": round((r["latency_ms"] or 0) / 1000, 1),
                        "client": None if client is None else {"position": client["position"], "kind": client["kind"],
                                                               "context": client["context"]},
                        "asked_for_location": r.get("asked_for_location", False),
                        "names": [m["entity_name"] for m in r["mentions"]],
                        "sources": [{"domain": c["domain"], "type": c["source_type"], "url": c["url"]}
                                    for c in r["citations"]],
                        "search_queries": (r["response"] or {}).get("search_queries", []),
                        "text": (r["response"] or {}).get("text", ""),
                    })
                if rs:
                    done = [r for r in rs if r["status"] == "done"]
                    freq.append({"platform_key": key, "label": PLATFORMS[key].label,
                                 "search_enabled": PLATFORMS[key].search_enabled, "location_id": loc["id"],
                                 "city": loc.get("city"), "runs": len(rs), "done": len(done),
                                 "named": sum(1 for r in done if _named(r)),
                                 "recommended": sum(1 for r in done if _recommended(r))})
        by_prompt.append({"id": p["id"], "text": p["text"], "intent": p["intent"], "results": cells,
                          "frequency": freq})

    by_location = []
    for loc in locs:
        rs = [r for r in unbranded if r["location_id"] == loc["id"]]
        lr, ln = _competitor_runs(rs)
        top = sorted(lr, key=lambda k: (-len(lr[k]), ln[k].most_common(1)[0][0]))[:5]
        by_location.append({
            "id": loc["id"], "city": loc.get("city"), "region": loc.get("region"),
            "country_code": loc.get("country_code"), "lat": loc.get("lat"), "lng": loc.get("lng"),
            "answers": len(rs), "named": sum(1 for r in rs if _named(r)),
            "recommended": sum(1 for r in rs if _recommended(r)),
            "platforms": [{"key": k, "label": PLATFORMS[k].label,
                           "answers": sum(1 for r in rs if r["platform_key"] == k),
                           "named": sum(1 for r in rs if r["platform_key"] == k and _named(r))}
                          for k in cfg["platforms"]],
            "competitors": [{"name": ln[k].most_common(1)[0][0], "answers": len(lr[k])} for k in top],
        })

    started = audit.get("started_at")
    first = audit.get("first_results_at")
    return {
        "audit_id": audit["_id"], "business_id": audit["business_id"], "status": audit["status"],
        "started_at": _iso(started), "finished_at": _iso(audit.get("finished_at")),
        "first_result_seconds": round((first - started).total_seconds(), 1) if first and started else None,
        "expected_runs": audit["expected_runs"], "finished_runs": len(runs), "location": cfg["location"],
        "skipped_platforms": [{"key": k, "label": PLATFORMS[k].label, "reason": v}
                              for k, v in cfg.get("skipped", {}).items()],
        "cost_usd": round(audit.get("cost_usd", 0.0), 4), "visibility_answers": len(unbranded),
        "platforms": platforms, "competitors": competitors[:25], "sources": sources[:25],
        "wrong_facts": wrong, "prompts": by_prompt, "note": audit.get("note"),
        # Added for the full audit (build step 7); free runs have one location, one run, maybe no search-off.
        "tier": audit.get("tier", "free"), "methodology_version": audit.get("methodology_version"),
        "runs_per_prompt": cfg.get("runs", 1), "branded_runs": cfg.get("branded_runs", cfg.get("runs", 1)),
        "previous_audit_id": audit.get("previous_audit_id"),
        "locations": by_location, "search_comparison": _search_comparison(unbranded),
        "skipped_runs": sum(1 for r in runs if r["status"] == "skipped"),
        "budget": cfg.get("budget"),
    }
