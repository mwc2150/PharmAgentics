---
branch: packet/uat-review
lane: shared
next: fix H-1 to H-4 of docs/reviews/2026-11-27-uat-review-v1.md, then rerun the uat-review skill on the next version with local/state-v1 seeded
---

# UAT review skill and v1 baseline

Added the `uat-review` project skill (`.claude/skills/uat-review/SKILL.md`), the Playwright capture script (`tests/ui/review_walkthrough.py`, Playwright added as a dev dependency) and the first review of `origin/main` at `09cb1ed` (`docs/reviews/2026-11-27-uat-review-v1.md`: 39 findings, 4 High). Run: start the app as the skill says, then `uv run python -u tests/ui/review_walkthrough.py --label <label>`; evidence goes to `local/reviews/` (git-ignored). Not pushed; no PR. The agent-team brief was not run (no key).
