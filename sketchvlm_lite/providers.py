"""Vision-language model client wrappers."""

from __future__ import annotations

import base64
import os
from typing import List, Optional


def call_anthropic(
    model: str,
    system: str,
    image_b64: str,
    user_text: str,
    max_tokens: int = 4000,
    stop_sequences: Optional[List[str]] = None,
    media_type: str = "image/png",
    api_key: Optional[str] = None,
) -> str:
    """Send a single-turn vision query to an Anthropic model and return raw text.

    The response is accumulated as the concatenation of all `text` blocks, plus
    any stop sequence that triggered termination (so the parser can still see
    the closing `</answer>` tag).
    """
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it in your shell or pass api_key=..."
        )

    client = anthropic.Anthropic(api_key=key)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    }
    if stop_sequences:
        kwargs["stop_sequences"] = list(stop_sequences)

    resp = client.messages.create(**kwargs)

    parts = []
    for block in resp.content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    out = "".join(parts)

    stop = getattr(resp, "stop_sequence", None)
    if stop:
        out = out + stop
    return out


def encode_image_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")
