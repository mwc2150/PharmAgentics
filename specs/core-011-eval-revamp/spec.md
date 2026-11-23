# Feature Specification: core-011 Eval Revamp (key facts, findings, run insights)

**Feature branch**: `feature/core-011-eval-revamp`
**Created**: 2026-11-22
**Status**: Draft
**Owners**: Michael (eval pack author); Meghna reviews Briefing golden edits. The Forecast lane's cases and scorers are untouched (Alvin and Sienna own them).
**Input**: the 2026-11-22 grill after the brief-008 scripted run. `golden_number_recall` extracts numbers from the October reference prose. On run `695fe76e` it is 0.682 as a per-case mean but 0.593 over all 167 golden numbers, because four cases with no golden numbers score 1.0. Of the 68 misses, about 12 are approximate golden wording ("about 120 to 200", so P4-Q6 stays at 0 even when the brief states the exact 116 to 177), about 45 are analyses the system does not do, and the rest are definitional. The score rewards repeating hand-written approximations, not finding the right story in a short brief.

## User Scenarios & Testing

### User Story 1 - The score says whether the brief stated the facts that matter (Priority: P1)

Michael reads one completeness number per run and trusts it: it counts only the facts a case says a brief must state, each recomputed by SQL, matched at its stated precision or its stated tolerance, and cases with nothing to check are left out rather than scored 1.0.

**Acceptance**:
1. **Given** a case with three must-state facts and a brief that states two, **then** `key_fact_recall` is 0.667 and the rationale names the missing fact by id.
2. **Given** a case with no must-state facts, **then** the case is not scored and does not move the run mean.
3. **Given** a fact with value 120 and tolerance 0.05 and a brief that states 116, **then** the fact counts as stated; with no tolerance it does not.

### User Story 2 - The score says whether the brief found the right story (Priority: P1)

For each case the golden set names the findings a first-pass analyst should reach (territory, direction, drivers supported, drivers ruled out, withheld cuts). The run reports how many the brief reached, and any driver it supported that the case does not expect.

**Acceptance**:
1. **Given** a case expecting Southeast down with promotion supported and access ruled out, and a brief whose Southeast story card says down, promotion supported, access ruled out, **then** `finding_recall` is 1.0.
2. **Given** the same brief also supports supply, **then** `false_drivers` reports 1 for the case.
3. **Given** a system whose envelope has no story cards (low-code, naive control), **then** the case is not scored.

### User Story 3 - Michael sees what changed across runs (Priority: P2)

`python -m eval insights` reads the local MLflow stores read-only and writes a per-case history: cases stuck at 0, cases that fell since the previous run of the same system, scripted against agent on the same case, and the spread across reruns. Runs scored against a different golden version are marked as not comparable.

### User Story 4 - The Evaluation page shows the per-case view (Priority: P3)

Analysts and the tester see the per-case table on the Evaluation page (latest run per system, each scorer, stuck and fallen cases marked). Leaders keep the totals only.

### User Story 5 - The golden facts are exact and reviewed (Priority: P1)

Every Briefing case that states numbers has facts with SQL; each fact is tagged must-state or context; "about X" in a reference answer becomes the exact value its SQL gives. Agent-drafted facts and findings are marked unreviewed until Michael reviews them.

## Requirements

- **FR-001**: A fact MUST carry `role` (`must` or `context`, default `context`), optional `tolerance` (a relative fraction, for values the source states only roughly) and `reviewed` (default true; agent drafts write false).
- **FR-002**: A case MAY carry `findings`: each with `id`, `territory`, `direction` (`up`, `down`, `flat`), `drivers_supported`, `drivers_ruled_out`, `withheld` (bool) and `reviewed`.
- **FR-003**: `key_fact_recall` MUST score the share of a case's must-state facts that the answer states, using the same number matching as today plus the fact's tolerance; a case with no must-state facts is not scored. The run also logs the pooled share over all must-state facts.
- **FR-004**: `finding_recall` MUST score expected findings against the story cards in the envelope's `sections` (black-box: the envelope only); `false_drivers` counts supported drivers no finding expects. A case with no expected findings, or an envelope with no story cards, is not scored.
- **FR-005**: `brief_words` (report-only) MUST count the words of the sections a reader sees unfolded (section text, cards, table cells; not `detail`), as the brevity guard for SC-002 of brief-008.
- **FR-006**: The new scores are report-only for the first two runs after the golden facts are reviewed; then `key_fact_recall` and `finding_recall` join `GATED` (code checks, Briefing B-VII). `golden_number_recall` stays report-only until facts cover every Briefing case that states numbers, then retires.
- **FR-007**: A golden edit MUST NOT move a value toward a system's output. Facts are drafted from SQL over the agent-visible data and the case's own text only; every edit is logged in `eval/golden/CHANGELOG.md`; `eval check` and `eval/tests/test_golden_integrity.py` MUST pass.
- **FR-008**: `python -m eval insights` MUST open each store read-only, never write to MLflow, and write Markdown plus JSON (the JSON is the input of US4).
- **FR-009**: The Evaluation page per-case table MUST hold scores, case ids and stories only: no reference answers, facts or SQL.
- **FR-010**: Forecast cases, FE scorers and `eval drivers` MUST NOT change.
- **FR-011** (2026-11-22, deterministic first): every scorer MUST have a kind in `scorers.KIND`: `code` (what code guarantees: numbers, claims, links, sections; scored on the scripted engine as regression tests), `agent` (what the agent infers: findings, drivers, must-say, scope, revisions, brevity, judges), `safety` (gated on both engines) or `ops`. `eval insights` and the Evaluation page group scores by kind.
- **FR-012**: `scope_match` (report-only, agent) MUST compare the scope the agent proposes (`trajectory.scope_proposal`) with the case's expected scope: an explicit `scope`, else one derived from the question prefix and the case's `comparison`. Not scored without a proposal.
- **FR-013**: For agent systems, "numbers lost by the agent" MUST be the scripted engine's `key_fact_recall` minus the agent's on the same case and golden version (insights and the Evaluation page).
- **FR-014**: Number matching MUST respect units: a percent matches only a percent, a count only a count; a golden number repeated in a reference answer counts once. A key fact's unit comes from its reference answer, else from an `_pct` id, else it is unknown.
- **FR-015**: Golden definitions follow the case text and house conventions (packet G): a window the text names is encoded in the case's `comparison`; otherwise the golden figure is restated under the four weeks before, from SQL. When two definitions stay defensible, the number is `context`.
- **FR-016**: A number MUST be scored against the fact's exact value, from the fact's own SQL, rounded half up to the precision the answer prints it at (the rule the brief's formatter follows, brief-008 FR-016); the golden file's written figure is display text and the fallback when the SQL cannot run. A golden prose number is tied to a fact when it is that fact's exact value or written figure at its own precision. So "22%" states a backorder rate of 22.45 written as "22.5", and a brief that rounds the true value once is never failed by a figure the golden file rounded twice. Applies to `key_fact_recall`, `golden_number_recall` and `numbers_match_golden`.
- **FR-017** (2026-11-22 night grill): Findings and story cards MAY carry a `cut` below the territory: `plan:<plan id>`, `channel:<channel>` or `segment:<segment>`. A finding with a cut is met only by a card with the same territory and cut; a finding without one only by a whole-territory card (no cut), as before. A cut card stands beside its territory card; it is never dropped for length.
- **FR-018**: Golden facts and findings MAY carry `needs`, the capability a system must have to state them: `plan_cut`, `segment_pct`, `restatement` or `national_card`. `eval insights` and the Evaluation page split misses into "needs a capability the system lacks" and "missed".
- **FR-019**: Targets live in code (`scorers.TARGETS`: pooled key-fact recall 0.85, finding recall 0.90). Every Briefing run logs `key_fact_recall_pooled`, `finding_recall_pooled` (points over all cases), `key_fact_target_met`, `finding_target_met` (1 or 0) and `over_word_budget` (cases over budget), all report-only.
- **FR-020**: The word budget is measured, one number per view (`scorers.WORD_BUDGET`: analyst, leader): the largest `brief_words` among the anchor briefs that printed on two A4 pages (brief-008 I2), as measured (a brief no longer than the longest one known to fit). `brief_words` reports the leader view's count beside the analyst's.
- **FR-021**: When `key_fact_recall` and `finding_recall` join `GATED` (FR-006), the gate also fails a run with any case over the word budget, so the system cannot pad a brief to score.

## Success Criteria

- **SC-001**: After the golden review, every Briefing case that states numbers has at least one must-state fact, and no scored case gets 1.0 for having nothing to check.
- **SC-002**: On the scripted engine, key-fact recall ≥ 0.85 and finding recall ≥ 0.90 (targets, not gates, until FR-006), with `brief_words` inside the two-page budget.
- **SC-003**: `eval insights` lists every case stuck at 0 across the last three scripted runs, and the brief-008 runs' per-case changes match the hand comparison of 2026-11-22.
- **SC-004**: The full suite and the scripted gate pass; Forecast scores are unchanged.

## Out of scope

The missing analyses that explain most remaining misses (duplicate-key overstatement, restatement deltas, plan-level TRx, holiday weeks against the year before, share trajectory, splits as percentages) belong to a Briefing spec, brief-010, chosen later. LLM judges stay report-only (Evaluation Pack open item 2).
