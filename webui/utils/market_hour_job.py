"""Persist the armed market-hour schedule and restart it with the process.

The wait loop lives in memory. A service restart drops it. The last Start
click is written to disk so the next process can arm the same job.
"""

import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from webui.utils.state import app_state


def schedule_path():
    override = os.getenv("TRADINGAGENTS_SCHEDULE_PATH")
    if override:
        return Path(override)
    home = os.path.join(os.path.expanduser("~"), ".tradingagents")
    return Path(home) / "market_hour_schedule.json"


def save_market_hour_job(job):
    path = schedule_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(f"[MARKET_HOUR] Saved schedule to {path}")
    return path


def load_market_hour_job():
    path = schedule_path()
    if not path.is_file():
        return None
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[MARKET_HOUR] Could not read saved schedule: {exc}")
        return None
    if not job.get("symbols") or not job.get("market_hours"):
        return None
    return job


def clear_market_hour_job():
    path = schedule_path()
    try:
        path.unlink()
        print(f"[MARKET_HOUR] Cleared saved schedule {path}")
    except FileNotFoundError:
        pass


def accept_control_click(n_clicks, seen):
    """Ignore the same click when the Start/Stop button is redrawn.

    Returns (accepted, new_seen).
    """
    if n_clicks is None or n_clicks == 0:
        return False, 0
    if seen is not None and n_clicks <= seen:
        return False, seen
    return True, n_clicks


def scheduler_is_alive():
    thread = getattr(app_state, "market_hour_thread", None)
    return bool(app_state.market_hour_enabled and thread is not None and thread.is_alive())


def _provider_settings(job):
    return {
        "google_thinking_level": job.get("google_thinking_level") or None,
        "anthropic_effort": job.get("anthropic_effort") or None,
    }


def run_market_hour_loop(job):
    """Block until market-hour mode is stopped. One scheduled run per due slot."""
    from webui.components.analysis import start_analysis
    from webui.utils.market_hours import market_hour_schedule_action, slot_fire_key

    symbols = list(job["symbols"])
    hours = [int(hour) for hour in job["market_hours"]]
    provider_settings = _provider_settings(job)
    app_state.start_market_hour_mode(symbols, job, hours)

    last_logged_slot = None
    while not app_state.stop_market_hour:
        try:
            action, next_hour, next_dt = market_hour_schedule_action(
                app_state.market_hours,
                fired=app_state.market_hour_fired,
            )
        except Exception as exc:
            print(f"[MARKET_HOUR] Scheduler failed to compute the next slot: {exc}")
            traceback.print_exc()
            time.sleep(30)
            continue

        slot_label = next_dt.strftime("%A, %B %d at %I:%M %p %Z")

        if action == "wait":
            log_key = (next_hour, slot_label)
            if last_logged_slot != log_key:
                print(f"[MARKET_HOUR] Next execution: {slot_label} (Hour {next_hour})")
                last_logged_slot = log_key
            remaining = (next_dt - datetime.now(timezone.utc)).total_seconds()
            sleep_for = 1 if remaining <= 90 else 30
            time.sleep(min(sleep_for, remaining) if remaining > 0 else 1)
            continue

        fire_key = slot_fire_key(next_dt, next_hour)
        print(f"[MARKET_HOUR] Starting analysis for {slot_label} (Hour {next_hour})")
        app_state.reset_for_loop()
        for symbol in symbols:
            app_state.init_symbol_state(symbol)
        app_state.add_symbols_to_queue(symbols)

        try:
            while app_state.analysis_queue and not app_state.stop_market_hour:
                symbol = app_state.get_next_symbol()
                if not symbol:
                    continue
                print(f"[MARKET_HOUR] Analyzing {symbol} at {slot_label}...")
                start_analysis(
                    symbol,
                    job.get("analysts_market"),
                    job.get("analysts_social"),
                    job.get("analysts_news"),
                    job.get("analysts_fundamentals"),
                    job.get("analysts_macro"),
                    job.get("research_depth"),
                    job.get("allow_shorts"),
                    job.get("quick_llm"),
                    job.get("deep_llm"),
                    job.get("quick_llm_params") or {},
                    job.get("deep_llm_params") or {},
                    llm_provider=job.get("llm_provider"),
                    backend_url=job.get("backend_url"),
                    output_language=job.get("output_language") or "English",
                    checkpoint_enabled=job.get("checkpoint_enabled"),
                    provider_settings=provider_settings,
                )
                if app_state.stop_market_hour:
                    break
        except Exception as exc:
            print(f"[MARKET_HOUR] Analysis failed for {slot_label}: {exc}")
            traceback.print_exc()
        finally:
            app_state.market_hour_fired.add(fire_key)

        if not app_state.stop_market_hour:
            print(f"[MARKET_HOUR] Analysis completed for {slot_label}. Waiting for next execution time.")

    app_state.analysis_running = False


def start_market_hour_thread(job, persist=True):
    """Arm the in-memory scheduler. Persist so a process restart can resume it."""
    if scheduler_is_alive():
        print("[MARKET_HOUR] Scheduler is already running")
        return False
    if persist:
        save_market_hour_job(job)
    for symbol in job["symbols"]:
        app_state.init_symbol_state(symbol)
    app_state.analysis_running = True
    app_state.trade_enabled = bool(job.get("trade_enabled"))
    app_state.trade_amount = job.get("trade_amount") or 1000
    thread = threading.Thread(
        target=run_market_hour_loop,
        args=(job,),
        name="market-hour-scheduler",
    )
    app_state.market_hour_thread = thread
    thread.start()
    return True


def resume_market_hour_job():
    """Start the saved schedule when this process boots. No browser click required."""
    job = load_market_hour_job()
    if not job:
        print("[MARKET_HOUR] No saved schedule. Waiting for Start Analysis.")
        return False
    print(
        f"[MARKET_HOUR] Resuming saved schedule for {job['symbols']} at hours {job['market_hours']}"
    )
    return start_market_hour_thread(job, persist=False)
