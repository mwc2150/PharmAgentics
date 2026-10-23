"""LLM client seam. v1 talks to Ollama; swap later without touching tools."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from feagent.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT_SEC


class LLMClient(Protocol):
    name: str
    model: str

    def available(self) -> tuple[bool, str]:
        ...

    def complete(self, messages: list[dict[str, str]]) -> str:
        ...


class OllamaClient:
    name = "ollama"

    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = OLLAMA_MODEL,
        timeout: float = OLLAMA_TIMEOUT_SEC,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def list_models(self) -> list[str]:
        tags = self._request("/api/tags", None, timeout=3)
        names: list[str] = []
        for item in tags.get("models", []):
            name = item.get("name") or item.get("model") or ""
            if name:
                names.append(name)
        return names

    def available(self) -> tuple[bool, str]:
        try:
            models = self.list_models()
        except Exception as exc:
            return False, f"Ollama not reachable at {self.host}: {exc}"
        if self._model_is_installed(models):
            return True, f"{self.model} is available"
        if models:
            return (
                False,
                f"Ollama is up, but {self.model} is not pulled. Installed: {', '.join(models)}. "
                f"Set the model name to one of these, or run: ollama pull {self.model}",
            )
        return False, f"Ollama is up, but no models are installed. Run: ollama pull {self.model}"

    def _model_is_installed(self, models: list[str]) -> bool:
        wanted = self.model.strip()
        short = wanted.split(":")[0]
        return any(m == wanted or m.startswith(wanted) or m.startswith(short + ":") for m in models)

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0},
        }
        data = self._request("/api/chat", payload)
        return data.get("message", {}).get("content", "")

    def _request(
        self,
        path: str,
        payload: dict[str, Any] | None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.host + path,
            data=body,
            method="GET" if payload is None else "POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


def parse_json_message(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in model response: {text[:400]}")
    return json.loads(text[start : end + 1])
