import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tradingagents.run_logger import (
    extract_reports_from_run,
    list_symbol_runs,
    list_symbols_with_runs,
    load_run_payload,
)
from webui.utils.report_history import (
    collect_picker_symbols,
    format_report_timestamp,
    resolve_picker_symbol,
)


def _write_run(root, symbol, run_id, trade_date, started_at, status="completed", **extra):
    runs_dir = Path(root) / symbol / "TradingAgentsStrategy_logs" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "symbol": symbol,
        "trade_date": trade_date,
        "started_at": started_at,
        "ended_at": started_at,
        "status": status,
        "summary": extra.pop("summary", {}),
        "events": extra.pop("events", []),
        "snapshots": extra.pop("snapshots", {}),
    }
    payload.update(extra)
    (runs_dir / f"{run_id}.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


class ReportHistoryLoaderTests(unittest.TestCase):
    def test_lists_newest_runs_with_reports_and_skips_empty(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "AAPL", "run-old", "2026-09-10",
                "2026-09-10T09:00:00+00:00",
                snapshots={"final_state": {"market_report": "old market"}},
                summary={"final_signal": "HOLD"},
            )
            _write_run(
                root, "AAPL", "run-new", "2026-09-12",
                "2026-09-12T15:30:00+00:00",
                snapshots={"final_state": {"final_trade_decision": "BUY AAPL"}},
                summary={"final_signal": "BUY"},
            )
            _write_run(
                root, "AAPL", "run-empty", "2026-09-11",
                "2026-09-11T12:00:00+00:00",
            )

            runs = list_symbol_runs("AAPL", eval_results_dir=root)

        self.assertEqual([item["run_id"] for item in runs], ["run-new", "run-old"])
        self.assertEqual(runs[0]["final_signal"], "BUY")

    def test_load_and_extract_reports_and_timestamps(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "AAPL", "run-1", "2026-09-12",
                "2026-09-12T16:05:00+00:00",
                snapshots={
                    "final_state": {
                        "market_report": "market body",
                        "investment_plan": "manager plan",
                        "investment_debate_state": {
                            "judge_decision": "research judge",
                            "history": "bull vs bear",
                        },
                        "trader_investment_plan": "trader body",
                        "final_trade_decision": "BUY",
                    }
                },
                events=[
                    {
                        "timestamp": "2026-09-12T16:10:11+00:00",
                        "type": "agent_output",
                        "payload": {
                            "output_type": "market_report",
                            "content": "market body",
                        },
                    }
                ],
            )
            payload = load_run_payload("AAPL", "run-1", eval_results_dir=root)
            view = extract_reports_from_run(payload)

        self.assertEqual(view["reports"]["market_report"], "market body")
        self.assertEqual(view["reports"]["research_manager_report"], "research judge")
        self.assertEqual(view["reports"]["trader_investment_plan"], "trader body")
        self.assertEqual(view["timestamps"]["market_report"], "2026-09-12T16:10:11+00:00")
        self.assertEqual(view["investment_debate_state"]["history"], "bull vs bear")

    def test_extracts_partial_reports_from_events_when_snapshot_missing(self):
        view = extract_reports_from_run(
            {
                "started_at": "2026-09-12T10:00:00+00:00",
                "events": [
                    {
                        "timestamp": "2026-09-12T10:05:00+00:00",
                        "type": "agent_output",
                        "payload": {
                            "output_type": "sentiment_report",
                            "content": "social body",
                        },
                    }
                ],
            }
        )
        self.assertEqual(view["reports"]["sentiment_report"], "social body")
        self.assertEqual(view["timestamps"]["sentiment_report"], "2026-09-12T10:05:00+00:00")

    def test_crypto_symbol_is_sanitized(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "BTC_USD", "run-btc", "2026-09-12",
                "2026-09-12T08:00:00+00:00",
                snapshots={"final_state": {"news_report": "btc news"}},
            )
            runs = list_symbol_runs("BTC/USD", eval_results_dir=root)
            payload = load_run_payload("BTC/USD", "run-btc", eval_results_dir=root)

        self.assertEqual(len(runs), 1)
        self.assertEqual(payload["run_id"], "run-btc")

    def test_missing_directory_is_empty(self):
        self.assertEqual(list_symbol_runs("ZZZZ", eval_results_dir="no_such_dir"), [])
        self.assertIsNone(load_run_payload("ZZZZ", "missing", eval_results_dir="no_such_dir"))

    def test_lists_symbols_that_have_run_files(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "AAPL", "run-1", "2026-09-12",
                "2026-09-12T10:00:00+00:00",
                snapshots={"final_state": {"market_report": "body"}},
            )
            _write_run(
                root, "BTC_USD", "run-btc", "2026-09-12",
                "2026-09-12T11:00:00+00:00",
            )
            empty_dir = Path(root) / "MSFT" / "TradingAgentsStrategy_logs" / "runs"
            empty_dir.mkdir(parents=True)

            symbols = list_symbols_with_runs(eval_results_dir=root)

        self.assertEqual(symbols, ["AAPL", "BTC_USD"])


class PickerSymbolTests(unittest.TestCase):
    def test_merges_live_config_and_saved_symbols_without_duplicates(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "NVDA", "run-1", "2026-09-12",
                "2026-09-12T10:00:00+00:00",
            )
            _write_run(
                root, "AAPL", "run-2", "2026-09-12",
                "2026-09-12T11:00:00+00:00",
            )
            symbols = collect_picker_symbols(
                "AAPL, GOOG",
                live_symbols=["INTC", "AAPL"],
                eval_results_dir=root,
            )

        self.assertEqual(symbols, ["INTC", "AAPL", "GOOG", "NVDA"])

    def test_resolve_picker_uses_page_index_into_merged_list(self):
        with tempfile.TemporaryDirectory() as root:
            _write_run(
                root, "MSFT", "run-1", "2026-09-12",
                "2026-09-12T10:00:00+00:00",
            )
            symbol = resolve_picker_symbol(
                3,
                "INTC, GOOG",
                live_symbols=["INTC"],
                eval_results_dir=root,
            )

        self.assertEqual(symbol, "MSFT")


class TimestampFormattingTests(unittest.TestCase):
    def test_formats_iso_and_unix(self):
        iso = format_report_timestamp("2026-09-12T16:05:00+00:00")
        unix = format_report_timestamp(
            datetime(2026, 9, 12, 16, 5, tzinfo=timezone.utc).timestamp()
        )
        self.assertIsNotNone(iso)
        self.assertIn("2026", iso)
        self.assertIsNotNone(unix)
        self.assertIsNone(format_report_timestamp(None))
        self.assertIsNone(format_report_timestamp(0))


if __name__ == "__main__":
    unittest.main()
