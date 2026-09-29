"""Butterflaw agent: predict deployment risk with and without Hindsight memory, then learn from outcomes."""
from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from . import llm, memory
from .data import DEFAULT_GUARDRAILS, HISTORY, INCIDENT_DETAILS, REPLAY

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "state.json"
_lock = threading.Lock()

SYSTEM = """You are Butterflaw, a deployment risk reviewer for one specific engineering team.
Decide whether the NEW DEPLOYMENT will cause a production incident.
Use the TEAM HISTORY when it is relevant: this team has its own failure patterns
(specific dependency versions, time windows, service combinations) that generic intuition misses,
and it also has safe practices (feature flags, canaries, expand/contract migrations) that make
some scary-looking changes safe. If the history is empty or irrelevant, use general engineering judgment.
Return ONLY a JSON object:
{"will_fail": true|false, "risk": "low"|"medium"|"high", "confidence": 0.0-1.0,
 "reasoning": "max 2 sentences, cite history items by id when you use them",
 "cited": ["INC-127", ...]}"""


# ---------------- state ----------------
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"bank_id": None, "replay": {"status": "idle", "results": [], "total": len(REPLAY)}, "preflights": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(STATE_FILE)


def update_state(fn) -> dict:
    with _lock:
        state = load_state()
        fn(state)
        save_state(state)
        return state


# ---------------- text helpers ----------------
def describe(dep: dict) -> str:
    when = datetime.fromisoformat(dep["when"])
    text = (f"Deploy {dep['version']} on {when:%A %d %b %Y} at {when:%H:%M} IST. "
            f"Services: {', '.join(dep['services'])}. Change: {dep['summary']}.")
    if dep.get("diff"):
        text += f" Diff excerpt: {dep['diff'][:600]}"
    return text


def outcome_memory(dep: dict, prediction: dict | None = None) -> str:
    text = describe(dep)
    if dep["failed"]:
        text += f" Outcome: CAUSED INCIDENT {dep['id']}. Root cause: {dep['root_cause']}"
    else:
        text += f" Outcome: shipped safely ({dep['id']}), no incident."
    if prediction is not None:
        predicted = "INCIDENT" if prediction["will_fail"] else "SAFE"
        if prediction["will_fail"] == dep["failed"]:
            text += f" Butterflaw predicted {predicted}, which was correct."
        else:
            text += (f" Butterflaw predicted {predicted}, which was WRONG. Lesson: "
                     + ("changes like this are dangerous for this team even though they look harmless."
                        if dep["failed"] else
                        "changes like this are safe for this team; do not over-warn on them."))
    return text


def retain_outcome(bank_id: str, dep: dict, prediction: dict | None = None) -> None:
    memory.retain(bank_id, outcome_memory(dep, prediction), datetime.fromisoformat(dep["when"]),
                  context="deployment_outcome",
                  metadata={"deploy_id": dep["id"], "version": dep["version"],
                            "services": ",".join(dep["services"]), "failed": str(dep["failed"]).lower()})


# ---------------- bank lifecycle ----------------
def new_bank() -> str:
    bank_id = f"butterflaw-{int(time.time())}"
    memory.create_bank(bank_id)
    for dep in HISTORY:
        retain_outcome(bank_id, dep)
    update_state(lambda s: s.__setitem__("bank_id", bank_id))
    return bank_id


def ensure_bank() -> str:
    return load_state().get("bank_id") or new_bank()


# ---------------- prediction ----------------
def _judge(dep: dict, history: list[dict], guardrails: list[dict] | None = None) -> dict:
    if history:
        lines = "\n".join(f"- [{m['when']}] {m['text']}" for m in history)
    else:
        lines = "(no team history available)"
    user = f"TEAM HISTORY:\n{lines}\n\n"
    if guardrails:
        user += "TEAM GUARDRAILS (learned rules; a deployment that violates one is very likely to fail):\n"
        user += "\n".join(f"- {g['id']}: {g['rule']}" for g in guardrails) + "\n\n"
    user += f"NEW DEPLOYMENT:\n{describe(dep)}"
    out = llm.chat_json(SYSTEM, user)
    return {
        "will_fail": bool(out.get("will_fail")),
        "risk": str(out.get("risk", "medium")).lower(),
        "confidence": max(0.0, min(1.0, float(out.get("confidence", 0.5) or 0.5))),
        "reasoning": str(out.get("reasoning", ""))[:600],
        "cited": [str(c) for c in (out.get("cited") or [])][:6],
    }


def predict(bank_id: str, dep: dict) -> dict:
    recalled = memory.recall(bank_id, describe(dep))
    with_memory = _judge(dep, recalled, get_guardrails())
    without_memory = _judge(dep, [])
    return {"with_memory": with_memory, "without_memory": without_memory, "recalled": recalled}


# ---------------- replay (the learning curve) ----------------
_replay_thread: threading.Thread | None = None


def _run_replay() -> None:
    try:
        bank_id = new_bank()
        update_state(lambda s: s["replay"].update(bank_id=bank_id))
        for i, dep in enumerate(REPLAY):
            result = predict(bank_id, dep)
            retain_outcome(bank_id, dep, result["with_memory"])  # learn from the real outcome
            row = {
                "n": i + 1, "id": dep["id"], "when": dep["when"], "services": dep["services"],
                "summary": dep["summary"], "failed": dep["failed"], "root_cause": dep["root_cause"],
                "with_memory": result["with_memory"], "without_memory": result["without_memory"],
                "recalled": result["recalled"][:4],
                "memory_correct": result["with_memory"]["will_fail"] == dep["failed"],
                "baseline_correct": result["without_memory"]["will_fail"] == dep["failed"],
            }
            update_state(lambda s: (s["replay"]["results"].append(row), s["replay"].update(progress=i + 1)))
        update_state(lambda s: s["replay"].update(status="done", finished_at=datetime.now().isoformat()))
    except Exception as exc:  # surface the failure in the UI instead of dying silently
        traceback.print_exc()
        update_state(lambda s: s["replay"].update(status="error", error=str(exc)[:500]))


def start_replay() -> bool:
    global _replay_thread
    if _replay_thread and _replay_thread.is_alive():
        return False
    update_state(lambda s: s.__setitem__("replay", {
        "status": "running", "results": [], "progress": 0, "total": len(REPLAY),
        "started_at": datetime.now().isoformat()}))
    _replay_thread = threading.Thread(target=_run_replay, daemon=True, name="replay")
    _replay_thread.start()
    return True


def replay_summary(results: list[dict]) -> dict:
    def acc(rows, key):
        return round(100 * sum(r[key] for r in rows) / len(rows)) if rows else None
    half = len(results) // 2
    return {
        "memory_accuracy": acc(results, "memory_correct"),
        "baseline_accuracy": acc(results, "baseline_correct"),
        "memory_first_half": acc(results[:half], "memory_correct"),
        "memory_second_half": acc(results[half:], "memory_correct"),
        "baseline_first_half": acc(results[:half], "baseline_correct"),
        "baseline_second_half": acc(results[half:], "baseline_correct"),
    }


# ---------------- interactive preflight ----------------
def blast_radius(cited: list[str]) -> dict | None:
    matches = [dict(INCIDENT_DETAILS[c], id=c) for c in cited if c in INCIDENT_DETAILS]
    if not matches:
        return None
    worst = max(matches, key=lambda m: m["amount_inr"] + m["failed_requests"])
    return {"based_on": worst["id"], "title": worst["title"], "failed_requests": worst["failed_requests"],
            "amount_inr": worst["amount_inr"], "downtime_min": worst["downtime_min"]}


def preflight(services: list[str], summary: str, when: str, version: str = "", diff: str = "") -> dict:
    bank_id = ensure_bank()
    dep = {"id": f"PRE-{uuid.uuid4().hex[:6].upper()}", "version": version.strip() or "next",
           "when": when, "services": services, "summary": summary, "diff": diff.strip(),
           "failed": False, "root_cause": ""}
    result = predict(bank_id, dep)
    record = {"deployment": dep, **result, "outcome": None,
              "blast_radius": blast_radius(result["with_memory"]["cited"]) if result["with_memory"]["will_fail"] else None}
    update_state(lambda s: s["preflights"].__setitem__(dep["id"], record))
    return record


def record_outcome(preflight_id: str, failed: bool, root_cause: str) -> dict:
    state = load_state()
    record = state["preflights"].get(preflight_id)
    if not record:
        raise KeyError(preflight_id)
    dep = {**record["deployment"], "failed": failed, "root_cause": root_cause.strip() or "not recorded"}
    retain_outcome(state["bank_id"], dep, record["with_memory"])
    update_state(lambda s: s["preflights"][preflight_id].update(outcome={"failed": failed, "root_cause": dep["root_cause"]}))
    return {"retained": outcome_memory(dep, record["with_memory"])}


def ask(question: str, preflight_id: str | None) -> dict:
    bank_id = ensure_bank()
    if preflight_id:
        record = load_state()["preflights"].get(preflight_id)
        if record:
            question = f"About this deployment: {describe(record['deployment'])}\nQuestion: {question}"
    return memory.reflect(bank_id, question)


# ---------------- guardrails ----------------
def get_guardrails() -> list[dict]:
    return load_state().get("guardrails") or list(DEFAULT_GUARDRAILS)


def add_guardrail(rule: str, source: str) -> dict:
    state = load_state()
    rails = state.get("guardrails") or list(DEFAULT_GUARDRAILS)
    g = {"id": f"GR-{len(rails) + 1}", "rule": rule.strip()[:400], "source": source.strip()[:20],
         "added": datetime.now().strftime("%Y-%m-%d")}
    if state.get("bank_id"):
        memory.retain(state["bank_id"], f"Team guardrail {g['id']} adopted: {g['rule']}"
                      + (f" (learned from {g['source']})" if g["source"] else ""),
                      datetime.now(), context="guardrail", metadata={"guardrail_id": g["id"], "source": g["source"]})
    update_state(lambda s: s.__setitem__("guardrails", rails + [g]))
    return g


# ---------------- incidents + lessons (UI views) ----------------
def incidents() -> list[dict]:
    state = load_state()
    seen = {r["id"] for r in state["replay"].get("results", [])}
    rows = [dict(d, source="history") for d in HISTORY if d["failed"]]
    rows += [dict(d, source="replay") for d in REPLAY if d["failed"] and d["id"] in seen]
    for p in state.get("preflights", {}).values():
        if p.get("outcome") and p["outcome"]["failed"]:
            rows.append(dict(p["deployment"], failed=True, root_cause=p["outcome"]["root_cause"], source="preflight"))
    out = []
    for d in rows:
        info = INCIDENT_DETAILS.get(d["id"], {})
        out.append({**d, "title": info.get("title", d["summary"]), "severity": info.get("severity", "medium"),
                    "failed_requests": info.get("failed_requests"), "amount_inr": info.get("amount_inr"),
                    "downtime_min": info.get("downtime_min"), "fix_type": info.get("fix_type", "patch"),
                    "trail": info.get("trail") or [d["summary"], d.get("root_cause", "")],
                    "resolution": info.get("resolution", "")})
    return sorted(out, key=lambda x: x["when"], reverse=True)


def lessons() -> list[dict]:
    state = load_state()
    out = []
    for r in state["replay"].get("results", []):
        if not r["memory_correct"]:
            predicted = "INCIDENT" if r["with_memory"]["will_fail"] else "SAFE"
            out.append({"id": r["id"], "when": r["when"], "summary": r["summary"],
                        "lesson": f"Predicted {predicted}, actual {'INCIDENT' if r['failed'] else 'SAFE'}. "
                                  + ("Changes like this are dangerous for this team even though they look harmless."
                                     if r["failed"] else "Changes like this are safe here; do not over-warn.")})
    for p in state.get("preflights", {}).values():
        if p.get("outcome"):
            ok = p["with_memory"]["will_fail"] == p["outcome"]["failed"]
            out.append({"id": p["deployment"]["id"], "when": p["deployment"]["when"], "summary": p["deployment"]["summary"],
                        "lesson": ("Prediction confirmed." if ok else "Prediction was wrong; lesson retained.")
                                  + (f" Root cause: {p['outcome']['root_cause']}" if p["outcome"]["failed"] else "")})
    return sorted(out, key=lambda x: x["when"], reverse=True)
