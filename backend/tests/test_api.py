import psycopg
import pytest
from fastapi.testclient import TestClient

from spotted import api
from spotted.config import Settings


@pytest.fixture
def client(database_url, fake_llm, monkeypatch):
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    monkeypatch.setattr(api, "settings", Settings(database_url=database_url))
    api.app.dependency_overrides[api.get_llm] = lambda: fake_llm
    with TestClient(api.app) as c:
        yield c
    api.app.dependency_overrides.clear()


def test_extract_then_confirm(client, florist_site, database_url):
    resp = client.post("/api/profiles", json={"url": "petallane.example"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["confirmed"] is False
    bid = body["business_id"]

    got = client.get(f"/api/businesses/{bid}").json()
    assert got["profile"]["name"]["value"] == "Petal Lane Florist"

    # Owner edits: drops the guessed Fort Worth area and an inferred service, adds a competitor.
    profile = got["profile"]
    profile["locations"] = [loc for loc in profile["locations"] if loc["city"] != "Fort Worth"]
    profile["services"] = [s for s in profile["services"] if s["value"] != "Corporate events"]
    profile["suggested_competitors"].append({"value": "Bloom Room", "origin": "inferred"})
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 200, resp.text
    confirmed = resp.json()
    assert confirmed["confirmed"] is True
    assert confirmed["profile"]["name"]["origin"] == "confirmed"
    assert confirmed["profile"]["services"][0]["source_url"]  # where it came from is kept
    assert confirmed["profile"]["warnings"] == []

    with psycopg.connect(database_url) as conn:
        row = conn.execute("SELECT name, category, phones, field_origins, profile_raw IS NOT NULL, confirmed_at "
                           "FROM businesses WHERE id = %s", (bid,)).fetchone()
        assert row[0] == "Petal Lane Florist" and row[1] == "florist"
        assert row[2] == ["+1 214-555-0142"]
        assert row[3]["name"] == "confirmed" and row[4] and row[5] is not None
        locs = conn.execute("SELECT city, is_physical, country_code, origin FROM business_locations "
                            "WHERE business_id = %s ORDER BY city", (bid,)).fetchall()
        assert locs == [("Dallas", True, "US", "confirmed"), ("Plano", False, "US", "confirmed")]
        assert conn.execute("SELECT count(*) FROM services WHERE business_id = %s", (bid,)).fetchone()[0] == 2
        comps = conn.execute("SELECT name FROM competitors WHERE business_id = %s ORDER BY name", (bid,)).fetchall()
        assert [c[0] for c in comps] == ["Bloom Room", "Dr Delphinium", "McShan Florist"]
        aliases = conn.execute("SELECT alias FROM business_aliases WHERE business_id = %s", (bid,)).fetchall()
        assert aliases == [("Petal Lane",)]

    # Confirming again replaces the child rows rather than duplicating them.
    assert client.put(f"/api/businesses/{bid}/profile", json=confirmed["profile"]).status_code == 200
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(*) FROM business_locations WHERE business_id = %s",
                            (bid,)).fetchone()[0] == 2


def test_confirm_requires_country_and_target(client, florist_site):
    bid = client.post("/api/profiles", json={"url": "petallane.example"}).json()["business_id"]
    profile = client.get(f"/api/businesses/{bid}").json()["profile"]
    profile["locations"][0]["country_code"] = None
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 422 and "country" in resp.json()["detail"]
    profile["locations"] = []
    resp = client.put(f"/api/businesses/{bid}/profile", json=profile)
    assert resp.status_code == 422 and "customers to find you" in resp.json()["detail"]


def test_bad_urls_get_plain_errors(client):
    resp = client.post("/api/profiles", json={"url": "localhost"})
    assert resp.status_code == 422 and "website address" in resp.json()["detail"]
    resp = client.post("/api/profiles", json={"url": "http://127.0.0.1/"})
    assert resp.status_code == 422 and "isn't a public website" in resp.json()["detail"]


def test_unknown_business_is_404(client):
    assert client.get("/api/businesses/00000000-0000-0000-0000-000000000000").status_code == 404
