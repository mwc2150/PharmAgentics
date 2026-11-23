# Feature Specification: A Readable Memo

**Spec ID**: `brief-008-readable-memo` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `feature/brief-008-readable-memo`
**Created**: 2026-11-22 | **Updated**: 2026-11-22
**Status**: Specified; build next (work packets in `tasks.md`, file contract in `plan.md`)
**Input**: Mentor feedback (Dr. Admasu, 2026-11-21): "Please add a chart or table or some KPIs in the briefing for leadership briefing since it's a wall of text right now." Grill with Michael, 2026-11-22. The state of `main` after brief-007 (`PROJECT_STATE.md`, 2026-11-22). Briefing constitution B-II, B-III, B-VI, B-VII.

## Why

The memo's structure is right. Both engines build the same six sections in code (brief-003 v3): Bottom line, The numbers, What changed and why, What the data can't tell us, Next checks, Appendix. But every section reaches the UI as lines of text, and `Memo.tsx` prints each section as one serif text block. The territory "table", the KPIs and the per-territory changes are prose lines. Each brief-007 slice added numbers as more lines, so the leader cut grew to 37 lines for a routine week, 60 for the Southeast brief and 67 for the Promotion review. Its only visual element is one line chart.

brief-007 also left gaps on `main`:
- "Where should the next dollar go?" (P4-Q6) gets the same text as P4-Q1 (recall 0).
- P4-Q5 is routed to the Promotion review (recall 0.33 to 0).
- The Promotion review prints "1 weeks", raw plan IDs, upper-case specialties and signed decimals.
- The Promotion review's Assumptions block says "no earlier weeks".
- Multi-week briefs quote a single-week change.

Two UI requests come with this work: the account menu's lane list is noise for every account, and the analyst should choose the period and the comparison length the way the Forecast lane's form does.

## Clarifications

### Session 2026-11-22 (grill with Michael; do not reopen)

- Q: How long may a brief be? → A: **At most two pages, in both views.** Nothing useful is cut for now; trimming is a later discussion. Depth beyond two pages sits in folded "Show detail" parts for analysts.
- Q: How should it read? → A: **Natural-language paragraphs.** Tables only for what really is a table (the territory table, the Promotion review's push figures). No bullet list longer than five items. No raw IDs (`SYN_GREAT_LAKES_MEDICARE_PART_D_1`, `PRIMARY_CARE`), no "1 weeks", no signed decimals.
- Q: What visual blocks? → A: A **KPI strip** (national TRx, change against the comparison weeks, BXA basket share, territories reportable n of 8), **one territory table** (TRx, change on last week, change on the comparison weeks, observed / projected / withheld), **the national chart**, and **story cards** (headline, confidence badge, one chart).
- Q: What do leaders see? → A: Bottom line, KPI strip, territory table, chart, stories, a short "What the data can't tell us", the **Assumptions** (comparison weeks and who chose them, like-for-like, projected or estimated territories, lag tested, review scope), and Next checks. Not data tables, SQL, method, glossary, splits or "considered and dropped". Splits stay with analysts because small cells are noisy (course Week 4) and to keep cuts that could drift toward rep level away from leaders (B-VI). Leaders get one line per story naming the drivers checked.
- Q: Does the scored answer change? → A: **No.** The `answer` text the eval scorers read stays complete. The blocks are built beside it from the same claims. Folding and the leader cut change what is shown, not what is scored.
- Q: Who writes the paragraphs? → A: **Both engines.** The scripted engine uses code templates written as paragraphs; the agent's Writer (Haiku) writes paragraphs around claim tokens, with the templates as fallback. The token check rejects any digit outside a token.
- Q: What weeks does the analyst pick? → A: **First week and Last week** (a period of at least one week, as in the Forecast form) and **"Compare with the previous N weeks"**: 1 to 13, default 4. brief-007's "same weeks last year" and "custom dates" move behind "Other comparison".
- Q: Who reads the question? → A: **Haiku proposes the scope; the analyst confirms it; code validates it.** As in the Forecast lane, the model turns the typed question into proposed weeks, territory, comparison length and whether it is a promotion question, which fill the form. The code parser decides in evals and when no model is configured. Haiku never sets a number in the brief. This amends B-II: Briefing constitution v1.1.0, reviewed by Meghna.
- Q: The account menu? → A: Remove the lane and role list ("Weekly briefing · Commercial Analyst · Forecast explanation · …") **for every account**. The trigger shows the signed-in name. The tester's Analyst / Leadership switch stays.
- Q: The brief-007 gaps? → A: Fixed in this spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A leader reads the brief in two minutes (Priority: P1)

The P3 leader opens an approved brief. At the top are four KPI tiles, then a three-to-four-sentence Bottom line, a territory table and the national chart. Each story is a short card with its confidence and one chart. The assumptions are stated plainly. Nothing on the page is a query or a data table.

**Why this priority**: It is the mentor's feedback, and the leader view is what the course presentation will show.

**Independent Test**: Open the leadership view of the 2026-08-24, P3-Q5 (Southeast, 5 weeks) and P4-Q1 briefs, printed to A4.

**Acceptance Scenarios**:

1. **Given** any brief, **When** the leader view renders, **Then** it shows the KPI strip, the territory table and at least one chart, and prints to at most two A4 pages.
2. **Given** the leader view, **When** it renders, **Then** it shows the Assumptions and a short limits paragraph, and no SQL, data table, method, glossary, split or "considered and dropped" line.
3. **Given** any number in a tile, table or paragraph, **When** it is compared with the analyst view, **Then** it is the same claim value.

---

### User Story 2 - An analyst reads paragraphs, with depth folded (Priority: P1)

Ace (P1) opens the same brief. He sees the same blocks plus citations on every number, the full "What the data can't tell us", the Appendix and the data behind each section. The splits, feed figures, method and glossary are folded under "Show detail", so the unfolded brief fits in two pages.

**Independent Test**: The P1-Q3 (2025-04-21) and P2-Q4 briefs in the analyst view.

**Acceptance Scenarios**:

1. **Given** any brief, **When** the analyst view renders with details folded, **Then** it prints to at most two A4 pages.
2. **Given** a story with splits, **When** the analyst unfolds it, **Then** the splits show as named cuts (plan, specialty, channel) with readable names, rounded TRx a week and small cells marked.
3. **Given** the scripted and the agent engine on the same question, **When** both render, **Then** they have the same blocks, sections and numbers; only the paragraphs' wording may differ.

---

### User Story 3 - The analyst sets the period and the comparison (Priority: P1)

Ace types "How did the Southeast do in August?" Haiku proposes Southeast, 2026-08-03 to 2026-08-31, compared with the previous 4 weeks. The form shows those values; Ace changes the comparison to 8 weeks and builds the brief. The brief names the eight comparison weeks and says the analyst chose them.

**Independent Test**: The API and UI checks for the scope route and the form; the eval harness with no model.

**Acceptance Scenarios**:

1. **Given** a typed question and a configured model, **When** the analyst asks for a scope, **Then** the form fills with the proposed first week, last week, territory, comparison length and promotion flag, and nothing runs until the analyst confirms.
2. **Given** a proposed or edited scope, **When** it is submitted, **Then** code validates it: weeks in the release, last week not before first, comparison 1 to 13 weeks inside the release. An invalid scope is refused with the reason before any brief is built.
3. **Given** no model configured, or an eval run, **When** a question arrives, **Then** the code parser sets the scope, as today.
4. **Given** any scope, **When** the brief is built, **Then** no model output sets a number in it.

---

### User Story 4 - Campaign questions answer what was asked (Priority: P2)

Magdalena (P4) asks "Where should the next dollar go?" The Bottom line answers that question: the release cannot rank channels or price a dollar (no spend data; calls and digital impressions moved together), the lapses cost about 120 to 200 TRx a week, and the next step is to discuss coverage backfill with sales operations. "Did the campaign reach the people…" gets the reach answer. The push figures are a table; each lapse is a short paragraph.

**Independent Test**: P4-Q1, P4-Q5 and P4-Q6 on the scripted engine; golden-number recall before and after (report-only).

**Acceptance Scenarios**:

1. **Given** P4-Q1 and P4-Q6, **When** both are answered, **Then** their Bottom lines differ and each answers its own question.
2. **Given** P4-Q5 ("How confident is the estimate, and when will we know more?"), **When** it is routed, **Then** it gets an answer that states the confidence and when the next read is due.
3. **Given** any Promotion review, **When** it renders, **Then** it has no "1 weeks", raw plan IDs, upper-case specialties or signed decimals, and its Assumptions do not say "no earlier weeks".

---

### User Story 5 - A cleaner account menu (Priority: P3)

Every account sees its name in the top-right menu, with sign-out, the survey and the suggestion link, and no lane or role list.

**Acceptance Scenarios**:

1. **Given** any account, **When** the menu opens, **Then** it shows no lane or role list; the tester still has the Analyst / Leadership switch.

### Edge Cases

- A brief with no story: the stories area says so in one sentence; the KPI strip and table still render.
- A withheld territory: its table row says "withheld" with no figures; its KPI effect is shown by "reportable 7 of 8".
- A multi-week period: changes are period against comparison weeks only; no single-week change is quoted unless the period is one week.
- The Promotion review: the KPI strip shows its own figures (territories with a lapse, longest lapse, push threshold) instead of the weekly KPIs.
- An older brief stored before this spec (no blocks): it renders as today.
- A model proposal that fails validation: the form shows the reason and keeps the analyst's last valid values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each brief MUST carry structured blocks beside its sections: a KPI strip on §1, a territory table on §2 and a card for each story in §3, each value a claim filled by code.
- **FR-002**: The `answer` text that the eval scorers read MUST stay complete; blocks, folding and the leader cut MUST NOT remove a claim from it.
- **FR-003**: Both views MUST print to at most two A4 pages, the analyst view with details folded.
- **FR-004**: Section text MUST read as paragraphs: tables only for the territory table and the push figures, no list longer than five items, no raw IDs or enum names, correct plurals, no signed decimals.
- **FR-005**: The leader cut MUST include the KPI strip, the territory table, the charts, the stories, a short limits paragraph, the Assumptions and Next checks, and MUST exclude data tables, SQL, method, glossary, splits and "considered and dropped".
- **FR-006**: The scripted engine MUST write paragraphs from code templates; the agent's Writer MAY write them around claim tokens, verified by the token check, with the templates as fallback.
- **FR-007**: The New briefing form MUST offer First week, Last week (period of at least one week) and "Compare with the previous N weeks" (1 to 13, default 4), with "same weeks last year" and custom dates under "Other comparison".
- **FR-008**: When a model is configured, the API MUST offer a scope route where the model proposes first week, last week, territory, comparison length and promotion flag from the question; code MUST validate the proposal; the brief MUST run only on the analyst's confirmed scope. Without a model, and in evals, the code parser MUST set the scope.
- **FR-009**: No model output may set or change a number, a week or the comparison in a built brief beyond the confirmed scope.
- **FR-010**: P4-Q6 MUST get a Bottom line that answers where the next dollar can go; P4-Q5 MUST get confidence and next-read timing; the Promotion review MUST meet FR-004.
- **FR-011**: A multi-week brief MUST NOT quote a single-week change.
- **FR-012**: The account menu MUST NOT show a lane or role list for any account.
- **FR-013**: Every gated check MUST stay at 1.000 on both engines (B-VII).

**Follow-up (2026-11-22 night, deterministic first; branch `feature/brief-008-polish`):**

- **FR-014**: The writer MUST name the comparison only through a code-filled phrase token (`{cmp}`), filled from the window the analyst chose ("the previous four weeks", "the same weeks last year", "the week of 2026-08-24"); the check rejects comparison wording the model writes itself ("the week before", "last week", "the prior weeks").
- **FR-015**: Each story's causal verb MUST be a code-filled token chosen from the story's confidence ("drove" for High, "moved with" otherwise, which agrees with a singular or plural subject); the causal-word rule covers the answer paragraph too; the writer prompt gives no free comparison example.
- **FR-016**: Briefing percentages MUST print as whole numbers at 10% and above and with one decimal below 10%; the shared `pct1` format (Forecast) is unchanged.
- **FR-017**: The agent MUST record the scope it proposes (`trajectory.scope_proposal`: territory, first and last week, comparison, intent) so core-011's `scope_match` scores it.
- **FR-018**: §1 and §2 MUST read as paragraphs, not one sentence per line, on screen and in print.
- **SC-006**: On a Haiku run, `needed_revision` is at most 15% (56% on 2026-11-22), with every gated check at 1.000 on both engines.

### Key Entities

- **KPI tile**: label, claim value, optional change and its direction, optional reference ("against 35.4% before launch").
- **Territory row**: territory name, TRx (claim), change on last week (claim or none), change on the comparison weeks (claim or none), basis (observed, projected, estimated, withheld).
- **Story card**: headline, confidence, drivers checked, prose paragraph, chart, folded splits.
- **Proposed scope**: first week, last week, territory, comparison length, promotion flag, source (model or code parser), validation result.

## Success Criteria *(mandatory)*

- **SC-001**: Every gated code check stays at 1.000 on both engines; zero digits outside claim tokens.
- **SC-002**: The leader and the analyst view (folded) of the five anchor briefs (2025-04-21, 2026-05-04, 2026-08-24, P3-Q5, P4-Q1) each print to at most two A4 pages.
- **SC-003**: Golden-number recall (report-only) does not fall below 0.668 on the scripted engine; P4-Q6 rises above 0.
- **SC-004**: Zero raw IDs or enum names in any rendered brief of the scripted run.
- **SC-005**: The model-proposed scope matches the code parser's on every golden question that names its weeks (a check, not a gate).

## Assumptions

- The territory table and KPI strip use claims the brief already registers; new claims are added only where a tile needs one (for example the share before launch).
- Two A4 pages are measured with the browser's print view at default zoom.
- The Promotion review keeps its own outline inside the six sections.
- Haiku is the model for scope reading (`anthropic:claude-haiku-5-5`), as for the agent team.
