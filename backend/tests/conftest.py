import os

import httpx
import pytest
import respx

from spotted import crawl
from spotted.models import LLMItem, LLMLocation, LLMProfile, LLMService

HOME_HTML = """<!doctype html><html lang="en-US"><head><title>Petal Lane Florist | Dallas Flowers</title>
<meta name="description" content="Fresh flowers and same-day delivery in Dallas.">
<meta property="og:site_name" content="Petal Lane Florist">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Florist","name":"Petal Lane Florist",
 "telephone":"+1 214-555-0142",
 "address":{"@type":"PostalAddress","streetAddress":"1200 Elm St","addressLocality":"Dallas",
            "addressRegion":"TX","postalCode":"75201","addressCountry":"US"},
 "geo":{"@type":"GeoCoordinates","latitude":32.781,"longitude":-96.800},
 "openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday"],
   "opens":"09:00","closes":"18:00"}],
 "sameAs":["https://www.instagram.com/petallane","https://example.org/not-social"]}
</script></head><body>
<nav><a href="/about-us">About</a> <a href="/contact">Contact</a> <a href="/weddings">Weddings</a>
<a href="https://other-site.com/contact">Partner</a> <a href="/menu.pdf">Price list</a></nav>
<h1>Dallas florist with same-day delivery</h1>
<p>We deliver same-day across Dallas, Plano and Richardson.</p>
<p>Wedding flowers, sympathy arrangements and weekly subscriptions.</p>
<a href="tel:+12145550142">Call us</a> <a href="mailto:hello@petallane.example">Email</a>
<a href="https://facebook.com/petallane">Facebook</a>
<script>var hidden = "do not read";</script>
</body></html>"""

ABOUT_HTML = """<html><body><h1>About</h1><p>Family-owned since 1998, Petal Lane grows its own peonies.</p></body></html>"""
CONTACT_HTML = """<html><body><p>Visit us at 1200 Elm St, Dallas, TX 75201.</p>
<a href="tel:(214) 555-0142">Call</a></body></html>"""


def fake_llm_profile() -> LLMProfile:
    return LLMProfile(
        name=LLMItem(value="Petal Lane", stated_on_site=True, evidence_quote="Petal Lane grows its own peonies", page=1),
        aliases=[LLMItem(value="Petal Lane Florist", stated_on_site=True, evidence_quote="Petal Lane Florist")],
        category=LLMItem(value="florist", stated_on_site=True, evidence_quote="Dallas florist with same-day delivery", page=0),
        services=[
            LLMService(value="Same-day delivery", stated_on_site=True, evidence_quote="We deliver same-day across Dallas", page=0),
            LLMService(value="Wedding flowers", stated_on_site=True, evidence_quote="Wedding flowers", page=0),
            # Quote not on any page: must be downgraded to inferred.
            LLMService(value="Corporate events", stated_on_site=True, evidence_quote="We cater to corporate events", page=0),
            LLMService(value="same-day DELIVERY", stated_on_site=False),
        ],
        locations=[
            LLMLocation(address="1200 Elm St", city="Dallas", region="TX", country_code="us", is_physical=True,
                        stated_on_site=True, evidence_quote="1200 Elm St, Dallas, TX 75201", page=2),
            LLMLocation(label="Service area", city="Plano", region="TX", country_code="US", is_physical=False,
                        stated_on_site=True, evidence_quote="Dallas, Plano and Richardson", page=0),
            LLMLocation(city="Fort Worth", country_code="US", is_physical=False, stated_on_site=False),
        ],
        differentiators=[LLMItem(value="Family-owned since 1998", stated_on_site=True,
                                 evidence_quote="Family-owned since 1998", page=1)],
        target_customer=LLMItem(value="Dallas residents sending flowers", stated_on_site=False),
        suggested_competitors=["McShan Florist", "Petal Lane", "Dr Delphinium"],
        notes=["Confirm whether you deliver to Fort Worth."],
    )


class FakeLLM:
    model = "fake-1"

    def __init__(self, profile: LLMProfile | None = None):
        self.profile = profile or fake_llm_profile()
        self.calls: list[tuple[str, str]] = []

    async def extract_profile(self, system: str, prompt: str) -> LLMProfile:
        self.calls.append((system, prompt))
        return self.profile


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def public_dns(monkeypatch):
    """Treat every host as public so mocked sites can be fetched."""
    async def ok(host: str) -> None:
        return None
    monkeypatch.setattr(crawl, "assert_public_host", ok)


@pytest.fixture
def florist_site(public_dns):
    html = {"content-type": "text/html; charset=utf-8"}
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://petallane.example/").respond(301, headers={"location": "https://www.petallane.example/"})
        mock.get("https://petallane.example/").respond(301, headers={"location": "https://www.petallane.example/"})
        mock.get("https://www.petallane.example/").respond(200, text=HOME_HTML, headers=html)
        mock.get("https://www.petallane.example/about-us").respond(200, text=ABOUT_HTML, headers=html)
        mock.get("https://www.petallane.example/contact").respond(200, text=CONTACT_HTML, headers=html)
        mock.get("https://www.petallane.example/weddings").respond(404, text="nope", headers=html)
        yield mock


@pytest.fixture
def mongo_url():
    url = os.getenv("TEST_MONGO_URL")
    if not url:
        pytest.skip("TEST_MONGO_URL not set")
    return url


# ---------- MongoDB (API tests) ----------
# TEST_MONGO_PREFIX lets several test runs share one database without dropping each other's collections.
TEST_DB = os.getenv("TEST_MONGO_DB", "spotted_test")
TEST_PREFIX = os.getenv("TEST_MONGO_PREFIX", "spotted_test_")


@pytest.fixture
def test_prefix():
    return TEST_PREFIX


def _drop_test_collections(database) -> None:
    """Only this run's prefixed collections are dropped, never other apps' data."""
    for name in database.list_collection_names():
        if name.startswith(TEST_PREFIX):
            database.drop_collection(name)


@pytest.fixture
def db(mongo_url):
    from pymongo import MongoClient

    with MongoClient(mongo_url) as mc:
        database = mc[TEST_DB]
        _drop_test_collections(database)
        yield database
        _drop_test_collections(database)


@pytest.fixture
def client(mongo_url, db, fake_llm, monkeypatch):
    """API test client on the test collections, with a fake LLM and no network geocoding."""
    from fastapi.testclient import TestClient

    from spotted import api, repo
    from spotted.config import Settings

    test_settings = Settings(mongo_url=mongo_url, mongo_db=TEST_DB, mongo_collection_prefix=TEST_PREFIX)
    monkeypatch.setattr(api, "settings", test_settings)
    monkeypatch.setattr(repo, "settings", test_settings)

    async def no_geocoder(query):  # tests never call OpenStreetMap
        return None

    monkeypatch.setattr(api, "get_geocoder", lambda: no_geocoder)
    api.app.dependency_overrides[api.get_llm] = lambda: fake_llm
    with TestClient(api.app) as c:
        yield c
    api.app.dependency_overrides.clear()
