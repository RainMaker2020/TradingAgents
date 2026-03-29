"""Append-only JSONL trace per run_id: tool calls, LLM summaries, graph node updates."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


def summarize_state_chunk_for_trace(chunk: dict[str, Any]) -> dict[str, Any]:
    """Thin, safe summary for graph stream chunks (values or updates mode)."""
    out: dict[str, Any] = {"update_keys": list(chunk.keys())}
    msgs = chunk.get("messages")
    if isinstance(msgs, list):
        out["messages_len"] = len(msgs)
        if msgs:
            last = msgs[-1]
            role = getattr(last, "type", None) or getattr(last, "_type", None)
            out["last_message_role"] = role or last.__class__.__name__
    return out


def redact_trace_value(value: Any, max_chars: int = 400) -> Any:
    """Reduce size and sensitivity of tool/LLM payloads for on-disk traces."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[: max_chars - 3] + "..."
    if isinstance(value, dict):
        return {str(k): redact_trace_value(v, max_chars) for k, v in list(value.items())[:40]}
    if isinstance(value, (list, tuple)):
        return [redact_trace_value(v, max_chars) for v in value[:30]]
    return str(value)[:max_chars]


class RunJsonlTraceWriter:
    """Thread-safe append-only JSONL at ``{results_dir}/traces/{run_id}.jsonl``."""

    def __init__(
        self,
        run_id: str,
        results_dir: str | Path,
        *,
        enabled: bool = True,
    ) -> None:
        self.run_id = run_id
        self._enabled = enabled
        self._seq = 0
        self._lock = threading.Lock()
        self._path: Path | None = None
        self._fh = None
        if not enabled:
            return
        base = Path(results_dir).expanduser().resolve()
        self._path = base / "traces" / f"{run_id}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._path, "a", encoding="utf-8", buffering=1)

    @property
    def path(self) -> Path | None:
        return self._path

    def append(self, event: str, payload: Optional[dict[str, Any]] = None) -> None:
        if not self._enabled or self._fh is None:
            return
        with self._lock:
            self._seq += 1
            line = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "run_id": self.run_id,
                "seq": self._seq,
                "event": event,
                "payload": payload or {},
            }
            self._fh.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                logger.exception("closing JSONL trace file")
            self._fh = None


def _one_line_preview(text: str, max_chars: int = 160) -> str:
    s = " ".join(text.split())
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3] + "..."


def extract_token_usage_from_llm_result(response: LLMResult) -> tuple[int, int]:
    """Best-effort tokens_in/tokens_out across providers (usage_metadata, response_metadata, llm_output)."""
    tokens_in = 0
    tokens_out = 0
    try:
        gen = response.generations[0][0]
    except (IndexError, TypeError):
        gen = None

    if gen is not None:
        msg = getattr(gen, "message", None)
        if isinstance(msg, AIMessage):
            um = getattr(msg, "usage_metadata", None)
            if isinstance(um, dict) and um:
                tokens_in = int(um.get("input_tokens", um.get("prompt_tokens", 0)) or 0)
                tokens_out = int(um.get("output_tokens", um.get("completion_tokens", 0)) or 0)
                if tokens_in or tokens_out:
                    return tokens_in, tokens_out
            rm = getattr(msg, "response_metadata", None)
            if isinstance(rm, dict):
                tu = rm.get("token_usage") or rm.get("usage")
                if isinstance(tu, dict):
                    tokens_in = int(
                        tu.get("input_tokens", tu.get("prompt_tokens", 0)) or 0
                    )
                    tokens_out = int(
                        tu.get("output_tokens", tu.get("completion_tokens", 0)) or 0
                    )
                    if tokens_in or tokens_out:
                        return tokens_in, tokens_out
        ginfo = getattr(gen, "generation_info", None)
        if isinstance(ginfo, dict):
            tu = ginfo.get("token_usage") or ginfo.get("usage")
            if isinstance(tu, dict):
                tokens_in = int(tu.get("prompt_tokens", tu.get("input_tokens", 0)) or 0)
                tokens_out = int(tu.get("completion_tokens", tu.get("output_tokens", 0)) or 0)
                if tokens_in or tokens_out:
                    return tokens_in, tokens_out

    lo = getattr(response, "llm_output", None)
    if isinstance(lo, dict):
        tu = lo.get("token_usage") or lo.get("usage")
        if isinstance(tu, dict):
            tokens_in = int(tu.get("prompt_tokens", tu.get("input_tokens", 0)) or 0)
            tokens_out = int(tu.get("completion_tokens", tu.get("output_tokens", 0)) or 0)

    return tokens_in, tokens_out


class RunTraceCallbackHandler(BaseCallbackHandler):
    """LangChain callbacks: LLM tool usage, tool start/end, and token summaries."""

    def __init__(
        self,
        writer: RunJsonlTraceWriter,
        *,
        max_arg_chars: int = 400,
    ) -> None:
        super().__init__()
        self._writer = writer
        self._max_arg_chars = max_arg_chars

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Non-chat completion LLMs (legacy); chat models use on_chat_model_start."""
        name = serialized.get("name") or serialized.get("id")
        preview = ""
        if prompts:
            preview = _one_line_preview(prompts[0], self._max_arg_chars)
        self._writer.append(
            "llm_start",
            {
                "class": name,
                "langchain_run_id": str(run_id),
                "interface": "completion",
                "prompt_preview": preview,
            },
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        name = serialized.get("name") or serialized.get("id")
        self._writer.append(
            "llm_start",
            {
                "class": name,
                "langchain_run_id": str(run_id),
                "interface": "chat",
                "message_batches": len(messages),
            },
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        tokens_in, tokens_out = extract_token_usage_from_llm_result(response)
        llm_summary = ""
        try:
            gen = response.generations[0][0]
            if hasattr(gen, "message"):
                m = gen.message
                if isinstance(m, AIMessage):
                    raw = (m.content or "") if isinstance(m.content, str) else str(m.content)
                    llm_summary = _one_line_preview(raw, 200)
        except (IndexError, TypeError, AttributeError):
            pass
        payload: dict[str, Any] = {
            "langchain_run_id": str(run_id),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
        if llm_summary:
            payload["llm_summary"] = llm_summary
        self._writer.append("llm_end", payload)

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        tool_name = serialized.get("name") or serialized.get("id") or "tool"
        payload: dict[str, Any] = {
            "tool": tool_name,
            "langchain_run_id": str(run_id),
        }
        if inputs:
            payload["inputs"] = redact_trace_value(inputs, self._max_arg_chars)
        if input_str:
            payload["input_str"] = redact_trace_value(input_str, self._max_arg_chars)
        self._writer.append("tool_start", payload)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        out = redact_trace_value(output, self._max_arg_chars)
        preview_cap = min(160, self._max_arg_chars)
        preview = _one_line_preview(str(out), preview_cap)
        self._writer.append(
            "tool_end",
            {
                "langchain_run_id": str(run_id),
                "output": out,
                "output_preview": preview,
            },
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        self._writer.append(
            "tool_error",
            {"langchain_run_id": str(run_id), "error": str(error)[:800]},
        )
