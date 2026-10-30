"""The only code allowed to read the answer-key store (constitution Principle III).

Unused so far: the 42 dev cases need only agent-visible data. Held-out cases and the
answer key (Evaluation Pack open items 8 and 11) will be read through here.
"""
from __future__ import annotations

import os
from pathlib import Path

from .paths import REPO_ROOT

ENV_VAR = "PHARMAGENTICS_EVAL_STORE"


def store_path() -> Path:
    value = os.environ.get(ENV_VAR)
    if not value:
        raise RuntimeError(f"{ENV_VAR} is not set; the answer-key store lives outside the repository.")
    path = Path(value).resolve()
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise RuntimeError(f"{ENV_VAR} points inside the repository; the store must live outside it.")
    return path
