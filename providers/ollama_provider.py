from __future__ import annotations

import json

from openai import OpenAI

from .base import LLMProvider, ProviderResponse, ToolUseBlock


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        # Ollama exposes an OpenAI-compatible API at /v1
        self._client = OpenAI(
            base_url=f"{base_url.rstrip('/')}/v1",
            api_key="ollama",  # Ollama doesn't require a real key
        )
        self._model = model

    @property
    def supports_thinking(self) -> bool:
        return False

    @property
    def supports_prompt_caching(self) -> bool:
        return False

    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
        max_tokens: int = 16000,
    ) -> ProviderResponse:
        full_messages = [{"role": "system", "content": system}] + messages

        # Convert Anthropic-style tool definitions to OpenAI format
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in tools
        ]

        kwargs: dict = dict(
            model=self._model,
            messages=full_messages,
            max_tokens=max_tokens,
        )
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text = message.content or ""
        tool_uses: list[ToolUseBlock] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_uses.append(
                    ToolUseBlock(id=tc.id, name=tc.function.name, input=args)
                )

        stop_reason = "tool_use" if tool_uses else "end_turn"

        return ProviderResponse(
            content_text=text,
            tool_uses=tool_uses,
            stop_reason=stop_reason,
            raw=response,
        )
