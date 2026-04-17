from __future__ import annotations

import json
from typing import Callable

from openai import OpenAI

from .base import LLMProvider, ProviderResponse, ToolUseBlock


def _to_openai_messages(messages: list[dict]) -> list[dict]:
    """Convert Anthropic-format messages to OpenAI format for Ollama."""
    result = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        # Plain string content — pass through unchanged
        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        # Assistant message — may contain text + tool_use blocks
        if role == "assistant":
            text_parts = [b["text"] for b in content if b.get("type") == "text"]
            tool_uses = [b for b in content if b.get("type") == "tool_use"]
            openai_msg: dict = {"role": "assistant", "content": " ".join(text_parts) or None}
            if tool_uses:
                openai_msg["tool_calls"] = [
                    {
                        "id": tu["id"],
                        "type": "function",
                        "function": {
                            "name": tu["name"],
                            "arguments": json.dumps(tu["input"]),
                        },
                    }
                    for tu in tool_uses
                ]
            result.append(openai_msg)
            continue

        # User message carrying tool results — expand into individual tool messages
        if role == "user" and isinstance(content, list):
            tool_results = [b for b in content if b.get("type") == "tool_result"]
            other = [b for b in content if b.get("type") != "tool_result"]
            for tr in tool_results:
                result.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": tr["content"] if isinstance(tr["content"], str) else json.dumps(tr["content"]),
                })
            if other:
                text = " ".join(b.get("text", "") for b in other if b.get("type") == "text")
                if text:
                    result.append({"role": "user", "content": text})
            continue

        result.append(msg)

    return result


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
        max_tokens: int = 4096,
        on_token: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
    ) -> ProviderResponse:
        full_messages = [{"role": "system", "content": system}] + _to_openai_messages(messages)

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

        tool_uses: list[ToolUseBlock] = []

        if on_token:
            # Streaming path — yield text tokens, assemble tool calls from deltas
            tool_calls_map: dict[int, dict] = {}
            full_text = ""
            with self._client.chat.completions.create(**kwargs, stream=True) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        on_token(delta.content)
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_map:
                                tool_calls_map[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls_map[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_calls_map[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_map[idx]["arguments"] += tc.function.arguments

            for entry in tool_calls_map.values():
                try:
                    args = json.loads(entry["arguments"])
                except json.JSONDecodeError:
                    args = {}
                tool_uses.append(ToolUseBlock(id=entry["id"], name=entry["name"], input=args))

            stop_reason = "tool_use" if tool_uses else "end_turn"
            return ProviderResponse(content_text=full_text, tool_uses=tool_uses, stop_reason=stop_reason)

        # Non-streaming path (unchanged)
        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        text = message.content or ""

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_uses.append(ToolUseBlock(id=tc.id, name=tc.function.name, input=args))

        stop_reason = "tool_use" if tool_uses else "end_turn"
        return ProviderResponse(content_text=text, tool_uses=tool_uses, stop_reason=stop_reason, raw=response)
