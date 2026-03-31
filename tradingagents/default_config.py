import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Per-analyst analyst↔tool cycles (each tools_* visit counts). Independent of debate rounds.
    # 0 = never execute tools_* (route straight to Msg Clear when the model requests tools).
    "max_analyst_tool_rounds": 32,
    "max_analyst_tool_rounds_by_role": {},
    # Append-only JSONL under results_dir/traces/{run_id}.jsonl (API graph runs).
    # Set TRADINGAGENTS_JSONL_TRACE=0 to disable.
    "jsonl_run_trace": os.getenv("TRADINGAGENTS_JSONL_TRACE", "1") != "0",
    "jsonl_trace_max_arg_chars": int(os.getenv("TRADINGAGENTS_JSONL_TRACE_MAX_ARG_CHARS", "400")),
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
