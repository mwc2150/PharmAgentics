# brief-010 packet D-B: the brief definition, backend (2026-11-22)

Branch `feature/brief-010-definition` (worktree `pa-010-DB`). Tasks DB1 to DB4 in `specs/brief-010-target-analyses/tasks.md` are ticked.
Spec: brief-010 FR-000a, FR-000c, FR-000e (every field but the period takes a list; the first value is the primary).

## What was built

- `src/pharmagentics/tools/definition.py`: `Definition` (pydantic, frozen, `extra="forbid"`), the pre-selected values, validation,
  `from_comparison`, `coerce(definition, comparison)`, `words`, `prompt_words`, `changed_words`, `assumption_sentence`, `labels`.
- Both engines take `definition` (a `Definition`, its JSON, or `None` = the pre-selected values) through the same paths the old
  `comparison` keyword took: `pipeline.answer / triage / run_with_plan / scope`, `stages.resolve`, the MCP `open_run`, and the agent
  `answer / triage / run_with_plan / worker`. The old `comparison` keyword still works and maps into `definition.comparison`.
- `Period` (stages.py) carries `definition`, the extra comparison weeks (`extra_baselines`) and the reportable territory sets; every
  stage reads them. `Registry` has `labels` and `reg.under(**labels)` so a claim records the value it was made under.
- Packet D-B did not touch `frontend/` or `eval/`.

### What each field does

| Field | Effect (primary drives stories, cards, triage, directions; extras add labelled figures beside it, never a second set of stories) |
| :- | :- |
| `comparison` | Primary: the comparison weeks (empty list or `null` = the house rule, the previous four weeks). `pre_launch` = the four weeks before Metacora launched (launch date read from `raw.market_basket`, not hard-coded; refused with a reason for a period that starts before the launch, and for any extra comparison too). Each extra comparison adds: a §1 sentence and a KPI tile ("Change against the pre-launch weeks"), a territory-table column ("On the pre-launch weeks"), a clause in each story headline ("..., down X% since before Metacora launched") and in the story head, and the §2 detail lines. |
| `territories` | Primary `like_for_like` = today. `all_reportable` = national figures over the territories reportable in each period separately (says n of 8 for the period and n of 8 for the comparison). `projected` = the projected national as the headline change (a TRx figure; NBRx falls back to like for like, said in the Assumptions). Extra rules add a labelled national line and tile ("Change, all reportable territories"). |
| `measure` | `["trx"]` today. `["nbrx"]` = KPI strip, territory table, story figures, splits and national lines in NBRx, labelled "new patients (NBRx)" (the words "new patients" appear only for NBRx). `"both"` = `["trx","nbrx"]`. The first is primary; the other adds NBRx (or TRx) lines, tiles, table columns and a story sentence. Driver checks, the code screen and the projection stay TRx. |
| `grain` | `national` gates the national lines, the projected-national chart, the competitor story and card; `territory` the territory stories, table, changes and the screen; `plan` the access plan stories; `plan`, `channel`, `specialty` their splits. Pre-selected: all five. |
| `relative_to` | Primary: `other_territories` ("while the other territories were ..."), `national` ("while national was ..."), `none` (no clause). Extra values add their figure after the primary ("... and national was down X%"). |

Holiday weeks: the Assumptions block says "Holiday weeks are left out." when no calendar note applies (the old calendar sentence is kept
when it does), and `words()` always lists it. This is the one deliberate text change to the pre-selected brief.

## JSON shapes

`definition` in a request (`BriefingQuery.definition`; agent jobs carry it at `AgentJobRequest.query.definition`, no top-level field):

```json
{"first_week": "2026-08-24", "last_week": "2026-08-24",
 "comparison": [{"kind": "previous", "weeks": 4, "start": null, "end": null}, {"kind": "pre_launch", "weeks": null, "start": null, "end": null}],
 "territories": ["like_for_like"], "measure": ["trx"], "grain": ["national", "territory", "plan", "channel", "specialty"],
 "relative_to": ["other_territories"]}
```

- Every field is optional. A bare string or object is a one-item list; `measure: "both"` is `["trx","nbrx"]`; `comparison: null` or `[]` is the
  house comparison. Validation (422): no value twice in a list, at least one value (grain, territories, measure, relative_to), weeks are ISO
  Mondays, `last_week >= first_week`, `last_week` needs `first_week`, the weeks must equal the query's `week_start`/`week_end`.
- `comparison` (top level of the query) still carries the primary comparison alone. If the definition also has a comparison, the
  definition wins (no error); if the definition's is empty or null, the query's fills it.
- `kind` is `previous` (with `weeks`), `last_year`, `custom` (`start`, `end`) or the new `pre_launch` (no other field).

The stored brief and the returned brief (analyst view) carry the effective definition (the query's weeks and comparison filled in; the
release-wide Promotion review takes neither) and the same definition in plain sentences:

```json
{"...": "...", "comparison": {"kind": "previous", "weeks": 4, "start": null, "end": null},
 "definition": {"first_week": "2026-08-24", "last_week": "2026-08-24", "comparison": [{"kind": "previous", "weeks": 4, "start": null, "end": null}],
                "territories": ["like_for_like"], "measure": ["nbrx"], "grain": ["national", "territory"], "relative_to": ["national"]},
 "definition_words": ["Period: the week of 2026-08-24.", "Comparison: the previous four weeks.", "Holiday weeks are left out.",
                      "Territories counted: like for like, only territories reportable in both periods.", "Measure: new patients (NBRx).",
                      "Levels shown: national and territory.", "Territory changes are set against: the national change."]}
```

The leader view has `definition` and `definition_words` (allow-listed; never claims, labels, args or SQL). The Assumptions block of §6
(both views) adds one short sentence only when the definition is not the pre-selected one, inside the "Like for like" item so the block
stays at five items: "Brief definition, changed from the pre-selected values: measure new patients (NBRx); territory changes set against national." Extra comparisons add "also compared with ...". The form prints the full words itself.
A different definition is a different `brief_id`; the pre-selected one keeps today's ID. The triage plan carries `definition`, and its
`plan_id` changes with any non-pre-selected selection or extra comparison.

Scope route (`POST /api/briefing/scope`) response adds `definition` (the full model, period and comparison filled in; `null` for the Promotion review):

```json
{"week_start": "2026-08-24", "week_end": "2026-08-24", "territory_id": null, "comparison_weeks": 4, "promotion_review": false, "notes": ["..."],
 "read_by": "rules", "model": null,
 "definition": {"first_week": "2026-08-24", "last_week": "2026-08-24", "comparison": [{"kind": "previous", "weeks": 4, "start": null, "end": null}],
                "territories": ["like_for_like"], "measure": ["nbrx"], "grain": ["national", "territory", "plan", "channel", "specialty"],
                "relative_to": ["other_territories"]}}
```

The rules read the measure from the question ("new patients" or "NBRx" gives `["nbrx"]`; with "TRx" too, `["trx","nbrx"]`) and a
comparison with "the weeks before Metacora launched" (`pre_launch`; kept as the previous weeks, with a note, when the period starts
before the launch). The Haiku reader (`briefing_agent/reader.py`, prompt `scope_reader.md`) may also propose `measure`, `territories`,
`grain`, `relative_to` and `comparison: "pre_launch"`; code checks every value and an unusable one keeps its pre-selected value with a note, never an error.

Claim labels: every claim in `claims[]` (API `Claim.labels`, engine claim dicts) has `labels`; evidence items are unchanged.

```json
{"value": "4,105", "evidence_id": "e12",
 "labels": {"territories": "like_for_like", "measure": "trx", "relative_to": "other_territories", "period": "2026-08-24 to 2026-08-24",
            "comparison": "2026-07-27 to 2026-08-17", "comparison_kind": "default", "grain": "national"}}
```

`grain` is `national | territory | plan | channel | specialty`; `cut` (`plan:<id>`, `channel:<name>`, `specialty:<name>`) is present only on a
claim that is one cut of a split or one plan. A claim made for an extra value overrides that field (`measure: "nbrx"`,
`comparison_kind: "pre_launch"` with `comparison: "2026-02-02 to 2026-02-23"`, `territories: "all_reportable"`, `relative_to: "national"`).
`comparison_kind` is `default | previous | last_year | custom | pre_launch`.

## Decisions and deviations to know

- Labels are claim-level metadata, not evidence params, so evidence (id, tool, params, query, result) and claim `value`/`evidence_id` are identical
  to today's for the pre-selected definition. Claims gain a `labels` key; the eval envelope's `Claim` ignores it.
- The key test compares today's output (a snapshot, `tests/fixtures/brief010_db_baseline.json`, nine questions: golden P1-Q1, P1-Q4, P2-Q2,
  P2-Q3, P3-Q1, P3-Q4, P4-Q4, WIN-1 and a six-week comparison) with `definition=None`, the explicit pre-selected definition and its JSON:
  identical answer, claims and evidence. The fixture's answers were refreshed once, deliberately, for the holiday sentence (verified: the
  answer minus that sentence equals the old answer, claims and evidence identical).
- The agent engine passes the definition to the MCP session (`open_run`), to the Manager triage prompt and the Writer prompt in words
  (`{definition}` placeholder; no period or number words), and to each story's Magentic task. No model run was made (shared machine).
- The Promotion review (release-wide) ignores the definition.
- Extra values are computed at the primary of the other fields (an extra comparison under the primary territories rule and measure, and so on), not as a cross product.

## Tests (focused only; no full suite, no eval run)

See the results block at the end of this file.

## Open issues

- The agent path was not run against a model; its scripted parts (open_run, plan, prompts) are covered, the Haiku run belongs to the integration step.
- The leadership KPI strip can now hold more than four tiles when extras are chosen; the form should wrap them.
- `Definition.comparison` is a list even for the pre-selected value (`[]`); the form sends `null`, which is read as `[]`.

## Results (focused runs only; no full suite, no eval run, no model)

- `tests/test_brief_definition.py`: 41 tests (the model and lists, pre-launch weeks and refusal, words, the pre-selected definition against the
  nine-question snapshot three ways, labels, nbrx, `measure: ["trx","nbrx"]` equals `"both"`, first measure primary, grain, relative_to with an
  extra value, all_reportable, projected, an extra territories rule, two comparisons (previous four + pre_launch) with the same stories, the
  refusal for a period before launch, MCP session, triage plan, API round trip with null comparison, top-level comparison plus definition,
  leader view in words, scope proposal, a model's proposed selectors) all pass.
- With the existing tests of the touched files (`test_comparison_windows`, `test_briefing_api`, `test_briefing_scope`, `test_triage`,
  `test_mcp_server`, `test_agent_build3`, `test_run_events`, `test_rbac`, `test_tools`, `test_memo`, `test_promotion_review`, `test_followup`,
  `test_projection`, `test_charts`, `test_jobs`, `test_agent_host`): 302 passed, 4 failed in one 56-minute run, and the 4 are fixed and re-run
  green: three `test_briefing_api` tests mocked `answer` with a fixed signature (the service now passes the old `comparison` keyword when a
  request has no `definition`, so that call is unchanged; 35 pass), and `test_triage::test_answer_unchanged` compares claims to a frozen
  fixture (its `comparable()` now ignores the claim `labels` and the one holiday sentence).
