"""Crawler registry (plan sections 2 and 20), seeded into the `crawlers` table.

Purposes are grouped so owners can choose: search & answer crawlers help you be found,
user-triggered fetchers open a page because a person asked, training controls only govern
model training. Every entry still needs checking against the vendor's current docs
(`verified_at` stays NULL until someone does).
"""

from dataclasses import dataclass

from psycopg import AsyncConnection


@dataclass(frozen=True)
class Crawler:
    token: str  # robots.txt product token, also crawlers.user_agent
    operator: str
    purpose: str  # crawler_group enum: search | user_fetch | training
    user_agent: str | None  # full UA string sent in access tests; None = control token that never fetches
    docs_url: str
    notes: str = ""

    @property
    def is_token_only(self) -> bool:
        return self.user_agent is None


_WEBKIT = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; {}; +{})"

CRAWLERS: list[Crawler] = [
    # Search & answer crawlers
    Crawler("Googlebot", "Google", "search",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers",
            "Google Search, including AI Overviews and AI Mode."),
    Crawler("Bingbot", "Microsoft", "search",
            "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0",
            "Bing Search; Copilot and ChatGPT search draw on Bing's index."),
    Crawler("OAI-SearchBot", "OpenAI", "search", _WEBKIT.format("OAI-SearchBot/1.0", "https://openai.com/searchbot"),
            "https://platform.openai.com/docs/bots", "ChatGPT search results."),
    Crawler("Claude-SearchBot", "Anthropic", "search",
            _WEBKIT.format("Claude-SearchBot/1.0", "Claude-SearchBot@anthropic.com"),
            "https://support.anthropic.com/en/articles/8896518", "Search indexing for Claude's answers."),
    Crawler("PerplexityBot", "Perplexity", "search",
            _WEBKIT.format("PerplexityBot/1.0", "https://perplexity.ai/perplexitybot"),
            "https://docs.perplexity.ai/guides/bots", "Perplexity search index."),
    Crawler("Applebot", "Apple", "search",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.4 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)",
            "https://support.apple.com/en-us/119829", "Siri, Spotlight and Safari suggestions."),
    Crawler("Amazonbot", "Amazon", "search",
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amazonbot/0.1; "
            "+https://developer.amazon.com/support/amazonbot) Chrome/119.0.6045.214 Safari/537.36",
            "https://developer.amazon.com/amazonbot", "Alexa answers and other Amazon services."),
    # User-triggered fetchers
    Crawler("ChatGPT-User", "OpenAI", "user_fetch", _WEBKIT.format("ChatGPT-User/1.0", "https://openai.com/bot"),
            "https://platform.openai.com/docs/bots", "Opens a page when a ChatGPT user's request needs it."),
    Crawler("Claude-User", "Anthropic", "user_fetch", _WEBKIT.format("Claude-User/1.0", "Claude-User@anthropic.com"),
            "https://support.anthropic.com/en/articles/8896518", "Opens a page when a Claude user asks."),
    Crawler("Perplexity-User", "Perplexity", "user_fetch",
            _WEBKIT.format("Perplexity-User/1.0", "https://perplexity.ai/perplexity-user"),
            "https://docs.perplexity.ai/guides/bots",
            "User-triggered; Perplexity has said it may not follow robots.txt for these. [verify]"),
    Crawler("Meta-ExternalFetcher", "Meta", "user_fetch",
            "meta-externalfetcher/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)",
            "https://developers.facebook.com/docs/sharing/webmasters/web-crawlers", "User-triggered fetches from Meta AI. [verify]"),
    # Training crawlers and control tokens
    Crawler("GPTBot", "OpenAI", "training", _WEBKIT.format("GPTBot/1.1", "https://openai.com/gptbot"),
            "https://platform.openai.com/docs/bots", "Model training. Separate from OAI-SearchBot."),
    Crawler("ClaudeBot", "Anthropic", "training", _WEBKIT.format("ClaudeBot/1.0", "claudebot@anthropic.com"),
            "https://support.anthropic.com/en/articles/8896518", "Model training."),
    Crawler("Meta-ExternalAgent", "Meta", "training",
            "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)",
            "https://developers.facebook.com/docs/sharing/webmasters/web-crawlers", "Meta AI / model training."),
    Crawler("Google-Extended", "Google", "training", None,
            "https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers",
            "robots.txt control token for Gemini training and grounding; does not affect Google Search."),
    Crawler("Applebot-Extended", "Apple", "training", None, "https://support.apple.com/en-us/119829",
            "robots.txt control token for Apple AI training; Applebot does the crawling."),
]

BY_TOKEN = {c.token: c for c in CRAWLERS}

PURPOSE_LABELS = {
    "search": "Search & answer crawlers (help you be found)",
    "user_fetch": "User-triggered fetchers (a person asked an AI to open your page)",
    "training": "Training controls (whether content may train AI models)",
}


async def seed_crawlers(conn: AsyncConnection) -> None:
    async with conn.cursor() as cur:
        await cur.executemany(
            """INSERT INTO crawlers (user_agent, operator, purpose, is_token_only, docs_url, notes)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_agent) DO UPDATE SET operator = EXCLUDED.operator, purpose = EXCLUDED.purpose,
                 is_token_only = EXCLUDED.is_token_only, docs_url = EXCLUDED.docs_url, notes = EXCLUDED.notes""",
            [(c.token, c.operator, c.purpose, c.is_token_only, c.docs_url, c.notes) for c in CRAWLERS],
        )
