import pytest

from spotted import crawl
from spotted.crawl import FetchError, Page, fetch_site, normalize_url, pick_key_pages


@pytest.mark.parametrize("raw,expected", [
    ("petallane.example", "https://petallane.example/"),
    ("  HTTP://WWW.Petallane.Example/shop#top ", "http://www.petallane.example/shop"),
    ("https://petallane.example:8443/a?b=1", "https://petallane.example:8443/a?b=1"),
])
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "ftp://x.com", "localhost", "javascript:alert(1)"])
def test_normalize_url_rejects(raw):
    with pytest.raises(FetchError):
        normalize_url(raw)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "10.0.0.5", "169.254.169.254", "[::1]"])
async def test_private_hosts_are_blocked(host):
    with pytest.raises(FetchError, match="isn't a public website|Couldn't find"):
        await crawl.assert_public_host(host.strip("[]"))


async def test_redirect_to_private_address_is_blocked(public_dns, monkeypatch):
    import respx

    async def guard(host):
        if host == "169.254.169.254":
            raise FetchError("169.254.169.254 isn't a public website.")
    monkeypatch.setattr(crawl, "assert_public_host", guard)
    with respx.mock() as mock:
        mock.get("https://evil.example/").respond(302, headers={"location": "http://169.254.169.254/latest/"})
        with pytest.raises(FetchError, match="isn't a public website"):
            await fetch_site("evil.example")


def test_pick_key_pages_prefers_contact_and_stays_on_site():
    page = Page(url="https://www.shop.example/", status=200, html="""
        <a href="/blog/post-1">Blog</a><a href="/contact">Contact</a><a href="/about">About us</a>
        <a href="https://shop.example/services">Services</a><a href="https://elsewhere.example/contact">x</a>
        <a href="tel:123">t</a><a href="/files/menu.pdf">Menu</a><a href="/">Home</a>""")
    assert pick_key_pages(page, 5) == [
        "https://www.shop.example/contact",
        "https://www.shop.example/about",
        "https://shop.example/services",
    ]


async def test_fetch_site_follows_redirects_and_skips_failed_pages(florist_site):
    site = await fetch_site("http://petallane.example")
    assert site.final_url == "https://www.petallane.example/"
    assert site.domain == "petallane.example"
    assert [p.url for p in site.pages] == [
        "https://www.petallane.example/",
        "https://www.petallane.example/contact",
        "https://www.petallane.example/about-us",
    ]


async def test_fetch_site_reports_http_errors(public_dns):
    import respx
    with respx.mock() as mock:
        mock.get("https://down.example/").respond(503)
        with pytest.raises(FetchError, match="HTTP 503"):
            await fetch_site("down.example")
