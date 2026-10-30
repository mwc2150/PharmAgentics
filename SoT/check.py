"""Check a source-of-truth drop before it updates Spec Kit. Changes nothing.

    uv run python SoT/check.py              newest drop
    uv run python SoT/check.py 2026-10-29   a named drop

1. Refuses the drop if a file name looks like ground truth (answer key, held-out parameters).
2. Lists files added, changed or removed since the previous drop.
3. For each Google Doc with a Markdown copy in docs/planning/, prints the lines that differ.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.harness.isolation import sot_drop_violations  # noqa: E402

SOT, PLANNING = ROOT / "SoT", ROOT / "docs" / "planning"
COPIES = [  # (words in the Drive file name, its copy in docs/planning/)
    ("user stories", "user-stories.md"),
    ("evaluation pack", "briefing-evaluation-pack.md"),
    ("system architecture (sot)", "system-architecture.md"),
    ("architecture 10", "briefing-architecture.md"),
    ("personas - ", "briefing-personas.md"),
]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def drop_date(path: Path) -> str | None:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name):
        return path.name
    if m := re.match(r"drive-download-(\d{4})(\d{2})(\d{2})T", path.name):
        return "-".join(m.groups())
    return None


def key(name: str) -> str:
    return re.sub(r"^copy of ", "", name.lower())


def docx_lines(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    lines = []
    for block in body:
        if block.tag == W + "p":
            lines.append("".join(t.text or "" for t in block.iter(W + "t")))
        elif block.tag == W + "tbl":
            for row in block.iter(W + "tr"):
                lines.append(" | ".join("".join(t.text or "" for t in c.iter(W + "t")) for c in row.iter(W + "tc")))
    return lines


def pdf_lines(path: Path) -> list[str]:
    from pypdf import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages).splitlines()


def norm(lines) -> list[str]:
    out = []
    for line in lines:
        if line.startswith("<!--"):
            continue
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        s = re.sub(r"\s+", " ", re.sub(r"[*_`#>|]|:-+|^\s*[-+]\s+", " ", s)).strip().lower()
        if len(s) >= 25:
            out.append(s)
    return out


def missing_from(lines: list[str], other: list[str]) -> list[str]:
    joined = " ".join(other)
    def close(line):
        return any(difflib.SequenceMatcher(None, line, o, autojunk=False).quick_ratio() > 0.85
                   and difflib.SequenceMatcher(None, line, o, autojunk=False).ratio() > 0.85 for o in other)
    return [x for x in lines if x not in joined and not close(x)]


def report_diff(title: str, new: list[str], old: list[str]) -> None:
    added, removed = missing_from(new, old), missing_from(old, new)
    print(f"  {title}: {len(added)} new or changed line(s), {len(removed)} gone")
    for x in added[:15]:
        print(f"    + {x[:200]}")
    for x in removed[:15]:
        print(f"    - {x[:200]}")


def main(argv: list[str]) -> int:
    drops = sorted((d for d in SOT.iterdir() if d.is_dir() and drop_date(d)), key=lambda d: (drop_date(d), d.name))
    if not drops:
        print("No drops in SoT/. Put a Drive export there as SoT/YYYY-MM-DD/.")
        return 1
    drop = next((d for d in drops if argv and argv[0] in (d.name, drop_date(d))), drops[-1] if not argv else None)
    if drop is None:
        print(f"No drop named {argv[0]}.")
        return 1
    print(f"Drop {drop.name} ({drop_date(drop)})")

    bad = sot_drop_violations(drop)
    if bad:
        print("REFUSED: these look like ground truth and must not be in the repository:")
        for b in bad:
            print(f"  {b}")
        return 2

    files = {key(p.name): p for p in drop.iterdir() if p.is_file()}
    previous = drops[drops.index(drop) - 1] if drops.index(drop) > 0 else None
    if previous:
        old = {key(p.name): p for p in previous.iterdir() if p.is_file()}
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        print(f"\nSince {previous.name}:")
        for k in sorted(files.keys() | old.keys()):
            state = ("added" if k not in old else "removed" if k not in files
                     else "unchanged" if digest(files[k]) == digest(old[k]) else "changed")
            print(f"  {state:<9} {k}")
            if state == "changed" and k.endswith(".pdf"):
                report_diff(f"text of {k}", norm(pdf_lines(files[k])), norm(pdf_lines(old[k])))
    else:
        print("\nFirst drop: no earlier drop to compare with.")

    print("\nAgainst the copies in docs/planning/:")
    for k, path in sorted(files.items()):
        copy = next((c for words, c in COPIES if words in k), None)
        if path.suffix == ".docx" and copy:
            report_diff(f"{path.name} -> {copy}", norm(docx_lines(path)),
                        norm((PLANNING / copy).read_text(encoding="utf8").splitlines()))
        elif path.suffix == ".docx":
            print(f"  {path.name}: no copy in docs/planning/ (add one, or list it as not copied there)")
    print("\nNext: refresh the changed copies, update the specs and golden cases that cite them, "
          "and add a row to the log in SoT/README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
