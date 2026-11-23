"""Print where the project stands, from the handoffs in conversations/ and from git: open work first, then the latest on main."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FOLDER = "conversations"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-.+\.md$")
HEADER_SINCE = "2026-11-24"  # handoffs from this date on start with the header; older ones are left as written
HEADER_KEYS = ("branch", "lane", "next")


@dataclass
class Handoff:
    path: str
    date: str
    title: str
    header: dict[str, str] = field(default_factory=dict)


def _git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def parse(path: str, text: str) -> Handoff | None:
    """A handoff from its path and text; None when the file name carries no date (README.md, for one)."""
    match = NAME.match(path.rsplit("/", 1)[-1])
    if not match:
        return None
    lines = text.replace("\r\n", "\n").split("\n")
    header: dict[str, str] = {}
    body = lines
    if lines and lines[0].strip() == "---" and "---" in (line.strip() for line in lines[1:]):
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
        for line in lines[1:end]:
            key, sep, value = line.partition(":")
            if sep and key.strip() in HEADER_KEYS:
                header[key.strip()] = value.strip()
        body = lines[end + 1:]
    title = next((line[2:].strip() for line in body if line.startswith("# ")), "(no title)")
    return Handoff(path, match.group(1), title, header)


def base_ref() -> str:
    for ref in ("origin/main", "main"):
        if _git("rev-parse", "--verify", "--quiet", ref).strip():
            return ref
    return "HEAD"


def _added_order(base: str) -> dict[str, int]:
    """Commit time at which each handoff first appeared on the base, so handoffs of one day sort newest first."""
    order: dict[str, int] = {}
    stamp = 0
    for line in _git("log", "--format=@%ct", "--name-only", "--diff-filter=A", base, "--", FOLDER).splitlines():
        if line.startswith("@"):
            stamp = int(line[1:] or 0)
        elif line.strip():
            order.setdefault(line.strip(), stamp)
    return order


def on_base(base: str) -> list[Handoff]:
    order = _added_order(base)
    found = []
    for path in _git("ls-tree", "--name-only", base, f"{FOLDER}/").splitlines():
        local = REPO / path
        text = local.read_text(encoding="utf-8", errors="replace") if local.is_file() else _git("show", f"{base}:{path}")
        handoff = parse(path, text)
        if handoff:
            found.append(handoff)
    return sorted(found, key=lambda h: (h.date, order.get(h.path, 0), h.path), reverse=True)


def open_work(base: str, merged: set[str]) -> tuple[list[tuple[str, list[Handoff]]], list[str]]:
    """Handoffs that are not on the base yet, grouped by where they live, and the unmerged branches that have none."""
    groups: list[tuple[str, list[Handoff]]] = []
    here = []
    for local in sorted((REPO / FOLDER).glob("*.md")):
        path = f"{FOLDER}/{local.name}"
        if path not in merged:
            handoff = parse(path, local.read_text(encoding="utf-8", errors="replace"))
            if handoff:
                here.append(handoff)
    if here:
        groups.append((f"this checkout ({_git('branch', '--show-current').strip() or 'detached'})", here))
    seen = {_git("rev-parse", "HEAD").strip()}
    shown = {h.path for h in here}
    bare: list[str] = []
    refs = _git("for-each-ref", f"--no-merged={base}", "--sort=-committerdate",
                "--format=%(objectname) %(committerdate:short) %(refname:short)", "refs/heads", "refs/remotes/origin")
    for line in refs.splitlines():
        sha, day, ref = line.split(" ", 2)
        if sha in seen or ref.endswith("/HEAD"):
            continue
        seen.add(sha)
        ahead = _git("rev-list", "--count", f"{base}..{ref}").strip() or "?"
        label = f"{ref} ({ahead} ahead, {day})"
        added = [p for p in _git("diff", "--name-only", "--diff-filter=A", f"{base}...{ref}", "--", FOLDER).splitlines()
                 if p not in merged and p not in shown]
        handoffs = [h for h in (parse(p, _git("show", f"{ref}:{p}")) for p in added) if h]
        if handoffs:
            shown.update(h.path for h in handoffs)
            groups.append((label, handoffs))
        else:
            bare.append(label)
    return groups, bare


def _entry(handoff: Handoff) -> list[str]:
    lane = f" [{handoff.header['lane']}]" if handoff.header.get("lane") else ""
    lines = [f"- `{handoff.path}`{lane}: {handoff.title}"]
    if handoff.header.get("next"):
        lines.append(f"  next: {handoff.header['next']}")
    return lines


def render(limit: int = 10) -> str:
    base = base_ref()
    tip = _git("log", "-1", "--format=%h, %cd", "--date=short", base).strip()
    merged = on_base(base)
    groups, bare = open_work(base, {h.path for h in merged})
    lines = [f"# Project status (against {base} at {tip})", "",
             "Priorities are in `PROJECT_STATE.md`. Run `git fetch` first if the date above looks old.", "",
             f"## Open: not on {base} yet", ""]
    for label, handoffs in groups:
        lines.append(f"{label}:")
        for handoff in handoffs:
            lines.extend(_entry(handoff))
    if not groups:
        lines.append("No handoff is waiting on an unmerged branch.")
    if bare:
        lines += ["", "Unmerged branches with no handoff: " + "; ".join(bare)]
    shown = merged if limit <= 0 else merged[:limit]
    lines += ["", f"## Latest on {base} ({len(shown)} of {len(merged)}; `--all` lists every one)", ""]
    for handoff in shown:
        lines.extend(_entry(handoff))
    everything = merged + [h for _, handoffs in groups for h in handoffs]
    missing = sorted(h.path for h in everything
                     if h.date >= HEADER_SINCE and not all(h.header.get(key) for key in HEADER_KEYS))
    if missing:
        lines += ["", "## Handoffs missing the branch, lane or next header (see conversations/README.md)", ""]
        lines.extend(f"- `{path}`" for path in missing)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pharmagentics.devtools.status",
        description="Print open handoffs, then the latest handoffs on main. Nothing is written.",
    )
    parser.add_argument("-n", type=int, default=10, help="how many merged handoffs to list (default 10)")
    parser.add_argument("--all", action="store_true", help="list every merged handoff")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(render(0 if args.all else args.n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
