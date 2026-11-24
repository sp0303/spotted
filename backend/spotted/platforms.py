"""AI platforms for the AI runs (build step 3), all through official APIs ("API view", plan section 6).

Each platform answers a prompt the way a customer would ask it and reports what it used: the text,
the web sources and Maps places it relied on, the searches it ran, tokens and cost.

  gemini_search  Gemini + Google Search grounding         (platform "gemini", search on)
  gemini_maps    Gemini + Google Maps at the target city  (platform "gemini", needs lat/lng)
  gemini_memory  Gemini with no tools                     (platform "gemini", search off: model knowledge)
  perplexity     Perplexity Sonar via OpenRouter           (platform "perplexity", search on)
  chatgpt        OpenAI Responses API + web search, approximate location = target city (openai_runner.py) when
                 OPENAI_API_KEY is set; otherwise OpenAI GPT via OpenRouter web search (research only)

A platform is offered only when its key is set. ChatGPT, Perplexity, Claude, Copilot and Google AI Mode are
"coming soon": shown to owners but not run until their keys are added (OPENAI_API_KEY etc.). The OpenRouter path
for Perplexity/ChatGPT stays available for research with OPENROUTER_ENABLED=1 (needs credit on the account).

Model comparison (research/model_compare, 24 Nov 2026): only web-search models are worth running. Models without
search overlapped 2-17% with what the apps show and named closed or out-of-town businesses; see docs/plan.md.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from .config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class Answer:
    text: str
    sources: list[dict] = field(default_factory=list)  # {"url", "title"}
    maps_places: list[dict] = field(default_factory=list)  # {"title", "uri", "place_id"}
    search_queries: list[str] = field(default_factory=list)
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class PlatformError(Exception):
    """A platform call failed; the message is safe to show."""


@dataclass(frozen=True)
class Platform:
    key: str
    platform: str  # schema ai_platform enum
    label: str
    search_enabled: bool
    grounding: str | None
    location_method: str  # schema location_method enum
    needs_latlng: bool = False


PLATFORMS = {
    "gemini_search": Platform("gemini_search", "gemini", "Gemini (Google Search)", True, "google_search", "prompt_only"),
    "gemini_maps": Platform("gemini_maps", "gemini", "Gemini (Google Maps)", True, "google_maps", "maps_latlng",
                            needs_latlng=True),
    "perplexity": Platform("perplexity", "perplexity", "Perplexity", True, "web_search", "prompt_only"),
    "chatgpt": Platform("chatgpt", "chatgpt", "ChatGPT (API, web search)", True, "web_search", "api_location"),
    "gemini_memory": Platform("gemini_memory", "gemini", "Gemini (no search)", False, None, "prompt_only"),
}

# Shown as "Coming soon" until a key is configured (no runner yet for claude, copilot, google_ai_mode).
COMING_SOON = {
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "claude": "Claude",
    "copilot": "Microsoft Copilot",
    "google_ai_mode": "Google AI Mode",
}


def available_platforms() -> list[str]:
    keys = []
    if settings.gemini_api_key:
        keys += ["gemini_search", "gemini_maps", "gemini_memory"]
    if settings.openrouter_keys and os.getenv("OPENROUTER_ENABLED") == "1":
        keys += ["perplexity", "chatgpt"]
    if os.getenv("OPENAI_API_KEY"):
        keys.append("chatgpt")  # direct OpenAI Responses API (openai_runner.py)
    return [k for k in PLATFORMS if k in keys]


# How each coming-soon platform will be measured (shown to owners as a tooltip/description).
COMING_SOON_NOTES = {
    "chatgpt": "OpenAI API with web search, located in your city (needs an OpenAI key)",
    "perplexity": "Perplexity Sonar API (needs a Perplexity key)",
    "claude": "Anthropic API with web search (needs an Anthropic key)",
    "copilot": "via Azure grounding with Bing (needs an Azure key)",
    "google_ai_mode": "no public API yet; use the Check it yourself link for now",
}


def coming_soon() -> list[dict]:
    ready = set(available_platforms())
    return [{"key": k, "label": label, "note": COMING_SOON_NOTES.get(k, "")}
            for k, label in COMING_SOON.items() if k not in ready]


def default_platforms() -> list[str]:
    return [k for k in settings.ai_platforms if k in available_platforms()]


def chatgpt_direct() -> bool:
    """ChatGPT goes to OpenAI directly (with the target city as its location) when the key is set."""
    return bool(os.getenv("OPENAI_API_KEY"))


def location_method(platform: Platform) -> str:
    if platform.key == "chatgpt" and not chatgpt_direct():
        return "prompt_only"  # the OpenRouter route has no location setting
    return platform.location_method


class Answerer(Protocol):
    # `where` ({city, region, country_code}) is passed only to platforms whose location_method is "api_location".
    async def answer(self, platform: Platform, prompt: str, lat: float | None, lng: float | None,
                     **kw) -> Answer: ...


def gemini_cost(tokens_in: int, tokens_out: int, grounded: bool) -> float:
    cost = tokens_in / 1e6 * settings.gemini_price_in_per_m + tokens_out / 1e6 * settings.gemini_price_out_per_m
    # Grounded requests are free for the first 5,000 a month per tool; count them at list price to stay safe.
    return cost + (settings.gemini_grounding_per_1k / 1000 if grounded and settings.count_grounding_cost else 0.0)


class LiveAnswerer:
    """Calls the real providers. Per-provider concurrency caps keep many audits from flooding a key."""

    def __init__(self):
        self._gemini = None
        self._http = httpx.AsyncClient(timeout=settings.ai_call_timeout_s)
        # Global per-provider caps across every running audit (plan 25); excess calls queue here.
        self._sems = {"gemini": asyncio.Semaphore(int(os.getenv("GEMINI_CONCURRENCY", "8"))),
                      "openrouter": asyncio.Semaphore(int(os.getenv("OPENROUTER_CONCURRENCY", "6"))),
                      "openai": asyncio.Semaphore(int(os.getenv("OPENAI_CONCURRENCY", "6")))}
        self._or_index = 0

    def _gemini_client(self):
        if self._gemini is None:
            from google import genai

            self._gemini = genai.Client(api_key=settings.gemini_api_key)
        return self._gemini

    async def answer(self, platform: Platform, prompt: str, lat: float | None, lng: float | None,
                     where: dict | None = None) -> Answer:
        t0 = time.perf_counter()
        try:
            if platform.key == "chatgpt" and chatgpt_direct():
                from .openai_runner import openai_answer

                async with self._sems["openai"]:
                    ans = await asyncio.wait_for(openai_answer(self._http, prompt, where), settings.ai_call_timeout_s)
            elif platform.key.startswith("gemini"):
                async with self._sems["gemini"]:
                    ans = await asyncio.wait_for(self._gemini_answer(platform, prompt, lat, lng),
                                                 settings.ai_call_timeout_s)
            else:
                async with self._sems["openrouter"]:
                    ans = await asyncio.wait_for(self._openrouter_answer(platform, prompt), settings.ai_call_timeout_s)
        except TimeoutError:
            raise PlatformError(f"No answer within {settings.ai_call_timeout_s:.0f} seconds.") from None
        ans.latency_ms = int((time.perf_counter() - t0) * 1000)
        return ans

    async def _gemini_answer(self, platform: Platform, prompt: str, lat, lng) -> Answer:
        from google.genai import errors, types

        config = types.GenerateContentConfig()
        if platform.grounding == "google_search":
            config.tools = [types.Tool(google_search=types.GoogleSearch())]
        elif platform.grounding == "google_maps":
            config.tools = [types.Tool(google_maps=types.GoogleMaps())]
            config.tool_config = types.ToolConfig(
                retrieval_config=types.RetrievalConfig(lat_lng=types.LatLng(latitude=lat, longitude=lng)))
        model = settings.gemini_model
        try:
            resp = await self._gemini_client().aio.models.generate_content(model=model, contents=prompt, config=config)
        except errors.APIError as exc:
            raise PlatformError(f"Gemini error {exc.code}: {exc.message}") from None
        ans = Answer(text=resp.text or "", model=model)
        m = resp.usage_metadata
        if m:
            ans.tokens_in = (m.prompt_token_count or 0) + (getattr(m, "tool_use_prompt_token_count", 0) or 0)
            ans.tokens_out = (m.candidates_token_count or 0) + (getattr(m, "thoughts_token_count", 0) or 0)
        try:
            gm = resp.candidates[0].grounding_metadata
        except (AttributeError, IndexError, TypeError):
            gm = None
        if gm:
            ans.search_queries = list(gm.web_search_queries or [])
            for ch in gm.grounding_chunks or []:
                web = getattr(ch, "web", None)
                if web and (web.uri or web.title):
                    # Gemini gives a redirect URL; the title is the source's domain.
                    ans.sources.append({"url": web.uri, "title": web.title})
                maps = getattr(ch, "maps", None)
                if maps and getattr(maps, "title", None):
                    ans.maps_places.append({"title": maps.title, "uri": getattr(maps, "uri", None),
                                            "place_id": getattr(maps, "place_id", None)})
        ans.cost_usd = gemini_cost(ans.tokens_in, ans.tokens_out, platform.grounding is not None)
        return ans

    async def _openrouter_answer(self, platform: Platform, prompt: str) -> Answer:
        model = settings.perplexity_model if platform.key == "perplexity" else settings.chatgpt_model
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000, "usage": {"include": True}}
        keys = settings.openrouter_keys
        self._or_index += 1
        err = "No OpenRouter key."
        for i in range(len(keys)):  # another account's key when one is out of credit or rate-limited
            key = keys[(self._or_index + i) % len(keys)]
            r = await self._http.post(OPENROUTER_URL, headers={"Authorization": f"Bearer {key}"}, json=body)
            if r.status_code < 400:
                break
            err = f"OpenRouter {r.status_code}: {r.text[:200]}"
            if r.status_code not in (401, 402, 403, 429):
                raise PlatformError(err)
        else:
            raise PlatformError("Out of OpenRouter credit." if "402" in err else err)
        data = r.json()
        msg = data["choices"][0]["message"]
        ans = Answer(text=(msg.get("content") or "").strip(), model=model)
        for a in msg.get("annotations") or []:
            c = a.get("url_citation") or {}
            if a.get("type") == "url_citation" and c.get("url"):
                ans.sources.append({"url": c["url"], "title": c.get("title")})
        known = {s["url"] for s in ans.sources}
        ans.sources += [{"url": u, "title": None} for u in data.get("citations") or [] if u not in known]
        usage = data.get("usage") or {}
        ans.tokens_in = usage.get("prompt_tokens") or 0
        ans.tokens_out = usage.get("completion_tokens") or 0
        ans.cost_usd = float(usage.get("cost") or 0.0)
        return ans
