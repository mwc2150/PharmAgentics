# brief-008 packet R: rendering the blocks (2026-11-22)

Branch `feature/brief-008-render` (worktree `pa-008-R`). Files touched: `frontend/figma-make/src/Memo.tsx`, `frontend/figma-make/src/agent/briefingApi.ts` (MemoSection and its new block types only), `frontend/figma-make/src/index.css` (print rules appended). No call site in `App.tsx` changed; none needed.

## What changed

- **Types (R1).** `MemoSection` gains optional `kpis`, `territory_table`, `card`, `detail`, `detail_citations`. New types `KpiTile` (with `value_citation`), `TerritoryTable` / `TerritoryRow` (with `cell_citations`), `StoryCardBlock` (with `headline_citations`).
- **Memo.tsx (R2, R3).**
  - `KpiStrip`: `<dl aria-label="Key figures">`, one tile per KPI (label `dt`, big tabular value `dd`, detail `dd`). Direction is an arrow plus a screen-reader word ("up", "down", "unchanged"); up is teal, down red, flat muted. Values are `Cited`, so analysts click through to evidence.
  - `TerritoryTableView`: real `<table>` with a screen-reader caption, `th scope="col"` and `th scope="row"`, sans face, tabular numbers, numbers right-aligned. The "Basis" column is a quiet label (amber for projected or estimated). A withheld row shows "withheld" across the number columns and a dash in Basis, ignoring any cells. The note shows under the table.
  - Story cards: sections with `card` render a bordered card with the headline, a "High / Medium / Low confidence" badge (always a word), "Checked: promotion, access, ...", the paragraphs, the chart (without a second border) and the detail.
  - `detail` sits under a native `<details>` ("Show detail" / "Hide detail"), analysts only (shown only when `claims` is passed; the leader cut never carries it).
  - Paragraphs: section `text` splits on blank lines into `<p>` at 68ch (and a run of "- " lines into a `<ul>`); citation offsets are re-based per paragraph, and `Cited` still drops any span that does not match its claim.
  - **Old briefs.** If no section has any new field, the memo renders exactly as before (one pre-wrapped block). "Modern" is decided per memo (`sections.some(kpis | territory_table | card | detail)`), so §4 to §6 of a new brief also read as paragraphs.
  - Nothing computes or formats a number; every string is shown as the server gave it.
- **Print (R4).** `@media print` block at the end of `index.css`: A4 page, light palette (token overrides on `:root`), hides sidebar, header, footer, nav, forms (message bar), dialogs, and every button except citation buttons; unfolded `details.pa-fold` only print when open (closed ones are hidden); tiles, table rows, figures and cards do not break across pages; the shell's fixed height and scroll container are released so the memo flows across pages.

## Checks

- `npx tsc --noEmit -p tsconfig.app.json`: pass.
- `npx vite build --config vite.config.standalone.ts`: pass (500 kB chunk warning as before).
- `uv run pytest -q tests/test_frontend_scope.py`: 2 passed. No new frontend file.
- Server-side render of `Memo` through Vite SSR with a sample analyst brief, the same brief as a leader cut, and an old brief (scratchpad script, not committed): tiles, table (withheld and projected rows), card, citations and the folded detail came out as intended; the leader render has no buttons and no detail; the old brief renders as one pre-wrap block.
- `npm ci` is not possible (the repo has `pnpm-lock.yaml`, no package lock); installed with `npx pnpm@9 install --frozen-lockfile`.

## Not verified (open)

- Print was not measured in a browser. The two-A4-page limit (FR-003, SC-002) needs the integrator's check on the real app (I2). Likely tuning knobs: `.pa-prose` size (10.5pt), `.pa-kpi-value` (17pt), table font (9.5pt) in the print block.
- Print hides every button that is not a citation button, including Approve, Return and the like in the analyst page; their empty panels may leave a little spacing.
- The dark theme was assumed (the worktree base has the dark tokens). If the light theme from `feature/ui-light-theme` merges first, the print block still overrides the tokens on `:root`, but the print override colours may need a second look.

## Assumptions about the schema

- `territory_table.rows[j].cell_citations` is a list of span lists, one per cell, with offsets inside that cell's string (the plan only says "in the same span form"). If the backend sends one flat list, it will not attach; tell me and I will change the lookup.
- `kpis[i].value_citation`, `card.headline_citations` and `detail_citations` are span lists over the filled string, as for `text_citations`. `kpis[i].detail` and `territory_table.note` carry no citations (the plan lists none) and show as plain text.
- The `Basis` column is found by header text "Basis" (case-insensitive); the cell text is shown, falling back to `row.basis`. A table without that column still renders.
- A withheld row has no figures; the UI shows "withheld" regardless of the cell strings.
- `card.drivers_checked` entries are shown verbatim, joined with ", ".
- Direction colouring is not a judgement of good or bad: up is teal, down is red, always with an arrow and a spoken word.
