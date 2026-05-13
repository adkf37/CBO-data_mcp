"""Flask web application for the CBO Data Assistant."""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

from flask import Flask, jsonify, render_template, request

from src.llm_agent import CBOAgent
from src.tool_registry import list_tool_names

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")


# Always return JSON for errors so res.json() never throws in the browser
@app.errorhandler(Exception)
def handle_exception(exc: Exception):
    logger.exception("Unhandled exception")
    return jsonify({"error": "An unexpected server error occurred.", "detail": str(exc)}), 500


@app.errorhandler(404)
def handle_404(exc):
    return jsonify({"error": "Not found"}), 404

MAX_QUESTION_LENGTH = 4000  # characters; reject oversized payloads early

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
# Each session holds a dedicated CBOAgent (which carries its own Gemini chat
# history) so multi-turn follow-ups ("what about the next decade?") work
# correctly per user.  Sessions are in-process and best-effort — they reset
# if the Cloud Run worker restarts, which is acceptable for this use case.

_sessions: dict[str, dict[str, Any]] = {}
_sessions_lock = threading.Lock()
_SESSION_TTL_SECONDS = 60 * 60  # 1 hour idle TTL
_SESSION_MAX = 100               # max concurrent sessions (LRU eviction)


def _prune_sessions_locked() -> None:
    """Expire stale sessions and enforce the max-sessions cap."""
    cutoff = time.monotonic() - _SESSION_TTL_SECONDS
    expired = [sid for sid, s in _sessions.items() if s["updated"] < cutoff]
    for sid in expired:
        _sessions.pop(sid, None)
    while len(_sessions) > _SESSION_MAX:
        _sessions.pop(next(iter(_sessions)), None)


def _get_or_create_session(session_id: str | None) -> tuple[str, dict[str, Any]]:
    """Return ``(session_id, session)``, creating a new one if needed."""
    with _sessions_lock:
        _prune_sessions_locked()
        if session_id and session_id in _sessions:
            session = _sessions[session_id]
            session["updated"] = time.monotonic()
            return session_id, session
        new_id = session_id or uuid.uuid4().hex
        session = {
            "agent": None,   # CBOAgent initialised lazily on first use
            "updated": time.monotonic(),
        }
        _sessions[new_id] = session
        return new_id, session


def _get_agent(session: dict[str, Any]) -> CBOAgent:
    """Return the session's CBOAgent, creating it lazily on first access."""
    if session["agent"] is None:
        session["agent"] = CBOAgent()  # reads GEMINI_API_KEY from env
    return session["agent"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/chat")
def chat() -> tuple[Any, int]:
    data: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    question: str = (data.get("question") or "").strip()
    session_id_in: str | None = data.get("session_id") or None

    if not question:
        return jsonify({"error": "question is required"}), 400
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify({"error": "question exceeds maximum length"}), 400

    session_id, session = _get_or_create_session(session_id_in)

    try:
        agent = _get_agent(session)
        answer = agent.ask(question)
        tool_calls = [
            {"name": tc["tool"], "args": tc.get("args", {})}
            for tc in agent.last_trace
        ]
        charts = [
            tc["result"]["chart_data"]
            for tc in agent.last_trace
            if tc["tool"] == "chart_projection"
            and isinstance(tc.get("result"), dict)
            and "chart_data" in tc["result"]
        ]
        return (
            jsonify(
                {
                    "answer": answer,
                    "session_id": session_id,
                    "tool_calls": tool_calls,
                    "charts": charts,
                }
            ),
            200,
        )
    except RuntimeError as exc:
        logger.error("Configuration error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error handling chat request")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.post("/api/session/reset")
def reset_session() -> tuple[Any, int]:
    """Clear a session's conversation history."""
    data: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    session_id: str | None = data.get("session_id") or None
    if session_id:
        with _sessions_lock:
            session = _sessions.get(session_id)
            if session and session.get("agent"):
                session["agent"].reset()
    return jsonify({"ok": True}), 200


@app.get("/api/health")
def health() -> tuple[Any, int]:
    api_key_set = bool(os.environ.get("GEMINI_API_KEY"))
    return (
        jsonify(
            {
                "status": "ok",
                "api_key_configured": api_key_set,
                "tools_count": len(list_tool_names()),
            }
        ),
        200,
    )


@app.get("/api/tools")
def tools() -> tuple[Any, int]:
    return jsonify({"tools": list_tool_names()}), 200


# ---------------------------------------------------------------------------
# Entry point (dev only — production uses gunicorn)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
