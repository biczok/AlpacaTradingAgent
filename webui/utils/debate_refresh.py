"""Skip no-op debate tab rebuilds so periodic refresh does not reset scroll."""

_DEBATE_RENDER_CACHE = {}
INTERVAL_TRIGGER = "medium-refresh-interval"


def debate_content_fingerprint(symbol, history_value, debate_state, empty_reason=None):
    """Stable identity for debate tab HTML so unchanged refreshes can be skipped."""
    if empty_reason:
        return ("empty", symbol, history_value or "current", empty_reason)
    if not debate_state:
        return ("empty", symbol, history_value or "current", "missing")
    return (
        symbol,
        history_value or "current",
        debate_state.get("history") or "",
        tuple(debate_state.get("bull_messages") or ()),
        tuple(debate_state.get("bear_messages") or ()),
        tuple(debate_state.get("risky_messages") or ()),
        tuple(debate_state.get("safe_messages") or ()),
        tuple(debate_state.get("neutral_messages") or ()),
        debate_state.get("bull_history") or "",
        debate_state.get("bear_history") or "",
        debate_state.get("risky_history") or "",
        debate_state.get("safe_history") or "",
        debate_state.get("neutral_history") or "",
        debate_state.get("judge_decision") or "",
    )


def skip_unchanged_interval_render(cache_key, fingerprint, triggered_id=None):
    """Return True when a medium-interval tick would rebuild identical debate HTML."""
    if triggered_id == INTERVAL_TRIGGER and _DEBATE_RENDER_CACHE.get(cache_key) == fingerprint:
        return True
    _DEBATE_RENDER_CACHE[cache_key] = fingerprint
    return False
