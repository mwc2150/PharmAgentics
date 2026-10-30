"""Fixed locations, all relative to the repository root."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "eval"
GOLDEN_DIR = EVAL_DIR / "golden"
MLFLOW_DIR = EVAL_DIR / "mlflow"
STORIES = REPO_ROOT / "docs" / "planning" / "user-stories.md"
EVAL_PACK = REPO_ROOT / "docs" / "planning" / "briefing-evaluation-pack.md"
DATABASE = REPO_ROOT / "local" / "pharmagentics.duckdb"
SOT_DIR = REPO_ROOT / "SoT"

EXPERIMENT = "pharmagentics-golden"
DEFAULT_LOCAL_MODEL = "gemma3:4b"
DEFAULT_JUDGE = f"ollama:/{DEFAULT_LOCAL_MODEL}"


def tracking_uri() -> str:
    return f"sqlite:///{(MLFLOW_DIR / 'mlflow.db').as_posix()}"
