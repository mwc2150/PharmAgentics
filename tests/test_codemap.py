"""The committed code map is current, fits its budget, and the generator never touches the eval folder."""

from __future__ import annotations

import unittest
from pathlib import Path

from pharmagentics.devtools import codemap

ROOT = Path(__file__).resolve().parents[1]
CODEMAP = ROOT / "docs" / "architecture" / "CODEMAP.md"


class CodemapTests(unittest.TestCase):
    def test_codemap_is_current(self):
        committed = CODEMAP.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(
            committed,
            codemap.render(),
            "docs/architecture/CODEMAP.md is stale; run `uv run python -m pharmagentics.devtools.codemap`",
        )

    def test_codemap_fits_the_budget(self):
        self.assertLessEqual(len(codemap.render()), 30000)

    def test_codemap_never_reads_eval(self):
        source = Path(codemap.__file__).read_text(encoding="utf-8")
        self.assertNotIn("eval.harness", source)
        self.assertNotIn("import eval", source)


if __name__ == "__main__":
    unittest.main()
