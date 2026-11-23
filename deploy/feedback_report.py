"""Summarize UAT feedback (core-008): the session ratings and the platform questionnaire.

    uv run python deploy/feedback_report.py [--state-dir DIR] [--out report.md] [--csv DIR] [--xlsx FILE.xlsx]

Reads the documents the app stored (the local state folder, default local/state or PHARMAGENTICS_STATE_DIR) and prints a
markdown report: sessions rated good, fine or bad by persona, thumbs up and down on answers (with every downvote), the System Usability Scale score, per-question means, the
net promoter score and every written answer. --csv also writes pulses.csv, votes.csv and survey.csv for a spreadsheet. --xlsx writes one
workbook (Summary, Questionnaire, Answer votes, Session ratings, Comments) for the repo's feedback/ folder: pseudonymous IDs and
role names only, the test login's records left out unless --include-test. For the cloud
copy run `uv run python deploy/gcp.py feedback --project pharmagentics --account <you>`, which downloads the bucket's
feedback/ folder first and then runs this. Nothing here sends anything anywhere.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmagentics.api import feedback, store  # noqa: E402

PULSE_COLUMNS = ["ts", "session", "user", "rating", "personas", "where", "ref", "comment"]
VOTE_COLUMNS = ["ts", "user", "personas", "lane", "ref", "view", "vote", "engine", "data_version", "comment"]


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:  # utf-8-sig: Excel reads it correctly
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def _when(ts: str) -> str:
    return f"{ts[:10]} {ts[11:16]} UTC"


def _cell(value):
    return "; ".join(value) if isinstance(value, list) else value


def _clean(value):
    """Control characters pasted from Word make openpyxl refuse the whole workbook; drop them."""
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    return ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value


def _plain(ws) -> None:
    """Participants' text stays text: a cell starting with "=" would otherwise be saved as a live formula in a file the
    public repository carries."""
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"


def _sheet(wb, title: str, header: list[str], rows: list[list], widths: list[int]):
    """A sheet with a bold, frozen header row and set column widths; text wraps so free answers stay readable."""
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet(title)
    ws.append(header)
    for row in rows:
        ws.append([_clean(v) for v in row])
    for n, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(n)].width = width
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    _plain(ws)
    return ws


def write_xlsx(path: Path, q: dict, pulses: list[dict], surveys: list[dict], votes: list[dict], comments: list[dict]) -> None:
    """One workbook for the class feedback. Only pseudonymous user IDs and role names go in: the stored documents hold
    no name, email or sign-in ID, and the answer text a voter was shown is left out."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    summary = feedback.summarize(pulses, surveys, q, votes)
    survey, pulse, answers = summary["survey"], summary["pulse"], summary["answers"]
    rows = {r["id"]: r for r in survey["items"]}

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    lines: list[tuple] = [
        ("Questionnaire", q["title"], None), ("Current questionnaire version", q["version"], None),
        ("Questionnaire responses", survey["responses"], None),
        ("Responses by questionnaire version", ", ".join(f"v{k}: {v}" for k, v in sorted(survey["versions"].items())) or "none", None)]
    if survey["umux"]:
        u = survey["umux"]
        lines += [("UMUX-Lite, 0 to 100 (mean)", u["raw_mean"], u["n"]),
                  ("UMUX-Lite, SUS-equivalent (mean; 0.65 x raw + 22.9)", u["sus_equivalent_mean"], u["n"])]
    else:
        lines.append(("UMUX-Lite", "no response answered both items", 0))
    if survey["legacy_sus_responses"]:
        s = survey["sus"]
        lines.append(("SUS from questionnaire version 1 (mean, 0 to 100)", s["mean"] if s else "none complete", s["n"] if s else 0))
    if "o_nps" in rows:
        n = rows["o_nps"]
        lines += [("Net promoter score (-100 to 100)", n["nps"], n["n"]), ("Recommend score, mean of 10", n["mean"], n["n"])]
    lines += [(f"Mean, 1 to 5: {r['text']}", r["mean"], r["n"]) for r in survey["items"] if r["type"] == "agree5"]
    lines += [("Sessions rated", pulse["sessions"], None), *((f"Sessions rated {k}", v, None) for k, v in pulse["by_rating"].items()),
              ("Answer votes", answers["votes"], None), ("Thumbs up", answers["up"], None), ("Thumbs down", answers["down"], None),
              ("Suggestions", len(comments), None)]
    ws.append(["Measure", "Value", "Responses"])
    for line in lines:
        ws.append([_clean(v) for v in line])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for col, width in zip("ABC", (62, 30, 12)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    _plain(ws)

    by_id = {i["id"]: i for i in feedback.items(q)}
    item_ids = list(by_id)
    header = ["Submitted", "User (pseudonymous)", "Role", "Questionnaire version", *(by_id[i]["text"] for i in item_ids),
              "UMUX-Lite (0-100)", "UMUX-Lite SUS-equivalent", "SUS (version 1)", "Answers to earlier questionnaire versions"]
    body = []
    for s in sorted(surveys, key=lambda d: d["ts"]):
        u = s.get("umux")
        old = feedback.earlier_answers_text(s, set(by_id))
        body.append([_when(s["ts"]), s["user"], feedback.role_label(s), s["version"], *(_cell(s["answers"].get(i)) for i in item_ids),
                     u["raw"] if u else None, round(u["sus_equivalent"], 1) if u else None, s.get("sus"), old or None])
    _sheet(wb, "Questionnaire", header, body, [18, 20, 22, 14, *([30] * len(item_ids)), 14, 16, 12, 50])

    _sheet(wb, "Answer votes", ["Submitted", "User (pseudonymous)", "Role", "Lane", "View", "Answer", "Vote", "Engine", "Data version", "Comment"],
           [[_when(v["ts"]), v["user"], feedback.role_label(v), v["lane"], v["view"], v["ref"], v["vote"], v.get("engine"),
             v.get("data_version"), v.get("comment")] for v in sorted(votes, key=lambda d: d["ts"])], [18, 20, 22, 10, 12, 20, 8, 12, 24, 50])
    _sheet(wb, "Session ratings", ["Submitted", "User (pseudonymous)", "Role", "Session", "Rating", "Where", "Comment"],
           [[_when(p["ts"]), p["user"], feedback.role_label(p), p["session"], p["rating"], p["where"], p.get("comment")]
            for p in sorted(pulses, key=lambda d: d["ts"])], [18, 20, 22, 14, 10, 12, 50])
    _sheet(wb, "Comments", ["Submitted", "User (pseudonymous)", "Role", "Topic", "Suggestion"],
           [[_when(c["ts"]), c["user"], feedback.role_label(c), c["topic"], c["text"]] for c in comments], [18, 20, 22, 12, 70])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Summarize UAT feedback.")
    ap.add_argument("--state-dir", type=Path, default=Path(os.environ.get("PHARMAGENTICS_STATE_DIR", ROOT / "local" / "state")))
    ap.add_argument("--out", type=Path, help="write the markdown report here instead of printing it")
    ap.add_argument("--csv", type=Path, metavar="DIR", help="also write pulses.csv, votes.csv and survey.csv into this folder")
    ap.add_argument("--xlsx", type=Path, metavar="FILE", help="also write one workbook: Summary, Questionnaire, Answer votes, Session ratings, Comments")
    ap.add_argument("--include-test", action="store_true", help="keep the test login's records in the workbook (left out by default)")
    a = ap.parse_args(argv)
    if not a.state_dir.is_dir():
        print(f"No state folder at {a.state_dir}: nothing has been stored there yet.", file=sys.stderr)
        return 1

    q = feedback.questionnaire()
    backend = store.LocalBackend(a.state_dir)
    pulses, surveys = feedback.load_feedback(backend)
    votes = feedback.load_votes(backend)
    summary = feedback.summarize(pulses, surveys, q, votes)
    summary["comments"] = feedback.load_comments(backend)
    summary["surveys"] = surveys  # for the answers to earlier questionnaire versions
    report = feedback.to_markdown(summary, q)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(report, encoding="utf-8")
        print(f"Report written to {a.out}")
    else:
        print(report)

    if a.csv:
        a.csv.mkdir(parents=True, exist_ok=True)
        _write_csv(a.csv / "pulses.csv", PULSE_COLUMNS,
                   [[p["ts"], p["session"], p["user"], p["rating"], "/".join(p["personas"]), p["where"], p.get("ref") or "",
                     p.get("comment") or ""] for p in sorted(pulses, key=lambda d: d["ts"])])
        _write_csv(a.csv / "votes.csv", VOTE_COLUMNS,
                   [[v["ts"], v["user"], "/".join(v["personas"]), v["lane"], v["ref"], v["view"], v["vote"], v.get("engine") or "",
                     v.get("data_version") or "", v.get("comment") or ""] for v in sorted(votes, key=lambda d: d["ts"])])
        item_ids = [i["id"] for i in feedback.items(q)]
        _write_csv(a.csv / "survey.csv", ["user", "ts", "version", "personas", "sus", *item_ids, "earlier_answers"],
                   [[s["user"], s["ts"], s["version"], "/".join(s["personas"]), "" if s["sus"] is None else s["sus"],
                     *(("; ".join(v) if isinstance(v, list) else v) if (v := s["answers"].get(i)) is not None else "" for i in item_ids),
                     feedback.earlier_answers_text(s, set(item_ids))]
                    for s in sorted(surveys, key=lambda d: d["ts"])])
        print(f"CSV files written to {a.csv}")
    if a.xlsx:
        keep = (lambda docs: docs) if a.include_test else feedback.real_only
        write_xlsx(a.xlsx, q, keep(pulses), keep(surveys), keep(votes), keep(summary["comments"]))
        print(f"Workbook written to {a.xlsx}. Skim the free-text answers before committing it: the repository is public.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
