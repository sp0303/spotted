"""
Test 2: how do different AI models answer the Dallas florist prompts, and is that useful?

Runs the Test 1 prompts through several models and compares them on three things:
  1. Overlap with what the consumer apps showed (gemini_test/app_results.json): does the model
     see what real users see?
  2. Run-to-run agreement: is the answer stable enough to measure?
  3. Real-business rate: are the named businesses real, operating Dallas florists? Names already
     seen in the apps or in Google Maps answers count as real; the rest are checked once with
     Gemini + Google Search.

Providers (keys in ./.env, see .env.example):
  gemini      Gemini API: no tools (memory only), Google Search grounding, Google Maps grounding at Dallas
  nvidia      NVIDIA API catalog (integrate.api.nvidia.com): open models, no web access (memory only)
  openrouter  OpenRouter: web-search models (":online" suffix or Perplexity Sonar) and others

Usage:
    python compare_models.py                       # all providers that have a key, 3 runs
    python compare_models.py --providers nvidia --runs 2
    python compare_models.py --nvidia-models moonshotai/kimi-k3.1-pro,z-ai/glm-5.3-flash
    python compare_models.py --list-models         # what each provider offers with your keys

Outputs go to ./results/<timestamp>/: raw.jsonl, verify.json, usage.json, report.md (with tokens and cost)
"""

import argparse
import asyncio
import difflib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

HERE = Path(__file__).parent
APP_RESULTS = HERE.parent / "gemini_test" / "app_results.json"

PROMPTS = [
    "best florists in Dallas",
    "same-day flower delivery Dallas",
    "best florist near me",
]
DALLAS = types.LatLng(latitude=32.7767, longitude=-96.7970)

GEMINI_MODEL = "gemini-3.8-flash"  # also used to extract names and verify businesses
GEMINI_SETUPS = ["memory", "search", "maps_dallas"]

NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODELS = [
    "moonshotai/kimi-k3.1-pro",
    "mistralai/mistral-large-4-1t-a52b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "minimaxai/minimax-m3.1-flash",
    "google/gemma-4-31b-it",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS = [
    "perplexity/sonar",                   # searches the web natively
    "openai/gpt-5-mini:online",           # ":online" = OpenRouter web search (OpenAI's own search for OpenAI models)
    "anthropic/claude-haiku-5.5:online",
    "openai/gpt-5-mini",                  # same model without web, to see what search adds
]

# Gemini 3.8 Flash paid Standard tier, USD (ai.google.dev pricing page, read 24 Nov 2026; doubles on 1 Jan 2027).
# Output includes thinking tokens. Grounding: first 5,000 requests/month free per tool, shared across Gemini 3+.
GEMINI_PRICE_IN_PER_M = 0.75
GEMINI_PRICE_OUT_PER_M = 3.75
GEMINI_GROUNDING_PER_1K = 14.0

CALL_TIMEOUT_S = 150  # per answer; reasoning models on NVIDIA can take 2-3 minutes
PARTIAL: Path | None = None  # results/<run>/partial.jsonl, appended as each answer finishes


def save_partial(rec):
    if PARTIAL:
        with open(PARTIAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Usage counters, filled as calls finish: purpose -> totals.
USAGE: dict[str, dict] = {}


def add_usage(purpose, **counts):
    u = USAGE.setdefault(purpose, {})
    for k, v in counts.items():
        u[k] = u.get(k, 0) + (v or 0)


def gemini_usage(purpose, resp, grounding=None):
    m = getattr(resp, "usage_metadata", None)
    add_usage(purpose, calls=1,
              tokens_in=getattr(m, "prompt_token_count", 0) or 0,
              tokens_out=(getattr(m, "candidates_token_count", 0) or 0) + (getattr(m, "thoughts_token_count", 0) or 0),
              tool_tokens=getattr(m, "tool_use_prompt_token_count", 0) or 0)
    if grounding:
        add_usage(purpose, **{f"{grounding}_requests": 1})


class KeyRing:
    """Comma-separated keys (one per account): rotate per call, skip a key that is refused or rate-limited."""

    def __init__(self, raw):
        self.keys = [k.strip() for k in (raw or "").split(",") if k.strip()]
        self.i = 0

    def __bool__(self):
        return bool(self.keys)

    def order(self):
        self.i += 1
        return [self.keys[(self.i + j) % len(self.keys)] for j in range(len(self.keys))]


# ---------- calls ----------

class Businesses(BaseModel):
    businesses: list[str]


EXTRACT_INSTRUCTION = (
    "List every business that the text recommends or names as an option, in the order they first appear. "
    "Return only business names, exactly as written. Exclude publications, review sites, directories "
    "and websites used as sources (for example Yelp, The Knot, D Magazine). If the text names no businesses "
    "(for example it asks for the user's location), return an empty list."
)

THINK = re.compile(r"<think>.*?</think>", re.S)


async def retry(fn, attempts=5):
    delay = 4
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:
            msg = str(e)
            # Rate limits and server hiccups are retried; timeouts are not (a slow model stays slow).
            retryable = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500", "502",
                                               "RemoteProtocol"))
            if not retryable or i == attempts - 1:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


async def gemini_answer(client, setup, prompt):
    config = types.GenerateContentConfig()
    if setup == "search":
        config.tools = [types.Tool(google_search=types.GoogleSearch())]
    elif setup == "maps_dallas":
        config.tools = [types.Tool(google_maps=types.GoogleMaps())]
        config.tool_config = types.ToolConfig(retrieval_config=types.RetrievalConfig(lat_lng=DALLAS))
    resp = await retry(lambda: client.aio.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config))
    gemini_usage("answers (gemini)", resp, grounding={"search": "search", "maps_dallas": "maps"}.get(setup))
    out = {"text": resp.text or "", "sources": [], "maps_places": []}
    try:
        gm = resp.candidates[0].grounding_metadata
    except (AttributeError, IndexError, TypeError):
        gm = None
    if gm and gm.web_search_queries:
        add_usage("answers (gemini)", search_queries=len(gm.web_search_queries))
    for ch in (gm.grounding_chunks or []) if gm else []:
        if getattr(ch, "web", None) and ch.web.uri:
            out["sources"].append(ch.web.title or ch.web.uri)
        if getattr(ch, "maps", None) and getattr(ch.maps, "title", None):
            out["maps_places"].append(ch.maps.title)
    return out


async def openai_compatible_answer(http, provider, base_url, ring, model, prompt):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000, "temperature": 0.7}
    if provider == "openrouter":
        body["usage"] = {"include": True}  # OpenRouter then reports the cost of the call

    async def call():
        err = None
        for key in ring.order():  # another account's key when one is refused or out of requests
            r = await http.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body)
            if r.status_code < 400:
                return r.json()
            err = f"{r.status_code} {r.text[:300]}"
            if r.status_code not in (401, 402, 403, 429):
                break
        raise RuntimeError(err)
    data = await retry(call)
    usage = data.get("usage") or {}
    add_usage(f"answers ({provider})", calls=1, tokens_in=usage.get("prompt_tokens"),
              tokens_out=usage.get("completion_tokens"), cost_usd=usage.get("cost"))
    msg = data["choices"][0]["message"]
    text = THINK.sub("", msg.get("content") or "").strip()
    sources = [a.get("url_citation", {}).get("url") for a in msg.get("annotations") or []
               if a.get("type") == "url_citation"]
    sources += data.get("citations") or []  # Perplexity
    return {"text": text, "sources": [s for s in sources if s], "maps_places": [],
            "tokens_out": (data.get("usage") or {}).get("completion_tokens")}


async def extract_names(client, text):
    if not text.strip():
        return []
    ex = await retry(lambda: client.aio.models.generate_content(
        model=GEMINI_MODEL, contents=f"{EXTRACT_INSTRUCTION}\n\nTEXT:\n{text}",
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Businesses)))
    gemini_usage("name extraction (gemini)", ex)
    return ex.parsed.businesses if ex.parsed else []


async def run_one(job, gclient, http, keys, sems):
    provider, model, setup, prompt, run = job
    label = f"{provider}:{model}" + (f" [{setup}]" if setup else "")
    rec = {"provider": provider, "model": model, "setup": setup, "label": label, "prompt": prompt, "run": run,
           "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    async with sems[provider]:
        t0 = time.perf_counter()
        try:
            if provider == "gemini":
                coro = gemini_answer(gclient, setup, prompt)
            else:
                url = NVIDIA_URL if provider == "nvidia" else OPENROUTER_URL
                coro = openai_compatible_answer(http, provider, url, keys[provider], model, prompt)
            rec.update(await asyncio.wait_for(coro, CALL_TIMEOUT_S))
        except TimeoutError:
            rec["error"] = f"timeout after {CALL_TIMEOUT_S}s"
        except Exception as e:
            rec["error"] = (str(e) or type(e).__name__)[:400]
        rec["latency_s"] = round(time.perf_counter() - t0, 1)
    if "error" in rec:
        rec["businesses"] = []
        save_partial(rec)
        print(f"  ERROR {label} | {prompt} | run {run}: {rec['error'][:140]}")
        return rec
    try:
        rec["businesses"] = await extract_names(gclient, rec["text"])
    except Exception as e:
        rec["businesses"], rec["extract_error"] = [], str(e)[:300]
    save_partial(rec)
    print(f"  done  {label:<55} | {prompt:<32} | run {run} | {rec['latency_s']:>5}s | {len(rec['businesses'])} names")
    return rec


# ---------- verifying that named businesses are real ----------

class Verdict(BaseModel):
    name: str
    status: str  # operating | closed | not_found | not_a_florist | not_in_dallas
    note: str


class Verdicts(BaseModel):
    verdicts: list[Verdict]


VERIFY_PROMPT = """For each business below, use Google Search to check whether it is a florist or flower shop that
is currently operating in the Dallas, Texas area (Dallas-Fort Worth metro counts; national online-only
services count as operating if they deliver in Dallas). Answer one verdict per name, same spelling:
  operating      real and currently open / delivering in Dallas
  closed         existed but is permanently closed
  not_florist    real business but not a florist or flower seller (e.g. a grocery app is NOT this if it sells flowers)
  not_in_dallas  real florist but not in or delivering to the Dallas area
  not_found      no evidence the business exists
Reply as JSON: {{"verdicts": [{{"name": ..., "status": ..., "note": short reason}}]}}

Businesses:
{names}"""


async def verify(gclient, names):
    """Check names with Gemini + Google Search, 15 per call. Returns {name: status}."""
    out = {}
    batches = [names[i:i + 15] for i in range(0, len(names), 15)]

    async def one(batch):
        resp = await retry(lambda: gclient.aio.models.generate_content(
            model=GEMINI_MODEL, contents=VERIFY_PROMPT.format(names="\n".join(f"- {n}" for n in batch)),
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])))
        gemini_usage("business check (gemini)", resp, grounding="search")
        m = re.search(r"\{.*\}", resp.text or "", re.S)
        try:
            for v in Verdicts.model_validate_json(m.group(0)).verdicts if m else []:
                out[v.name] = {"status": v.status, "note": v.note}
        except Exception as e:
            print(f"  verify parse error: {e}")

    await asyncio.gather(*(one(b) for b in batches))
    return out


# ---------- comparing names (same rules as gemini_test) ----------

STOP = {"the", "florist", "florists", "flowers", "flower", "shop", "designs", "design", "events",
        "and", "co", "inc", "llc", "dallas", "on", "of", "by", "interior", "same", "day", "delivery"}


def norm(name):
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and ")).split()
    return " ".join(w for w in words if w not in STOP) or " ".join(words)


def same_business(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def overlap(list_a, list_b):
    if not list_a and not list_b:
        return None
    matched, common = set(), 0
    for a in list_a:
        for j, b in enumerate(list_b):
            if j not in matched and same_business(a, b):
                matched.add(j)
                common += 1
                break
    union = len(list_a) + len(list_b) - common
    return common / union if union else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(x):
    return "–" if x is None else f"{round(x * 100)}%"


# ---------- report ----------

def build_report(records, app_results, real_status, args, wall):
    labels = list(dict.fromkeys(r["label"] for r in records))
    by = {}
    for r in records:
        by.setdefault((r["label"], r["prompt"]), []).append(r)

    def is_real(name):
        for known, st in real_status.items():
            if same_business(name, known):
                return st == "operating"
        return None

    rows = []
    for label in labels:
        recs = [r for r in records if r["label"] == label]
        ok = [r for r in recs if not r.get("error")]
        stab, app_ov, names, real = [], [], [], []
        for prompt in PROMPTS:
            lists = [r["businesses"] for r in by.get((label, prompt), []) if not r.get("error")]
            stab += [overlap(lists[i], lists[j]) for i in range(len(lists)) for j in range(i + 1, len(lists))]
            if prompt != "best florist near me":  # app 'near me' answers carried chat context; skip
                for apps in app_results.get(prompt, {}).values():
                    app_ov += [overlap(l, apps) for l in lists]
            for l in lists:
                names += l
                real += [is_real(n) for n in l]
        checked = [x for x in real if x is not None]
        near = [r for r in by.get((label, "best florist near me"), []) if not r.get("error")]
        near_names = [n for r in near for n in r["businesses"]]
        near_dallas = sum(1 for n in near_names if is_real(n)) if near_names else 0
        rows.append({
            "label": label, "calls": len(recs), "errors": len(recs) - len(ok),
            "app_overlap": mean(app_ov), "stability": mean(stab),
            "avg_names": (len(names) / len(ok)) if ok else None,
            "real_rate": (sum(checked) / len(checked)) if checked else None,
            "near_me": ("asks / no names" if near and not near_names else
                        f"{near_dallas}/{len(near_names)} Dallas" if near_names else "–"),
            "latency": mean([r["latency_s"] for r in ok]),
            "web": any(r.get("sources") or r.get("maps_places") for r in ok),
        })

    L = [f"# Model comparison — Dallas florist prompts", "",
         f"Run {datetime.now().strftime('%d %b %Y %H:%M')} · {args.runs} runs per prompt · {len(records)} calls in "
         f"{wall:.0f}s · names extracted and checked with {GEMINI_MODEL}", "",
         "| Model | Web? | Overlap with apps | Run-to-run | Names/answer | Real & operating | \"near me\" | Avg s | Errors |",
         "|---|---|---|---|---|---|---|---|---|"]
    for x in sorted(rows, key=lambda x: -(x["app_overlap"] or 0)):
        L.append(f"| {x['label']} | {'yes' if x['web'] else 'no'} | {pct(x['app_overlap'])} | {pct(x['stability'])} | "
                 f"{'–' if x['avg_names'] is None else round(x['avg_names'], 1)} | {pct(x['real_rate'])} | {x['near_me']} | "
                 f"{'–' if x['latency'] is None else round(x['latency'])} | {x['errors']}/{x['calls']} |")
    L += ["", "*Overlap with apps*: share of businesses in common with each app answer (ChatGPT, Google AI Mode, "
          "Copilot, Bing) for the two Dallas prompts, averaged. *Real & operating*: share of named businesses "
          "confirmed as open Dallas-area florists (seen in an app or in Google Maps, or checked with Google Search).", ""]

    bad = {n: v for n, v in real_status.items() if v != "operating"}
    if bad:
        L += ["## Named businesses that are not real, open Dallas florists", "",
              "| Name | Status | Named by |", "|---|---|---|"]
        for n, st in sorted(bad.items(), key=lambda kv: kv[1]):
            who = sorted({r["label"].split(":", 1)[1] for r in records if any(same_business(n, b) for b in r["businesses"])})
            L.append(f"| {n} | {st} | {', '.join(who)[:120]} |")
        L.append("")

    L += usage_section() + ["## Answers per prompt", ""]
    for prompt in PROMPTS:
        L += [f"### {prompt}", ""]
        for label in labels:
            for r in sorted(by.get((label, prompt), []), key=lambda r: r["run"]):
                body = f"ERROR {r['error'][:120]}" if r.get("error") else (", ".join(r["businesses"]) or "(no businesses named)")
                L.append(f"- **{label}** run {r['run']}: {body}")
        L.append("")
    errs = [r for r in records if r.get("error")]
    if errs:
        L += ["## Errors", ""] + [f"- {r['label']} | {r['prompt']} | run {r['run']}: {r['error'][:200]}" for r in errs]
    return "\n".join(L)


def usage_section():
    L = ["## Usage and cost", "",
         "| Purpose | Calls | Tokens in | Tokens out (incl. thinking) | Search grounding | Maps grounding | Cost (USD) |",
         "|---|---|---|---|---|---|---|"]
    total = 0.0
    grounded = 0
    for purpose, u in USAGE.items():
        tokens_in = u.get("tokens_in", 0) + u.get("tool_tokens", 0)
        if "(gemini)" in purpose:
            cost = tokens_in / 1e6 * GEMINI_PRICE_IN_PER_M + u.get("tokens_out", 0) / 1e6 * GEMINI_PRICE_OUT_PER_M
            grounded += u.get("search_requests", 0) + u.get("maps_requests", 0)
            cost_s = f"${cost:.4f}"
        elif "(openrouter)" in purpose:
            cost = u.get("cost_usd", 0.0)
            cost_s = f"${cost:.4f} (reported)"
        else:
            cost, cost_s = 0.0, "free credits"
        total += cost
        L.append(f"| {purpose} | {u.get('calls', 0)} | {tokens_in:,} | {u.get('tokens_out', 0):,} | "
                 f"{u.get('search_requests', 0) or '–'} | {u.get('maps_requests', 0) or '–'} | {cost_s} |")
    L += ["", f"**Total: ${total:.4f}** in tokens. Plus {grounded} grounded Gemini requests: free within the first 5,000 "
          f"per month per tool, then ${GEMINI_GROUNDING_PER_1K:.0f}/1,000 (= ${grounded * GEMINI_GROUNDING_PER_1K / 1000:.2f} "
          f"if the free allowance is used up). Gemini prices: ${GEMINI_PRICE_IN_PER_M}/M in, "
          f"${GEMINI_PRICE_OUT_PER_M}/M out (paid tier, until 31 Dec 2026).", ""]
    return L


# ---------- main ----------

async def list_models(keys):
    async with httpx.AsyncClient(timeout=30) as http:
        for name, url in (("nvidia", NVIDIA_URL), ("openrouter", OPENROUTER_URL)):
            if not keys.get(name):
                print(f"{name}: no key")
                continue
            r = await http.get(f"{url}/models", headers={"Authorization": f"Bearer {keys[name].keys[0]}"})
            ids = sorted(m["id"] for m in r.json().get("data", []))
            print(f"{name}: {len(ids)} models\n  " + "\n  ".join(ids))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--providers", default="gemini,nvidia,openrouter")
    ap.add_argument("--nvidia-models", default=",".join(NVIDIA_MODELS))
    ap.add_argument("--openrouter-models", default=",".join(OPENROUTER_MODELS))
    ap.add_argument("--gemini-setups", default=",".join(GEMINI_SETUPS))
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="skip checking unknown names with Google Search")
    args = ap.parse_args()

    load_dotenv(HERE / ".env")
    keys = {"gemini": os.getenv("GEMINI_API_KEY"), "nvidia": KeyRing(os.getenv("NVIDIA_API_KEY")),
            "openrouter": KeyRing(os.getenv("OPENROUTER_API_KEY"))}
    if args.list_models:
        return await list_models(keys)
    if not keys["gemini"]:
        raise SystemExit("GEMINI_API_KEY is required (it extracts and checks names).")

    providers = [p for p in args.providers.split(",") if keys.get(p)]
    skipped = [p for p in args.providers.split(",") if p and not keys.get(p)]
    if skipped:
        print(f"Skipping (no key): {', '.join(skipped)}")
    jobs = []
    for p in providers:
        if p == "gemini":
            models = [("gemini", GEMINI_MODEL, s) for s in args.gemini_setups.split(",") if s]
        else:
            models = [(p, m, None) for m in getattr(args, f"{p}_models").split(",") if m]
        jobs += [(prov, m, s, prompt, run) for prov, m, s in models for prompt in PROMPTS
                 for run in range(1, args.runs + 1)]

    app_results = {k: v for k, v in json.loads(APP_RESULTS.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    gclient = genai.Client(api_key=keys["gemini"])
    sems = {"gemini": asyncio.Semaphore(6), "nvidia": asyncio.Semaphore(6), "openrouter": asyncio.Semaphore(6)}
    global PARTIAL
    out = HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    PARTIAL = out / "partial.jsonl"
    print(f"Running {len(jobs)} calls... (answers are saved to {PARTIAL} as they finish)")
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=240) as http:
        records = await asyncio.gather(*(run_one(j, gclient, http, keys, sems) for j in jobs))

    # Names seen in an app answer or a Google Maps answer are taken as real; the rest get checked.
    known = [n for apps in app_results.values() for l in apps.values() for n in l]
    known += [n for r in records for n in r.get("maps_places", [])]
    named = list(dict.fromkeys(n for r in records for n in r["businesses"]))
    real_status = {}
    to_check = []
    for n in named:
        if any(same_business(n, k) for k in known):
            real_status[n] = "operating"
        elif not any(same_business(n, c) for c in to_check):
            to_check.append(n)
    if to_check and not args.no_verify:
        print(f"Checking {len(to_check)} names not seen in any app or Maps answer...")
        checked = await verify(gclient, to_check)
        for n in to_check:
            v = next((v for k, v in checked.items() if same_business(n, k)), None)
            real_status[n] = v["status"] if v else "unchecked"
    wall = time.perf_counter() - t0

    with open(out / "raw.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out / "verify.json").write_text(json.dumps(real_status, indent=1, ensure_ascii=False), encoding="utf-8")
    report = build_report(records, app_results, real_status, args, wall)
    (out / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report.split("## Answers per prompt")[0])
    (out / "usage.json").write_text(json.dumps(USAGE, indent=1), encoding="utf-8")
    print(f"Saved to {out}")


if __name__ == "__main__":
    asyncio.run(main())
