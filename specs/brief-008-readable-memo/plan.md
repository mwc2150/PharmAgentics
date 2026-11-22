# Plan: brief-008 A Readable Memo

A file contract for the agents that build this spec in parallel. Each work packet in `tasks.md` owns the files listed for it. A packet that must change a file owned by another packet stops and writes a note in its handoff instead.

## Block schema (the contract between the backend and the UI)

New optional fields on a memo section dict. They are built by code, carry `{cN}` claim tokens before `render_sections`, and filled values after. `render_sections` fills them like `text` and records their citations. An older stored brief has none of them, and the UI renders it as today.

```python
# on section "1"
"kpis": [                                   # 3 to 4 tiles, in this order
  {"label": "National BXA TRx",              # plain words, no digits
   "value": "{c1}",                          # one claim token
   "detail": "projected, week of 2026-08-24", # optional; tokens and ISO dates allowed
   "direction": "up" | "down" | "flat" | None},
]
# on section "2"
"territory_table": {
  "columns": ["Territory", "BXA TRx", "On the week before", "On the comparison weeks", "Basis"],
  "rows": [{"cells": ["Great Lakes", "{c7}", "down {c8}", "down {c9}", "observed"],
            "basis": "observed" | "projected" | "estimated" | "withheld"}],
  "note": "Compared with the four weeks before (2026-07-27 to 2026-08-17)."  # optional, tokens allowed
}
# on each story section "3.N"
"card": {"headline": "Southeast fell {c20} against the other territories", # tokens allowed
         "confidence": "High" | "Medium" | "Low",
         "drivers_checked": ["promotion", "access", "supply", "competitor"]}
# on any section
"detail": "…lines shown folded under Show detail (analysts only)…"        # tokens allowed
```

After `render_sections`, each filled field keeps its citations: `kpis[i].value_citation`, `territory_table.rows[j].cell_citations`, `card.headline_citations`, `detail_citations`, all in the same `{start, end, claim}` span form as `text_citations`.

Rules:
- Every number in a block is a claim token that also appears in the section's `text` or `detail`. A block adds no claim the answer text lacks, so the scored `answer` keeps every claim (FR-002).
- `compose` writes `text` + `detail` into the flattened answer, in that order. The visible `text` is what fits two pages; `detail` is the depth.
- The leader cut (`api/views.py`) passes `kpis`, `territory_table` and `card` (values and labels only, no citations). It passes `text` and the charts as today, never `detail`. It adds §4 in short form (its first paragraph) and the Assumptions from §6 (FR-005).
- For a one-week period, "On the week before" is filled; for a multi-week period, that column is dropped (FR-011).

## Packets and the files they own

| Packet | Owns | Must not touch |
| :- | :- | :- |
| **F: form, scope, menu** | `frontend/figma-make/src/App.tsx` (AccountMenu, New briefing form, scope card), `frontend/figma-make/src/ComparisonPicker.tsx`, new `frontend/figma-make/src/BriefingScope.tsx`, `frontend/figma-make/src/agent/briefingApi.ts` (request and scope types only), `src/pharmagentics/api/schemas.py` (BriefingQuery, new BriefingScope models), `src/pharmagentics/api/service.py` (`normalize_question`), `src/pharmagentics/api/app.py` (new route only), new `agents/brand-briefing/briefing_agent/reader.py`, new `agents/brand-briefing/briefing_agent/prompts/scope_reader.md`, `tests/test_briefing_api.py`, `tests/test_frontend_scope.py`, new `tests/test_briefing_scope.py` | memo, views, charts, promotion, Memo.tsx |
| **M: memo blocks and prose** | `src/pharmagentics/tools/memo.py`, `src/pharmagentics/tools/charts.py`, `src/pharmagentics/tools/stages.py` (text only), `agents/brand-briefing/briefing_baseline/pipeline.py`, `src/pharmagentics/mcp_server/server.py` (`brief_sections`, `memo_close`), `agents/brand-briefing/briefing_agent/write.py` (`assemble`), `src/pharmagentics/api/views.py`, `tests/test_memo.py`, `tests/test_charts.py`, `tests/test_agent_build3.py`, `tests/test_rbac.py` (leader-cut tests), `tests/test_triage.py` (fixture test), `tests/fixtures/scripted_answers.json` | App.tsx, Memo.tsx, promotion.py, window.py |
| **R: memo rendering** | `frontend/figma-make/src/Memo.tsx`, `frontend/figma-make/src/agent/briefingApi.ts` (MemoSection, ChartSpec types only), `frontend/figma-make/src/index.css` (print rules only) | App.tsx except the two `<Memo …/>` call sites, any Python |
| **G: Promotion review and routing** (after M merges) | `src/pharmagentics/tools/promotion.py`, `src/pharmagentics/tools/window.py` (`_PROMOTION`), `agents/brand-briefing/briefing_baseline/triage.py` (routing only), `tests/test_promotion_review.py`, `tests/test_comparison_windows.py` | memo.py (use its blocks) |
| **W: Writer paragraphs** (after M merges) | `agents/brand-briefing/briefing_agent/prompts/writer.md`, `revise.md`, `briefing_agent/write.py` (prose checks), `tests/test_followup_agent.py` | memo.py |

Shared touch points: `briefingApi.ts` is split by type (F: request and scope; R: section and chart). `App.tsx` belongs to F, except R may change the props at the two `<Memo/>` call sites.

## Scope reading (F)

Copy the Forecast pattern (`agents/forecast-explanation/forecast_agent/reader.py`, `src/pharmagentics/api/forecast.py::scope`):
- `POST /api/briefing/scope` takes `{question, brand_id}` and returns `{question, week_start, week_end, territory_id, comparison_weeks, promotion_review, notes, read_by: "model" | "rules"}`. Analysts only.
- `read_by="model"` only when `PHARMAGENTICS_AGENT_MODEL` (or the Forecast-style question model setting) is an Anthropic model and the key is present. The model fills one tool call, and code validates every field against the release: Mondays, `week_end >= week_start`, comparison 1 to 13 inside the release, known territory. Any failure falls back to `window.parse` and `read_by="rules"`.
- `BriefingQuery` gains `week_end: date | None` (a Monday, not before `week_start`). `normalize_question` writes `"Week of A"` for one week and `"Weeks of A to B"` for more, so `window.parse` keeps deciding the weeks from the text before the colon. The eval harness is unchanged and never calls the route.
- `comparison` stays the brief-007 `Comparison` model. The UI sends `{"kind": "previous", "weeks": N}` from the N field, default 4, and keeps last year and custom dates under "Other comparison".

## Checks each packet runs

Focused tests for its files, `uv run pytest -q tests/test_frontend_scope.py` for any frontend change, and, in `frontend/figma-make`, `npx tsc --noEmit -p tsconfig.app.json` for a TypeScript change. No full suite and no eval run: the integrator runs those once per pull request.
