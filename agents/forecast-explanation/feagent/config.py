from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CASES_DIR = DATA_DIR / "cases"
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(DATA_DIR / "pharmagentics.duckdb"))
PHARMAGENTICS_DATA_DIR = os.environ.get("PHARMAGENTICS_DATA_DIR", "")
API_HOST = os.environ.get("FEAGENT_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("FEAGENT_PORT", "8787"))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")
OLLAMA_TIMEOUT_SEC = float(os.environ.get("OLLAMA_TIMEOUT_SEC", "60"))

MAX_INVESTIGATOR_STEPS = int(os.environ.get("MAX_INVESTIGATOR_STEPS", "12"))
BRAND = "LUMINA"
METRIC = "TRx"
