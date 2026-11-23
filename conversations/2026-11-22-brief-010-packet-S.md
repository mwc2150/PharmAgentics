# brief-010 packet S: segment and channel percent (2026-11-22)

Branch `feature/brief-010-segments` (worktree `pa-010-S`), on packet P (`3653240`). Tasks S1 to S3 in
`specs/brief-010-target-analyses/tasks.md` are ticked. Spec: brief-010 FR-003, User Story 2. The scripted run and gate are the integrator's (I1).

## What was built

- `tools/splits.py`: `_cells` (per channel or specialty of a territory: the primary measure's weekly mean on the period and the comparison
  weeks, percent change, size in TRx a week on the smaller side whatever the measure; flat cells inside the 0.5% band are left out; no
  claims), `mover_text(reg, p, territory, by, quote_small=False)`, `segment_line(reg, p, territory, quote_small=False, lead="")`.
  At most `MOST_MOVERS` = 2 a grain, largest absolute change first, each a claim (`get_segment_metric`, `pct1`) labelled grain `channel` or
  `specialty` and cut `channel:<NAME>` / `specialty:<NAME>`. Only when the definition's grain has the dimension, and only for a territory
  the gate leaves reportable with comparison weeks.
- Story text (`briefing_baseline/pipeline.py::_story`, and the same line in `mcp_server/server.py::story_section` for the agent engine): one line
  after the head, before "Checked, in this order:", for example "By channel: Medicaid down 24.9%, Commercial down 16.2%, Cash too small to
  quote; by specialty: Internal medicine down 21.7%, Primary care down 19.7%." A small cell (under `SMALL_CELL`, TRx a week on either side)
  is never given a number in a story: it is named "too small to quote" when it would have ranked among the movers.
- Promotion review (`tools/promotion.py::_segment_lines`): each lapse story gets a fourth line, "Over the lapse, by channel: ...; by
  specialty: ... In its first four weeks, by channel: ...; by specialty: ...", against the four weeks before the lapse, with the review's
  own windows. Here a small cell is quoted with its flag "(small cell: noisy)" (see decisions).
- Percent format: the repo's `pct1` (one decimal, "31.4%"). I found no "whole from 10%" format in the code or brief-008 spec; `pct1` is what
  the cut cards, the stories and the golden scorer already use, and it states the exact value at the scorer's precision.
- Extra measures and extra comparisons: not done (movers use the primary measure and primary comparison only). Cheap to add later with
  `reg.under(measure=...)` as in `splits.cut_figures`.

## Decisions to confirm (Michael)

1. **GL cash is a small cell, and the golden needs it.** Great Lakes cash is 48 TRx a week before and 33 during (under `SMALL_CELL` = 50), but
   `gl_cash_change_pct` is a must-state fact (exact -31.443). A rule of "small cells are never given a number" cannot state it. I applied the
   strict rule in territory stories (S1) and the "quote it, flagged noisy" rule in the Promotion review (S2), which is what the P4-Q2
   golden itself says ("flags small cells as noisy"). `mover_text(..., quote_small=True)` is the switch. The spec's edge case and FR-003 text
   ("above the small-cell floor") disagree with the P4-Q2 acceptance scenario; one of them should be reworded.
2. **Windows.** The review detects Great Lakes' lapse as ten weeks (2026-02-02 to 2026-04-06) and Southeast's as five (08-03 to 08-31). The
   golden reads Great Lakes on its first four weeks (02-02 to 02-23, exact -31.4%) and Southeast on all five. No single rule gives both, so
   the review states the movers over the whole lapse and, for a lapse longer than four weeks (`stages.BASELINE_WEEKS`), also over its first
   four weeks. Over the whole lapse Great Lakes cash is -29.7%, Southeast commercial -30.1%; first four weeks -31.4% and -29.0%. It
   costs about 50 words a lapse; say if you would rather have one window.
3. The movers sentence reaches the leader view (it is story text, not a split table). Leader words rise with it.

## P4-Q2 now (scripted, golden definition)

States `gl_cash_change_pct` ("Cash down 31.4% (small cell: noisy)", first four weeks) and `se_commercial_change_pct` ("Commercial down 30.1%"):
key facts 0 of 2 to 2 of 2. Findings are unchanged (both lapses already scored). Words (analyst, leader): **637 / 612 to 734 / 709**; the
review is under WORD_BUDGET 836.

Other cases (analyst words, leader words, before to after; key facts unchanged, all 3 of 3 or 2 of 2): P4-Q1 784 / 750 to 833 / 799;
P2-Q2 632 / 445 to 648 / 461; P1-Q4 817 / 638 to 834 / 655; P2-Q3 758 / 576 to 778 / 596; P3-Q4 806 / 677 to 825 / 696; P4-Q4 828 / 560
to 724 / 559 (the longest territory card shrinks to its headline: its lines, with the movers, are folded and still scored); P1-Q1 745 / 707
unchanged (no story). All inside 836. P1-Q4 (834) and P4-Q1 (833) have two words and three words of room: any further addition to a
story will trip `over_word_budget` there. P4-Q1 leader 799 was already over the leader budget (705) before this packet (750).

## Fixtures regenerated from the engine (not hand-edited)

- `tests/fixtures/scripted_answers.json`: the 2026-06-08 Pacific and 2026-07-13 Mid-Atlantic entries (a story each). The other four are unchanged.
- `tests/fixtures/brief010_db_baseline.json`: P1-Q1, P1-Q4, P2-Q2, P2-Q3, P3-Q4, P4-Q4 (a story each). CMP-3, P3-Q1, WIN-1 unchanged.
  That file is one line of compact JSON, so a merge conflict is all or nothing: regenerate with the engine if it conflicts.
- `tests/test_promotion_review.py`: a lapse story may now be four lines (was three).

## Tests (focused only; no full suite, no eval run, no model)

New `tests/test_segment_percent.py` (21): P4-Q2 states both facts (through the scorer's `key_fact_counts`, and the printed value equals the
golden SQL run on the governed view), the lapse and first-four-weeks windows, a small cell never unflagged in the review and withheld in a
story, at most two movers a grain and ordered, claim labels (grain, cut, tool), no digit outside a token, grain without channel or specialty
shows none (story and review), nothing outside the flat band gives no line, a withheld territory gives no line, a story without the
line reads as before, the analyst view inside the budget. See "Results" below for the other focused files.

## Open issues

- The Haiku agent: the Writer words stories around the line the Manager's story section carries (`server.story_section`); not run here.
- Leader view: the line is visible to leaders (decision 3).
- Spec wording on small cells (decision 1) and the golden P4-Q2's windows (decision 2).
