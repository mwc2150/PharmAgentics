@README.md

# brand-briefing rules

- No digit in a brief comes from a language model: the writer fills claim tokens, and code fills the numbers.
- Say "competitive intelligence", never "statistical surveillance" or "surveillance". Say "new patients" only for NBRx.
- No output line identifies an individual rep.
- Prompts under `*/prompts/` are code. Changing one is a system change: run `uv run python -m eval run --system <name> --lane briefing` and the gate.
- MAF prompt templates treat braces as placeholders: write literal claim tokens as `{{c7}}`.
- A Magentic team that hits its round cap returns no answer. The code must handle that.
- Briefing-lane rules are in `.specify/memory/constitution-briefing.md`.
