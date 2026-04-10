from __future__ import annotations

import anthropic

from .base import LLMProvider, ProviderResponse, ToolUseBlock


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, enable_caching: bool = True) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._enable_caching = enable_caching

    @property
    def supports_thinking(self) -> bool:
        return True

    @property
    def supports_prompt_caching(self) -> bool:
        return self._enable_caching

    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
        max_tokens: int = 16000,
    ) -> ProviderResponse:
        system_block: list[dict] = [{"type": "text", "text": system}]
        if self._enable_caching:
            system_block[0]["cache_control"] = {"type": "ephemeral"}

        kwargs: dict = dict(
            model=self._model,
            max_tokens=max_tokens,
            system=system_block,
            messages=messages,
            tools=tools,
        )
        if self.supports_thinking:
            kwargs["thinking"] = {"type": "adaptive", "budget_tokens": 8000}

        response = self._client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_uses: list[ToolUseBlock] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(
                    ToolUseBlock(id=block.id, name=block.name, input=block.input)
                )

        return ProviderResponse(
            content_text="\n".join(text_parts),
            tool_uses=tool_uses,
            stop_reason=response.stop_reason or "end_turn",
            raw=response,
        )
