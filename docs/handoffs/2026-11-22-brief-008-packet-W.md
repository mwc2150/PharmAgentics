# Handoff: brief-008 packet W (the Writer's paragraphs)

Branch `feature/brief-008-writer`, worktree `C:\Users\micha\test_agent_v1\pa-008-W`. Not pushed. No model call, no eval run.

## What changed

- `prompts/writer.md` rewritten for the new memo: it names the tiles, the territory table, the story cards and what is folded (splits, feed figures, method, glossary, "considered and dropped"), and asks for: the answer in two or three short sentences; each story as a paragraph of two to four short sentences (what moved, what the checks found, how sure); chart lines of one or two sentences. Rules: STE short sentences (at most 20 words), one plain paragraph, no digit and no spelled-out number, readable names only, only the allowed tokens, "association" for promotion and causal words only for a High story, no repeat of tiles, table, headline or "Next:".
- `prompts/revise.md` carries the same rules in short form.
- `write.py`: new `style()` and the checks it holds, called from `problems()`: list, line break or markup; raw IDs (`SYN_...`, `PRIMARY_CARE`, `territory:`/`competitor:` prefixes, ALL-CAPS words of 5+ letters, snake_case); spelled-out numbers (two..twenty, tens, hundred, thousand, percent, half, double, twice; code's own "four weeks before", "four-brand", "week of" are exempt); a named rep; folded-detail terms (split, by plan/specialty/channel, cuts of the change, considered and dropped, glossary, "Method:"); a sentence over 25 words; paragraph caps (answer 4, story 5, chart line 3 sentences). `problems(..., causal_ok=, max_sentences=)`; `check` and `clean` take `confidences` (story id to its stated confidence, from the new `confidence(section)`): causal words are rejected for a story that is not High, and in the answer unless every story is High. Without `confidences` the causal check is skipped (old callers unchanged). `sections_text` now shows the figure tiles and which territories are not plainly observed (no per-territory figures), and `section_tokens` allows the tile tokens in the answer. `chart_explanations` uses the sentence cap. `assemble` is untouched.
- `briefing_agent/__init__.py` (`_write`): three-line change, builds `confidences` from each story's section and passes it to `check` and `clean`. Not in any packet's file list; the integrator should glance at it.
- Fallback is unchanged: one revise round, anything still failing is dropped and the code template stands.

## Tests

`uv run pytest -q tests/test_writer_prose.py tests/test_agent_build3.py tests/test_followup_agent.py`: 44 passed. New `tests/test_writer_prose.py` covers each rule, the causal rule by confidence, chart lines, prompt formatting, the Writer's view of the Southeast brief (tiles and table in, folded detail out), and `_write` end to end with stubbed replies (good reply kept; bad reply revised once, the story that still fails dropped; typed digit and invented token never kept).

## Open issues and risks

- The new checks are stricter than before. A Haiku reply that spells a number ("two stories"), runs long, or says "because" for a Medium story is rejected, revised once, then dropped, which leaves the story with no paragraph. Watch the dropped counts.
- Spelled-out number check may reject honest phrases ("half the territories"); words like "one" are not checked.
- "ALL-CAPS 5+ letters" would flag an acronym such as "MEDICARE" typed in capitals; ordinary acronyms (BXA, TRx, NBRx) pass.
- Story paragraphs sit under the card headline in the UI; the code story lines still list the checks, so the paragraph should add the reading, not the list.

## What to look for in the Haiku run

1. `dropped` lines in the trace (`6_verification`): which rule rejects most. If "spells out numbers" or "sentence of N words" dominates, loosen the check or tighten the prompt rather than keep dropping.
2. Revise rate (`revised` true) against the last agent run.
3. The kept paragraphs in a rendered brief: two to four short sentences, no bullets, no IDs, "association" wording on Medium and Low promotion stories, no restated splits.
4. All gated code checks stay 1.000; zero digits outside tokens; golden-number recall unchanged (the Writer adds no number).
