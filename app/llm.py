"""Groq chat completions (OpenAI-compatible), returning parsed JSON with retries."""
from __future__ import annotations

import json
import os
import re
import time

from openai import APIStatusError, OpenAI, RateLimitError

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def _client() -> OpenAI:
    return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1", max_retries=0)


def _parse(text: str) -> dict:
    text = (text or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(match.group(0))


def chat_json(system: str, user: str, max_tokens: int = 1200) -> dict:
    client, json_mode, last = _client(), True, "unknown error"
    for attempt in range(6):
        kwargs = {"model": MODEL, "temperature": 0.1, "max_completion_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = client.chat.completions.create(**kwargs)
            return _parse(response.choices[0].message.content)
        except RateLimitError as e:
            wait = float(e.response.headers.get("retry-after", 0) or 0) or 4 * (attempt + 1)
            last = f"rate limited, waited {wait:.0f}s"
            time.sleep(min(wait, 60))
        except APIStatusError as e:
            last = f"HTTP {e.status_code}: {str(e)[:200]}"
            if e.status_code == 400 and json_mode:
                json_mode = False  # model rejected JSON mode or failed to produce JSON; retry in plain mode
                continue
            if e.status_code in (401, 403, 404):
                raise RuntimeError(f"Groq error: {last}") from None
            time.sleep(2 * (attempt + 1))
        except (ValueError, json.JSONDecodeError) as e:
            last = str(e)
            json_mode = False
    raise RuntimeError(f"Groq call failed after retries: {last}")
