from __future__ import annotations

from typing import Callable

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
        max_tokens: int = 4096,
        on_token: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
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
            kwargs["betas"] = ["interleaved-thinking-2025-05-14"]

        text_parts: list[str] = []
        tool_uses: list[ToolUseBlock] = []

        # Use beta client when interleaved-thinking beta is active
        _msg_client = self._client.beta.messages if "betas" in kwargs else self._client.messages
        _betas = kwargs.pop("betas", None)

        if on_thinking:
            # Raw event iteration — surfaces both thinking and text deltas separately
            stream_kwargs = {**kwargs, **({"betas": _betas} if _betas else {})}
            with _msg_client.stream(**stream_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "thinking_delta":
                            on_thinking(delta.thinking)
                        elif delta.type == "text_delta" and on_token:
                            on_token(delta.text)
            response = stream.get_final_message()
        elif on_token:
            stream_kwargs = {**kwargs, **({"betas": _betas} if _betas else {})}
            with _msg_client.stream(**stream_kwargs) as stream:
                for text in stream.text_stream:
                    on_token(text)
            response = stream.get_final_message()
        else:
            create_kwargs = {**kwargs, **({"betas": _betas} if _betas else {})}
            response = _msg_client.create(**create_kwargs)

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
