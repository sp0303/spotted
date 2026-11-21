from spotted.crawl import fetch_site
from spotted.extract import extract_structured, page_text
from spotted.profile import SYSTEM_PROMPT, extract_profile


async def test_structured_facts(florist_site):
    site = await fetch_site("petallane.example")
    facts = extract_structured(site.pages)
    assert facts.names[0][0] == "Petal Lane Florist"
    assert ("Florist", "https://www.petallane.example/") in facts.schema_types
    assert facts.addresses[0][0] == {"street": "1200 Elm St", "city": "Dallas", "region": "TX",
                                     "postal_code": "75201", "country": "US", "lat": 32.781, "lng": -96.8}
    assert "Monday,Tuesday 09:00-18:00" in [h for h, _ in facts.hours]
    assert {p for p, _, _ in facts.social} == {"instagram", "facebook"}
    assert ("hello@petallane.example", "https://www.petallane.example/") in facts.emails
    assert {lang for lang, _ in facts.languages} == {"en"}


async def test_page_text_drops_scripts(florist_site):
    site = await fetch_site("petallane.example")
    text = page_text(site.homepage)
    assert "same-day across Dallas" in text and "do not read" not in text


async def test_extract_profile_keeps_extracted_and_inferred_apart(florist_site, fake_llm):
    profile, raw = await extract_profile("petallane.example", fake_llm)

    # Markup name wins; the LLM's shorter name becomes an alias.
    assert profile.name.value == "Petal Lane Florist" and profile.name.origin == "extracted"
    assert [a.value for a in profile.aliases] == ["Petal Lane"]

    services = {s.value: s for s in profile.services}
    assert services["Same-day delivery"].origin == "extracted"
    assert services["Same-day delivery"].source_url == "https://www.petallane.example/"
    assert services["Corporate events"].origin == "inferred"  # quote isn't on the site
    assert "same-day DELIVERY" not in services  # duplicate of an extracted service

    locs = profile.locations
    elm = [loc for loc in locs if loc.address == "1200 Elm St"]
    assert len(elm) == 1 and elm[0].origin == "extracted" and elm[0].lat == 32.781 and elm[0].country_code == "US"
    plano = next(loc for loc in locs if loc.city == "Plano")
    assert plano.is_physical is False and plano.origin == "extracted"
    fort_worth = next(loc for loc in locs if loc.city == "Fort Worth")
    assert fort_worth.origin == "inferred"

    assert [p.value for p in profile.phones] == ["+1 214-555-0142"]  # three copies, one number
    assert profile.target_customer.origin == "inferred"
    assert profile.differentiators[0].source_url == "https://www.petallane.example/about-us"
    assert [c.value for c in profile.suggested_competitors] == ["McShan Florist", "Dr Delphinium"]
    assert all(c.origin == "inferred" for c in profile.suggested_competitors)
    assert any("Fort Worth" in w for w in profile.warnings)
    assert any("competitors" in w for w in profile.warnings)

    system, prompt = fake_llm.calls[0]
    assert system == SYSTEM_PROMPT
    assert "### Page 2: https://www.petallane.example/about-us" in prompt
    assert raw["model"] == "fake-1" and raw["structured"]["phones"]
