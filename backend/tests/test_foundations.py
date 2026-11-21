import httpx
import pytest
import respx

from spotted.foundations import check_js_render, detect_cdn, detect_challenge, run_foundations
from spotted.crawl import Page
from spotted.render import RenderResult

from conftest import ABOUT_HTML, CONTACT_HTML, HOME_HTML

HTML = {"content-type": "text/html; charset=utf-8"}
CF = {"server": "cloudflare", "cf-ray": "8abc-DFW"}
ROBOTS = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nSitemap: https://www.petallane.example/sitemap.xml\n"
SITEMAP = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://www.petallane.example/</loc></url><url><loc>https://www.petallane.example/about-us</loc></url>
</urlset>"""
CHALLENGE = "<html><head><title>Just a moment...</title></head><body>cf-chl-widget</body></html>"


class FakeRenderer:
    def __init__(self, result):
        self.result = result

    async def render(self, url):
        return self.result


def homepage(request):
    ua = request.headers.get("user-agent", "")
    if "PerplexityBot" in ua or "ClaudeBot" in ua:  # Cloudflare "Block AI bots"
        return httpx.Response(403, text=CHALLENGE, headers=HTML | CF | {"cf-mitigated": "challenge"})
    return httpx.Response(200, text=HOME_HTML, headers=HTML | CF)


@pytest.fixture
def cf_site(public_dns):
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.petallane.example/").mock(side_effect=homepage)
        mock.get("http://www.petallane.example/").respond(301, headers={"location": "https://www.petallane.example/"})
        mock.get("https://www.petallane.example/robots.txt").respond(200, text=ROBOTS, headers={"content-type": "text/plain"})
        mock.get("https://www.petallane.example/sitemap.xml").respond(200, text=SITEMAP, headers={"content-type": "application/xml"})
        mock.get("https://www.petallane.example/about-us").respond(
            200, text=ABOUT_HTML.replace("<html>", '<html><head><meta name="robots" content="noindex,follow"></head>'),
            headers=HTML)
        mock.get("https://www.petallane.example/contact").respond(
            200, text=CONTACT_HTML.replace("<html>", '<html><head><link rel="canonical" href="https://other.example/c"></head>'),
            headers=HTML)
        mock.get("https://www.petallane.example/weddings").respond(404, headers=HTML)
        yield mock


async def test_full_run(cf_site):
    report = await run_foundations("https://www.petallane.example/", "Petal Lane Florist", ["+1 214-555-0142"],
                                   renderer=FakeRenderer(None))
    assert report.cdn == "cloudflare" and report.rendered is False
    by = {}
    for c in report.checks:
        by.setdefault(c.check_type, []).append(c)

    assert by["http_status"][0].status == "pass"
    assert by["robots_txt"][0].status == "pass"
    assert by["sitemap"][0].status == "pass" and by["sitemap"][0].evidence["url_count"] == 2

    cdn = by["cdn_waf"][0]
    assert cdn.status == "issue" and "PerplexityBot" in cdn.summary and "Cloudflare" in cdn.fix
    assert cdn.evidence_level == "likely"

    crawlers = {r.token: r for r in report.crawlers}
    assert crawlers["Googlebot"].result == "accessible" and crawlers["Googlebot"].robots == "no_rule"
    assert crawlers["GPTBot"].robots == "disallow" and crawlers["GPTBot"].result == "accessible"
    assert crawlers["PerplexityBot"].result == "likely_blocked" and crawlers["PerplexityBot"].challenge
    assert crawlers["Google-Extended"].token_only and crawlers["Google-Extended"].http_status is None

    noindex = {c.target: c.status for c in by["noindex"]}
    assert noindex["https://www.petallane.example/about-us"] == "issue"
    assert noindex["https://www.petallane.example/"] == "pass"
    canon = {c.target: c.status for c in by["canonical"]}
    assert canon["https://www.petallane.example/contact"] == "issue"

    assert by["js_render"][0].status == "pass"  # name and phone are in the raw HTML
    assert by["webmcp"][0].status == "opportunity"
    assert {c.status for t in ("google_index", "bing_index", "indexnow") for c in by[t]} == {"not_verified"}


async def test_only_training_crawlers_blocked_is_not_an_issue(public_dns):
    def home(request):
        if "GPTBot" in request.headers.get("user-agent", ""):
            return httpx.Response(403, text="Forbidden", headers=HTML)
        return httpx.Response(200, text=HOME_HTML, headers=HTML)
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://shop.example/").mock(side_effect=home)
        mock.route(host="shop.example").respond(404, headers=HTML)
        mock.get("http://shop.example/").respond(301, headers={"location": "https://shop.example/"})
        report = await run_foundations("https://shop.example/", "Petal Lane Florist", [], renderer=None)
    cdn = next(c for c in report.checks if c.check_type == "cdn_waf")
    assert cdn.status == "pass" and "GPTBot" in cdn.summary
    robots = next(c for c in report.checks if c.check_type == "robots_txt")
    assert robots.status == "pass" and "don't have a robots.txt" in robots.summary
    sitemap = next(c for c in report.checks if c.check_type == "sitemap")
    assert sitemap.status == "warning"


async def test_robots_blocking_google_is_an_issue(public_dns):
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://shop.example/").respond(200, text=HOME_HTML, headers=HTML)
        mock.get("https://shop.example/robots.txt").respond(200, text="User-agent: *\nDisallow: /\n")
        mock.route(host="shop.example").respond(404, headers=HTML)
        report = await run_foundations("https://shop.example/", "Petal Lane Florist", [], renderer=None)
    robots = next(c for c in report.checks if c.check_type == "robots_txt")
    assert robots.status == "issue" and "Googlebot and Bingbot" in robots.summary
    assert next(c for c in report.checks if c.check_type == "cdn_waf").status == "issue"


def test_js_render_with_browser():
    shell = Page(url="https://spa.example/", status=200,
                 html='<html><body><div id="root"></div><script src="/app.js"></script></body></html>')
    rendered = RenderResult(url=shell.url, text="Petal Lane Florist " + "flowers " * 300 + " 214-555-0142",
                            words=303, links=12)
    check = check_js_render(shell, rendered, "Petal Lane Florist", ["+1 214-555-0142"])
    assert check.status == "issue" and "0 words without it" in check.summary
    # Without a browser we can still see it's an empty shell.
    assert check_js_render(shell, None, "Petal Lane Florist", []).status == "issue"


def test_js_render_name_only_in_js():
    words = " ".join(["flowers"] * 200)
    page = Page(url="https://a.example/", status=200, html=f"<html><body><p>{words}</p></body></html>")
    rendered = RenderResult(url=page.url, text=f"Petal Lane Florist {words}", words=203, links=0)
    check = check_js_render(page, rendered, "Petal Lane Florist", [])
    assert check.status == "warning" and "name" in check.summary


def test_cdn_and_challenge_detection():
    assert detect_cdn({"server": "cloudflare"}) == "cloudflare"
    assert detect_cdn({"x-vercel-id": "x"}) == "vercel"
    assert detect_cdn({"server": "nginx"}) is None
    assert detect_challenge(Page(url="u", status=403, html=CHALLENGE)) == "cloudflare"
    assert detect_challenge(Page(url="u", status=200, html=HOME_HTML)) is None
