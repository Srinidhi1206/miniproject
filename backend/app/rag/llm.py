"""Optional LLM provider for the explanation layer.

The LLM never classifies. It only receives (a) the verdict already computed by
the risk engine, (b) the evidence list, (c) passages retrieved from the
knowledge base, and rewrites them into plain language. Its output is a fixed
Pydantic schema; anything that fails validation is discarded and the
deterministic template explanation is used instead.

Provider is chosen with LLM_PROVIDER (none | anthropic).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.config import get_settings

log = logging.getLogger("sentinel.llm")


class LLMExplanation(BaseModel):
    summary: str = Field(description="2-3 plain sentences explaining the verdict to a non-technical person.")
    why_it_matters: list[str] = Field(description="2-4 short points, each tied to one piece of evidence.")


class LLMProvider(Protocol):
    name: str

    def explain(self, system: str, prompt: str) -> LLMExplanation | None: ...


class AnthropicProvider:
    def __init__(self, api_key: str, model: str):
        import anthropic  # optional dependency, imported lazily

        self._anthropic = anthropic
        # Short timeout + one retry: the explanation must never stall the scan.
        self.client = anthropic.Anthropic(api_key=api_key, timeout=20.0, max_retries=1)
        self.model = model
        self.name = f"anthropic:{model}"

    def explain(self, system: str, prompt: str) -> LLMExplanation | None:
        a = self._anthropic
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=2000,
                system=system,
                output_config={"effort": "low"},  # short rewriting task
                messages=[{"role": "user", "content": prompt}],
                output_format=LLMExplanation,
            )
        except a.AuthenticationError:
            log.error("LLM provider rejected the API key; using template explanations")
            return None
        except a.RateLimitError:
            log.warning("LLM provider rate limited; using template explanation")
            return None
        except a.APIStatusError as exc:
            log.warning("LLM provider error %s; using template explanation", exc.status_code)
            return None
        except a.APIConnectionError:
            log.warning("LLM provider unreachable; using template explanation")
            return None
        if response.stop_reason == "refusal":
            return None
        return response.parsed_output


@lru_cache
def get_llm() -> LLMProvider | None:
    s = get_settings()
    if s.llm_provider == "anthropic":
        if not s.llm_api_key:
            log.warning("LLM_PROVIDER=anthropic but LLM_API_KEY is empty; LLM disabled")
            return None
        try:
            return AnthropicProvider(s.llm_api_key, s.llm_model)
        except Exception as exc:  # pragma: no cover
            log.warning("Could not initialise LLM provider: %s", exc)
            return None
    return None
