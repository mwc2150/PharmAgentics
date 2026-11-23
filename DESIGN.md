# Design

The web app (`frontend/figma-make`) is an analyst's tool: quiet, precise, consistent. The interface recedes so the evidence and the decision lead. The theme is "Positivus dark": a near-black page, one seafoam accent (lime until 2026-11-23), chunky controls and panels that sit on a hard offset slab instead of a soft shadow. Product context is in [PRODUCT.md](PRODUCT.md); tokens live in `frontend/figma-make/src/index.css`.

## Theme

Dark only. Neutrals carry the page; seafoam (#3ecfb2) is the one accent and it is rationed. It marks the primary action, the current selection and focus, links and citations, and one highlight block (see "Where seafoam is allowed").

Tokens (Tailwind `@theme`; use as `bg-primary`, `text-muted`, `border-edge`). The old names `navy`, `navyhover`, `seafoamdeep`, `onaccent`, `agent`, `agentdeep`, `agentbg` are deprecated aliases kept for other branches; do not use them in new code.

| Token | Value | Use | Contrast |
| :- | :- | :- | :- |
| `paper` | #101117 | Page, input wells, hover fill on rows | base |
| `sheet` | #1b1d27 | Panels and the sidebar (one flat, solid layer) | base |
| `ink` | #f3f3f3 | Body text | 17.0:1 on `paper`, 15.1:1 on `sheet`, 13.9:1 on `primarybg` |
| `muted` | #a6aabf | Secondary text, labels, axis text | 8.2:1 on `paper`, 7.3:1 on `sheet`, 6.7:1 on `primarybg`, 4.8:1 on `rule` |
| `rule` | #373a52 | Panel borders, dividers, bands, gridlines | 1.5:1 on `sheet` (decorative only; never the sole edge of a control) |
| `edge` | #8a8ea6 | Borders of controls (fields, secondary buttons, switch, tab pill) | 5.8:1 on `paper`, 5.2:1 on `sheet` (needs 3:1) |
| `slab` | #3a3e58 | Hard offset shadow under panels, secondary buttons, the tab pill | 1.8:1 on `paper` (decorative) |
| `primary` | #3ecfb2 | Primary button fill; current selection, focus ring; the highlight block; chart marks; links and citations | 9.7:1 on `paper`, 8.6:1 on `sheet` |
| `primaryink` | = `primary` | Accent text (links, citations, the current tab's label); its own token in case a darker accent returns | as `primary` |
| `primaryhover` | #62dbc3 | Primary button hover fill | `onprimary` on it 11.6:1 |
| `primarydeep` | #1f7a68 | Hard shadow under the primary button and under the logo tile | shadow, decorative |
| `primarybg` | #0f2622 | Current sidebar row, hovered citation | `ink` 14.3:1 |
| `onprimary` | #0b0c10 | Text on seafoam fills (button, highlight block, active view switch, selection) | 10.0:1 on `primary` |
| `ok` / `okbg` | #8ab4f8 / #14233f | Verified and approved, always with a word or a check mark | 7.4:1 |
| `amber` / `amberbg` / `amberline` | #fbbf24 / #2d2209 / #5c4513 | Data-health warnings, uncertainty, review required | 9.4:1 on `amberbg`, 10.1:1 on `sheet` |
| `neg` | #f87171 | Adverse change, rejection, Sensitive data | 6.1:1 on `sheet`, 6.8:1 on `paper` |
| `warn` / `warnbg` | #c9ccd8 / #23253a | Rejected and withheld states (neutral grey, a word carries it) | 9.4:1 |
| `human` / `humanbg` | #c4b5fd / #26213f | Leaders and human review | 8.3:1 on `humanbg`, 9.1:1 on `sheet` |

Every text pair clears WCAG AA (4.5:1), and control borders and focus rings clear 3:1. Remeasure after any colour change. Ratios above were measured against the token values in `index.css`.

### Where seafoam is allowed

- The primary action (`BTN`): seafoam fill, `onprimary` text. One per view.
- The current selection: the current sidebar item's icon, the current tab's label, the active view-switch segment, the current marker in a chart. Focus: the 2px `primary` outline (offset 2px) on every `:focus-visible`, including memo citations and menu items (an inset ring there), and the text-selection colour. Under `forced-colors` the highlight block becomes a rule and the current item an outline.
- Links and citations: a cited figure is underlined with a dotted seafoam line and carries a seafoam evidence number; "Ask about this" is a seafoam text link.
- One seafoam block per view section: the greeting at the top of a workspace, and the top-level heading of each memo section (`.pa-mark`, `onprimary` text, 8px radius, `box-decoration-break: clone` so a wrapped heading keeps its block). Sub-sections (§3.1 and below) stay plain text with a 2px `rule` bar on the left.
- The one data series of a chart, and the filled dot for a material change (hollow = not material).
- Seafoam never means state. Approved, warning, adverse, paused and rejected come from `ok`, `amber`, `neg`, `warn` and always carry a word.

## Type

- **Space Grotesk** (self-hosted variable, weights 300 to 700, `public/fonts`) for the page title, the greeting (a paragraph, not a heading), memo section headings, panel headings and figures (KPI values, dashboard numbers). h1 to h3 are 700 with -0.02em tracking and balanced wrapping. The wordmark is Space Grotesk 18px bold. `font-display` is the class; `font-serif` is a legacy alias for the same face.
- **IBM Plex Sans** (self-hosted variable, 100 to 700) for the interface, labels, tables, data and brief prose. Numbers use `tabular-nums`. Body is 15px.
- Brief prose is Plex Sans now (it was a serif): 16px, line height 1.65, at most 68 characters a line. One reading face keeps a figure inside a sentence in the same digits as the tables and tiles beside it, and Space Grotesk's wide, geometric letters tire over a paragraph.
- Scale in use: page title 18px (20px from `sm`) bold; greeting 32px, line height 1.25; memo section heading 20px bold, line height 1.5, with a 14px mono `§n` marker in `muted`; memo sub-section 16px semibold; panel heading 14px semibold; KPI value 28px bold; button and field text 14px; field label 12px medium `muted`; KPI label and classification 11px uppercase (0.05em and 0.06em tracking); chips 11px medium; chart text 9 to 11px.
- Source Serif 4 is no longer used; its font files were removed from `public/fonts`.

## Components

Use the shared class constants in `App.tsx` (`Overview.tsx` keeps its own copy of `BTN`), not one-off styles:

- `BTN` (primary, one per view): `primary` fill, `onprimary` 14px semibold, 14px radius, padding 20/10px, hard shadow `0 4px 0 primarydeep`. Hover `primaryhover`. Press: moves down 3px and the shadow shrinks to `0 1px 0`. Disabled: `rule` fill, `muted` text, no shadow.
- `BTN2` (secondary): transparent, 1px `edge` border, `ink` 14px medium, shadow `0 3px 0 slab`. Hover fills `paper`. Press: down 2px, shadow `0 1px 0`.
- `FIELD`: `paper` well, 1px `edge` border, 14px radius, 14px text. `LABEL` above it. `PANEL`: `.pa-panel`, 22px radius, 1px `rule` border, `sheet` fill.
- Controls are 14px radius (`--radius-lg`); panels are 22px (`--radius-xl`); the highlight block is 8px; status and actor tags 6px. Nested tiles (KPI tiles) use the 14px control radius.
- Tabs (`SubTabs`): plain text; the current tab is `primary` semibold. A pill slides behind the current tab: `paper` fill, 1px `edge` border, 14px radius, shadow `0 3px 0 slab` (280ms ease-out; none with reduced motion). The row wraps rather than scrolls. They follow the tab pattern: roving tabindex, arrow keys and Home/End move focus, Enter or Space selects. The current tab's data classification sits at the row's end.
- View switch (`ViewToggle`, analyst/leadership): a small bordered control (1px `edge`, 14px radius) with a solid seafoam segment for the open view and `muted` text on the other. It is a group of `aria-pressed` buttons, not tabs; the open view stays focusable.
- Sidebar items: 14px radius rows, 20px icon. Current: `primarybg` fill, `ink` text, semibold, seafoam icon, `aria-current="page"`. Hover: `paper` fill, `ink` text, seafoam icon. Not current: `muted`.
- Lists are rows divided by `rule` inside one panel, never grids of cards.
- Tags only for status (in review, approved, paused, confidence) and actors (Code, Agent, Person): an outlined word (1px border in the state colour or `edge`), never a filled pill. Approved adds a check mark.
- Data classification (core-009) is a quiet uppercase text label, never a coloured pill; only Sensitive takes a colour (`neg`).
- Memo: KPI tiles (up to four across; 14px radius, `rule` border, `sheet` at 60%) with the value in Space Grotesk 28px and a direction arrow plus a screen-reader word; story cards (22px radius, `rule` border, `sheet` at 40%); tables in Plex Sans 13px with tabular figures.

## Dashboards and charts

- A dashboard opens with one stat bar: up to four figures in one panel, divided by `rule`. A change line under each figure; only an adverse change takes `amber`, and it always says "Down" or "Up" in words.
- Lists of entities are rows in one panel; a chart that belongs to each row lives in a column of that row (the Overview's dot against each territory's normal range), with the axis in the column header. No separate chart-plus-list.
- One series per chart, one axis per chart. Different scales (TRx, NRx, NBRx) are small multiples, never a dual axis.
- Meaning never rides on colour alone: state is filled versus hollow, plus a word. Every mark has a hover readout and an accessible name.
- Every figure opens what produced it: a slide-out panel with its governed query and the pinned data version.
- Marks: 2px lines in `primary`, dots at least 10px, recessive bands and gridlines in `rule`, axis text in `muted`.

## Surfaces and depth

- Depth is a hard offset slab: `0 5px 0 slab` under panels (`.pa-panel`), `0 4px 0 primarydeep` under the primary button, `0 3px 0 slab` under the secondary button and tab pill. No blur radius, no spread, no glow, no soft shadow.
- Panels are one flat `sheet` layer on the `paper` page; the sidebar and header are separated by a 1px `rule` line, not a shadow.
- Frosted glass (`.glass`, `sheet` at 80%, 16px blur) only on things that float over the page: the phone drawer and toasts. Menus are solid panels (`.pa-panel`), so nothing shows through them. The dialog scrim is black at 60%.
- Motion is state only: 150 to 300ms, exponential ease-out; none with `prefers-reduced-motion`.
- Print: the memo prints as a plain light A4 page. Tokens are redefined to light values, shadows and the seafoam block are removed (the heading prints as text), and app chrome and buttons are hidden.

## Layout

- Sidebar: a 64px icon rail; the header toggle or Ctrl+B opens it to 248px and the choice is remembered. On phones the same toggle opens a 280px slide-out drawer. The header is 64px tall.
- The rail's logo tile is its only seafoam tile; the wordmark appears beside it when the sidebar is open.
- Content (`.workspace-content`, max 52rem) is centred on the whole page, using `--shift` (the rail's width when the sidebar is closed), and clears the sidebar when the screen is narrow.
- Dashboards (the Overview tab, Evaluation) use `.workspace-wide` (max 72rem), centred the same way. Reading pages stay at 52rem.

## Logo

- One logo: `public/pa-mark.svg`, a periodic-table-style element tile. A seafoam (`primary`) rounded tile with "Pa" large in Space Grotesk and "v1" small in the top-left corner, where an element's number would sit. Letters are outlined paths in `onprimary`, so no font loads. A hard slab in `primarydeep` sits 4 units below the tile (the same offset shadow as the primary button).
- It is an SVG on a 64-unit square, so it scales freely: 36px in the rail, 56px on the sign-in card. Give it its own size class; it is decorative (`alt=""`) next to the name.
- `public/favicon.svg` is the same tile without "v1" and without the slab, so "Pa" stays legible at 16px. `favicon.png` is the raster fallback.
- Use it in the rail and the sign-in card only. Never repeat it in the page.

## Sign-in pages

The pages people see before the app follow the same theme. Keycloak's login uses the `pharmagentics` login theme (`deploy/keycloak/themes/pharmagentics`, over keycloak.v2): near-black page, the tile mark beside the "PharmAgentics" wordmark, one 22px panel with the `slab` shadow, 14px fields with `edge` borders and a seafoam focus ring, and a seafoam "Sign in" button with the `primarydeep` shadow (not full width). Errors are a red word under the field, never a filled banner. The realm's display name is "PharmAgentics" (no "UAT"). The API's own pages (dev sign-in, "Starting the sign-in service") share one template in `src/pharmagentics/api/auth.py` with the same panel, mark and buttons. Keep the theme's hex values in step with `index.css` when a token changes.

## Avoid

Avatar circles with initials, coloured badge pills with icons, tinted and ringed selected states, a logo repeated in the page, hero headings on working screens, full-width buttons, and blur on solid panels. Also:

- Seafoam as decoration: a seafoam border, icon, divider or chart fill that carries no action, selection or link.
- Seafoam on more than one block per view section (a second highlighted heading, a seafoam panel header, a seafoam tile beside the greeting).
- Seafoam for state (approved, warning, adverse, paused); use `ok`, `amber`, `neg`, `warn` with a word.
- Blurred shadows and glows on solid panels, buttons and tiles; the offset slab is the only depth.
- Meaning carried by colour alone.
