# core-011 integration handoff (2026-11-22, night)

Branch `feature/core-011-eval-revamp` (worktree `pa-011`). Packets and what each did are in `PROJECT_STATE.md` (top entry) and `specs/core-011-eval-revamp/tasks.md`.

- Runs live in the `PharmAgentics-memo` worktree's MLflow store (it holds every baseline and `.env`): scripted `a5a49682`, Haiku `727bc006`. `eval insights --store <that store>` reads them.
- `src/pharmagentics/api/telemetry.json` was regenerated from that store, so the deployed Evaluation page shows the per-case table after the merge.
- Golden edits from packets D and G are `reviewed: false`; Michael reviews them on the review page (artifact `Y9d36cGC7shx5y1dEaYGXs`, collection `reviews`). Only after that and two runs do `key_fact_recall` and `finding_recall` join `GATED`.
- Promotion-review card rule (kept by Michael): promotion supported when TRx fell behind the other territories' trend during the lapse, ruled out when it kept pace, neither when the gap is unknown or the feed gate blocks TRx (then no direction either).
- Open: C-020, C-023 and C-024 span two periods, so their numbers stay context. A Forecast API test is flaky under heavy load.
- Next branch: `feature/brief-008-polish` (worktree `pa-008-P`, brief-008 FR-014 to FR-018), stacked on this one.
