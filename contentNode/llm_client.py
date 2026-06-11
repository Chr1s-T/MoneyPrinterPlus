"""DeepSeek API client with thinking mode support."""

import json
import os
from openai import OpenAI


def create_client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError(
            "DeepSeek API key required. Set DEEPSEEK_API_KEY env var or pass --api-key"
        )
    return OpenAI(api_key=key, base_url="https://api.deepseek.com")


def chat(
    client: OpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str = "deepseek-v4-flash",
    max_tokens: int = 16384,
) -> str:
    """Call DeepSeek with thinking mode enabled. Returns final content."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
        stream=False,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek returned empty content")
    return content.strip()
