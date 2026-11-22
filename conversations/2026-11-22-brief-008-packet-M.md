# Handoff: brief-008 packet M (memo blocks, paragraphs, leader cut)

Branch `feature/brief-008-memo`, worktree `C:\Users\micha\test_agent_v1\pa-008-M`. Not pushed. No eval run.

## What changed

- **Blocks** (schema in `specs/brief-008-readable-memo/plan.md`): `kpis` on §1, `territory_table` on §2, `card` on each story section, `detail` on any section. Built in `tools/memo.py` (`kpis`, `territory_table`, `numbers`, `story_card`, `competitor_card`, `bottom_detail`, `story_detail`), called by both engines. `compose` writes text, then detail, into the answer; `render_sections` fills block tokens and emits `value_citation` (span list), `cell_citations` (one span list per cell), `headline_citations`, `detail_citations`. Tile detail and table note are filled without citations. Sections without blocks render as before.
- **Claims by name.** `stages.kpis`, `territory_change` and `competitor_status` take an optional `facts` dict that receives the claims they register, so the table, tiles and cards reuse a claim instead of making a second one. `memo.bottom_line` fills a `facts` dict for the KPI strip and adds one claim, the share before launch (`35.4%`, a value the competitor story already states).
- **Paragraphs.** §2 text is the scope line and short sentences (like-for-like change, week over week for one week, largest fall and rise); the per-territory lines move to `detail` (sentences, no dashes). §4 text is the first paragraph (data health, withheld focus territory, calendar note); the gate bullets, feed figures and method lines are detail. §6 text is the data version plus the Assumptions block (at most five items; driver timing is one item); the method and glossary are detail. "Considered and dropped" is §3's detail. Splits are each story's detail: readable names (`Commercial plan one`, `primary care`), rounded TRx a week with a direction word, at most five cuts a split, small cells marked.
- **Plurals and IDs.** "1 territory-weeks", "1 territories" and the like are fixed in `stages` and `charts`. Data-health bullets are capped at five. Plan IDs become words with no digit (`plan one`), since a digit outside a token fails the number check.
- **FR-011.** A multi-week brief has no "week before" change in text, table, detail or the `stages.kpis` tool output; the table column is dropped.
- **Agent path.** `brief_sections` returns `numbers` and `limits` as lists, plus `territory_table` and `details` ({"2", "4"}). `memo_close` returns `kpis`, `details` ({"1"}), `story_cards`, `story_details` (keyed by territory, or `competitor`). `story_section` no longer prints splits; it stores them as the story's detail. `write.assemble` merges all of it, tolerating a payload without any of these keys.
- **Leader cut** (`api/views.py`): allow-lists `kpis`, `territory_table`, `card` (values and labels only), adds §4 as its first paragraph (no chart), and the Assumptions items from §6 (title "Assumptions"). Never `detail` or citations. `executive_summary(answer, sections=None)` is cut from the sections when given (the flat-text path stays for old briefs). `leadership()` and `feedback.py` pass the sections.

## Files outside packet M's table that I had to touch

- `src/pharmagentics/tools/splits.py`: new `readable()` and `readable_lines()`; the CTE is now `_cuts_sql` (shared by the old `split_change` tool, which is unchanged in output). Packet G can call `splits.readable()` and `splits.readable_lines()` for the Promotion review.
- `src/pharmagentics/tools/followup.py`: `_labelled` and the "by plan/specialty/channel" restatement read `text` plus `detail`, because the levels and splits are folded now (`tests/test_followup.py` needs it).
- `src/pharmagentics/api/feedback.py`: one line, passes sections to `executive_summary`.

## Tests

`uv run pytest -q tests/test_memo.py` (40 passed). `uv run pytest -q tests/test_charts.py tests/test_agent_build3.py tests/test_rbac.py tests/test_triage.py tests/test_promotion_review.py tests/test_followup.py tests/test_comparison_windows.py` (80 passed). Not run: the full suite, any eval.

New tests: block schema (one-week and multi-week), every block token appears in the scored answer, no raw ID / signed decimal / "1 weeks" / list over five in any section of six anchor briefs, readable folded splits, old sections render unchanged, and the agent's assembled blocks equal the scripted brief's (`test_sections_match_the_scripted_brief`). Updated for the new wording: `test_memo.py`, `test_charts.py`, `test_agent_build3.py`, `test_rbac.py`. `test_charts.py` and `test_rbac.py` leak checks still prove no query, table data, citation or detail reaches leaders; `territory_table` does not match the `"table"` literal, so no leak string changed.

`tests/fixtures/scripted_answers.json` was regenerated. Against the old fixture, claim values differ only by (a) split values, now rounded and absolute (`-210.00` is `210`) and capped at five cuts a split, and (b) the share before launch in briefs where Metacora had launched. Every other claim, and `abstained`, is identical.

## Left and risks

- Golden-number recall (report-only) will move: the split claims are rounded and capped at five, so golden numbers like `-48.35` no longer appear. Check SC-003 after the integrator's scripted run; if recall falls below 0.668, the cap or the rounding is the place to look.
- Next checks can still exceed five lines (four stories, Metacora and a withheld-cut line); not merged further.
- The Promotion review (packet G) still prints raw plan IDs and "1 weeks"; its appendix now has the method folded like every brief.
- Memo.tsx (packet R) must read `detail` for the §2 per-territory lines; until it does, the UI shows only the table.
- The agent's Writer prompts do not mention that splits moved out of the story section (packet W).
