# Plan: brief-010 The Analyses the Targets Need

A file contract for the four work packets in `tasks.md`. Starts after the golden review and the brief-009 merge; rebase on `main` first.

## Shapes

A cut card (core-011 FR-017), built by code in `src/pharmagentics/tools/memo.py`:

```python
{"headline": "Medicare Part D plan one in Mid-Atlantic fell {c1} to {c2} TRx a week, while Mid-Atlantic rose {c3}.",
 "confidence": "High", "drivers_checked": ["Access", "Promotion", ...],
 "territory": "MID_ATLANTIC", "cut": "plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1", "direction": "down",
 "drivers_supported": ["access"], "drivers_ruled_out": ["promotion", "supply", "competitor", "data"],
 "text": "... TRx a week {before} before, {after} on the comparison weeks ({pct}) ..."}
```

A national card: `territory: "NATIONAL"`, `cut: None`, `direction` from Metacora's basket-share change.

## Packets and the files they own

| Packet | Owns |
| :- | :- |
| **P: plan cuts** (FR-001, FR-002, FR-007, FR-008) | `src/pharmagentics/tools/splits.py` (a cut screen beside `split_change`: per-plan before, after, percent, against the territory), `tools/memo.py` (`cut_card`, the §3 order, the budget shrink), `briefing_baseline/triage.py` (cut cards as candidate stories), `briefing_agent/plan.py` (the Manager sees them), tests |
| **S: segment and channel percent** (FR-003) | `tools/splits.py` (percent movers by channel and specialty), `tools/memo.py` (story text), the Promotion review builder (find it from `memo.py`), tests |
| **R: restatement detail** (FR-004, FR-005) | `tools/checks.py` or a new `tools/restatement.py` (naive vs deduplicated; signed-off vs restated from `raw.restatement_log` through a governed view; add the view in `data/` if none exists), `tools/memo.py` (§2 and §4 text, the restatement card), tests |
| **N: national card** (FR-006) | `tools/memo.py` (`competitor_card` becomes the national card), the competitor check's national verdict, tests |

P and S both touch `splits.py` and `memo.py`: run them one after the other, not side by side. R and N touch different parts of `memo.py` and may run beside each other after P.

## Checks per packet

Focused tests; the scripted run and gate against the previous packet's run (exit 0; all seven at 1.000); the merge bar (core-011 FR-019): `key_fact_recall_pooled` and `finding_recall_pooled` do not fall, `over_word_budget` 0, the packet's target cases rise. The Haiku agent run after P and after the last packet. A real-app look at one cut card and the national card in both views.
