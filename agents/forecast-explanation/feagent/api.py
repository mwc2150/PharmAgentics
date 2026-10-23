"""Investigation-request interface.

The Briefing Agent (or a manual caller) posts JSON matching InvestigationRequest.
This is the v1 handoff seam; it is not wired to a live briefing agent yet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from feagent.investigator import run_investigation
from feagent.schema import InvestigationRequest


def handle_investigation_request(
    payload: dict[str, Any],
    mode: str = "auto",
    case_id: str = "week18",
) -> dict[str, Any]:
    request = InvestigationRequest.from_dict(payload)
    report = run_investigation(request, mode=mode, case_id=case_id)
    return report.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one forecast-explanation investigation")
    parser.add_argument("request_json", help="Path to an InvestigationRequest JSON file")
    parser.add_argument("--mode", default="auto", choices=["auto", "stub", "ollama"])
    parser.add_argument("--case-id", default="week18")
    args = parser.parse_args()
    payload = json.loads(Path(args.request_json).read_text())
    if "default_request" in payload:
        payload = payload["default_request"]
    report = handle_investigation_request(payload, mode=args.mode, case_id=args.case_id)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
