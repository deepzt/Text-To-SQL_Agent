from __future__ import annotations

from .base import LLMProvider, ProviderResponse, ToolUseBlock


def get_provider(config) -> LLMProvider:
    """Factory: returns the correct LLMProvider based on config."""
    if config.LLM_PROVIDER == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
        )
    if config.LLM_PROVIDER == "claude":
        from .claude_provider import ClaudeProvider
        return ClaudeProvider(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.CLAUDE_MODEL,
            enable_caching=config.ENABLE_PROMPT_CACHING,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {config.LLM_PROVIDER!r}. Choose 'claude' or 'ollama'.")


__all__ = [
    "LLMProvider",
    "ProviderResponse",
    "ToolUseBlock",
    "get_provider",
]
