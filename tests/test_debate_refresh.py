import unittest

from webui.utils.debate_refresh import (
    _DEBATE_RENDER_CACHE,
    debate_content_fingerprint,
    skip_unchanged_interval_render,
)


class DebateRefreshTests(unittest.TestCase):
    def setUp(self):
        _DEBATE_RENDER_CACHE.clear()

    def test_same_debate_text_has_the_same_fingerprint(self):
        state = {
            "history": "Risky Analyst: go\nSafe Analyst: wait",
            "risky_messages": ["Risky Analyst: go"],
            "safe_messages": ["Safe Analyst: wait"],
            "neutral_messages": [],
        }
        self.assertEqual(
            debate_content_fingerprint("NVDA", "current", state),
            debate_content_fingerprint("NVDA", "current", state),
        )

    def test_new_message_changes_fingerprint(self):
        first = {
            "history": "Risky Analyst: go",
            "risky_messages": ["Risky Analyst: go"],
            "safe_messages": [],
            "neutral_messages": [],
        }
        second = {
            "history": "Risky Analyst: go\nSafe Analyst: wait",
            "risky_messages": ["Risky Analyst: go"],
            "safe_messages": ["Safe Analyst: wait"],
            "neutral_messages": [],
        }
        self.assertNotEqual(
            debate_content_fingerprint("NVDA", "current", first),
            debate_content_fingerprint("NVDA", "current", second),
        )

    def test_interval_tick_skips_identical_content(self):
        fingerprint = debate_content_fingerprint(
            "NVDA",
            "current",
            {"history": "done", "risky_messages": ["a"]},
        )
        self.assertFalse(
            skip_unchanged_interval_render("risk-debate", fingerprint, "report-history-selector")
        )
        self.assertTrue(
            skip_unchanged_interval_render("risk-debate", fingerprint, "medium-refresh-interval")
        )

    def test_interval_tick_still_renders_when_content_changes(self):
        first = debate_content_fingerprint(
            "NVDA", "current", {"history": "one", "risky_messages": ["a"]}
        )
        second = debate_content_fingerprint(
            "NVDA", "current", {"history": "one two", "risky_messages": ["a", "b"]}
        )
        self.assertFalse(
            skip_unchanged_interval_render("risk-debate", first, "medium-refresh-interval")
        )
        self.assertFalse(
            skip_unchanged_interval_render("risk-debate", second, "medium-refresh-interval")
        )


if __name__ == "__main__":
    unittest.main()
