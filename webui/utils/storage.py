import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")


# Default settings structure
DEFAULT_SETTINGS = {
    "ticker_input": os.getenv("DEFAULT_TICKERS", "INTC, GOOG, AMD, SOXX, SHLD"),
    "analyst_market": True,
    "analyst_social": True,
    "analyst_news": True,
    "analyst_fundamentals": True,
    "analyst_macro": True,
    "research_depth": os.getenv("RESEARCH_DEPTH", "Shallow"),
    "allow_shorts": _env_bool("ALLOW_SHORTS", False),
    "loop_enabled": _env_bool("LOOP_ENABLED", False),
    "loop_interval": int(os.getenv("LOOP_INTERVAL", "60")),
    "market_hour_enabled": _env_bool("MARKET_HOUR_ENABLED", True),
    "market_hours_input": os.getenv("MARKET_HOURS_INPUT", "9, 10, 11, 12, 13, 14, 15"),
    "trade_after_analyze": _env_bool("TRADE_AFTER_ANALYZE", True),
    "trade_dollar_amount": int(os.getenv("TRADE_DOLLAR_AMOUNT", "4500")),
    "llm_provider": os.getenv("LLM_PROVIDER", "google"),
    "backend_url": os.getenv("BACKEND_URL", ""),
    "output_language": "English",
    "checkpoint_enabled": False,
    "quick_llm": os.getenv("QUICK_THINK_LLM", "gemini-2.5-flash"),
    "deep_llm": os.getenv("DEEP_THINK_LLM", "gemini-2.5-flash"),
    "quick_llm_custom_model": "",
    "deep_llm_custom_model": "",
    "google_thinking_level": "",
    "anthropic_effort": "",
}

# Default API keys structure (empty by default, loaded from localStorage or .env)
DEFAULT_API_KEYS = {
    "openai": "",
    "google": "",
    "anthropic": "",
    "xai": "",
    "minimax": "",
    "deepseek": "",
    "dashscope": "",
    "zhipu": "",
    "openrouter": "",
    "azure-openai": "",
    "alpha-vantage": "",
    "alpaca-key": "",
    "alpaca-secret": "",
    "finnhub": "",
    "fred": "",
    "coindesk": "",
    "alpaca-paper": True
}


def get_default_settings() -> Dict[str, Any]:
    """Get the default settings structure"""
    return DEFAULT_SETTINGS.copy()


def get_default_api_keys() -> Dict[str, Any]:
    """Get the default API keys structure"""
    return DEFAULT_API_KEYS.copy()


def create_storage_store_component():
    """Create a dcc.Store component for localStorage persistence"""
    from dash import dcc
    return dcc.Store(id='settings-store', storage_type='local', data=DEFAULT_SETTINGS)


def create_api_keys_store_component():
    """Create a dcc.Store component for API keys localStorage persistence"""
    from dash import dcc
    return dcc.Store(id='api-keys-store', storage_type='local', data=DEFAULT_API_KEYS)
