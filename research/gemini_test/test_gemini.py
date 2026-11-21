"""
Test 1 (API side): run the Dallas florist prompts through the Gemini API
with Google Search grounding and Google Maps grounding, repeat each run,
and compare the businesses named with what the consumer apps showed.

Usage:
    pip install -r requirements.txt
    copy .env.example .env      (then put your key in .env)
    python test_gemini.py                 # default: 3 runs
    python test_gemini.py --runs 5
    python test_gemini.py --model gemini-2.5-flash

Outputs go to ./results/<timestamp>/:
    raw.jsonl     every API response with grounding sources and search queries
    summary.csv   one row per call: condition, prompt, run, businesses named
    report.txt    run-to-run overlap and overlap with the app results
"""

import argparse
import asyncio
import csv
import difflib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

HERE = Path(__file__).parent

PROMPTS = [
    "best florists in Dallas",
    "same-day flower delivery Dallas",
    "best florist near me",
]

# Downtown Dallas. Used only by the Maps-grounded conditions.
DALLAS = types.LatLng(latitude=32.7767, longitude=-96.7970)

CONDITIONS = {
    # Google Search grounding. The API has no location setting for search.
    "search": dict(tools=[types.Tool(google_search=types.GoogleSearch())], lat_lng=None),
    # Google Maps grounding with the user placed in Dallas.
    "maps_dallas": dict(tools=[types.Tool(google_maps=types.GoogleMaps())], lat_lng=DALLAS),
    # Both tools, user placed in Dallas.
    "search_maps_dallas": dict(
        tools=[types.Tool(google_search=types.GoogleSearch()), types.Tool(google_maps=types.GoogleMaps())],
        lat_lng=DALLAS,
    ),
}


class Businesses(BaseModel):
    businesses: list[str]


EXTRACT_INSTRUCTION = (
    "List every business that the text recommends or names as an option, in the order they first appear. "
    "Return only business names, exactly as written. Exclude publications, review sites, directories "
    "and websites used as sources (for example Yelp, The Knot, D Magazine)."
)


# ---------- API calls ----------

async def call_with_retry(fn, attempts=5):
    delay = 5
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:  # rate limits and transient errors
            msg = str(e)
            retryable = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500"))
            if not retryable or i == attempts - 1:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


def grounding_info(resp):
    out = {"search_queries": [], "web_sources": [], "maps_places": []}
    try:
        gm = resp.candidates[0].grounding_metadata
    except (AttributeError, IndexError, TypeError):
        return out
    if not gm:
        return out
    out["search_queries"] = list(gm.web_search_queries or [])
    for ch in gm.grounding_chunks or []:
        web = getattr(ch, "web", None)
        if web and (web.uri or web.title):
            out["web_sources"].append({"title": web.title, "uri": web.uri})
        maps = getattr(ch, "maps", None)
        if maps and (getattr(maps, "title", None) or getattr(maps, "uri", None)):
            out["maps_places"].append({
                "title": getattr(maps, "title", None),
                "uri": getattr(maps, "uri", None),
                "place_id": getattr(maps, "place_id", None),
            })
    return out


async def run_one(client, model, sem, condition, prompt, run):
    cfg = CONDITIONS[condition]
    config = types.GenerateContentConfig(tools=cfg["tools"])
    if cfg["lat_lng"] is not None:
        config.tool_config = types.ToolConfig(
            retrieval_config=types.RetrievalConfig(lat_lng=cfg["lat_lng"])
        )
    record = {
        "condition": condition, "prompt": prompt, "run": run, "model": model,
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    async with sem:
        t0 = time.perf_counter()
        try:
            resp = await call_with_retry(lambda: client.aio.models.generate_content(
                model=model, contents=prompt, config=config))
            record["latency_s"] = round(time.perf_counter() - t0, 2)
            record["text"] = resp.text or ""
            record.update(grounding_info(resp))
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                record["tokens_in"] = usage.prompt_token_count
                record["tokens_out"] = usage.candidates_token_count
        except Exception as e:
            record["latency_s"] = round(time.perf_counter() - t0, 2)
            record["error"] = str(e)[:500]
            record["businesses"] = []
            print(f"  ERROR {condition} | {prompt} | run {run}: {record['error'][:120]}")
            return record

        # Second, cheap call: pull the business names out of the answer.
        try:
            ex = await call_with_retry(lambda: client.aio.models.generate_content(
                model=model,
                contents=f"{EXTRACT_INSTRUCTION}\n\nTEXT:\n{record['text']}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=Businesses),
            ))
            record["businesses"] = ex.parsed.businesses if ex.parsed else []
        except Exception as e:
            record["businesses"] = []
            record["extract_error"] = str(e)[:300]
    print(f"  done {condition:<20} | {prompt:<32} | run {run} | {record['latency_s']}s | "
          f"{len(record['businesses'])} businesses")
    return record


# ---------- comparing names ----------

STOP = {"the", "florist", "florists", "flowers", "flower", "shop", "designs", "design", "events",
        "and", "co", "inc", "llc", "dallas", "on", "of", "by", "interior", "same", "day", "delivery"}


def norm(name):
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and ")).split()
    key = " ".join(w for w in words if w not in STOP)
    return key or " ".join(words)


def same_business(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def overlap(list_a, list_b):
    """Share of businesses in common (Jaccard), matching names loosely."""
    if not list_a and not list_b:
        return None
    matched_b = set()
    common = 0
    for a in list_a:
        for j, b in enumerate(list_b):
            if j not in matched_b and same_business(a, b):
                matched_b.add(j)
                common += 1
                break
    union = len(list_a) + len(list_b) - common
    return common / union if union else None


def pct(x):
    return "  n/a" if x is None else f"{round(x * 100):>4}%"


# ---------- report ----------

def build_report(records, app_results):
    lines = []
    by_key = {}
    for r in records:
        by_key.setdefault((r["condition"], r["prompt"]), []).append(r)

    lines.append("GEMINI API RESULTS — Dallas florist test")
    lines.append("=" * 72)
    for prompt in PROMPTS:
        lines.append(f"\nPROMPT: {prompt}")
        lines.append("-" * 72)
        for condition in CONDITIONS:
            runs = sorted(by_key.get((condition, prompt), []), key=lambda r: r["run"])
            if not runs:
                continue
            lines.append(f"\n  [{condition}]")
            for r in runs:
                if r.get("error"):
                    lines.append(f"    run {r['run']}: ERROR {r['error'][:100]}")
                else:
                    lines.append(f"    run {r['run']} ({r['latency_s']}s): " + ", ".join(r["businesses"]))
            ok = [r["businesses"] for r in runs if not r.get("error")]
            pairs = [overlap(ok[i], ok[j]) for i in range(len(ok)) for j in range(i + 1, len(ok))]
            pairs = [p for p in pairs if p is not None]
            if pairs:
                lines.append(f"    run-to-run overlap (avg): {pct(sum(pairs) / len(pairs))}")
            apps = app_results.get(prompt, {})
            for app_name, app_list in apps.items():
                vals = [overlap(b, app_list) for b in ok]
                vals = [v for v in vals if v is not None]
                if vals:
                    lines.append(f"    overlap with {app_name:<32} {pct(sum(vals) / len(vals))}")
            places = {p["title"] for r in runs for p in r.get("maps_places", []) if p.get("title")}
            if places:
                lines.append(f"    Maps places returned: {len(places)}")
            queries = {q for r in runs for q in r.get("search_queries", [])}
            if queries:
                lines.append(f"    search queries Gemini ran: {'; '.join(sorted(queries))[:300]}")
    return "\n".join(lines)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    ap.add_argument("--concurrency", type=int, default=3,
                    help="parallel calls; keep low on the free tier")
    ap.add_argument("--conditions", default=",".join(CONDITIONS),
                    help="comma list from: " + ",".join(CONDITIONS))
    args = ap.parse_args()

    load_dotenv(HERE / ".env")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("Put GEMINI_API_KEY in gemini_test/.env first (see .env.example).")

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip() in CONDITIONS]
    app_results = json.loads((HERE / "app_results.json").read_text(encoding="utf-8"))
    app_results = {k: v for k, v in app_results.items() if not k.startswith("_")}

    client = genai.Client()
    sem = asyncio.Semaphore(args.concurrency)
    jobs = [run_one(client, args.model, sem, c, p, r)
            for c in conditions for p in PROMPTS for r in range(1, args.runs + 1)]
    print(f"Running {len(jobs)} calls on {args.model} "
          f"({len(conditions)} conditions x {len(PROMPTS)} prompts x {args.runs} runs)...")
    t0 = time.perf_counter()
    records = await asyncio.gather(*jobs)
    total = round(time.perf_counter() - t0, 1)

    out = HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "raw.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "prompt", "run", "latency_s", "n_businesses", "businesses",
                    "n_web_sources", "n_maps_places", "error"])
        for r in records:
            w.writerow([r["condition"], r["prompt"], r["run"], r.get("latency_s"),
                        len(r.get("businesses", [])), " | ".join(r.get("businesses", [])),
                        len(r.get("web_sources", [])), len(r.get("maps_places", [])), r.get("error", "")])
    report = build_report(records, app_results)
    report += f"\n\nTotal wall time: {total}s for {len(jobs)} calls"
    (out / "report.txt").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    asyncio.run(main())
