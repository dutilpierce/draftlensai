from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedModel:
    provider: str  # openai | anthropic | google
    model_id: str


@dataclass(frozen=True)
class AgentModelAssignment:
    author_intent: ResolvedModel
    skeptical_reviewer: ResolvedModel
    consistency_parser: ResolvedModel
    arbiter: ResolvedModel
