from __future__ import annotations

from typing import Any

from draftlens_api.config import ProviderEnv, Settings
from draftlens_api.providers.anthropic_adapter import AnthropicProviderAdapter
from draftlens_api.providers.base import BaseLLMProvider
from draftlens_api.providers.gemini_adapter import GeminiProviderAdapter
from draftlens_api.providers.openai_adapter import OpenAIProviderAdapter
from draftlens_api.routing.agent_assignment import AgentModelAssignment, ResolvedModel


def parse_model_ref(ref: str) -> ResolvedModel:
    ref = ref.strip()
    if "/" in ref:
        prov, mid = ref.split("/", 1)
    else:
        prov, mid = "openai", ref
    prov = prov.strip().lower()
    if prov in {"google", "gemini"}:
        prov = "google"
    if prov not in {"openai", "anthropic", "google"}:
        prov = "openai"
    return ResolvedModel(provider=prov, model_id=mid.strip())


class ModelRegistry:
    """Configurable provider routing; adapters are shared instances keyed by provider."""

    def __init__(self, routing: dict[str, Any], adapters: dict[str, BaseLLMProvider]) -> None:
        self._routing = routing
        self._adapters = adapters

    @classmethod
    def from_settings(cls, settings: Settings, penv: ProviderEnv) -> "ModelRegistry":
        routing = dict(settings.model_routing())
        gm = (settings.draftlens_gemini_model or "").strip()
        if gm:
            routing["consistency_parser_model"] = gm if "/" in gm else f"google/{gm}"
        adapters: dict[str, BaseLLMProvider] = {
            "openai": OpenAIProviderAdapter(penv.openai_api_key),
            "anthropic": AnthropicProviderAdapter(penv.anthropic_api_key),
            "google": GeminiProviderAdapter(penv.gemini_api_key),
        }
        return cls(routing=routing, adapters=adapters)

    def assignment(self) -> AgentModelAssignment:
        mr = self._routing
        return AgentModelAssignment(
            author_intent=parse_model_ref(str(mr.get("author_intent_model", ""))),
            skeptical_reviewer=parse_model_ref(str(mr.get("skeptical_reviewer_model", ""))),
            consistency_parser=parse_model_ref(str(mr.get("consistency_parser_model", ""))),
            arbiter=parse_model_ref(str(mr.get("arbiter_model", ""))),
        )

    def adapter(self, resolved: ResolvedModel) -> BaseLLMProvider:
        return self._adapters[resolved.provider]
