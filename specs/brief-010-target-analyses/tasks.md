# Tasks: brief-010 The Analyses the Targets Need

Base: `main` plus `feature/core-011-exact-values` plus `feature/brief-009-timeline`. Packets D-B, D-U and G first, side by side; then N and R side by side; then P, then S. Built by Sonnet in their own worktrees; Opus integrates.

## Packet D-B: the brief definition, backend (FR-000a, FR-000c)
- [ ] DB1 `tools/definition.py`: the `Definition` model, its pre-selected values, validation, and words for the Assumptions block.
- [ ] DB2 Both engines take `definition` (None means the pre-selected values) and honour every field; claims record the fields plus grain and cut.
- [ ] DB3 API: brief and job requests carry `definition`; the stored brief keeps it; the scope reader proposes it; the Assumptions block prints it.
- [ ] DB4 Tests: pre-selected definition gives today's brief unchanged (answer, claims, evidence); each field changes what it should.

## Packet D-U: the brief definition, form (FR-000b)
- [ ] DU1 Six selectors at the start of the Briefing form, pre-selected, editable; the scope reader's proposal fills them; the request sends `definition`.
- [ ] DU2 The Assumptions block shows the definition in both views; tsc, build, frontend-scope test.

## Packet G: golden definitions and the review (FR-000d; grill 2026-11-22)
- [x] G1 `Case.definition` (explicit, all fields) replaces `comparison` (the loader maps old files); the harness passes it to systems; findings take an optional `measure`.
- [x] G2 Every Briefing case states its definition; P2-Q3, P2-Q4 and P1-Q5 changes restated like-for-like from SQL with the reference prose; plan cuts on P1-Q4, P2-Q2, P2-Q4, P4-Q4; `needs` tags; must facts and findings `reviewed: true`; CHANGELOG.
- [x] G3 `eval check` passes; eval tests.

## Packet P: plan cuts (FR-001, FR-002, FR-007, FR-008)
- [ ] P1 Cut screen in `splits.py`: per plan in a story territory, TRx (or NBRx) a week before and after on the comparison weeks and the percent change, as claim tokens; flags a plan against its territory or holding the supported access driver.
- [ ] P2 `memo.cut_card` and the §3 order (territory card, then its cut cards); at most two cut cards a brief; the budget shrink of territory cards (FR-008).
- [ ] P3 Triage passes cut cards as candidate stories; the agent's Manager prompt lists them (`briefing_agent/plan.py`).
- [ ] P4 Tests; scripted run and gate; targets P1-Q4, P2-Q2, P2-Q4, P4-Q4 rise; Haiku run and gate.

## Packet S: segment and channel percent (FR-003)
- [ ] S1 Percent movers by channel and specialty (at most two a story, small cells named, not quoted).
- [ ] S2 The Promotion review states them for each lapsed territory.
- [ ] S3 Tests; scripted run and gate; P4-Q2 rises.

## Packet R: restatement detail (FR-004, FR-005)
- [ ] R1 Duplicate overstatement (naive, deduplicated, overstatement) in §4 when the gate withholds a territory.
- [ ] R2 Signed-off and restated figures and the change, from a governed view over `raw.restatement_log`; a restatement card with data supported.
- [ ] R3 Tests; scripted run and gate; P1-Q1, P2-Q5, P3-Q6 rise.

## Packet N: national card (FR-006)
- [ ] N1 `competitor_card` becomes a national card: territory NATIONAL, direction from the share change (house flat band), competitor supported from the check.
- [ ] N2 Tests; scripted run and gate; P1-Q5, P3-Q4 findings rise.

## Integration (Opus)
- [ ] I1 After the last packet: full suite, scripted gate, SC-001 (targets met, `over_word_budget` 0).
- [ ] I2 Haiku agent run and gate (SC-002).
- [ ] I3 Real-app look at a cut card and the national card in both views; print fits two A4 pages.
- [ ] I4 `/code-review`, PR, `PROJECT_STATE.md`, handoff.
