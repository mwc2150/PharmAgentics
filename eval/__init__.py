"""Eval-driven development harness for PharmAgentics (spec core-006). Run `python -m eval --help`."""
import os

# Set before anything imports mlflow. MLflow's usage telemetry sends events to an external service
# (data-use rule, EV-9.4) and deadlocks parallel scorer threads on its first import (MLflow 3.17).
os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
