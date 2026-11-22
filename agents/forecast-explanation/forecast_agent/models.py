"""Model options for the Forecast lane. With local Ollama (Qwen 3 4B until the designs are set): keep the model loaded
between steps, so a question does not pay the load time again, and use a context that fits an 8 GB Mac's GPU (8192
tokens), larger only when a long report prompt needs it. Hosted models get the shared defaults unchanged."""
from __future__ import annotations

import os

from pharmagentics.llm import chat_options

KEEP_ALIVE = os.environ.get("FORECAST_OLLAMA_KEEP_ALIVE", "30m")
BASE_CTX = int(os.environ.get("FORECAST_OLLAMA_NUM_CTX", "8192"))
MAX_CTX = int(os.environ.get("FORECAST_OLLAMA_MAX_CTX", "16384"))


def options(spec: str, prompt_chars: int = 0) -> dict:
    """chat_options for `spec`, tuned for local Ollama; `prompt_chars` lets a long prompt get a larger context."""
    opts = dict(chat_options(spec))
    if spec.startswith("ollama:"):
        need = prompt_chars // 3 + 2048  # about three characters a token, plus room for the answer
        ctx = BASE_CTX
        while ctx < need and ctx < MAX_CTX:
            ctx *= 2
        opts.update(num_ctx=min(ctx, MAX_CTX), keep_alive=KEEP_ALIVE)
    return opts
