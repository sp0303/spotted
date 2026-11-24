"""Try profile extraction from the command line, without a database.

    python -m spotted.cli https://example-florist.com
"""

import argparse
import asyncio
import json
import time

from .crawl import FetchError
from .llm import GeminiProfileLLM, LLMError
from .profile import extract_profile


async def main() -> int:
    ap = argparse.ArgumentParser(description="Extract a draft business profile from a website.")
    ap.add_argument("url")
    ap.add_argument("--model", default=None, help="Gemini model (default from GEMINI_MODEL)")
    ap.add_argument("--raw", action="store_true", help="also print the raw LLM output and structured hints")
    args = ap.parse_args()
    start = time.monotonic()
    try:
        profile, raw = await extract_profile(args.url, GeminiProfileLLM(model=args.model))
    except (FetchError, LLMError) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps(raw if args.raw else profile.model_dump(exclude_none=True), indent=2, ensure_ascii=False))
    print(f"\n{len(profile.pages_read)} pages read in {time.monotonic() - start:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
