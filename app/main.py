"""Butterflaw web app: FastAPI + a single-page UI."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from . import agent, llm, memory  # noqa: E402
from .data import DEPENDENCIES, HISTORY, REPLAY, SERVICES  # noqa: E402

app = FastAPI(title="Butterflaw")
STATIC = Path(__file__).resolve().parent / "static"


class PreflightIn(BaseModel):
    services: list[str] = Field(min_length=1)
    summary: str = Field(min_length=3, max_length=1000)
    when: str
    version: str = Field(default="", max_length=60)
    diff: str = Field(default="", max_length=4000)


class OutcomeIn(BaseModel):
    preflight_id: str
    failed: bool
    root_cause: str = ""


class GuardrailIn(BaseModel):
    rule: str = Field(min_length=5, max_length=400)
    source: str = Field(default="", max_length=20)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    preflight_id: str | None = None


def _require_keys() -> None:
    missing = [n for n, ok in (("HINDSIGHT_API_KEY", memory.configured()), ("GROQ_API_KEY", llm.configured())) if not ok]
    if missing:
        raise HTTPException(503, f"Missing secrets: {', '.join(missing)}")


def _fail(exc: Exception) -> HTTPException:
    return HTTPException(502, f"{type(exc).__name__}: {str(exc)[:400]}")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    result = {"hindsight_key": memory.configured(), "groq_key": llm.configured(), "model": llm.MODEL}
    if memory.configured():
        try:
            result["hindsight_api"] = memory.version()
        except Exception as exc:
            result["hindsight_error"] = str(exc)[:300]
    return result


@app.get("/api/meta")
def meta():
    return {"services": SERVICES, "history": HISTORY, "replay_count": len(REPLAY),
            "dependencies": [{"from": a, "to": b, "kind": k} for a, b, k in DEPENDENCIES]}


@app.get("/api/replay")
def replay_status():
    state = agent.load_state()
    replay = state["replay"]
    return {**replay, "summary": agent.replay_summary(replay.get("results", [])), "bank_id": state.get("bank_id")}


@app.post("/api/replay/start")
def replay_start():
    _require_keys()
    if not agent.start_replay():
        raise HTTPException(409, "Replay already running")
    return {"started": True}


@app.post("/api/preflight")
def preflight(body: PreflightIn):
    _require_keys()
    try:
        return agent.preflight(body.services, body.summary.strip(), body.when, body.version, body.diff)
    except Exception as exc:
        raise _fail(exc)


@app.post("/api/outcome")
def outcome(body: OutcomeIn):
    _require_keys()
    try:
        return agent.record_outcome(body.preflight_id, body.failed, body.root_cause)
    except KeyError:
        raise HTTPException(404, "Unknown preflight id")
    except Exception as exc:
        raise _fail(exc)


@app.post("/api/ask")
def ask(body: AskIn):
    _require_keys()
    try:
        return agent.ask(body.question, body.preflight_id)
    except Exception as exc:
        raise _fail(exc)


@app.get("/api/memory")
def memories(q: str | None = None, type: str | None = None):
    _require_keys()
    bank_id = agent.load_state().get("bank_id")
    if not bank_id:
        return {"bank_id": None, "total": 0, "items": []}
    try:
        if q:
            items = memory.recall(bank_id, q, limit=20)
            return {"bank_id": bank_id, "total": len(items), "items": items, "query": q}
        return {"bank_id": bank_id, **memory.list_memories(bank_id, type=type if type in ("world", "experience", "observation") else None)}
    except Exception as exc:
        raise _fail(exc)


@app.get("/api/incidents")
def incidents():
    return {"items": agent.incidents()}


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str, similar: bool = True):
    item = next((i for i in agent.incidents() if i["id"] == incident_id), None)
    if not item:
        raise HTTPException(404, "Unknown incident")
    deps = [{"from": a, "to": b, "kind": k} for a, b, k in DEPENDENCIES
            if a in item["services"] or b in item["services"]]
    result = {**item, "dependencies": deps, "similar": []}
    bank_id = agent.load_state().get("bank_id")
    if similar and bank_id and memory.configured():
        try:
            result["similar"] = [m for m in memory.recall(bank_id, agent.describe(item), limit=6)][:5]
        except Exception as exc:
            result["similar_error"] = str(exc)[:200]
    return result


@app.get("/api/lessons")
def lessons():
    return {"items": agent.lessons()}


@app.get("/api/guardrails")
def guardrails():
    return {"items": agent.get_guardrails()}


@app.post("/api/guardrails")
def add_guardrail(body: GuardrailIn):
    _require_keys()
    try:
        return agent.add_guardrail(body.rule, body.source)
    except Exception as exc:
        raise _fail(exc)
