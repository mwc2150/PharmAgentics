"""Answer-key isolation (constitution Principle III; EV-9.3, FE-30)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .paths import REPO_ROOT

STORE_VAR = "PHARMAGENTICS_EVAL_STORE"
STORE_READER = "eval/harness/store.py"
GROUND_TRUTH_NAME = re.compile(
    r"answer[_ -]?key|ground[_ -]?truth|counterfactual|true_before_feed_artifacts|held[_ -]?out[_ -]?(params|sealed)"
    r"|heldout[_ -]?(params|sealed)|eval_private",
    re.I,
)
CODE_SUFFIXES = {".py", ".ps1", ".sh", ".js", ".ts", ".ipynb", ".sql"}
AGENT_CODE_DIRS = ("src/", "agents/")


def repo_files() -> list[str]:
    """Tracked files plus untracked files git does not ignore."""
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line and (REPO_ROOT / line).is_file()]


def ground_truth_files(paths) -> list[str]:
    return [str(p) for p in paths if GROUND_TRUTH_NAME.search(str(p))]


def _text(root: Path, f: str) -> str:
    return (root / f).read_text(encoding="utf8", errors="ignore")


def store_readers(files: list[str], root: Path = REPO_ROOT) -> list[str]:
    allowed = (STORE_READER, "eval/harness/isolation.py", "eval/tests/test_isolation.py")
    return [f for f in files if Path(f).suffix in CODE_SUFFIXES and f not in allowed and STORE_VAR in _text(root, f)]


def agent_code_reading_eval(files: list[str], root: Path = REPO_ROOT) -> list[str]:
    pattern = re.compile(r"^\s*(from|import)\s+eval\b|eval[/\\]golden", re.M)
    return [f for f in files if f.startswith(AGENT_CODE_DIRS) and Path(f).suffix in CODE_SUFFIXES
            and pattern.search(_text(root, f))]


def sot_drop_violations(sot_dir: Path) -> list[str]:
    """Any file in a SoT drop whose name looks like ground truth. Drops are git-ignored, so walk the disk."""
    if not sot_dir.exists():
        return []
    return ground_truth_files(p.relative_to(sot_dir).as_posix() for p in sot_dir.rglob("*") if p.is_file())
