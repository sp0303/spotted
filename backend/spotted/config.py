"""Settings read from the environment (and backend/.env when present)."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://spotted:spotted@localhost:5432/spotted")
    )
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    # Crawl limits: profile extraction has a ~5-15 s budget (plan section 25).
    fetch_timeout_s: float = 8.0
    max_page_bytes: int = 2_000_000
    max_extra_pages: int = 5
    llm_timeout_s: float = 40.0


settings = Settings()
