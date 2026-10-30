"""Optional spans (Briefing B-IV). A no-op unless PHARMAGENTICS_TRACING=1, which the eval runner sets,
so agent code never writes traces on its own. Spans are MLflow spans, which are OpenTelemetry-compatible."""
from __future__ import annotations

import os
from contextlib import contextmanager


@contextmanager
def span(name: str, span_type: str = "CHAIN", inputs=None, **attributes):
    if os.environ.get("PHARMAGENTICS_TRACING") != "1":
        yield None
        return
    import mlflow

    with mlflow.start_span(name=name, span_type=span_type) as sp:
        if inputs is not None:
            sp.set_inputs(inputs)
        if attributes:
            sp.set_attributes(attributes)
        yield sp


def finish(sp, outputs) -> None:
    if sp is not None:
        sp.set_outputs(outputs)
