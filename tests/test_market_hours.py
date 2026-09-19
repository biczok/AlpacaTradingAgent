import datetime
import importlib.util
import pathlib
import unittest

import pytz

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "webui" / "utils" / "market_hours.py"
SPEC = importlib.util.spec_from_file_location("market_hours_under_test", MODULE_PATH)
market_hours = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(market_hours)

get_next_market_datetime = market_hours.get_next_market_datetime
is_market_open = market_hours.is_market_open
market_hour_schedule_action = market_hours.market_hour_schedule_action
get_due_market_slot = market_hours.get_due_market_slot
slot_fire_key = market_hours.slot_fire_key


class MarketHoursTests(unittest.TestCase):
    def test_naive_datetime_is_treated_as_eastern_wall_clock(self):
        is_open, reason = is_market_open(datetime.datetime(2025, 1, 6, 10, 0))
        self.assertTrue(is_open, reason)

    def test_aware_utc_datetime_is_converted_to_eastern(self):
        is_open, reason = is_market_open(datetime.datetime(2025, 1, 6, 15, 0, tzinfo=pytz.utc))
        self.assertTrue(is_open, reason)

    def test_2026_nyse_holiday_is_closed(self):
        eastern = pytz.timezone("US/Eastern")
        is_open, reason = is_market_open(eastern.localize(datetime.datetime(2026, 7, 3, 10, 0)))
        self.assertFalse(is_open)
        self.assertIn("holiday", reason.lower())

    def test_next_market_datetime_uses_eastern_schedule_from_aware_input(self):
        start = datetime.datetime(2025, 1, 6, 17, 30, tzinfo=pytz.utc)  # Monday 12:30 PM ET
        next_dt = get_next_market_datetime(11, start)
        self.assertEqual(next_dt.strftime("%Y-%m-%d %H:%M %Z"), "2025-01-07 11:00 EST")

    def test_hour_9_is_due_at_9_10_premarket(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 9, 10))
        action, hour, slot = market_hour_schedule_action([9, 14], now)
        self.assertEqual(action, "run")
        self.assertEqual(hour, 9)
        self.assertEqual(slot.strftime("%Y-%m-%d %H:%M"), "2026-09-18 09:10")

    def test_late_start_during_open_hours_catches_up_latest_slot(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 10, 5))
        action, hour, slot = market_hour_schedule_action([9, 14], now)
        self.assertEqual(action, "run")
        self.assertEqual(hour, 9)

    def test_after_morning_run_waits_for_afternoon_slot(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 10, 5))
        morning = eastern.localize(datetime.datetime(2026, 9, 18, 9, 10))
        fired = {slot_fire_key(morning, 9)}
        action, hour, slot = market_hour_schedule_action([9, 14], now, fired=fired)
        self.assertEqual(action, "wait")
        self.assertEqual(hour, 14)
        self.assertEqual(slot.strftime("%Y-%m-%d %H:%M"), "2026-09-18 14:00")

    def test_old_scheduler_would_skip_current_slot_at_exact_time(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 14, 0))
        # get_next_market_datetime treats an exact hit as already passed.
        self.assertEqual(
            get_next_market_datetime(14, now).strftime("%Y-%m-%d"),
            "2026-09-21",
        )
        action, hour, _ = market_hour_schedule_action([9, 14], now)
        self.assertEqual((action, hour), ("run", 14))

    def test_friday_evening_waits_until_monday_premarket(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 22, 56))
        self.assertIsNone(get_due_market_slot([9, 14], now))
        action, hour, slot = market_hour_schedule_action([9, 14], now)
        self.assertEqual(action, "wait")
        self.assertEqual(hour, 9)
        self.assertEqual(slot.strftime("%Y-%m-%d %H:%M %Z"), "2026-09-21 09:10 EDT")

    def test_closed_market_does_not_catch_up_hours_later(self):
        eastern = pytz.timezone("US/Eastern")
        now = eastern.localize(datetime.datetime(2026, 9, 18, 17, 30))
        self.assertIsNone(get_due_market_slot([9, 14], now))


if __name__ == "__main__":
    unittest.main()
