"""
Dedicated debug logger for the chat pipeline.

Writes structured, human-readable entries to logs/chat_debug.log
with full timestamps. Each chat request gets a unique trace_id so
all stages (request → model call → response) can be correlated.

Usage:
    from src.core.chat_debug import debug_log
    debug_log.request(...)
    debug_log.model_call(...)
    debug_log.response(...)
    debug_log.error(...)
"""

import logging
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FILE = _LOG_DIR / "chat_debug.log"

# ── File handler — rotates at 10 MB, keeps 5 backups ─────────────────────────
_file_handler = RotatingFileHandler(
    _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_logger = logging.getLogger("chat_debug")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_file_handler)
_logger.propagate = False  # don't bubble up to root logger


def _now() -> str:
    """ISO-8601 timestamp with timezone, e.g. 2026-04-21 14:32:05.123 UTC+05:30"""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + \
           " " + datetime.now(timezone.utc).astimezone().strftime("%Z")


def _divider(char: str = "─", width: int = 72) -> str:
    return char * width


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12].upper()


class _ChatDebugLogger:

    def request(
        self,
        trace_id: str,
        app_id: str,
        session_id: str,
        message: str,
        stream: bool,
        provider_override: str | None,
    ) -> None:
        lines = [
            _divider("═"),
            f"[{_now()}]  CHAT REQUEST  trace={trace_id}",
            _divider(),
            f"  app_id           : {app_id}",
            f"  session_id       : {session_id}",
            f"  stream           : {stream}",
            f"  provider_override: {provider_override!r}",
            f"  message          : {message!r}",
            _divider("─"),
        ]
        _logger.debug("\n".join(lines))

    def assembled_context(
        self,
        trace_id: str,
        system_prompt: str,
        messages: list[dict],
        token_breakdown: dict,
        rag_chunks: list[Any],
    ) -> None:
        chunk_summary = (
            f"{len(rag_chunks)} chunk(s): "
            + ", ".join(f"{c.source_file}(rel={max(0.0,1-c.distance/2):.2f})" for c in rag_chunks)
            if rag_chunks else "no RAG chunks retrieved"
        )
        history_msgs = [m for m in messages if m["role"] != "user" or m is not messages[-1]]
        lines = [
            f"[{_now()}]  ASSEMBLED CONTEXT  trace={trace_id}",
            _divider(),
            f"  token_breakdown  : {token_breakdown}",
            f"  rag              : {chunk_summary}",
            f"  history_turns    : {len(history_msgs)}",
            "  system_prompt    :",
        ]
        for ln in system_prompt.splitlines():
            lines.append(f"    {ln}")
        lines.append("  messages         :")
        for m in messages:
            role = m["role"].upper()
            content_preview = m["content"][:200].replace("\n", " ")
            suffix = "…" if len(m["content"]) > 200 else ""
            lines.append(f"    [{role}] {content_preview}{suffix}")
        lines.append(_divider("─"))
        _logger.debug("\n".join(lines))

    def model_call(
        self,
        trace_id: str,
        provider: str,
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
        message_count: int,
        system_prompt_len: int,
    ) -> None:
        lines = [
            f"[{_now()}]  MODEL CALL  trace={trace_id}",
            _divider(),
            f"  provider         : {provider}",
            f"  model            : {model}",
            f"  max_tokens       : {max_tokens}",
            f"  temperature      : {temperature}",
            f"  stream           : {stream}",
            f"  messages_count   : {message_count}",
            f"  system_prompt_len: {system_prompt_len} chars",
            _divider("─"),
        ]
        _logger.debug("\n".join(lines))

    def response(
        self,
        trace_id: str,
        provider: str,
        model: str,
        reply: str,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str,
        latency_ms: float,
    ) -> None:
        lines = [
            f"[{_now()}]  MODEL RESPONSE  trace={trace_id}",
            _divider(),
            f"  provider         : {provider}",
            f"  model            : {model}",
            f"  finish_reason    : {finish_reason}",
            f"  input_tokens     : {input_tokens}",
            f"  output_tokens    : {output_tokens}",
            f"  latency_ms       : {latency_ms:.1f}",
            "  reply            :",
        ]
        for ln in reply.splitlines():
            lines.append(f"    {ln}")
        lines.append(_divider("═"))
        _logger.debug("\n".join(lines))

    def error(
        self,
        trace_id: str,
        stage: str,
        exc: Exception,
    ) -> None:
        import traceback
        lines = [
            f"[{_now()}]  ERROR  trace={trace_id}  stage={stage}",
            _divider(),
            f"  {type(exc).__name__}: {exc}",
            "  traceback:",
        ]
        for ln in traceback.format_exc().splitlines():
            lines.append(f"    {ln}")
        lines.append(_divider("═"))
        _logger.debug("\n".join(lines))


debug_log = _ChatDebugLogger()
