# Tasks: core-011 Eval Revamp

Packets and file ownership are in `plan.md`.

### Packet A: schema and scorers (FR-001 to FR-006)
- [x] A1 `Fact` gains `role`, `tolerance`, `reviewed`; new `Finding`; `Case.findings`; `expectations()` gains `key_facts` and `findings`. Existing YAML loads unchanged.
- [x] A2 `key_fact_recall` with tolerance; not scored without must facts; pooled run metric.
- [x] A3 `finding_recall` and `false_drivers` over `sections[*].card`; not scored without cards or findings.
- [x] A4 `brief_words`.
- [x] A5 Not-scored cases stay out of the run mean (check MLflow's aggregation; log the mean over scored cases if needed).
- [x] A6 Tests for each scorer, including the US1 and US2 acceptance cases; `golden_number_recall` unchanged.

### Packet B: insights (FR-008)
- [x] B1 `eval/harness/insights.py`: read-only stores, parent and child runs, per-case matrix by scorer.
- [x] B2 Stuck, fallen, engine comparison, rerun spread, golden-version breaks; Markdown and JSON.
- [x] B3 `python -m eval insights` subcommand; tests on a small SQLite fixture built in the test.

### Packet C: Evaluation page (FR-009), after brief-008 merges
- [x] C1 `cases` block in the telemetry export; API passes it to analysts and the tester only.
- [x] C2 Per-case table on the Evaluation page; `tsc`, `vite build`, `tests/test_frontend_scope.py`.

### Packet D: golden facts and findings (FR-007), after A's schema commit
- [x] D1 For every Briefing case whose reference answer states numbers: a fact with SQL for each number it can recompute from the agent-visible data; `role` must for the numbers the story hinges on, context for the rest; `reviewed: false`.
- [x] D2 Where the reference answer says "about X" or a rounded range and the SQL gives the exact value, write the exact value in the answer.
- [x] D3 `findings` for each Briefing case from its own given, then and reference answer; `reviewed: false`.
- [x] D4 CHANGELOG entry; `eval check` and `eval/tests/test_golden_integrity.py` pass.
- [ ] D5 Michael reviews and flips `reviewed` (person task).

### Packet E: story card fields, after brief-008 merges
- [x] E1 Cards gain `territory`, `direction`, `drivers_supported`, `drivers_ruled_out` from tool verdicts, on both engines; answer text unchanged.

## Integration (Opus)
- [ ] I1 Merge A, B, D; full suite; one scripted run; gate (unchanged gated checks); `eval insights` over the brief-008 runs.
- [ ] I2 After brief-008 merges: C and E; one scripted and one Haiku run; two report-only runs, then propose `GATED` changes to Michael (FR-006).
- [ ] I3 `/code-review`; pull request; `specs/README.md`, `eval/README.md` and `PROJECT_STATE.md` updated.
