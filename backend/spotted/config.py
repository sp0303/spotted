"""Settings read from the environment (and backend/.env when present)."""

import os
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

# backend/.env, wherever the process was started from (values already in the environment win).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    mongo_url: str = field(default_factory=lambda: os.getenv("MONGO_URL", "mongodb://localhost:27017/spotted"))
    mongo_db: str = field(default_factory=lambda: os.getenv("MONGO_DB", "spotted"))
    # Every collection name starts with this, so Spotted can share a database with other apps.
    mongo_collection_prefix: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_PREFIX", "spotted_"))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    # Crawl limits: profile extraction has a ~5-15 s budget (plan section 25).
    fetch_timeout_s: float = 8.0
    max_page_bytes: int = 2_000_000
    max_extra_pages: int = 5
    llm_timeout_s: float = 40.0
    # Development only: lets the crawler fetch localhost fixture sites. Never set in production.
    allow_private_hosts: bool = field(default_factory=lambda: os.getenv("SPOTTED_ALLOW_PRIVATE_HOSTS") == "1")
    # Chromium for the JavaScript-rendering check. Empty = Playwright's own browser; "off" disables rendering.
    chromium_path: str | None = field(default_factory=lambda: os.getenv("CHROMIUM_PATH") or None)
    render_timeout_s: float = 15.0
    # --- AI runs (build step 3) ---
    # OpenRouter key(s), comma separated (one per account): Perplexity and ChatGPT-with-search via OpenRouter.
    openrouter_keys: tuple[str, ...] = field(default_factory=lambda: tuple(
        k.strip() for k in os.getenv("OPENROUTER_API_KEY", "").split(",") if k.strip()))
    perplexity_model: str = field(default_factory=lambda: os.getenv("PERPLEXITY_MODEL", "perplexity/sonar"))
    chatgpt_model: str = field(default_factory=lambda: os.getenv("CHATGPT_MODEL", "openai/gpt-5-mini:online"))
    # Platforms for a free run, in order; ones without a key are left out (see platforms.py).
    ai_platforms: tuple[str, ...] = field(default_factory=lambda: tuple(
        os.getenv("AI_PLATFORMS", "gemini_search,gemini_maps,perplexity,chatgpt").split(",")))
    ai_call_timeout_s: float = field(default_factory=lambda: float(os.getenv("AI_CALL_TIMEOUT_S", "60")))
    # Where API calls leave from; answers can follow it (plan section 31), so it's recorded with each audit.
    server_region: str = field(default_factory=lambda: os.getenv("SERVER_REGION", "local"))
    # Gemini paid Standard tier prices, USD (pricing page, 24 Nov 2026; they double on 1 Jan 2027).
    gemini_price_in_per_m: float = field(default_factory=lambda: float(os.getenv("GEMINI_PRICE_IN_PER_M", "0.75")))
    gemini_price_out_per_m: float = field(default_factory=lambda: float(os.getenv("GEMINI_PRICE_OUT_PER_M", "3.75")))
    # Search/Maps grounding: 5,000 free requests a month per tool, then this per 1,000.
    gemini_grounding_per_1k: float = 14.0
    count_grounding_cost: bool = field(default_factory=lambda: os.getenv("COUNT_GROUNDING_COST") == "1")
    # Browser origins allowed to call the API (the Vite dev server by default).
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))
    )


settings = Settings()
