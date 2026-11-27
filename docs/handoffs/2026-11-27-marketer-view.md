---
branch: packet/marketer-view
lane: briefing
next: Michael reviews the screenshots under local/marketer-view/ and merges; then the Marketer sees the promotion read on the hosted app
---

# v2 Marketer (P4) view: promotion panel and budget note (2026-11-27)

Based on `feature/v2-assumptions-first` 916bd79 (after the promotion-verdict packet). Scripted engine only; no model was run.
Approved by Michael on 2026-11-27 (Q15).

## What changed

- `api/views.py`: `marketer(record)` is `leadership(record)` plus, on each §3 story section whose stored card has `promotion`, a
  `promotion` object built from an allow-list (verdict, lag_label, new_patients and trx, the four channels, the effect's low, high,
  word and territories, separable_from, recheck) and a top-level `budget_note`. The effect also carries `phrase`, from
  `lag_checks.effect_words`, so the client never builds a sentence from numbers. Never sent: `held_level`, `method`, `threshold`,
  `tested`, `lag` (number), evidence ids, SQL, claim tokens. `leader_payload(record, "P3")` is unchanged (`leadership`); P1 and P2
  previews are unchanged. The tester's "marketer" view resolves to persona P4 through `rbac`, so it gets the same payload.
- Frontend: `Promotion.tsx` (new) draws the panel (verdict in words, a table of New patients (NBRx), TRx and the four channels, the
  lag and the re-check date, and when supported "Compared with N territories without a promotion change: <range>" with a note that it
  is a range across those territories, not a return on spend) and the budget note; `Memo.tsx` puts the panel under a story's card text
  and the note after §3 (once); `App.tsx` gives the Marketer's landing its own intro line (the Director's is unchanged);
  `agent/briefingApi.ts` has the types. On a phone the table rows stack (name and change on one line, figures and the "moved"
  marker under it), so nothing scrolls sideways or clips.
- Tests: `tests/test_marketer_view.py` (6 tests); `tests/ui/check_marketer_view.py` (Playwright, 1280 and 390 px).
  `tests/test_signoff.py` and `tests/test_brand_access.py` asserted "P4 reads exactly what P3 reads"; they now assert P4 equals P3 plus
  the budget note.

## Not done

- `not_separable` and `ruled_out` do not occur in the three scripted briefs used for the browser check, so their wording was checked
  on a payload the browser rewrites in flight (labelled as such in the script), not on a server brief.
- No Haiku or agent-engine brief was read in the Marketer view.
