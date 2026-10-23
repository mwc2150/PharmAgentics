"""Spans and the live event stream (Briefing B-IV; FR-011).

A minimal stand-in for OpenTelemetry: every stage, agent turn, model call and tool
call opens a span. Each span start and end is pushed to a listener (the SSE stream).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Callable

Listener = Callable[[dict[str, Any]], None]


class Tracer:
    def __init__(self, run_id: str, listener: Listener | None = None):
        self.run_id = run_id
        self.listener = listener or (lambda event: None)
        self.spans: list[dict[str, Any]] = []
        self._stack: list[str] = []
        self._n = 0
        self.t0 = time.perf_counter()

    def _ms(self) -> int:
        return int((time.perf_counter() - self.t0) * 1000)

    def emit(self, type_: str, **payload: Any) -> None:
        event = {"type": type_, "run_id": self.run_id, "t_ms": self._ms(), **payload}
        try:
            self.listener(event)
        except Exception:  # a broken listener never breaks the run
            pass

    @property
    def current(self) -> str | None:
        return self._stack[-1] if self._stack else None

    @contextmanager
    def span(self, name: str, *, agent: str = "code", kind: str = "stage", **attrs: Any):
        self._n += 1
        span_id = f"S-{self._n:03d}"
        record = {"span_id": span_id, "parent": self.current, "name": name, "agent": agent,
                  "kind": kind, "start_ms": self._ms(), "end_ms": None, "attrs": dict(attrs), "status": "ok"}
        self.spans.append(record)
        self._stack.append(span_id)
        self.emit("span_start", span=dict(record))
        try:
            yield record
        except Exception as error:
            record["status"] = "error"
            record["attrs"]["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            self._stack.pop()
            record["end_ms"] = self._ms()
            self.emit("span_end", span=dict(record))
