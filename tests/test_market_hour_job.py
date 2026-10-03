import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webui.utils.market_hour_job import (
    accept_control_click,
    clear_market_hour_job,
    load_market_hour_job,
    save_market_hour_job,
)


class MarketHourJobTests(unittest.TestCase):
    def test_saved_schedule_survives_a_reload(self):
        job = {"symbols": ["NVDA", "AAPL"], "market_hours": [9, 14]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market_hour_schedule.json"
            with patch("webui.utils.market_hour_job.schedule_path", return_value=path):
                save_market_hour_job(job)
                loaded = load_market_hour_job()
                self.assertEqual(loaded["symbols"], ["NVDA", "AAPL"])
                self.assertEqual(loaded["market_hours"], [9, 14])
                clear_market_hour_job()
                self.assertIsNone(load_market_hour_job())
                self.assertFalse(path.exists())

    def test_redrawn_button_does_not_count_as_a_second_click(self):
        accepted, seen = accept_control_click(1, 0)
        self.assertTrue(accepted)
        self.assertEqual(seen, 1)
        accepted, seen = accept_control_click(1, seen)
        self.assertFalse(accepted)
        self.assertEqual(seen, 1)

    def test_a_later_click_is_accepted(self):
        accepted, seen = accept_control_click(2, 1)
        self.assertTrue(accepted)
        self.assertEqual(seen, 2)

    def test_reset_click_count_is_ignored(self):
        accepted, seen = accept_control_click(0, 1)
        self.assertFalse(accepted)
        self.assertEqual(seen, 0)


if __name__ == "__main__":
    unittest.main()
