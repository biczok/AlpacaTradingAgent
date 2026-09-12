"""Helpers for showing generated-at timestamps and browsing persisted reports."""

from datetime import datetime
import time
from typing import Any, Dict, List, Optional


_LIST_CACHE: Dict[str, Any] = {}
_VIEW_CACHE: Dict[tuple, Dict[str, Any]] = {}
_LIST_TTL_SECONDS = 15.0
_VIEW_CACHE_LIMIT = 20


def get_eval_results_dir() -> str:
    try:
        from tradingagents.dataflows.config import get_config

        return (get_config() or {}).get("results_dir", "eval_results")
    except Exception:
        return "eval_results"


def format_report_timestamp(value: Any) -> Optional[str]:
    """Format unix seconds or ISO datetimes for display in local time."""
    if value in (None, "", 0):
        return None

    parsed = None
    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        parsed = datetime.fromtimestamp(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone()
        except ValueError:
            return text
    else:
        return None

    return parsed.strftime("%b %d, %Y %I:%M:%S %p")


def create_generated_at_badge(value: Any):
    from dash import html

    formatted = format_report_timestamp(value)
    if not formatted:
        return None
    return html.Div(
        [
            html.I(className="fas fa-clock me-2"),
            html.Span(f"Generated {formatted}"),
        ],
        className="report-generated-at",
    )


def build_history_options(symbol: Optional[str], ttl: float = _LIST_TTL_SECONDS) -> List[Dict[str, str]]:
    options = [{"label": "Current analysis", "value": "current"}]
    if not symbol:
        return options

    cache_key = f"{get_eval_results_dir()}::{symbol}"
    now = time.monotonic()
    cached = _LIST_CACHE.get(cache_key)
    if cached and now - cached[0] < ttl:
        return cached[1]

    from tradingagents.run_logger import list_symbol_runs

    for run in list_symbol_runs(symbol, eval_results_dir=get_eval_results_dir()):
        when = format_report_timestamp(run.get("started_at")) or run.get("trade_date") or run["run_id"]
        extras = [part for part in (run.get("final_signal"),) if part]
        status = run.get("status") or ""
        if status and status != "completed":
            extras.append(status)
        suffix = f" · {' · '.join(extras)}" if extras else ""
        options.append(
            {
                "label": f"{when}{suffix}",
                "value": run["run_id"],
            }
        )

    _LIST_CACHE[cache_key] = (now, options)
    return options


def load_historical_view(symbol: Optional[str], run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not symbol or not run_id or run_id == "current":
        return None

    cache_key = (get_eval_results_dir(), symbol, run_id)
    cached = _VIEW_CACHE.get(cache_key)
    if cached is not None:
        return cached

    from tradingagents.run_logger import extract_reports_from_run, load_run_payload

    payload = load_run_payload(symbol, run_id, eval_results_dir=get_eval_results_dir())
    if not payload:
        return None

    view = extract_reports_from_run(payload)
    _VIEW_CACHE[cache_key] = view
    if len(_VIEW_CACHE) > _VIEW_CACHE_LIMIT:
        _VIEW_CACHE.pop(next(iter(_VIEW_CACHE)))
    return view
