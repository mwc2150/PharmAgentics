"""Print a compact map of the repo (folders, context files, Python modules) that coding agents read before crawling the tree."""

from __future__ import annotations

import argparse
import ast
import posixpath
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BUDGET = 30_000
PUBLIC_NAMES_SHOWN = 6

FOLDERS: list[tuple[str, str]] = [
    (
        "src/pharmagentics/",
        "shared data layer and orchestration: data/ (loader, checks), tools/ (governed read-only queries, "
        "evidence, claim tokens, the driver checks, question parser, stage steps), mcp_server/ (the tools over "
        "MCP; Proposed as the shared interface, S9), api/ (web app API and roles), llm.py (agent model clients), "
        "tracing.py, devtools/ (this code map and the status command)",
    ),
    (
        "agents/brand-briefing/",
        "Briefing lane; briefing_baseline/ is its scripted baseline, briefing_lowcode/ its low-code build "
        "(Magentic-One over the MCP server), briefing_agent/ the agent team (build 3); prompts/ folders hold "
        "the agent prompts (code, not docs)",
    ),
    (
        "agents/forecast-explanation/",
        "Forecast lane (Alvin, Sienna); forecast_baseline/ is the scripted baseline BL-0, feagent/ and "
        "forecast_agent/ the fcst-002 agent",
    ),
    (
        "eval/",
        "golden set (42 cases), scorers, controls, MLflow store (eval/mlflow/, git-ignored). Agent code never reads it",
    ),
    (
        "frontend/figma-make/",
        "the team's web UI (dark theme only); has its own AGENTS.md and CLAUDE.md",
    ),
    (
        "deploy/",
        "Docker Compose, Keycloak realm, Google Cloud scripts (gcp.py), UAT worker setup",
    ),
    (
        "data/agent_visible/",
        "the 14-table synthetic release; local/pharmagentics.duckdb is built from it",
    ),
    (
        "sql/",
        "governed reporting views loaded into DuckDB (001_reporting_views.sql)",
    ),
    (
        "specs/",
        "Spec Kit specs: core-### shared, brief-### Briefing, fcst-### Forecast",
    ),
    (
        "docs/",
        "README.md (index), handoffs/ (one dated handoff per branch or session; `python -m pharmagentics.devtools.status` summarises them), open-items.md, guides/ (build and run, workflow, DuckDB first run, UAT), planning/ (Markdown copies of the source docs), adr/, architecture/ (diagrams), team/",
    ),
    (
        "SoT/",
        "dated Drive exports of the source docs; drops git-ignored, README and check.py committed",
    ),
    (
        "tests/",
        "data-foundation, tools, API and UI tests; fixtures/ holds large recorded answers (do not load whole)",
    ),
    (
        ".specify/",
        "Spec Kit templates and scripts, and both constitutions in memory/",
    ),
    (
        ".claude/skills/",
        "the same Spec Kit skills for Claude Code (tool-mandated path)",
    ),
    (
        ".agents/skills/",
        "the same Spec Kit skills for Codex (tool-mandated path)",
    ),
    (
        ".github/workflows/",
        "CI (data-foundation.yml) and the Cloud Run deploy (deploy-uat.yml)",
    ),
    (
        ".impeccable/",
        "config for the impeccable UI skill's hook (it reads PRODUCT.md and DESIGN.md at the root)",
    ),
]

CONTEXT_NAMES = {"README.md", "CLAUDE.md", "AGENTS.md"}
CONTEXT_EXCLUDED_PREFIXES = ("specs/", ".claude/", ".agents/", ".specify/")
MODULE_PREFIXES = ("src/pharmagentics/", "agents/")


def _tracked_files() -> list[str]:
    """Tracked paths from git, sorted, with forward slashes."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    paths = [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    return sorted(paths)


def _folders_section() -> list[str]:
    lines = ["## Folders", "", "| Folder | What it holds |", "| --- | --- |"]
    for folder, description in FOLDERS:
        lines.append(f"| `{folder}` | {description} |")
    return lines


def _context_section(tracked: list[str]) -> list[str]:
    selected = []
    for path in tracked:
        name = posixpath.basename(path)
        if name not in CONTEXT_NAMES:
            continue
        if path == "CLAUDE.md":
            continue
        if path.startswith(CONTEXT_EXCLUDED_PREFIXES):
            continue
        if "node_modules" in path.split("/"):
            continue
        selected.append(path)
    lines = ["## Context files", ""]
    lines.extend(f"- `{path}`" for path in sorted(selected))
    return lines


def _is_module(path: str) -> bool:
    if not path.startswith(MODULE_PREFIXES) or not path.endswith(".py"):
        return False
    parts = path.split("/")
    if "tests" in parts[:-1]:
        return False
    name = parts[-1]
    if name.startswith("test_") or name == "conftest.py":
        return False
    return True


def _public_names(tree: ast.Module) -> list[str]:
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    return names


def _describe_module(path: str) -> tuple[str, list[str]] | None:
    """Return (docstring summary, public names) for a module, or None to skip it."""
    try:
        tree = ast.parse((REPO / path).read_bytes(), filename=path)
    except (SyntaxError, ValueError):
        return "(could not parse)", []
    doc = ast.get_docstring(tree)
    first = doc.strip().splitlines()[0].strip() if doc and doc.strip() else ""
    if path.endswith("/__init__.py") and not first:
        return None
    return (first or "(no docstring)"), _public_names(tree)


def _format_module(name: str, summary: str, public: list[str]) -> str:
    line = f"- `{name}` — {summary}"
    if public:
        shown = ", ".join(public[:PUBLIC_NAMES_SHOWN])
        if len(public) > PUBLIC_NAMES_SHOWN:
            shown += ", …"
        line += f" (public: {shown})"
    return line


def _modules_section(tracked: list[str]) -> list[str]:
    by_dir: dict[str, list[str]] = {}
    for path in tracked:
        if not _is_module(path):
            continue
        if not (REPO / path).is_file():
            continue
        described = _describe_module(path)
        if described is None:
            continue
        summary, public = described
        parent, name = path.rsplit("/", 1)
        by_dir.setdefault(parent + "/", []).append(_format_module(name, summary, public))
    lines = ["## Python modules", ""]
    for directory in sorted(by_dir):
        lines.append(f"### {directory}")
        lines.append("")
        lines.extend(by_dir[directory])
        lines.append("")
    return lines


def render() -> str:
    """The code map text, deterministic for a given set of tracked files."""
    tracked = _tracked_files()
    lines = [
        "# Code map",
        "",
        "Printed by `uv run python -m pharmagentics.devtools.codemap` from the tracked files, so it is always "
        "current and never committed. Read it before crawling the tree; go to the READMEs and folder CLAUDE.md "
        "files below for detail, then to the code.",
        "",
    ]
    lines.extend(_folders_section())
    lines.append("")
    lines.extend(_context_section(tracked))
    lines.append("")
    lines.extend(_modules_section(tracked))
    lines.append("Commands: see `AGENTS.md` and `docs/guides/build-and-run.md`.")
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pharmagentics.devtools.codemap",
        description="Print a compact map of the repository: folders, context files and Python modules.",
    )
    parser.add_argument("--out", help="write the map to this file instead of printing it (keep it out of git)")
    args = parser.parse_args(argv)
    text = render()
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print(f"wrote {args.out} ({len(text)} characters)")
        return 0
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
