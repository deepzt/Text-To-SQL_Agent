from __future__ import annotations

from .base import LLMProvider, ProviderResponse, ToolUseBlock
from .claude_provider import ClaudeProvider
from .ollama_provider import OllamaProvider


def get_provider(config) -> LLMProvider:
    """Factory: returns the correct LLMProvider based on config."""
    if config.LLM_PROVIDER == "ollama":
        return OllamaProvider(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
        )
    return ClaudeProvider(
        api_key=config.ANTHROPIC_API_KEY,
        model=config.CLAUDE_MODEL,
        enable_caching=config.ENABLE_PROMPT_CACHING,
    )


__all__ = [
    "LLMProvider",
    "ProviderResponse",
    "ToolUseBlock",
    "ClaudeProvider",
    "OllamaProvider",
    "get_provider",
]
