"""Thin wrapper around Hindsight: the agent's only long-term memory.

retain  -> store every deployment outcome, root cause and lesson
recall  -> find similar past deployments before predicting risk
reflect -> answer "why are you warning me?" by reasoning over memory
"""
from __future__ import annotations

import contextlib
import os
from datetime import datetime

from hindsight_client import Hindsight

MISSION = (
    "I am Butterflaw, the deployment memory of one e-commerce engineering team. "
    "I remember every deployment, which services and changes it touched, when it shipped, "
    "whether it caused an incident, the root cause, and lessons from my own wrong predictions. "
    "I use this to predict which new deployments will break production."
)


def configured() -> bool:
    return bool(os.getenv("HINDSIGHT_API_KEY"))


@contextlib.contextmanager
def _client():
    # A fresh client per call: the SDK's sync wrappers run their own event loop,
    # so sharing one client across FastAPI worker threads is not safe.
    client = Hindsight(
        base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
        api_key=os.getenv("HINDSIGHT_API_KEY"),
        timeout=180.0,
    )
    try:
        yield client
    finally:
        with contextlib.suppress(Exception):
            client.close()


def version() -> str:
    with _client() as c:
        return str(c.get_version().api_version)


def create_bank(bank_id: str) -> None:
    with _client() as c:
        c.create_bank(bank_id=bank_id, name="Butterflaw", mission=MISSION)


def retain(bank_id: str, content: str, when: datetime, context: str, metadata: dict[str, str]) -> None:
    with _client() as c:
        c.retain(bank_id=bank_id, content=content, timestamp=when, context=context,
                 metadata=metadata, retain_async=False)


def recall(bank_id: str, query: str, limit: int = 8) -> list[dict]:
    with _client() as c:
        response = c.recall(bank_id=bank_id, query=query, budget="mid", max_tokens=2000)
    out = []
    for r in (response.results or [])[:limit]:
        when = r.occurred_start or r.mentioned_at
        out.append({"text": r.text, "type": r.type or "", "when": str(when)[:10] if when else ""})
    return out


def reflect(bank_id: str, question: str) -> dict:
    with _client() as c:
        response = c.reflect(bank_id=bank_id, query=question, budget="mid",
                             context="deployment risk review")
    used = 0
    if response.based_on and response.based_on.memories:
        used = len(response.based_on.memories)
    return {"text": response.text, "memories_used": used}


def list_memories(bank_id: str, limit: int = 100, type: str | None = None) -> dict:
    with _client() as c:
        response = c.list_memories(bank_id=bank_id, limit=limit, type=type or None)
    items = [{"text": m.text, "type": m.fact_type or "", "context": m.context or "",
              "when": str(m.occurred_start or m.mentioned_at or "")[:10]} for m in (response.items or [])]
    return {"total": response.total, "items": items}
