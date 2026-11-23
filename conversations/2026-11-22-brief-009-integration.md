# brief-009 integration: handoff (2026-11-22, late night)

Claude Opus (integration) with Sonnet packets E and T and one Sonnet fix packet. Branch `feature/brief-009-timeline` from `main` cc0a740.

## Contents
- Packet E (`d2d3026`, `153dfaf`): event log on both engines, live `progress`, `events` and `claim_events` on the saved brief, leader `process_summary`. See `2026-11-22-brief-009-packet-E.md`.
- Packet T (`0a17237`): `Timeline.tsx`, `HowItWorks.tsx`, `GET /api/briefing/agents`.
- Merge `4e2ea7b`; review fixes `fcc71b4` (tasks R1 to R10).

## Results
| Run | System | Against | Gate |
|---|---|---|---|
| `104da6d2e59d424ca3e3716d6982396b` | scripted, before fixes | `a5a49682` | exit 0, seven 1.000, answers unchanged |
| `be5f26cde73d4bf595ef44d32a97d488` | Haiku, before fixes | `727bc006` | exit 0, seven 1.000, recall 0.682 |
| `e4e5194e91254a5398daf2e58b66caa2` | scripted, after fixes | `a5a49682` | exit 0, seven 1.000, answers unchanged |

Full suite after the fixes: 933 passed; `test_a_split_follow_up_locates_the_gap_and_can_be_pinned` failed under load and passes alone.

Live check (local server, dev auth, Haiku worker): triage then brief; progress grew 0 to 25 events; actors Code, Manager, Data Forensics, Driver Investigator, Writer, Person; prompt refs present; 82 of 82 claims own an event; event story ids equal the investigated `triage.calls`; leader view carries no event keys; leader gets 403 on the job route. The UI on :8080 runs this branch for a visual check.

## Open
- Not re-run on Haiku after the fixes (the fixes move when summaries are filled and when progress is saved; answers are unchanged on the scripted gate and the agent on/off equality test).
- Live in-story summaries can read "a figure" until the story closes; the saved brief has the values.
- `persist_progress` writes outside the lock; a store write slower than the 30 s join could land after `complete`. In-memory state stays right.
- Scripted triage route records no events (the scripted brief carries them).
- Merge order: after PR #22 (brief-008 polish).
