"""Business profile as shown to the owner for confirmation.

Every value records where it came from (plan section 2, step 2):
  extracted - stated on the website (source_url, and evidence where we have a quote)
  inferred  - our guess from the site's content or general knowledge; the owner must check it
  confirmed - the owner confirmed or entered it
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Origin = Literal["extracted", "inferred", "confirmed"]


class Fact(BaseModel):
    value: str
    origin: Origin
    source_url: str | None = None
    evidence: str | None = None  # short quote from the page, when origin is "extracted"


class Service(Fact):
    description: str | None = None


class Location(BaseModel):
    label: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country_code: str | None = Field(default=None, description="ISO 3166-1 alpha-2")
    postal_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_physical: bool = True  # false = service area only
    is_target: bool = True
    priority: int = 1
    origin: Origin
    source_url: str | None = None
    evidence: str | None = None

    @field_validator("country_code")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("country_code must be a two-letter ISO code")
        return v


class SocialProfile(BaseModel):
    platform: str
    url: str
    origin: Origin = "extracted"
    source_url: str | None = None


class BusinessProfile(BaseModel):
    website_url: str
    domain: str
    name: Fact
    aliases: list[Fact] = []
    category: Fact | None = None
    subcategories: list[Fact] = []
    description: Fact | None = None
    services: list[Service] = []
    locations: list[Location] = []
    phones: list[Fact] = []
    emails: list[Fact] = []
    hours: list[Fact] = []
    languages: list[Fact] = []
    target_customer: Fact | None = None
    differentiators: list[Fact] = []
    social_profiles: list[SocialProfile] = []
    suggested_competitors: list[Fact] = []
    # What the owner should look at before confirming, in plain language.
    warnings: list[str] = []
    pages_read: list[str] = []


class ExtractRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2048, examples=["mcshanflorist.com"])


class StoredProfile(BaseModel):
    business_id: str
    confirmed: bool
    profile: BusinessProfile


# ---------------------------------------------------------------------------
# What the LLM returns (Gemini structured output). Kept flat and simple: the
# schema subset accepted by structured output does not cover every pydantic feature.
# ---------------------------------------------------------------------------


class LLMItem(BaseModel):
    value: str
    stated_on_site: bool = Field(description="true only if the website text says this directly")
    evidence_quote: str | None = Field(
        default=None, description="exact short quote (under 25 words) copied from the page text when stated_on_site"
    )
    page: int | None = Field(default=None, description="index of the page the quote comes from")


class LLMService(LLMItem):
    description: str | None = None


class LLMLocation(BaseModel):
    label: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country_code: str | None = None
    postal_code: str | None = None
    is_physical: bool = Field(description="true for a shop/office customers can visit; false for a service area")
    stated_on_site: bool
    evidence_quote: str | None = None
    page: int | None = None


class LLMProfile(BaseModel):
    name: LLMItem
    aliases: list[LLMItem] = []
    category: LLMItem | None = None
    subcategories: list[LLMItem] = []
    description: LLMItem | None = None
    services: list[LLMService] = []
    locations: list[LLMLocation] = []
    target_customer: LLMItem | None = None
    differentiators: list[LLMItem] = []
    languages: list[LLMItem] = []
    suggested_competitors: list[str] = []
    notes: list[str] = Field(default=[], description="anything unclear the owner should check")

