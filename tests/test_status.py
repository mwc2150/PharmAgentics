"""The status command reads handoff headers, tolerates handoffs without one, and renders on this repository."""

from __future__ import annotations

import unittest

from pharmagentics.devtools import status

WITH_HEADER = """---
branch: feature/example
lane: briefing
next: run the Haiku gate: then merge
other: ignored
---

# Example handoff

Body.
"""


class StatusTests(unittest.TestCase):
    def test_header_and_title_are_read(self):
        handoff = status.parse("docs/handoffs/2026-11-24-example.md", WITH_HEADER)
        self.assertEqual(handoff.date, "2026-11-24")
        self.assertEqual(handoff.title, "Example handoff")
        self.assertEqual(handoff.header, {"branch": "feature/example", "lane": "briefing",
                                          "next": "run the Haiku gate: then merge"})

    def test_a_handoff_without_a_header_still_lists(self):
        handoff = status.parse("docs/handoffs/2026-11-20-old.md", "# Old handoff\r\n\r\nText with --- in it.\r\n")
        self.assertEqual((handoff.title, handoff.header), ("Old handoff", {}))

    def test_files_without_a_date_are_not_handoffs(self):
        self.assertIsNone(status.parse("docs/handoffs/README.md", "# Handoffs\n"))

    def test_status_renders_here(self):
        text = status.render()
        self.assertIn("# Project status", text)
        self.assertIn("## Latest on", text)


if __name__ == "__main__":
    unittest.main()
