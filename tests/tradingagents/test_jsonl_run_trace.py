"""Tests for append-only JSONL run traces."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from tradingagents.tracing.jsonl_run_trace import (
    RunJsonlTraceWriter,
    RunTraceCallbackHandler,
    extract_token_usage_from_llm_result,
    redact_trace_value,
    summarize_state_chunk_for_trace,
)

pytest.importorskip("langchain_core")

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult


def test_redact_trace_value_truncates_long_string():
    s = "x" * 500
    out = redact_trace_value(s, max_chars=20)
    assert len(out) == 20
    assert out.endswith("...")


def test_run_jsonl_trace_writer_append(tmp_path: Path):
    w = RunJsonlTraceWriter("run123", tmp_path, enabled=True)
    try:
        w.append("test_event", {"a": 1})
        w.append("test_event", {"b": 2})
        assert w.path is not None
        lines = w.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        o1 = json.loads(lines[0])
        o2 = json.loads(lines[1])
        assert o1["run_id"] == "run123" and o1["event"] == "test_event"
        assert o1["seq"] == 1 and o2["seq"] == 2
        assert o1["payload"] == {"a": 1}
    finally:
        w.close()


def test_run_jsonl_trace_writer_disabled_no_file(tmp_path: Path):
    w = RunJsonlTraceWriter("x", tmp_path, enabled=False)
    w.append("x", {})
    w.close()
    trace_dir = tmp_path / "traces"
    assert not trace_dir.exists() or not (trace_dir / "x.jsonl").exists()


def test_summarize_state_chunk_for_trace_roles_and_keys():
    m = AIMessage(content="x", id="1")
    chunk = {"messages": [m], "foo": 1}
    s = summarize_state_chunk_for_trace(chunk)
    assert s["update_keys"] == ["messages", "foo"]
    assert s["messages_len"] == 1
    assert "last_message_role" in s


def test_extract_token_usage_from_llm_result_usage_metadata():
    msg = AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": 3,
            "output_tokens": 7,
            "total_tokens": 10,
        },
    )
    gen = ChatGeneration(message=msg)
    res = LLMResult(generations=[[gen]])
    assert extract_token_usage_from_llm_result(res) == (3, 7)


def test_run_trace_callback_handler_writes_llm_and_tool_events(tmp_path: Path):
    """Callback handler + writer integration (no live LLM)."""
    w = RunJsonlTraceWriter("trace-run", tmp_path, enabled=True)
    try:
        h = RunTraceCallbackHandler(w, max_arg_chars=80)
        rid = uuid4()
        h.on_llm_start(
            {"name": "FakeLLM"},
            ["hello world " * 20],
            run_id=rid,
        )
        msg = AIMessage(
            content="summary text here",
            usage_metadata={
                "input_tokens": 1,
                "output_tokens": 2,
                "total_tokens": 3,
            },
        )
        gen = ChatGeneration(message=msg)
        h.on_llm_end(LLMResult(generations=[[gen]]), run_id=rid)
        tid = uuid4()
        h.on_tool_end({"big": "x" * 100}, run_id=tid)
        assert w.path is not None
        lines = [json.loads(x) for x in w.path.read_text(encoding="utf-8").splitlines()]
        events = [x["event"] for x in lines]
        assert "llm_start" in events and "llm_end" in events and "tool_end" in events
        llm_end = next(x for x in lines if x["event"] == "llm_end")
        assert llm_end["payload"].get("tokens_in") == 1
        assert "llm_summary" in llm_end["payload"]
        tool_end = next(x for x in lines if x["event"] == "tool_end")
        assert "output_preview" in tool_end["payload"]
    finally:
        w.close()


def test_tool_end_preview_derives_from_redacted_output(tmp_path: Path):
    """output_preview must not reflect unredacted tool output (privacy)."""
    w = RunJsonlTraceWriter("r", tmp_path, enabled=True)
    try:
        h = RunTraceCallbackHandler(w, max_arg_chars=40)
        rid = uuid4()
        raw = "SECRET" * 50
        h.on_tool_end({"key": raw}, run_id=rid)
        assert w.path is not None
        line = json.loads(w.path.read_text(encoding="utf-8").strip().splitlines()[-1])
        prev = line["payload"]["output_preview"]
        assert raw not in prev
        assert len(prev) <= 200
        out = line["payload"]["output"]
        assert isinstance(out, dict)
        assert isinstance(out["key"], str)
        assert len(out["key"]) <= 40
    finally:
        w.close()
