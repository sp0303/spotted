"""ChatGPT through OpenAI's own API ("API view", plan sections 6 and 27): the Responses API with web search on and
the customer's approximate location set to the target city.

Enabled only when OPENAI_API_KEY is set; until then ChatGPT stays "Coming soon". Request/response shape checked
against OpenAI's web search guide (Nov 2026):

  POST /v1/responses  {"model", "input", "tools": [{"type": "web_search", "user_location": {"type": "approximate",
                       "country", "city", "region"}}], "include": ["web_search_call.action.sources"]}
  output[]: {"type": "web_search_call", "action": {"type": "search", "query" | "queries", "sources": [{"url"}]}}
            {"type": "message", "content": [{"type": "output_text", "text", "annotations": [{"type": "url_citation",
                                                                                         "url", "title"}]}]}
  usage:    {"input_tokens", "output_tokens"}  (read defensively)

Settings (environment):
  OPENAI_API_KEY             enables the runner
  OPENAI_MODEL               default "gpt-5-mini"
  OPENAI_PRICE_IN_PER_M      USD per 1M input tokens, default 0.25
  OPENAI_PRICE_OUT_PER_M     USD per 1M output tokens, default 2.00
  OPENAI_WEB_SEARCH_PER_1K   USD per 1,000 web search calls, default 10.00
  OPENAI_CONCURRENCY         parallel calls across all audits, default 6
"""

import os

import httpx

from .platforms import Answer, PlatformError

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def openai_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or None


def openai_enabled() -> bool:
    return bool(openai_key())


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini")


def _f(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


def openai_cost(tokens_in: int, tokens_out: int, searches: int) -> float:
    return (tokens_in / 1e6 * _f("OPENAI_PRICE_IN_PER_M", "0.25") + tokens_out / 1e6 * _f("OPENAI_PRICE_OUT_PER_M", "2.0")
            + searches * _f("OPENAI_WEB_SEARCH_PER_1K", "10.0") / 1000)


def request_body(prompt: str, where: dict | None) -> dict:
    tool: dict = {"type": "web_search"}
    where = where or {}
    loc = {k: v for k, v in (("country", where.get("country_code")), ("city", where.get("city")),
                             ("region", where.get("region"))) if v}
    if loc:
        tool["user_location"] = {"type": "approximate", **loc}
    return {"model": openai_model(), "input": prompt, "tools": [tool],
            "include": ["web_search_call.action.sources"]}


def parse_response(data: dict, model: str) -> Answer:
    """Text, cited URLs, searches and cost from a Responses API result. Missing pieces are left empty."""
    texts: list[str] = []
    ans = Answer(text="", model=str(data.get("model") or model))
    cited: list[dict] = []
    consulted: list[dict] = []
    searches = 0
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            searches += 1
            action = item.get("action") or {}
            qs = action.get("queries") or ([action["query"]] if action.get("query") else [])
            ans.search_queries += [q for q in qs if isinstance(q, str) and q not in ans.search_queries]
            for s in action.get("sources") or []:
                if isinstance(s, dict) and s.get("url"):
                    consulted.append({"url": s["url"], "title": s.get("title")})
        elif item.get("type") == "message":
            for part in item.get("content") or []:
                if not isinstance(part, dict) or part.get("type") != "output_text":
                    continue
                texts.append(part.get("text") or "")
                for a in part.get("annotations") or []:
                    if isinstance(a, dict) and a.get("type") == "url_citation" and a.get("url"):
                        cited.append({"url": a["url"], "title": a.get("title")})
    ans.text = "\n\n".join(t for t in texts if t).strip() or str(data.get("output_text") or "").strip()
    # Cited sources first (what the answer points to), then ones it read but didn't cite.
    seen = set()
    for s in cited + consulted:
        if s["url"] not in seen:
            seen.add(s["url"])
            ans.sources.append(s)
    usage = data.get("usage") or {}
    ans.tokens_in = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    ans.tokens_out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    ans.cost_usd = openai_cost(ans.tokens_in, ans.tokens_out, searches)
    return ans


async def openai_answer(http: httpx.AsyncClient, prompt: str, where: dict | None) -> Answer:
    key = openai_key()
    if not key:
        raise PlatformError("OPENAI_API_KEY is not set.")
    body = request_body(prompt, where)
    try:
        r = await http.post(OPENAI_RESPONSES_URL, headers={"Authorization": f"Bearer {key}"}, json=body)
    except httpx.HTTPError as exc:
        raise PlatformError(f"OpenAI request failed: {type(exc).__name__}") from None
    if r.status_code >= 400:
        try:
            msg = (r.json().get("error") or {}).get("message") or r.text
        except ValueError:
            msg = r.text
        raise PlatformError(f"OpenAI {r.status_code}: {str(msg)[:200]}")
    try:
        data = r.json()
    except ValueError:
        raise PlatformError("OpenAI returned a response that isn't JSON.") from None
    if data.get("status") in ("failed", "incomplete") and not data.get("output"):
        raise PlatformError(f"OpenAI answer {data.get('status')}.")
    return parse_response(data, body["model"])
