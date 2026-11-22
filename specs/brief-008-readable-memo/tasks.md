# Tasks: brief-008 A Readable Memo

Work packets for agents working in parallel (`plan.md` has the file contract and the block schema). Wave 1 runs F, M and R at once; G and W follow when M merges. Each packet works in its own worktree and branch, commits by path, and writes a short handoff in `conversations/` before it stops. The integrator (Opus) reviews, merges the packets, runs the full suite and the scripted gate, and opens the pull request.

## Wave 1

### Packet F: form, scope and account menu (US3, US5; FR-007, FR-008, FR-009, FR-012)
- [x] F1 Account menu: remove the lane and role list for every account; the trigger shows `me.name` (and "Test view ·" for the tester). Keep the tester's Analyst / Leadership switch, the suggestion link, the questionnaire and sign-out.
- [x] F2 `BriefingQuery.week_end` (optional Monday, not before `week_start`) and `normalize_question` writing "Week of A" or "Weeks of A to B". The scripted and agent paths, the triage plan id and the job round trip carry the period unchanged.
- [x] F3 New briefing form: First week and Last week selects (the Forecast pattern), "Compare with the previous N weeks" (number, 1 to 13, default 4), and "Other comparison" holding brief-007's last-year and custom choices. Code validates the period and the comparison before any request; errors show beside the field.
- [x] F4 `POST /api/briefing/scope` and `briefing_agent/reader.py`: the model proposes the scope through one tool call; code validates it; any failure falls back to `window.parse` with `read_by="rules"`. Analysts only. No model call without an Anthropic model and key. Unit tests stub the model.
- [x] F5 UI: a "Read my question" action fills the form from the proposed scope, and the analyst confirms with the usual Build button. The scope card shows `read_by` in plain words ("Read by Haiku" or "Read by rules").
- [x] F6 Tests: `tests/test_briefing_scope.py` (validation, fallback, analysts only, no model call in evals), updated `tests/test_briefing_api.py`, `tests/test_frontend_scope.py` (new file in the allow-list), `npx tsc --noEmit -p tsconfig.app.json`.

### Packet M: memo blocks, paragraphs and the leader cut (US1, US2; FR-001 to FR-006, FR-011, FR-013)
- [x] M1 Blocks: build `kpis` on §1, `territory_table` on §2 and `card` on each story section, in `memo.py`, from the claims the brief already registers (add a claim only where a tile needs one). Both the scripted pipeline and the MCP server (`brief_sections`, `memo_close`) produce them, so `test_sections_match_the_scripted_brief` still holds. `render_sections` fills them and records citations.
- [x] M2 Paragraphs: rewrite the section templates as short paragraphs (ASD-STE100: short sentences). The level list and the change list become the `territory_table` and one sentence; story lines become a paragraph. No list longer than five items; no raw IDs or enum names (map plan, specialty and channel IDs to readable names); correct plurals; no signed decimals ("down 121 TRx a week").
- [x] M3 Folding: move splits, feed figures, the method, the glossary and "considered and dropped" into `detail`. `compose` writes `text` then `detail` into the answer, so the scored answer keeps every claim.
- [x] M4 Multi-week periods: no single-week change in any line or table column (FR-011).
- [x] M5 Leader cut (`api/views.py`): allow-list `kpis`, `territory_table` and `card`; never `detail` or citations; add the short §4 and the Assumptions (from §6). Update `executive_summary` the same way for the text cut.
- [x] M6 Tests: update the exact-string tests in `test_memo.py`, `test_charts.py`, `test_agent_build3.py` and `test_rbac.py` to the new wording, keeping what each test proves. Add tests for the block schema, for every block number appearing in the answer, and for no raw ID in any section. Regenerate `tests/fixtures/scripted_answers.json` and check that its diff changes wording only, with the same claim values.

### Packet R: rendering the blocks (US1, US2; FR-003)
- [x] R1 Types: `MemoSection` gains `kpis`, `territory_table`, `card`, `detail` and their citations (`plan.md` schema).
- [x] R2 Memo.tsx: a KPI strip (tiles with value, label, detail and direction), a territory table (basis shown as a quiet label; withheld rows say "withheld"), story cards (headline, confidence badge, drivers checked, prose, chart), and `detail` folded under "Show detail" for analysts. Leaders get the same components without citations. A section with none of the new fields renders as today.
- [x] R3 Paragraph styling: body text in short paragraphs at a readable measure; tables in the app's sans face with tabular numbers.
- [x] R4 Print: print rules so the analyst view (folded) and the leader view fit two A4 pages for the anchor briefs; folded details stay folded in print.
- [x] R5 Checks: `npx tsc --noEmit -p tsconfig.app.json` and `npx vite build --config vite.config.standalone.ts` pass. Add no new frontend file (the allow-list in `tests/test_frontend_scope.py` is F's). The integrator checks the real app.

## Wave 2 (after M merges)

### Packet G: Promotion review and routing (US4; FR-010)
- [x] G1 P4-Q6 ("Where should the next dollar go?") gets its own Bottom line: no channel ranking or dollar price (no spend data; calls and impressions moved together), the size of the lapses in TRx a week, and coverage backfill with sales operations.
- [x] G2 P4-Q5 ("How confident is the estimate…") is no longer routed to the Promotion review by a stray term; it gets confidence and the next-read timing.
- [x] G3 The review uses the blocks (KPI strip: territories with a lapse, longest lapse, push threshold; the push figures as a `territory_table`), paragraphs, readable names, correct plurals, and an Assumptions block without "no earlier weeks".

### Packet W: the Writer's paragraphs (FR-006)
- [x] W1 The agent's Writer writes each section's paragraph around the code's claim tokens; the token check and `revise` keep their rules; the code template is the fallback.

## Integration (Opus)
- [x] I1 Merge F, M and R; full suite; scripted run and gate against `c65d888fe3e444adab380e509f497a88`; golden-number recall per case.
- [x] I2 Real-app check: the leader and analyst views of the five anchor briefs, printed to A4.
- [x] I3 `/code-review` at medium on the diff; fix; push; open the pull request.
- [ ] I4 After G and W: the Haiku agent run and gate against the agent baseline; update `PROJECT_STATE.md`.
