# brief-010 packet D-U: the brief definition, form (2026-11-22)

Branch `feature/brief-010-form`. Frontend only (FR-000b). Coded against the plan.md contract; packet D-B supplies the backend fields.

## Built
- `frontend/figma-make/src/BriefDefinition.tsx` (new): `DefinitionPicker` (Territories counted, Measure, Relative to as selects; Grain as five checkboxes, at least one required), `DEFAULT_CHOICES` (like_for_like, trx, all five grains, other_territories), `proposedChoices` (checks a reader's proposal field by field), `definitionLines` / `DefinitionWords` (a stored definition in words).
- `App.tsx` Briefing form: a "What the brief counts" fieldset now opens the form with all six selectors in order: Period (existing `PeriodPicker`), Comparison (existing `ComparisonPicker`, unchanged: previous N weeks, last year, named weeks), then the four new ones; the question box and "Read my question" come after. State `choices` and `proposed`; `choices` reset on brand change. The request `definition` is `{...choices, first_week, last_week, comparison}` (weeks and comparison null for the Promotion review). It is sent on triage, brief and agent-job requests as `query.definition` (the job request carries a `BriefingQuery`). Generate is disabled when no grain is ticked.
- `BriefingScope.tsx`: `scopeToForm` reads `scope.definition` (first_week, last_week, comparison, territories, measure, grain, relative_to), prefers its weeks and comparison over the older `week_start`, `week_end`, `comparison_weeks`, and returns `choices` and `proposed`. Proposed fields show a "Proposed, check it" mark until the analyst edits that field; nothing is locked. An invalid proposal is refused with a reason, as before.
- `agent/briefingApi.ts`: types `BriefDefinition`, `TerritoriesCounted`, `MeasureChoice`, `GrainLevel`, `RelativeTo`; `definition?` on `BriefingQuery`, `BriefingScope` (Partial), `BriefingResult` and `LeadershipBrief`.
- `Memo.tsx`: optional `definition` and `labelWeek` props; `DefinitionWords` renders under §6 (the Assumptions block; under the last section if there is no §6), in both views. No definition, nothing extra. The leader type carries only the definition fields.
- `tests/test_frontend_scope.py`: allow-list gains `BriefDefinition.tsx`; new test for form order, field names, pre-selected values and the Memo wiring.

## Follow-up: Pre-launch weeks (integrator, Michael's decision)
The Comparison selector has a fourth choice, "Pre-launch weeks" (under "Other comparison"), sent as `comparison: {"kind": "pre_launch"}` with no weeks, start or end. `Comparison` in `agent/briefingApi.ts` gains the kind; `scopeToForm` accepts it from the reader; the Assumptions words say "the four weeks before Metacora launched". `comparisonError` allows it without checks (the server owns the launch date). tsc clean, standalone build ok, `tests/test_frontend_scope.py` 4 passed.

## Follow-up: every selector takes one or more values (FR-000e; spec commit 6285be7)
- Wire format: `definition` carries lists. `comparison: Comparison[] | null` (null when the analyst has not chosen: the server's default, as before), `territories`, `measure` (`("trx"|"nbrx")[]`, the old "Both" is `["trx","nbrx"]`), `grain`, `relative_to`. The first value is the primary. The top-level `comparison` field of the query still carries the primary comparison alone, for the older fields.
- Form: `BriefDefinition.tsx` `MultiChoice` (checkboxes, an ordered list when more than one value is chosen, a "primary" tag and a "Make primary" button on the others) for Territories counted, Measure, Relative to and Grain; each needs at least one value (error text, Generate disabled). `ComparisonPicker.tsx` is now a list: each row picks previous N weeks, same weeks last year, Pre-launch weeks or custom weeks, with Make primary and Remove; "Add another comparison"; an empty list shows the default row ("The previous [Default] weeks"). `comparisonsError` also refuses the same comparison twice. `App.tsx` state is `comparisons: Comparison[]` (`[]` is the default).
- Scope reader: each definition field may be one value or a list (`ProposedDefinition`, `OneOrMany`); the old measure "both" is read as TRx then NBRx; `proposedComparisons` and `proposedChoices` validate each value. A lone previous-weeks comparison equal to the default rule stays the default.
- Assumptions words: every chosen value is listed, primary first and marked "(primary)" when there are several; a stored single value (older brief) reads as a list of one.
- Checks: tsc clean, standalone build ok, `tests/test_frontend_scope.py` 5 passed (assertions updated, one test added).
- Open: an empty comparison list is sent as `comparison: null` (not `[]`); D-B should read null as the default.

## Fields used
Request: `definition.{first_week,last_week,comparison,territories,measure,grain,relative_to}` inside the briefing query. Scope response: `definition` (any subset). Brief response (analyst and leadership): `definition`.

## Checks
- `npx tsc --noEmit -p tsconfig.app.json`: clean.
- `npx vite build -c vite.config.standalone.ts`: built (chunk-size warning only, as before).
- `uv run pytest -q tests/test_frontend_scope.py`: 4 passed. No full suite, no eval run.
- Not looked at in a running app (needs D-B's backend); Integration I3 covers the real-app look.

## Open issues
- Where `definition` sits on the agent job request: I put it in `query.definition` (the job's `query` is a `BriefingQuery`). plan.md says "AgentJobRequest.definition"; D-B must accept it on `BriefingQuery` (schemas use `extra="forbid"`) or tell me to move it.
- D-B also prints the definition in the Assumptions text; the structured block repeats it in the Assumptions area. Drop one when integrating if it reads as a duplicate.
- The comparison default row shows the placeholder "Default" with the note about 4 weeks (an empty list means the house rule); it is not literally pre-filled with 4.
- The "Proposed" mark covers the four new selectors only; period and comparison fill as before, with the reader's existing "Check the form" note.
