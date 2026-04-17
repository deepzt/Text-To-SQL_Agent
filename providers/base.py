from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ProviderResponse:
    content_text: str
    tool_uses: list[ToolUseBlock] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw: Any = None


class LLMProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
        max_tokens: int = 4096,
        on_token: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
    ) -> ProviderResponse:
        """Send a chat request and return a ProviderResponse."""

    @property
    @abstractmethod
    def supports_thinking(self) -> bool:
        """Whether this provider supports extended/adaptive thinking."""

    @property
    @abstractmethod
    def supports_prompt_caching(self) -> bool:
        """Whether this provider supports prompt caching."""
