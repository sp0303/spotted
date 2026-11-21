"""LLM adapter for profile extraction. Thin on purpose (plan section 26: direct provider SDKs)."""

import asyncio
from typing import Protocol

from .config import settings
from .models import LLMProfile


class LLMError(Exception):
    """The LLM call failed; message is safe to show."""


class ProfileLLM(Protocol):
    model: str

    async def extract_profile(self, system: str, prompt: str) -> LLMProfile: ...


class GeminiProfileLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from google import genai

        key = api_key or settings.gemini_api_key
        if not key:
            raise LLMError("GEMINI_API_KEY is not set.")
        self.model = model or settings.gemini_model
        self._client = genai.Client(api_key=key)

    async def extract_profile(self, system: str, prompt: str) -> LLMProfile:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=LLMProfile,
            temperature=0.1,
        )
        try:
            resp = await asyncio.wait_for(
                self._client.aio.models.generate_content(model=self.model, contents=prompt, config=config),
                timeout=settings.llm_timeout_s,
            )
        except TimeoutError:
            raise LLMError("Profile extraction timed out.") from None
        except errors.APIError as exc:
            raise LLMError(f"Gemini error {exc.code}: {exc.message}") from None
        if isinstance(resp.parsed, LLMProfile):
            return resp.parsed
        try:
            return LLMProfile.model_validate_json(resp.text or "")
        except ValueError:
            raise LLMError("Gemini returned a profile we couldn't read.") from None


def default_llm() -> ProfileLLM:
    return GeminiProfileLLM()
