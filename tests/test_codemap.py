"""The code map renders from the tracked files and its generator never touches the eval folder."""

from __future__ import annotations

import unittest
from pathlib import Path

from pharmagentics.devtools import codemap


class CodemapTests(unittest.TestCase):
    def test_codemap_has_its_three_sections(self):
        text = codemap.render()
        for heading in ("## Folders", "## Context files", "## Python modules"):
            self.assertIn(heading, text)
        self.assertIn("`load_duckdb.py`", text)

    def test_codemap_is_deterministic(self):
        self.assertEqual(codemap.render(), codemap.render())

    def test_codemap_never_reads_eval(self):
        source = Path(codemap.__file__).read_text(encoding="utf-8")
        self.assertNotIn("eval.harness", source)
        self.assertNotIn("import eval", source)


if __name__ == "__main__":
    unittest.main()
